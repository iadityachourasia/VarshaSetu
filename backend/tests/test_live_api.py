"""Read-only experimental-cycle API (docs/139) against synthetic bundles in a temporary root: served equals stored, labels, staleness, withheld leads, and tamper refusal."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

import numpy as np
import pytest
from fastapi.testclient import TestClient

from backend.app.api import live as api
from backend.app.live import bundle

BASE = "/api/science/live"


@pytest.fixture(scope="module")
def client() -> TestClient:
    from backend.main import app
    return TestClient(app)


def _arrays(seed=1, products=("day1_24h",)):
    rng = np.random.default_rng(seed)
    out = {}
    for product in products:
        for name in ("M0", "M1", "M2", "M3", "M4"):
            out[f"{name}_{product}"] = rng.gamma(1.0, 3.0, (49, 49)).astype(np.float32)
        for name in ("heavy_probability", "very_heavy_probability"):
            out[f"{name}_{product}"] = rng.uniform(0, 0.2, (49, 49))
        out[f"regime_probability_{product}"] = np.array([0.2, 0.3, 0.5])
    return out


def _put(root, kind, date, products=("day1_24h",), withheld=None, extra=None):
    return bundle.write_bundle(root, kind, date, _arrays(products=products), list(products),
                               {"sources": [{"bytes": 100}, {"bytes": 250}], "withheld_products": withheld or {}, "frozen_models": {"M1": "a" * 64}, "applicability": {"status": "WITHIN_TRAINING_RANGE"}}, extra=extra)


@pytest.fixture()
def root(tmp_path, monkeypatch):
    monkeypatch.setattr(api, "ROOT", tmp_path)
    return tmp_path


def test_no_bundle_is_stated_honestly(client, root):
    body = client.get(f"{BASE}/status").json()
    assert body["has_live_cycle"] is False and body["cycles"] == [] and "No experimental cycle has been published" in body["message"]
    assert any("no verification and no skill statement" in c for c in body["caveats"]) and any("not an official warning" in c.lower() for c in body["caveats"])
    assert client.get(f"{BASE}/cycle?kind=live&date=20250926").status_code == 404


def test_replay_only_is_never_presented_as_a_live_cycle(client, root):
    _put(root, "replay", "20250926", extra={"replay_comparison": {"date": "20250926"}})
    body = client.get(f"{BASE}/status").json()
    assert body["has_live_cycle"] is False and body["latest_live"] is None and "Only historical replays" in body["message"]
    assert body["cycles"][0]["kind"] == "replay" and "not a forecast" in body["cycles"][0]["label"] and body["cycles"][0]["stale"] is False


def test_a_live_bundle_is_served_with_its_experimental_label_and_stale_flag(client, root):
    _put(root, "live", "20250926")
    body = client.get(f"{BASE}/status").json()
    assert body["has_live_cycle"] is True and body["latest_live"]["cycle"] == "20250926" and body["latest_live"]["stale"] is True and "stale" in body["message"]
    assert body["latest_live"]["season_scope"] == "JJAS_RESEARCH_SCOPE"
    assert "no verification yet" in body["latest_live"]["label"] and "not an official warning" in body["latest_live"]["label"]
    cycle = client.get(f"{BASE}/cycle?kind=live&date=20250926").json()
    assert cycle["messages"] == 2 and cycle["transferred_bytes"] == 350 and cycle["observation_read"] is False
    assert cycle["regime_probabilities"]["day1_24h"] == {"ACTIVE_MONSOON": 0.2, "BREAK_WEAK_MONSOON": 0.3, "LOW_DEPRESSION_INFLUENCED": 0.5}
    assert set(cycle["domain_statistics"]["day1_24h"]) == set(api.FIELDS) and cycle["applicability"]["status"] == "WITHIN_TRAINING_RANGE"


def test_freshness_uses_elapsed_48_hours_not_rounded_calendar_age():
    start = datetime(2026, 10, 1, tzinfo=timezone.utc)
    assert api._age_and_stale(start, start + timedelta(days=2)) == (2, False)
    assert api._age_and_stale(start, start + timedelta(days=2, seconds=1)) == (2, True)
    assert api._age_and_stale(start, start - timedelta(hours=1)) == (0, False)


def test_october_cycle_is_marked_outside_research_season(client, root):
    _put(root, "live", "20261006")
    body = client.get(f"{BASE}/status").json()
    assert body["latest_live"]["season_scope"] == "OUTSIDE_JJAS_RESEARCH_SCOPE"
    assert client.get(f"{BASE}/cycle?kind=live&date=20261006").json()["summary"]["season_scope"] == "OUTSIDE_JJAS_RESEARCH_SCOPE"


def test_a_field_equals_the_stored_array_rounded_and_carries_the_label(client, root):
    directory = _put(root, "live", "20250926")
    served = client.get(f"{BASE}/field?kind=live&date=20250926&product=day1_24h&field=M1").json()
    stored = np.load(directory / "M1_day1_24h.npy").astype(np.float64)
    assert np.array_equal(np.array(served["values"]), np.round(stored, 2)) and served["units"] == "mm per 24 h" and served["evidence_label"] == bundle.LABELS["live"]
    assert served["probability_status"] is None
    assert served["schema_version"] == "live_field_v2" and served["lead_hours"] == 24
    assert served["source_track"] == "B_OPERATIONAL_GEFS" and served["model_id"] == "M1"
    assert served["initialization_utc"] == "2025-09-26T00:00:00Z" and served["accumulation_window_hours"] == [3, 27]
    assert served["valid_cells"] == 49 * 49 and all(all(row) for row in served["valid_mask"])
    assert served["evidence_manifest_sha256"] == bundle.sha256_file(directory / "manifest.json")
    assert len(served["latitude"]) == 49 and served["latitude"][0] == 10.0 and served["longitude"][-1] == 80.0
    probability = client.get(f"{BASE}/field?kind=live&date=20250926&product=day1_24h&field=heavy_probability").json()
    assert probability["units"] == "probability" and 0 <= min(min(r) for r in probability["values"]) and max(max(r) for r in probability["values"]) <= 1
    assert probability["probability_status"] == "RESEARCH_ONLY_RELIABILITY_UNVERIFIED"
    assert served["array_sha256"] == json.loads((directory / "manifest.json").read_text(encoding="utf-8"))["arrays"]["M1_day1_24h"]["sha256"]


def test_live_district_table_uses_verified_forecast_fields_without_observations(client, root):
    directory = _put(root, "live", "20250926")
    response = client.get(f"{BASE}/districts?kind=live&date=20250926&product=day1_24h&model=M2")
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["schema_version"] == "live_district_v2" and body["lead_hours"] == 24
    assert body["initialization_utc"] == "2025-09-26T00:00:00Z"
    assert body["valid_cells"] == 49 * 49 and all(all(row) for row in body["valid_mask"])
    assert body["model_id"] == "M2" and body["source_track"] == "B_OPERATIONAL_GEFS"
    assert body["probability_status"] == "RESEARCH_ONLY_RELIABILITY_UNVERIFIED"
    assert body["district_coverage"] == "REGIONAL_ONLY_10_TO_22_N_68_TO_80_E" and body["accumulation_window_hours"] == [3, 27]
    assert body["coverage_threshold_fraction"] == 0.95 and body["withheld_district_count"] == 0
    assert all(row["weighted_grid_coverage_fraction"] == pytest.approx(1.0) for row in body["districts"])
    assert body["season_scope"] == "JJAS_RESEARCH_SCOPE"
    assert body["evidence_manifest_sha256"] == bundle.sha256_file(directory / "manifest.json")
    assert body["district_count"] == len(body["districts"]) > 0
    assert not any(key.startswith("observed") or key.startswith("imd") for row in body["districts"] for key in row)
    from backend.app.live.districts import verified_weights
    definitions, weights, _ = verified_weights()
    index = next(i for i, d in enumerate(definitions) if d["district_id"] == body["districts"][0]["district_id"])
    w = weights[index].astype(float)
    q = w / w.sum()
    expected = float(q @ np.load(directory / "M2_day1_24h.npy").ravel())
    assert body["districts"][0]["corrected_mean_mm"] == pytest.approx(expected, abs=1e-6)
    assert client.get(f"{BASE}/districts?kind=live&date=20250926&product=day2_24h").status_code == 404


def test_district_aggregation_suppresses_partial_represented_coverage_without_zero_fill():
    from backend.app.live.districts import aggregate_live
    definitions = [{"district_id": "partial", "district_name": "Partial"},
                   {"district_id": "complete", "district_name": "Complete"}]
    weights = np.zeros((2, 49 * 49), dtype=np.float32)
    weights[0, :2] = 0.5
    weights[1, 1] = 1.0
    raw = np.ones((49, 49))
    raw.flat[0] = np.nan
    rows = aggregate_live(definitions, weights, raw=raw, corrected=np.ones((49, 49)) * 2,
                          heavy_p=np.ones((49, 49)) * 0.2, very_heavy_p=np.ones((49, 49)) * 0.1)
    assert [row["district_id"] for row in rows] == ["complete"]
    assert rows[0]["weighted_grid_coverage_fraction"] == pytest.approx(1.0)
    assert rows[0]["raw_mean_mm"] == pytest.approx(1.0)


def test_a_withheld_lead_is_listed_with_its_reason_and_never_served(client, root):
    _put(root, "replay", "20250715", withheld={"day1_24h": "canonical rainfall reconstruction failed (x)", "day2_24h": "canonical rainfall reconstruction failed (y)"}, products=("day3_24h",))
    summary = client.get(f"{BASE}/status").json()["cycles"][0]
    assert summary["products"] == ["day3_24h"] and set(summary["withheld_products"]) == {"day1_24h", "day2_24h"}
    assert client.get(f"{BASE}/field?kind=replay&date=20250715&product=day1_24h&field=M1").status_code == 404
    assert client.get(f"{BASE}/field?kind=replay&date=20250715&product=day3_24h&field=M1").status_code == 200
    assert client.get(f"{BASE}/field?kind=replay&date=20250715&product=day3_24h&field=bogus").status_code == 404


@pytest.mark.parametrize("victim", ["array", "manifest"])
def test_tampered_bundles_are_refused_everywhere(client, root, victim):
    directory = _put(root, "live", "20250926")
    if victim == "array":
        array = np.load(directory / "M2_day1_24h.npy")
        array[0, 0] += 5
        np.save(directory / "M2_day1_24h.npy", array)
    else:
        (directory / "manifest.json").write_text((directory / "manifest.json").read_text(encoding="utf-8") + " ", encoding="utf-8")
    for path in (f"{BASE}/status", f"{BASE}/cycle?kind=live&date=20250926", f"{BASE}/field?kind=live&date=20250926&product=day1_24h&field=M1"):
        response = client.get(path)
        assert response.status_code == 503 and response.json()["code"] == "SCIENCE_INTEGRITY_FAILURE"


def test_bad_parameters_are_404_not_path_traversal(client, root):
    for query in ("kind=../x&date=20250926", "kind=live&date=../../etc", "kind=live&date=2025", "kind=other&date=20250926"):
        assert client.get(f"{BASE}/cycle?{query}").status_code == 404
