"""Append IMD daily-source acquisition and the later annual retry to ledger v3."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts import build_source_year_ledger_v3 as previous  # noqa: E402
from scripts.run_2026_frozen_inference import sealed, sha  # noqa: E402

BASE = ROOT / "data/manifests/research_pilot"
OUT = BASE / "source_year_ledger_v4.json"
ANNUAL_RETRY = BASE / "2026_imd_annual_retry_result_v3.json"
DAILY = BASE / "2026_imd_realtime_acquisition_v1.json"
PILOT = BASE / "2025_imd_realtime_annual_comparison_v1.json"
TERMS = BASE / "2026_imd_realtime_access_terms_v1.json"
VERSION = BASE / "2026_gefs_version_source_audit_v1.json"


def build() -> dict:
    prior = sealed(previous.OUT)
    if prior != previous.build():
        raise ValueError("v3 ledger does not reproduce")
    annual, daily, pilot, terms, version = (sealed(path) for path in (ANNUAL_RETRY, DAILY, PILOT, TERMS, VERSION))
    if annual["status"] != "UNAVAILABLE_OR_NON_NETCDF_RESPONSE" or annual["response_bytes"] != 0:
        raise ValueError("latest annual retry differs")
    if daily["status"] != "COMPLETE_UNSCORED_CANDIDATE" or daily["received_dates"] != 125 or daily["errors"]:
        raise ValueError("daily source is not complete")
    if daily["observation_values_decoded"] is not False or daily["forecast_observation_pairing"] is not False:
        raise ValueError("daily source already used")
    if pilot["2026_observation_values_used"] is not False or pilot["nonidentical_valid_cells"] == 0:
        raise ValueError("daily/annual distinction lost")
    if terms["rights_for_public_warning_or_raw_redistribution"] != "NOT_ESTABLISHED" or version["clearance_status"] != "OPEN_DO_NOT_SCORE_ANNUAL_INDEPENDENT_TEST_YET":
        raise ValueError("source rights or model-version state changed")
    rows = [dict(row) for row in prior["rows"]]
    candidates = [row for row in rows if row["track"] == "B_OPERATIONAL_GEFS" and row["year"] == 2026]
    if len(candidates) != 1:
        raise ValueError("expected one 2026 operational GEFS row")
    row = candidates[0]
    row["imd_reference"] = {**row["imd_reference"], "latest_header_probe_sha256": sha(ANNUAL_RETRY),
                            "latest_header_probe_status": annual["status"],
                            "latest_header_probe_http_status": annual["http_status"],
                            "latest_header_probe_response_bytes": annual["response_bytes"]}
    row["imd_realtime_candidate"] = {"status": "local_complete_unscored", "source_page": terms["source_page"],
                                     "acquisition_manifest_path": DAILY.relative_to(ROOT).as_posix(),
                                     "acquisition_manifest_sha256": sha(DAILY), "daily_grid_count": daily["received_dates"],
                                     "date_range": ["2026-06-01", "2026-10-03"],
                                     "source_comparison_sha256": sha(PILOT), "rights_review_sha256": sha(TERMS),
                                     "primary_reference_equivalent": False,
                                     "raw_redistribution_authorized": False}
    row["gefs_version_source_audit_sha256"] = sha(VERSION)
    sources = {**prior["sources"], "IMD_REALTIME_DAILY": terms["source_page"]}
    return {**prior, "schema": "source-year-ledger-v4", "previous_ledger_sha256": sha(previous.OUT),
            "2026_imd_annual_retry_sha256": sha(ANNUAL_RETRY), "2026_imd_realtime_acquisition_sha256": sha(DAILY),
            "2025_imd_daily_annual_comparison_sha256": sha(PILOT), "2026_imd_realtime_access_terms_sha256": sha(TERMS),
            "2026_gefs_version_source_audit_sha256": sha(VERSION), "rows": rows, "sources": sources,
            "meaning": "2026 daily real-time IMD candidate locally complete and unscored; annual NetCDF remains absent and GEFS actual-version review open"}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    payload = json.dumps(build(), indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    if args.check:
        if OUT.read_text(encoding="utf-8") != payload or OUT.with_suffix(".sha256").read_text(encoding="ascii").split()[0] != sha(OUT):
            raise ValueError("v4 ledger differs from local evidence")
        print(f"verified {OUT.relative_to(ROOT)}")
        return
    with OUT.open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(payload)
    OUT.with_suffix(".sha256").write_text(hashlib.sha256(payload.encode("utf-8")).hexdigest() + "  " + OUT.name + "\n", encoding="ascii")
    print(f"wrote {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
