"""Reforecast heavy-rain study rules (docs/142): grid, validation-only selection, sealed-test decision, regime routing."""

from __future__ import annotations

import numpy as np
import pytest

from backend.app.ml import reforecast_study as rs


def _metrics(rmse=10.0, bias=0.1, h_csi=0.1, h_fb=0.9, v_csi=0.03, v_fb=0.5):
    return {"rmse_mm": rmse, "bias_mm": bias, "heavy": {"csi": h_csi, "frequency_bias": h_fb}, "very_heavy": {"csi": v_csi, "frequency_bias": v_fb}}


RAW = _metrics(rmse=11.0, bias=0.0, h_csi=0.07, h_fb=0.3, v_csi=0.02, v_fb=0.2)


def test_grid_is_the_frozen_24_and_years_never_overlap():
    grid = rs.configurations()
    assert len(grid) == 24 and grid[0] == {"objective": "reg:squarederror", "cap": None, "max_depth": 4, "n_estimators": 200} and grid[-1]["cap"] == 8.0
    assert len({tuple(sorted(c.items(), key=str)) for c in grid}) == 24
    assert not set(rs.TRAIN_YEARS) & set(rs.VALIDATION_YEARS) and not set(rs.SEALED_YEARS) & (set(rs.TRAIN_YEARS) | set(rs.VALIDATION_YEARS))
    assert rs.TRAIN_YEARS[-1] + 1 == rs.VALIDATION_YEARS[0] and rs.VALIDATION_YEARS[-1] + 1 == rs.SEALED_YEARS[0]


def test_row_weights_use_the_cap_and_never_negative_targets():
    y = np.array([0.0, 64.5, 300.0])
    assert rs.row_weights(y, None) is None
    assert rs.row_weights(y, 4.0).tolist() == pytest.approx([1.0, 2.0, 4.0]) and rs.row_weights(y, 8.0)[2] == 5.6511627906976745
    with pytest.raises(ValueError):
        rs.row_weights(np.array([-1.0]), 4.0)


def test_eligibility_requires_every_guardrail_and_treats_undefined_as_failing():
    assert rs.eligible(_metrics(), RAW)
    assert not rs.eligible(_metrics(rmse=11.5), RAW)                  # worse RMSE than Raw
    assert not rs.eligible(_metrics(h_csi=0.05), RAW)                 # heavy CSI below Raw
    assert not rs.eligible(_metrics(bias=2.0), RAW)
    assert not rs.eligible(_metrics(h_fb=2.5), RAW) and not rs.eligible(_metrics(v_fb=3.5), RAW)
    assert not rs.eligible(_metrics(h_csi=None), RAW) and not rs.eligible(_metrics(v_fb=None), RAW)


def test_selection_maximises_the_mean_heavy_and_very_heavy_csi_among_the_eligible_and_breaks_ties_deterministically():
    results = [{"grid_index": 0, "validation": _metrics(h_csi=0.10, v_csi=0.02)}, {"grid_index": 1, "validation": _metrics(h_csi=0.09, v_csi=0.06)},
               {"grid_index": 2, "validation": _metrics(h_csi=0.30, v_csi=0.30, rmse=12.0)},          # ineligible: RMSE worse than Raw
               {"grid_index": 3, "validation": _metrics(h_csi=0.09, v_csi=0.06, rmse=9.0)}]
    assert rs.select_configuration(results, RAW)["grid_index"] == 3                                   # same score as 1, lower RMSE
    results[3]["validation"]["rmse_mm"] = 10.0
    assert rs.select_configuration(results, RAW)["grid_index"] == 1                                   # exact tie: the earlier grid position
    assert rs.select_configuration([{"grid_index": 0, "validation": _metrics(rmse=20.0)}], RAW) is None


def _ok(point, low, high, level=None):
    return {"status": "ok", "point": point, "interval95": [low, high], "excludes_zero": bool(low > 0 or high < 0)}


def test_the_decision_tiers_follow_the_intervals_and_never_the_point_estimates_alone():
    full = rs.decide_candidate({"rmse": _ok(-1.0, -1.5, -0.5), "heavy_csi": _ok(0.1, 0.05, 0.15), "very_heavy_csi": _ok(0.03, 0.01, 0.05)}, _metrics())
    assert full["tier"] == "FULL" and full["improvements"] == ["IMPROVES_RMSE", "IMPROVES_HEAVY", "IMPROVES_VERY_HEAVY"]
    two = rs.decide_candidate({"rmse": _ok(-1.0, -1.5, -0.5), "heavy_csi": _ok(0.1, 0.05, 0.15), "very_heavy_csi": _ok(0.03, -0.01, 0.05)}, _metrics())
    assert two["tier"] == "RMSE_AND_HEAVY" and not two["IMPROVES_VERY_HEAVY"]                       # a positive point whose interval includes zero is not an improvement
    wrong_sign = rs.decide_candidate({"rmse": _ok(1.0, 0.5, 1.5), "heavy_csi": _ok(-0.1, -0.15, -0.05), "very_heavy_csi": None}, _metrics())
    assert wrong_sign["tier"] == "NONE" and wrong_sign["improvements"] == []
    biased = rs.decide_candidate({"rmse": _ok(-1.0, -1.5, -0.5), "heavy_csi": _ok(0.1, 0.05, 0.15), "very_heavy_csi": _ok(0.03, 0.01, 0.05)}, _metrics(h_fb=3.0))
    assert biased["tier"] == "NONE" and not biased["BIAS_OK"]


def test_regime_adds_value_only_with_a_clear_heavy_gain_and_no_material_rmse_loss():
    assert rs.regime_adds_value({"heavy_csi": _ok(0.02, 0.005, 0.03), "rmse": _ok(0.0, -0.1, 0.1)})["adds_value"]
    assert not rs.regime_adds_value({"heavy_csi": _ok(0.02, -0.005, 0.03), "rmse": _ok(0.0, -0.1, 0.1)})["adds_value"]
    assert not rs.regime_adds_value({"heavy_csi": _ok(0.02, 0.005, 0.03), "rmse": _ok(0.4, 0.3, 0.5)})["adds_value"]
    assert not rs.regime_adds_value({})["adds_value"]


def test_pseudo_labels_are_fitted_on_training_features_and_routing_matches_the_definitions():
    rng = np.random.default_rng(1)
    X = rng.normal(size=(400, 12))
    rule = rs.fit_pseudo_labeler(X)
    labels = rs.pseudo_labels(X, rule)
    assert set(labels.tolist()) <= {0, 1, 2} and (labels == 2).mean() == pytest.approx(0.25, abs=0.02)
    with pytest.raises(ValueError):
        rs.fit_pseudo_labeler(np.full((10, 12), np.nan))
    probs = np.array([[0.7, 0.2, 0.1], [0.1, 0.1, 0.8]])
    rows = np.array([2, 3])
    experts = {r: np.full(5, float(r + 1), dtype=np.float32) for r in (0, 1, 2)}
    assert rs.route_hard(probs, experts, rows).tolist() == [1, 1, 3, 3, 3]
    soft = rs.route_soft(probs, experts, rows)
    assert soft[0] == pytest.approx(0.7 * 1 + 0.2 * 2 + 0.1 * 3) and soft[4] == pytest.approx(0.1 + 0.2 + 2.4) and (soft >= 0).all()


def test_exceedance_grid_tau_selection_and_metrics():
    grid = rs.exceedance_configurations()
    assert len(grid) == 8 and grid[0] == {"max_depth": 4, "n_estimators": 200, "pos_weight": "none"} and grid[-1] == {"max_depth": 6, "n_estimators": 350, "pos_weight": "sqrt_balance"}
    rng = np.random.default_rng(4)
    y = np.where(rng.random(5000) < 0.05, 80.0, 1.0)
    prob = np.clip(0.04 + 0.5 * (y > 64.5) * rng.random(5000) + 0.05 * rng.random(5000), 0, 1)
    best = rs.best_tau(prob, y, 64.5, (0.5, 2.0))
    assert best is not None and 0.5 <= best["frequency_bias"] <= 2.0 and best["csi"] > 0.3
    exact = rs.exceedance_metrics(prob, y, best["tau"], 64.5)
    assert exact == best and exact["hits"] + exact["misses"] == int((y >= 64.5).sum())
    assert rs.best_tau(np.zeros(100), np.ones(100), 64.5, (0.5, 2.0)) is None                      # no event: nothing qualifies
    results = [{"grid_index": 0, "validation": {"csi": 0.2}}, {"grid_index": 1, "validation": {"csi": 0.2}}, {"grid_index": 2, "validation": {"csi": 0.1}}, {"grid_index": 3, "validation": None}]
    assert rs.select_exceedance(results, 0.05)["grid_index"] == 0                                    # a tie goes to the earlier position; None and below-Raw never win
    assert rs.select_exceedance(results, 0.5) is None and rs.select_exceedance(results, None) is None
