"""Observation-based active/break labels and their scoring (docs/136): pure-function tests on synthetic data."""

from __future__ import annotations

from datetime import date

import numpy as np
import pytest

from backend.app.ml import regime_validation as rv

CLASSES = ("ACTIVE_MONSOON", "BREAK_WEAK_MONSOON", "LOW_DEPRESSION_INFLUENCED")


def test_area_mean_uses_valid_cells_in_the_box_with_cosine_weights():
    lat, lon = np.array([10.0, 20.0, 25.0, 60.0]), np.array([70.0, 80.0, 95.0])
    rain = np.full((2, 4, 3), np.nan)
    rain[0, 1, 0], rain[0, 2, 1] = 10.0, 30.0                       # both inside the box (lat 18-28, lon 65-88)
    rain[0, 0, 0] = 500.0                                           # outside the box (lat 10)
    rain[0, 1, 2] = 400.0                                           # outside the box (lon 95)
    rain[1, 1, 0] = -999.0                                          # fill value: not valid, so the day has no valid cell
    series = rv.area_mean_series(rain, lat, lon)
    w1, w2 = np.cos(np.deg2rad(20.0)), np.cos(np.deg2rad(25.0))
    assert series[0] == pytest.approx((10.0 * w1 + 30.0 * w2) / (w1 + w2)) and np.isnan(series[1])


def test_the_season_has_122_days_and_never_29_february():
    days = rv.season_days()
    assert len(days) == 122 and days[0] == (6, 1) and days[-1] == (9, 30) and (2, 29) not in days


def test_spell_detection_needs_three_consecutive_days_inclusive_threshold_and_nan_breaks_runs():
    z = np.array([1.2, 1.5, 1.0, 0.3, 1.1, 1.4, 0.2, np.nan, 1.5, 1.5, np.nan, 1.5, 1.5, 1.5])
    mask = rv.spell_mask(z, positive=True)
    assert mask.tolist() == [True, True, True, False, False, False, False, False, False, False, False, True, True, True]
    assert rv.spell_mask(np.array([-1.0, -1.0, -1.0, 0.0]), positive=False).tolist() == [True, True, True, False]
    assert not rv.spell_mask(np.array([-0.99, -2.0, -2.0, -0.5]), positive=False).any()
    assert rv.spell_mask(np.array([1.0, 1.0, 1.0]), positive=True).all()                       # a run that ends at the end of the series still counts


def _z_with(spells: dict[tuple[int, int], float]) -> np.ndarray:
    calendar = rv.season_days()
    z = np.zeros(len(calendar))
    for (month, day), value in spells.items():
        z[calendar.index((month, day))] = value
    return z


def test_labels_cover_july_and_august_only_and_mark_spell_days():
    z = _z_with({(7, 10): 1.4, (7, 11): 1.2, (7, 12): 1.1, (8, 5): -1.3, (8, 6): -1.1, (8, 7): -1.6, (6, 20): 2.0, (6, 21): 2.0, (6, 22): 2.0, (9, 3): -2.0, (9, 4): -2.0, (9, 5): -2.0})
    labels = rv.label_days(z, 2024)
    assert labels[date(2024, 7, 11)] == "ACTIVE" and labels[date(2024, 8, 6)] == "BREAK" and labels[date(2024, 7, 20)] == "NEUTRAL"
    assert date(2024, 6, 21) not in labels and date(2024, 9, 4) not in labels                 # June and September spells exist but are never labelled
    assert len(labels) == 62
    assert list(labels.values()).count("ACTIVE") == 3 and list(labels.values()).count("BREAK") == 3


def test_the_climatology_is_smoothed_pools_one_sigma_and_rejects_incomplete_years():
    rng = np.random.default_rng(3)
    calendar = rv.season_days()
    per_year = {y: {day: 10.0 + 5.0 * np.sin(i / 20.0) + rng.normal(0, 2.0) for i, day in enumerate(calendar)} for y in range(1981, 2001)}
    mean, sigma, info = rv.climatology(per_year)
    assert mean.shape == (122,) and 1.0 < sigma < 4.0 and info["years"] == list(range(1981, 2001)) and info["window_days"] == 62
    raw = np.array([[per_year[y][d] for d in calendar] for y in sorted(per_year)]).mean(axis=0)
    assert np.std(np.diff(mean)) < np.std(np.diff(raw))                                       # smoothing reduces day-to-day jitter
    broken = {y: dict(v) for y, v in per_year.items()}
    del broken[1990][(7, 4)]
    with pytest.raises(ValueError):
        rv.climatology(broken)


def test_valid_date_pairs_day_one_with_the_next_calendar_day():
    assert rv.valid_date(date(2025, 7, 14), 1) == date(2025, 7, 15) and rv.valid_date(date(2025, 7, 14), 3) == date(2025, 7, 17)


def test_binary_metrics_perfect_trivial_and_undefined():
    obs = np.array([1, 1, 0, 0, 0, 0], dtype=bool)
    perfect = rv.binary_metrics(obs, obs)
    assert perfect["balanced_accuracy"] == 1.0 and perfect["f1"] == 1.0 and perfect["recall"] == 1.0
    never = rv.binary_metrics(np.zeros(6, dtype=bool), obs)
    assert never["balanced_accuracy"] == 0.5 and never["recall"] == 0.0 and never["precision"] is None and never["f1"] is None
    always = rv.binary_metrics(np.ones(6, dtype=bool), obs)
    assert always["balanced_accuracy"] == 0.5 and always["specificity"] == 0.0
    nothing_observed = rv.binary_metrics(np.array([True, False]), np.array([False, False]))
    assert nothing_observed["recall"] is None and nothing_observed["balanced_accuracy"] is None


def test_confusion_and_tasks_use_the_declared_class_mapping():
    predicted = np.array([0, 1, 2, 0, 1])
    observed = ["ACTIVE", "BREAK", "NEUTRAL", "NEUTRAL", "ACTIVE"]
    table = rv.confusion(predicted, observed, CLASSES)
    assert table["ACTIVE_MONSOON"] == {"ACTIVE": 1, "BREAK": 0, "NEUTRAL": 1} and table["BREAK_WEAK_MONSOON"] == {"ACTIVE": 1, "BREAK": 1, "NEUTRAL": 0}
    assert table["LOW_DEPRESSION_INFLUENCED"] == {"ACTIVE": 0, "BREAK": 0, "NEUTRAL": 1}
    tasks = rv.task_arrays(predicted, observed, CLASSES)
    assert tasks["active_vs_not_active"][0].tolist() == [True, False, False, True, False] and tasks["active_vs_not_active"][1].tolist() == [True, False, False, False, True]
    assert tasks["break_vs_not_break"][0].tolist() == [False, True, False, False, True] and tasks["break_vs_not_break"][1].tolist() == [False, True, False, False, False]


def test_bootstrap_is_deterministic_clustered_and_ordered():
    rng = np.random.default_rng(5)
    obs = rng.random(300) < 0.3
    pred = np.where(rng.random(300) < 0.7, obs, ~obs)
    clusters = [i // 3 for i in range(300)]
    a = rv.cluster_bootstrap_balanced_accuracy(pred, obs, clusters, repeats=300, seed=1)
    b = rv.cluster_bootstrap_balanced_accuracy(pred, obs, clusters, repeats=300, seed=1)
    assert a == b and a["interval95"][0] < rv.binary_metrics(pred, obs)["balanced_accuracy"] < a["interval95"][1]


def test_the_support_gate_needs_enough_cases_on_both_sides():
    assert rv.supported({"ACTIVE": 40, "BREAK": 29, "NEUTRAL": 100}) == {"ACTIVE": True, "BREAK": False}
    assert rv.supported({"ACTIVE": 30, "BREAK": 30, "NEUTRAL": 0}) == {"ACTIVE": True, "BREAK": True}
    assert rv.supported({"ACTIVE": 0, "BREAK": 0, "NEUTRAL": 50}) == {"ACTIVE": False, "BREAK": False}
