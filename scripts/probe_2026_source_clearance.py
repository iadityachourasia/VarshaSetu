"""Reproducible, metadata-only audit of the open 2026 source gates.

This script never opens rainfall grids, forecast arrays, or model predictions.
It does not produce the clearance manifests consumed by the frozen scorer.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "data/manifests/research_pilot"
OUTPUT = BASE / "2026_source_version_audit_v1.json"
INPUTS = {
    "annual_retry": "2026_imd_annual_retry_result_v3.json",
    "daily_candidate": "2026_imd_realtime_acquisition_v1.json",
    "gefs_source_audit": "2026_gefs_version_source_audit_v1.json",
    "radiation_probe": "2026_gefs_radiation_transition_result_v1.json",
    "score_protocol": "2026_track_b_score_protocol_v1.json",
}


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_sealed(path: Path) -> tuple[dict, str]:
    actual = digest(path)
    receipt = path.with_suffix(".sha256").read_text(encoding="ascii").split()
    if len(receipt) != 2 or receipt != [actual, path.name]:
        raise ValueError(f"missing or mismatched SHA-256 receipt: {path.name}")
    return json.loads(path.read_text(encoding="utf-8")), actual


def assess(annual: dict, daily: dict, gefs: dict, radiation: dict, protocol: dict) -> dict:
    """Return only supportable gate states from source metadata."""
    if protocol.get("reference_clearance_required") is None or protocol.get("model_version_clearance_required") is None:
        raise ValueError("frozen scorer source requirements are missing")
    if annual.get("observation_rainfall_values_read") is not False or daily.get("observation_values_decoded") is not False:
        raise ValueError("source audit must not consume 2026 rainfall values")
    if radiation.get("observation_read") is not False or radiation.get("model_inference") is not False:
        raise ValueError("radiation probe no longer has forecast-only provenance")

    annual_complete = annual.get("response_bytes", 0) > 0 and annual.get("status") == "VALID_COMPLETE_ANNUAL_REFERENCE"
    daily_complete = daily.get("expected_dates") == daily.get("received_dates") == 125 and not daily.get("errors")
    rows = radiation.get("rows", [])
    packing_change = (
        [row.get("cycle") for row in rows] == ["20230616", "20260615", "20260616"]
        and [row.get("grib_metadata", {}).get("bitsPerValue") for row in rows] == [10, 10, 16]
    )
    actual_transition = gefs.get("actual_2026_transition_confirmed") is True
    training_version = gefs.get("exact_2023_training_version_confirmed") is True
    equivalent = gefs.get("model_numerical_equivalence_established") is True

    blockers = []
    if not annual_complete:
        blockers.append("COMPLETE_2026_IMD_ANNUAL_REFERENCE_NOT_OBTAINED")
    if not actual_transition:
        blockers.append("ACTUAL_2026_GEFS_EXECUTABLE_TRANSITION_UNCONFIRMED")
    if not training_version:
        blockers.append("EXACT_2023_TRAINING_GEFS_PATCH_UNCONFIRMED")
    if not equivalent:
        blockers.append("2023_TO_2026_PREDICTOR_COMPARABILITY_UNREVIEWED")
    return {
        "status": "OPEN_NO_CLEARANCE" if blockers else "SOURCE_EVIDENCE_REQUIRES_MANUAL_REVIEW",
        "blockers": blockers,
        "annual_http_status": annual.get("http_status"),
        "annual_response_bytes": annual.get("response_bytes"),
        "daily_candidate_dates_receipted": daily.get("received_dates") if daily_complete else None,
        "daily_candidate_is_annual_reference": False,
        "radiation_packing_change_observed": packing_change,
        "radiation_probe_identifies_executable": False,
        "observation_values_read": False,
        "forecast_pairing_or_scoring": False,
        "clearance_manifests_written": False,
    }


def build(base: Path = BASE) -> dict:
    records = {key: read_sealed(base / filename) for key, filename in INPUTS.items()}
    decision = assess(*(records[key][0] for key in INPUTS))
    return {
        "schema": "varshasetu-2026-source-version-audit-v1",
        "evidence_sha256": {key: records[key][1] for key in INPUTS},
        **decision,
    }


def encode(record: dict) -> bytes:
    return (json.dumps(record, indent=2, sort_keys=True, allow_nan=False) + "\n").encode("utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true", help="create the write-once audit and SHA-256 receipt")
    parser.add_argument("--check", action="store_true", help="recompute and verify the existing audit")
    args = parser.parse_args()
    if args.write == args.check:
        parser.error("choose exactly one of --write or --check")
    payload = encode(build())
    receipt_path = OUTPUT.with_suffix(".sha256")
    if args.write:
        if OUTPUT.exists() or receipt_path.exists():
            raise FileExistsError("source audit is write-once")
        with OUTPUT.open("xb") as stream:
            stream.write(payload)
        receipt_path.write_text(f"{hashlib.sha256(payload).hexdigest()}  {OUTPUT.name}\n", encoding="ascii")
    else:
        saved, _ = read_sealed(OUTPUT)
        if encode(saved) != payload:
            raise ValueError("source audit no longer reproduces from sealed evidence")
    print(json.dumps({"status": json.loads(payload)["status"], "blockers": json.loads(payload)["blockers"]}, sort_keys=True))


if __name__ == "__main__":
    main()
