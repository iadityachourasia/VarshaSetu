"""Independent-years corpus v2 (2021-2022): the tracked governing records are intact, consistent and honest about sealing and eligibility (docs/127, docs/128)."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

PHASE10 = Path(__file__).resolve().parents[1] / "app/evidence_data/phase10"
ARTIFACTS = Path(__file__).resolve().parents[2] / "docs/artifacts"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(name: str, folder: Path = PHASE10) -> dict:
    return json.loads((folder / name).read_text(encoding="utf-8"))


MANIFEST = load("corpus_v2_manifest.json")
PROTOCOL = load("corpus_v2_protocol.json")


def test_every_tracked_file_matches_the_manifest_and_the_manifest_matches_its_sidecar():
    assert (PHASE10 / "corpus_v2_manifest.sha256").read_text(encoding="ascii").split()[0] == sha(PHASE10 / "corpus_v2_manifest.json")
    assert set(MANIFEST["files"]) == {p.name for p in PHASE10.glob("corpus_v2_*.json") if p.name != "corpus_v2_manifest.json"}
    for name, entry in MANIFEST["files"].items():
        assert sha(PHASE10 / name) == entry["sha256"] and (PHASE10 / name).stat().st_size == entry["bytes"], name
    assert b"\r\n" not in (PHASE10 / "corpus_v2_protocol.json").read_bytes()


def test_the_protocol_hash_chain_is_consistent_everywhere_it_is_recorded():
    protocol_sha = sha(PHASE10 / "corpus_v2_protocol.json")
    assert MANIFEST["protocol_sha256"] == protocol_sha == MANIFEST["protocol_sidecar_sha256"]
    assert load("corpus_v2_payload_corpus_summary.json")["protocol_sha256"] == protocol_sha
    assert load("corpus_v2_payload_pinned_constants.json")["protocol_sha"] == protocol_sha
    assert load("corpus_v2_payload_corpus_summary.json")["acquisition_manifest_sha256"] == MANIFEST["heavy_artifact_hashes"]["acquisition_manifest_sha256"]


def test_schedule_and_counts_follow_from_the_protocol_not_from_typed_numbers():
    assert PROTOCOL["years"] == [2021, 2022] and PROTOCOL["scheduled_initializations_total"] == 250 and PROTOCOL["scheduled_date_lead_cases_total"] == 750
    counts = MANIFEST["counts"]
    assert counts["scheduled_cases"] == PROTOCOL["scheduled_date_lead_cases_total"]
    per_init = PROTOCOL["selected_messages_per_initialization"]
    assert per_init["rainfall"] + per_init["atmosphere"] == per_init["total"] == 98
    assert counts["planned_messages"] == counts["hash_verified_messages"] == counts["metadata_valid_messages"] == PROTOCOL["scheduled_initializations_total"] * per_init["total"]
    for year, block in counts["by_year"].items():
        report = load(f"corpus_v2_payload_year_report_{year}.json")
        assert block["status"] == report["status"] == "COMPLETE" and block["scheduled_cases"] == 375
        assert block["deterministic_source_eligible"] == block["control_rainfall_qc_pass"] <= block["scheduled_cases"]
        assert block["full_five_member_rainfall_qc_pass"] <= block["deterministic_source_eligible"]


def test_year_roles_and_sealing_are_stated_and_nothing_authorises_scoring():
    roles = MANIFEST["year_roles"]
    assert roles["2021"].startswith("DEVELOPMENT") and roles["2022"].startswith("SEALED INDEPENDENT TEST")
    assert MANIFEST["sealing"] == {"2022_imd_rainfall_values_read": False, "scoring_authorized": False, "note": MANIFEST["sealing"]["note"]}
    assert PROTOCOL["test_sealing_policy"]["scoring_authorized_by_this_protocol"] is False
    audit = load("corpus_v2_holdout_seal_audit.json")
    assert audit["conclusion"] == "SEALED" and audit["static_forbidden_source_markers"] == [] and audit["outcome_named_files"] == []
    for year in (2021, 2022):
        header = load(f"corpus_v2_imd_{year}_manifest.json")["header_validation"]
        assert header["rainfall_values_read"] is False and header["required_dates_complete"] is True


def test_imd_files_are_recorded_by_hash_and_marked_non_redistributable():
    for year in (2021, 2022):
        meta = load(f"corpus_v2_imd_{year}_manifest.json")
        assert meta["sha256"] == PROTOCOL["observation_source"]["sha256"][str(year)] and len(meta["sha256"]) == 64
    assert "unresolved" in PROTOCOL["observation_source"]["redistribution"] and "must not be uploaded" in PROTOCOL["observation_source"]["redistribution"]


def test_the_july_2021_layout_change_is_disclosed_and_the_seasonal_control_is_recorded():
    analysis = load("corpus2_layout_change_qc.json", ARTIFACTS)
    assert analysis["boundary_date"] == "20210721" and analysis["before"]["cases"] + analysis["on_or_after"]["cases"] == 375
    control = analysis["seasonal_control_2022_same_calendar_split"]
    assert control["before_jul21"]["cases"] + control["on_or_after_jul21"]["cases"] == 375
    assert "no observation, model or score" in analysis["scope"]
    compat = load("corpus_v2_inventory_cross_year_compatibility.json")
    assert compat["signature_differences"] == [] and compat["material_anomalies"] == [] and len(compat["ordering_or_multiplicity_differences"]) > 0


def test_context_check_reads_observations_only_for_development_years():
    check = load("corpus2_context_check.json", ARTIFACTS)
    assert set(check["raw_gefs_by_zone"]) == {"2021", "2023", "2024"}           # no 2022 target exists and 2025 targets were never loaded
    assert "development years" in check["scope"] and "no 2022 target exists" in check["scope"] and "no model, selection or skill claim" in check["scope"]
    assert {"2022_vs_2021", "2022_vs_2023_2024", "2025_vs_2023_2024", "2021_vs_2023_2024"} <= set(check["feature_drift_standardised_mean_difference"])
    for block in check["raw_gefs_by_zone"].values():
        assert block["ALL"]["cells"] == sum(block[z]["cells"] for z in ("COASTAL", "OROGRAPHIC", "COASTAL_AND_OROGRAPHIC", "OTHER"))
