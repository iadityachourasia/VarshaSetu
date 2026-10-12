"""Leakage and threshold-scale regression checks for the v2 research head."""

import numpy as np
import pytest

from backend.app.ml.nationwide_probability_v2 import apply_lead_calibration, frequency_cutoff, validate_head_folds


def test_head_folds_partition_held_cases_and_reject_direct_overlap():
    folds = [{"train": ["20230602_day1"], "held": ["20230601_day1"]},
             {"train": ["20230601_day1"], "held": ["20230602_day1"]}]
    validate_head_folds(folds, ["20230601_day1", "20230602_day1"])
    with pytest.raises(ValueError, match="held cases"):
        validate_head_folds([{"train": ["20230601_day1"], "held": ["20230601_day1"]}, folds[1]],
                            ["20230601_day1", "20230602_day1"])


def test_cutoff_uses_calibrated_coherent_scale():
    raw = np.array([0.04, 0.10, 0.20, 0.40])
    target = np.array([0, 0, 0, 1])
    calibrated = apply_lead_calibration(raw, np.array([24, 24, 24, 24]),
                                        {"24": {"method": "isotonic", "x": [0, 1], "y": [0, 0.5]}})
    assert np.allclose(calibrated, raw / 2)
    assert frequency_cutoff(calibrated, target) == pytest.approx(0.11)
    assert frequency_cutoff(raw, target) == pytest.approx(0.21)


def test_invalid_probabilities_and_empty_event_population_fail_closed():
    with pytest.raises(ValueError):
        apply_lead_calibration(np.array([1.1]), np.array([24]), {"24": {"method": "identity"}})
    with pytest.raises(ValueError):
        frequency_cutoff(np.array([0.2, 0.3]), np.array([0, 0]))
