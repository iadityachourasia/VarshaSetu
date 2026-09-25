from __future__ import annotations

from datetime import date

import numpy as np
import pytest

from backend.app.data.cache import fetch_cached, store_verified_bytes
from backend.app.data.monthly_qc import product_valid_date
from backend.app.data.seasonal_corpus import (
    SeasonAdmission,
    eligibility_index_row,
    raw_control_verification,
    seasonal_admission,
    seasonal_initializations,
    validate_seasonal_zarr_shape,
)


@pytest.mark.parametrize("year", [2017, 2018, 2019])
def test_jjas_initialization_generation_is_complete_and_ordered(year: int) -> None:
    values = seasonal_initializations(year)
    assert len(values) == 122
    assert values[0].date() == date(year, 6, 1)
    assert values[-1].date() == date(year, 9, 30)
    assert len(set(values)) == 122


@pytest.mark.parametrize("year", [2017, 2018, 2019])
def test_september_initialization_preserves_october_day3(year: int) -> None:
    initialization = seasonal_initializations(year)[-1]
    assert product_valid_date(initialization, "day1_24h") == date(year, 10, 1)
    assert product_valid_date(initialization, "day2_24h") == date(year, 10, 2)
    assert product_valid_date(initialization, "day3_24h") == date(year, 10, 3)


def test_seasonal_admission_preserves_monthly_quarantine() -> None:
    assert seasonal_admission(["MONTH_ACCEPTED"] * 4) == SeasonAdmission.SEASON_ACCEPTED
    assert seasonal_admission(["MONTH_ACCEPTED"] * 3 + ["MONTH_ACCEPTED_WITH_QUARANTINED_SAMPLES"]) == SeasonAdmission.SEASON_ACCEPTED_WITH_QUARANTINED_SAMPLES
    assert seasonal_admission(["MONTH_ACCEPTED"] * 3 + ["MONTH_REJECTED"]) == SeasonAdmission.SEASON_REJECTED


def test_eligibility_index_requires_complete_tiers_and_lineage() -> None:
    tiers = {
        "SOURCE_VALID": True, "PAIR_VALID": True,
        "CONTROL_MODEL_ELIGIBLE": True, "FULL_ENSEMBLE_ELIGIBLE": False,
        "REGIME_ELIGIBLE": True, "EXTREME_EVENT_ELIGIBLE": True,
        "FSS_ELIGIBLE": True, "REJECTED": False,
    }
    row = eligibility_index_row(
        initialization="2019-06-11T00:00:00+00:00", product="day2_24h",
        valid_date="2019-06-13", eligibility=tiers,
        reasons=["p03 quarantined"], source_manifest="manifest.json",
    )
    assert row["FULL_ENSEMBLE_ELIGIBLE"] is False
    assert row["CONTROL_MODEL_ELIGIBLE"] is True
    assert "p03" in row["quarantine_reason"]
    with pytest.raises(ValueError, match="lineage"):
        eligibility_index_row(
            initialization="x", product="x", valid_date="x",
            eligibility=tiers, reasons=[], source_manifest="",
        )


def test_frozen_seasonal_zarr_dimensions() -> None:
    validate_seasonal_zarr_shape(
        forecast_shape=(122, 3, 5, 49, 49),
        observation_shape=(122, 3, 49, 49),
        mask_shape=(122, 3, 49, 49),
        atmosphere_shape=(122, 3, 6, 51, 81),
    )
    with pytest.raises(ValueError):
        validate_seasonal_zarr_shape(
            forecast_shape=(121, 3, 5, 49, 49),
            observation_shape=(122, 3, 49, 49),
            mask_shape=(122, 3, 49, 49),
            atmosphere_shape=(122, 3, 6, 51, 81),
        )


def test_raw_baseline_verification_and_contingency() -> None:
    forecast = np.array([[0.0, 70.0], [120.0, 210.0]])
    observation = np.array([[0.0, 80.0], [100.0, 220.0]])
    result = raw_control_verification(forecast, observation, np.ones((2, 2), dtype=bool))
    assert result["rmse_mm"] == pytest.approx(np.sqrt(150.0))
    assert result["mae_mm"] == pytest.approx(10.0)
    assert result["bias_mm"] == pytest.approx(0.0)
    assert result["contingency"]["64.5"]["hits"] == 3


def test_cache_only_rerun_never_calls_network(tmp_path) -> None:
    path = tmp_path / "source.grib2"
    store_verified_bytes(path, url="https://example.invalid/source", byte_range=(0, 3), payload=b"GRIB")

    def forbidden_fetcher(*args):
        raise AssertionError("network called for valid cache")

    result = fetch_cached(
        "https://example.invalid/source", path, byte_range=(0, 3),
        fetcher=forbidden_fetcher,
    )
    assert result.from_cache is True
    assert result.network_bytes == 0
