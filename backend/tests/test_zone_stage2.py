"""Stage 2 (forcing strength): pure functions and the frozen evidence (spec hash chain, partition, support, training-year cut-points)."""

from __future__ import annotations

import hashlib
import inspect
import json
from pathlib import Path

import numpy as np
import pytest

from backend.app.ml import zone_verification as zv

PHASE7 = Path(__file__).resolve().parents[2] / "backend/app/evidence_data/phase7"
SPEC_SHA = "3755e06cc48f04e553ac204ea6534de1c2856ff4e2f7d438186ebc5e11e133ff"
MANIFEST = json.loads((PHASE7 / "zone_stage2_manifest.json").read_text(encoding="utf-8"))
YEARS = {("A", 2018): 2017, ("A", 2019): 2017, ("B", 2024): 2023, ("B", 2025): 2023}
KEYS = ("COASTAL|onshore", "OROGRAPHIC|cross_barrier", "COASTAL_AND_OROGRAPHIC|onshore", "COASTAL_AND_OROGRAPHIC|cross_barrier")


def load(name):
    return json.loads((PHASE7 / name).read_text(encoding="utf-8"))


# ------------------------------------------------------------------ pure functions
def test_forcing_signature_has_no_observation_argument_and_uses_unit_vectors():
    assert list(inspect.signature(zv.forcing_fields).parameters) == ["u850", "v850", "pwat", "geometry"]
    n = zv.GRID_CELLS
    geometry = {"coast_landward_east": np.ones(n), "coast_landward_north": np.zeros(n), "terrain_uphill_east": np.zeros(n), "terrain_uphill_north": np.ones(n)}
    u, v, pwat = np.full(n, 6.0), np.full(n, -3.0), np.full(n, 50.0)
    out = zv.forcing_fields(u, v, pwat, geometry)
    assert np.allclose(out["onshore"], 6.0 * 50.0) and np.allclose(out["cross_barrier"], 0.0)       # wind toward the south is downslope, not cross-barrier
    assert (zv.forcing_fields(-u, v, pwat, geometry)["onshore"] == 0).all()                            # offshore flow gives no onshore forcing


def test_bilinear_resampling_is_exact_for_a_linear_field_and_refuses_extrapolation():
    lat, lon = np.linspace(5, 30, 51), np.linspace(55, 95, 81)
    field = 2.0 * lat[:, None] + 0.5 * lon[None, :]
    target_lat, target_lon = np.linspace(10, 22, 49), np.linspace(68, 80, 49)
    out = zv.resample_to_target(field, lat, lon, target_lat, target_lon).reshape(49, 49)
    assert np.allclose(out, 2.0 * target_lat[:, None] + 0.5 * target_lon[None, :])
    with pytest.raises(ValueError):
        zv.resample_to_target(field, lat, lon, np.array([31.0]), np.array([70.0]))


def test_terciles_and_strata_partition_the_zone():
    rng = np.random.default_rng(3)
    values = np.concatenate([np.zeros(500), rng.gamma(2.0, 50.0, 700)])
    cuts = zv.tercile_cut_points(values)
    assert cuts["q33"] == 0.0 and cuts["q67"] > 0 and not cuts["degenerate"]          # a zero lower cut-point is legitimate: weak includes no-forcing pairs
    zone = np.zeros(zv.GRID_CELLS, bool)
    zone[:1200] = True
    forcing = np.zeros(zv.GRID_CELLS)
    forcing[:1200] = values
    masks = zv.stratum_masks(forcing, zone, cuts)
    assert sum(int(m.sum()) for m in masks.values()) == 1200
    assert not (masks["weak"] & masks["middle"]).any() and not (masks["middle"] & masks["strong"]).any()
    assert zv.tercile_cut_points(np.ones(30))["degenerate"]


def test_q3_statistics_and_support_gate():
    names = ["ALL", "Z|c|weak", "Z|c|middle", "Z|c|strong"]
    totals = np.zeros((4, 2, zv.S))
    for i, (hits, misses, fa) in enumerate([(0, 0, 0), (1, 9, 0), (0, 0, 0), (6, 4, 6)]):
        for m in range(2):
            totals[i, m, 0] = 100
            totals[i, m, zv.STAT_NAMES.index("heavy_hits")] = hits
            totals[i, m, zv.STAT_NAMES.index("heavy_misses")] = misses
            totals[i, m, zv.STAT_NAMES.index("heavy_false_alarms")] = fa
    out = zv.q3_statistics(totals, ["M0", "M2"], [("Z", "c")], names)
    assert out[("q3", "Z|c", "M0", "heavy_fb")] == pytest.approx(1.2 - 0.1)
    assert out[("q3", "Z|c", "M0", "heavy_csi")] == pytest.approx(6 / 16 - 1 / 10)
    stack = np.zeros((40, 4, 1, zv.S))
    stack[:, :, 0, 0] = 20
    stack[:, 1, 0, zv.STAT_NAMES.index("heavy_hits")] = 1
    gate = zv.stratum_support(stack, names)
    assert gate["Z|c|weak"]["continuous_supported"] and gate["Z|c|weak"]["heavy_supported"] is True
    assert gate["Z|c|middle"]["heavy_supported"] is False                     # no observed events
    assert zv.stratum_support(stack[:10], names)["Z|c|weak"]["continuous_supported"] is False


# ------------------------------------------------------------------ frozen evidence
def test_spec_hash_chain_and_manifest_hashes():
    spec_bytes = (PHASE7 / "zone_stage2_spec_v1.json").read_bytes()
    assert hashlib.sha256(spec_bytes).hexdigest() == SPEC_SHA == (PHASE7 / "zone_stage2_spec_v1.sha256").read_text().split()[0]
    spec = json.loads(spec_bytes)
    assert spec["parent"]["stage1_manifest_sha256"] == hashlib.sha256((PHASE7 / "zone_verification_manifest.json").read_bytes()).hexdigest()
    assert spec["parent"]["static_geography_sha256"] == hashlib.sha256((PHASE7 / "static_geography_v1.json").read_bytes()).hexdigest()
    raw = (PHASE7 / "zone_stage2_manifest.json").read_bytes()
    assert hashlib.sha256(raw).hexdigest() == (PHASE7 / "zone_stage2_manifest.sha256").read_text().strip() and b"\r\n" not in raw
    assert MANIFEST["spec_sha256"] == SPEC_SHA
    for name, entry in MANIFEST["files"].items():
        assert hashlib.sha256((PHASE7 / name).read_bytes()).hexdigest() == entry["sha256"], name


@pytest.mark.parametrize("track,year", list(YEARS))
def test_each_year_partitions_the_stage1_zones_and_uses_training_year_cut_points(track, year):
    stage2, stage1 = load(f"zone_stage2_{track}_{year}.json"), load(f"zone_verification_{track}_{year}.json")
    assert stage2["spec_sha256"] == SPEC_SHA and stage2["reproduction"]["strata_partition_zones"]
    assert stage2["reproduction"]["zones_equal_stage1_max_abs_diff"] <= 1e-9
    assert stage2["forcing_inputs"] == {"fields": ["u850", "v850", "pwat"], "observations_read": False}
    assert stage2["forcing_cut_points"]["year"] == YEARS[(track, year)] != year
    assert stage2["reproduction"]["stage1_sha256"] == hashlib.sha256((PHASE7 / f"zone_verification_{track}_{year}.json").read_bytes()).hexdigest()
    for key in KEYS:
        zone = key.split("|")[0]
        for model in stage2["models"]:
            total = sum(stage2["pooled"][f"{key}|{s}"][model]["cell_count"] for s in zv.STRATA)
            assert total == stage1["pooled"][zone][model]["cell_count"], (key, model)
        assert not stage2["forcing_cut_points"]["cut_points"][key]["degenerate"]
    assert stage2["fss"]["status"] == "not_reported" and not any(k.startswith("OTHER") for k in stage2["support"])


@pytest.mark.parametrize("track,year", list(YEARS))
def test_unsupported_strata_carry_no_number(track, year):
    data = load(f"zone_stage2_{track}_{year}.json")
    for name, gate in data["support"].items():
        for model in data["models"]:
            block = data["pooled"][name][model]
            if not gate["continuous_supported"]:
                assert block.get("status") == "insufficient_support" and "rmse_mm" not in block
            elif not gate["heavy_supported"]:
                heavy = block["categorical"]["heavy"]
                assert heavy.get("status") == "insufficient_support" and "CSI" not in heavy
            assert "very_heavy" not in block.get("categorical", {})
    for label, by_model in data["q3"].items():
        weak, strong = data["support"][f"{label}|weak"], data["support"][f"{label}|strong"]
        for model_metrics in by_model.values():
            if not (weak["heavy_supported"] and strong["heavy_supported"]):
                assert model_metrics["heavy_csi"]["status"] == "insufficient_support" and model_metrics["heavy_csi"]["point"] is None


def test_stage2_summary_is_consistent_and_labels_post_hoc_years():
    summary = load("zone_stage2_summary.json")
    assert "descriptive only" in summary["rule"]
    for track, block in summary["tracks"].items():
        assert block["development_significant"] == len(block["rows"]) and block["forcing_gaps"] == sum(r["forcing_gap"] for r in block["rows"])
        assert block["forcing_gaps"] <= block["development_significant"] <= block["tests"]
        for row in block["rows"]:
            lo, hi = row["development_interval95"]
            assert (lo > 0 or hi < 0) and row["same_sign"] == (row["development_point"] * row["final_point"] > 0) and row["metric"] in zv.Q3_DECISION
        assert "POST_HOC" not in load(f"zone_stage2_{track}_{block['development_year']}.json")["evidence_role"]
        assert "POST_HOC" in load(f"zone_stage2_{track}_{block['final_test_year']}.json")["evidence_role"]
