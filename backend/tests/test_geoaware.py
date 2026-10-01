"""Pure functions of the geography-aware correction: they must implement the frozen protocol exactly."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import pytest

from backend.app.ml import geoaware as ga

PROTOCOL_FILE = Path(__file__).resolve().parents[1] / "app/evidence_data/phase9/geoaware_protocol_v1.json"
PROTOCOL = json.loads(PROTOCOL_FILE.read_text(encoding="utf-8"))


# ------------------------------------------------------------------ the code equals the frozen protocol
def test_protocol_file_matches_its_sidecar_and_is_lf():
    raw = PROTOCOL_FILE.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == PROTOCOL_FILE.with_suffix(".sha256").read_text().split()[0] and b"\r\n" not in raw
    assert PROTOCOL["status"] == "APPROVED_FOR_DEVELOPMENT_ONLY_NO_INDEPENDENT_TEST" and PROTOCOL["approval"]["approved_before_any_training"] is True


def test_feature_registry_constants_equal_the_protocol():
    reg = PROTOCOL["feature_registry_v2"]
    assert ga.BASE_FEATURES == reg["base_22"] and ga.STATIC_FEATURES == reg["static_8"] and ga.FORCING_FEATURES == reg["forcing_2"]
    assert ga.ARMS == reg["arms"] and reg["primary_candidate"] == "A3" and reg["v1_registry_edited"] is False
    assert [len(v) for v in ga.ARMS.values()] == [22, 30, 24, 32]


def test_grid_guardrails_weights_and_embargo_equal_the_protocol():
    grid = PROTOCOL["model"]["grid"]
    configs = ga.configurations()
    assert len(configs) == PROTOCOL["model"]["configurations_per_arm"] == 16
    assert configs[0] == {"objective": "reg:squarederror", "weights": "none", "max_depth": 4, "n_estimators": 200}
    assert configs[-1] == {"objective": "reg:tweedie", "weights": "capped_event", "max_depth": 6, "n_estimators": 350}
    assert {c["objective"] for c in configs} == set(grid["objective"]) and {c["weights"] for c in configs} == set(grid["weights"])
    assert {c["max_depth"] for c in configs} == set(grid["max_depth"]) and {c["n_estimators"] for c in configs} == set(grid["n_estimators"])
    assert ga.EVENT_WEIGHT_CAP == PROTOCOL["model"]["event_weight"]["cap"] == 10.0
    assert ga.EMBARGO_DAYS == PROTOCOL["training"]["folds"]["embargo_initialization_days_each_side"] == 3
    assert ga.G2_MAX_ABS_BIAS_MM == 1.5 and ga.G3_MIN_VERY_HEAVY_FREQUENCY_BIAS == 0.05 and (ga.HEAVY_MM, ga.VERY_HEAVY_MM) == (64.5, 115.6)


# ------------------------------------------------------------------ features
def test_static_columns_index_by_cell_and_keep_undefined_values_missing():
    static = {name: np.arange(ga.GRID_CELLS, dtype=float) * (k + 1) for k, name in enumerate(ga.STATIC_FEATURES)}
    static["mean_elevation_m"][7] = np.nan
    pixel = np.array([5, 7, 2400, 5])
    out = ga.static_columns(static, pixel)
    assert out.shape == (4, 8) and out.dtype == np.float32
    assert out[0, 1] == 5 * 2 and out[2, 7] == 2400 * 8 and np.isnan(out[1, 0]) and not np.isnan(out[1, 1])
    with pytest.raises(ValueError):
        ga.static_columns(static, np.array([ga.GRID_CELLS]))


def test_forcing_columns_cover_every_row_exactly_once():
    forcing = [{"onshore_flux": np.full(ga.GRID_CELLS, 3.0), "cross_barrier_flux": np.full(ga.GRID_CELLS, 4.0)},
               {"onshore_flux": np.arange(ga.GRID_CELLS, dtype=float), "cross_barrier_flux": np.zeros(ga.GRID_CELLS)}]
    pixel = np.array([0, 1, 2, 10, 11])
    out = ga.forcing_columns([(0, 3), (3, 2)], forcing, pixel, 5)
    assert out[:3, 0].tolist() == [3, 3, 3] and out[3:, 0].tolist() == [10, 11] and out[:3, 1].tolist() == [4, 4, 4]
    with pytest.raises(ValueError):
        ga.forcing_columns([(0, 3)], forcing[:1], pixel, 5)                   # rows left uncovered
    with pytest.raises(ValueError):
        ga.forcing_columns([(0, 3), (2, 3)], forcing, pixel, 5)                # overlapping cases


def test_assemble_follows_the_registry_order_for_each_arm():
    base, static, forcing = np.ones((4, 22)), np.full((4, 8), 2.0), np.full((4, 2), 3.0)
    assert ga.assemble(base, None, None, "A0").shape == (4, 22)
    a1, a2, a3 = (ga.assemble(base, static, forcing, arm) for arm in ("A1", "A2", "A3"))
    assert a1.shape == (4, 30) and a2.shape == (4, 24) and a3.shape == (4, 32)
    assert a3[0, 21] == 1 and a3[0, 22] == 2 and a3[0, 29] == 2 and a3[0, 30] == 3 and a3[0, 31] == 3 and a2[0, 22] == 3
    with pytest.raises(ValueError):
        ga.assemble(base, None, forcing, "A3")
    with pytest.raises(ValueError):
        ga.assemble(np.ones((4, 21)), static, forcing, "A3")


def test_event_weights_are_capped_monotone_and_reject_bad_targets():
    w = ga.event_weights(np.array([0.0, 64.5, 300.0, 1000.0]))
    assert w[0] == 1.0 and w[1] == 2.0 and w[2] == pytest.approx(1 + 300 / 64.5) and w[3] == 10.0 and np.all(np.diff(w) >= 0)
    assert 1.0 < ga.effective_sample_size(w) <= len(w)
    for bad in (np.array([-1.0]), np.array([np.nan])):
        with pytest.raises(ValueError):
            ga.event_weights(bad)


# ------------------------------------------------------------------ folds
def _cases():
    days = [f"2023-06-{d:02d}T00:00:00Z" for d in range(1, 31)]
    inits, folds = [], []
    for i, d in enumerate(days):
        for lead in range(3):
            inits.append(d)
            folds.append(f"F{i // 6 + 1}")
    return inits, folds


def test_embargo_removes_three_initialization_days_on_both_sides_and_keeps_leads_together():
    inits, folds = _cases()                                   # 30 dates, five blocks of 6 dates, three leads each
    mask = ga.training_case_mask(inits, folds, "F3")           # F3 = dates 13..18
    train_days = {d[8:10] for d, keep in zip(inits, mask) if keep}
    assert "13" not in train_days and "18" not in train_days
    assert {"10", "11", "12", "19", "20", "21"}.isdisjoint(train_days)             # 3 days before the first and after the last
    assert {"09", "22"} <= train_days                                                # just outside the embargo
    assert not mask[[i for i, f in enumerate(folds) if f == "F3"]].any()
    for d in set(inits):                                                             # all leads of one date share the same status
        assert len({bool(m) for dd, m in zip(inits, mask) if dd == d}) == 1
    first = ga.training_case_mask(inits, folds, "F1")
    assert {d[8:10] for d, keep in zip(inits, first) if keep} == {f"{x:02d}" for x in range(10, 31)}   # no left side; right embargo 7..9
    with pytest.raises(ValueError):
        ga.training_case_mask(inits, folds, "F9")


def test_rows_of_cases_selects_whole_cases():
    mask = ga.rows_of_cases([(0, 3), (3, 2), (5, 4)], np.array([True, False, True]))
    assert mask.tolist() == [True] * 3 + [False] * 2 + [True] * 4


# ------------------------------------------------------------------ metrics, guardrails and selection
def _metrics(rmse, bias=0.0, heavy_csi=0.2, very_fb=0.5):
    return {"rmse_mm": rmse, "bias_mm": bias, "heavy": {"csi": heavy_csi}, "very_heavy": {"frequency_bias": very_fb}}


def test_pooled_metrics_match_hand_arithmetic_and_clip_at_zero():
    y = np.array([0.0, 70.0, 120.0, 10.0])
    m = ga.pooled_metrics(y, np.array([-5.0, 70.0, 100.0, 80.0]))                    # the negative forecast is clipped to 0
    assert m["bias_mm"] == pytest.approx((0 + 0 - 20 + 70) / 4) and m["rmse_mm"] == pytest.approx(np.sqrt((0 + 0 + 400 + 4900) / 4))
    assert m["heavy"] == {"hits": 2, "misses": 0, "false_alarms": 1, "observed_events": 2, "csi": 2 / 3, "frequency_bias": 1.5}
    assert m["very_heavy"]["hits"] == 0 and m["very_heavy"]["misses"] == 1 and m["very_heavy"]["frequency_bias"] == 0.0
    assert ga.pooled_metrics(np.zeros(3), np.zeros(3))["heavy"]["csi"] is None            # undefined is not zero


def test_float32_threshold_semantics_match_the_frozen_metrics():
    near = np.float32(115.6)                                           # float32 rounding of the cut-off is the frozen convention
    assert ga.pooled_metrics(np.array([near]), np.array([near]))["very_heavy"]["hits"] == 1


def test_guardrails_never_pass_on_undefined_values():
    assert all(ga.guardrails(_metrics(1.0), 0.1).values())
    assert not ga.guardrails(_metrics(1.0, heavy_csi=0.05), 0.1)["G1"]
    assert not ga.guardrails(_metrics(1.0, bias=-1.6), 0.1)["G2"] and ga.guardrails(_metrics(1.0, bias=1.5), 0.1)["G2"]
    assert not ga.guardrails(_metrics(1.0, very_fb=0.049), 0.1)["G3"] and ga.guardrails(_metrics(1.0, very_fb=0.05), 0.1)["G3"]
    assert not ga.guardrails(_metrics(1.0, heavy_csi=None), 0.1)["G1"] and not ga.guardrails(_metrics(1.0, very_fb=None), 0.1)["G3"]


def test_selection_takes_the_lowest_rmse_among_passing_configurations_and_breaks_ties_by_grid_order():
    results = [{"grid_index": 0, "metrics": _metrics(10.0, heavy_csi=0.01)},       # fails G1
               {"grid_index": 1, "metrics": _metrics(12.0)}, {"grid_index": 2, "metrics": _metrics(11.0)}, {"grid_index": 3, "metrics": _metrics(11.0)},
               {"grid_index": 4, "metrics": _metrics(9.0, bias=3.0)}]                  # fails G2
    chosen = ga.select_configuration(results, raw_heavy_csi=0.1)
    assert chosen["grid_index"] == 2
    assert ga.select_configuration([r for r in results if r["grid_index"] in (0, 4)], 0.1) is None      # nothing passes: reported, not forced
