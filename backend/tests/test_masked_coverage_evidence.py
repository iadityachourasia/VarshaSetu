"""Recompute exploratory coverage counts from the immutable small reports."""

import hashlib
import json
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]
MANIFESTS = ROOT / "data/manifests/research_pilot"
REPORTS = (
    ("2021_june_masked_coverage_result_v1", 34, 56),
    ("2026_june_masked_coverage_diagnostic_v1", 40, 50),
)


@pytest.mark.parametrize("name,passing,withheld", REPORTS)
def test_coverage_evidence_recomputes_counts_and_never_fills_missing(name, passing, withheld):
    path = MANIFESTS / f"{name}.json"
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    assert path.with_suffix(".sha256").read_text(encoding="ascii").split()[0] == digest
    report = json.loads(path.read_text(encoding="utf-8"))
    assert report["observation_read"] is False
    assert report["diagnostic_only"] is True
    anchor = ("2021_june_masked_coverage_protocol_v1.json" if name.startswith("2021")
              else "2026_forecast_corpus_protocol_v1.json")
    anchor_key = "protocol_sha256" if name.startswith("2021") else "corpus_protocol_sha256"
    assert report[anchor_key] == hashlib.sha256((MANIFESTS / anchor).read_bytes()).hexdigest()
    assert len(report["rows"]) == 30
    leads = [lead for row in report["rows"] for lead in row["leads"].values()]
    assert len(leads) == 90
    assert sum(lead["canonical_passed"] for lead in leads) == report["canonical_passing_leads"] == passing
    assert sum(not lead["canonical_passed"] for lead in leads) == report["canonical_withheld_leads"] == withheld
    for lead in leads:
        assert lead["valid_cells"] + lead["invalid_cells"] == lead["total_cells"] == 2401
        assert lead["valid_fraction"] == lead["valid_cells"] / 2401
        if lead["canonical_passed"]:
            assert lead["invalid_cells"] == 0
        else:
            assert lead["invalid_cells"] >= 1


def test_june_2026_feature_range_report_is_forecast_only_and_case_matched():
    path = MANIFESTS / "2026_june_feature_range_v1.json"
    assert path.with_suffix(".sha256").read_text(encoding="ascii").split()[0] == hashlib.sha256(path.read_bytes()).hexdigest()
    report = json.loads(path.read_text(encoding="utf-8"))
    assert report["observation_read"] is False
    assert report["model_inference"] is False
    assert report["cases"] == len(report["rows"]) == 40
    training_manifest = ROOT / "data/operational_derived/operational_features_2023_2025_v1/2023/train/year_manifest.json"
    if training_manifest.is_file():
        assert report["training_X_sha256"] == json.loads(training_manifest.read_text(encoding="utf-8"))["outputs_sha256"]["deterministic"]["features"]
    for lead, block in report["by_lead"].items():
        assert block["cases"] == sum(row["lead"] == lead for row in report["rows"])
    assert all(0 <= fraction <= 1 for row in report["rows"] for fraction in row["outside_fraction_by_feature"].values())


def test_2026_gefs_version_note_preserves_unknown_actual_transition():
    path = MANIFESTS / "2026_gefs_model_change_note_v1.json"
    assert path.with_suffix(".sha256").read_text(encoding="ascii").split()[0] == hashlib.sha256(path.read_bytes()).hexdigest()
    note = json.loads(path.read_text(encoding="utf-8"))
    assert note["announced_effective_cycle_utc"] == "2026-06-15T12:00:00Z"
    assert note["selected_fields_explicitly_named_as_changed_by_notice"] == []
    assert note["test_year_status"] == "CANDIDATE_NOT_CLEARED"
    assert note["observation_read"] is False


def test_2026_prior_observation_audit_remains_a_candidate():
    path = MANIFESTS / "2026_prior_observation_use_audit_v1.json"
    assert path.with_suffix(".sha256").read_text(encoding="ascii").split()[0] == hashlib.sha256(path.read_bytes()).hexdigest()
    audit = json.loads(path.read_text(encoding="utf-8"))
    assert audit["prior_use_gate"].startswith("PROVISIONALLY_CLEARED")
    assert audit["test_year_status"] == "CANDIDATE_NOT_YET_SCORED"
    assert audit["observation_values_read_for_this_audit"] is False
    followup = MANIFESTS / "2026_prior_observation_use_audit_v2.json"
    assert followup.with_suffix(".sha256").read_text(encoding="ascii").split()[0] == hashlib.sha256(followup.read_bytes()).hexdigest()
    second = json.loads(followup.read_text(encoding="utf-8"))
    assert second["previous_audit_sha256"] == hashlib.sha256(path.read_bytes()).hexdigest()
    assert second["additional_local_checks"]["data_raw_observation_path_absent"] is True
    assert second["test_year_status"] == "CANDIDATE_NOT_YET_SCORED"
