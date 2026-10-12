"""Seal forecast-only JJAS 2026 only after all four month summaries verify."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts import summarize_gefs_2026_forecast_corpus as monthly  # noqa: E402

OUT = ROOT / "data/manifests/research_pilot/2026_forecast_jjas_year_v1.json"
MONTHS = ("202606", "202607", "202608", "202609")


def summary(*, base: Path = monthly.OUT) -> dict:
    month_rows = []
    for month in MONTHS:
        path = base / f"2026_forecast_month_{month}_v1.json"
        sidecar = path.with_suffix(".sha256")
        if not path.is_file() or not sidecar.is_file():
            raise ValueError(f"forecast-only 2026 year is incomplete: {month} month seal missing")
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if sidecar.read_text(encoding="ascii").split()[0] != digest:
            raise ValueError(f"forecast-only month seal hash mismatch: {month}")
        report = json.loads(path.read_text(encoding="utf-8"))
        if report["month"] != month or report["observation_read"] is not False or report["model_inference"] is not False:
            raise ValueError(f"forecast-only month identity differs: {month}")
        # Re-verify every local source receipt and feature array. The month
        # summary alone cannot substitute for the local forecast-side corpus.
        reproduced = monthly.summary(month)
        if report != reproduced:
            raise ValueError(f"forecast-only month differs from current sources: {month}")
        month_rows.append({"month": month, "manifest_sha256": digest, "cycle_count": report["cycle_count"],
                           "passing": report["products_passing_qc"], "withheld": report["products_withheld_qc"],
                           "no_eligible_lead_cycles": report["no_eligible_lead_cycles"]})
    if sum(row["cycle_count"] for row in month_rows) != 122:
        raise ValueError("JJAS 2026 requires exactly 122 cycle records")
    products = month_rows[0]["passing"]
    return {"schema": "varshasetu-2026-forecast-only-jjas-year-v1", "cycle_count": 122,
            "possible_date_lead_products": 366, "observation_read": False, "model_inference": False,
            "months": month_rows,
            "products_passing_qc": {name: sum(row["passing"][name] for row in month_rows) for name in products},
            "products_withheld_qc": {name: sum(row["withheld"][name] for row in month_rows) for name in products},
            "no_eligible_lead_cycles": sum(row["no_eligible_lead_cycles"] for row in month_rows),
            "interpretation": "Forecast-side availability only; no reference rainfall, independence clearance or model skill."}


def main() -> None:
    report = summary()
    value = json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + "\n"
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(value)
    OUT.with_suffix(".sha256").write_text(hashlib.sha256(value.encode("utf-8")).hexdigest() + "  " + OUT.name + "\n", encoding="ascii")
    print(json.dumps({"cycle_count": report["cycle_count"], "products_passing_qc": report["products_passing_qc"],
                      "no_eligible_lead_cycles": report["no_eligible_lead_cycles"]}, sort_keys=True))


if __name__ == "__main__":
    main()
