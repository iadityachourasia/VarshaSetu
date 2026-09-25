"""Read-only validation of the frozen Phase 4D acquisition design."""

from datetime import date, timedelta
from hashlib import sha256
import json
from pathlib import Path

from backend.app.ml.forecast_regimes import FEATURE_NAMES as REGIME_NAMES
from backend.app.ml.phase2b import FEATURE_NAMES as DETERMINISTIC_NAMES


ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "experiments/recent_historical/operational_corpus_protocol_v1"


def _load(name: str) -> dict:
    return json.loads((BASE / f"{name}.json").read_text(encoding="utf-8"))


def test_protocol_and_feature_contract_hashes_are_frozen():
    for name in ("protocol", "feature_contract"):
        payload = (BASE / f"{name}.json").read_bytes()
        stated = (BASE / f"{name}.sha256").read_text(encoding="ascii").split()[0]
        assert sha256(payload).hexdigest() == stated
    assert _load("protocol")["feature_contract"]["sha256"] == sha256(
        (BASE / "feature_contract.json").read_bytes()
    ).hexdigest()


def test_every_date_and_case_is_predeclared_without_leap_ambiguity():
    p = _load("protocol")
    all_dates = []
    for year in p["years"]:
        start, end = map(date.fromisoformat, p["date_ranges_utc_inclusive"][str(year)])
        dates = [start + timedelta(days=i) for i in range((end - start).days + 1)]
        assert dates[0] == date(year, 6, 1)
        assert dates[-1] == date(year, 10, 3)
        assert len(dates) == p["scheduled_initializations_per_year"] == 125
        assert len(set(dates)) == len(dates)
        all_dates.extend(dates)
    assert len(set(all_dates)) == p["scheduled_initializations_total"] == 375
    assert len(all_dates) * len(p["forecast_leads"]) == p["scheduled_date_lead_cases_total"] == 1125
    assert date(2024, 2, 29) not in all_dates
    assert p["initialization_cycle_utc_hour"] == 0


def test_exact_leads_members_source_and_observation_contract():
    p = _load("protocol")
    assert p["rainfall_members"] == ["c00", "p01", "p02", "p03", "p04"]
    assert {k: v["window_hours"] for k, v in p["forecast_leads"].items()} == {
        "day1_24h": [3, 27], "day2_24h": [27, 51], "day3_24h": [51, 75]
    }
    assert {k: v["observation_offset_days"] for k, v in p["forecast_leads"].items()} == {
        "day1_24h": 1, "day2_24h": 2, "day3_24h": 3
    }
    rain_hours = {hour for lead in p["forecast_leads"].values() for hour in lead["rainfall_source_hours"]}
    assert sorted(rain_hours) == p["rainfall_source_hours_union"]
    assert len(rain_hours) * 5 == p["selected_messages_per_initialization"]["rainfall"] == 80
    assert len(p["required_atmospheric_variables"]) == 6
    assert p["selected_messages_per_initialization"]["atmosphere"] == 18
    assert "pgrb2sp25" in p["source_families"]["rainfall"]
    assert "pgrb2ap5" in p["source_families"]["atmosphere_a"]
    assert "pgrb2bp5" in p["source_families"]["atmosphere_b"]
    assert "date_mapping" in p["observation_source"]
    assert "timing_limitation" in p["observation_source"]


def test_feature_schema_exactly_matches_frozen_code_order():
    p = _load("protocol")
    f = _load("feature_contract")
    assert f["ordered_regime_features"] == list(REGIME_NAMES)
    assert f["ordered_deterministic_features"] == list(DETERMINISTIC_NAMES)
    assert f["ordered_probability_features"] == [
        *DETERMINISTIC_NAMES, "frozen_m2_corrected_mm", "regime_p_active",
        "regime_p_break_weak", "regime_p_low_depression",
    ]
    assert (len(f["ordered_deterministic_features"]), len(f["ordered_probability_features"])) == (22, 26)
    assert p["feature_contract"]["deterministic_count"] == 22
    assert p["feature_contract"]["probability_count"] == 26
    assert all(name in f["base_field_definitions"] or name in f["regime_derived_definitions"] for name in DETERMINISTIC_NAMES)
    assert all(name in f["probability_only_definitions"] for name in f["ordered_probability_features"][22:])


def test_split_holdout_qc_and_eligibility_are_explicit():
    p = _load("protocol")
    assert p["split_policy"]["2023"].startswith("TRAIN")
    assert p["split_policy"]["2024"].startswith("VALIDATION")
    assert p["split_policy"]["2025"].startswith("FINAL TEST")
    assert set(p["years"]) == {2023, 2024, 2025}
    assert "2025 IMD values" in p["test_sealing_policy"]["before_unseal"]
    assert "reconstruct_minimal_accumulation_window" in p["qc_version"]
    assert p["qc_policy"]["difference_bound_mm"] == "(q_total + q_prefix)/2 for each subtraction"
    assert len(p["eligibility_definitions"]) == 13
    assert "FULL_5_MEMBER_ENSEMBLE_ELIGIBLE" in p["eligibility_definitions"]
    assert "FINAL_PAIRED_EVALUATION_ELIGIBLE" in p["eligibility_definitions"]
    assert len(p["stop_conditions"]) >= 8
    assert p["source_inventory_schema"]["denominator"].startswith("all 1125")
    assert "no bulk retrieval" in p["acquisition_policy"]["phase4d"]
    assert not any(key in p for key in ("rmse", "brier", "auc", "csi", "model_performance"))
