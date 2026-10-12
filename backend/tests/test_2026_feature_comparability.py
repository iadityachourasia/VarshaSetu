"""Common-footprint forecast feature comparison is descriptive and fail-closed."""

from __future__ import annotations

import json
import numpy as np
import pytest

from scripts import compare_2023_2026_forecast_features as study


@pytest.mark.skipif(not (study.TRAIN / "X.npy").exists(), reason="ignored local 2023 training features absent")
def test_protocol_is_frozen_before_distribution_comparison():
    base, digest = study._protocol()
    assert len(digest) == 64
    assert base["source_track"] == "B_OPERATIONAL_GEFS"
    assert "NO_GEFS_VERSION_CLEARANCE" in base["research_status"]


def test_all_dynamic_features_are_described_without_static_coordinates():
    old = np.array([[0., 10., 69.], [1., 10., 69.], [2., 10., 69.], [3., 10., 69.]])
    new = np.array([[1., 10., 69.], [2., 10., 69.], [3., 10., 69.], [4., 10., 69.]])
    result = study.compare_stratum(old, new, ("forecast_mslp", "latitude_deg", "longitude_deg"))
    assert set(result) == {"forecast_mslp"}
    assert result["forecast_mslp"]["forecast_minus_training_median"] == pytest.approx(1)
    assert result["forecast_mslp"]["forecast_fraction_outside_training_p001_p999"] == pytest.approx(.5)


def test_comparison_rejects_nonfinite_or_misaligned_layout():
    old = np.array([[0., 1.], [1., 1.]])
    with pytest.raises(ValueError, match="Feature layout"):
        study.compare_stratum(old, old[:, :1], ("rain", "lead_hours"))
    bad = old.copy()
    bad[0, 0] = np.nan
    with pytest.raises(ValueError, match="nonfinite"):
        study.compare_stratum(old, bad, ("rain", "lead_hours"))


@pytest.mark.skipif(not study.OUT.exists(), reason="local exploratory comparison result absent")
def test_sealed_result_is_complete_and_research_only():
    assert study._receipt(study.OUT) == "202f153ec16c75ef44375dbac4d8aefa2f4eef6156a3b411f84cde84a9891a80"
    report = json.loads(study.OUT.read_text(encoding="utf-8"))
    assert report["status"] == "EXPLORATORY_FORECAST_FEATURE_COMPARISON_NO_VERSION_CLEARANCE_NO_PROMOTION"
    assert report["observation_values_read"] is False and report["model_fitted"] is False
    assert (report["training_cases_jjas"], report["forecast_cases_jjas"]) == (192, 213)
    assert len(report["strata"]) == 12
    assert all(row["common_grid_cells"] == 1301 and len(row["features"]) == 19 for row in report["strata"].values())
