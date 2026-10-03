"""Pure rules of the geography-aware follow-up (docs/129): arms, grid, leave-one-year-out, guardrails G1 to G4 and the selection rule."""

from __future__ import annotations

import numpy as np
import pytest

from backend.app.ml import geoaware_followup as gf
from backend.app.ml.geoaware import BASE_FEATURES, STATIC_FEATURES


def test_the_four_arms_are_the_declared_registry():
    assert {a: len(f) for a, f in gf.ARMS.items()} == {"B0": 22, "B1": 30, "B0Z": 20, "B1Z": 28}
    assert gf.ARMS["B0"] == list(BASE_FEATURES) and gf.ARMS["B1"] == list(BASE_FEATURES) + list(STATIC_FEATURES)
    for arm in ("B0Z", "B1Z"):
        assert not set(gf.Z500_FEATURES) & set(gf.ARMS[arm]) and set(gf.ARMS[arm]) == set(gf.ARMS[arm[:2]]) - set(gf.Z500_FEATURES)
    assert not any("flux" in f or "onshore" in f for f in gf.ARMS["B1"])          # forecast-time forcing is not carried over


def test_assemble_selects_columns_by_name_in_registry_order():
    rows = 5
    base = np.tile(np.arange(22, dtype=np.float64), (rows, 1))
    static = np.tile(100 + np.arange(8, dtype=np.float64), (rows, 1))
    for arm, names in gf.ARMS.items():
        expected = [(BASE_FEATURES + STATIC_FEATURES).index(n) for n in names]
        full = np.concatenate([np.arange(22), 100 + np.arange(8)])
        assert np.array_equal(gf.assemble(base, static, arm)[0], full[expected].astype(np.float32))
    with pytest.raises(ValueError):
        gf.assemble(base, static, "A3")
    with pytest.raises(ValueError):
        gf.assemble(base[:, :21], static, "B0")


def test_the_grid_is_sixteen_configurations_and_the_cap_is_four():
    configs = gf.configurations()
    assert len(configs) == 16 and len({tuple(c.items()) for c in configs}) == 16
    assert {c["weights"] for c in configs} == {"none", "capped_event"} and gf.EVENT_WEIGHT_CAP == 4.0
    assert gf.event_weights(np.array([0.0, 64.5, 1000.0]), gf.EVENT_WEIGHT_CAP).tolist() == [1.0, 2.0, 4.0]


def test_leave_one_year_out_never_trains_on_the_held_out_year_and_refuses_the_sealed_year():
    years = np.array([2021] * 4 + [2023] * 5 + [2024] * 3)
    for held in gf.DEVELOPMENT_YEARS:
        train, test = gf.leave_one_year_out_masks(years, held)
        assert not (train & test).any() and (train | test).all() and set(years[test]) == {held} and held not in set(years[train])
    with pytest.raises(ValueError, match="sealed year"):
        gf.leave_one_year_out_masks(np.array([2021, 2022, 2023]), 2021)
    with pytest.raises(ValueError):
        gf.leave_one_year_out_masks(years, 2022)


def _metrics(csi=0.2, bias=0.5, very_fb=0.3, zone_fb=0.8, rmse=15.0):
    return {"heavy": {"csi": csi}, "very_heavy": {"frequency_bias": very_fb}, "bias_mm": bias, "rmse_mm": rmse, "zone": {"heavy_frequency_bias": zone_fb}}


def test_guardrails_g1_to_g4_and_undefined_never_passes():
    ok = gf.guardrails_for_year(_metrics(), raw_heavy_csi=0.1)
    assert all(ok.values())
    assert gf.guardrails_for_year(_metrics(csi=0.05), 0.1)["G1"] is False
    assert gf.guardrails_for_year(_metrics(bias=-1.6), 0.1)["G2"] is False and gf.guardrails_for_year(_metrics(bias=-1.5), 0.1)["G2"] is True
    assert gf.guardrails_for_year(_metrics(very_fb=0.04), 0.1)["G3"] is False
    assert gf.guardrails_for_year(_metrics(zone_fb=1.51), 0.1)["G4"] is False and gf.guardrails_for_year(_metrics(zone_fb=1.5), 0.1)["G4"] is True
    # G4 is a loose floor: it does not flag a zone frequency bias of 1.28 (the first candidate's 2024 value, which G2 caught through the overall bias) but it flags 2x
    assert gf.guardrails_for_year(_metrics(zone_fb=1.28), 0.1)["G4"] is True
    assert gf.guardrails_for_year(_metrics(bias=5.2), 0.1)["G2"] is False
    assert gf.guardrails_for_year(_metrics(zone_fb=2.0), 0.1)["G4"] is False
    for undefined in (_metrics(csi=None), _metrics(very_fb=None), _metrics(zone_fb=None)):
        assert not all(gf.guardrails_for_year(undefined, 0.1).values())


def _result(index, rmse, **kwargs):
    return {"grid_index": index, "pooled": {"rmse_mm": rmse}, "by_year": {y: _metrics(**kwargs) for y in (2021, 2023, 2024)}}


RAW = {2021: 0.1, 2023: 0.1, 2024: 0.1}


def test_selection_needs_every_guardrail_in_every_held_out_year_and_picks_the_lowest_rmse():
    results = [_result(0, 14.0, zone_fb=2.0), _result(1, 15.0), _result(2, 14.5), _result(3, 14.5)]
    assert gf.select_configuration(results, RAW)["grid_index"] == 2                       # 0 fails G4, 1 is worse than 2, tie 2 vs 3 goes to the earlier index
    one_bad_year = _result(4, 10.0)
    one_bad_year["by_year"][2024] = _metrics(bias=7.4)                                    # the 2024-style failure disqualifies it despite the best RMSE
    assert gf.select_configuration(results + [one_bad_year], RAW)["grid_index"] == 2
    assert gf.select_configuration([_result(0, 14.0, zone_fb=2.0), one_bad_year], RAW) is None
    with pytest.raises(ValueError):
        gf.select_configuration([{"grid_index": 0, "pooled": {"rmse_mm": 1.0}, "by_year": {2021: _metrics()}}], RAW)


def test_year_metrics_reports_the_zone_frequency_bias():
    y = np.array([0.0, 70.0, 80.0, 10.0, 90.0, 0.0])
    p = np.array([0.0, 70.0, 0.0, 10.0, 100.0, 70.0])
    zone = np.array([False, True, True, False, True, False])
    m = gf.year_metrics(y, p, zone)
    assert m["zone"]["cells"] == 3 and m["zone"]["heavy_observed_events"] == 3 and m["zone"]["heavy_frequency_bias"] == pytest.approx(2 / 3)
    assert m["heavy"]["observed_events"] == 3 and m["heavy"]["false_alarms"] == 1


def test_protocol_v2_gating_reports_g3_without_gating_on_it_and_v1_behaviour_is_unchanged():
    g3_only_failure = _result(0, 14.0, very_fb=0.0)                              # fails only G3 in every year
    assert gf.select_configuration([g3_only_failure], RAW) is None               # v1 default: all four gate
    assert gf.select_configuration([g3_only_failure], RAW, gating=gf.GUARDRAILS_V2)["grid_index"] == 0
    g2_failure = _result(1, 10.0, bias=5.0)
    assert gf.select_configuration([g2_failure, g3_only_failure], RAW, gating=gf.GUARDRAILS_V2)["grid_index"] == 0     # G2 still gates
    zone_over = _result(2, 9.0, zone_fb=2.0)
    assert gf.select_configuration([zone_over], RAW, gating=gf.GUARDRAILS_V2) is None                                   # G4 still gates
    assert gf.GUARDRAILS_V2 == ("G1", "G2", "G4")
    with pytest.raises(ValueError):
        gf.select_configuration([g3_only_failure], RAW, gating=())
    with pytest.raises(ValueError):
        gf.select_configuration([g3_only_failure], RAW, gating=("G1", "G9"))


def _aligned(index, rmse, zone_csi, **kwargs):
    r = _result(index, rmse, **kwargs)
    for year in r["by_year"]:
        r["by_year"][year]["zone"] = {"heavy_frequency_bias": kwargs.get("zone_fb", 0.8), "heavy_csi": zone_csi}
    return r


def test_protocol_v3_selection_prefers_zone_csi_within_the_rmse_tolerance_and_keeps_eligibility():
    low_rmse = _aligned(0, 14.0, 0.20)
    high_csi_in_tolerance = _aligned(1, 14.15, 0.30)
    high_csi_out_of_tolerance = _aligned(2, 14.35, 0.40)                       # 0.35 mm above the floor: outside the 0.2 mm tolerance
    assert gf.select_configuration_aligned([low_rmse, high_csi_in_tolerance, high_csi_out_of_tolerance], RAW)["grid_index"] == 1
    assert gf.select_configuration(([low_rmse, high_csi_in_tolerance, high_csi_out_of_tolerance]), RAW, gating=gf.GUARDRAILS_V2)["grid_index"] == 0     # v2 would pick the lowest RMSE
    ineligible_best = _aligned(3, 14.05, 0.90, zone_fb=2.0)                    # fails G4, so it can neither win nor move the RMSE floor
    assert gf.select_configuration_aligned([low_rmse, ineligible_best], RAW)["grid_index"] == 0
    cheap = _aligned(4, 13.0, 0.10, zone_fb=2.0)                               # an ineligible configuration must not set the floor
    assert gf.select_configuration_aligned([cheap, low_rmse, high_csi_out_of_tolerance], RAW)["grid_index"] == 0
    assert gf.select_configuration_aligned([ineligible_best], RAW) is None


def test_protocol_v3_ties_and_undefined_zone_csi():
    a, b = _aligned(5, 14.10, 0.25), _aligned(6, 14.00, 0.25)
    assert gf.select_configuration_aligned([a, b], RAW)["grid_index"] == 6                  # equal CSI: lower pooled RMSE wins
    c, d = _aligned(7, 14.0, 0.25), _aligned(8, 14.0, 0.25)
    assert gf.select_configuration_aligned([d, c], RAW)["grid_index"] == 7                  # equal CSI and RMSE: earlier grid position wins
    undefined = _aligned(9, 14.0, 0.5)
    undefined["by_year"][2023]["zone"]["heavy_csi"] = None
    assert gf.mean_zone_heavy_csi(undefined) == float("-inf") and gf.select_configuration_aligned([undefined, _aligned(10, 14.1, 0.1)], RAW)["grid_index"] == 10
    with pytest.raises(ValueError):
        gf.select_configuration_aligned([a], RAW, rmse_tolerance=-0.1)
    with pytest.raises(ValueError):
        gf.select_configuration_aligned([{"grid_index": 0, "pooled": {"rmse_mm": 1.0}, "by_year": {2021: _metrics()}}], RAW)
