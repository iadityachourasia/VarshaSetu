"""Scientific invariants of the development-only multi-label residual method."""

import numpy as np
import pytest

from backend.app.ml import regime_residual as rr


def test_five_detector_heads_are_independent_and_scores_need_not_sum_to_one():
    rng = np.random.default_rng(26080)
    X = rng.normal(size=(120, 17))
    Y = np.column_stack([(X[:, j] > 0).astype(int) for j in range(5)])
    bundle = rr.fit_detectors(X, Y)
    assert bundle["calibration_status"] == "UNCALIBRATED_LOGISTIC_OUTPUT"
    scores = rr.score_detectors(bundle, X)
    assert scores.shape == (120, 5) and np.all((0 <= scores) & (scores <= 1))
    assert not np.allclose(scores.sum(axis=1), 1)
    with pytest.raises(ValueError, match="insufficient"):
        rr.fit_detectors(X, np.zeros_like(Y))


def test_soft_residual_uses_case_scores_and_shrinks_to_a_global_fallback():
    cases, cells = 80, 4
    counts = np.full(cases, cells)
    X = np.zeros((cases * cells, 22), dtype=np.float32)
    X[:, 0] = np.tile([5, 10, 15, 20], cases)
    X[:, 19] = np.repeat(np.linspace(10, 22, cases), cells)
    X[:, 20] = 75
    X[:, 21] = 24
    base = X[:, 0] * 0.8
    scores = np.zeros((cases, len(rr.TASKS)))
    scores[:40, 0], scores[40:, 0] = 0.9, 0.1
    y = base + np.repeat(np.where(np.arange(cases) < 40, 8, 1), cells)
    fitted = rr.fit_correction(base, X, y, scores, counts)
    assert fitted["specialists"]["ACTIVE"]["status"] == "FITTED"
    assert all(fitted["specialists"][name]["status"].startswith("FALLBACK") for name in rr.TASKS[1:])
    predicted = rr.predict_correction(fitted, base, X, scores, counts)
    assert np.isfinite(predicted["regime_soft_residual"]).all() and np.all(predicted["regime_soft_residual"] >= 0)
    assert not np.array_equal(predicted["global_residual"], predicted["regime_soft_residual"])
    zero_scores = rr.predict_correction(fitted, base, X, np.zeros_like(scores), counts)
    assert np.array_equal(zero_scores["global_residual"], zero_scores["regime_soft_residual"])
    with pytest.raises(ValueError, match="align"):
        rr.predict_correction(fitted, base, X, scores[:-1], counts)
