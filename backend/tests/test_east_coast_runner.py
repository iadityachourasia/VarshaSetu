"""Guard the separate forecast-seal and development-score stages."""

import json
from pathlib import Path

import pytest

from scripts.run_east_coast_development import cases, receipt, write_once


def test_case_admission_is_included_only_and_deterministic():
    ledger = {"populations": {"2024": [
        {"case_id": "20240602_day2_24h", "product": "day2_24h", "status": "INCLUDED"},
        {"case_id": "20240601_day1_24h", "product": "day1_24h", "status": "INCLUDED"},
        {"case_id": "20240603_day3_24h", "product": "day3_24h", "status": "EXCLUDED"},
    ]}}
    assert cases(ledger, 2024) == [("20240601_day1_24h", 24), ("20240602_day2_24h", 48)]


def test_case_admission_rejects_duplicate():
    row = {"case_id": "20240601_day1_24h", "product": "day1_24h", "status": "INCLUDED"}
    with pytest.raises(ValueError, match="duplicate"):
        cases({"populations": {"2024": [row, row]}}, 2024)


def test_seal_is_write_once_and_tamper_detected(tmp_path: Path):
    path = tmp_path / "seal.json"
    write_once(path, {"forecast_year": 2024, "observation_values_read": False})
    assert receipt(path)
    assert json.loads(path.read_text())["observation_values_read"] is False
    with pytest.raises(FileExistsError):
        write_once(path, {})
    path.write_text('{"observation_values_read": true}\n')
    with pytest.raises(ValueError, match="receipt mismatch"):
        receipt(path)
