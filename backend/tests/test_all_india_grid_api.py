"""All-India Raw map API: frozen ledger, local array hashes and honest domain semantics."""

from __future__ import annotations

import numpy as np
import pytest
from fastapi.testclient import TestClient

from backend.app.api import all_india_raw as api
from backend.main import app


@pytest.fixture(scope="module")
def client() -> TestClient:
    return TestClient(app)


def test_catalogue_uses_only_sealed_included_cases(client):
    response = client.get("/api/science/evidence/all-india-raw/cases?year=2025")
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["year"] == 2025 and len(body["cases"]) == 167
    assert all(case["case_id"].startswith("2025") and case["product"] in api.WINDOWS for case in body["cases"])
    assert all(case["accumulation_window_hours"] == list(api.WINDOWS[case["product"]]) for case in body["cases"])
    assert client.get("/api/science/evidence/all-india-raw/cases?year=2026").status_code == 404


@pytest.mark.skipif(not (api.ROOT / "data/operational_derived/all_india_raw_v1/2025/20250926_day1_24h.npy").exists(), reason="ignored local Raw cache absent")
def test_historical_raw_grid_is_same_hashed_array_with_research_display_mask(client):
    case_id = "20250926_day1_24h"
    response = client.get(f"/api/science/evidence/all-india-raw/grid?year=2025&case_id={case_id}")
    assert response.status_code == 200, response.text
    body = response.json()
    entry = next(e for e in api._included(2025) if e["case_id"] == case_id)
    stored = np.load(api._cache_path(entry, 2025), allow_pickle=False)
    assert body["raw_array_sha256"] == entry["sha256"] and np.array_equal(np.asarray(body["values"]), stored)
    assert np.asarray(body["display_mask"]).shape == (129, 135)
    assert body["grid"]["shape"] == [129, 135] and body["source_track"] == "B_OPERATIONAL_GEFS"
    assert body["field"] == "M0_RAW_GEFS" and body["accumulation_window_hours"] == [3, 27]
    assert "not official" in body["caveat"] and "No correction" in body["caveat"]
    assert "corrected" not in body and "observed" not in body


def test_grid_refuses_unlisted_case_and_missing_cache(client, monkeypatch, tmp_path):
    assert client.get("/api/science/evidence/all-india-raw/grid?year=2025&case_id=20250101_day1_24h").status_code == 404
    monkeypatch.setattr(api, "_cache_path", lambda entry, year: tmp_path / "absent.npy")
    assert client.get("/api/science/evidence/all-india-raw/grid?year=2025&case_id=20250926_day1_24h").status_code == 404


def test_grid_refuses_changed_bytes_before_decoding(client, monkeypatch, tmp_path):
    changed = tmp_path / "changed.npy"
    np.save(changed, np.ones((129, 135)))
    monkeypatch.setattr(api, "_cache_path", lambda entry, year: changed)
    response = client.get("/api/science/evidence/all-india-raw/grid?year=2025&case_id=20250926_day1_24h")
    assert response.status_code == 503 and response.json()["code"] == "SCIENCE_INTEGRITY_FAILURE"


def test_small_offline_bundle_serves_the_same_raw_bytes_without_large_cache(client, monkeypatch, tmp_path):
    from scripts.build_india_map_demo_bundle import check

    check()
    monkeypatch.setattr(api, "ROOT", tmp_path)
    entry = next(e for e in api._included(2025) if e["case_id"] == "20250926_day1_24h")
    assert api._cache_path(entry, 2025) == api.BUNDLE / "20250926_day1_24h.npy"
    response = client.get("/api/science/evidence/all-india-raw/grid?year=2025&case_id=20250926_day1_24h")
    assert response.status_code == 200 and response.json()["raw_array_sha256"] == entry["sha256"]
