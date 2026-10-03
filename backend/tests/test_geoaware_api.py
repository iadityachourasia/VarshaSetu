"""Read-only geography-aware evidence API (docs/124, docs/126): served == frozen file, post-hoc label enforced, negative verdict kept, tamper -> 503."""

from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

from backend.app.api import geoaware

BASE = "/api/science/evidence/geoaware"
POST_HOC_2025 = "POST-HOC EXPLORATORY ANALYSIS OF THE COMPLETED 2025 FINAL TEST"


@pytest.fixture(scope="module")
def client() -> TestClient:
    from backend.main import app
    return TestClient(app)


@pytest.fixture(autouse=True)
def _fresh():
    geoaware._chain.cache_clear()
    geoaware._evaluation.cache_clear()
    yield
    geoaware._chain.cache_clear()
    geoaware._evaluation.cache_clear()


def test_overview_serves_the_negative_verdict_and_the_frozen_chain(client):
    body = client.get(f"{BASE}/overview").json()
    assert body["decision"]["adds_value"] is False and body["decision"]["geography_attribution"] is None
    assert body["status"] == "APPROVED_FOR_DEVELOPMENT_ONLY_NO_INDEPENDENT_TEST"
    assert all(len(body[k]) == 64 for k in ("protocol_sha256", "selection_freeze_sha256", "manifest_sha256"))
    assert [a["year"] for a in body["available"]] == [2024, 2025]
    assert body["selection"]["A0"]["selected"] is None and body["selection"]["A3"]["selected"] is not None
    assert len(body["configurations"]) == 64 and any("not met" in c for c in body["caveats"])


@pytest.mark.parametrize("year", [2024, 2025])
def test_evaluation_equals_the_frozen_file_and_is_labelled(client, year):
    body = client.get(f"{BASE}/evaluation?year={year}").json()
    frozen = json.loads((geoaware.PHASE9 / f"geoaware_evaluation_B_{year}.json").read_text(encoding="utf-8"))
    assert body["payload"] == frozen and len(body["evidence_sha256"]) == 64
    assert (POST_HOC_2025 in body["evidence_label"]) == (year == 2025)
    assert body["payload"]["reproduction"]["status"] == "REPRODUCED"


def test_unknown_year_is_a_structured_404(client):
    response = client.get(f"{BASE}/evaluation?year=2023")
    assert response.status_code == 404 and response.json()["code"] == "SCIENCE_PRODUCT_UNAVAILABLE"
    assert client.get(f"{BASE}/evaluation").status_code == 422


@pytest.mark.parametrize("victim", ["geoaware_evaluation_B_2025.json", "geoaware_protocol_v1.json", "geoaware_decision.json"])
def test_tampered_evidence_is_refused(client, monkeypatch, victim):
    real = geoaware.sha256_file
    monkeypatch.setattr(geoaware, "sha256_file", lambda path: "0" * 64 if path.name == victim else real(path))
    response = client.get(f"{BASE}/overview")    # the chain walk covers every manifest file, so any one mismatch blocks the whole API
    assert response.status_code == 503 and response.json()["code"] == "SCIENCE_INTEGRITY_FAILURE"


def test_unregistered_role_is_refused(client, monkeypatch):
    monkeypatch.setattr(geoaware, "EVIDENCE_LABELS", {})
    response = client.get(f"{BASE}/evaluation?year=2024")
    assert response.status_code == 503 and response.json()["code"] == "SCIENCE_INTEGRITY_FAILURE"


# ------------------------------------------------------------------------------------------------------------------ follow-up (phase 11)
FOLLOWUP = f"{BASE}/followup"


@pytest.fixture(autouse=True)
def _fresh_followup():
    geoaware._followup_chain.cache_clear()
    yield
    geoaware._followup_chain.cache_clear()


def test_followup_serves_the_frozen_selections_the_unseal_record_and_the_test_result(client):
    body = client.get(FOLLOWUP).json()
    freeze2 = json.loads((geoaware.PHASE11 / "geoaware_followup_selection_freeze_v2.json").read_text(encoding="utf-8"))
    freeze3 = json.loads((geoaware.PHASE11 / "geoaware_followup_selection_freeze_v3.json").read_text(encoding="utf-8"))
    result = json.loads((geoaware.PHASE11 / "geoaware_followup_test_2022.json").read_text(encoding="utf-8"))
    assert body["sealed_test"]["opened"] is True and body["sealed_test"]["status"] == "OPENED_ONCE_UNDER_THE_UNSEAL_RECORD" and body["sealed_test"]["sealed_at_selection_freezes"] is True
    assert body["unseal_record"]["owner_message"]["verbatim"] == "do all of three perfectly" and body["unseal_record"]["hashes_listed"] == 29
    assert body["v1_outcome"]["all_arms_without_candidate"] is True and body["development_years"] == [2021, 2023, 2024]
    for arm, block in freeze2["selection"].items():
        assert body["v2_selection"][arm]["grid_index"] == block["selected"]["grid_index"]
    for arm, block in freeze3["selection"].items():
        assert body["v3_selection"][arm]["grid_index"] == block["selected"]["grid_index"]
    assert [c["id"] for c in body["changes"]] == ["C1", "C2"] and "not an unbiased selection" in body["post_hoc_disclosure"]["consequence"]
    test = body["test_2022"]
    assert test["label"] == "INDEPENDENT TEST: first use of this year" and test["claim"] == result["claim"] and test["cases"] == result["cases"] == 173
    assert set(test["decisions"]) == {"v3_primary", "v2_secondary"}
    for key, decision in result["decisions"].items():
        served = test["decisions"][key]
        assert served["adds_value"] == decision["adds_value"] and served["candidate"] == decision["candidate"] and served["comparator"] == decision["comparator"]
        assert served["zone_heavy_csi_difference"] == decision["zone_heavy_csi_difference"] and served["level"] == 0.975
    for label, summary in test["pooled_summary"].items():
        assert summary["zone_heavy_csi"] == result["pooled"][label]["COASTAL_AND_OROGRAPHIC"]["categorical"]["heavy"]["CSI"]
    assert any("secondary" in c and "did not pass" in c for c in body["caveats"]) and any("Bonferroni" in c for c in body["caveats"])
    assert len({body[k] for k in ("protocol_v1_sha256", "protocol_v2_sha256", "protocol_v3_sha256", "freeze_v3_sha256", "unseal_record_sha256", "test_result_sha256")}) == 6


@pytest.mark.parametrize("victim", ["geoaware_followup_protocol_v1.json", "geoaware_followup_protocol_v2.json", "geoaware_followup_protocol_v3.json", "geoaware_followup_selection_freeze.json",
                                     "geoaware_followup_selection_freeze_v2.json", "geoaware_followup_selection_freeze_v3.json", "geoaware_followup_development_summary.json",
                                     "geoaware_followup_unseal_record.json", "geoaware_followup_test_2022.json"])
def test_followup_tamper_is_a_hard_failure(client, monkeypatch, victim):
    real = geoaware.sha256_file
    monkeypatch.setattr(geoaware, "sha256_file", lambda path: "0" * 64 if path.name == victim else real(path))
    response = client.get(FOLLOWUP)
    assert response.status_code == 503 and response.json()["code"] == "SCIENCE_INTEGRITY_FAILURE"


def _tamper(monkeypatch, schema: str, change):
    real = json.loads

    def tampered(text, *args, **kwargs):
        value = real(text, *args, **kwargs)
        if isinstance(value, dict) and value.get("schema") == schema:
            change(value)
        return value
    monkeypatch.setattr(geoaware.json, "loads", tampered)


def test_followup_refuses_a_freeze_that_claims_2022_was_already_open_at_freeze_time(client, monkeypatch):
    _tamper(monkeypatch, "geoaware-followup-selection-freeze-v3", lambda v: v["sealed_test"].update(opened=True))
    response = client.get(FOLLOWUP)
    assert response.status_code == 503 and response.json()["code"] == "SCIENCE_INTEGRITY_FAILURE"


def test_followup_refuses_a_test_result_that_is_not_labelled_as_the_first_use_independent_test(client, monkeypatch):
    _tamper(monkeypatch, "geoaware-followup-test-2022-v1", lambda v: v.update(label="SOMETHING ELSE"))
    response = client.get(FOLLOWUP)
    assert response.status_code == 503 and response.json()["code"] == "SCIENCE_INTEGRITY_FAILURE"


def test_followup_refuses_an_unseal_record_without_the_owner_authorisation(client, monkeypatch):
    _tamper(monkeypatch, "geoaware-followup-unseal-record-v1", lambda v: v["owner_message"].update(verbatim=""))
    response = client.get(FOLLOWUP)
    assert response.status_code == 503 and response.json()["code"] == "SCIENCE_INTEGRITY_FAILURE"
