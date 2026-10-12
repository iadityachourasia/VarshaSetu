"""Seal a development-only ordinal probability fit before selection scoring.

Usage: python scripts/experiment_extreme_ordinal_fit.py --source-root C:/SIH26/Varsha-NXT
The source checkout is read-only; only extreme_* manifest paths here are written.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.app.ml.extreme_ordinal_probability import fit_ordinal, predict_ordinal  # noqa: E402

OUT = ROOT / "data/manifests/research_pilot"
PROTOCOL = OUT / "extreme_ordinal_probability_protocol_v1.json"
PREDICTIONS = OUT / "extreme_ordinal_probability_prediction_v1.npz"
SEAL = OUT / "extreme_ordinal_probability_prediction_seal_v1.json"
COUNT = 238083
PHASE4I = Path("experiments/recent_historical/phase4i_operational_model_development_v1")
YEAR = Path("data/operational_derived/operational_features_2023_2025_v1/2024/validation")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def checked(path: Path) -> tuple[dict, str]:
    actual = sha256(path)
    expected = path.with_suffix(".sha256").read_text(encoding="ascii").split()[0]
    if actual != expected:
        raise ValueError(f"SHA-256 sidecar mismatch: {path}")
    return json.loads(path.read_text(encoding="utf-8")), actual


def write_once_json(path: Path, value: dict) -> str:
    payload = (json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n").encode()
    digest = hashlib.sha256(payload).hexdigest()
    if path.exists():
        if path.read_bytes() != payload or checked(path)[1] != digest:
            raise ValueError(f"sealed artifact differs: {path}")
    else:
        with path.open("xb") as stream:
            stream.write(payload)
        path.with_suffix(".sha256").write_text(f"{digest}  {path.name}\n", encoding="ascii")
    return digest


def inputs(source_root: Path) -> dict:
    rule, protocol_sha = checked(PROTOCOL)
    if (rule.get("status") != "PRESPECIFIED_BEFORE_ORDINAL_FIT_OR_SELECTION_SCORE"
            or rule.get("excluded_years") != [2025, 2026]):
        raise ValueError("ordinal protocol role differs")
    base = source_root / PHASE4I
    year_dir = source_root / YEAR
    split_path = base / "calibration/split_2024.json"
    cases_path = year_dir / "deterministic/cases.json"
    year_path = year_dir / "year_manifest.json"
    split, cases, year = (json.loads(p.read_text(encoding="utf-8"))
                          for p in (split_path, cases_path, year_path))
    if (len(cases) != 183 or sum(int(case["row_count"]) for case in cases) != COUNT
            or sha256(cases_path) != year["outputs_sha256"]["deterministic"]["cases"]
            or [split[f"{name}_case_count"] for name in ("calibration", "purged", "selection")] != [108, 7, 68]):
        raise ValueError("Phase 4I development population differs")
    membership = {name: set(split[f"{name}_case_ids"])
                  for name in ("calibration", "purged", "selection")}
    masks = {name: np.zeros(COUNT, dtype=bool) for name in membership}
    for index, case in enumerate(cases):
        start, size = int(case["row_start"]), int(case["row_count"])
        if start != index * 1301 or size != 1301 or case["lead_hours"] not in (24, 48, 72):
            raise ValueError("case row/lead alignment differs")
        found = [name for name, members in membership.items() if case["case_id"] in members]
        if len(found) != 1:
            raise ValueError("split case missing or duplicated")
        masks[found[0]][start:start + size] = True
    if any(int(mask.sum()) != split[f"{name}_case_count"] * 1301
           for name, mask in masks.items()):
        raise ValueError("split row count differs")
    raw, labels, source_hashes = {}, {}, {}
    for target in ("heavy", "very_heavy"):
        report_path = base / f"validation/probability_{target}_2024.json"
        report = json.loads(report_path.read_text(encoding="utf-8"))
        if report["calibration_split_sha256"] != sha256(split_path):
            raise ValueError("probability model split differs")
        selected = report["selected_base_model_id"]
        candidate = next(row for row in report["candidate_models"] if row["id"] == selected)
        raw_path = base / f"probability_models/{target}/{selected}_2024.npy"
        label_path = year_dir / f"deterministic/{target}_label.npy"
        if (sha256(raw_path) != candidate["prediction_sha256"]
                or sha256(label_path) != year["outputs_sha256"]["deterministic"][f"{target}_label"]):
            raise ValueError("base probability or label hash differs")
        raw[target] = np.load(raw_path, mmap_mode="r", allow_pickle=False)
        labels[target] = np.load(label_path, mmap_mode="r", allow_pickle=False)
        if raw[target].shape != (COUNT,) or labels[target].shape != (COUNT,):
            raise ValueError("base probability or label shape differs")
        source_hashes[target] = {"base_probability_sha256": sha256(raw_path),
                                 "label_sha256": sha256(label_path),
                                 "selection_report_sha256": sha256(report_path)}
    prior_path = source_root / "data/processed/lead_aware_probability_v1"
    prior_manifest_path = prior_path / "manifest.json"
    prior_manifest = json.loads(prior_manifest_path.read_text(encoding="utf-8"))
    prior_seal_path = OUT / "lead_aware_probability_prediction_seal_v1.json"
    prior_seal, prior_seal_sha = checked(prior_seal_path)
    if (sha256(prior_manifest_path) != prior_path.joinpath("manifest.sha256").read_text(encoding="ascii").split()[0]
            or sha256(prior_path / "predictions.npz") != prior_manifest["prediction_archive_sha256"]
            or prior_seal["fit_manifest_sha256"] != sha256(prior_manifest_path)
            or prior_seal["prediction_archive_sha256"] != prior_manifest["prediction_archive_sha256"]):
        raise ValueError("prior pooled/frozen control seal differs")
    source_hashes.update({"split_sha256": sha256(split_path), "cases_sha256": sha256(cases_path),
                          "year_manifest_sha256": sha256(year_path),
                          "prior_prediction_seal_sha256": prior_seal_sha,
                          "prior_fit_manifest_sha256": sha256(prior_manifest_path),
                          "prior_prediction_sha256": prior_manifest["prediction_archive_sha256"]})
    return {"rule": rule, "protocol_sha256": protocol_sha, "cases": cases,
            "masks": masks, "raw": raw, "labels": labels,
            "source_hashes": source_hashes, "prior_path": prior_path}


def fit_and_seal(source_root: Path) -> dict:
    data = inputs(source_root)
    if PREDICTIONS.exists() or SEAL.exists():
        raise ValueError("ordinal prediction seal exists; no refit or overwrite")
    early = data["masks"]["calibration"]
    yh = np.asarray(data["labels"]["heavy"][early], dtype=np.uint8)
    yv = np.asarray(data["labels"]["very_heavy"][early], dtype=np.uint8)
    event_cases = 0
    for case in data["cases"]:
        if early[int(case["row_start"])]:
            sl = slice(int(case["row_start"]), int(case["row_start"]) + 1301)
            event_cases += int(np.asarray(data["labels"]["very_heavy"][sl]).sum() > 0)
    if int(yv.sum()) < 100 or event_cases < 20:
        raise ValueError("very-heavy early-block event support gate failed")
    model = fit_ordinal(data["raw"]["heavy"][early], data["raw"]["very_heavy"][early], yh, yv)
    model["fit_block"] = "2024_early_calibration_only"
    h, v = predict_ordinal(data["raw"]["heavy"], data["raw"]["very_heavy"], model)
    with np.load(data["prior_path"] / "predictions.npz", allow_pickle=False) as prior:
        arrays = {"ordinal_heavy": h, "ordinal_very_heavy": v}
        for arm in ("frozen", "global"):
            for target in ("heavy", "very_heavy"):
                arrays[f"{arm}_{target}"] = prior[f"{arm}_{target}"]
    for arm in ("ordinal", "frozen", "global"):
        ph, pv = arrays[f"{arm}_heavy"], arrays[f"{arm}_very_heavy"]
        if (ph.shape != (COUNT,) or pv.shape != ph.shape or not np.isfinite(ph).all()
                or not np.isfinite(pv).all() or np.any((ph < 0) | (ph > 1))
                or np.any((pv < 0) | (pv > ph))):
            raise ValueError("prediction array is nonfinite, out of bounds, or incoherent")
    with PREDICTIONS.open("xb") as stream:
        np.savez_compressed(stream, **arrays)
    seal = {"schema": "varshasetu-extreme-ordinal-prediction-seal-v1",
            "protocol_sha256": data["protocol_sha256"],
            "source_hashes": data["source_hashes"], "model": model,
            "prediction_archive_sha256": sha256(PREDICTIONS),
            "calibration_positive_cells": {"heavy": int(yh.sum()), "very_heavy": int(yv.sum())},
            "calibration_very_heavy_event_cases": event_cases,
            "selection_labels_decoded": False,
            "role": "consumed_2024_development_only_no_promotion"}
    write_once_json(SEAL, seal)
    return seal


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, required=True)
    args = parser.parse_args()
    result = fit_and_seal(args.source_root.resolve())
    print(json.dumps({"prediction_sha256": result["prediction_archive_sha256"],
                      "calibration_positive_cells": result["calibration_positive_cells"]}, sort_keys=True))
