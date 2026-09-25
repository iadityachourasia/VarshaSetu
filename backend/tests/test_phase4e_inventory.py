"""Index-only Phase 4E contract tests; no HTTP, GRIB, IMD or model access."""

from datetime import date

import pytest

from experiments.recent_historical.phase4e_source_inventory_v1.inventory import (
    EXPECTED_INTERVALS, checked_protocol, expected_fields, expected_objects,
    match_message, parse_index, schedule, source_key,
)
from experiments.recent_historical.phase4e_source_inventory_v1.summarize import (
    _case, _compatibility, _expectation_rows, build_acquisition_rows,
)


def _index(day="20230601", hour=3, member="c00", interval="0-3"):
    ensemble = "low-res ctl" if member == "c00" else f"+{int(member[1:])}"
    return (f"1:0:d={day}00:VIS:surface:{hour} hour fcst:ENS={ensemble}\n"
            f"2:100:d={day}00:APCP:surface:{interval} hour acc fcst:ENS={ensemble}\n"
            f"3:300:d={day}00:TMP:surface:{hour} hour fcst:ENS={ensemble}\n").encode()


def test_frozen_hash_calendar_and_case_count():
    protocol = checked_protocol()
    days = schedule(protocol)
    assert len(days) == 375
    assert days[0] == "20230601" and days[-1] == "20251003"
    assert len(days) * len(protocol["forecast_leads"]) == 1125
    assert "20240229" not in days
    assert len({date(int(x[:4]), int(x[4:6]), int(x[6:])) for x in days}) == 375


def test_exact_object_enumeration_and_member_hour_mapping():
    protocol = checked_protocol()
    objects = expected_objects("20230601", protocol)
    assert len(objects) == 86
    assert len({obj["key"] for obj in objects}) == 86
    assert sum(obj["family"] == "pgrb2sp25" for obj in objects) == 80
    assert sum(obj["family"] == "pgrb2ap5" for obj in objects) == 3
    assert sum(obj["family"] == "pgrb2bp5" for obj in objects) == 3
    assert source_key("20230601", "pgrb2sp25", "p04", 75).endswith("gep04.t00z.pgrb2s.0p25.f075")
    with pytest.raises(ValueError):
        source_key("20230601", "pgrb2sp25", "p05", 75)
    assert len(expected_fields(next(obj for obj in objects if obj["family"] == "pgrb2ap5"), protocol)) == 4
    assert len(expected_fields(next(obj for obj in objects if obj["family"] == "pgrb2bp5"), protocol)) == 2
    assert set(EXPECTED_INTERVALS) == set(protocol["rainfall_source_hours_union"])


def test_index_parser_unique_match_and_exact_byte_range():
    rows = parse_index(_index())
    assert len(rows) == 3
    assert rows[1]["number"] == 2
    assert (rows[1]["start"], rows[1]["end"]) == (100, 299)
    match = match_message(rows, day="20230601", hour=3, member="c00",
                          field="rain", parameter="APCP", level="surface")
    assert match["status"] == "MESSAGE_AVAILABLE"
    assert match["message"]["interval"] == [0, 3]
    assert match["requires_object_size"] is False


def test_missing_ambiguous_and_changed_metadata_are_not_admitted():
    rows = parse_index(_index())
    assert match_message(rows, day="20230601", hour=3, member="c00", field="rain",
                         parameter="SPFH", level="700 mb")["status"] == "MESSAGE_MISSING"
    assert match_message(rows + [dict(rows[1])], day="20230601", hour=3, member="c00",
                         field="rain", parameter="APCP", level="surface")["status"] == "UNEXPECTED_PRODUCT_STRUCTURE"
    assert match_message(rows, day="20230602", hour=3, member="c00", field="rain",
                         parameter="APCP", level="surface")["status"] == "METADATA_INCONSISTENT"
    assert match_message(rows, day="20230601", hour=3, member="p01", field="rain",
                         parameter="APCP", level="surface")["status"] == "METADATA_INCONSISTENT"
    wrong = parse_index(_index(interval="3-6"))
    assert match_message(wrong, day="20230601", hour=3, member="c00", field="rain",
                         parameter="APCP", level="surface")["status"] == "METADATA_INCONSISTENT"
    with pytest.raises(ValueError):
        parse_index(b"not a NOAA inventory")


def test_case_completeness_is_member_specific_and_payload_qc_remains_pending():
    protocol = checked_protocol()
    objects = {}
    for item in expected_objects("20230601", protocol):
        fields = [{"variable": name, "status": "MESSAGE_AVAILABLE", "reason": None,
                   "message": {"number": 2, "start": 100, "end": 299,
                               "interval": [0, 3] if item["family"] == "pgrb2sp25" else None,
                               "forecast": "0-3 hour acc fcst", "ensemble": "ENS=low-res ctl"}}
                  for name, _, _ in expected_fields(item, protocol)]
        objects[(item["family"], item["member"], item["hour"])] = {
            **item, "fields": fields, "key": item["key"], "index_url": "https://example.invalid/index",
            "source_url": "https://example.invalid/source",
            "checked_at_utc": "2026-01-01T00:00:00Z", "index_sha256": "a" * 64}
    lead = protocol["forecast_leads"]["day1_24h"]
    case = _case("20230601", "day1_24h", lead, objects, protocol)
    assert case["deterministic_index_complete"] is True
    assert case["full_five_member_index_complete"] is True
    assert case["rainfall_requires_decoded_qc"] is True
    rows = _expectation_rows("20230601", case, lead, objects, protocol)
    assert len(rows) == 36
    assert rows[0]["grid_template"] is None and rows[0]["units"] is None
    assert rows[0]["interval_start_hour"] == 0
    objects[("pgrb2sp25", "p04", 3)]["fields"][0]["status"] = "MESSAGE_MISSING"
    case = _case("20230601", "day1_24h", lead, objects, protocol)
    assert case["deterministic_index_complete"] is True
    assert case["full_five_member_index_complete"] is False
    assert case["rainfall_messages_complete_by_member"]["p04"] is False
    assert case["missing_count"] == 1


def test_holdout_seal_is_not_bypassed_by_index_module_imports():
    from pathlib import Path
    import experiments.recent_historical.phase4e_source_inventory_v1.inventory as inventory
    import experiments.recent_historical.phase4e_source_inventory_v1.summarize as summarize

    for module in (inventory, summarize):
        text = Path(module.__file__).read_text(encoding="utf-8").lower()
        assert "load_imd_day" not in text
        assert "xgb_predict" not in text
        assert "rf25_ind2025" not in text


def test_acquisition_manifest_deduplicates_shared_messages_and_keeps_exact_ranges():
    base = {"year": 2023, "initialization": "2023-06-01T00:00:00Z", "member": "c00",
            "product_family": "pgrb2sp25", "variable": "rain", "forecast_hour": 27,
            "parameter": "APCP", "level": "surface", "expected_object": "gefs.20230601/example",
            "index_object": "gefs.20230601/example.idx", "grib_message_number": 18,
            "byte_start": 100, "byte_end": 299, "index_sha256": "a" * 64,
            "status": "MESSAGE_AVAILABLE"}
    rows = [{**base, "lead": "day1_24h"}, {**base, "lead": "day2_24h"},
            {**base, "lead": "day3_24h", "status": "MESSAGE_MISSING"}]
    manifest = build_acquisition_rows(rows)
    assert len(manifest) == 1
    assert manifest[0]["leads"] == ["day1_24h", "day2_24h"]
    assert manifest[0]["calculated_length"] == 200
    assert manifest[0]["byte_end"] == 299


def test_cross_year_signature_change_blocks_or_limits_payload_gate():
    rows = []
    cases = []
    for year in (2023, 2024, 2025):
        cases.append({"initialization": f"{year}-06-01T00:00:00Z", "missing_count": 0,
                      "full_five_member_index_complete": True, "atmospheric_index_complete": True})
        rows.append({"year": year, "initialization": f"{year}-06-01T00:00:00Z", "lead": "day1_24h",
                     "member": "c00", "product_family": "pgrb2sp25", "variable": "rain",
                     "forecast_hour": 3, "parameter": "APCP", "level": "surface",
                     "forecast_description": "0-3 hour acc fcst" if year != 2025 else "3 hour acc fcst",
                     "ensemble_description": "ENS=low-res ctl", "status": "MESSAGE_AVAILABLE", "reason": None})
    result = _compatibility(rows, cases)
    assert result["decision"] == "PARTIAL_COMPATIBILITY"
    assert result["index_message_signatures_comparable"] is False


def test_missing_index_and_missing_source_object_are_distinguished(monkeypatch, tmp_path):
    from urllib.error import HTTPError
    import experiments.recent_historical.phase4e_source_inventory_v1.inventory as inventory

    monkeypatch.setattr(inventory, "_index_paths", lambda item: (tmp_path / "x.idx", tmp_path / "x.receipt.json"))
    monkeypatch.setattr(inventory, "_old_cache_paths", lambda item: [])

    def not_found(request, timeout):
        url = request if isinstance(request, str) else request.full_url
        raise HTTPError(url, 404, "Not Found", {}, None)

    monkeypatch.setattr(inventory, "urlopen", not_found)
    monkeypatch.setattr(inventory, "_fetch_small_index", not_found)
    item = expected_objects("20230601", checked_protocol())[0]
    result = inventory.fetch_index(item, retries=0)
    assert result["status"] == "SOURCE_OBJECT_MISSING"
    assert result["http_status"] == 404
    assert result["grib_head_status"] == 404
    assert not (tmp_path / "x.idx").exists()
