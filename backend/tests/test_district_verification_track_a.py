"""District verification for Track A (protocol A v1, docs/135): hash chain, one-document derivation from protocol B, stored reproduction, API for both tracks."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend.app.api import evidence

PHASE6 = Path(__file__).resolve().parents[1] / "app/evidence_data/phase6"
ROLE_2018 = "TRACK_A_2018_VALIDATION_YEAR_DEVELOPMENT_EVIDENCE"
ROLE_2019 = "TRACK_A_2019_CONSUMED_FINAL_TEST__POST_HOC_EXPLORATORY_ANALYSIS_OF_THE_COMPLETED_2019_FINAL_TEST"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(name: str) -> dict:
    return json.loads((PHASE6 / name).read_text(encoding="utf-8"))


PA, PB = load("district_verification_protocol_A_v1.json"), load("district_verification_protocol_v1.json")
MANIFEST_A = load("district_verification_manifest_A.json")


@pytest.fixture(scope="module")
def client() -> TestClient:
    from backend.main import app
    return TestClient(app)


@pytest.fixture(autouse=True)
def _fresh():
    evidence._district_manifest.cache_clear()
    evidence._district_evidence.cache_clear()
    yield
    evidence._district_manifest.cache_clear()
    evidence._district_evidence.cache_clear()


def test_hash_chain_protocol_manifest_and_evidence_files():
    assert (PHASE6 / "district_verification_protocol_A_v1.sha256").read_text(encoding="ascii").split()[0] == sha(PHASE6 / "district_verification_protocol_A_v1.json")
    assert (PHASE6 / "district_verification_manifest_A.sha256").read_text(encoding="ascii").strip() == sha(PHASE6 / "district_verification_manifest_A.json")
    assert MANIFEST_A["protocol_sha256"] == sha(PHASE6 / "district_verification_protocol_A_v1.json")
    assert set(MANIFEST_A["files"]) == {"district_verification_A_2018.json", "district_verification_A_2019.json"}
    for name, entry in MANIFEST_A["files"].items():
        assert sha(PHASE6 / name) == entry["sha256"], name
        assert load(name)["protocol_sha256"] == MANIFEST_A["protocol_sha256"] and entry["reproduction"] == "REPRODUCED"
    assert b"\r\n" not in (PHASE6 / "district_verification_protocol_A_v1.json").read_bytes()


def test_protocol_a_carries_every_definition_over_from_protocol_b_unchanged():
    for unchanged in ("models", "unit_of_analysis", "coverage_rule", "continuous_metrics", "event_definitions", "categorical_metrics", "paired_comparison", "secondary_breakdowns",
                      "region_rule", "per_district_outputs"):
        assert PA[unchanged] == PB[unchanged], unchanged
    assert PA["derived_from"]["protocol_v1_sha256"] == sha(PHASE6 / "district_verification_protocol_v1.json")
    assert PA["approval"]["decisions"] == PB["approval"]["decisions"] and "may withdraw" in PA["approval"]["note"]
    assert PA["no_results_computed"] is True and PA["status"] == "APPROVED_FOR_EXECUTION"
    assert "pooling Track A and Track B" in PA["forbidden"] and set(PA["populations"]) == {"2018", "2019"}
    assert PA["populations"]["2019"]["label"] == "POST-HOC EXPLORATORY ANALYSIS OF THE COMPLETED 2019 FINAL TEST"


def test_the_protocol_counts_were_observation_only_and_are_reproduced_by_the_evidence():
    counts = PA["observation_only_support_counts"]
    assert "no model value was read" in counts["note"]
    for year in ("2018", "2019"):
        evidence_file = load(f"district_verification_A_{year}.json")
        assert evidence_file["inclusion"]["district_case_pairs"] == counts[year]["district_case_pairs"] and evidence_file["inclusion"]["districts_included"] == counts["districts_kept"]
        for definition in ("E1", "E2", "E3"):
            for key in ("heavy", "very_heavy"):
                assert evidence_file["observed_events_pooled"][definition][key] == counts[year][key][definition]["event_pairs"]
        names = [c["check"] for c in evidence_file["reproduction"]["checks"]]
        assert evidence_file["reproduction"]["status"] == "REPRODUCED" and all(c["ok"] for c in evidence_file["reproduction"]["checks"] if "ok" in c)
        assert "pooled_raw_rmse_loop_vs_vectorised" in names and (("district_means_vs_served_grids" in names) == (year == "2019"))     # only 2019 is served by the API


def test_evidence_roles_models_and_labels():
    a, b = load("district_verification_A_2018.json"), load("district_verification_A_2019.json")
    assert (a["track"], a["evidence_role"], a["year"]) == ("A", ROLE_2018, 2018) and (b["track"], b["evidence_role"], b["year"]) == ("A", ROLE_2019, 2019)
    assert a["models"] == b["models"] == ["M0", "M1", "M2", "M3", "M4"] and a["corrected_models"] == ["M1", "M2", "M3", "M4"]
    assert a["bootstrap"]["repeats"] == 2000 and a["bootstrap"]["seed"] == 26080 and "whole cases" in a["bootstrap"]["resampling"]
    assert a["inclusion"]["districts_total"] == 188 and a["inclusion"]["districts_included"] == 169


@pytest.mark.parametrize("year,track", [(2018, "A"), (2019, "A"), (2024, "B"), (2025, "B")])
def test_the_api_serves_the_frozen_file_for_both_tracks(client, year, track):
    body = client.get(f"/api/science/evidence/district-verification?year={year}").json()
    frozen = json.loads((PHASE6 / f"district_verification_{track}_{year}.json").read_text(encoding="utf-8"))
    assert body["track"] == track and body["year"] == year and body["inclusion"] == frozen["inclusion"] and body["districts"] == frozen["districts"]
    assert body["evidence_role"] == frozen["evidence_role"] and len(body["evidence_sha256"]) == 64
    assert (body["evidence_label"] == "POST-HOC EXPLORATORY ANALYSIS OF THE COMPLETED 2019 FINAL TEST") == (year == 2019)
    assert any("Track A and Track B are never pooled" in c for c in body["caveats"])


def test_an_unserved_year_is_a_structured_404_listing_the_available_years(client):
    response = client.get("/api/science/evidence/district-verification?year=2023")
    assert response.status_code == 404 and response.json()["code"] == "SCIENCE_PRODUCT_UNAVAILABLE" and "2018, 2019, 2024, 2025" in response.json()["detail"]


@pytest.mark.parametrize("victim", ["district_verification_A_2019.json", "district_verification_protocol_A_v1.json", "district_verification_manifest_A.json"])
def test_tampered_track_a_evidence_is_refused(client, monkeypatch, victim):
    real = evidence.sha256_file
    monkeypatch.setattr(evidence, "sha256_file", lambda path: "0" * 64 if path.name == victim else real(path))
    response = client.get("/api/science/evidence/district-verification?year=2019")
    assert response.status_code == 503 and response.json()["code"] == "SCIENCE_INTEGRITY_FAILURE"


def test_tampering_with_track_a_does_not_block_track_b(client, monkeypatch):
    real = evidence.sha256_file
    monkeypatch.setattr(evidence, "sha256_file", lambda path: "0" * 64 if path.name == "district_verification_A_2019.json" else real(path))
    assert client.get("/api/science/evidence/district-verification?year=2025").status_code == 200


@pytest.mark.parametrize("format,media", [("md", "text/markdown"), ("csv", "text/csv"), ("json", "application/json")])
def test_the_track_a_report_is_labelled_and_named_for_its_track(client, format, media):
    response = client.get(f"/api/science/evidence/district-verification/report?year=2019&format={format}")
    assert response.status_code == 200 and response.headers["content-type"].startswith(media)
    assert 'filename="varshasetu_district_verification_A_2019.' in response.headers["content-disposition"]
    if format == "md":
        assert "Track A 2019" in response.text and "POST-HOC EXPLORATORY ANALYSIS OF THE COMPLETED 2019 FINAL TEST" in response.text
    if format == "json":
        assert json.loads(response.text)["track"] == "A"
