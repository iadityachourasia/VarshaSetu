"""Nested split, calibration, and persisted threshold guards for v3 research."""

from datetime import date, timedelta

import numpy as np
import pytest

from backend.app.ml.nationwide_probability_v3 import (
    apply_platt, fit_platt, frequency_cutoff_persisted, validate_nested_folds,
)
from backend.app.ml.nationwide_research import date_block_folds
from scripts import nationwide_probability_v3 as v3


def test_nested_date_folds_keep_every_held_case_out_of_both_fit_levels() -> None:
    cases = [(date(2023, 6, 1) + timedelta(days=day)).strftime("%Y%m%d") + "_day1"
             for day in range(60)]
    outer = date_block_folds(cases, folds=3, embargo_days=3)
    inner = {str(fold["fold"]): date_block_folds(fold["train"], folds=2, embargo_days=3)
             for fold in outer}
    validate_nested_folds(cases, outer, inner, embargo_days=3)
    bad = {**inner, "0": [{**inner["0"][0], "train": inner["0"][0]["train"] + inner["0"][0]["held"][:1]},
                           inner["0"][1]]}
    with pytest.raises(ValueError, match="overlap"):
        validate_nested_folds(cases, outer, bad, embargo_days=3)


def test_platt_map_is_finite_monotone_and_support_checked() -> None:
    leads = np.repeat([24, 48, 72], 200)
    raw = np.tile(np.linspace(0.002, 0.8, 200), 3)
    target = np.tile(np.r_[np.zeros(140), np.ones(60)], 3)
    calibration = fit_platt(raw, target, leads)
    mapped = apply_platt(raw, leads, calibration)
    assert np.isfinite(mapped).all()
    assert np.all((mapped >= 0) & (mapped <= 1))
    for lead in (24, 48, 72):
        assert np.all(np.diff(mapped[leads == lead]) >= 0)
        assert calibration[str(lead)]["events"] == 60
    with pytest.raises(ValueError, match="insufficient calibration events"):
        fit_platt(raw, np.tile(np.r_[np.zeros(180), np.ones(20)], 3), leads)


def test_cutoff_is_chosen_on_persisted_float32_bytes() -> None:
    probabilities = np.array([0.01, 0.03, 0.08, 0.08, 0.2], dtype=np.float64)
    target = np.array([0, 0, 0, 0, 1])
    cutoff = frequency_cutoff_persisted(probabilities, target)
    values = probabilities.astype(np.float32).astype(np.float64)
    candidates = np.arange(0.01, 0.501, 0.01)
    assert cutoff == pytest.approx(min(candidates, key=lambda t: (abs(np.count_nonzero(values >= t) - 1), t)))
    with pytest.raises(ValueError):
        frequency_cutoff_persisted(np.array([0.1, np.nan]), np.array([0, 1]))


def test_research_recipe_is_fixed_and_separate_from_frozen_v2() -> None:
    assert v3.MODEL_SPEC["device"] == "cpu"
    assert v3.MODEL_SPEC["n_jobs"] == 4
    assert v3.PROTOCOL != v3.v2.PROTOCOL
    assert v3.OUT != v3.v2.OUT
