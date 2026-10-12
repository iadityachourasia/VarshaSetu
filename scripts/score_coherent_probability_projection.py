"""Score a sealed, deterministic nested-probability projection on consumed 2024 development data."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.app.ml.coherent_probability import project_nested_probabilities  # noqa: E402
from backend.app.ml.phase2c import reliability_bins  # noqa: E402
from experiments.recent_historical.phase4g_features_v1.finalize import verify_year  # noqa: E402
from experiments.recent_historical.phase4i_operational_model_development_v1.core import HERE, load_year, read_json, sha256  # noqa: E402

MANIFEST = ROOT / "data/manifests/research_pilot"
PROTOCOL = MANIFEST / "coherent_probability_projection_protocol_v1.json"
OUT = MANIFEST / "coherent_probability_projection_score_v1.json"


def verified_protocol() -> str:
    digest = sha256(PROTOCOL)
    sidecar = PROTOCOL.with_suffix(".sha256")
    if sidecar.read_text(encoding="ascii").split()[0] != digest:
        raise ValueError("coherent projection protocol hash mismatch")
    rule = read_json(PROTOCOL)
    if (rule["status"] != "FROZEN_BEFORE_OUTCOME_PAIRED_ANALYSIS"
            or rule["excluded_years"] != [2025, 2026]):
        raise ValueError("coherent projection protocol scope changed")
    return digest


def target_score(y: np.ndarray, p: np.ndarray) -> dict:
    if len(y) != len(p) or not len(y):
        raise ValueError("empty or unaligned probability score")
    return {"sample_count": len(y), "observed_events": int(np.sum(y)),
            "mean_probability": float(np.mean(p)),
            "brier": float(np.mean((p - y) ** 2)),
            "reliability": reliability_bins(y, p)}


def score_block(yh, yv, h, v, mask) -> dict:
    oh, ov = h[mask], v[mask]
    ph, pv = project_nested_probabilities(oh, ov)
    bad = ov > oh
    yh, yv = yh[mask], yv[mask]
    original_h, original_v = target_score(yh, oh), target_score(yv, ov)
    projected_h, projected_v = target_score(yh, ph), target_score(yv, pv)
    original_joint = original_h["brier"] + original_v["brier"]
    projected_joint = projected_h["brier"] + projected_v["brier"]
    if projected_joint > original_joint + 1e-12 or np.any(pv > ph):
        raise RuntimeError("nested projection violated its mathematical guarantee")
    return {"cases": None, "cells": len(oh), "violation_cells": int(bad.sum()),
            "violation_fraction": float(np.mean(bad)),
            "maximum_violation_gap": float(np.max(ov[bad] - oh[bad])) if bad.any() else 0.0,
            "original": {"heavy": original_h, "very_heavy": original_v, "joint_brier_sum": original_joint},
            "projected": {"heavy": projected_h, "very_heavy": projected_v, "joint_brier_sum": projected_joint}}


def main() -> None:
    protocol_sha = verified_protocol()  # must precede any observation access
    source = {}
    probabilities = {}
    for name in ("heavy", "very_heavy"):
        path = HERE / "probability_models" / name / "selected_2024_probability.npy"
        report_path = HERE / "validation" / f"probability_{name}_2024.json"
        report = read_json(report_path)
        digest = sha256(path)
        if digest != report["selected_probability_sha256"]:
            raise ValueError(f"frozen {name} probability hash mismatch")
        probabilities[name] = np.load(path, allow_pickle=False)
        source[f"{name}_probability_sha256"] = digest
        source[f"{name}_report_sha256"] = sha256(report_path)
    split_path = HERE / "calibration/split_2024.json"
    source["split_sha256"] = sha256(split_path)
    if source["split_sha256"] != read_json(HERE / "validation/probability_heavy_2024.json")["calibration_split_sha256"]:
        raise ValueError("frozen development split hash mismatch")
    verify_year(2024)
    year = load_year(2024)
    source["year_manifest_sha256"] = sha256(ROOT / "data/operational_derived/operational_features_2023_2025_v1/2024/validation/year_manifest.json")
    h, v = probabilities["heavy"], probabilities["very_heavy"]
    if h.shape != year.heavy.shape or v.shape != year.very_heavy.shape or np.any(year.very_heavy > year.heavy):
        raise ValueError("2024 probability/label alignment or nesting differs")
    split = read_json(split_path)
    blocks = {"all_2024": np.ones(len(h), dtype=bool)}
    for name, key in (("calibration", "calibration_case_ids"), ("purged", "purged_case_ids"),
                      ("selection", "selection_case_ids")):
        blocks[name] = year.row_mask(split[key])
    if not np.array_equal(blocks["calibration"] | blocks["purged"] | blocks["selection"], blocks["all_2024"]):
        raise ValueError("2024 development split does not partition rows")
    scores = {}
    for name, mask in blocks.items():
        scores[name] = score_block(year.heavy, year.very_heavy, h, v, mask)
        scores[name]["cases"] = len(year.cases) if name == "all_2024" else split[f"{name}_case_count"]
    result = {"schema": "varshasetu-coherent-probability-projection-score-v1", "protocol_sha256": protocol_sha,
              "source": source, "year": 2024, "role": "consumed_development_diagnostic_not_independent_validation",
              "method": "symmetric_euclidean_projection_no_refit", "blocks": scores,
              "decision": "research diagnostic only; no calibrated or operational promotion without a separately frozen independent-year reliability test"}
    payload = json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n"
    if OUT.exists():
        if OUT.read_text(encoding="utf-8") != payload or OUT.with_suffix(".sha256").read_text(encoding="ascii").split()[0] != sha256(OUT):
            raise ValueError("immutable coherent projection score differs")
    else:
        with OUT.open("x", encoding="utf-8", newline="\n") as stream:
            stream.write(payload)
        OUT.with_suffix(".sha256").write_text(hashlib.sha256(payload.encode()).hexdigest() + "  " + OUT.name + "\n", encoding="ascii")
    print(json.dumps({name: {key: block[key] for key in ("cells", "violation_cells", "violation_fraction", "maximum_violation_gap")}
                      | {"original_joint_brier_sum": block["original"]["joint_brier_sum"],
                         "projected_joint_brier_sum": block["projected"]["joint_brier_sum"]}
                      for name, block in scores.items()}))


if __name__ == "__main__":
    main()
