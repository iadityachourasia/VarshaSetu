"""Stage 1 zone verification arithmetic: zones partition the footprint, additive statistics equal a brute-force recomputation, bootstrap is paired and deterministic."""

from __future__ import annotations

import numpy as np
import pytest

from backend.app.ml import zone_verification as zv

RNG = np.random.default_rng(7)


def labels():
    grid = [[None] * 49 for _ in range(49)]
    pattern = ["COASTAL", "OROGRAPHIC", "COASTAL_AND_OROGRAPHIC", "OTHER"]
    k = 0
    for i in range(10, 30):
        for j in range(10, 30):
            grid[i][j] = pattern[k % 4]
            k += 1
    return grid


MASKS = zv.zone_masks(labels())


def make_case(seed):
    rng = np.random.default_rng(seed)
    obs = np.full(zv.GRID_CELLS, np.nan)
    cells = MASKS["ALL"]
    obs[cells] = rng.gamma(0.4, 40.0, cells.sum())
    fc = {}
    for name, scale in (("M0", 1.0), ("M2", 0.7), ("M3", 0.8)):
        field = np.full(zv.GRID_CELLS, np.nan)
        field[cells] = np.maximum(0, obs[cells] * scale + rng.normal(0, 8, cells.sum()))
        fc[name] = field
    return obs, fc


def test_zones_partition_footprint_and_overlapping_views_are_unions():
    names = zv.PRE_REGISTERED_ZONES
    assert sum(int(MASKS[n].sum()) for n in names) == int(MASKS["ALL"].sum()) == 400
    assert not any((MASKS[a] & MASKS[b]).any() for i, a in enumerate(names) for b in names[i + 1:])
    assert np.array_equal(MASKS["COASTAL_ANY"], MASKS["COASTAL"] | MASKS["COASTAL_AND_OROGRAPHIC"])


def test_case_stats_match_brute_force_and_zone_totals_add_up_to_all():
    obs, fc = make_case(1)
    stats = zv.case_stats(obs, fc, MASKS)
    assert stats.shape == (len(zv.ZONES), 3, zv.S)
    for zi, zone in enumerate(zv.ZONES):
        cells = np.isfinite(obs) & MASKS[zone]
        for mi, field in enumerate(fc.values()):
            e = field[cells] - obs[cells]
            assert stats[zi, mi, 0] == cells.sum()
            assert stats[zi, mi, 1] == pytest.approx(e.sum()) and stats[zi, mi, 3] == pytest.approx((e ** 2).sum())
            o, f = obs[cells] >= 64.5, field[cells] >= 64.5
            assert stats[zi, mi, 4] == np.count_nonzero(o & f) and stats[zi, mi, 5] == np.count_nonzero(o & ~f)
    parts = sum(stats[zv.ZONES.index(n)] for n in zv.PRE_REGISTERED_ZONES)
    assert np.allclose(parts, stats[0])


def test_unpaired_or_misaligned_cells_are_refused():
    obs, fc = make_case(2)
    bad = {k: v.copy() for k, v in fc.items()}
    bad["M0"][np.flatnonzero(MASKS["ALL"])[0]] = np.nan
    with pytest.raises(ValueError):
        zv.case_stats(obs, bad, MASKS)
    outside = obs.copy()
    outside[0] = 5.0
    with pytest.raises(ValueError):
        zv.case_stats(outside, {k: np.where(np.isfinite(outside), v, 1.0) for k, v in fc.items()}, MASKS)


def test_metrics_formulas_and_undefined_values():
    v = np.zeros(zv.S)
    v[0] = 10
    assert zv.metrics(v)["categorical"]["heavy"]["CSI"] is None and zv.metrics(v)["categorical"]["heavy"]["frequency_bias"] is None
    v[zv.STAT_NAMES.index("heavy_hits")], v[zv.STAT_NAMES.index("heavy_misses")], v[zv.STAT_NAMES.index("heavy_false_alarms")] = 3, 1, 2
    c = zv.metrics(v)["categorical"]["heavy"]
    assert c["POD"] == 0.75 and c["FAR"] == 0.4 and c["CSI"] == 0.5 and c["frequency_bias"] == 1.25
    assert zv.metrics(np.zeros(zv.S))["rmse_mm"] is None


def test_support_gate_uses_cells_cases_and_observed_events():
    stack = np.stack([zv.case_stats(*make_case(s)[:1], make_case(s)[1], MASKS) for s in range(40)])
    cell_counts = {z: int(MASKS[z].sum()) for z in zv.ZONES}
    gate = zv.support(stack, cell_counts)
    assert gate["ALL"]["cases"] == 40 and gate["ALL"]["continuous_supported"]
    few = zv.support(stack[:10], cell_counts)
    assert not few["ALL"]["continuous_supported"] and not few["ALL"]["heavy"]["supported"]
    tiny = dict(cell_counts, COASTAL=5)
    assert not zv.support(stack, tiny)["COASTAL"]["continuous_supported"]


def test_bootstrap_is_deterministic_paired_and_consistent_with_point_estimates():
    stack = np.stack([zv.case_stats(*make_case(s)[:1], make_case(s)[1], MASKS) for s in range(30)])
    models = ["M0", "M2", "M3"]
    a = zv.paired_bootstrap(stack, models, repeats=200)
    b = zv.paired_bootstrap(stack, models, repeats=200)
    assert a == b
    point = zv.difference_statistics(stack.sum(axis=0), models)
    for key, value in a.items():
        if value["status"] == "ok":
            assert value["point"] == pytest.approx(point[key]) and value["interval95"][0] <= value["interval95"][1]
            assert value["excludes_zero"] == (value["interval95"][0] > 0 or value["interval95"][1] < 0)
    assert ("q1", "COASTAL", "M2", "rmse") in a and ("q2", "COASTAL", "M2", "rmse") in a and ("q2", "COASTAL", "M0", "rmse") not in a


def test_identical_zone_and_all_gives_zero_difference():
    # a statistic of ALL against itself is not produced; a zone equal to everything would give exactly zero
    stack = np.zeros((5, len(zv.ZONES), 2, zv.S))
    stack[:, :, :, 0] = 3
    stack[:, :, :, 3] = 12
    d = zv.difference_statistics(stack.sum(axis=0), ["M0", "M2"])
    assert d[("q1", "COASTAL", "M2", "rmse")] == 0.0 and d[("q2", "COASTAL", "M2", "rmse")] == 0.0
