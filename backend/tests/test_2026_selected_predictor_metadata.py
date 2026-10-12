"""Forecast-only, read-only selected-predictor source audit gates."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from scripts.audit_2026_selected_predictor_metadata import (
    RESULT,
    build,
    differences,
    encode,
    sealed,
    verified_source,
)


def test_result_reproduces_without_source_clearance() -> None:
    saved, _ = sealed(RESULT)
    rebuilt = build()
    assert encode(saved) == encode(rebuilt)
    assert rebuilt["status"] == "METADATA_DIAGNOSTIC_COMPLETE_SOURCE_CLEARANCE_OPEN"
    assert rebuilt["observation_read"] is False
    assert rebuilt["forecast_values_decoded"] is False
    assert rebuilt["clearance_written"] is False
    assert len(rebuilt["rows"]) == 7
    for row in rebuilt["rows"].values():
        assert len(row["cycles"]) == 3
        assert row["comparisons"]["pre_to_post"]["identity_differences"] == {}


def test_identity_and_encoding_differences_remain_distinct() -> None:
    assert differences({"parameterNumber": 1, "bitsPerValue": 12},
                       {"parameterNumber": 2, "bitsPerValue": 12},
                       ("parameterNumber",)) == {"parameterNumber": {"first": 1, "second": 2}}
    assert differences({"parameterNumber": 1}, {"parameterNumber": 2}, ("bitsPerValue",)) == {}


def test_receipt_tamper_refused(tmp_path: Path) -> None:
    path = tmp_path / "result.json"
    path.write_text("{}\n", encoding="utf-8")
    path.with_suffix(".sha256").write_text("0" * 64 + "  result.json\n", encoding="ascii")
    with pytest.raises(ValueError, match="receipt mismatch"):
        sealed(path)


def test_2026_source_hash_tamper_refused(tmp_path: Path) -> None:
    folder = tmp_path / "pgrb2ap5"
    folder.mkdir()
    path = folder / "f024_u850.grib2"
    path.write_bytes(b"GRIB7777")
    receipt = {"url": "https://noaa-gefs-pds.s3.amazonaws.com/gefs.20260616/00/atmos/pgrb2ap5/gec00.t00z.pgrb2a.0p50.f024",
               "byte_range": [0, 7], "byte_size": 8, "sha256": hashlib.sha256(b"other").hexdigest()}
    Path(str(path) + ".receipt.json").write_text(json.dumps(receipt), encoding="utf-8")
    with pytest.raises(ValueError, match="receipt mismatch"):
        verified_source(path, "20260616", "u850", {})
