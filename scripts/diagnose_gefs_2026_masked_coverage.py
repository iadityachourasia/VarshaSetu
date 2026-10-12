"""Forecast-only, read-only cell-mask coverage study for the sealed June corpus.

This diagnostic never publishes forecasts or changes the canonical QC decision.
It reads only receipt-verified cached NOAA precipitation messages and reports
how many 0.25-degree regional cells a separate masked method could retain.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import numpy as np  # noqa: E402

from backend.app.data.accumulation import GriddedAccumulationMessage, reconstruct_minimal_accumulation_window  # noqa: E402
from backend.app.data.accumulation_masked import reconstruct_masked_diagnostic  # noqa: E402
from backend.app.data_sources.noaa_gefs_monthly import crop_grid, decode_precipitation_message  # noqa: E402
from backend.app.live.pipeline import LEADS, SOURCE_CACHE  # noqa: E402
from scripts.build_gefs_2026_forecast_corpus import CORPUS, protocol, verify_case  # noqa: E402

OUTPUT = ROOT / "data/manifests/research_pilot/2026_june_masked_coverage_diagnostic_v1.json"


def load_rain(cycle: str, case: dict, *, cache_root: Path = SOURCE_CACHE) -> dict[int, GriddedAccumulationMessage]:
    """Use manifest hashes and cache receipts; never make a network request."""
    messages = {}
    for hour in sorted({hour for lead in LEADS.values() for hour in lead["rain_hours"]}):
        path = cache_root / cycle / "pgrb2sp25" / f"f{hour:03d}_rain.grib2"
        payload = path.read_bytes()
        digest = hashlib.sha256(payload).hexdigest()
        key = f"pgrb2sp25:{hour}:rain"
        receipt = json.loads(path.with_name(path.name + ".receipt.json").read_text(encoding="utf-8"))
        if digest != case["source_sha256"][key] or digest != receipt["sha256"] or len(payload) != receipt["byte_size"]:
            raise ValueError(f"source receipt mismatch: {cycle} f{hour:03d}")
        accumulation, grid = decode_precipitation_message(
            payload, member="c00", description="ENS=low-res ctl", source_id=digest
        )
        if accumulation.end_hour != hour:
            raise ValueError(f"wrong precipitation end step: {cycle} f{hour:03d}")
        region = crop_grid(grid, south=10, north=22, west=68, east=80)
        if region.values.shape != (49, 49):
            raise ValueError(f"wrong region shape: {cycle} f{hour:03d}")
        messages[hour] = GriddedAccumulationMessage(
            accumulation.start_hour, accumulation.end_hour, region.values,
            accumulation.source_id, accumulation.packing_quantum_mm,
        )
    return messages


def diagnose_lead(messages: list[GriddedAccumulationMessage], start: int, end: int, *, canonical_passed: bool) -> dict:
    masked = reconstruct_masked_diagnostic(messages, window_start_hour=start, window_end_hour=end)
    total = masked.valid_mask.size
    if canonical_passed:
        canonical = reconstruct_minimal_accumulation_window(messages, window_start_hour=start, window_end_hour=end)
        if masked.invalid_cells != 0 or not np.array_equal(masked.rainfall_mm, canonical.rainfall_mm):
            raise ValueError("masked diagnostic differs from a canonical passing lead")
    elif masked.invalid_cells == 0:
        raise ValueError("masked diagnostic recovered all cells from a canonical withheld lead")
    return {
        "canonical_passed": canonical_passed,
        "valid_cells": int(masked.valid_mask.sum()),
        "invalid_cells": masked.invalid_cells,
        "total_cells": total,
        "valid_fraction": float(masked.valid_mask.mean()),
        "minimum_valid_rainfall_mm": float(np.min(masked.rainfall_mm[masked.valid_mask])) if masked.valid_mask.any() else None,
        "segments": list(masked.segments),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--month", default="202606", choices=["202606"])
    args = parser.parse_args()
    settings, corpus_protocol_hash = protocol()
    cycles = [f"202606{day:02d}" for day in range(1, 31)]
    rows = []
    for cycle in cycles:
        case = verify_case(CORPUS / cycle, corpus_protocol_hash)
        rain = load_rain(cycle, case)
        leads = {}
        for name, rule in LEADS.items():
            lead = diagnose_lead(
                [rain[hour] for hour in rule["rain_hours"]], *rule["window"],
                canonical_passed=name in case["products_passing_qc"],
            )
            withheld = name in case["withheld_products"] or "all" in case["withheld_products"]
            if withheld == lead["canonical_passed"]:
                raise ValueError(f"case/QC status mismatch: {cycle} {name}")
            leads[name] = lead
        rows.append({"cycle": cycle, "case_manifest_sha256": hashlib.sha256((CORPUS / cycle / "manifest.json").read_bytes()).hexdigest(), "leads": leads})
        print(json.dumps({"cycle": cycle, "completed": len(rows)}), flush=True)
    all_leads = [row["leads"][name] for row in rows for name in LEADS]
    withheld = [item for item in all_leads if not item["canonical_passed"]]
    report = {
        "schema": "varshasetu.2026_june_masked_coverage_diagnostic.v1",
        "scope": "regional_10_to_22_n_68_to_80_e_2026_june_forecast_only",
        "observation_read": False,
        "diagnostic_only": True,
        "changes_canonical_qc": False,
        "corpus_protocol_sha256": corpus_protocol_hash,
        "canonical_passing_leads": len(all_leads) - len(withheld),
        "canonical_withheld_leads": len(withheld),
        "withheld_leads_with_at_least_99pct_valid_cells": sum(item["valid_fraction"] >= .99 for item in withheld),
        "minimum_valid_fraction_among_withheld": min((item["valid_fraction"] for item in withheld), default=None),
        "rows": rows,
    }
    value = json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + "\n"
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT.open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(value)
    OUTPUT.with_suffix(".sha256").write_text(hashlib.sha256(value.encode("utf-8")).hexdigest() + "  " + OUTPUT.name + "\n", encoding="ascii")
    print(json.dumps({key: report[key] for key in ("canonical_passing_leads", "canonical_withheld_leads", "withheld_leads_with_at_least_99pct_valid_cells", "minimum_valid_fraction_among_withheld")}, sort_keys=True))


if __name__ == "__main__":
    main()
