"""District verification statistics (protocol v1, docs/112): pure-function tests on synthetic data and invariants."""

from __future__ import annotations

import numpy as np
import pytest

from backend.app.ml.district_product import GRID_CELLS, aggregate_operational_districts
from backend.app.ml.district_verification import (AREA_FRACTION, BAND_NAMES, CORRECTED, MIN_CELLS, MODELS, Stack,
                                                  analyse_districts, case_district_stats, latitude_band)

REGIMES = ("ACTIVE_MONSOON", "BREAK_WEAK_MONSOON", "LOW_DEPRESSION_INFLUENCED")


def _weights(n_districts, seed=0, cells_per_district=14):
    rng = np.random.default_rng(seed)
    w = np.zeros((n_districts, GRID_CELLS), dtype=np.float32)
    for d in range(n_districts):
        idx = rng.choice(GRID_CELLS, cells_per_district + d % 3, replace=False)
        w[d, idx] = rng.uniform(0.5, 1.5, idx.size)
    return w


def _fields(rng, mask, n_models=5):
    base = np.where(rng.random(GRID_CELLS) > 0.85, rng.uniform(60, 140, GRID_CELLS), rng.uniform(0, 30, GRID_CELLS))
    out = {"obs": base}
    for m in MODELS:
        out[m] = np.maximum(0, base + rng.normal(0, 20, GRID_CELLS))
    return {k: np.where(mask, v, np.nan) for k, v in out.items()}


def test_latitude_band_edges_belong_to_the_northern_band():
    assert [latitude_band(x) for x in (10.0, 13.99, 14.0, 17.99, 18.0, 21.9)] == [0, 0, 1, 1, 2, 2]
    assert len(BAND_NAMES) == 3


def test_case_stats_equal_the_shared_district_aggregation_and_a_brute_force_any_cell():
    rng = np.random.default_rng(1)
    weights = _weights(8, 1)
    mask = rng.random(GRID_CELLS) > 0.3
    fields = _fields(rng, mask)
    stats = case_district_stats(weights, fields)
    districts = [{"district_id": f"D{i}", "district_name": f"D{i}"} for i in range(8)]
    rows = {r["district_id"]: r for r in aggregate_operational_districts(
        districts, weights, raw=fields["M0"], corrected=fields["M2"], observed=fields["obs"])}
    for d in range(8):
        row = rows.get(f"D{d}")
        assert (stats["cells"][d] > 0) == (row is not None)
        if row is None:
            continue
        assert stats["cells"][d] == row["valid_grid_cells"]
        # The shared aggregation normalises float32 weights in float32; case_district_stats uses float64 (more precise).
        # The two agree to ~1e-6 mm, far below any reported precision.
        assert stats["mean:M0"][d] == pytest.approx(row["raw_mean_mm"], abs=1e-4)
        assert stats["mean:M2"][d] == pytest.approx(row["corrected_mean_mm"], abs=1e-4)
        assert stats["mean:obs"][d] == pytest.approx(row["observed_mean_mm"], abs=1e-4)
        assert stats["frac:M2:heavy"][d] == pytest.approx(row["heavy_area_fraction"], abs=1e-6)
        assert stats["frac:obs:very_heavy"][d] == pytest.approx(row["observed_very_heavy_area_fraction"], abs=1e-6)
        active = (weights[d] > 0) & mask
        assert bool(stats["any:obs:heavy"][d]) == bool((fields["obs"][active] >= 64.5).any())
        assert bool(stats["any:M3:very_heavy"][d]) == bool((fields["M3"][active] >= 115.6).any())
    with pytest.raises(ValueError):
        case_district_stats(weights, {**fields, "M0": fields["M0"][:10]})


def _synthetic_stack(n_cases=60, n_districts=12, perfect=None, seed=3):
    rng = np.random.default_rng(seed)
    weights = _weights(n_districts, seed)
    per_case, regimes = [], []
    for c in range(n_cases):
        mask = rng.random(GRID_CELLS) > 0.25
        fields = _fields(rng, mask)
        if perfect:
            fields[perfect] = fields["obs"].copy()
        per_case.append(case_district_stats(weights, fields))
        regimes.append(c % 3)
    case_ids = [f"2024{6 + c // 30:02d}{c % 28 + 1:02d}_day{c % 3 + 1}_24h" for c in range(n_cases)]
    lat = np.linspace(10.5, 21.5, n_districts)
    return Stack(per_case, case_ids, [f"D{i}" for i in range(n_districts)], [f"District {i}" for i in range(n_districts)], lat, np.array(regimes))


def test_stack_inclusion_applies_the_five_cell_rule_and_excludes_thin_districts():
    rng = np.random.default_rng(5)
    weights = _weights(4, 5, cells_per_district=10)
    weights[3] = 0
    weights[3, :3] = 1.0                                   # a district covered by 3 cells only
    per_case = [case_district_stats(weights, _fields(rng, np.ones(GRID_CELLS, bool))) for _ in range(6)]
    stack = Stack(per_case, [f"2024061{c}_day1_24h" for c in range(6)], list("abcd"), list("ABCD"), np.array([11., 13., 17., 20.]), np.zeros(6, int))
    assert MIN_CELLS == 5 and stack.kept.tolist() == [True, True, True, False]
    assert not stack.included[:, 3].any() and stack.included[:, :3].all()


@pytest.fixture(scope="module")
def planted():
    stack = _synthetic_stack(perfect="M3")
    return stack, analyse_districts(stack, REGIMES, repeats=300)


def test_a_perfect_model_scores_perfectly_and_a_noise_model_is_not_called_improved(planted):
    stack, result = planted
    pooled = result["categorical"]["E1"]["heavy"]["pooled"]["all"]
    assert pooled["M3"]["POD"] == 1.0 and pooled["M3"]["FAR"] == 0.0 and pooled["M3"]["CSI"] == 1.0 and pooled["M3"]["ETS"] == 1.0
    assert pooled["M0"]["CSI"] < pooled["M3"]["CSI"]          # noisy Raw is strictly worse than the planted perfect model
    assert result["continuous"]["pooled"]["all"]["M3"]["rmse_mm"] == 0.0
    counts = result["improved_worsened"]
    assert counts["M3"]["improved"] == counts["M3"]["tested_districts"] == 12
    assert counts["M2"]["improved"] == 0                       # M2 is noisy like Raw: nothing planted
    assert result["contrasts"]["continuous"]["M3_vs_M0"]["interval95"][0] > 0


def test_group_partitions_sum_to_the_pooled_counts_for_every_definition(planted):
    _, result = planted
    for definition in ("E1", "E2", "E3"):
        for threshold in ("heavy", "very_heavy"):
            block = result["categorical"][definition][threshold]
            for model in MODELS:
                whole = block["pooled"]["all"][model]
                for kind in ("by_lead", "by_regime", "by_region"):
                    for field in ("hits", "misses", "false_alarms", "sample_count"):
                        assert sum(g[model][field] for g in block[kind].values()) == whole[field], (definition, threshold, kind, model, field)
                assert whole["hits"] + whole["misses"] == whole["observed_event_count"]
    for kind, members in result["continuous"].items():
        assert sum(v["M0"]["pairs"] for v in members.values()) == result["inclusion"]["district_case_pairs"]


def test_per_district_observed_events_sum_to_the_pooled_count_and_support_gating(planted):
    stack, result = planted
    for definition in ("E1", "E2"):
        for threshold in ("heavy", "very_heavy"):
            total = sum(e["categorical"][definition][threshold]["observed_events"] for e in result["districts"])
            assert total == result["observed_events_pooled"][definition][threshold] == result["categorical"][definition][threshold]["pooled"]["all"]["M0"]["observed_event_count"]
            for entry in result["districts"]:
                cell = entry["categorical"][definition][threshold]
                assert (cell["status"] == "supported") == (cell["observed_events"] >= 30)
                assert (cell["models"] is None) == (cell["status"] == "insufficient_support")
    assert result["supported_district_counts"]["E1"]["heavy"] == sum(
        e["categorical"]["E1"]["heavy"]["status"] == "supported" for e in result["districts"])


def test_expected_by_chance_and_exclusions_are_reported(planted):
    _, result = planted
    tested = result["improved_worsened"]["M1"]["tested_districts"]
    assert result["improved_worsened"]["M1"]["expected_by_chance_total"] == round(0.05 * tested, 1)
    assert result["improved_worsened"]["M1"]["expected_by_chance_per_direction"] == round(0.025 * tested, 1)
    assert result["inclusion"]["districts_included"] + len(result["inclusion"]["districts_excluded"]) == result["inclusion"]["districts_total"]
    assert AREA_FRACTION == 0.25


def test_the_analysis_is_deterministic_for_a_fixed_seed():
    stack = _synthetic_stack(n_cases=40, n_districts=6, seed=9)
    a = analyse_districts(stack, REGIMES, repeats=100)
    b = analyse_districts(stack, REGIMES, repeats=100)

    def canon(value):                       # NaN != NaN, so compare a NaN-free canonical form
        if isinstance(value, dict):
            return {k: canon(v) for k, v in value.items()}
        if isinstance(value, (list, tuple)):
            return [canon(v) for v in value]
        return None if isinstance(value, float) and np.isnan(value) else value
    assert canon(a) == canon(b)
    assert set(CORRECTED) == set(a["improved_worsened"])
