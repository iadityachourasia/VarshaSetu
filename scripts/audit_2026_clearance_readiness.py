"""Supplemental 2026 source-clearance audit; never opens rainfall values.

The frozen v1 scorer is unchanged. This audit makes its evidence requirements
explicit before any future versioned, authorized one-shot score.
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import numpy as np
from scipy.io import netcdf_file

from scripts.score_2026_frozen_inference import (  # noqa: E402
    FORECAST_YEAR,
    IMD,
    REFERENCE_CLEARANCE,
    VERSION_CLEARANCE,
    preflight as frozen_preflight,
)
from scripts.run_2026_frozen_inference import sealed  # noqa: E402

TRAIN_CASES = ROOT / "data/operational_derived/operational_features_2023_2025_v1/2023/train/deterministic/cases.json"
FIELDS = ("rain", "u850", "v850", "q700", "z500", "mslp", "pwat")
SHA256 = re.compile(r"^[0-9a-f]{64}$")
VERSION = re.compile(r"^gefs\.v\d+\.\d+\.\d+$")


def _evidence(value: object) -> bool:
    return isinstance(value, str) and (value.startswith("https://") or bool(SHA256.fullmatch(value)))


def validate_reference_claim(review: dict) -> list[str]:
    """Check explicit annual-file and rights claims, before touching the file."""
    reasons = []
    expected = {
        "status": "APPROVED_FOR_LOCAL_RESEARCH_VERIFICATION",
        "annual_calendar_year": 2026,
        "daily_record_count": 365,
        "first_date": "2026-01-01",
        "last_date": "2026-12-31",
        "accumulation_window_utc": "03:00-03:00",
    }
    if any(review.get(key) != value for key, value in expected.items()):
        reasons.append("ANNUAL_REFERENCE_COVERAGE_OR_WINDOW_NOT_REVIEWED")
    if not isinstance(review.get("file_sha256"), str) or not SHA256.fullmatch(review["file_sha256"]):
        reasons.append("ANNUAL_REFERENCE_SHA256_MISSING")
    if not _evidence(review.get("source_url_or_receipt")):
        reasons.append("ANNUAL_REFERENCE_SOURCE_RECEIPT_MISSING")
    terms = review.get("terms")
    if (not isinstance(terms, dict) or terms.get("local_research_use_authorized") is not True
            or not _evidence(terms.get("authorization_evidence_uri_or_hash"))
            or terms.get("redistribution_decision") not in ("AUTHORIZED", "NOT_AUTHORIZED")):
        reasons.append("IMD_LOCAL_USE_AND_REDISTRIBUTION_TERMS_UNREVIEWED")
    return reasons


def validate_annual_metadata(path: Path) -> list[str]:
    """Read only NetCDF axes, variable shape and file bytes; never rainfall values."""
    if not path.is_file():
        return ["COMPLETE_ANNUAL_REFERENCE_FILE_MISSING"]
    try:
        with netcdf_file(path, "r", mmap=True) as dataset:
            variables = dataset.variables
            if not {"TIME", "LATITUDE", "LONGITUDE", "RAINFALL"}.issubset(variables):
                return ["ANNUAL_REFERENCE_NETCDF_VARIABLES_INVALID"]
            time = variables["TIME"]
            units = getattr(time, "units")
            units = units.decode("ascii") if isinstance(units, bytes) else str(units)
            if not units.startswith("days since "):
                return ["ANNUAL_REFERENCE_TIME_UNITS_INVALID"]
            origin = datetime.fromisoformat(units[len("days since "):])
            offsets = np.asarray(time.data, dtype=np.float64).copy()
            dates = [origin + timedelta(days=float(value)) for value in offsets]
            if (len(dates) != 365 or len(set(dates)) != 365
                    or dates[0].date().isoformat() != "2026-01-01"
                    or dates[-1].date().isoformat() != "2026-12-31"
                    or any((dates[i + 1] - dates[i]) != timedelta(days=1) for i in range(364))):
                return ["ANNUAL_REFERENCE_DAILY_AXIS_INCOMPLETE"]
            if variables["RAINFALL"].shape != (365, 129, 135):
                return ["ANNUAL_REFERENCE_RAINFALL_SHAPE_INVALID"]
            if len(variables["LATITUDE"].data) != 129 or len(variables["LONGITUDE"].data) != 135:
                return ["ANNUAL_REFERENCE_GRID_SHAPE_INVALID"]
    except (OSError, ValueError, AttributeError, TypeError):
        return ["ANNUAL_REFERENCE_NETCDF_METADATA_UNREADABLE"]
    return []


def validate_version_claim(review: dict, training_cycles: set[str], forecast_cycles: set[str]) -> list[str]:
    """Require cycle-specific executable identity and seven predictor reviews."""
    reasons = []
    transition = review.get("actual_transition_utc")
    try:
        parsed_transition = datetime.fromisoformat(transition.replace("Z", "+00:00"))
        valid_transition = parsed_transition.tzinfo is not None and parsed_transition.utcoffset() == timedelta(0)
    except (AttributeError, ValueError):
        valid_transition = False
    if (review.get("status") != "MODEL_VERSION_REVIEW_COMPLETE"
            or not _evidence(review.get("authoritative_evidence_uri_or_hash"))
            or not valid_transition):
        reasons.append("ACTUAL_2026_GEFS_DEPLOYMENT_EVIDENCE_INCOMPLETE")
    for name, expected in (("training_cycle_versions", training_cycles),
                           ("forecast_cycle_versions", forecast_cycles)):
        versions = review.get(name)
        if (not isinstance(versions, dict) or set(versions) != expected
                or any(not isinstance(value, str) or not VERSION.fullmatch(value) for value in versions.values())):
            reasons.append(f"{name.upper()}_INCOMPLETE")
    if not _evidence(review.get("training_version_evidence_uri_or_hash")):
        reasons.append("EXACT_2023_TRAINING_PATCH_EVIDENCE_MISSING")
    reviewed = review.get("selected_predictor_review")
    if (not isinstance(reviewed, dict) or set(reviewed) != set(FIELDS)
            or any(not isinstance(item, dict)
                   or item.get("decision") != "ACCEPT_FOR_STRATIFIED_EVALUATION"
                   or not _evidence(item.get("evidence_uri_or_hash"))
                   or not isinstance(item.get("rationale"), str) or not item["rationale"].strip()
                   for item in reviewed.values())):
        reasons.append("SELECTED_PREDICTOR_COMPARABILITY_NOT_APPROVED")
    return reasons


def preflight() -> dict:
    prior = frozen_preflight()
    reasons = list(prior["reasons"])
    if REFERENCE_CLEARANCE.exists():
        try:
            ref = sealed(REFERENCE_CLEARANCE)
            reasons.extend(validate_reference_claim(ref))
            reasons.extend(validate_annual_metadata(IMD))
            if IMD.is_file():
                h = hashlib.sha256()
                with IMD.open("rb") as stream:
                    for block in iter(lambda: stream.read(1 << 20), b""):
                        h.update(block)
                if ref.get("file_sha256") != h.hexdigest():
                    reasons.append("ANNUAL_REFERENCE_FILE_HASH_MISMATCH")
        except (OSError, ValueError, KeyError):
            reasons.append("ANNUAL_REFERENCE_REVIEW_SEAL_INVALID")
    if VERSION_CLEARANCE.exists():
        try:
            version = sealed(VERSION_CLEARANCE)
            train = json.loads(TRAIN_CASES.read_text(encoding="utf-8"))
            training_cycles = {case["initialization_utc"][:10].replace("-", "") for case in train}
            forecast_cycles = set(sealed(FORECAST_YEAR)["case_manifest_sha256"])
            reasons.extend(validate_version_claim(version, training_cycles, forecast_cycles))
        except (OSError, ValueError, KeyError):
            reasons.append("GEFS_VERSION_REVIEW_SEAL_INVALID")
    return {"status": "READY_FOR_MANUAL_SOURCE_REVIEW" if not reasons else "BLOCKED_BEFORE_OBSERVATION_READ",
            "reasons": sorted(set(reasons)), "observation_values_read": False,
            "scorer_modified": False, "score_run": False}


if __name__ == "__main__":
    print(json.dumps(preflight(), sort_keys=True))
