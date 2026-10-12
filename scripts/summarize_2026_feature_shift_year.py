"""Check JJAS 2026 forecast feature ranges after its full forecast-side seal."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import numpy as np  # noqa: E402

from scripts import summarize_2026_feature_shift as feature  # noqa: E402
from scripts import summarize_gefs_2026_forecast_year as yearly  # noqa: E402

OUT = ROOT / "data/manifests/research_pilot/2026_jjas_feature_range_v1.json"
STATIC = {"latitude_deg", "longitude_deg", "lead_hours"}


def summary() -> dict:
    year = yearly.summary()
    path = yearly.OUT
    if not path.is_file() or path.with_suffix(".sha256").read_text(encoding="ascii").split()[0] != hashlib.sha256(path.read_bytes()).hexdigest():
        raise ValueError("JJAS forecast-only year seal is missing or corrupt")
    if json.loads(path.read_text(encoding="utf-8")) != year:
        raise ValueError("JJAS forecast-only year differs from local sources")
    months = [feature.summarize(month) for month in yearly.MONTHS]
    training_hashes = {month["training_X_sha256"] for month in months}
    if len(training_hashes) != 1:
        raise ValueError("training matrix changed between feature-range checks")
    rows = [row for month in months for row in month["rows"]]
    if len(rows) != sum(year["products_passing_qc"].values()):
        raise ValueError("feature-range population differs from sealed QC population")
    by_lead = {}
    for name, expected in year["products_passing_qc"].items():
        subset = [row for row in rows if row["lead"] == name]
        if len(subset) != expected:
            raise ValueError(f"feature-range {name} population differs from QC seal")
        by_lead[name] = {"cases": expected, "mean_outside_fraction_by_feature":
                         {key: float(np.mean([row["outside_fraction_by_feature"][key] for row in subset])) if subset else None
                          for key in feature.FEATURE_NAMES}}
    warnings = [{"cycle": row["cycle"], "lead": row["lead"], "feature": key, "outside_fraction": value}
                for row in rows for key, value in row["outside_fraction_by_feature"].items()
                if key not in STATIC and value > .05]
    return {"schema": "varshasetu-2026-jjas-feature-range-v1", "source_track": "B_OPERATIONAL_GEFS",
            "observation_read": False, "model_inference": False, "training_X_sha256": next(iter(training_hashes)),
            "forecast_year_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "range_quantiles": [0.001, 0.999], "cases": len(rows), "by_lead": by_lead,
            "dynamic_case_feature_warnings_over_5pct": warnings,
            "interpretation": "Descriptive forecast-feature applicability only. It cannot prove model-version equivalence or rainfall skill."}


def main() -> None:
    report = summary()
    value = json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + "\n"
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(value)
    OUT.with_suffix(".sha256").write_text(hashlib.sha256(value.encode("utf-8")).hexdigest() + "  " + OUT.name + "\n", encoding="ascii")
    print(json.dumps({"cases": report["cases"], "by_lead": {key: value["cases"] for key, value in report["by_lead"].items()},
                      "dynamic_case_feature_warnings_over_5pct": len(report["dynamic_case_feature_warnings_over_5pct"])}, sort_keys=True))


if __name__ == "__main__":
    main()
