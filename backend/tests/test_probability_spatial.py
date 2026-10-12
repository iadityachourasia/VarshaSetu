"""Aligned 2-D warning FSS, edge and missing-cell guards."""

import numpy as np
import pytest

from backend.app.ml.probability_spatial import fss_from_sums, warning_fss_components


def test_perfect_and_displaced_events_use_real_two_dimensional_neighborhoods() -> None:
    p = np.zeros((5, 5))
    rain = np.zeros((5, 5))
    p[2, 2] = 0.6
    rain[2, 2] = 120.0
    mask = np.ones((5, 5), dtype=bool)
    perfect = warning_fss_components(p, rain, mask, probability_cutoff=0.05,
                                     rain_threshold_mm=115.6, size=3)
    assert perfect["paired_cells"] == perfect["eligible_centers"] == 25
    assert perfect["hits"] == 1
    assert fss_from_sums(perfect["numerator"], perfect["denominator"]) == pytest.approx(1)
    shifted = np.roll(p, 1, axis=1)
    exact = warning_fss_components(shifted, rain, mask, probability_cutoff=0.05,
                                   rain_threshold_mm=115.6, size=1)
    neighborhood = warning_fss_components(shifted, rain, mask, probability_cutoff=0.05,
                                          rain_threshold_mm=115.6, size=3)
    assert fss_from_sums(exact["numerator"], exact["denominator"]) == pytest.approx(0)
    assert 0 < fss_from_sums(neighborhood["numerator"], neighborhood["denominator"]) < 1


def test_missing_cells_are_excluded_and_not_treated_as_zero_events() -> None:
    p = np.full((3, 3), np.nan)
    rain = np.full((3, 3), np.nan)
    p[1, 1] = 0.5
    rain[1, 1] = 120
    mask = np.zeros((3, 3), dtype=bool)
    mask[1, 1] = True
    result = warning_fss_components(p, rain, mask, probability_cutoff=0.05,
                                    rain_threshold_mm=115.6, size=1)
    assert result["paired_cells"] == result["eligible_centers"] == 1
    assert fss_from_sums(result["numerator"], result["denominator"]) == pytest.approx(1)
    empty = warning_fss_components(np.zeros((3, 3)), np.zeros((3, 3)),
                                   np.ones((3, 3), dtype=bool), probability_cutoff=0.05,
                                   rain_threshold_mm=115.6, size=3)
    assert fss_from_sums(empty["numerator"], empty["denominator"]) is None
    with pytest.raises(ValueError, match="invalid probability or reference"):
        warning_fss_components(p, rain, np.ones((3, 3), dtype=bool),
                               probability_cutoff=0.05, rain_threshold_mm=115.6, size=1)


def test_single_cell_fss_matches_contingency_identity() -> None:
    p = np.array([[0.2, 0.0], [0.3, 0.0]])
    rain = np.array([[120.0, 0.0], [0.0, 120.0]])
    result = warning_fss_components(p, rain, np.ones((2, 2), dtype=bool),
                                    probability_cutoff=0.05, rain_threshold_mm=115.6, size=1)
    expected = 2 * result["hits"] / (result["forecast_events"] + result["observed_events"])
    assert fss_from_sums(result["numerator"], result["denominator"]) == pytest.approx(expected)
