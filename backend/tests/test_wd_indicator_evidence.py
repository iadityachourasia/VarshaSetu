"""Forecast-time western-disturbance indicator (protocol v1, docs/138): hash chain, flags re-derived from the stored index and frozen threshold, honest decision, API, tamper refusal."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import pytest
from fastapi.testclient import TestClient

from backend.app.api import wd_indicator as api
from backend.app.ml import wd_indicator as wd

PHASE13 = Path(__file__).resolve().parents[1] / "app/evidence_data/phase13"
BASE = "/api/science/evidence/wd-indicator"
YEARS = (2021, 2022, 2024, 2025)


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(name: str) -> dict:
    return json.loads((PHASE13 / name).read_text(encoding="utf-8"))


PROTOCOL, MANIFEST, CASES = load("wd_indicator_protocol_v1.json"), load("wd_indicator_manifest.json"), load("wd_indicator_cases_v1.json")
RESULTS = {y: load(f"wd_indicator_{y}.json") for y in YEARS}


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
    assert (PHASE13 / "wd_indicator_protocol_v1.sha256").read_text(encoding="ascii").split()[0] == sha(PHASE13 / "wd_indicator_protocol_v1.json")
    assert (PHASE13 / "wd_indicator_manifest.sha256").read_text(encoding="ascii").split()[0] == sha(PHASE13 / "wd_indicator_manifest.json")
    cases_sha = sha(PHASE13 / "wd_indicator_cases_v1.json")
    assert PROTOCOL["definition"]["cases_file_sha256"] == MANIFEST["cases_file_sha256"] == cases_sha and MANIFEST["protocol_sha256"] == sha(PHASE13 / "wd_indicator_protocol_v1.json")
    assert set(MANIFEST["files"]) == {f"wd_indicator_{y}.json" for y in YEARS}
    for name, entry in MANIFEST["files"].items():
        assert sha(PHASE13 / name) == entry["sha256"] and load(name)["protocol_sha256"] == MANIFEST["protocol_sha256"]
    assert CASES["threshold"] == PROTOCOL["definition"]["threshold"]


def test_the_protocol_is_forecast_only_trained_on_2023_and_forbids_a_detection_claim():
    assert PROTOCOL["no_observation_read"] is True and "heuristic" in PROTOCOL["purpose"].lower()
    assert PROTOCOL["definition"]["training_year"] == 2023 and PROTOCOL["definition"]["boxes"] == {"indicator": list(wd.WD_BOX), "rain": list(wd.RAIN_BOX)}
    assert any("no label source exists" in item for item in PROTOCOL["not_established_whatever_the_result"])
    assert "2022 and 2025 are reported descriptively and cannot change the decision" in PROTOCOL["decision_rule"]["post_hoc_populations"]
    labels = {y: PROTOCOL["populations"][str(y)]["label"] for y in YEARS}
    assert labels[2022] == "POST-HOC EXPLORATORY ANALYSIS OF THE COMPLETED 2022 FINAL TEST" and labels[2025] == "POST-HOC EXPLORATORY ANALYSIS OF THE COMPLETED 2025 FINAL TEST"
    assert "development" in labels[2024] and "2023" not in PROTOCOL["populations"]


def test_every_stored_flag_follows_from_the_stored_index_and_the_frozen_threshold():
    cut = CASES["threshold"]
    for year in YEARS:
        rows = CASES["populations"][str(year)]
        flagged = 0
        for row in rows:
            expected = wd.flag(float("nan") if row["index"] is None else row["index"], cut)
            assert row["flag"] == expected, (year, row["case_id"])
            flagged += bool(row["flag"])
        counts = PROTOCOL["populations"][str(year)]["forecast_only_counts"]
        assert counts["cases"] == len(rows) and counts["flagged"] == flagged and counts["flagged"] + counts["not_flagged"] + counts["undefined_index"] == counts["cases"]


def test_scores_are_consistent_with_the_frozen_counts_and_the_intervals_bracket_the_points():
    for year, result in RESULTS.items():
        counts = PROTOCOL["populations"][str(year)]["forecast_only_counts"]
        groups = result["groups"]
        assert groups["flagged"]["cases"] == counts["flagged"] and groups["not_flagged"]["cases"] == counts["not_flagged"]
        assert groups["flagged"]["cases"] + groups["not_flagged"]["cases"] == result["cases_scored"] and result["reproduction"]["status"] == "REPRODUCED"
        assert result["supported"] == wd.supported(groups)
        for key in ("flagged_minus_not_flagged_mean_rain", "spearman"):
            entry = result["association"][key]
            low, high = entry["interval95"]
            assert low <= entry["point"] <= high and entry["excludes_zero"] == (low > 0 or high < 0)
        difference = groups["flagged"]["mean_rain_mm_per_day"] - groups["not_flagged"]["mean_rain_mm_per_day"]
        assert result["association"]["flagged_minus_not_flagged_mean_rain"]["point"] == pytest.approx(difference)


def test_the_decision_is_rederived_from_the_development_intervals_and_post_hoc_years_cannot_change_it():
    development = [RESULTS[2021], RESULTS[2024]]
    met = all(r["supported"] and (e := r["association"]["flagged_minus_not_flagged_mean_rain"])["point"] > 0 and e["excludes_zero"] for r in development)
    assert MANIFEST["decision"]["associated"] is met
    assert [RESULTS[y]["development"] for y in YEARS] == [True, False, True, False]
    assert met is False and "without a claim" in MANIFEST["decision"]["wording"]


def test_recorded_finding_the_sign_of_the_association_is_not_consistent_across_years():
    signs = [np.sign(RESULTS[y]["association"]["flagged_minus_not_flagged_mean_rain"]["point"]) for y in YEARS]
    assert set(signs) == {-1.0, 1.0}                       # negative in 2021 and 2022, positive in 2024 and 2025: stated, not hidden


@pytest.mark.parametrize("year", YEARS)
def test_the_api_serves_the_frozen_files(client, year):
    result = client.get(f"{BASE}/result?year={year}").json()
    assert result["payload"] == load(f"wd_indicator_{year}.json") and result["year"] == year
    assert result["evidence_label"].startswith("POST-HOC") == (year in (2022, 2025))
    served = client.get(f"{BASE}/cases?year={year}").json()
    assert served["cases"] == CASES["populations"][str(year)] and served["threshold"] == CASES["threshold"]
    assert any("NOT a validated detection" in c for c in served["caveats"]) and any("No model uses this indicator" in c for c in served["caveats"])


def test_overview_and_unknown_year(client):
    body = client.get(f"{BASE}/overview").json()
    assert body["decision"]["associated"] is False and [a["year"] for a in body["available"]] == list(YEARS)
    assert body["protocol_sha256"] == sha(PHASE13 / "wd_indicator_protocol_v1.json")
    for path in ("result", "cases"):
        for year in (2023, 2019):
            response = client.get(f"{BASE}/{path}?year={year}")
            assert response.status_code == 404 and response.json()["code"] == "SCIENCE_PRODUCT_UNAVAILABLE"


@pytest.mark.parametrize("victim", ["wd_indicator_2025.json", "wd_indicator_protocol_v1.json", "wd_indicator_manifest.json", "wd_indicator_cases_v1.json"])
def test_tampered_evidence_is_refused(client, monkeypatch, victim):
    real = api.sha256_file
    monkeypatch.setattr(api, "sha256_file", lambda path: "0" * 64 if path.name == victim else real(path))
    response = client.get(f"{BASE}/overview")
    assert response.status_code == 503 and response.json()["code"] == "SCIENCE_INTEGRITY_FAILURE"


def test_a_threshold_edit_in_the_case_file_is_caught(client, monkeypatch):
    real = json.loads

    def tampered(text, *args, **kwargs):
        value = real(text, *args, **kwargs)
        if isinstance(value, dict) and "populations" in value and "threshold" in value and value.get("schema", "").startswith("wd-indicator-cases"):
            value["threshold"]["threshold"] += 1.0
        return value
    monkeypatch.setattr(api.json, "loads", tampered)
    response = client.get(f"{BASE}/overview")
    assert response.status_code == 503 and response.json()["code"] == "SCIENCE_INTEGRITY_FAILURE"
