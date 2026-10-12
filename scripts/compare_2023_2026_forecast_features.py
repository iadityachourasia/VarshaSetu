"""Common-footprint 2023/2026 forecast-feature distribution diagnostic.

Uses only frozen feature matrices and forecast-side receipts. The 2023 matrix
inherits historical reference admission, so the result is exploratory and
cannot clear GEFS version equivalence or score 2026 rainfall.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import numpy as np

from backend.app.ml.phase2b import FEATURE_NAMES
from scripts import build_gefs_2026_forecast_corpus as corpus
from scripts import summarize_gefs_2026_forecast_year as year_summary

BASE = ROOT / "data/manifests/research_pilot"
TRAIN = ROOT / "data/operational_derived/operational_features_2023_2025_v1/2023/train/deterministic"
YEAR = BASE / "2026_forecast_jjas_year_v1.json"
V1 = BASE / "2026_feature_comparability_protocol_v1.json"
V2 = BASE / "2026_feature_comparability_protocol_v2.json"
OUT = BASE / "2026_feature_comparability_result_v1.json"
STATIC = frozenset(("latitude_deg", "longitude_deg", "lead_hours"))
MONTHS = ("06", "07", "08", "09")
LEADS = ("day1_24h", "day2_24h", "day3_24h")


def _sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def _receipt(path: Path) -> str:
    digest = _sha(path)
    if path.with_suffix(".sha256").read_text(encoding="ascii").split() != [digest, path.name]:
        raise ValueError(f"Receipt mismatch: {path.name}")
    return digest


def _protocol() -> tuple[dict, str]:
    base_sha = _receipt(V1)
    version_sha = _receipt(V2)
    base = json.loads(V1.read_text(encoding="utf-8"))
    version = json.loads(V2.read_text(encoding="utf-8"))
    if (version["base_v1_protocol_sha256"] != base_sha
            or version["status"] != "EXPLORATORY_FORECAST_FEATURE_COMPARISON_NO_VERSION_CLEARANCE_NO_PROMOTION"):
        raise ValueError("Exploratory protocol boundary changed")
    paths = {"training_X_sha256": TRAIN / "X.npy", "training_cases_sha256": TRAIN / "cases.json",
             "training_pixel_index_sha256": TRAIN / "pixel_index.npy",
             "feature_names_module_sha256": ROOT / "backend/app/ml/phase2b.py",
             "forecast_year_sha256": YEAR, "forecast_corpus_protocol_sha256": corpus.PROTOCOL}
    for key, path in paths.items():
        if _sha(path) != base["inputs"][key]:
            raise ValueError(f"Frozen comparability input changed: {key}")
    return base, version_sha


def compare_stratum(training: np.ndarray, forecast: np.ndarray, names: tuple[str, ...]) -> dict:
    """Describe all dynamic columns on a common ordered cell footprint."""
    if training.ndim != 2 or forecast.ndim != 2 or training.shape[1] != len(names) or forecast.shape[1] != len(names):
        raise ValueError("Feature layout differs")
    if not len(training) or not len(forecast) or not np.isfinite(training).all() or not np.isfinite(forecast).all():
        raise ValueError("Empty or nonfinite feature stratum")
    result = {}
    for i, name in enumerate(names):
        if name in STATIC:
            continue
        old = training[:, i]
        new = forecast[:, i]
        old_q = np.quantile(old, (0.001, 0.01, 0.5, 0.99, 0.999))
        new_q = np.quantile(new, (0.01, 0.5, 0.99))
        result[name] = {
            "training_p01": float(old_q[1]), "training_median": float(old_q[2]), "training_p99": float(old_q[3]),
            "forecast_p01": float(new_q[0]), "forecast_median": float(new_q[1]), "forecast_p99": float(new_q[2]),
            "forecast_minus_training_median": float(new_q[1] - old_q[2]),
            "forecast_fraction_outside_training_p001_p999": float(np.mean((new < old_q[0]) | (new > old_q[4]))),
        }
    return result


def summary() -> dict:
    _, protocol_sha = _protocol()
    _, corpus_sha = corpus.protocol()
    if _receipt(YEAR) != _sha(YEAR) or json.loads(YEAR.read_text(encoding="utf-8")) != year_summary.summary():
        raise ValueError("2026 forecast-year population differs from source receipts")
    anchored = json.loads((TRAIN.parent / "year_manifest.json").read_text(encoding="utf-8"))["outputs_sha256"]["deterministic"]
    if any(_sha(TRAIN / name) != anchored[key] for name, key in (("X.npy", "features"), ("cases.json", "cases"), ("pixel_index.npy", "pixel_index"))):
        raise ValueError("2023 training feature evidence changed")
    training = np.load(TRAIN / "X.npy", mmap_mode="r", allow_pickle=False)
    pixels = np.load(TRAIN / "pixel_index.npy", mmap_mode="r", allow_pickle=False)
    cases = json.loads((TRAIN / "cases.json").read_text(encoding="utf-8"))
    if (training.ndim != 2 or training.shape[1] != len(FEATURE_NAMES) or len(training) != len(pixels)
            or len(cases) != 200):
        raise ValueError("2023 training feature layout or population differs")
    fixed = np.asarray(pixels[:1301], dtype=np.int64)
    if len(np.unique(fixed)) != 1301 or fixed.min() < 0 or fixed.max() >= 2401:
        raise ValueError("2023 common footprint is invalid")
    train_groups: dict[tuple[str, str], list[np.ndarray]] = defaultdict(list)
    static_columns = [FEATURE_NAMES.index(name) for name in ("latitude_deg", "longitude_deg")]
    for case in cases:
        start, count = case["row_start"], case["row_count"]
        if count != 1301 or not np.array_equal(pixels[start:start + count], fixed):
            raise ValueError("2023 cases do not share the frozen footprint")
        if case["initialization_utc"][:4] != "2023":
            raise ValueError("Unexpected training case year")
        month = case["initialization_utc"][5:7]
        if month in MONTHS:
            train_groups[(month, case["product"])].append(np.asarray(training[start:start + count]))
    if sum(map(len, train_groups.values())) != 192:
        raise ValueError("2023 JJAS training case count changed")
    reference_static = train_groups[("06", "day1_24h")][0][:, static_columns]
    forecast_groups: dict[tuple[str, str], list[np.ndarray]] = defaultdict(list)
    for month in MONTHS:
        for cycle in corpus.dates_for_month(f"2026{month}", json.loads(corpus.PROTOCOL.read_text(encoding="utf-8"))):
            directory = corpus.CORPUS / cycle
            manifest = json.loads((directory / "manifest.json").read_text(encoding="utf-8"))
            if (manifest["cycle"] != cycle or manifest["protocol_sha256"] != corpus_sha
                    or manifest["observation_read"] is not False or manifest["model_inference"] is not False):
                raise ValueError("Forecast-side case identity changed")
            for lead in manifest["products_passing_qc"]:
                if lead not in LEADS:
                    raise ValueError("Unexpected forecast lead")
                path = directory / f"X_{lead}.npy"
                if _sha(path) != manifest["array_sha256"][path.name]:
                    raise ValueError("Forecast feature hash mismatch")
                array = np.load(path, mmap_mode="r", allow_pickle=False)
                if array.shape != (2401, len(FEATURE_NAMES)) or not np.isfinite(array).all():
                    raise ValueError("Forecast feature shape or finiteness differs")
                subset = np.asarray(array[fixed])
                if not np.array_equal(subset[:, static_columns], reference_static):
                    raise ValueError("2023/2026 latitude-longitude footprint differs")
                if not np.all(subset[:, FEATURE_NAMES.index("lead_hours")] == (LEADS.index(lead) + 1) * 24):
                    raise ValueError("Forecast lead feature differs")
                forecast_groups[(month, lead)].append(subset)
    if sum(map(len, forecast_groups.values())) != 213:
        raise ValueError("2026 strict-QC lead count changed")
    strata = {}
    for month in MONTHS:
        for lead in LEADS:
            old_cases, new_cases = train_groups[(month, lead)], forecast_groups[(month, lead)]
            if not old_cases or not new_cases:
                raise ValueError("An expected month-lead stratum lacks support")
            old, new = np.concatenate(old_cases), np.concatenate(new_cases)
            strata[f"{month}_{lead}"] = {"training_cases": len(old_cases), "forecast_cases": len(new_cases),
                                       "common_grid_cells": 1301, "training_rows": len(old), "forecast_rows": len(new),
                                       "features": compare_stratum(old, new, FEATURE_NAMES)}
    return {"schema": "varshasetu-2026-feature-comparability-result-v1",
            "status": "EXPLORATORY_FORECAST_FEATURE_COMPARISON_NO_VERSION_CLEARANCE_NO_PROMOTION",
            "protocol_v2_sha256": protocol_sha, "source_track": "B_OPERATIONAL_GEFS",
            "training_cases_jjas": 192, "forecast_cases_jjas": 213,
            "observation_values_read": False, "model_fitted": False, "rainfall_skill_computed": False,
            "strata": strata,
            "interpretation": "Historical 2023 case admission differs from forecast-only 2026 QC. Common-grid distribution descriptions are not GEFS version proof or skill."}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("write", "check"))
    args = parser.parse_args()
    report = summary()
    value = json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + "\n"
    if args.command == "write":
        with OUT.open("x", encoding="utf-8", newline="\n") as stream:
            stream.write(value)
        OUT.with_suffix(".sha256").write_text(_sha(OUT) + "  " + OUT.name + "\n", encoding="ascii")
    elif _receipt(OUT) != _sha(OUT) or json.loads(OUT.read_text(encoding="utf-8")) != report:
        raise ValueError("Sealed comparability result differs from current source population")
    print(json.dumps({"status": report["status"], "training_cases_jjas": 192, "forecast_cases_jjas": 213,
                      "strata": len(report["strata"]), "result_sha256": _sha(OUT)}, sort_keys=True))


if __name__ == "__main__":
    main()
