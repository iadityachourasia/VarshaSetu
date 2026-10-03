"""Independent regime validation (protocol v1, docs/136): hash chain, counts, honest gating, re-derived metrics, API with tamper refusal."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import pytest
from fastapi.testclient import TestClient

from backend.app.api import regime_validation as api
from backend.app.ml import regime_validation as rv

PHASE6 = Path(__file__).resolve().parents[1] / "app/evidence_data/phase6"
BASE = "/api/science/evidence/regime-validation"
POST_HOC = {2019: "POST-HOC EXPLORATORY ANALYSIS OF THE COMPLETED 2019 FINAL TEST", 2025: "POST-HOC EXPLORATORY ANALYSIS OF THE COMPLETED 2025 FINAL TEST"}
POPULATIONS = {"A2018": ("A", 2018), "A2019": ("A", 2019), "B2024": ("B", 2024), "B2025": ("B", 2025)}


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(name: str) -> dict:
    return json.loads((PHASE6 / name).read_text(encoding="utf-8"))


PROTOCOL, MANIFEST = load("regime_validation_protocol_v1.json"), load("regime_validation_manifest.json")
RESULTS = {pop: load(f"regime_validation_{t}_{y}.json") for pop, (t, y) in POPULATIONS.items()}


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


def test_hash_chain_protocol_manifest_and_every_result():
    assert (PHASE6 / "regime_validation_protocol_v1.sha256").read_text(encoding="ascii").split()[0] == sha(PHASE6 / "regime_validation_protocol_v1.json")
    assert (PHASE6 / "regime_validation_manifest.sha256").read_text(encoding="ascii").strip() == sha(PHASE6 / "regime_validation_manifest.json")
    assert MANIFEST["protocol_sha256"] == sha(PHASE6 / "regime_validation_protocol_v1.json")
    assert set(MANIFEST["files"]) == {f"regime_validation_{t}_{y}.json" for t, y in POPULATIONS.values()}
    for name, entry in MANIFEST["files"].items():
        assert sha(PHASE6 / name) == entry["sha256"] and load(name)["protocol_sha256"] == MANIFEST["protocol_sha256"] and entry["reproduction"] == "REPRODUCED"
    assert b"\r\n" not in (PHASE6 / "regime_validation_protocol_v1.json").read_bytes()


def test_the_protocol_states_its_limits_and_was_frozen_before_any_prediction_was_read():
    assert PROTOCOL["no_classifier_prediction_read"] is True and PROTOCOL["criteria"]["not_the_published_classification"] is True
    assert len(PROTOCOL["criteria"]["deviations_from_the_published_work"]) >= 4 and "NOT validated" in PROTOCOL["tasks"]["not_scored"]
    clim = PROTOCOL["criteria"]["climatology"]
    assert clim["years"] == [1981, 2016] and len(clim["file_sha256"]) == 36 and len(clim["mean_mm_per_day_by_season_day"]) == 122
    assert not set(range(1981, 2017)) & {2018, 2019, 2023, 2024, 2025}                                    # the climatology shares no year with any evaluated population
    assert "may withdraw" in PROTOCOL["approval"]["note"] and "merging this result with the pseudo-label agreement figures" in PROTOCOL["forbidden"]
    assert PROTOCOL["labels"]["A2019"] == POST_HOC[2019] and PROTOCOL["labels"]["B2025"] == POST_HOC[2025]


def test_label_window_and_parameters_equal_the_pure_module():
    c = PROTOCOL["criteria"]
    assert c["core_zone_box"] == {"lat": list(rv.CMZ_LAT), "lon": list(rv.CMZ_LON)} and c["threshold_sd"] == rv.THRESHOLD_SD and c["min_spell_days"] == rv.MIN_SPELL_DAYS
    assert c["label_window_months"] == list(rv.WINDOW_MONTHS) and PROTOCOL["support_gate"]["min_cases_per_side"] == rv.MIN_CLASS_CASES
    assert PROTOCOL["uncertainty"]["repeats"] == rv.REPEATS and PROTOCOL["uncertainty"]["seed"] == rv.SEED


def test_the_support_gate_follows_from_the_observation_only_counts_and_gates_every_score():
    for pop, result in RESULTS.items():
        counts = PROTOCOL["observation_only_counts"][pop]
        assert result["observed_state_counts"] == counts["cases_by_observed_state"] and result["cases_labelled"] == counts["cases_with_labelled_valid_day"]
        assert counts["supported"] == rv.supported(counts["cases_by_observed_state"])
        for task, state in (("active_vs_not_active", "ACTIVE"), ("break_vs_not_break", "BREAK")):
            assert (result["tasks"][task]["status"] == "scored") == counts["supported"][state], (pop, task)
            if result["tasks"][task]["status"] != "scored":
                assert result["tasks"][task]["status"] == "insufficient_support" and "balanced_accuracy" not in result["tasks"][task]       # no number without support
    assert {pop for pop, r in RESULTS.items() if r["tasks"]["active_vs_not_active"]["status"] == "scored"} == {"A2019", "B2024"}
    assert all(r["tasks"]["break_vs_not_break"]["status"] == "insufficient_support" for r in RESULTS.values())      # break cannot be validated in any population


def test_scores_are_rederived_from_the_stored_confusion_tables():
    for pop, result in RESULTS.items():
        table = result["confusion_predicted_class_by_observed_state"]
        assert sum(sum(v.values()) for v in table.values()) == result["cases_labelled"]
        task = result["tasks"]["active_vs_not_active"]
        if task["status"] != "scored":
            continue
        hits = table["ACTIVE_MONSOON"]["ACTIVE"]
        predicted = sum(table["ACTIVE_MONSOON"].values())
        observed = sum(row["ACTIVE"] for row in table.values())
        derived = rv.binary_metrics(np.array([True] * hits + [True] * (predicted - hits) + [False] * (observed - hits) + [False] * (result["cases_labelled"] - predicted - observed + hits)),
                                    np.array([True] * hits + [False] * (predicted - hits) + [True] * (observed - hits) + [False] * (result["cases_labelled"] - predicted - observed + hits)))
        for key in ("hits", "misses", "false_alarms", "correct_negatives", "recall", "specificity", "precision", "balanced_accuracy", "f1", "base_rate"):
            assert task[key] == pytest.approx(derived[key]), (pop, key)
        low, high = task["balanced_accuracy_bootstrap"]["interval95"]
        assert low <= task["balanced_accuracy"] <= high and task["balanced_accuracy_bootstrap"]["repeats"] == 2000


def test_the_recorded_finding_active_days_are_classified_as_low_depression_not_active_and_depression_is_not_validated():
    for pop in ("A2019", "B2024"):
        result = RESULTS[pop]
        task = result["tasks"]["active_vs_not_active"]
        table = result["confusion_predicted_class_by_observed_state"]
        assert task["balanced_accuracy"] < 0.5                                                      # below the chance level of 0.5
        assert table["LOW_DEPRESSION_INFLUENCED"]["ACTIVE"] > table["ACTIVE_MONSOON"]["ACTIVE"]      # most observed active days fall in the low/depression pseudo-class
        assert "NOT VALIDATED" in result["depression"] and result["pseudo_label_agreement_is_separate"] is True
    assert RESULTS["A2019"]["label"] == POST_HOC[2019]


@pytest.mark.parametrize("year", [2018, 2019, 2024, 2025])
def test_the_api_serves_the_frozen_result_with_its_label(client, year):
    body = client.get(f"{BASE}/result?year={year}").json()
    frozen = RESULTS[{2018: "A2018", 2019: "A2019", 2024: "B2024", 2025: "B2025"}[year]]
    assert body["payload"] == frozen and body["year"] == year and len(body["evidence_sha256"]) == 64
    assert (body["evidence_label"] == POST_HOC.get(year, body["evidence_label"])) and ((year in POST_HOC) == body["evidence_label"].startswith("POST-HOC"))
    assert any("NOT validated" in c for c in body["caveats"]) and any("never merged" in c for c in body["caveats"])


def test_the_overview_and_unknown_year(client):
    body = client.get(f"{BASE}/overview").json()
    assert body["protocol_sha256"] == sha(PHASE6 / "regime_validation_protocol_v1.json") and [a["year"] for a in body["available"]] == [2018, 2019, 2024, 2025]
    assert body["criteria"]["not_the_published_classification"] is True and body["criteria"]["climatology"]["files"] == 36
    response = client.get(f"{BASE}/result?year=2023")
    assert response.status_code == 404 and response.json()["code"] == "SCIENCE_PRODUCT_UNAVAILABLE"


@pytest.mark.parametrize("victim", ["regime_validation_A_2019.json", "regime_validation_protocol_v1.json", "regime_validation_manifest.json"])
def test_tampered_evidence_is_refused(client, monkeypatch, victim):
    real = api.sha256_file
    monkeypatch.setattr(api, "sha256_file", lambda path: "0" * 64 if path.name == victim else real(path))
    response = client.get(f"{BASE}/overview")
    assert response.status_code == 503 and response.json()["code"] == "SCIENCE_INTEGRITY_FAILURE"


def test_an_unregistered_role_is_refused(client, monkeypatch):
    monkeypatch.setattr(api, "EVIDENCE_LABELS", {})
    response = client.get(f"{BASE}/result?year=2019")
    assert response.status_code == 503 and response.json()["code"] == "SCIENCE_INTEGRITY_FAILURE"
