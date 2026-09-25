import hashlib
import json
from datetime import date, datetime, timezone
from pathlib import Path

import numpy as np
import pytest
from pydantic import ValidationError

from app.data.cache import CacheIntegrityError, FetchResponse, fetch_cached, receipt_path
from app.data.loader import load_source_dataset
from app.data.monthly_models import MonthlyCollectionManifest
from app.data.monthly_qc import (
    ATMOSPHERIC_LEADS,
    ENSEMBLE_MEMBERS,
    PRODUCT_WINDOWS,
    monthly_initializations,
    product_valid_date,
    summarize_initialization_status,
)
from app.data.readiness import assess_training_readiness
from app.data_sources import noaa_gefs_monthly as gefs


def test_july_sequence_and_product_dates_are_exact():
    initializations = monthly_initializations()
    assert len(initializations) == 31
    assert initializations[0] == datetime(2019, 7, 1, tzinfo=timezone.utc)
    assert initializations[-1] == datetime(2019, 7, 31, tzinfo=timezone.utc)
    assert list(PRODUCT_WINDOWS.values()) == [(3, 27), (27, 51), (51, 75)]
    assert [product_valid_date(initializations[0], product) for product in PRODUCT_WINDOWS] == [
        date(2019, 7, 2),
        date(2019, 7, 3),
        date(2019, 7, 4),
    ]
    assert product_valid_date(initializations[-1], "day3_24h") == date(2019, 8, 3)


def test_valid_cache_is_reused_without_network(tmp_path):
    calls = 0

    def fetcher(url, byte_range, timeout):
        nonlocal calls
        calls += 1
        return FetchResponse(b"authoritative", 200, {})

    path = tmp_path / "source.bin"
    first = fetch_cached("https://example.test/source", path, fetcher=fetcher)
    second = fetch_cached("https://example.test/source", path, fetcher=fetcher)
    assert first.from_cache is False
    assert second.from_cache is True
    assert second.network_bytes == 0
    assert calls == 1


def test_invalid_or_partial_cache_is_rejected(tmp_path):
    path = tmp_path / "source.bin"
    path.write_bytes(b"unreceipted partial data")
    with pytest.raises(CacheIntegrityError, match="partial cache state"):
        fetch_cached("https://example.test/source", path)

    path.unlink()
    path.write_bytes(b"valid-before-corruption")
    receipt_path(path).write_text(
        json.dumps(
            {
                "url": "https://example.test/source",
                "byte_range": None,
                "byte_size": path.stat().st_size,
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            }
        ),
        encoding="utf-8",
    )
    path.write_bytes(b"corrupted")
    with pytest.raises(CacheIntegrityError, match="checksum mismatch"):
        fetch_cached("https://example.test/source", path)


def test_timeout_is_retried_and_truncated_range_never_commits(tmp_path):
    attempts = 0

    def flaky(url, byte_range, timeout):
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            raise TimeoutError("simulated timeout")
        return FetchResponse(b"abcd", 206, {"content-range": "bytes 0-3/10"})

    path = tmp_path / "range.bin"
    result = fetch_cached(
        "https://example.test/range",
        path,
        byte_range=(0, 3),
        retries=2,
        backoff_seconds=0,
        fetcher=flaky,
    )
    assert attempts == 2
    assert result.attempts == 2

    truncated = tmp_path / "truncated.bin"
    with pytest.raises(IOError, match="failed to fetch"):
        fetch_cached(
            "https://example.test/truncated",
            truncated,
            byte_range=(0, 3),
            retries=1,
            fetcher=lambda *_: FetchResponse(b"abc", 206, {}),
        )
    assert not truncated.exists()
    assert not receipt_path(truncated).exists()

    wrong_range = tmp_path / "wrong-range.bin"
    with pytest.raises(IOError, match="failed to fetch") as captured:
        fetch_cached(
            "https://example.test/wrong-range",
            wrong_range,
            byte_range=(0, 3),
            retries=1,
            fetcher=lambda *_: FetchResponse(
                b"abcd", 206, {"content-range": "bytes 4-7/10"}
            ),
        )
    assert "Content-Range" in str(captured.value.__cause__)
    assert not wrong_range.exists()


def test_missing_noaa_object_remains_visible_and_uncommitted(tmp_path):
    path = tmp_path / "missing.grib2"
    with pytest.raises(IOError, match="failed to fetch"):
        fetch_cached(
            "https://example.test/missing.grib2",
            path,
            retries=1,
            fetcher=lambda *_: FetchResponse(b"not found", 404, {}),
        )
    assert not path.exists()
    assert not receipt_path(path).exists()


def test_member_identity_must_match_requested_archive_member(monkeypatch):
    metadata = {
        "perturbationNumber": 1,
        "typeOfEnsembleForecast": 3,
    }
    monkeypatch.setattr(gefs, "_optional", lambda handle, key: metadata.get(key))
    confirmed = gefs._member_metadata(
        object(), "p01", "1:0:d=2019070100:APCP:surface:0-3 hour acc fcst:ENS=+1"
    )
    assert confirmed["requested_member"] == "p01"
    assert confirmed["perturbation_number"] == 1
    with pytest.raises(ValueError, match="does not match requested"):
        gefs._member_metadata(
            object(), "p02", "1:0:d=2019070100:APCP:surface:0-3 hour acc fcst:ENS=+2"
        )


def test_q700_contract_uses_actual_above_700mb_archive_family():
    spec = gefs.ATMOSPHERIC_SPECS["q700"]
    assert spec.object_family == "spfh_pres_abv700mb"
    assert spec.short_name == "q"
    assert spec.parameter_name == "Specific humidity"
    assert spec.type_of_level == "isobaricInhPa"
    assert spec.level == 700
    assert "kg kg**-1" in spec.units
    assert ATMOSPHERIC_LEADS == (24, 48, 72)


def test_atmospheric_decoder_rejects_wrong_level_and_lead(monkeypatch):
    values = np.ones((2, 2))
    latitude = np.array([5.0, 5.5])
    longitude = np.array([55.0, 55.5])
    spec = gefs.ATMOSPHERIC_SPECS["q700"]
    base = {
        "short_name": "q",
        "parameter_name": "Specific humidity",
        "type_of_level": "isobaricInhPa",
        "level": 700,
        "units": "kg kg**-1",
        "forecast_step": 24,
        "step_type": "instant",
    }
    monkeypatch.setattr(gefs, "codes_new_from_message", lambda payload: object())
    monkeypatch.setattr(gefs, "codes_release", lambda handle: None)
    monkeypatch.setattr(gefs, "_decode_grid", lambda handle: (values, latitude, longitude))
    monkeypatch.setattr(gefs, "_member_metadata", lambda *args: {"requested_member": "c00"})
    monkeypatch.setattr(gefs, "_common_metadata", lambda *args: base | {"level": 850})
    with pytest.raises(ValueError, match="unexpected level"):
        gefs.decode_atmospheric_message(
            b"fixture", member="c00", description="ENS=low-res ctl", spec=spec, lead_hour=24
        )

    monkeypatch.setattr(gefs, "_common_metadata", lambda *args: base | {"forecast_step": 48})
    with pytest.raises(ValueError, match="unexpected forecast timing"):
        gefs.decode_atmospheric_message(
            b"fixture", member="c00", description="ENS=low-res ctl", spec=spec, lead_hour=24
        )


def test_monthly_manifest_requires_counts_lineage_and_training_block():
    digest = hashlib.sha256(b"child").hexdigest()
    manifest = MonthlyCollectionManifest(
        collection_id="phase1c-july-2019-v1",
        period={"month": "2019-07"},
        forecast_provider="NOAA/NCEP GEFSv12 Reforecast",
        observation_provider="IMD",
        expected_initializations=31,
        observed_initializations=31,
        rainfall_products=list(PRODUCT_WINDOWS),
        ensemble_members=list(ENSEMBLE_MEMBERS),
        atmospheric_fields=list(gefs.ATMOSPHERIC_SPECS),
        target_domain={"south": 10, "north": 22, "west": 68, "east": 80},
        context_domain={"south": 5, "north": 30, "west": 55, "east": 95},
        source_bytes={},
        processed_bytes={},
        child_manifest_hashes={"source:2019070100": digest},
        failed_cases=[],
        qc_summary={},
        training_eligible=False,
    )
    assert manifest.expected_initializations == manifest.observed_initializations == 31
    assert manifest.child_manifest_hashes["source:2019070100"] == digest
    with pytest.raises(ValidationError):
        MonthlyCollectionManifest.model_validate(
            manifest.model_dump() | {"training_eligible": True}
        )


def test_failure_accounting_is_visible_and_month_does_not_unblock_science():
    assert summarize_initialization_status(["PASS", "BLOCKED"]) == "PARTIAL"
    assert summarize_initialization_status(["BLOCKED", "BLOCKED"]) == "BLOCKED"
    assert summarize_initialization_status(["FAIL", "FAIL"]) == "FAIL"
    prototype, metadata = load_source_dataset()
    readiness = assess_training_readiness(prototype, metadata)
    assert readiness.ready is False
    assert readiness.mode == "stabilization_blocked"
    assert metadata["training_eligible"] is False
