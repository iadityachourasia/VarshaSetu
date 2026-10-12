"""The source/year inventory cannot silently reclassify consumed tests."""

import json
import hashlib
from pathlib import Path

import pytest

from scripts import build_source_year_ledger as ledger
from scripts import build_source_year_ledger_v2 as ledger_v2
from scripts import build_source_year_ledger_v3 as ledger_v3
from scripts import build_source_year_ledger_v4 as ledger_v4


def test_saved_ledger_marks_consumed_years_and_does_not_preseal_2026():
    path = Path(__file__).resolve().parents[2] / "data/manifests/research_pilot/source_year_ledger_v1.json"
    saved = json.loads(path.read_text(encoding="utf-8"))
    rows = {(row["track"], row["year"]): row for row in saved["rows"]}
    assert saved["schema"] == "source-year-ledger-v1" and len(rows) == 27
    for year in (2014, 2015, 2016, 2019):
        assert rows[("A_GEFSV12_REFORECAST", year)]["consumed_test"] is True
    for year in (2022, 2025):
        assert rows[("B_OPERATIONAL_GEFS", year)]["consumed_test"] is True
    candidate = rows[("B_OPERATIONAL_GEFS", 2026)]
    assert candidate["role_in_prior_work"] == "test_candidate_audit_pending"
    assert candidate["imd_reference"]["status"] == "not_local"
    assert "requires a separate frozen protocol" in candidate["new_experiment_role"]
    assert "candidate only" in saved["test_reservation"]["2026"]


def test_local_ledger_rebuild_matches_saved_hashes_when_local_data_exist():
    path = ledger.OUTPUT
    if not ledger.REFORECAST_PROTOCOL.is_file() or not ledger.OPERATIONAL_MANIFESTS[2023].is_file():
        pytest.skip("local source manifests are unavailable; saved ledger semantics remain tested")
    assert json.loads(path.read_text(encoding="utf-8")) == ledger.build()


def test_v2_refuses_to_replace_2026_live_example_before_year_seal(monkeypatch, tmp_path):
    monkeypatch.setattr(ledger_v2.yearly, "OUT", tmp_path / "missing-year.json")
    with pytest.raises(ValueError, match="year seal missing"):
        ledger_v2.build()


def test_v2_attaches_a_complete_forecast_side_without_skill_claim(monkeypatch, tmp_path):
    v1 = json.loads(ledger.OUTPUT.read_text(encoding="utf-8"))
    monkeypatch.setattr(ledger_v2.previous, "build", lambda: v1)
    year = {"cycle_count": 122, "products_passing_qc": {"day1_24h": 40},
            "products_withheld_qc": {"day1_24h": 82}, "no_eligible_lead_cycles": 8,
            "months": [{"month": "202606", "manifest_sha256": "a" * 64}]}
    path = tmp_path / "year.json"
    path.write_text(json.dumps(year), encoding="utf-8")
    path.with_suffix(".sha256").write_text(hashlib.sha256(path.read_bytes()).hexdigest(), encoding="ascii")
    monkeypatch.setattr(ledger_v2.yearly, "OUT", path)
    monkeypatch.setattr(ledger_v2.yearly, "summary", lambda: year)
    monkeypatch.setattr(ledger_v2.previous, "artifact", lambda _: {"status": "local", "path": "year.json", "sha256": hashlib.sha256(path.read_bytes()).hexdigest(), "bytes": path.stat().st_size})
    probe = tmp_path / "imd_probe.json"
    probe.write_text(json.dumps({"forecast_year_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                                 "observation_rainfall_values_read": False, "status": "SOURCE_UNAVAILABLE"}), encoding="utf-8")
    probe.with_suffix(".sha256").write_text(hashlib.sha256(probe.read_bytes()).hexdigest(), encoding="ascii")
    monkeypatch.setattr(ledger_v2, "IMD_PROBE", probe)
    result = ledger_v2.build()
    candidate = next(row for row in result["rows"] if row["track"] == "B_OPERATIONAL_GEFS" and row["year"] == 2026)
    assert candidate["forecast_content"]["case_count"] == 122
    assert candidate["forecast_content"]["observation_read"] is False
    assert candidate["imd_reference"]["status"] == "not_local"
    assert candidate["imd_reference"]["header_probe_status"] == "SOURCE_UNAVAILABLE"
    assert "candidate" in candidate["new_experiment_role"]


def test_v3_records_empty_imd_response_without_promoting_2026():
    result = ledger_v3.build()
    candidate = next(row for row in result["rows"] if row["track"] == "B_OPERATIONAL_GEFS" and row["year"] == 2026)
    assert candidate["imd_reference"]["status"] == "not_local"
    assert candidate["imd_reference"]["header_probe_http_status"] == 200
    assert candidate["imd_reference"]["header_probe_response_bytes"] == 0
    assert candidate["consumed_test"] is False


def test_v4_keeps_daily_candidate_separate_from_missing_annual_reference():
    result = ledger_v4.build()
    candidate = next(row for row in result["rows"] if row["track"] == "B_OPERATIONAL_GEFS" and row["year"] == 2026)
    assert candidate["imd_reference"]["status"] == "not_local"
    assert candidate["imd_reference"]["latest_header_probe_response_bytes"] == 0
    assert candidate["imd_realtime_candidate"]["daily_grid_count"] == 125
    assert candidate["imd_realtime_candidate"]["primary_reference_equivalent"] is False
    assert candidate["imd_realtime_candidate"]["raw_redistribution_authorized"] is False
    assert candidate["consumed_test"] is False
