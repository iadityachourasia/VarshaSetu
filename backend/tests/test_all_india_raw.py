"""Raw all-India verification (docs/140): the frozen region partition, additive statistics against an independent loop, support gate and bootstrap."""

from __future__ import annotations

import numpy as np
import pytest

from backend.app.ml import all_india_raw as air
from backend.app.ml import zone_verification as zv


def test_partition_is_disjoint_exhaustive_over_the_scored_grid_and_follows_the_rule():
    lat, lon = np.arange(6.5, 38.5 + 1e-9, 0.25), np.arange(66.5, 100.0 + 1e-9, 0.25)
    masks = air.region_masks(lat, lon)
    assert len(lat) == 129 and len(lon) == 135
    assert sum(int(masks[r].sum()) for r in air.REGIONS) == int(masks["ALL"].sum())
    assert not np.any(sum(masks[r].astype(int) for r in air.REGIONS) > 1)
    inside = [(a, b) for a in lat for b in lon if 10 <= a <= 22 and 68 <= b <= 80]
    assert int(masks["INSIDE_MODEL_DOMAIN"].sum()) == len(inside) == 49 * 49
    assert air.region_of(30.0, 75.0) == "NORTH_OF_DOMAIN" and air.region_of(26.0, 92.0) == "EAST_AND_NORTH_EAST" and air.region_of(20.0, 85.0) == "EAST_COAST_PENINSULA"
    assert air.region_of(8.0, 77.0) == "SOUTH_OF_DOMAIN" and air.region_of(15.0, 67.0) is None and air.region_of(30.0, 90.0) == "EAST_AND_NORTH_EAST" and air.region_of(25.0, 88.0) == "NORTH_OF_DOMAIN"
    assert air.region_of(22.0, 80.0) == "INSIDE_MODEL_DOMAIN" and air.region_of(22.25, 80.0) == "NORTH_OF_DOMAIN" and air.region_of(9.75, 80.0) == "SOUTH_OF_DOMAIN"
    assert air.region_of(9.75, 80.25) == "EAST_COAST_PENINSULA"


def _case(rng, shape=(6, 7)):
    obs = rng.gamma(0.5, 25.0, shape).ravel()
    raw = np.maximum(0, obs * rng.uniform(0.4, 1.6, obs.size) + rng.normal(0, 5, obs.size))
    obs[rng.random(obs.size) < 0.15] = np.nan
    raw = np.where(np.isfinite(obs), raw, np.nan)
    return obs, raw


def _toy_masks():
    lat, lon = np.array([9.0, 15.0, 25.0, 30.0, 12.0, 20.0]), np.array([70.0, 75.0, 85.0, 95.0, 78.0, 66.5, 79.0])
    return lat, lon, air.region_masks(lat, lon)


def test_case_statistics_equal_an_independent_loop_and_regions_add_up_to_all_india():
    lat, lon, masks = _toy_masks()
    rng = np.random.default_rng(5)
    obs, raw = _case(rng)
    stats = air.case_stats(obs, raw, masks)
    for i, name in enumerate(air.NAMES):
        sel = masks["ALL"] if name == "ALL_INDIA" else masks[name]
        cells = np.isfinite(obs) & sel
        err = raw[cells] - obs[cells]
        assert stats[i, 0] == cells.sum() and stats[i, 1] == pytest.approx(err.sum()) and stats[i, 3] == pytest.approx((err ** 2).sum())
        hits = np.count_nonzero((obs[cells] >= 64.5) & (raw[cells] >= 64.5))
        assert stats[i, zv._idx("heavy_hits")] == hits
    assert np.allclose(stats[1:].sum(axis=0), stats[0])                      # the regions partition ALL_INDIA


def test_cells_in_no_region_are_dropped_and_counted_and_mismatched_cells_are_refused():
    lat, lon, masks = _toy_masks()
    obs, raw = _case(np.random.default_rng(1))
    off = np.flatnonzero(~masks["ALL"])
    assert off.size
    obs2, raw2 = obs.copy(), raw.copy()
    obs2[off[0]], raw2[off[0]] = 10.0, 10.0
    assert air.unscored_cells(obs2, masks) >= 1
    assert np.array_equal(air.case_stats(obs2, raw2, masks), air.case_stats(np.where(masks["ALL"], obs2, np.nan), np.where(masks["ALL"], raw2, np.nan), masks))
    raw3 = raw.copy()
    raw3[np.flatnonzero(np.isfinite(raw3))[0]] = np.nan
    with pytest.raises(ValueError):
        air.case_stats(obs, raw3, masks)


def test_support_gate_and_metrics_do_not_invent_values_for_unsupported_regions():
    lat, lon, masks = _toy_masks()
    rng = np.random.default_rng(2)
    stack = np.stack([air.case_stats(*_case(rng), masks) for _ in range(40)])
    counts = {n: int(masks["ALL"].sum()) if n == "ALL_INDIA" else int(masks[n].sum()) for n in air.NAMES}
    gate = air.support(stack, counts)
    assert gate["ALL_INDIA"]["continuous_supported"] and gate["ALL_INDIA"]["cases"] == 40
    tiny = air.support(stack[:10], counts)
    assert not tiny["ALL_INDIA"]["continuous_supported"] and not tiny["ALL_INDIA"]["heavy"]["supported"]
    metrics = air.region_metrics(stack.sum(axis=0))
    assert metrics["ALL_INDIA"]["rmse_mm"] > 0 and metrics["ALL_INDIA"]["cell_count"] == int(stack[:, 0, 0].sum())


def test_bootstrap_is_deterministic_and_brackets_the_point():
    lat, lon, masks = _toy_masks()
    rng = np.random.default_rng(3)
    stack = np.stack([air.case_stats(*_case(rng), masks) for _ in range(30)])
    a = air.bootstrap(stack, repeats=100, seed=7)
    b = air.bootstrap(stack, repeats=100, seed=7)
    assert a == b
    entry = a[("ALL_INDIA", "rmse")]
    assert entry["status"] == "ok" and entry["interval95"][0] <= entry["point"] <= entry["interval95"][1]
    assert entry["point"] == pytest.approx(air.region_metrics(stack.sum(axis=0))["ALL_INDIA"]["rmse_mm"])
