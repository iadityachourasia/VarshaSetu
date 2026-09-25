"""Phase 4F source-only checks. Network, observations and models are never used."""

from pathlib import Path

import numpy as np
import pytest

from backend.app.data.accumulation import GriddedAccumulationMessage
from experiments.recent_historical.phase4f_payload_acquisition_v1 import acquire, foundation, run, science, summarize


def _row(length=12):
    return {"year": 2023, "initialization": "2023-06-01T00:00:00Z",
            "member": "c00", "product_family": "pgrb2sp25", "variable": "rain",
            "forecast_hour": 3, "parameter": "APCP", "level": "surface",
            "noaa_object_key": "gefs.20230601/00/atmos/pgrb2sp25/gec00.t00z.pgrb2s.0p25.f003",
            "byte_start": 100, "byte_end": 100 + length - 1,
            "calculated_length": length, "index_sha256": "a" * 64,
            "expected_local_relative_path": "data/operational_gefs/v1/2023/20230601/pgrb2sp25/c00_f003_rain.grib2",
            "leads": ["day1_24h"]}


def test_frozen_protocol_and_phase4e_manifest_integrity():
    protocol, rows = foundation.checked_inputs()
    assert protocol["planned_dataset_identifier"] == "operational_gefs_imd_2023_2025_v1"
    assert len(rows) == 36_750
    assert sum(row["calculated_length"] for row in rows) == 10_485_487_577


def test_safe_path_and_invalid_range_rejection():
    row = _row()
    assert foundation.raw_path(row).is_relative_to(foundation.RAW_ROOT)
    with pytest.raises(ValueError):
        foundation.raw_path({**row, "expected_local_relative_path": "../outside.grib2"})
    acquire.verify_range_response(206, "bytes 100-111/1000", 12, row)
    for status, header, length in ((200, None, 12), (206, "bytes 101-112/1000", 12),
                                   (206, "bytes 100-111/1000", 11)):
        with pytest.raises(ValueError):
            acquire.verify_range_response(status, header, length, row)


class _Response:
    status = 206

    def __init__(self, payload):
        self.payload = payload
        self.sent = False

    def getheader(self, name):
        return {"Content-Range": "bytes 100-111/1000", "Content-Length": "12"}.get(name)

    def read(self, count):
        if self.sent:
            return b""
        self.sent = True
        return self.payload


class _Connection:
    def __init__(self, payload):
        self.payload = payload
        self.requests = []

    def request(self, method, path, headers):
        self.requests.append((method, path, headers))

    def getresponse(self):
        return _Response(self.payload)

    def close(self):
        pass


def test_atomic_range_receipt_and_hash_verified_resume(monkeypatch, tmp_path):
    payload = b"GRIBabcd7777"
    conn = _Connection(payload)
    raw = tmp_path / "data" / "operational_gefs" / "v1" / "rain.grib2"
    receipt = tmp_path / "receipt.json"
    monkeypatch.setattr(acquire, "ROOT", tmp_path)
    monkeypatch.setattr(acquire, "raw_path", lambda row: raw)
    monkeypatch.setattr(acquire, "receipt_path", lambda row: receipt)
    monkeypatch.setattr(acquire, "_protected_cache", lambda row: None)
    monkeypatch.setattr(acquire, "_connection", lambda: conn)
    first = acquire.download_one(_row())
    assert first["state"] == "HASH_VERIFIED" and first["bytes_network"] == 12
    saved = foundation.read_json(receipt)
    assert saved["sha256"] == foundation.sha256_file(raw)
    assert saved["content_range"] == "bytes 100-111/1000"
    assert conn.requests[0][0] == "GET" and conn.requests[0][2]["Range"] == "bytes=100-111"
    assert not raw.with_suffix(".grib2.part").exists()
    second = acquire.download_one(_row())
    assert second["cached"] and second["bytes_network"] == 0
    assert len(conn.requests) == 1


def test_interrupted_verified_transaction_recovers_without_network(monkeypatch, tmp_path):
    import hashlib
    payload = b"GRIBabcd7777"
    raw = tmp_path / "data" / "operational_gefs" / "v1" / "rain.grib2"
    raw.parent.mkdir(parents=True)
    part = raw.with_suffix(".grib2.part")
    part.write_bytes(payload)
    receipt = tmp_path / "receipt.json"
    pending = receipt.with_suffix(".pending.json")
    row = _row()
    foundation.write_json(pending, {"state": "HASH_VERIFIED",
        "source_url": f"https://{foundation.NOAA_HOST}/{row['noaa_object_key']}",
        "index_sha256": row["index_sha256"], "byte_start": row["byte_start"],
        "byte_end": row["byte_end"], "sha256": hashlib.sha256(payload).hexdigest()})
    monkeypatch.setattr(acquire, "raw_path", lambda row: raw)
    monkeypatch.setattr(acquire, "receipt_path", lambda row: receipt)
    monkeypatch.setattr(acquire, "_connection", lambda: pytest.fail("network must not be called"))
    result = acquire.download_one(row)
    assert result["cached"] and raw.read_bytes() == payload and receipt.exists()
    assert not part.exists() and not pending.exists()


def test_grib_header_trailer_and_length_validation(tmp_path):
    path = tmp_path / "message.grib2"
    path.write_bytes(b"GRIBabcd7777")
    assert len(acquire.verify_grib_file(path, _row())) == 64
    with pytest.raises(ValueError):
        acquire.verify_grib_file(path, _row(length=13))
    path.write_bytes(b"GRIBabcd0000")
    with pytest.raises(ValueError):
        acquire.verify_grib_file(path, _row())


def test_member_specific_packing_diagnostic_and_frozen_reconstruction(tmp_path, monkeypatch):
    prefix = GriddedAccumulationMessage(0, 3, np.full((49, 49), 0.06), "a", 0.01)
    total = GriddedAccumulationMessage(0, 6, np.zeros((49, 49)), "b", 0.1)
    direct = [GriddedAccumulationMessage(a, b, np.ones((49, 49)), str(b), 0.1)
              for a, b in ((6, 12), (12, 18), (18, 24), (24, 27))]
    messages = [prefix, total, *direct]
    diag = science._difference_diagnostic(messages, 3)
    assert diag["packing_bound_mm"] == pytest.approx(0.055)
    assert diag["negative_intermediate_cells"] == 49 * 49
    assert diag["packing_bound_violations"] == 49 * 49
    monkeypatch.setattr(science, "HERE", tmp_path)
    decoded = {("pgrb2sp25", "c00", hour, "rain"): {"status": "DECODE_VALIDATED", "accumulation": msg}
               for hour, msg in zip((3, 6, 12, 18, 24, 27), messages)}
    lead = {"rainfall_source_hours": [3, 6, 12, 18, 24, 27], "window_hours": [3, 27]}
    rejected = science._rain_case("20230601", "day1_24h", lead, "c00", decoded)
    assert rejected["status"] == "FAIL" and rejected["final_negative_cells"] is None
    good_total = GriddedAccumulationMessage(0, 6, np.full((49, 49), 0.02), "b", 0.1)
    decoded[("pgrb2sp25", "c00", 6, "rain")]["accumulation"] = good_total
    accepted = science._rain_case("20230601", "day1_24h", lead, "c00", decoded)
    assert accepted["status"] == "PASS" and accepted["final_negative_cells"] == 0
    assert accepted["subtraction_count"] == 1


def test_metadata_identity_grid_member_hour_and_accumulation():
    row = _row()
    row["calculated_length"] = 12
    meta = {"forecast_init": "20230601T0000Z", "valid_date": 20230601, "valid_time": 300,
            "requested_member": "c00", "grid": {"ni": 1440, "nj": 721,
                "grid_type": "regular_ll", "latitude_first": -90., "latitude_last": 90.,
                "longitude_first": 0., "longitude_last": 359.75},
            "short_name": "tp", "units": "kg m**-2", "start_step": 0, "end_step": 3,
            "step_type": "accum"}
    extra = {"edition": 2, "totalLength": 12, "gridDefinitionTemplateNumber": 0,
             "typeOfStatisticalProcessing": 1, "indicatorOfUnitForTimeRange": 1,
             "lengthOfTimeRange": 3}
    science.validate_metadata(row, meta, extra, [0, 3])
    for changed in ({"forecast_init": "20230602T0000Z"}, {"requested_member": "p01"},
                    {"valid_time": 600}, {"end_step": 6}, {"units": "mm"},
                    {"grid": {**meta["grid"], "ni": 720}}):
        with pytest.raises(ValueError):
            science.validate_metadata(row, {**meta, **changed}, extra, [0, 3])
    with pytest.raises(ValueError):
        science.validate_metadata(row, meta, {**extra, "lengthOfTimeRange": 6}, [0, 3])


def test_actual_cached_2024_grib_metadata_if_available():
    root = Path(__file__).resolve().parents[2]
    folder = root / "experiments/recent_historical/phase4b_20240718_20240724_v1/source/20240718/messages"
    matches = list(folder.glob("sp25_c00_f003_*.grib2"))
    if not matches:
        pytest.skip("optional protected Phase 4B source cache unavailable")
    payload = matches[0].read_bytes()
    old_receipt = foundation.read_json(matches[0].with_suffix(".receipt.json"))
    from backend.app.data_sources.noaa_gefs_monthly import decode_precipitation_message
    _, grid = decode_precipitation_message(payload, member="c00",
        description=old_receipt["index_description"], source_id=old_receipt["sha256"])
    extra = science.extra_grib_metadata(payload)
    row = {**_row(length=len(payload)), "year": 2024,
           "initialization": "2024-07-18T00:00:00Z", "forecast_hour": 3}
    science.validate_metadata(row, grid.metadata, extra, [0, 3])


def test_phase4f_modules_do_not_open_observations_or_models():
    # summarize.py names forbidden APIs as inert audit markers; acquisition
    # and decoding modules must not mention or call them.
    for module in (foundation, acquire, science):
        source = Path(module.__file__).read_text(encoding="utf-8").lower()
        assert "load_imd_day" not in source
        assert "xgb_predict" not in source
        assert "rf25_ind2025" not in source


def test_source_eligibility_statistics_keep_rejected_cases():
    def case(lead, control, atmosphere, other):
        rain = {name: {"status": "PASS" if value else "FAIL"} for name, value in
                {"c00": control, "p01": other, "p02": other, "p03": other, "p04": other}.items()}
        return {"product": lead, "rainfall_by_member": rain, "SOURCE_COMPLETE": True,
                "C00_RAINFALL_QC_PASS": control,
                "FULL_5_MEMBER_RAINFALL_QC_PASS": control and other,
                "ATMOSPHERIC_QC_PASS": atmosphere,
                "DETERMINISTIC_SOURCE_ELIGIBLE": control and atmosphere,
                "ENSEMBLE_SOURCE_ELIGIBLE": control and other and atmosphere,
                "PROBABILITY_SOURCE_ELIGIBLE": control and atmosphere,
                "REGIME_SOURCE_ELIGIBLE": atmosphere}
    cases = [case("day1_24h", True, True, False),
             case("day1_24h", False, True, True),
             case("day2_24h", True, False, True)]
    result = summarize._statistics(cases)
    assert result["scheduled_cases"] == 3
    assert result["control_rainfall_qc_pass"] == 2
    assert result["deterministic_source_eligible"] == 1
    assert result["ensemble_source_eligible"] == 0
    assert result["regime_source_eligible"] == 2
    assert result["by_lead"]["day1_24h"]["rainfall_by_member"]["c00"] == {"pass": 1, "fail": 1}


def test_recovery_rejects_out_of_schedule_date_before_preflight():
    with pytest.raises(ValueError, match="date outside frozen years"):
        run.recover_day("20260603")
    with pytest.raises(ValueError, match="date must be YYYYMMDD"):
        run.recover_day("../2025")


def test_real_recovery_preserves_partial_evidence_and_accepted_arrays():
    recovery_root = foundation.HERE / "recovery" / "2025"
    if not recovery_root.exists():
        pytest.skip("2025 selected-range recovery evidence not present")
    for day in ("20250603", "20250806"):
        archive = recovery_root / day
        log = foundation.read_json(archive / "recovery_log.json")
        old_checkpoint = archive / "initial_partial_checkpoint.json"
        old_metadata = archive / "initial_partial_decoded_metadata.json"
        assert foundation.sha256_file(old_checkpoint) == log["initial_checkpoint_sha256"]
        assert foundation.sha256_file(old_metadata) == log["initial_metadata_sha256"]
        prior = foundation.read_json(old_checkpoint)
        assert prior["missing_source_messages"] == 1
        assert prior["metadata_valid_messages"] == 97
        assert log["recovered_messages"] == 1
        current = foundation.read_json(foundation.HERE / "checkpoints" / "2025" / f"{day}.json")
        assert current["metadata_valid_messages"] == 98
        assert current["missing_source_messages"] == 0
        previous_arrays = []
        for record in foundation.read_json(old_metadata):
            if record.get("array_relative_path"):
                previous_arrays.append((record["array_relative_path"], record["array_sha256"]))
        for case in prior["cases"]:
            for item in case["rainfall_by_member"].values():
                if item.get("rainfall_relative_path"):
                    previous_arrays.append((item["rainfall_relative_path"], item["rainfall_sha256"]))
        assert len(previous_arrays) == log["preserved_accepted_array_hashes"]
        assert all(foundation.sha256_file(foundation.HERE / relative) == digest
                   for relative, digest in previous_arrays)
