"""Phase 4M: regime/lead-stratified categorical and FSS diagnostics (read-only re-aggregation)."""

import json
from pathlib import Path

import numpy as np
import pytest

from backend.app.ml.phase2c import fss_many
from experiments.recent_historical.phase4m_regime_categorical_fss_v1.analysis import (
    assert_counts_match_event_metrics, case_counts, categorical_from_counts, fss_components,
    fss_from_components, paired_case_bootstrap, to_field)

RESULTS = Path(__file__).resolve().parents[2] / "experiments/recent_historical/phase4m_regime_categorical_fss_v1/results"


def _cases(seed=0, n=6):
    rng = np.random.default_rng(seed)
    out = []
    for _ in range(n):
        mask = rng.random((49, 49)) > 0.3
        obs = np.where(rng.random((49, 49)) > 0.85, rng.uniform(60, 130, (49, 49)), rng.uniform(0, 30, (49, 49)))
        fc = np.where(rng.random((49, 49)) > 0.85, rng.uniform(60, 130, (49, 49)), rng.uniform(0, 30, (49, 49)))
        out.append({"forecast": fc, "observed": obs, "mask": mask})
    return out


@pytest.mark.parametrize("threshold,size", [(64.5, 1), (64.5, 3), (115.6, 5), (64.5, 9)])
def test_component_fss_reproduces_frozen_fss_many(threshold, size):
    cases = _cases()
    comps = [fss_components(c["forecast"], c["observed"], c["mask"], threshold, size) for c in cases]
    mine, frozen = fss_from_components(comps), fss_many(cases, threshold, size)
    assert mine["fss"] == pytest.approx(frozen["fss"], abs=1e-12)
    assert mine["case_count"] == frozen["case_count"]


def test_fss_undefined_when_no_events_anywhere():
    case = {"forecast": np.zeros((49, 49)), "observed": np.zeros((49, 49)), "mask": np.ones((49, 49), bool)}
    assert fss_components(case["forecast"], case["observed"], case["mask"], 64.5, 3) is None
    assert fss_from_components([None])["fss"] is None


def test_count_based_categorical_equals_frozen_event_metrics():
    rng = np.random.default_rng(3)
    obs, fc = rng.uniform(0, 140, 5000), rng.uniform(0, 140, 5000)
    for threshold in (64.5, 115.6):
        assert_counts_match_event_metrics(obs, fc, threshold)
    # forecast never reaches the threshold: POD/CSI defined and zero, FAR undefined, as in event_metrics
    assert_counts_match_event_metrics(obs, np.zeros_like(fc), 64.5)
    assert categorical_from_counts(case_counts(np.zeros_like(fc), obs, 64.5))["FAR"] is None
    # no events at all: everything undefined
    assert categorical_from_counts(case_counts(np.zeros(10), np.zeros(10), 64.5))["CSI"] is None


def test_pooled_counts_are_additive_across_cases():
    rng = np.random.default_rng(4)
    parts = [(rng.uniform(0, 140, 400), rng.uniform(0, 140, 400)) for _ in range(5)]
    pooled = sum(case_counts(f, o, 64.5) for o, f in parts)
    whole = case_counts(np.concatenate([f for _, f in parts]), np.concatenate([o for o, _ in parts]), 64.5)
    assert pooled.tolist() == whole.tolist()


def test_to_field_rejects_duplicate_or_out_of_range_pixels():
    with pytest.raises(ValueError):
        to_field(np.ones(2), np.array([5, 5]))
    with pytest.raises(ValueError):
        to_field(np.ones(1), np.array([2401]))
    grid, mask = to_field(np.array([1.0, 2.0]), np.array([0, 2400]))
    assert mask.sum() == 2 and grid[0, 0] == 1.0 and grid[48, 48] == 2.0


def test_paired_bootstrap_is_seeded_paired_and_null_for_identical_models():
    rng = np.random.default_rng(5)
    per_case = rng.integers(0, 20, size=(40, 2, 4)).astype(float)
    per_case[:, 1] = per_case[:, 0]                      # identical "models"

    def diff(total):
        return float(total[0, 0] - total[1, 0])
    a = paired_case_bootstrap(per_case, diff, repeats=200)
    b = paired_case_bootstrap(per_case, diff, repeats=200)
    assert a == b
    assert a["interval95"] == [0.0, 0.0] and a["point"] == 0.0
    assert paired_case_bootstrap(per_case[:1], diff)["status"] == "insufficient_cases"


@pytest.mark.skipif(not (RESULTS / "2025_regime_categorical_fss.json").exists(), reason="Phase 4M results not generated")
@pytest.mark.parametrize("year,role", [(2024, "DEVELOPMENT"), (2025, "POST_HOC_DESCRIPTIVE_ONLY")])
def test_frozen_outputs_reproduce_prior_phases_and_are_labelled(year, role):
    d = json.loads((RESULTS / f"{year}_regime_categorical_fss.json").read_text(encoding="utf-8"))
    assert d["reproduction"]["status"] == "REPRODUCED" and d["reproduction"]["max_abs_diff"] < 1e-9
    assert role in d["evidence_role"]
    assert sum(b["case_count"] for b in d["by_predicted_regime"].values()) == d["case_count"]
    assert sum(b["case_count"] for b in d["by_lead_day"].values()) == d["case_count"]
    for m in ("M0", "M1", "M2", "M3", "M4"):
        v = d["overall"]["fss"]["heavy"]["3"]["all_cases"][m]["fss"]
        assert v is None or 0 <= v <= 1
