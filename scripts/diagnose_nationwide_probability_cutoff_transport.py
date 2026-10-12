"""Read-only forecast-score audit of the failed nationwide v2 warning cutoff.

This recomputes 2024 head scores from sealed forecast-only features and the
sealed 2023-fit model. It never loads annual IMD reference or refits a model.
The 2024 year is already a consumed development diagnostic, not an independent
validation population. Commands: write, check.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.app.ml.nationwide_research import coherent_probabilities  # noqa: E402
from scripts import nationwide_probability_v2 as v2  # noqa: E402
from scripts import nationwide_research as national  # noqa: E402

BASE = ROOT / "data/manifests/research_pilot"
PROTOCOL = BASE / "nationwide_probability_cutoff_transport_protocol_v1.json"
RESULT = BASE / "nationwide_probability_cutoff_transport_result_v1.json"
HEADS = ("heavy", "very_heavy")
STAGES = ("raw_head", "lead_calibrated", "coherent_saved")
LEADS = (24, 48, 72)


def _protocol() -> dict:
    if national.receipt(PROTOCOL) != national.sha(PROTOCOL):
        raise ValueError("cutoff diagnostic protocol receipt mismatch")
    protocol = json.loads(PROTOCOL.read_text(encoding="utf-8"))
    expected = {
        "v2_probability_protocol_sha256": national.sha(v2.PROTOCOL),
        "v2_fit_seal_sha256": national.sha(v2.SEAL),
        "forecast_feature_manifest_sha256": national.sha(national.FEATURES),
        "v2_model_sha256": national.sha(v2.OUT / "models.json"),
        "diagnostic_code_sha256": national.sha(Path(__file__)),
    }
    if (protocol.get("status") != "FROZEN_FORECAST_ONLY_CUTOFF_DIAGNOSTIC"
            or any(protocol.get(key) != digest for key, digest in expected.items())):
        raise ValueError("cutoff diagnostic source or code changed")
    return protocol


def stage_counts(values: np.ndarray, cutoff: float) -> dict:
    """Count warnings at one explicitly named probability processing stage."""
    values = np.asarray(values, dtype=np.float64)
    if (values.ndim != 1 or not len(values) or not np.isfinite(values).all()
            or np.any((values < 0) | (values > 1)) or not 0 < cutoff <= 1):
        raise ValueError("invalid probability stage or cutoff")
    return {"cells": int(len(values)), "maximum": float(values.max()),
            "mean": float(values.mean()), "warnings": int(np.count_nonzero(values >= cutoff))}


def _summary() -> dict:
    _protocol()
    _, fit = v2._sealed()  # verifies every saved prediction hash
    _, features, _ = national._feature_manifest()  # verifies every feature hash
    by_case = {row["case_id"]: row for row in features["cases"] if row["year"] == 2024}
    if (len(fit["predictions"]) != 156
            or set(by_case) != {row["case_id"] for row in fit["predictions"]}):
        raise ValueError("2024 forecast-only case population changed")
    models = json.loads((v2.OUT / "models.json").read_text(encoding="utf-8"))
    cutoffs = {name: float(models[name]["warning_cutoff_calibrated_coherent_2023_oof"])
               for name in HEADS}
    accum = {name: {str(lead): {stage: {"cases": 0, "cells": 0, "maximum": 0.0,
                                          "sum": 0.0, "warnings": 0, "cases_with_warnings": 0}
                                for stage in STAGES} for lead in LEADS} for name in HEADS}
    for row in fit["predictions"]:
        lead = int(row["hour"])
        if lead not in LEADS:
            raise ValueError("unexpected lead")
        x, _ = national._load_x(by_case[row["case_id"]])
        if len(x) != row["cells"]:
            raise ValueError("forecast feature and prediction cell counts differ")
        raw = {name: national._scale_predict(models[name]["head"], x) for name in HEADS}
        calibrated = {name: v2.apply_lead_calibration(raw[name], x[:, -1],
                                                       models[name]["calibrators"])
                      for name in HEADS}
        coherent = dict(zip(HEADS, coherent_probabilities(
            calibrated["heavy"], calibrated["very_heavy"])))
        with np.load(ROOT / row["file"], allow_pickle=False) as saved:
            for name in HEADS:
                if not np.array_equal(saved[name + "_p"], coherent[name].astype(np.float32)):
                    raise ValueError(f"saved v2 probability differs from recomputation: {row['case_id']}, {name}")
                for stage, values in (("raw_head", raw[name]),
                                      ("lead_calibrated", calibrated[name]),
                                      ("coherent_saved", saved[name + "_p"])):
                    stats = stage_counts(values, cutoffs[name])
                    current = accum[name][str(lead)][stage]
                    current["cases"] += 1
                    current["cells"] += stats["cells"]
                    current["maximum"] = max(current["maximum"], stats["maximum"])
                    current["sum"] += stats["mean"] * stats["cells"]
                    current["warnings"] += stats["warnings"]
                    current["cases_with_warnings"] += int(stats["warnings"] > 0)
    for heads in accum.values():
        for leads in heads.values():
            for block in leads.values():
                block["mean"] = block.pop("sum") / block["cells"]
    return {
        "schema": "nationwide-probability-cutoff-transport-diagnostic-v1",
        "status": "CONSUMED_2024_FORECAST_ONLY_DIAGNOSTIC_NO_MODEL_CHANGE",
        "protocol_sha256": national.sha(PROTOCOL),
        "v2_fit_seal_sha256": national.sha(v2.SEAL),
        "cutoff_origin": "2023 calibrated/coherent out-of-fold frequency selection",
        "cutoffs": cutoffs,
        "counts_by_head_lead_and_stage": accum,
        "reference_values_read_by_diagnostic": False,
        "2025_2026_values_read_by_diagnostic": False,
        "model_refitted": False,
        "warning_threshold_changed": False,
        "product_default_unchanged": "regional_M2",
        "independent_reliability_claim": False,
        "public_warning_allowed": False,
    }


def write() -> dict:
    if RESULT.exists() or RESULT.with_suffix(".sha256").exists():
        raise FileExistsError("cutoff diagnostic result is write-once")
    result = _summary()
    digest = national.write_json(RESULT, result)
    return {"status": result["status"], "result_sha256": digest}


def check() -> dict:
    stored = json.loads(RESULT.read_text(encoding="utf-8"))
    if national.receipt(RESULT) != national.sha(RESULT) or stored != _summary():
        raise ValueError("cutoff diagnostic does not reproduce")
    return {"status": "CUTOFF_DIAGNOSTIC_REPRODUCED", "result_sha256": national.sha(RESULT)}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("write", "check"))
    args = parser.parse_args()
    print(json.dumps({"write": write, "check": check}[args.command](), sort_keys=True))


if __name__ == "__main__":
    main()
