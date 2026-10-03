"""Production hardening: one version source, honest health, retired legacy audit routes, explicit CORS, best-effort warm-up."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from backend.app import version
from backend.app.api import routes
from backend.app.core import cors


@pytest.fixture(scope="module")
def client() -> TestClient:
    from backend.main import app
    return TestClient(app)


# ------------------------------------------------------------------ version
def test_version_is_one_constant_used_everywhere(client):
    from backend.main import app
    assert app.version == version.API_VERSION and "phase0" not in version.API_VERSION
    health = client.get("/api/health").json()
    assert health["version"] == version.API_VERSION == client.get("/").json()["version"]
    assert client.get("/openapi.json").json()["info"]["version"] == version.API_VERSION


def test_commit_comes_from_the_environment_never_from_git():
    assert version.deployed_commit({"RENDER_GIT_COMMIT": "a" * 50}) == "a" * 40
    assert version.deployed_commit({"GIT_COMMIT": "abc123"}) == "abc123"
    assert version.deployed_commit({}) == "unknown" and version.deployed_commit({"RENDER_GIT_COMMIT": "  "}) == "unknown"


# ------------------------------------------------------------------ health and legacy routes
def test_health_is_liveness_and_does_not_need_the_legacy_dataset(client, monkeypatch):
    def unavailable():
        raise FileNotFoundError("GOA_CLEAN.csv is not part of the deployed image")
    monkeypatch.setattr(routes.pipeline_service, "ensure_loaded", unavailable)
    body = client.get("/api/health")
    assert body.status_code == 200
    assert body.json()["status"] == "ok" and body.json()["legacy_prototype"].startswith("quarantined")
    assert body.json()["scientific_api"] == "/api/science/status"


@pytest.mark.parametrize("path", ["/api/status", "/api/dataset/audit", "/api/stations", "/api/provenance", "/api/metrics/overall", "/api/metrics/regimes"])
def test_missing_legacy_dataset_is_a_structured_410_not_a_500(client, monkeypatch, path):
    def unavailable():
        raise FileNotFoundError("missing")
    monkeypatch.setattr(routes.pipeline_service, "ensure_loaded", unavailable)
    response = client.get(path)
    assert response.status_code == 410
    assert response.json()["code"] == "LEGACY_DATASET_UNAVAILABLE" and "/api/science" in response.json()["detail"]


@pytest.mark.parametrize("path,replacement", [("/api/audit", "ps-coverage"), ("/api/jury-defense", "JUDGE_QA")])
def test_static_audit_endpoints_are_retired_whatever_the_dataset_state(client, path, replacement):
    response = client.get(path)
    assert response.status_code == 410
    body = response.json()
    assert body["code"] == "LEGACY_ENDPOINT_RETIRED" and replacement in body["detail"] and "PASS" not in str(body)


def test_legacy_blocked_gate_and_scientific_api_are_unchanged(client):
    assert client.get("/api/metrics/overall").status_code in (409, 410)
    if client.get("/api/metrics/overall").status_code == 409:
        assert client.get("/api/metrics/overall").json()["detail"]["status"] == "blocked_by_scientific_readiness_gate"
    assert client.get("/api/health").status_code == 200
    assert client.get("/api/science/evidence/manifest").status_code == 200


# ------------------------------------------------------------------ CORS
def test_cors_allows_named_origins_without_credentials(client):
    origin = "https://varshasetu.vercel.app"
    preflight = client.options("/api/health", headers={"Origin": origin, "Access-Control-Request-Method": "GET"})
    assert preflight.status_code == 200 and preflight.headers["access-control-allow-origin"] == origin
    assert "access-control-allow-credentials" not in preflight.headers
    simple = client.get("/api/health", headers={"Origin": origin})
    assert simple.headers["access-control-allow-origin"] == origin and "access-control-allow-credentials" not in simple.headers


@pytest.mark.parametrize("origin", ["https://evil.example", "https://varshasetu.vercel.app.evil.example", "http://localhost:9999", "null"])
def test_cors_refuses_other_origins(client, origin):
    response = client.get("/api/health", headers={"Origin": origin})
    assert response.status_code == 200 and "access-control-allow-origin" not in response.headers
    preflight = client.options("/api/health", headers={"Origin": origin, "Access-Control-Request-Method": "GET"})
    assert "access-control-allow-origin" not in preflight.headers


def test_cors_methods_are_read_only(client):
    preflight = client.options("/api/health", headers={"Origin": "http://localhost:3100", "Access-Control-Request-Method": "POST"})
    assert preflight.status_code == 400                      # POST is not an allowed cross-origin method


def test_cors_configuration_helper():
    assert "*" not in cors.DEFAULT_ORIGINS and cors.allowed_origins({}) == list(cors.DEFAULT_ORIGINS)
    assert cors.allowed_origins({"CORS_ALLOW_ORIGINS": "https://a.example/, https://b.example"}) == ["https://a.example", "https://b.example"]
    for bad in ("*", "https://a.example,*", " , "):
        with pytest.raises(ValueError):
            cors.allowed_origins({"CORS_ALLOW_ORIGINS": bad})


# ------------------------------------------------------------------ warm-up
def test_warmup_fills_the_evidence_caches():
    from backend.app.api import evidence, zones
    from backend.main import warm_evidence_caches
    for cache in (evidence._manifest, evidence._coverage, zones._chain, evidence._district_manifest):
        cache.cache_clear()
    assert set(warm_evidence_caches().values()) == {"ok"}
    assert zones._chain.cache_info().currsize == 1 and evidence._coverage.cache_info().currsize == 1


def test_warmup_never_raises_and_does_not_hide_a_later_integrity_failure(monkeypatch, client):
    from backend.app.api import zones
    from backend.main import warm_evidence_caches
    zones._chain.cache_clear()
    real = zones.sha256_file
    monkeypatch.setattr(zones, "sha256_file", lambda path: "0" * 64 if path.name == "static_geography_v1.json" else real(path))
    outcome = warm_evidence_caches()
    assert outcome["zone_chain"].startswith("failed") and outcome["evidence_manifest"] == "ok"
    response = client.get("/api/science/evidence/zones/overview")
    assert response.status_code == 503 and response.json()["code"] == "SCIENCE_INTEGRITY_FAILURE"
    zones._chain.cache_clear()
