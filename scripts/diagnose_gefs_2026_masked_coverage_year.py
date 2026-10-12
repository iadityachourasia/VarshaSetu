"""Read-only masked-cell coverage study over the sealed 2026 JJAS corpus.

This exploratory report never changes the canonical QC population or fills a
missing rainfall cell. It reads receipt-verified forecast precipitation only.
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.app.live.pipeline import LEADS  # noqa: E402
from scripts import build_gefs_2026_forecast_corpus as corpus  # noqa: E402
from scripts import summarize_gefs_2026_forecast_year as yearly  # noqa: E402
from scripts.diagnose_gefs_2026_masked_coverage import diagnose_lead, load_rain  # noqa: E402

OUT = ROOT / "data/manifests/research_pilot/2026_jjas_masked_coverage_diagnostic_v1.json"


def summary() -> dict:
    year = yearly.summary()
    year_path = yearly.OUT
    if not year_path.is_file() or year_path.with_suffix(".sha256").read_text(encoding="ascii").split()[0] != hashlib.sha256(year_path.read_bytes()).hexdigest():
        raise ValueError("forecast-only JJAS year seal is missing or corrupt")
    if json.loads(year_path.read_text(encoding="utf-8")) != year:
        raise ValueError("forecast-only JJAS year differs from local sources")
    settings, corpus_hash = corpus.protocol()
    rows = []
    for month in yearly.MONTHS:
        for cycle in corpus.dates_for_month(month, settings):
            case_path = corpus.CORPUS / cycle / "manifest.json"
            case = corpus.verify_case(case_path.parent, corpus_hash)
            rain = load_rain(cycle, case)
            leads = {}
            for name, rule in LEADS.items():
                result = diagnose_lead([rain[hour] for hour in rule["rain_hours"]], *rule["window"],
                                       canonical_passed=name in case["products_passing_qc"])
                withheld = name in case["withheld_products"] or "all" in case["withheld_products"]
                if withheld == result["canonical_passed"]:
                    raise ValueError(f"canonical case status differs: {cycle} {name}")
                leads[name] = {key: result[key] for key in ("canonical_passed", "valid_cells", "invalid_cells", "total_cells", "valid_fraction")}
            rows.append({"cycle": cycle, "case_manifest_sha256": corpus.sha(case_path), "leads": leads})
            print(json.dumps({"cycle": cycle, "completed": len(rows)}), flush=True)
    if len(rows) != 122:
        raise ValueError("JJAS diagnostic requires 122 forecast dates")
    all_leads = [row["leads"][name] for row in rows for name in LEADS]
    passing = sum(lead["canonical_passed"] for lead in all_leads)
    if passing != sum(year["products_passing_qc"].values()):
        raise ValueError("masked diagnostic canonical population differs from year seal")
    withheld = [lead for lead in all_leads if not lead["canonical_passed"]]
    return {"schema": "varshasetu-2026-jjas-masked-coverage-diagnostic-v1",
            "forecast_year_sha256": hashlib.sha256(year_path.read_bytes()).hexdigest(),
            "observation_read": False, "model_inference": False, "changes_canonical_qc": False,
            "diagnostic_only": True, "date_count": len(rows), "possible_date_lead_products": len(all_leads),
            "canonical_passing_leads": passing, "canonical_withheld_leads": len(withheld),
            "withheld_leads_with_at_least_99pct_valid_cells": sum(lead["valid_fraction"] >= .99 for lead in withheld),
            "minimum_valid_fraction_among_withheld": min((lead["valid_fraction"] for lead in withheld), default=None),
            "rows": rows,
            "interpretation": "Post hoc forecast-side coverage only. Missing cells stay missing; no partial forecast is published or scored."}


def main() -> None:
    report = summary()
    value = json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + "\n"
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(value)
    OUT.with_suffix(".sha256").write_text(hashlib.sha256(value.encode("utf-8")).hexdigest() + "  " + OUT.name + "\n", encoding="ascii")
    print(json.dumps({key: report[key] for key in ("date_count", "canonical_passing_leads", "canonical_withheld_leads", "withheld_leads_with_at_least_99pct_valid_cells", "minimum_valid_fraction_among_withheld")}, sort_keys=True))


if __name__ == "__main__":
    main()
