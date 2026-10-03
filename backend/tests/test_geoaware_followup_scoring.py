"""Decision logic of the one-shot 2022 test (docs/132), exercised on synthetic data before 2022 is opened."""

from __future__ import annotations

import numpy as np
import pytest

from backend.app.ml import geoaware_followup_scoring as sc
from backend.app.ml import zone_verification as zv
from backend.app.ml.geoaware_followup import ZONE

MODELS = ["M0", "CTRL", "CAND"]


def _labels(zone_cells: int = 40):
    labels = [[None] * 49 for _ in range(49)]
    cells = [(i, j) for i in range(10) for j in range(49)]
    for k, (i, j) in enumerate(cells):
        labels[i][j] = ZONE if k < zone_cells else ("COASTAL" if k % 3 == 0 else "OROGRAPHIC" if k % 3 == 1 else "OTHER")
    return labels


def _stack(cases: int, zone_cells: int, make, seed: int = 1):
    """Stack of per-case statistics; ``make(rng, obs, mask_zone)`` returns the forecast fields (M0, CTRL, CAND)."""
    labels = _labels(zone_cells)
    masks = zv.zone_masks(labels)
    rng = np.random.default_rng(seed)
    stacks = []
    for _ in range(cases):
        obs = np.full(zv.GRID_CELLS, np.nan)
        cells = masks["ALL"]
        obs[cells] = np.where(rng.random(cells.sum()) < 0.25, rng.gamma(2.0, 45.0, cells.sum()), rng.gamma(1.0, 3.0, cells.sum()))
        fields = make(rng, obs, masks[ZONE])
        stacks.append(zv.case_stats(obs, dict(zip(MODELS, fields)), masks))
    cell_counts = {zone: int(masks[zone].sum()) for zone in zv.ZONES}
    return np.stack(stacks), cell_counts


def _fields(zone_sigma: float, zone_gain: float = 1.0):
    """Unbiased multiplicative-noise forecasts. M0 forecasts a fifth of the rain; CTRL is unbiased with noise 1.0; CAND is unbiased with noise ``zone_sigma``
    inside the Ghats-coast zone (``zone_gain`` scales it, so a gain above 1 over-forecasts) and equals CTRL elsewhere."""
    def lognormal(rng, size, sigma):
        return np.exp(rng.normal(-sigma ** 2 / 2, sigma, size))

    def make(rng, obs, zone):
        valid = np.isfinite(obs)
        truth = np.where(valid, obs, np.nan)
        m0 = np.where(valid, 0.2 * truth * lognormal(rng, obs.size, 1.0), np.nan)
        ctrl = np.where(valid, truth * lognormal(rng, obs.size, 1.0), np.nan)
        cand_zone = truth * zone_gain * lognormal(rng, obs.size, zone_sigma)
        cand = np.where(valid, np.where(zone, cand_zone, ctrl), np.nan)           # identical to the control outside the zone: any overall difference comes from the zone
        return [m0, ctrl, cand]
    return make


def _run(zone_sigma: float, zone_gain: float = 1.0, cases: int = 120, zone_cells: int = 40, repeats: int = 400):
    stack, cell_counts = _stack(cases, zone_cells, _fields(zone_sigma, zone_gain))
    totals = stack.sum(axis=0)
    pooled = {zone: zv.metrics(totals[i, 2]) for i, zone in enumerate(zv.ZONES)}
    raw = {zone: zv.metrics(totals[i, 0]) for i, zone in enumerate(zv.ZONES)}
    boot = zv.paired_bootstrap(stack, MODELS, statistic=sc.difference_statistic_factory([("CAND", "CTRL")]), repeats=repeats, seed=26080, level=sc.DECISION_LEVEL)
    return sc.decide("CAND", "CTRL", pooled, raw, boot, zv.support(stack, cell_counts)), boot


def test_a_clearly_better_candidate_passes_p1_to_p3_at_the_stated_level():
    decision, _ = _run(zone_sigma=0.3)
    assert decision["status"] == "EVALUATED" and decision["level"] == 0.975
    assert decision["P1_zone_heavy_csi_beats_comparator_975"] and decision["P2_overall_rmse_within_tolerance"] and decision["P3_gating_guardrails_G1_G2_G4"]
    assert decision["adds_value"] is True
    gain = decision["zone_heavy_csi_difference"]
    assert gain["interval"][0] > 0 and "interval95" not in gain and gain["level"] == 0.975      # labelled 97.5 percent, never 95


def test_a_candidate_no_better_than_the_control_fails_p1_and_adds_no_value():
    decision, _ = _run(zone_sigma=1.0)                                             # same noise as the control inside the zone: no real gain
    assert decision["status"] == "EVALUATED" and decision["P1_zone_heavy_csi_beats_comparator_975"] is False and decision["adds_value"] is False
    interval = decision["zone_heavy_csi_difference"]["interval"]
    assert interval[0] <= 0 <= interval[1]


def test_a_candidate_that_over_forecasts_the_zone_fails_a_gating_guardrail_and_adds_no_value():
    decision, _ = _run(zone_sigma=0.3, zone_gain=3.0)                              # sharper but three times too wet in the zone
    assert decision["status"] == "EVALUATED"
    assert decision["guardrails"]["G4"] is False and decision["P3_gating_guardrails_G1_G2_G4"] is False and decision["adds_value"] is False


def test_adds_value_is_exactly_the_conjunction_of_p1_p2_p3():
    for kwargs in ({"zone_sigma": 0.3}, {"zone_sigma": 1.0}, {"zone_sigma": 0.3, "zone_gain": 3.0}):
        decision, _ = _run(**kwargs)
        assert decision["adds_value"] == (decision["P1_zone_heavy_csi_beats_comparator_975"] and decision["P2_overall_rmse_within_tolerance"] and decision["P3_gating_guardrails_G1_G2_G4"])


def test_a_97_5_percent_interval_is_wider_than_the_95_percent_one_on_the_same_resamples():
    stack, _ = _stack(120, 40, _fields(0.3))
    stat = sc.difference_statistic_factory([("CAND", "CTRL")])
    narrow = zv.paired_bootstrap(stack, MODELS, statistic=stat, repeats=400, seed=26080)
    wide = zv.paired_bootstrap(stack, MODELS, statistic=stat, repeats=400, seed=26080, level=sc.DECISION_LEVEL)
    key = ("diff", ZONE, "CAND", "CTRL", "heavy_csi")
    assert wide[key]["interval"][0] <= narrow[key]["interval95"][0] and wide[key]["interval"][1] >= narrow[key]["interval95"][1] and wide[key]["point"] == narrow[key]["point"]


def test_an_unsupported_zone_is_unevaluable_not_a_pass_or_a_fail():
    decision, _ = _run(zone_sigma=0.3, zone_cells=10)                              # fewer than 20 zone cells: the support gate fails
    assert decision["status"] == "UNEVALUABLE" and decision["adds_value"] is None and "support gate" in decision["reason"]


def test_guardrails_on_test_treat_undefined_as_failing_and_report_g3_separately():
    good = {"ALL": {"bias_mm": 0.3, "categorical": {"heavy": {"CSI": 0.2}, "very_heavy": {"frequency_bias": 0.0}}}, ZONE: {"categorical": {"heavy": {"frequency_bias": 0.8}}}}
    raw = {"ALL": {"categorical": {"heavy": {"CSI": 0.1}}}}
    guard = sc.guardrails_on_test(good, raw)
    assert guard == {"G1": True, "G2": True, "G3": False, "G4": True}
    assert sc.guardrails_on_test({**good, ZONE: {"categorical": {"heavy": {"frequency_bias": None}}}}, raw)["G4"] is False
    assert sc.guardrails_on_test({**good, "ALL": {**good["ALL"], "bias_mm": 1.6}}, raw)["G2"] is False
    assert sc.guardrails_on_test({**good, "ALL": {**good["ALL"], "categorical": {"heavy": {"CSI": None}, "very_heavy": {"frequency_bias": 0.2}}}}, raw)["G1"] is False


def test_difference_statistic_is_the_plain_metric_difference():
    stack, _ = _stack(30, 40, _fields(0.9))
    totals = stack.sum(axis=0)
    out = sc.difference_statistic_factory([("CAND", "CTRL")])(totals, MODELS)
    zone_i = zv.ZONES.index(ZONE)
    expected = zv._metric(totals[zone_i, 2], "heavy_csi") - zv._metric(totals[zone_i, 1], "heavy_csi")
    assert out[("diff", ZONE, "CAND", "CTRL", "heavy_csi")] == pytest.approx(expected)
    assert set(k[1] for k in out) == {"ALL", ZONE} and set(k[4] for k in out) == set(sc.DIFF_METRICS)
