"""One-shot provisional 2026 score against separately acquired IMD daily grids.

This is a source-sensitivity analysis performed only after the frozen annual
NetCDF test. It cannot replace that primary test or authorize promotion.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date, timedelta
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from backend.app.ml.track_b_2026_scoring import MODELS, score_cases  # noqa: E402
from scripts.acquire_imd_realtime_2026 import END, EXPECTED_BYTES, FINAL as ACQUISITION, RAW, START  # noqa: E402
from scripts.run_2026_frozen_inference import OUT as FORECASTS, sealed, sha, verify_output  # noqa: E402
from scripts.score_2026_frozen_inference import FORECAST_YEAR, LEAD_DAYS, SELECTION  # noqa: E402
from scripts.summarize_gefs_version_partition import partition  # noqa: E402

BASE = ROOT / "data/manifests/research_pilot"
PROTOCOL = BASE / "2026_imd_realtime_sensitivity_protocol_v1.json"
RESULT = BASE / "2026_imd_realtime_sensitivity_v1.json"
PRIMARY_RESULT = BASE / "2026_track_b_score_v1.json"


def preflight() -> dict:
    reasons = []
    try:
        rule = sealed(PROTOCOL)
        if (rule["status"] != "FROZEN_BEFORE_2026_DAILY_VALUE_DECODING_AND_PAIRING"
                or rule["scorer_sha256"] != sha(Path(__file__)) or rule["forecast_year_sha256"] != sha(FORECAST_YEAR)
                or rule["pure_scoring_sha256"] != sha(ROOT / "backend/app/ml/track_b_2026_scoring.py")
                or rule["selection_sha256"] != sha(SELECTION)):
            reasons.append("SENSITIVITY_PROTOCOL_OR_INPUT_HASH_CHANGED")
    except (OSError, KeyError, ValueError):
        reasons.append("SENSITIVITY_PROTOCOL_MISSING_OR_CHANGED")
    try:
        year = sealed(FORECAST_YEAR)
        if year["cycle_count"] != 122 or sum(year["strict_qc_inferred_leads"].values()) != 213 or year["observation_read"] is not False:
            reasons.append("FORECAST_YEAR_SEAL_INCOMPLETE")
    except (OSError, KeyError, ValueError):
        reasons.append("FORECAST_YEAR_SEAL_MISSING_OR_CHANGED")
    try:
        source = sealed(ACQUISITION)
        if source["status"] != "COMPLETE_UNSCORED_CANDIDATE" or source["received_dates"] != 125 or source["errors"] or source["observation_values_decoded"] is not False or source["forecast_observation_pairing"] is not False:
            reasons.append("REALTIME_SOURCE_INCOMPLETE_OR_ALREADY_USED")
        if rule["acquisition_sha256"] != sha(ACQUISITION):
            reasons.append("REALTIME_SOURCE_MANIFEST_CHANGED")
    except (OSError, KeyError, ValueError, UnboundLocalError):
        reasons.append("REALTIME_SOURCE_MANIFEST_MISSING_OR_CHANGED")
    try:
        primary = sealed(PRIMARY_RESULT)
        if primary["status"] != "SCORED_ONCE_NO_AUTOMATIC_PROMOTION" or primary["forecast_year_sha256"] != sha(FORECAST_YEAR):
            reasons.append("PRIMARY_ANNUAL_SCORE_INVALID")
    except (OSError, KeyError, ValueError):
        reasons.append("PRIMARY_ANNUAL_SCORE_REQUIRED_FIRST")
    return {"status": "READY_FOR_SECONDARY_PAIRING" if not reasons else "BLOCKED_BEFORE_VALUE_DECODING",
            "reasons": reasons, "reference_role": "PROVISIONAL_IMD_REALTIME_DAILY_NOT_ANNUAL_RF25",
            "observation_values_decoded": False}


def load_day(valid: date, record: dict, root: Path = ROOT) -> tuple[np.ndarray, np.ndarray]:
    if not START <= valid <= END or record["date"] != valid.isoformat() or record["byte_size"] != EXPECTED_BYTES:
        raise ValueError(f"daily identity or byte count invalid: {valid}")
    expected_relative = f"data/raw/observations/imd_realtime_2026_v1/rainfall_{valid:%Y%m%d}.grd"
    if record["local_path"] != expected_relative:
        raise ValueError(f"daily path differs from frozen layout: {valid}")
    path = root / expected_relative
    receipt = path.parent / "receipts" / f"{valid:%Y%m%d}.json"
    if json.loads(receipt.read_text(encoding="utf-8")) != record or path.stat().st_size != EXPECTED_BYTES or sha(path) != record["sha256"]:
        raise ValueError(f"daily receipt or bytes changed: {valid}")
    grid = np.fromfile(path, dtype="<f4").reshape(129, 135)
    field = grid[14:63, 6:55].astype(np.float64, copy=True)
    mask = np.isfinite(field) & (field >= 0) & (field <= 10000)
    if not mask.any():
        raise ValueError(f"no valid IMD real-time cells: {valid}")
    return field, mask


def score_once() -> dict:
    gate = preflight()
    if gate["status"] != "READY_FOR_SECONDARY_PAIRING":
        raise RuntimeError("provisional scoring blocked before value decoding: " + ", ".join(gate["reasons"]))
    if RESULT.exists():
        raise FileExistsError("provisional score already exists: one-shot")
    year = sealed(FORECAST_YEAR)
    acquisition = sealed(ACQUISITION)
    rule = sealed(PROTOCOL)
    selection = json.loads(SELECTION.read_text(encoding="utf-8"))
    records = acquisition["records"]
    days = [START + timedelta(days=i) for i in range((END - START).days + 1)]
    if sorted(records) != [day.isoformat() for day in days]:
        raise ValueError("daily source manifest does not cover every required date")
    observations = {day: load_day(day, records[day.isoformat()]) for day in days}
    cases = []
    for cycle in sorted(year["case_manifest_sha256"]):
        folder = FORECASTS / cycle
        manifest = verify_output(folder, sha(ROOT / "data/processed/gefs_2026_forecast_only_v1" / cycle / "manifest.json"),
                                 year["protocol_sha256"], year["model_artifact_sha256"])
        if sha(folder / "manifest.json") != year["case_manifest_sha256"][cycle]:
            raise ValueError(f"forecast manifest changed: {cycle}")
        for lead, metadata in sorted(manifest["products"].items()):
            valid = date.fromisoformat(f"{cycle[:4]}-{cycle[4:6]}-{cycle[6:8]}") + timedelta(days=LEAD_DAYS[lead])
            observed, mask = observations[valid]
            with np.load(folder / f"{lead}.npz", allow_pickle=False) as saved:
                arrays = {name: saved[name].reshape(49, 49) if name != "regime_probability" else saved[name].copy() for name in saved.files}
            cases.append({"cycle": cycle, "lead": lead, "version_stratum": partition(cycle, "2026-06-15T12:00:00Z"),
                          "observed": observed, "valid_mask": mask, "rainfall": {name: arrays[name] for name in MODELS},
                          "heavy_probability": arrays["heavy_probability"], "very_heavy_probability": arrays["very_heavy_probability"],
                          "regime_probability": arrays["regime_probability"],
                          "nested_probability_violating_cells": metadata["nested_probability_violating_cells"]})
    if len(cases) != 213:
        raise ValueError("paired population differs from frozen 213 leads")
    metrics = score_cases(cases,
                          climatology={name: selection[name]["bss_reference_2023"] for name in ("heavy", "very_heavy")},
                          probability_cutoffs={name: selection[name]["threshold"] for name in ("heavy", "very_heavy")},
                          repeats=rule["bootstrap_replicates"], seed=rule["bootstrap_seed"])
    result = {"schema": "varshasetu-imd-realtime-2026-sensitivity-v1", "status": "PROVISIONAL_REFERENCE_SCORED_ONCE_NO_PROMOTION",
              "protocol_sha256": sha(PROTOCOL), "acquisition_sha256": sha(ACQUISITION), "forecast_year_sha256": sha(FORECAST_YEAR),
              "reference_role": "IMD_REALTIME_DAILY_BINARY_PROVISIONAL_NOT_ANNUAL_RF25_NETCDF", "paired_case_count": len(cases),
              "paired_cell_count": metrics["overall"]["paired_cells"], "metrics": metrics,
              "diagnostic_promotion_gates_only": metrics["promotion_gates"], "regime_promotion_authorized": False,
              "primary_annual_score_sha256": sha(PRIMARY_RESULT), "annual_netCDF_reference_gate": "PRIMARY_SCORED_FIRST",
              "gefs_actual_version_review_gate": "REVIEWED_FOR_PRIMARY",
              "model_default_after_score": "M2_UNCHANGED"}
    stage = RESULT.with_name(RESULT.name + ".stage")
    with stage.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(result, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write("\n")
    if RESULT.exists():
        raise FileExistsError("provisional score appeared during staging")
    stage.rename(RESULT)
    RESULT.with_suffix(".sha256").write_text(f"{sha(RESULT)}  {RESULT.name}\n", encoding="ascii")
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--preflight", action="store_true")
    group.add_argument("--score", action="store_true")
    args = parser.parse_args()
    if args.preflight:
        print(json.dumps(preflight(), sort_keys=True))
    else:
        result = score_once()
        print(json.dumps({"status": result["status"], "paired_case_count": result["paired_case_count"],
                          "paired_cell_count": result["paired_cell_count"], "sha256": sha(RESULT)}, sort_keys=True))


if __name__ == "__main__":
    main()
