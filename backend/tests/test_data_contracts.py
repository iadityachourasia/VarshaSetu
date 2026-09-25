import json
from datetime import date, datetime, timezone
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.data.contracts import (
    AccumulatedPrecipitationMessage,
    BoundingBox,
    ForecastGridRecord,
    GridDefinition,
    ObservationGridRecord,
    SourceFileManifest,
    imd_daily_window,
    reconstruct_three_hour_increments,
    validate_pairing_window,
)


UTC = timezone.utc


def target_grid() -> GridDefinition:
    return GridDefinition(
        grid_id="imd-025-western-india-v1",
        crs="EPSG:4326",
        latitude_spacing_degrees=0.25,
        longitude_spacing_degrees=0.25,
        bounds=BoundingBox(south=10, north=22, west=68, east=80),
        latitude_order="ascending",
        longitude_convention="0_to_360",
    )


def valid_forecast_payload() -> dict:
    return {
        "source": "NOAA GEFSv12 Reforecast",
        "source_documentation_url": "https://registry.opendata.aws/noaa-gefs-reforecast/",
        "model_name": "GEFS",
        "model_version": "v12 reforecast",
        "ensemble_member": "c00",
        "initialization_time_utc": datetime(2000, 7, 1, tzinfo=UTC),
        "valid_time_utc": datetime(2000, 7, 2, 3, tzinfo=UTC),
        "lead_hours": 27,
        "accumulation_start_utc": datetime(2000, 7, 1, 3, tzinfo=UTC),
        "accumulation_end_utc": datetime(2000, 7, 2, 3, tzinfo=UTC),
        "accumulation_hours": 24,
        "grid_definition": target_grid(),
        "variable": "apcp_sfc",
        "level": "surface",
        "units": "mm",
        "available_at_issue_time": True,
    }


def test_forecast_contract_accepts_exact_day_one_window():
    record = ForecastGridRecord.model_validate(valid_forecast_payload())
    assert record.lead_hours == 27
    assert record.accumulation_hours == 24


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("lead_hours", 24, "lead_hours must equal"),
        ("available_at_issue_time", False, "available at issue time"),
        ("units", "mystery", "unknown units"),
    ],
)
def test_forecast_contract_rejects_ambiguous_or_unsafe_metadata(field, value, message):
    payload = valid_forecast_payload()
    payload[field] = value
    with pytest.raises(ValidationError, match=message):
        ForecastGridRecord.model_validate(payload)


def test_forecast_contract_rejects_naive_timestamp():
    payload = valid_forecast_payload()
    payload["valid_time_utc"] = datetime(2000, 7, 2, 3)
    with pytest.raises(ValidationError, match="timezone-aware UTC"):
        ForecastGridRecord.model_validate(payload)


def test_imd_daily_window_and_observation_contract_are_exactly_24_hours():
    start, end = imd_daily_window(date(2000, 7, 2))
    assert start == datetime(2000, 7, 1, 3, tzinfo=UTC)
    assert end == datetime(2000, 7, 2, 3, tzinfo=UTC)

    record = ObservationGridRecord(
        source="India Meteorological Department",
        source_documentation_url="https://imdpune.gov.in/",
        product="0.25 degree daily gridded rainfall",
        version="file-declared-version-required-at-acquisition",
        valid_date=date(2000, 7, 2),
        accumulation_start_utc=start,
        accumulation_end_utc=end,
        accumulation_hours=24,
        grid_definition=target_grid(),
        rainfall_units="mm",
        quality_status="source QC; local missing-value scan pending",
        missing_value_policy="read NetCDF _FillValue/missing_value; reject undocumented sentinels",
    )
    assert record.accumulation_hours == 24
    validate_pairing_window(ForecastGridRecord.model_validate(valid_forecast_payload()), record)


def test_pairing_rejects_shifted_observation_window():
    start, end = imd_daily_window(date(2000, 7, 3))
    shifted = ObservationGridRecord(
        source="India Meteorological Department",
        source_documentation_url="https://imdpune.gov.in/",
        product="0.25 degree daily gridded rainfall",
        version="file-declared-version-required-at-acquisition",
        valid_date=date(2000, 7, 3),
        accumulation_start_utc=start,
        accumulation_end_utc=end,
        accumulation_hours=24,
        grid_definition=target_grid(),
        rainfall_units="mm",
        quality_status="source QC; local missing-value scan pending",
        missing_value_policy="read file attributes",
    )
    with pytest.raises(ValueError, match="do not match exactly"):
        validate_pairing_window(ForecastGridRecord.model_validate(valid_forecast_payload()), shifted)


def test_gefs_mixed_step_ranges_reconstruct_three_hour_amounts():
    messages = [
        AccumulatedPrecipitationMessage(start_hour=0, end_hour=3, value_mm=1.0),
        AccumulatedPrecipitationMessage(start_hour=0, end_hour=6, value_mm=3.5),
        AccumulatedPrecipitationMessage(start_hour=6, end_hour=9, value_mm=4.0),
        AccumulatedPrecipitationMessage(start_hour=6, end_hour=12, value_mm=10.0),
    ]
    assert reconstruct_three_hour_increments(
        messages, window_start_hour=0, window_end_hour=12
    ) == [1.0, 2.5, 4.0, 6.0]


def test_gefs_reconstruction_fails_on_missing_or_negative_increment():
    with pytest.raises(ValueError, match="missing precipitation messages"):
        reconstruct_three_hour_increments(
            [AccumulatedPrecipitationMessage(start_hour=0, end_hour=3, value_mm=1.0)],
            window_start_hour=0,
            window_end_hour=6,
        )

    with pytest.raises(ValueError, match="negative reconstructed precipitation"):
        reconstruct_three_hour_increments(
            [
                AccumulatedPrecipitationMessage(start_hour=0, end_hour=3, value_mm=3.0),
                AccumulatedPrecipitationMessage(start_hour=0, end_hour=6, value_mm=2.0),
            ],
            window_start_hour=0,
            window_end_hour=6,
        )


def test_source_manifest_requires_hash_and_forecast_identity():
    base = {
        "dataset_id": "noaa-gefsv12-reforecast-apcp-sample",
        "provider": "NOAA/NCEP",
        "source_url": "https://noaa-gefs-retrospective.s3.amazonaws.com/",
        "retrieval_date": date(2026, 9, 19),
        "filename": "apcp_sfc_2000010100_c00.grib2.idx",
        "sha256": "a" * 64,
        "byte_size": 5960,
        "data_type": "forecast",
        "product": "GEFSv12 Reforecast",
        "version": "v12",
        "model_name": "GEFS",
        "initialization_time_utc": datetime(2000, 1, 1, tzinfo=UTC),
        "lead_hours": [3, 6],
        "variable": "apcp_sfc",
        "level": "surface",
        "units": "kg m-2",
        "spatial_resolution": "0.25 degree for days 1-10",
        "temporal_resolution": "3-hour forecast messages for days 1-10",
        "license_or_terms": "NOAA open-data terms; attribution requested",
        "request_or_subset": "official index sidecar; no scientific data subset acquired",
        "provenance_status": "access-probe-only-not-training-eligible",
    }
    assert SourceFileManifest.model_validate(base).data_type.value == "forecast"

    bad_hash = base | {"sha256": "not-a-hash"}
    with pytest.raises(ValidationError, match="64 hexadecimal"):
        SourceFileManifest.model_validate(bad_hash)

    missing_identity = base | {"model_name": None}
    with pytest.raises(ValidationError, match="forecast manifests require"):
        SourceFileManifest.model_validate(missing_identity)


def test_architecture_manifest_cannot_be_mistaken_for_training_readiness():
    repository_root = Path(__file__).resolve().parents[2]
    manifest = json.loads(
        (repository_root / "data/manifests/authoritative_data_architecture.v1.json").read_text(
            encoding="utf-8"
        )
    )
    assert manifest["training_eligible"] is False
    assert manifest["scientific_gate"] == "BLOCKED"
    assert manifest["readiness_effect"] == "none"
    assert manifest["official_access_probe"]["status"] == (
        "first-grib-message-decoded-and-locally-subset-no-files-retained"
    )
