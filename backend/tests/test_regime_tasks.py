"""Regime-detection task rules (docs/142): AUC against scipy, confusion arithmetic, operating point, C selection, bootstrap determinism and verdict tiers."""

from __future__ import annotations

import numpy as np
import pytest
from scipy.stats import mannwhitneyu

from backend.app.ml import regime_tasks as rt


def test_auc_equals_the_mann_whitney_statistic_including_ties_and_is_nan_for_one_class():
    rng = np.random.default_rng(1)
    label = rng.random(300) < 0.3
    score = np.round(rng.normal(size=300) + label * 0.8, 1)                                        # rounded: many ties
    expected = mannwhitneyu(score[label], score[~label]).statistic / (label.sum() * (~label).sum())
    assert rt.auc(score, label) == pytest.approx(expected, abs=1e-12)
    assert rt.auc(label.astype(float), label) == 1.0 and rt.auc(-label.astype(float), label) == 0.0 and rt.auc(np.zeros(300), label) == 0.5
    assert np.isnan(rt.auc(score, np.zeros(300, dtype=bool))) and np.isnan(rt.auc(score, np.ones(300, dtype=bool)))


def test_confusion_and_balanced_accuracy_are_exact_and_undefined_when_a_class_is_empty():
    c = rt.confusion(np.array([1, 1, 0, 0, 1, 0]), np.array([1, 0, 0, 1, 1, 0]))
    assert (c["tp"], c["fn"], c["fp"], c["tn"]) == (2, 1, 1, 2) and c["balanced_accuracy"] == pytest.approx((2 / 3 + 2 / 3) / 2) and c["precision"] == pytest.approx(2 / 3)
    assert np.isnan(rt.confusion(np.array([1, 0]), np.array([0, 0]))["balanced_accuracy"])


def test_best_threshold_maximises_balanced_accuracy_on_the_data_given():
    score = np.array([0.1, 0.2, 0.3, 0.7, 0.8, 0.9])
    label = np.array([0, 0, 0, 1, 1, 1])
    t = rt.best_threshold(score, label)
    assert t == 0.7 and rt.confusion(score >= t, label)["balanced_accuracy"] == 1.0


def _data(n=900, strength=1.5, seed=3):
    rng = np.random.default_rng(seed)
    X = rng.normal(size=(n, 4))
    y = (X[:, 0] * strength + rng.normal(size=n) > 0.8)
    return X, y


def test_logistic_recovers_a_real_signal_and_select_C_uses_validation_only():
    X, y = _data()
    Xv, yv = _data(seed=9)
    model = rt.fit_logistic(X, y, 1.0)
    assert rt.auc(rt.score_logistic(model, Xv), yv) > 0.8
    best, table = rt.select_C(X, y, Xv, yv)
    assert best in rt.C_GRID and set(table) == {str(c) for c in rt.C_GRID} and table[str(best)] == max(table.values())
    noise = rt.fit_logistic(X, np.random.default_rng(0).random(len(y)) < 0.3, 1.0)
    assert abs(rt.auc(rt.score_logistic(noise, Xv), np.random.default_rng(1).random(len(yv)) < 0.3) - 0.5) < 0.1           # labels unrelated to the features give no skill
    with pytest.raises(ValueError):
        rt.select_C(X, y, Xv, np.zeros(len(yv), dtype=bool))


def test_bootstrap_is_deterministic_and_verdicts_follow_the_intervals_and_the_gate():
    X, y = _data(n=600)
    model = rt.fit_logistic(X, y, 1.0)
    score = rt.score_logistic(model, X)
    baseline = np.random.default_rng(2).random(len(y))
    clusters = [i // 3 for i in range(len(y))]
    predicted = score >= rt.best_threshold(score, y)
    a = rt.bootstrap(score, baseline, y, predicted, clusters, repeats=200, seed=5)
    assert a == rt.bootstrap(score, baseline, y, predicted, clusters, repeats=200, seed=5)
    assert a["auc"]["interval95"][0] <= a["auc"]["point"] <= a["auc"]["interval95"][1]
    v = rt.verdict(a, rt.supported(y))
    assert v["validated"] and v["useful"] and v["tier"] == "USEFUL"
    null = rt.bootstrap(baseline, baseline[::-1], y, baseline > 0.5, clusters, repeats=200, seed=5)
    assert rt.verdict(null, True)["tier"] == "NOT_VALIDATED"
    assert rt.verdict(a, False)["tier"] == "INSUFFICIENT_SUPPORT"
    assert rt.supported(np.array([1] * 30 + [0] * 30)) and not rt.supported(np.array([1] * 29 + [0] * 100))
