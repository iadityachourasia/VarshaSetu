"""Versioned source-gated entrypoint for the unchanged 2026 one-shot scorer.

The v2 amendment adds source and human-review checks before delegating to
the hash-pinned v1 scoring algorithm. No 2026 rainfall values are read in
preflight. Never call --score before every external source gate is cleared.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts import audit_2026_clearance_readiness as audit  # noqa: E402
from scripts import score_2026_frozen_inference as frozen  # noqa: E402
from scripts.run_2026_frozen_inference import sealed, sha  # noqa: E402

BASE = ROOT / "data/manifests/research_pilot"
PROTOCOL = BASE / "2026_track_b_score_gate_protocol_v2.json"
APPROVAL = BASE / "2026_source_review_approval_v2.json"
GATE_RESULT = BASE / "2026_track_b_score_gate_result_v2.json"


def validate_approval(record: dict, *, reference_sha256: str,
                      version_sha256: str, annual_sha256: str) -> list[str]:
    """Check explicit human approval bound to the exact source clearances."""
    reasons = []
    try:
        reviewed = datetime.fromisoformat(record["reviewed_utc"].replace("Z", "+00:00"))
        dated = reviewed.tzinfo is not None and reviewed.utcoffset() == timedelta(0)
    except (KeyError, AttributeError, ValueError):
        dated = False
    if (record.get("schema") != "varshasetu-2026-source-review-approval-v2"
            or record.get("status") != "APPROVED_FOR_ONE_SHOT_RESEARCH_VERIFICATION"
            or not dated or not isinstance(record.get("reviewer_name"), str)
            or not record["reviewer_name"].strip()
            or not isinstance(record.get("review_notes"), str)
            or not record["review_notes"].strip()):
        reasons.append("SOURCE_REVIEW_APPROVAL_IDENTITY_OR_DECISION_INVALID")
    if (record.get("imd_clearance_sha256") != reference_sha256
            or record.get("gefs_clearance_sha256") != version_sha256
            or record.get("annual_reference_sha256") != annual_sha256):
        reasons.append("SOURCE_REVIEW_APPROVAL_INPUT_HASH_MISMATCH")
    if (record.get("source_authenticity_and_rights_reviewed") is not True
            or record.get("gefs_deployment_and_predictors_reviewed") is not True
            or record.get("independent_test_seal_reconfirmed") is not True):
        reasons.append("SOURCE_REVIEW_APPROVAL_SCOPE_INCOMPLETE")
    return reasons


def preflight() -> dict:
    reasons: list[str] = []
    try:
        protocol = sealed(PROTOCOL)
        expected = {
            "v1_score_protocol_sha256": sha(frozen.PROTOCOL),
            "v1_scorer_sha256": sha(Path(frozen.__file__)),
            "supplemental_auditor_sha256": sha(Path(audit.__file__)),
            "v2_entrypoint_sha256": sha(Path(__file__)),
        }
        if protocol.get("status") != "FROZEN_SOURCE_GATE_AMENDMENT_BEFORE_2026_OBSERVATION_PAIRING":
            reasons.append("V2_SCORE_GATE_PROTOCOL_NOT_FROZEN")
        if any(protocol.get(key) != value for key, value in expected.items()):
            reasons.append("V2_SCORE_GATE_CODE_OR_PROTOCOL_HASH_CHANGED")
    except (OSError, ValueError, KeyError):
        reasons.append("V2_SCORE_GATE_PROTOCOL_SEAL_INVALID")

    try:
        source = audit.preflight()
        if source["status"] != "READY_FOR_MANUAL_SOURCE_REVIEW":
            reasons.extend(source["reasons"])
    except (OSError, ValueError, KeyError) as error:
        reasons.append(f"SUPPLEMENTAL_SOURCE_AUDIT_FAILED:{type(error).__name__}")

    if not APPROVAL.is_file():
        reasons.append("HUMAN_SOURCE_REVIEW_APPROVAL_MISSING")
    else:
        try:
            record = sealed(APPROVAL)
            reasons.extend(validate_approval(
                record, reference_sha256=sha(frozen.REFERENCE_CLEARANCE),
                version_sha256=sha(frozen.VERSION_CLEARANCE),
                annual_sha256=sha(frozen.IMD),
            ))
        except (OSError, ValueError, KeyError):
            reasons.append("HUMAN_SOURCE_REVIEW_APPROVAL_INVALID")
    if (frozen.RESULT.exists() or GATE_RESULT.exists()
            or GATE_RESULT.with_suffix(".sha256").exists()):
        reasons.append("ONE_SHOT_2026_SCORE_ALREADY_EXISTS")
    return {"status": "READY_FOR_AUTHORIZED_ONE_SHOT_SCORE" if not reasons else "BLOCKED_BEFORE_OBSERVATION_READ",
            "reasons": sorted(set(reasons)), "forecast_cases": 213,
            "observation_read": False, "score_run": False}


def score_once() -> dict:
    gate = preflight()
    if gate["status"] != "READY_FOR_AUTHORIZED_ONE_SHOT_SCORE":
        raise RuntimeError("2026 v2 source gate blocked before observation read: " + ", ".join(gate["reasons"]))
    result = frozen.score_once()
    companion = {
        "schema": "varshasetu-2026-track-b-score-gate-result-v2",
        "status": "V1_SCORE_EXECUTED_THROUGH_V2_SOURCE_GATE_NO_AUTOMATIC_PROMOTION",
        "v2_gate_protocol_sha256": sha(PROTOCOL),
        "source_review_approval_sha256": sha(APPROVAL),
        "imd_clearance_sha256": sha(frozen.REFERENCE_CLEARANCE),
        "gefs_clearance_sha256": sha(frozen.VERSION_CLEARANCE),
        "v1_score_sha256": sha(frozen.RESULT),
        "forecast_cases": result["case_count"],
        "model_default_after_score": "M2_UNCHANGED_PENDING_FORECASTER_GOVERNANCE",
    }
    payload = (json.dumps(companion, indent=2, sort_keys=True, allow_nan=False) + "\n").encode("utf-8")
    with GATE_RESULT.open("xb") as stream:
        stream.write(payload)
    with GATE_RESULT.with_suffix(".sha256").open("x", encoding="ascii", newline="\n") as receipt:
        receipt.write(f"{sha(GATE_RESULT)}  {GATE_RESULT.name}\n")
    return companion


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--preflight", action="store_true")
    group.add_argument("--score", action="store_true")
    args = parser.parse_args()
    result = preflight() if args.preflight else score_once()
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
