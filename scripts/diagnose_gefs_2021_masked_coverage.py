"""Forecast-only 2021 development-year check of the exploratory cell mask."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.app.data.accumulation import GriddedAccumulationMessage, reconstruct_minimal_accumulation_window  # noqa: E402
from backend.app.data_sources.noaa_gefs_monthly import crop_grid, decode_precipitation_message  # noqa: E402
from backend.app.live.pipeline import LEADS  # noqa: E402
from scripts.diagnose_gefs_2026_masked_coverage import diagnose_lead  # noqa: E402

PROTOCOL = ROOT / "data/manifests/research_pilot/2021_june_masked_coverage_protocol_v1.json"
SOURCE_MANIFEST = ROOT / "experiments/recent_historical/corpus2_payload_acquisition_v1/manifests/2021_source_manifest.json"
OUTPUT = ROOT / "data/manifests/research_pilot/2021_june_masked_coverage_result_v1.json"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def checked_json(path: Path) -> tuple[dict, str]:
    digest = sha(path)
    if path.with_suffix(".sha256").read_text(encoding="ascii").split()[0] != digest:
        raise ValueError(f"manifest hash mismatch: {path}")
    return json.loads(path.read_text(encoding="utf-8")), digest


def load_cycle(cycle: str, source_files: dict) -> tuple[dict[int, GriddedAccumulationMessage], dict[str, str]]:
    messages, hashes = {}, {}
    for hour in sorted({hour for lead in LEADS.values() for hour in lead["rain_hours"]}):
        relative = f"data/operational_gefs/v2/2021/{cycle}/pgrb2sp25/c00_f{hour:03d}_rain.grib2"
        path = ROOT / relative
        payload = path.read_bytes()
        digest = hashlib.sha256(payload).hexdigest()
        expected = source_files[relative]
        if digest != expected["sha256"] or len(payload) != expected["bytes"]:
            raise ValueError(f"source manifest mismatch: {relative}")
        accumulation, grid = decode_precipitation_message(
            payload, member="c00", description="ENS=low-res ctl", source_id=digest
        )
        if accumulation.end_hour != hour:
            raise ValueError(f"source end step mismatch: {relative}")
        region = crop_grid(grid, south=10, north=22, west=68, east=80)
        if region.values.shape != (49, 49):
            raise ValueError(f"regional grid mismatch: {relative}")
        messages[hour] = GriddedAccumulationMessage(
            accumulation.start_hour, accumulation.end_hour, region.values,
            accumulation.source_id, accumulation.packing_quantum_mm,
        )
        hashes[str(hour)] = digest
    return messages, hashes


def main() -> None:
    settings, protocol_hash = checked_json(PROTOCOL)
    if settings["observation_read"] is not False or settings["model_inference"] is not False or settings["changes_canonical_qc"] is not False:
        raise ValueError("development diagnostic protocol changed")
    source, source_manifest_hash = checked_json(SOURCE_MANIFEST)
    rows = []
    for day in range(1, 31):
        cycle = f"202106{day:02d}"
        rain, hashes = load_cycle(cycle, source["files"])
        leads = {}
        for name, rule in LEADS.items():
            messages = [rain[hour] for hour in rule["rain_hours"]]
            try:
                reconstruct_minimal_accumulation_window(messages, window_start_hour=rule["window"][0], window_end_hour=rule["window"][1])
            except ValueError as error:
                if "negative difference exceeds packing bound" not in str(error):
                    raise
                passed = False
            else:
                passed = True
            leads[name] = diagnose_lead(messages, *rule["window"], canonical_passed=passed)
        rows.append({"cycle": cycle, "source_rain_sha256": hashes, "leads": leads})
        print(json.dumps({"cycle": cycle, "completed": len(rows)}), flush=True)
    all_leads = [row["leads"][name] for row in rows for name in LEADS]
    withheld = [lead for lead in all_leads if not lead["canonical_passed"]]
    report = {
        "schema": "varshasetu-2021-june-masked-coverage-result-v1",
        "protocol_sha256": protocol_hash,
        "source_manifest_sha256": source_manifest_hash,
        "observation_read": False,
        "model_inference": False,
        "diagnostic_only": True,
        "canonical_passing_leads": len(all_leads) - len(withheld),
        "canonical_withheld_leads": len(withheld),
        "withheld_leads_with_at_least_99pct_valid_cells": sum(lead["valid_fraction"] >= .99 for lead in withheld),
        "minimum_valid_fraction_among_withheld": min((lead["valid_fraction"] for lead in withheld), default=None),
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
