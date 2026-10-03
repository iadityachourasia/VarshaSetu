"""Geography-aware follow-up (docs/129, docs/130): hash chain, independent re-derivation of the 'no candidate' outcome, and sealing of 2022."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from backend.app.ml import geoaware_followup as gf

PHASE10 = Path(__file__).resolve().parents[1] / "app/evidence_data/phase10"
PHASE11 = Path(__file__).resolve().parents[1] / "app/evidence_data/phase11"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(name: str, folder: Path = PHASE11) -> dict:
    return json.loads((folder / name).read_text(encoding="utf-8"))


PROTOCOL, FREEZE, SUMMARY = load("geoaware_followup_protocol_v1.json"), load("geoaware_followup_selection_freeze.json"), load("geoaware_followup_development_summary.json")


def test_hash_chain_protocol_freeze_summary():
    for stem in ("geoaware_followup_protocol_v1", "geoaware_followup_selection_freeze", "geoaware_followup_development_summary"):
        assert (PHASE11 / f"{stem}.sha256").read_text(encoding="ascii").split()[0] == sha(PHASE11 / f"{stem}.json"), stem
        assert b"\r\n" not in (PHASE11 / f"{stem}.json").read_bytes()
    assert FREEZE["protocol_sha256"] == SUMMARY["protocol_sha256"] == sha(PHASE11 / "geoaware_followup_protocol_v1.json")
    assert SUMMARY["selection_freeze_sha256"] == sha(PHASE11 / "geoaware_followup_selection_freeze.json")
    assert PROTOCOL["parents"]["corpus_v2_evidence_manifest_sha256"] == sha(PHASE10 / "corpus_v2_manifest.json")
    assert FREEZE["development"]["input_sha256"] == PROTOCOL["development_data_sha256"]


def test_protocol_matches_the_code_and_the_approval_is_recorded_with_its_limits():
    assert PROTOCOL["status"] == "APPROVED_FOR_DEVELOPMENT_SELECTION_ONLY_TEST_SEALED" and PROTOCOL["years"] == {"development": list(gf.DEVELOPMENT_YEARS), "sealed_test": 2022}
    assert PROTOCOL["feature_registry"]["arms"] == gf.ARMS and PROTOCOL["model"]["event_weight"]["cap"] == gf.EVENT_WEIGHT_CAP == 4.0
    assert PROTOCOL["selection"]["guardrails"]["G4"].startswith("heavy-rain forecast frequency bias in the coastal-and-orographic zone at most 1.5")
    approval = PROTOCOL["approval"]
    assert approval["approved_before_any_training"] is True and "not an explicit item-by-item approval" in approval["interpretation"]
    assert "NO" in approval["not_approved"]["scoring_of_frozen_M1_to_M4_on_2022"] and "unresolved" in approval["not_approved"]["D2_imd_redistribution"]
    assert "separate signed unseal record" in approval["unseal"]
    assert "development_data_sha256" in PROTOCOL and set(PROTOCOL["development_data_sha256"]) == {"2021", "2023", "2024"}     # 2022 appears in no input list


def test_no_arm_has_a_candidate_and_this_is_rederived_from_the_stored_guardrails():
    table = FREEZE["all_configurations"]
    assert len(table) == 64 and {r["arm"] for r in table} == set(gf.ARMS)
    for r in table:
        flags = [ok for gs in r["guardrails_by_year"].values() for ok in gs.values()]
        assert set(r["guardrails_by_year"]) == {"2021", "2023", "2024"} and len(flags) == 12
        assert r["passes_in_every_year"] == all(flags)
    assert not any(r["passes_in_every_year"] for r in table)
    assert all(block["selected"] is None and "no configuration passed G1 to G4" in block["reason"] for block in FREEZE["selection"].values())


def test_selection_outcome_follows_from_the_per_year_metrics_with_the_pure_rule():
    by_arm: dict[str, list[dict]] = {a: [] for a in gf.ARMS}
    raw = {int(y): v for y, v in FREEZE["development"]["raw_heavy_csi_by_year"].items()}
    for row in SUMMARY["rows"]:
        by_arm_row = next((r for r in by_arm[row["arm"]] if r["grid_index"] == row["grid_index"]), None)
        if by_arm_row is None:
            by_arm_row = {"grid_index": row["grid_index"], "pooled": {"rmse_mm": 0.0}, "by_year": {}}
            by_arm[row["arm"]].append(by_arm_row)
        by_arm_row["by_year"][row["held_out_year"]] = {"heavy": {"csi": row["heavy_csi"]}, "very_heavy": {"frequency_bias": row["very_heavy_frequency_bias"]}, "bias_mm": row["bias_mm"],
                                                       "zone": {"heavy_frequency_bias": row["zone_heavy_frequency_bias"]}}
    for arm, results in by_arm.items():
        assert len(results) == 16
        assert gf.select_configuration(results, raw) is None, arm                  # the stored metrics and the pure rule agree with the freeze
        for result in results:               # and the stored guardrail flags equal the flags recomputed from the stored metrics
            stored = next(r for r in FREEZE["all_configurations"] if r["arm"] == arm and r["grid_index"] == result["grid_index"])
            for year, metrics in result["by_year"].items():
                assert gf.guardrails_for_year(metrics, raw[year]) == stored["guardrails_by_year"][str(year)]


def test_the_development_comparison_of_geography_against_the_control_is_stated_and_labelled():
    counts = SUMMARY["b1_versus_b0_counts"]
    assert counts["configurations"] == 16 and counts["zone_heavy_csi_higher_in_every_held_out_year"] == sum(
        all(c["zone_heavy_csi_b1_minus_b0"][y] > 0 for y in ("2021", "2023", "2024")) for c in SUMMARY["b1_versus_b0"])
    assert counts["pooled_rmse_lower"] == sum(c["pooled_rmse_b1_minus_b0_mm"] < 0 for c in SUMMARY["b1_versus_b0"])
    assert "not a test result" in SUMMARY["scope"] and "sealed 2022 was not opened" in SUMMARY["scope"]


def test_the_sealed_year_was_not_opened_by_the_selection():
    assert FREEZE["sealed_test"] == {"year": 2022, "opened": False, "note": FREEZE["sealed_test"]["note"]} and "no 2022 feature, target or observation was read" in FREEZE["sealed_test"]["note"]
    assert FREEZE["development"]["years"] == [2021, 2023, 2024]
    assert not any(row["held_out_year"] == 2022 for row in SUMMARY["rows"])
    features_freeze = Path(__file__).resolve().parents[2] / "data/operational_derived/v2/features/feature_generation_manifest_v1.json"
    if features_freeze.exists():
        assert json.loads(features_freeze.read_text(encoding="utf-8"))["observation_values_opened"]["2022"] is False
