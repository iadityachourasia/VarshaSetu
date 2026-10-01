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
