"""Read-only monthly audit of the sealed 2026 forecast feature-range report.

No forecast values, observations, model predictions or GRIB messages are read.
The output is descriptive applicability evidence, never version clearance.
"""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "data/manifests/research_pilot"
FEATURES = BASE / "2026_jjas_feature_range_v1.json"
YEAR = BASE / "2026_forecast_jjas_year_v1.json"


def _verified_json(path: Path) -> tuple[dict, str]:
    raw = path.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    if path.with_suffix(".sha256").read_text(encoding="ascii").split() != [digest, path.name]:
        raise ValueError(f"SHA-256 receipt mismatch: {path.name}")
    return json.loads(raw), digest


def audit(feature_path: Path = FEATURES, year_path: Path = YEAR) -> dict:
    feature, feature_hash = _verified_json(feature_path)
    year, year_hash = _verified_json(year_path)
    if (feature.get("observation_read") is not False or feature.get("model_inference") is not False
            or year.get("observation_read") is not False or year.get("model_inference") is not False
            or feature.get("source_track") != "B_OPERATIONAL_GEFS"
            or feature.get("forecast_year_sha256") != year_hash):
        raise ValueError("Forecast-only provenance or year linkage is invalid")
    months = year["months"]
    if (sum(sum(month["passing"].values()) for month in months) != feature["cases"]
            or sum(block["cases"] for block in feature["by_lead"].values()) != feature["cases"]):
        raise ValueError("Feature-range and forecast-year case populations differ")
    expected_leads = set(feature["by_lead"])
    warnings = feature["dynamic_case_feature_warnings_over_5pct"]
    if any(row["lead"] not in expected_leads or not (0.05 < row["outside_fraction"] <= 1)
           or len(row["cycle"]) != 8 or not row["cycle"].isdigit() for row in warnings):
        raise ValueError("Invalid feature warning row")
    if len({(r["cycle"], r["lead"], r["feature"]) for r in warnings}) != len(warnings):
        raise ValueError("Duplicate feature warning row")
    result = []
    for month in months:
        name = month["month"]
        selected = [row for row in warnings if row["cycle"].startswith(name)]
        eligible = sum(month["passing"].values())
        flagged = len({(row["cycle"], row["lead"]) for row in selected})
        if flagged > eligible:
            raise ValueError("Flagged case count exceeds admitted population")
        result.append({"month": name, "eligible_case_leads": eligible,
                       "flagged_case_leads": flagged,
                       "flagged_fraction": flagged / eligible if eligible else None,
                       "feature_case_warnings": len(selected),
                       "warning_count_by_feature": dict(sorted(Counter(row["feature"] for row in selected).items()))})
    if sum(row["feature_case_warnings"] for row in result) != len(warnings):
        raise ValueError("Warning month is absent from the sealed forecast-year population")
    return {"status": "DESCRIPTIVE_FORECAST_ONLY_NO_VERSION_CLEARANCE",
            "feature_range_sha256": feature_hash, "forecast_year_sha256": year_hash,
            "observation_read": False, "cases": feature["cases"],
            "flagged_case_leads": len({(row["cycle"], row["lead"]) for row in warnings}),
            "feature_case_warnings": len(warnings), "months": result}


if __name__ == "__main__":
    print(json.dumps(audit(), indent=2, sort_keys=True))
