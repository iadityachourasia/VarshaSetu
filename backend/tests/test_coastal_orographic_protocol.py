"""Frozen coastal/orographic protocol v1 (P0-7): byte hash, doc agreement and the guards that keep the requirement honest."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PHASE6 = ROOT / "backend/app/evidence_data/phase6"
PROTOCOL = PHASE6 / "coastal_orographic_protocol_v1.json"
DOC = ROOT / "docs/115_COASTAL_OROGRAPHIC_REGIME_PROTOCOL.md"
COVERAGE = json.loads((PHASE6 / "ps_coverage.json").read_text(encoding="utf-8"))
P = json.loads(PROTOCOL.read_text(encoding="utf-8"))


def test_protocol_bytes_match_sidecar_and_the_hash_quoted_in_the_document():
    digest = hashlib.sha256(PROTOCOL.read_bytes()).hexdigest()
    sidecar = (PHASE6 / "coastal_orographic_protocol_v1.sha256").read_text(encoding="utf-8").split()[0]
    assert digest == sidecar
    assert digest in DOC.read_text(encoding="utf-8")
    assert b"\r\n" not in PROTOCOL.read_bytes()


def test_scope_is_limited_to_stages_zero_to_two_and_changes_no_frozen_model():
    assert P["status"] == "APPROVED_FOR_STAGES_0_TO_2" and P["approval"]["approved_before_any_zone_result"] is True
    assert P["design"]["frozen_models_modified"] is False and P["design"]["taxonomy_is_flat"] is False
    for stage in ("0", "1", "2"):
        assert P["stages"][stage]["training"] is False and P["stages"][stage]["new_model"] is False
    assert P["stages"]["3"]["authorised"] is False
    assert P["leakage"]["feature_registry_v1_edited"] is False and P["leakage"]["static_fields_are_model_inputs_in_stages_0_to_2"] is False


def test_zone_rules_are_the_approved_values_and_not_exclusive():
    zones = P["zones"]
    assert zones["mutually_exclusive"] is False and zones["primary_zones_reselected_after_results"] is False
    assert zones["labels"]["COASTAL"]["distance_to_coast_km_max"] == 100.0
    assert zones["labels"]["OROGRAPHIC"] == {"mean_elevation_m_min": 400.0, "or_local_relief_m_min": 300.0}
    assert P["support_gate"] == {"min_cells": 20, "min_cases": 30, "min_observed_event_cell_case_pairs": 30,
                                 "otherwise": "insufficient_support with counts, no number"}


def test_final_test_years_stay_post_hoc_and_tracks_are_not_pooled():
    pops = P["populations"]
    assert pops["pooling_across_tracks"] is False
    assert pops["A"]["consumed_final_test_post_hoc"] == 2019 and pops["B"]["consumed_final_test_post_hoc"] == 2025
    assert set(pops["post_hoc_labels"]) == {"2019", "2025"} and all("POST-HOC" in v for v in pops["post_hoc_labels"].values())
    assert P["thresholds_mm_per_24h"] == {"heavy": 64.5, "very_heavy": 115.6}
    assert "rainfall" in P["forcing_strength"]["forbidden_inputs"]


def test_the_requirement_is_partial_only_because_stage_1_and_2_evidence_exists_and_never_implemented():
    row = next(r for r in COVERAGE["rows"] if r["id"] == "REGIME-COASTAL-OROGRAPHIC")
    assert row["status"] == "IMPLEMENTED" and row["ps_mandatory"]       # IMPLEMENTED only through the validated sealed-year detector (docs/142); the Stage 3 correction model is still not authorised
    assert {f["source"].split(":")[0] for f in row["facts"]} == {"zone", "coastalregime", "reforecast"} and len([f for f in row["facts"] if f["source"].startswith("zone:")]) >= 8
    for doc in ("115_COASTAL_OROGRAPHIC_REGIME_PROTOCOL", "116_STATIC_GEOGRAPHY_STAGE0", "117_ZONE_VERIFICATION_STAGE1", "118_ZONE_FORCING_STAGE2"):
        assert f"docs/{doc}.md" in row["docs"]
    assert P["coverage_status_mapping"]["today"] == "PLANNED"            # v1 wording at freeze time; the mapping below is what authorised the change
    assert P["coverage_status_mapping"]["stages_1_2_complete"] == "PARTIAL"
    assert P["stages"]["3"]["authorised"] is False


def test_document_states_the_gate_and_the_feasibility_counts_match_the_footprint_sizes():
    text = DOC.read_text(encoding="utf-8")
    assert "P0_7_PROTOCOL_APPROVED_FROZEN" in text
    assert re.search(r"\| Valid cells \(of 1,301\) \| 74 \| 102 \| 178 \| 274 \| 413 \|", text)
    assert P["grid"]["valid_cells_per_case"] == 1301
