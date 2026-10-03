"""Forecast-time coastal/orographic forcing regime (protocol v1, docs/137): hash chain, classes re-derived from the frozen cut-points, honest decision, API, tamper refusal."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import pytest
from fastapi.testclient import TestClient

from backend.app.api import coastal_regime as api
from backend.app.ml import coastal_regime as cr

PHASE12 = Path(__file__).resolve().parents[1] / "app/evidence_data/phase12"
PHASE7 = Path(__file__).resolve().parents[1] / "app/evidence_data/phase7"
BASE = "/api/science/evidence/coastal-regime"
POPULATIONS = {"A2018": ("A", 2018), "A2019": ("A", 2019), "B2024": ("B", 2024), "B2025": ("B", 2025)}


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(name: str) -> dict:
    return json.loads((PHASE12 / name).read_text(encoding="utf-8"))


PROTOCOL, MANIFEST, CASES = load("coastal_regime_protocol_v1.json"), load("coastal_regime_manifest.json"), load("coastal_regime_cases_v1.json")
RESULTS = {pop: load(f"coastal_regime_{t}_{y}.json") for pop, (t, y) in POPULATIONS.items()}


@pytest.fixture(scope="module")
def client() -> TestClient:
    from backend.main import app
    return TestClient(app)


@pytest.fixture(autouse=True)
def _fresh():
    api._chain.cache_clear()
    api._result.cache_clear()
    yield
    api._chain.cache_clear()
    api._result.cache_clear()


def test_hash_chain():
    assert (PHASE12 / "coastal_regime_protocol_v1.sha256").read_text(encoding="ascii").split()[0] == sha(PHASE12 / "coastal_regime_protocol_v1.json")
    assert (PHASE12 / "coastal_regime_manifest.sha256").read_text(encoding="ascii").strip() == sha(PHASE12 / "coastal_regime_manifest.json")
    assert PROTOCOL["definition"]["cases_file_sha256"] == MANIFEST["cases_file_sha256"] == sha(PHASE12 / "coastal_regime_cases_v1.json") and MANIFEST["protocol_sha256"] == sha(PHASE12 / "coastal_regime_protocol_v1.json")
    assert PROTOCOL["definition"]["static_geography_sha256"] == sha(PHASE7 / "static_geography_v1.json")
    assert set(MANIFEST["files"]) == {f"coastal_regime_{t}_{y}.json" for t, y in POPULATIONS.values()}
    for name, entry in MANIFEST["files"].items():
        assert sha(PHASE12 / name) == entry["sha256"] and load(name)["protocol_sha256"] == MANIFEST["protocol_sha256"]
    assert CASES["cut_points"] == PROTOCOL["definition"]["cut_points"]


def test_the_protocol_is_forecast_only_fitted_on_training_years_and_labelled_a_heuristic():
    assert PROTOCOL["no_observation_read"] is True and "not a learned or validated regime" in PROTOCOL["purpose"]
    cuts = PROTOCOL["definition"]["cut_points"]
    assert cuts["A"]["training_year"] == 2017 and cuts["B"]["training_year"] == 2023 and not cuts["A"]["degenerate"] and not cuts["B"]["degenerate"]
    assert cuts["A"]["q33"] < cuts["A"]["q67"] and cuts["B"]["q33"] < cuts["B"]["q67"]
    assert "no observation and no model output" in PROTOCOL["definition"]["inputs"] and "pooling Track A and Track B" in PROTOCOL["forbidden"]
    assert "fitting a threshold on any validation or test year" in PROTOCOL["forbidden"] and "may" in PROTOCOL["approval"]["note"]
    for name, population in PROTOCOL["populations"].items():
        assert population["label"] == {"A2018": "Track A 2018 validation year: development evidence", "A2019": "POST-HOC EXPLORATORY ANALYSIS OF THE COMPLETED 2019 FINAL TEST",
                                       "B2024": "Track B 2024 validation/selection year: development evidence", "B2025": "POST-HOC EXPLORATORY ANALYSIS OF THE COMPLETED 2025 FINAL TEST"}[name]


def test_every_stored_class_and_percentile_follows_from_the_stored_index_and_the_frozen_cut_points():
    for name, (track, _) in POPULATIONS.items():
        rows = CASES["populations"][name]
        cuts = CASES["cut_points"][track]
        counts = {c: 0 for c in cr.CLASSES}
        for row in rows:
            klass = cr.classify(float("nan") if row["index"] is None else row["index"], cuts)
            assert (None if klass is None else cr.CLASSES[klass]) == row["class"], (name, row["case_id"])
            assert row["percentile_vs_training"] is None or 0.0 <= row["percentile_vs_training"] <= 1.0
            if row["class"] is not None:
                counts[row["class"]] += 1
        assert {c: PROTOCOL["populations"][name]["forecast_only_counts"][c] for c in cr.CLASSES} == counts
        assert [r["case_id"] for r in rows] == sorted(r["case_id"] for r in rows) or track == "A"


def test_scores_reproduce_stage_1_and_partition_the_events():
    for name, result in RESULTS.items():
        assert result["observed_heavy_event_pairs"] == result["stage1_heavy_event_pairs"] and result["reproduction"]["status"] == "REPRODUCED"
        groups = result["groups"]
        assert sum(g["heavy_event_pairs"] for g in groups.values()) == result["observed_heavy_event_pairs"] and sum(g["cases"] for g in groups.values()) == result["cases"]
        assert sum(g["share_of_all_heavy_event_pairs"] for g in groups.values()) == pytest.approx(1.0)
        assert result["supported"] == cr.supported(groups)
        stage1 = json.loads((PHASE7 / f"zone_verification_{result['track']}_{result['year']}.json").read_text(encoding="utf-8"))
        assert stage1["support"]["COASTAL_AND_OROGRAPHIC"]["heavy"]["observed_event_pairs"] == result["observed_heavy_event_pairs"]
        d = result["discrimination"]
        for key in ("strong_minus_weak_heavy_fraction", "spearman"):
            low, high = d[key]["interval95"]
            assert low <= d[key]["point"] <= high


def test_the_decision_is_rederived_from_the_stored_development_intervals_and_post_hoc_years_cannot_change_it():
    development = [RESULTS["A2018"], RESULTS["B2024"]]
    met = all(r["supported"] and r["discrimination"]["strong_minus_weak_heavy_fraction"]["point"] > 0 and r["discrimination"]["strong_minus_weak_heavy_fraction"]["excludes_zero"] for r in development)
    assert MANIFEST["decision"]["discriminates"] is met is True
    assert "not a validated or learned regime" in MANIFEST["decision"]["wording"]
    assert [r["development"] for r in development] == [True, True] and RESULTS["A2019"]["development"] is False and RESULTS["B2025"]["development"] is False
    assert "cannot change the decision" in PROTOCOL["decision_rule"]["post_hoc_populations"]


def test_recorded_findings_strong_class_holds_most_events_and_the_class_shares_shift_in_later_years():
    for name, result in RESULTS.items():
        strong = result["groups"]["STRONG"]
        assert strong["share_of_all_heavy_event_pairs"] > 0.8 and result["discrimination"]["spearman"]["point"] > 0.5, name
        assert result["groups"]["WEAK"]["mean_heavy_fraction"] < result["groups"]["MODERATE"]["mean_heavy_fraction"] < strong["mean_heavy_fraction"]
        assert strong["cases"] / result["cases"] > 1 / 3 + 0.1                       # the training-year terciles put well over a third of later cases in STRONG: stated, not hidden
    assert "heuristic" in RESULTS["B2025"]["regime_nature"] and "not a probability" in RESULTS["B2025"]["regime_nature"]


@pytest.mark.parametrize("year", [2018, 2019, 2024, 2025])
def test_the_api_serves_the_frozen_files(client, year):
    track = {2018: "A", 2019: "A", 2024: "B", 2025: "B"}[year]
    result = client.get(f"{BASE}/result?year={year}").json()
    assert result["payload"] == json.loads((PHASE12 / f"coastal_regime_{track}_{year}.json").read_text(encoding="utf-8")) and result["year"] == year
    assert (result["evidence_label"].startswith("POST-HOC")) == (year in (2019, 2025))
    served = client.get(f"{BASE}/cases?year={year}").json()
    assert served["cases"] == CASES["populations"][f"{track}{year}"] and served["cut_points"] == CASES["cut_points"][track]
    assert any("not a probability" in c for c in served["caveats"]) and any("No model uses this regime" in c for c in served["caveats"])


def test_overview_and_unknown_year(client):
    body = client.get(f"{BASE}/overview").json()
    assert body["decision"]["discriminates"] is True and [a["year"] for a in body["available"]] == [2018, 2019, 2024, 2025]
    assert body["protocol_sha256"] == sha(PHASE12 / "coastal_regime_protocol_v1.json") and "not a learned or validated regime" in body["purpose"]
    for path in ("result", "cases"):
        response = client.get(f"{BASE}/{path}?year=2023")
        assert response.status_code == 404 and response.json()["code"] == "SCIENCE_PRODUCT_UNAVAILABLE"


@pytest.mark.parametrize("victim", ["coastal_regime_B_2025.json", "coastal_regime_protocol_v1.json", "coastal_regime_manifest.json", "coastal_regime_cases_v1.json"])
def test_tampered_evidence_is_refused(client, monkeypatch, victim):
    real = api.sha256_file
    monkeypatch.setattr(api, "sha256_file", lambda path: "0" * 64 if path.name == victim else real(path))
    response = client.get(f"{BASE}/overview")
    assert response.status_code == 503 and response.json()["code"] == "SCIENCE_INTEGRITY_FAILURE"


def test_a_cut_point_edit_in_the_case_file_is_caught(client, monkeypatch):
    real = json.loads

    def tampered(text, *args, **kwargs):
        value = real(text, *args, **kwargs)
        if isinstance(value, dict) and value.get("schema") == "coastal-regime-cases-v1":
            value["cut_points"]["A"]["q33"] += 1.0
        return value
    monkeypatch.setattr(api.json, "loads", tampered)
    response = client.get(f"{BASE}/overview")
    assert response.status_code == 503 and response.json()["code"] == "SCIENCE_INTEGRITY_FAILURE"
