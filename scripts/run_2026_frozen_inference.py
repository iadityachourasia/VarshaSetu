"""Seal frozen Track B forecasts on the 2026 JJAS forecast-only corpus.

No observation, fitting, threshold choice, scoring or live publication occurs.
Research-only probability-order failures are recorded, never repaired here.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
import time
from collections import Counter
from pathlib import Path
from uuid import uuid4

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.app.live.pipeline import FrozenModels, LEADS  # noqa: E402
from scripts.build_gefs_2026_forecast_corpus import CORPUS, verify_case  # noqa: E402

BASE = ROOT / "data/manifests/research_pilot"
PROTOCOL = BASE / "2026_frozen_inference_protocol_v1.json"
YEAR = BASE / "2026_frozen_inference_year_v1.json"
OUT = ROOT / "data/processed/gefs_2026_frozen_inference_v1"
FREEZE = ROOT / "experiments/recent_historical/phase4i_operational_model_development_v1/final_freeze"
MONTHS = ("202606", "202607", "202608", "202609")
RAIN = ("M0", "M1", "M2", "M3", "M4")
PROB = ("heavy_probability", "very_heavy_probability")
ARRAYS = (*RAIN, *PROB, "regime_probability")


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def sealed(path: Path) -> dict:
    if not path.is_file() or not path.with_suffix(".sha256").is_file() or path.with_suffix(".sha256").read_text(encoding="ascii").split()[0] != sha(path):
        raise ValueError(f"sealed file missing or changed: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def protocol() -> tuple[dict, str]:
    value = sealed(PROTOCOL)
    expected = {"source_year_sha256": sha(BASE / "2026_forecast_jjas_year_v1.json"),
                "evaluation_protocol_sha256": sha(BASE / "2026_track_b_evaluation_protocol_v1.json"),
                "model_readiness_sha256": sha(FREEZE / "FINAL_TEST_READY.json"),
                "model_selection_sha256": sha(FREEZE / "model_selection_freeze.json"),
                "runner_sha256": sha(Path(__file__))}
    if any(value[k] != v for k, v in expected.items()) or value["observation_read"] is not False or value["model_training"] is not False:
        raise ValueError("frozen inference protocol/source/model hash mismatch")
    year = sealed(BASE / "2026_forecast_jjas_year_v1.json")
    if year["cycle_count"] != 122 or year["observation_read"] is not False:
        raise ValueError("2026 source year is not forecast-only and complete")
    if value["source_version_status"] != "ACTUAL_2026_SWITCHOVER_AND_2023_EQUIVALENCE_UNPROVEN":
        raise ValueError("version caveat missing")
    return value, sha(PROTOCOL)


def validate_outputs(output: dict, X: np.ndarray) -> int:
    if set(output) != set(ARRAYS) or X.shape != (2401, 22):
        raise ValueError("unexpected frozen model outputs or input shape")
    for name in RAIN:
        values = np.asarray(output[name])
        if values.shape != (2401,) or not np.isfinite(values).all() or np.any(values < 0):
            raise ValueError(f"invalid nonnegative rainfall field: {name}")
    if not np.array_equal(output["M0"], X[:, 0]):
        raise ValueError("Raw output differs from the sealed forecast input")
    for name in PROB:
        values = np.asarray(output[name])
        if values.shape != (2401,) or not np.isfinite(values).all() or np.any((values < 0) | (values > 1)):
            raise ValueError(f"invalid frozen probability field: {name}")
    regime = np.asarray(output["regime_probability"])
    if regime.shape != (3,) or not np.isfinite(regime).all() or np.any((regime < 0) | (regime > 1)) or not np.isclose(regime.sum(), 1.0, atol=1e-8):
        raise ValueError("invalid frozen regime class output")
    return int(np.count_nonzero(output["very_heavy_probability"] > output["heavy_probability"] + 1e-12))


def verify_output(directory: Path, source_sha: str, protocol_sha: str, model_hashes: dict) -> dict:
    path = directory / "manifest.json"
    if not path.is_file() or not (directory / "manifest.sha256").is_file() or (directory / "manifest.sha256").read_text(encoding="ascii").split()[0] != sha(path):
        raise ValueError(f"inference manifest integrity failure: {directory}")
    manifest = json.loads(path.read_text(encoding="utf-8"))
    if (manifest["cycle"] != directory.name or manifest["source_manifest_sha256"] != source_sha or
            manifest["protocol_sha256"] != protocol_sha or manifest["model_artifact_sha256"] != model_hashes or
            manifest["observation_read"] is not False or manifest["model_training"] is not False):
        raise ValueError(f"inference lineage mismatch: {directory}")
    for product, block in manifest["products"].items():
        if product not in LEADS or sha(directory / f"{product}.npz") != block["array_sha256"]:
            raise ValueError(f"inference array integrity failure: {directory}/{product}")
        with np.load(directory / f"{product}.npz", allow_pickle=False) as saved:
            data = {name: saved[name] for name in saved.files}
        if set(data) != set(ARRAYS):
            raise ValueError(f"inference arrays missing: {directory}/{product}")
        if any(not np.isfinite(data[name]).all() for name in ARRAYS):
            raise ValueError(f"nonfinite inference array: {directory}/{product}")
        if int(np.count_nonzero(data["very_heavy_probability"] > data["heavy_probability"] + 1e-12)) != block["nested_probability_violating_cells"]:
            raise ValueError(f"probability-order metadata differs: {directory}/{product}")
    return manifest


def publish_case(cycle: str, source: dict, source_sha: str, model: FrozenModels, protocol_sha: str) -> dict:
    target = OUT / cycle
    if target.exists():
        return verify_output(target, source_sha, protocol_sha, model.hashes)
    OUT.mkdir(parents=True, exist_ok=True)
    if shutil.disk_usage(OUT).free < 50 * 1024**3:
        raise ValueError("50 GiB free-space guard failed")
    stage = OUT / f".stage-{cycle}-{uuid4().hex}"
    stage.mkdir()
    try:
        products = {}
        for product in source["products_passing_qc"]:
            X = np.load(CORPUS / cycle / f"X_{product}.npy", allow_pickle=False)
            regime = np.load(CORPUS / cycle / f"regime_{product}.npy", allow_pickle=False)
            raw = model._apply_unchecked(X, regime)
            violation_count = validate_outputs(raw, X)
            path = stage / f"{product}.npz"
            np.savez_compressed(path, **{name: np.asarray(raw[name]) for name in ARRAYS})
            products[product] = {"array_sha256": sha(path), "cells": 2401,
                                 "nested_probability_violating_cells": violation_count,
                                 "probability_status": "COHERENT_FROZEN_OUTPUT_UNVERIFIED_2026_RELIABILITY" if violation_count == 0 else "INCOHERENT_RESEARCH_ONLY_NO_WARNING_USE"}
        record = {"schema": "varshasetu-2026-frozen-inference-case-v1", "cycle": cycle,
                  "protocol_sha256": protocol_sha, "source_manifest_sha256": source_sha,
                  "model_artifact_sha256": model.hashes, "products": products,
                  "source_strict_qc_passing": source["products_passing_qc"], "source_withheld": source["withheld_products"],
                  "source_version_status": "ACTUAL_2026_SWITCHOVER_AND_2023_EQUIVALENCE_UNPROVEN",
                  "observation_read": False, "model_training": False, "skill_scored": False,
                  "live_publication": False}
        value = json.dumps(record, indent=2, sort_keys=True, allow_nan=False) + "\n"
        (stage / "manifest.json").write_text(value, encoding="utf-8", newline="\n")
        (stage / "manifest.sha256").write_text(hashlib.sha256(value.encode("utf-8")).hexdigest() + "\n", encoding="ascii")
        for attempt in range(5):
            if target.exists():
                raise FileExistsError(f"immutable inference already exists: {target}")
            try:
                stage.rename(target)
                break
            except PermissionError as error:
                if getattr(error, "winerror", None) != 5 or attempt == 4:
                    raise
                time.sleep(0.05 * 2**attempt)
        return record
    except Exception:
        shutil.rmtree(stage)
        raise


def cases_by_month(month: str) -> list[dict]:
    report = sealed(BASE / f"2026_forecast_month_{month}_v1.json")
    year = sealed(BASE / "2026_forecast_jjas_year_v1.json")
    linked = next(r for r in year["months"] if r["month"] == month)
    if sha(BASE / f"2026_forecast_month_{month}_v1.json") != linked["manifest_sha256"]:
        raise ValueError(f"month/year source seal mismatch: {month}")
    return report["cases"]


def run_month(month: str) -> None:
    _, protocol_sha = protocol()
    model = FrozenModels.load()
    cases = cases_by_month(month)
    for i, case in enumerate(cases, 1):
        cycle = case["cycle"]
        source = verify_case(CORPUS / cycle, sha(BASE / "2026_forecast_corpus_protocol_v1.json"))
        if sha(CORPUS / cycle / "manifest.json") != case["manifest_sha256"]:
            raise ValueError(f"source differs from month seal: {cycle}")
        out = publish_case(cycle, source, case["manifest_sha256"], model, protocol_sha)
        print(json.dumps({"progress": f"{i}/{len(cases)}", "cycle": cycle, "products": len(out["products"]),
                          "nested_violating_cells": sum(p["nested_probability_violating_cells"] for p in out["products"].values())}), flush=True)


def seal_year() -> dict:
    _, protocol_sha = protocol()
    model = FrozenModels.load()
    counts = Counter()
    violations = Counter()
    case_hashes = {}
    for month in MONTHS:
        for case in cases_by_month(month):
            cycle = case["cycle"]
            source = verify_case(CORPUS / cycle, sha(BASE / "2026_forecast_corpus_protocol_v1.json"))
            if sha(CORPUS / cycle / "manifest.json") != case["manifest_sha256"]:
                raise ValueError(f"source differs from month seal: {cycle}")
            output_path = OUT / cycle / "manifest.json"
            result = verify_output(OUT / cycle, case["manifest_sha256"], protocol_sha, model.hashes)
            if set(result["products"]) != set(source["products_passing_qc"]):
                raise ValueError(f"inference/source lead mismatch: {cycle}")
            case_hashes[cycle] = sha(output_path)
            for lead, item in result["products"].items():
                counts[lead] += 1
                violations[lead] += item["nested_probability_violating_cells"]
                if item["nested_probability_violating_cells"]:
                    violations[f"{lead}_cases"] += 1
    year_source = sealed(BASE / "2026_forecast_jjas_year_v1.json")
    if len(case_hashes) != 122 or any(counts[lead] != year_source["products_passing_qc"][lead] for lead in LEADS):
        raise ValueError("inference year does not match the sealed forecast population")
    report = {"schema": "varshasetu-2026-frozen-inference-year-v1", "status": "FORECASTS_SEALED_NO_OBSERVATION_PAIRING",
              "protocol_sha256": protocol_sha, "source_year_sha256": sha(BASE / "2026_forecast_jjas_year_v1.json"),
              "model_artifact_sha256": model.hashes, "cycle_count": len(case_hashes),
              "strict_qc_inferred_leads": {lead: counts[lead] for lead in LEADS},
              "nested_probability_violating_cells": {lead: violations[lead] for lead in LEADS},
              "nested_probability_violating_cases": {lead: violations[f"{lead}_cases"] for lead in LEADS},
              "case_manifest_sha256": case_hashes, "observation_read": False,
              "model_training": False, "skill_scored": False, "live_publication": False,
              "interpretation": "Frozen predictions only. Probability-order failures remain research-only; no 2026 skill, reliability, warning or model promotion is established."}
    value = json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + "\n"
    if YEAR.exists():
        if YEAR.read_text(encoding="utf-8") != value or sealed(YEAR) != report:
            raise ValueError("existing inference year differs: write-once")
    else:
        with YEAR.open("x", encoding="utf-8", newline="\n") as stream:
            stream.write(value)
        YEAR.with_suffix(".sha256").write_text(f"{sha(YEAR)}  {YEAR.name}\n", encoding="ascii")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--month", choices=MONTHS)
    group.add_argument("--seal-year", action="store_true")
    args = parser.parse_args()
    if args.month:
        run_month(args.month)
    else:
        report = seal_year()
        print(json.dumps({"sha256": sha(YEAR), "cycle_count": report["cycle_count"],
                          "inferred_leads": report["strict_qc_inferred_leads"],
                          "nested_probability_violating_cases": report["nested_probability_violating_cases"]}, sort_keys=True))


if __name__ == "__main__":
    main()
