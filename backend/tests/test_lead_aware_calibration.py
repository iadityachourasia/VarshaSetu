"""Forecast-lead recalibration has explicit inputs and reproducible artifacts."""

import numpy as np
import pytest

from backend.app.ml.lead_aware_calibration import apply_recalibrator, design_matrix, fit_recalibrator


def test_design_matrix_uses_only_base_score_and_known_lead():
    p = np.array([0, 0.2, 1.0])
    lead = np.array([1, 2, 3])
    global_X = design_matrix(p, lead, lead_aware=False)
    aware_X = design_matrix(p, lead, lead_aware=True)
    assert global_X.shape == (3, 1) and aware_X.shape == (3, 3)
    np.testing.assert_array_equal(aware_X[:, 1:], [[0, 0], [1, 0], [0, 1]])
    assert np.isfinite(aware_X).all()


def test_fitted_calibrator_predicts_valid_probability_and_lead_effect():
    lead = np.repeat([1, 2, 3], 100)
    p = np.full(300, 0.2)
    y = np.zeros(300, dtype=np.uint8)
    y[:10] = 1
    y[100:150] = 1
    y[200:280] = 1
    model = fit_recalibrator(p, lead, y, lead_aware=True)
    assert model == fit_recalibrator(p, lead, y, lead_aware=True)
    predicted = apply_recalibrator(np.array([0.2, 0.2, 0.2]), np.array([1, 2, 3]), model)
    assert model["fit_events"] == 140 and model["feature_names"] == ["base_logit", "day2_offset", "day3_offset"]
    assert np.all((predicted > 0) & (predicted < 1))
    assert predicted[0] < predicted[1] < predicted[2]


def test_invalid_forecast_scores_and_artifacts_refuse():
    with pytest.raises(ValueError):
        design_matrix(np.array([np.nan]), np.array([1]), lead_aware=True)
    with pytest.raises(ValueError):
        design_matrix(np.array([0.2]), np.array([4]), lead_aware=True)
    with pytest.raises(ValueError):
        apply_recalibrator(np.array([0.2]), np.array([1]), {"format": "unknown"})
