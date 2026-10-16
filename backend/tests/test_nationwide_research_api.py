"""The national research view is opt-in, historical, and hash fail-closed."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend.main import app
from backend.app.api import nationwide_research as api


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("VARSHASETU_LOCAL_NATIONWIDE_RESEARCH", "1")
    return TestClient(app)


def test_disabled_by_default(monkeypatch):
    monkeypatch.delenv("VARSHASETU_LOCAL_NATIONWIDE_RESEARCH", raising=False)
    response = TestClient(app).get("/api/science/research/nationwide/overview")
    assert response.status_code == 404
RESEARCH_AVAILABLE = api.SCORE.exists() and (api.OUT / "research_land_mask.npy").is_file() and (api.OUT / "predictions").is_dir()
DISTRICT_AVAILABLE = api.DISTRICT.exists() and (api.OUT / "district_tables").is_dir()


@pytest.mark.skipif(not RESEARCH_AVAILABLE, reason="ignored local national research artifacts absent")
def test_overview_and_case_grid_are_consumed_development_only(client):
    overview = client.get("/api/science/research/nationwide/overview")
    assert overview.status_code == 200
    body = overview.json()
    assert body["cases"] == 156 and not body["m2_selection_passed"]
    assert not body["nationwide_promotion_eligible"]
    assert body["model_default"] == "regional_M2"
    assert body["probability_status"] == "RESEARCH_METHOD_AUDIT_FAILED_RELIABILITY_UNVALIDATED"
    cases = client.get("/api/science/research/nationwide/cases").json()["cases"]
    selected = cases[0]["case_id"]
    response = client.get("/api/science/research/nationwide/grid", params={"case_id": selected, "field": "M2"})
    assert response.status_code == 200
    grid = response.json()
    assert grid["status"] == "CONSUMED_2024_DEVELOPMENT_RESEARCH_ONLY"
    assert grid["grid"]["shape"] == [129, 135]
    assert sum(sum(row) for row in grid["valid_mask"]) == 5105
    assert sum(value is None for row in grid["values"] for value in row) == 129 * 135 - 5105
    probability = client.get("/api/science/research/nationwide/grid", params={"case_id": selected, "field": "very_heavy_p"}).json()
    assert probability["probability_status"] == body["probability_status"]
    assert "validation audit" in probability["caveat"]
    assert client.get("/api/science/research/nationwide/grid", params={"case_id": selected, "field": "unknown"}).status_code == 404


@pytest.mark.skipif(not RESEARCH_AVAILABLE, reason="ignored local national research artifacts absent")
def test_sealed_verification_is_same_case_and_exposes_counts_fss_uncertainty(client):
    response = client.get("/api/science/research/nationwide/verification", params={"region": "ALL_INDIA", "lead_hours": 24})
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "CONSUMED_2024_DEVELOPMENT_RESEARCH_ONLY"
    assert body["independent_skill_claim"] is False
    assert body["source_track"] == "B_OPERATIONAL_GEFS"
    assert body["reference"] == "IMD_RF25_03_TO_03_UTC"
    assert set(body["models"]) == {"M0", "M1", "M2", "M3", "M4"}
    assert set(body["uncertainty"]) == set(body["models"])
    assert {(arm["cases"], arm["cells"]) for arm in body["models"].values()} == {(body["paired_cases"], body["paired_cells"])}
    for arm in body["models"].values():
        assert arm["metrics"]["continuous"]["sample_count"] == body["paired_cells"]
        assert arm["metrics"]["heavy"]["hits"] + arm["metrics"]["heavy"]["misses"] == arm["metrics"]["heavy"]["observed_event_count"]
        assert set(arm["fss"]["heavy"]) == {"1", "3", "5"}
    assert client.get("/api/science/research/nationwide/verification", params={"region": "unknown"}).status_code == 404
    assert client.get("/api/science/research/nationwide/verification", params={"lead_hours": 12}).status_code == 404


@pytest.mark.skipif(not DISTRICT_AVAILABLE, reason="ignored local national district artifacts absent")
def test_research_district_table_never_claims_official_geometry(client):
    case_id = client.get("/api/science/research/nationwide/cases").json()["cases"][0]["case_id"]
    response = client.get("/api/science/research/nationwide/districts", params={"case_id": case_id})
    assert response.status_code == 200
    body = response.json()
    assert len(body["districts"]) == 735
    assert body["status"] == "LOCAL_RESEARCH_GEOMETRY_ONLY_NOT_OFFICIAL"
    assert all(row["supported"] for row in body["districts"])


def test_hash_receipt_rejects_modified_evidence(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("VARSHASETU_LOCAL_NATIONWIDE_RESEARCH", "1")
    path = tmp_path / "protocol.json"
    path.write_text('{"changed":true}\n', encoding="utf-8")
    path.with_suffix(".sha256").write_text("0" * 64 + "  protocol.json\n", encoding="ascii")
    monkeypatch.setattr(api, "PROTOCOL", path)
    response = TestClient(app).get("/api/science/research/nationwide/overview")
    assert response.status_code == 503
    assert response.json()["code"] == "INTEGRITY_FAILURE"
