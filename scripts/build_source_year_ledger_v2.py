"""Version the source/year ledger after the complete 2026 forecast-only seal.

The v1 ledger is retained byte-for-byte. V2 updates the 2026 forecast entry
from an October live example to the verified JJAS year while leaving its
independent-test candidacy and missing IMD reference explicit.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts import build_source_year_ledger as previous  # noqa: E402
from scripts import summarize_gefs_2026_forecast_year as yearly  # noqa: E402

OUT = ROOT / "data/manifests/research_pilot/source_year_ledger_v2.json"
NOTE = ROOT / "data/manifests/research_pilot/2026_gefs_model_change_note_v1.json"
AUDIT = ROOT / "data/manifests/research_pilot/2026_prior_observation_use_audit_v2.json"
IMD_PROBE = ROOT / "data/manifests/research_pilot/2026_imd_header_probe_result_v1.json"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build() -> dict:
    if not previous.OUTPUT.is_file():
        raise ValueError("source/year ledger v1 is missing")
    v1 = json.loads(previous.OUTPUT.read_text(encoding="utf-8"))
    if v1 != previous.build():
        raise ValueError("source/year ledger v1 differs from current local inputs")
    year_path = yearly.OUT
    if not year_path.is_file() or year_path.with_suffix(".sha256").read_text(encoding="ascii").split()[0] != sha(year_path):
        raise ValueError("2026 JJAS forecast-only year seal missing or corrupt")
    year = json.loads(year_path.read_text(encoding="utf-8"))
    if year != yearly.summary():
        raise ValueError("2026 JJAS year seal differs from month/source artifacts")
    if NOTE.with_suffix(".sha256").read_text(encoding="ascii").split()[0] != sha(NOTE):
        raise ValueError("2026 GEFS model-change note hash mismatch")
    if AUDIT.with_suffix(".sha256").read_text(encoding="ascii").split()[0] != sha(AUDIT):
        raise ValueError("2026 prior observation-use audit hash mismatch")
    prior_use = json.loads(AUDIT.read_text(encoding="utf-8"))
    prior_path = AUDIT.with_name("2026_prior_observation_use_audit_v1.json")
    if prior_use["previous_audit_sha256"] != sha(prior_path):
        raise ValueError("2026 prior observation-use audit history differs")
    if not prior_use["prior_use_gate"].startswith("PROVISIONALLY_CLEARED") or prior_use["observation_values_read_for_this_audit"] is not False:
        raise ValueError("2026 prior observation-use audit did not clear its limited gate")
    if IMD_PROBE.with_suffix(".sha256").read_text(encoding="ascii").split()[0] != sha(IMD_PROBE):
        raise ValueError("2026 IMD header probe hash mismatch")
    imd_probe = json.loads(IMD_PROBE.read_text(encoding="utf-8"))
    if imd_probe["forecast_year_sha256"] != sha(year_path) or imd_probe["observation_rainfall_values_read"] is not False:
        raise ValueError("2026 IMD header probe does not match sealed forecast year")
    rows = [dict(row) for row in v1["rows"]]
    candidates = [row for row in rows if row["track"] == "B_OPERATIONAL_GEFS" and row["year"] == 2026]
    if len(candidates) != 1:
        raise ValueError("expected exactly one 2026 Track B source row")
    row = candidates[0]
    row["forecast"] = previous.artifact(year_path)
    row["imd_reference"] = {
        "status": "not_local" if imd_probe["status"] != "LOCAL_REFERENCE_HEADER_READY_UNSCORED" else "local_unscored",
        "path": imd_probe.get("local_path"),
        "sha256": imd_probe.get("response_sha256") if imd_probe.get("local_path") else None,
        "bytes": imd_probe.get("response_bytes") if imd_probe.get("local_path") else None,
        "header_probe_status": imd_probe["status"],
        "header_probe_sha256": sha(IMD_PROBE),
    }
    row["forecast_content"] = {
        "source": "NOAA operational GEFS control member, selected byte ranges",
        "source_url_pattern": "https://noaa-gefs-pds.s3.amazonaws.com/gefs.YYYYMMDD/00/atmos/",
        "initialization_time_utc": "00:00",
        "forecast_publication_time": "not recorded by cache receipts",
        "processing_time": "per-cycle created_at_utc in immutable local case manifests",
        "spatial_coverage": "10-22 N, 68-80 E, 0.25-degree, 49x49 cells",
        "accumulation_window_hours": previous.WINDOWS,
        "case_count": year["cycle_count"],
        "passing_leads": year["products_passing_qc"],
        "withheld_leads": year["products_withheld_qc"],
        "no_eligible_lead_cycles": year["no_eligible_lead_cycles"],
        "month_manifest_sha256": {entry["month"]: entry["manifest_sha256"] for entry in year["months"]},
        "model_change_note_sha256": sha(NOTE),
        "prior_observation_use_audit_sha256": sha(AUDIT),
        "licence_and_redistribution": "NOAA archive public access; downstream reuse terms not independently audited",
        "observation_read": False,
        "training_or_model_selection": False,
    }
    row["new_experiment_role"] = "2026 Track B test candidate only; independence, reference and model-version gates pending"
    return {**v1, "schema": "source-year-ledger-v2", "previous_ledger_sha256": sha(previous.OUTPUT),
            "2026_forecast_year_sha256": sha(year_path), "rows": rows,
            "meaning": "Versioned local evidence inventory; 2026 forecast side complete but independent test, rights and rainfall skill unclaimed"}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    payload = json.dumps(build(), indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    if args.check:
        if not OUT.is_file() or OUT.read_text(encoding="utf-8") != payload or OUT.with_suffix(".sha256").read_text(encoding="ascii").split()[0] != sha(OUT):
            raise ValueError("source/year ledger v2 differs from verified local artifacts")
        print(f"verified {OUT.relative_to(ROOT)}")
        return
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(payload)
    OUT.with_suffix(".sha256").write_text(hashlib.sha256(payload.encode("utf-8")).hexdigest() + "  " + OUT.name + "\n", encoding="ascii")
    print(f"wrote {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
