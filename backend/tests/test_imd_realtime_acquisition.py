"""Local integrity checks for the separately acquired IMD daily candidate."""

from __future__ import annotations

from datetime import date

import pytest

from scripts import acquire_imd_realtime_2026 as acquisition


def test_daily_receipt_is_immutable_and_cached_bytes_are_verified(tmp_path, monkeypatch):
    sample = bytes(acquisition.EXPECTED_BYTES)
    calls = []

    def fake_request(target):
        calls.append(target)
        return sample, {"http_status": 200, "content_type": "application/octet-stream", "retrieved_utc": "2026-10-07T00:00:00+00:00", "attempts": 1}

    monkeypatch.setattr(acquisition, "_request", fake_request)
    monkeypatch.setattr(acquisition, "ROOT", tmp_path)
    day = date(2026, 6, 1)
    first = acquisition._write_day(day, tmp_path / "raw")
    assert first["byte_size"] == acquisition.EXPECTED_BYTES
    assert first["forecast_pairing"] is False
    assert first["observation_values_decoded"] is False
    assert acquisition._write_day(day, tmp_path / "raw") == first
    assert calls == [day]

    (tmp_path / "raw" / "rainfall_20260601.grd").write_bytes(bytes([1]) + sample[1:])
    with pytest.raises(ValueError, match="cached day changed"):
        acquisition._write_day(day, tmp_path / "raw")


def test_2026_protocol_dates_and_byte_count_are_fixed():
    assert acquisition.EXPECTED_BYTES == 69660
    assert (acquisition.END - acquisition.START).days + 1 == 125
    assert acquisition.START == date(2026, 6, 1)
    assert acquisition.END == date(2026, 10, 3)
