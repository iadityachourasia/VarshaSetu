"""Forecast-time coastal/orographic forcing regime (docs/137): pure-function tests on synthetic data."""

from __future__ import annotations

import numpy as np
import pytest

from backend.app.ml import coastal_regime as cr


def test_zone_index_is_the_mean_over_the_zone_and_nan_if_a_zone_cell_is_missing():
    field = np.arange(2401, dtype=float)
    mask = np.zeros(2401, dtype=bool)
    mask[[10, 20, 30]] = True
    assert cr.zone_index(field, mask) == 20.0
    bad = field.copy()
    bad[20] = np.nan
    assert np.isnan(cr.zone_index(bad, mask))
    bad2 = field.copy()
    bad2[5] = np.nan                                                    # a missing cell outside the zone does not matter
    assert cr.zone_index(bad2, mask) == 20.0
    assert np.isnan(cr.zone_index(field, np.zeros(2401, dtype=bool)))


def test_cut_points_are_training_terciles_and_degenerate_ones_are_flagged():
    values = np.arange(300, dtype=float)
    cuts = cr.cut_points(values)
    assert cuts["q33"] == pytest.approx(np.quantile(values, 1 / 3)) and cuts["q67"] == pytest.approx(np.quantile(values, 2 / 3)) and cuts["training_cases"] == 300 and cuts["degenerate"] is False
    assert cr.cut_points(np.zeros(300))["degenerate"] is True
    with pytest.raises(ValueError):
        cr.cut_points(np.arange(50, dtype=float))                      # too few training cases


def test_classification_boundaries_and_undefined():
    cuts = {"q33": 10.0, "q67": 20.0}
    assert [cr.classify(v, cuts) for v in (9.99, 10.0, 19.99, 20.0, 99.0)] == [0, 1, 1, 2, 2]
    assert cr.classify(float("nan"), cuts) is None


def test_percentile_is_a_rank_against_the_training_distribution():
    training = np.arange(1, 101, dtype=float)
    assert cr.percentile(50.0, training) == 0.5 and cr.percentile(0.0, training) == 0.0 and cr.percentile(1000.0, training) == 1.0 and cr.percentile(float("nan"), training) is None


def _population(n=300, strength=1.0, seed=2):
    rng = np.random.default_rng(seed)
    index = rng.normal(0, 1, n)
    valid = np.full(n, 109)
    rate = 1 / (1 + np.exp(-(strength * index - 1.5)))
    heavy = rng.binomial(valid, rate * 0.4)
    return index, valid, heavy


def test_group_statistics_partition_the_events_and_the_gate_needs_every_class():
    index, valid, heavy = _population()
    cuts = cr.cut_points(index)
    classes = np.array([cr.classify(v, cuts) for v in index])
    groups = cr.group_statistics(classes, heavy, valid)
    assert sum(g["cases"] for g in groups.values()) == len(index) and sum(g["heavy_event_pairs"] for g in groups.values()) == int(heavy.sum())
    assert sum(g["share_of_all_heavy_event_pairs"] for g in groups.values()) == pytest.approx(1.0)
    assert cr.supported(groups) is True
    thin = cr.group_statistics(np.array([0] * 40 + [2] * 40), np.ones(80, dtype=int), np.full(80, 109))
    assert cr.supported(thin) is False                                   # an empty middle class fails the gate


def test_a_forcing_index_that_drives_heavy_rain_is_detected_and_a_noise_index_is_not():
    index, valid, heavy = _population(n=400, strength=2.0)
    cuts = cr.cut_points(index)
    classes = np.array([cr.classify(v, cuts) for v in index])
    boot = cr.bootstrap(index, classes, heavy, valid, repeats=300, seed=1)
    assert boot["strong_minus_weak_heavy_fraction"]["excludes_zero"] and boot["strong_minus_weak_heavy_fraction"]["point"] > 0 and boot["spearman"]["point"] > 0.2
    rng = np.random.default_rng(9)
    noise_heavy = rng.binomial(valid, 0.05)
    null = cr.bootstrap(index, classes, noise_heavy, valid, repeats=300, seed=1)
    low, high = null["strong_minus_weak_heavy_fraction"]["interval95"]
    assert low <= 0 <= high


def test_bootstrap_is_deterministic_and_undefined_when_no_event_varies():
    index, valid, heavy = _population()
    cuts = cr.cut_points(index)
    classes = np.array([cr.classify(v, cuts) for v in index])
    assert cr.bootstrap(index, classes, heavy, valid, repeats=200, seed=3) == cr.bootstrap(index, classes, heavy, valid, repeats=200, seed=3)
    none = cr.bootstrap(index, classes, np.zeros_like(heavy), valid, repeats=100, seed=3)
    assert none["spearman"]["status"] == "undefined" and none["strong_minus_weak_heavy_fraction"]["point"] == 0.0
