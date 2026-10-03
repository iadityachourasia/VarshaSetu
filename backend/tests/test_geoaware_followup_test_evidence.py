"""The one-shot 2022 test of the geography-aware follow-up (docs/132, docs/133): hash chain, unseal record, v3 selection re-derivation, and decisions re-derived from stored statistics."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from backend.app.ml import geoaware_followup as gf
from backend.app.ml import geoaware_followup_scoring as sc

ROOT = Path(__file__).resolve().parents[2]
PHASE11 = ROOT / "backend/app/evidence_data/phase11"
ZONE = "COASTAL_AND_OROGRAPHIC"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(name: str) -> dict:
    return json.loads((PHASE11 / name).read_text(encoding="utf-8"))


P2, P3 = load("geoaware_followup_protocol_v2.json"), load("geoaware_followup_protocol_v3.json")
F2, F3, SUMMARY = load("geoaware_followup_selection_freeze_v2.json"), load("geoaware_followup_selection_freeze_v3.json"), load("geoaware_followup_development_summary.json")
RECORD, RESULT = load("geoaware_followup_unseal_record.json"), load("geoaware_followup_test_2022.json")


def test_hash_chain_v3_record_and_result():
    for stem in ("geoaware_followup_protocol_v3", "geoaware_followup_selection_freeze_v3", "geoaware_followup_unseal_record", "geoaware_followup_test_2022"):
        assert (PHASE11 / f"{stem}.sha256").read_text(encoding="ascii").split()[0] == sha(PHASE11 / f"{stem}.json"), stem
        assert b"\r\n" not in (PHASE11 / f"{stem}.json").read_bytes()
    assert P3["supersedes"]["protocol_v2_sha256"] == sha(PHASE11 / "geoaware_followup_protocol_v2.json")
    assert F3["protocol_sha256"] == sha(PHASE11 / "geoaware_followup_protocol_v3.json") and F3["v2_selection_freeze_sha256"] == sha(PHASE11 / "geoaware_followup_selection_freeze_v2.json")
    assert RESULT["protocol_v3_sha256"] == sha(PHASE11 / "geoaware_followup_protocol_v3.json") and RESULT["unseal_record_sha256"] == sha(PHASE11 / "geoaware_followup_unseal_record.json")
    assert F3["cross_validation_checkpoint_sha256"] == F2["cross_validation_checkpoint_sha256"] == SUMMARY["checkpoint_sha256"]


def test_the_unseal_record_precedes_the_result_and_every_tracked_listed_file_still_matches():
    assert RECORD["written_before_any_2022_observation_value_was_read"] is True and RECORD["owner_message"]["verbatim"] == "do all of three perfectly"
    assert RECORD["written_at_utc"] < RESULT["run_at_utc"]
    assert len(RECORD["hashes"]) == 29 and "scoring_script" in RECORD["hashes"]
    checked = 0
    for name, entry in RECORD["hashes"].items():
        path = ROOT / entry["path"]
        if path.is_file() and (entry["path"].startswith(("backend/", "scripts/"))):
            lf = hashlib.sha256(path.read_bytes().replace(bytes([13, 10]), bytes([10]))).hexdigest()           # tolerate a CRLF checkout; .gitattributes also marks these files -text
            assert entry["sha256"] in (sha(path), lf), f"{name} changed after the unseal record"
            checked += 1
    assert checked >= 12
    assert "scoring the frozen M1 to M4 (decision 5 stays no)" in RECORD["what_is_not_authorised"]
    assert any("rehearsed on the development year 2021" in line for line in RECORD["disclosed_before_opening"])


def _results(freeze_rows):
    out = {}
    for row in SUMMARY["rows"]:
        entry = out.setdefault((row["arm"], row["grid_index"]), {"grid_index": row["grid_index"], "arm": row["arm"], "by_year": {}})
        entry["by_year"][row["held_out_year"]] = {"heavy": {"csi": row["heavy_csi"]}, "very_heavy": {"frequency_bias": row["very_heavy_frequency_bias"]}, "bias_mm": row["bias_mm"],
                                                  "zone": {"heavy_frequency_bias": row["zone_heavy_frequency_bias"], "heavy_csi": row["zone_heavy_csi"]}}
    for r in freeze_rows:
        out[(r["arm"], r["grid_index"])]["pooled"] = {"rmse_mm": r["pooled_rmse_mm"]}
    return out


def test_the_v3_selection_is_rederived_by_the_aligned_rule_from_the_stored_table():
    raw = {int(y): v for y, v in F3["development"]["raw_heavy_csi_by_year"].items()}
    results = _results(F3["all_configurations"])
    for arm in gf.ARMS:
        chosen = gf.select_configuration_aligned([r for (a, _), r in sorted(results.items()) if a == arm], raw)
        assert chosen["grid_index"] == F3["selection"][arm]["selected"]["grid_index"], arm
    assert [F3["selection"][a]["selected"]["grid_index"] for a in ("B0", "B1", "B0Z", "B1Z")] == [14, 15, 14, 15]
    assert F3["selection"]["B0"]["selected"]["model_sha256"] == F2["selection"]["B0"]["selected"]["model_sha256"]       # the shared control is one model (training is deterministic)
    assert F3["selection"]["B1"]["selected"]["model_sha256"] != F2["selection"]["B1"]["selected"]["model_sha256"]


def test_v3_differs_from_v2_only_in_the_documented_change_and_the_test_design():
    changed = {k for k in set(P2) | set(P3) if P2.get(k) != P3.get(k)}
    assert changed <= {"schema_id", "title", "supersedes", "changes", "post_hoc_disclosure", "approval", "parents", "selection", "test", "decision_rule", "evaluation", "immutability"}
    for untouched in ("model", "feature_registry", "years", "development_data_sha256", "track", "contamination_disclosure"):
        assert P2[untouched] == P3[untouched], untouched
    assert [c["id"] for c in P3["changes"]] == ["C1", "C2"] and P3["selection"]["rmse_tolerance_mm"] == gf.RMSE_TOLERANCE_MM == sc.RMSE_TOLERANCE_MM
    assert "second post-hoc change" in P3["post_hoc_disclosure"]["consequence"] and "Bonferroni" in P3["test"]["multiplicity"]["method"]
    assert P3["test"]["not_scored"].startswith("the frozen M1 to M4") and P3["evaluation"]["uncertainty"]["level_for_decision"] == 0.975


def _bootstrap(block):
    return {tuple(key.split("|")): value for key, value in block.items()}


def test_every_decision_is_rederived_from_the_stored_statistics_with_the_pure_rule():
    boot = _bootstrap(RESULT["bootstrap"]["decision_level_0975"])
    for key, stored in RESULT["decisions"].items():
        a, b = stored["candidate"], stored["comparator"]
        derived = sc.decide(a, b, RESULT["pooled"][a], RESULT["pooled"]["M0"], boot, RESULT["support"])
        for flag in ("P1_zone_heavy_csi_beats_comparator_975", "P2_overall_rmse_within_tolerance", "P3_gating_guardrails_G1_G2_G4", "adds_value", "guardrails", "level"):
            assert derived[flag] == stored[flag], (key, flag)
        assert stored["zone_heavy_csi_difference"] == boot[("diff", ZONE, a, b, "heavy_csi")]
    primary = RESULT["decisions"]["v3_primary"]
    assert RESULT["claim"] == ("ADDS_VALUE_ON_AN_INDEPENDENT_YEAR" if primary["adds_value"] else "NO_INDEPENDENT_EVIDENCE_OF_ADDED_VALUE")


def test_the_stored_decision_intervals_are_97_5_percent_and_the_95_percent_ones_are_labelled_descriptive():
    for entry in RESULT["bootstrap"]["decision_level_0975"].values():
        if entry["status"] == "ok":
            assert entry["level"] == 0.975 and "interval95" not in entry
    for entry in RESULT["bootstrap"]["descriptive_level_095"].values():
        if entry["status"] == "ok":
            assert "interval95" in entry and "level" not in entry
    assert RESULT["bootstrap"]["repeats"] == 2000 and RESULT["bootstrap"]["seed"] == 26080 and "Bonferroni" in RESULT["multiplicity"]


def test_the_test_is_what_the_protocol_says_one_year_unique_models_no_m1_to_m4_and_a_supported_zone():
    assert RESULT["label"] == "INDEPENDENT TEST: first use of this year" and RESULT["evidence_role"] == "INDEPENDENT_TEST_FIRST_USE_OF_2022" and RESULT["year"] == 2022
    assert RESULT["cases"] == 173 and RESULT["paired_cells_per_case"] == {"min": 1301, "max": 1301} and RESULT["imd_valid_cells_outside_footprint"] == 0
    expected = {}
    for freeze in (F2, F3):
        for arm, block in freeze["selection"].items():
            expected[f"{arm}#{block['selected']['grid_index']}"] = block["selected"]["model_sha256"]
    assert {label: m["model_sha256"] for label, m in RESULT["models"].items()} == expected
    assert set(RESULT["pooled"]) == {"M0", *expected} and not any(name in RESULT["pooled"] for name in ("M1", "M2", "M3", "M4"))
    assert RESULT["support"][ZONE]["heavy"]["supported"] is True and RESULT["support"][ZONE]["cells"] == 109
    cells = {label: block["ALL"]["cell_count"] for label, block in RESULT["pooled"].items()}
    assert set(cells.values()) == {173 * 1301}
    events = {label: block[ZONE]["categorical"]["heavy"]["observed_event_count"] for label, block in RESULT["pooled"].items()}
    assert len(set(events.values())) == 1 and next(iter(events.values())) == RESULT["support"][ZONE]["heavy"]["observed_event_pairs"]   # every model is scored on the same observed events
    assert RESULT["candidate_sets"]["v3_primary"] == {"candidate": "B1#15", "comparator": "B0#14"} and RESULT["candidate_sets"]["v2_secondary"] == {"candidate": "B1#8", "comparator": "B0#14"}
    assert any("frozen M1 to M4 were not scored" in limit for limit in RESULT["limits"])


def test_the_recorded_outcome_primary_passes_secondary_does_not_and_the_caveats_hold():
    primary, secondary = RESULT["decisions"]["v3_primary"], RESULT["decisions"]["v2_secondary"]
    assert primary["adds_value"] is True and secondary["adds_value"] is False
    assert primary["zone_heavy_csi_difference"]["interval"][0] > 0 and secondary["zone_heavy_csi_difference"]["interval"][1] < 0      # the RMSE-selected candidate is worse than its control
    assert primary["overall_rmse_difference"]["point"] < 0 and all(primary["guardrails"].values())
    b1, b0 = RESULT["pooled"]["B1#15"], RESULT["pooled"]["B0#14"]
    assert b1[ZONE]["categorical"]["heavy"]["frequency_bias"] > 1 > b0[ZONE]["categorical"]["heavy"]["frequency_bias"]         # the gain comes with mild zone over-forecasting
    sensitivity = RESULT["bootstrap"]["decision_level_0975"][f"diff|{ZONE}|B1Z#15|B1#15|heavy_csi"]
    assert sensitivity["interval"][0] < 0 < sensitivity["interval"][1]                                                           # no evidence the result depends on the 500 hPa height
