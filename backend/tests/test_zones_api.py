"""Read-only zone evidence API (docs/115-118): served == frozen file, post-hoc labels enforced, any tamper or broken chain -> 503."""

from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

from backend.app.api import evidence, zones

BASE = "/api/science/evidence/zones"
POST_HOC = {("A", 2019): "POST-HOC EXPLORATORY ANALYSIS OF THE COMPLETED 2019 FINAL TEST", ("B", 2025): "POST-HOC EXPLORATORY ANALYSIS OF THE COMPLETED 2025 FINAL TEST"}
YEARS = [("A", 2018), ("A", 2019), ("B", 2024), ("B", 2025)]


@pytest.fixture(scope="module")
def client() -> TestClient:
    from backend.main import app
    return TestClient(app)


@pytest.fixture(autouse=True)
def _fresh():
    zones._chain.cache_clear()
    zones._evidence.cache_clear()
    yield
    zones._chain.cache_clear()
    zones._evidence.cache_clear()


def test_overview_reports_the_frozen_chain_and_keeps_stage_3_closed(client):
    body = client.get(f"{BASE}/overview").json()
    assert body["stage_3_authorised"] is False and body["stage_3_recommended_by_pre_registered_rule"] is True
    assert body["status"] == "APPROVED_FOR_STAGES_0_TO_2" and len(body["protocol_sha256"]) == 64
    assert [(a["track"], a["year"]) for a in body["available"]] == YEARS
    assert body["decision_stage1"]["rule"] and "descriptive only" in body["decision_stage2"]["rule"]
    assert any("rule-based convention" in c for c in body["caveats"]) and any("never pooled" in c for c in body["caveats"])


def test_geography_equals_the_frozen_artifact_and_reports_zone_counts(client):
    body = client.get(f"{BASE}/geography").json()
    artifact = json.loads(zones.GEOGRAPHY.read_text(encoding="utf-8"))
    assert body["fields"]["zone"] == artifact["fields"]["zone"] and body["zone_cell_counts"] == artifact["zone_cell_counts"]
    assert sum(body["zone_cell_counts"].values()) == 1301 and body["qa"]["criteria_met"] is True
    assert set(body["zone_notes"]) == set(zones.PRE_REGISTERED_ZONES) and "CC BY 4.0" in body["source"]["distribution"]
    assert "fields" in body and "slope_m_per_km" not in body["fields"]          # only what the page needs is served


@pytest.mark.parametrize("track,year", YEARS)
def test_verification_and_forcing_serve_the_frozen_files_with_labels(client, track, year):
    for path, name in (("verification", f"zone_verification_{track}_{year}.json"), ("forcing", f"zone_stage2_{track}_{year}.json")):
        body = client.get(f"{BASE}/{path}", params={"track": track, "year": year}).json()
        assert body["payload"] == json.loads((zones.PHASE7 / name).read_text(encoding="utf-8"))
        assert body["evidence_label"] == evidence.EVIDENCE_LABELS[body["evidence_role"]]
        assert (track, year) not in POST_HOC or body["evidence_label"] == POST_HOC[(track, year)]
        assert "POST-HOC" not in body["evidence_label"] or (track, year) in POST_HOC
        assert len(body["evidence_sha256"]) == 64 and body["caveats"]


def test_unknown_year_or_track_is_a_structured_404_or_422(client):
    r = client.get(f"{BASE}/verification", params={"track": "B", "year": 2023})
    assert r.status_code == 404 and r.json()["code"] == "SCIENCE_PRODUCT_UNAVAILABLE" and "Available" in r.json()["detail"]
    assert client.get(f"{BASE}/forcing", params={"track": "C", "year": 2024}).status_code == 422


@pytest.mark.parametrize("victim", ["zone_verification_B_2025.json", "zone_stage2_B_2025.json"])
def test_tampered_evidence_file_is_refused(client, monkeypatch, victim):
    real = zones.sha256_file
    monkeypatch.setattr(zones, "sha256_file", lambda path: "0" * 64 if path.name == victim else real(path))
    path = "verification" if victim.startswith("zone_verification") else "forcing"
    response = client.get(f"{BASE}/{path}", params={"track": "B", "year": 2025})
    assert response.status_code == 503 and response.json()["code"] == "SCIENCE_INTEGRITY_FAILURE"


@pytest.mark.parametrize("victim", ["coastal_orographic_protocol_v3.json", "static_geography_v1.json", "zone_stage2_spec_v1.json",
                                    "zone_verification_manifest.json", "zone_stage2_manifest.json"])
def test_broken_chain_blocks_every_endpoint(client, monkeypatch, victim):
    real = zones.sha256_file
    monkeypatch.setattr(zones, "sha256_file", lambda path: "f" * 64 if path.name == victim else real(path))
    for url in (f"{BASE}/overview", f"{BASE}/geography"):
        response = client.get(url)
        assert response.status_code == 503 and response.json()["code"] == "SCIENCE_INTEGRITY_FAILURE", (victim, url)


def test_unregistered_role_is_refused(client, monkeypatch):
    monkeypatch.setattr(zones, "EVIDENCE_LABELS", {})
    response = client.get(f"{BASE}/verification", params={"track": "A", "year": 2018})
    assert response.status_code in (500, 503)
