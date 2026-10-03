"""Reforecast study (protocol v1, docs/142): hash chain, sealing discipline, verdicts re-derived from the stored intervals, API, tamper refusal and (locally) an independent recomputation."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import pytest
from fastapi.testclient import TestClient

from backend.app.api import reforecast as api
from backend.app.ml import reforecast_study as rs
from backend.app.ml import regime_tasks as rt

ROOT = Path(__file__).resolve().parents[2]
PHASE15 = ROOT / "backend/app/evidence_data/phase15"
BASE = "/api/science/evidence/reforecast"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(name: str) -> dict:
    return json.loads((PHASE15 / name).read_text(encoding="utf-8"))


PROTOCOL, SELECTION, TASKS, UNSEAL, MANIFEST = (load(n) for n in ("reforecast_study_protocol_v1.json", "reforecast_selection_freeze.json", "regime_tasks_selection_freeze.json", "reforecast_unseal_record.json", "reforecast_manifest.json"))
R05, R03 = load("reforecast_r05_test.json"), load("reforecast_r03_test.json")


@pytest.fixture(scope="module")
def client() -> TestClient:
    from backend.main import app
    return TestClient(app)


@pytest.fixture(autouse=True)
def _fresh():
    api._chain.cache_clear()
    api._confirmation.cache_clear()
    yield
    api._chain.cache_clear()
    api._confirmation.cache_clear()


def test_hash_chain_and_sealing_discipline():
    for name in ("reforecast_study_protocol_v1", "reforecast_selection_freeze", "regime_tasks_selection_freeze", "reforecast_unseal_record", "reforecast_manifest", "reforecast_protocol_v1_amendment_1"):
        assert (PHASE15 / f"{name}.sha256").read_text(encoding="ascii").split()[0] == sha(PHASE15 / f"{name}.json"), name
    p = sha(PHASE15 / "reforecast_study_protocol_v1.json")
    assert MANIFEST["protocol_sha256"] == UNSEAL["protocol_sha256"] == SELECTION["protocol_sha256"] == TASKS["protocol_sha256"] == p and load("reforecast_protocol_v1_amendment_1.json")["amends_protocol_sha256"] == p
    assert MANIFEST["unseal_record_sha256"] == sha(PHASE15 / "reforecast_unseal_record.json") and MANIFEST["selection_freeze_sha256"] == UNSEAL["selection_freeze_sha256"] == sha(PHASE15 / "reforecast_selection_freeze.json")
    assert SELECTION["sealed_test"]["opened"] is False and TASKS["sealed_test"]["opened"] is False and UNSEAL["written_before_any_sealed_observation_was_read"] is True and PROTOCOL["no_observation_read"] is True
    assert UNSEAL["years"] == list(rs.SEALED_YEARS) and UNSEAL["owner_message"]["verbatim"].strip()
    assert "retraining, re-selecting or changing any threshold, configuration or rule" in UNSEAL["what_is_not_authorised"]
    for name, entry in MANIFEST["files"].items():
        assert sha(PHASE15 / name) == entry["sha256"] and load(name)["protocol_sha256"] == p and load(name)["unseal_record_sha256"] == MANIFEST["unseal_record_sha256"]
    assert R05["label"] == R03["label"] == "POST-UNSEAL SEALED TEST 2014-2016: first use of these years"


def test_the_protocol_pins_disjoint_years_the_grid_and_the_rules_the_code_implements():
    pop = PROTOCOL["populations"]
    assert pop["train_years"] == list(rs.TRAIN_YEARS) and pop["validation_years"] == list(rs.VALIDATION_YEARS) and pop["sealed_test_years"] == list(rs.SEALED_YEARS)
    assert PROTOCOL["r05"]["grid"]["configurations"] == rs.configurations() and PROTOCOL["r05"]["grid"]["size"] == 24
    assert PROTOCOL["r03"]["classifier"]["C_grid"] == list(rt.C_GRID) and PROTOCOL["r03"]["sealed_test"]["tiers"]["USEFUL"].endswith("AUC at least 0.70")
    assert any("sealed-year observation" in f for f in PROTOCOL["forbidden"]) and "using ERA5 or any observation as a model input" in PROTOCOL["forbidden"]
    assert set(PROTOCOL["data"]["forecast_side_files"]) == {str(y) for y in range(2000, 2017)}
    assert "reanalysis" in PROTOCOL["data"] and "never a forecast input" in PROTOCOL["data"]["reanalysis"]


def test_selection_is_reproduced_from_the_stored_validation_metrics():
    raw = SELECTION["development"]["raw_validation"]
    for arm in rs.ARMS:
        results = [{"grid_index": c["grid_index"], "validation": c["validation"]} for c in SELECTION["all_configurations"] if c["arm"] == arm]
        assert len(results) == 24
        chosen = rs.select_configuration(results, raw)
        stored = SELECTION["selection"][arm]
        if chosen is None:
            assert stored is None
        else:
            assert stored["grid_index"] == chosen["grid_index"] and stored["config"] == rs.configurations()[chosen["grid_index"]]
        for c in SELECTION["all_configurations"]:
            if c["arm"] == arm:
                assert c["eligible"] == rs.eligible(c["validation"], raw)


def test_r05_decisions_are_rederived_from_the_stored_intervals_and_metrics():
    for arm, block in R05["decisions"].items():
        assert block["decision"] == rs.decide_candidate(block["vs_raw"], R05["pooled"][arm]), arm
    for arm, block in R05["regime_decisions"].items():
        assert block["adds_value"] == rs.regime_adds_value(block["vs_b0"]) and block["decision_vs_raw"] == rs.decide_candidate(block["vs_raw"], R05["pooled"][arm])
    for key, levels in R05["paired_intervals"].items():
        for level, e in levels.items():
            if e and e["status"] == "ok":
                low, high = e["interval95"]
                assert low <= e["point"] <= high and e["excludes_zero"] == (low > 0 or high < 0), (key, level)
    for model, m in R05["pooled"].items():
        assert m["heavy"]["observed_events"] == m["heavy"]["hits"] + m["heavy"]["misses"] and m["rmse_mm"] >= 0
    assert R05["pooled"]["M0"]["heavy"]["observed_events"] == R05["support"]["observed_event_pairs"]["heavy"] and R05["reproduction"]["status"] == "REPRODUCED"
    assert {"M0", "B0"} <= set(R05["pooled"]) and R05["years"] == list(rs.SEALED_YEARS)


def test_r03_verdicts_are_rederived_from_the_stored_statistics_and_the_gate():
    assert set(R03["tasks"]) == set(rt.TASKS)
    for task, t in R03["tasks"].items():
        gate = t["positives"] >= rt.MIN_CLASS_CASES and t["negatives"] >= rt.MIN_CLASS_CASES
        if "auc" not in t:
            assert t["tier"] == "INSUFFICIENT_SUPPORT" and not t["validated"] and not t["useful"], task
            continue
        assert gate and {k: t[k] for k in ("tier", "validated", "useful")} == rt.verdict({"auc": t["auc"], "auc_over_baseline": t["auc_over_baseline"]}, True), task
        low, high = t["auc"]["interval95"]
        assert low <= t["auc"]["point"] <= high and t["confusion"]["tp"] + t["confusion"]["fn"] == t["positives"] and t["confusion"]["tn"] + t["confusion"]["fp"] == t["negatives"]
    assert "not expert analyses" in R03["label_nature"]


@pytest.mark.parametrize("path,name", [("r05", "reforecast_r05_test.json"), ("r03", "reforecast_r03_test.json")])
def test_the_api_serves_the_frozen_files(client, path, name):
    body = client.get(f"{BASE}/{path}").json()
    assert body["payload"] == load(name) and body["evidence_label"] == "POST-UNSEAL SEALED TEST 2014-2016: first use of these years"
    assert any("Sealed years 2014-2016" in c for c in body["caveats"]) and any("reanalysis" in c for c in body["caveats"])


def test_overview_states_the_sealing_and_hides_model_coefficients(client):
    body = client.get(f"{BASE}/overview").json()
    assert body["protocol_sha256"] == sha(PHASE15 / "reforecast_study_protocol_v1.json") and body["unseal_record"]["years"] == [2014, 2015, 2016]
    assert all("model" not in t and "baseline_model" not in t for t in body["regime_tasks_selection"]["tasks"].values())
    assert body["populations"]["sealed_test_years"] == [2014, 2015, 2016] and "forecast_side_files" not in body["data"]


@pytest.mark.parametrize("victim", ["reforecast_r05_test.json", "reforecast_study_protocol_v1.json", "reforecast_manifest.json", "reforecast_selection_freeze.json", "reforecast_unseal_record.json", "regime_tasks_selection_freeze.json"])
def test_tampered_evidence_is_refused(client, monkeypatch, victim):
    real = api.sha256_file
    monkeypatch.setattr(api, "sha256_file", lambda path: "0" * 64 if path.name == victim else real(path))
    response = client.get(f"{BASE}/overview")
    assert response.status_code == 503 and response.json()["code"] == "SCIENCE_INTEGRITY_FAILURE"


def test_a_recorded_claim_that_the_sealed_years_were_already_open_is_refused(client, monkeypatch):
    real = json.loads

    def tampered(text, *args, **kwargs):
        value = real(text, *args, **kwargs)
        if isinstance(value, dict) and value.get("schema") == "reforecast-selection-freeze-v1":
            value["sealed_test"]["opened"] = True
        return value
    monkeypatch.setattr(api.json, "loads", tampered)
    assert client.get(f"{BASE}/overview").status_code == 503


LOCAL = pytest.mark.skipif(not (ROOT / "data/processed/reforecast_control_v1/2014/y_mm.npy").exists(), reason="the local sealed-year paired files are not present")


@LOCAL
def test_raw_metrics_equal_an_independent_loop_over_the_stored_paired_cells():
    y_all, x_all = [], []
    for year in rs.SEALED_YEARS:
        folder = ROOT / "data/processed/reforecast_control_v1" / str(year)
        y_all.append(np.load(folder / "y_mm.npy"))
        x_all.append(np.load(folder / "X.npy")[:, 0].astype(np.float64))
    y, f = np.concatenate(y_all), np.concatenate(x_all)
    m = R05["pooled"]["M0"]
    assert m["cells"] == len(y) and m["rmse_mm"] == pytest.approx(float(np.sqrt(np.mean((f - y) ** 2))), rel=1e-9) and m["bias_mm"] == pytest.approx(float(np.mean(f - y)), rel=1e-9)
    hits = int(np.count_nonzero((y.astype(np.float32) >= np.float32(64.5)) & (f.astype(np.float32) >= np.float32(64.5))))
    assert m["heavy"]["hits"] == hits


def test_exceedance_freeze_amendments_and_bundle_decisions_are_consistent():
    EXC = load("reforecast_exceedance_freeze.json")
    assert (PHASE15 / "reforecast_exceedance_freeze.sha256").read_text(encoding="ascii").split()[0] == sha(PHASE15 / "reforecast_exceedance_freeze.json")
    assert MANIFEST["exceedance_freeze_sha256"] == UNSEAL["exceedance_freeze_sha256"] == sha(PHASE15 / "reforecast_exceedance_freeze.json") and EXC["sealed_test"]["opened"] is False
    assert set(UNSEAL["amendments_sha256"]) == {"reforecast_protocol_v1_amendment_1.json", "reforecast_protocol_v1_amendment_2.json"}
    for name, digest in UNSEAL["amendments_sha256"].items():
        assert sha(PHASE15 / name) == digest
    for key, block in EXC["selection"].items():
        assert block is not None and block["tau"] == block["validation"]["tau"] and block["validation"]["csi"] >= EXC["raw_validation"][key.split(":")[1]]
    for arm, block in R05["bundle_decisions"].items():
        like = {"bias_mm": R05["pooled"][arm]["bias_mm"], "heavy": {"frequency_bias": R05["exceedance"][f"{arm}:heavy"]["test"]["frequency_bias"]}, "very_heavy": {"frequency_bias": R05["exceedance"][f"{arm}:very_heavy"]["test"]["frequency_bias"]}}
        assert block["decision"] == rs.decide_candidate(block["vs_raw"], like), arm
        assert R05["exceedance"][f"{arm}:heavy"]["tau"] == EXC["selection"][f"{arm}:heavy"]["tau"]


def test_recorded_findings_are_stated_as_they_came_out_not_as_hoped():
    for arm, block in R05["bundle_decisions"].items():
        d = block["decision"]
        # the three improvements are each shown with an interval excluding zero, but the frozen mean-bias guardrail (1.5 mm) fails on the sealed years, so the frozen tier is NONE and the row stays partial
        assert d["improvements"] == ["IMPROVES_RMSE", "IMPROVES_HEAVY", "IMPROVES_VERY_HEAVY"] and d["BIAS_OK"] is False and d["tier"] == "NONE"
        assert abs(R05["pooled"][arm]["bias_mm"]) > 1.5 and R05["exceedance"][f"{arm}:very_heavy"]["test"]["csi"] > R05["raw_categorical"]["very_heavy"]["csi"]
    for arm, block in R05["regime_decisions"].items():
        assert block["adds_value"]["adds_value"] is False                       # regime-awareness does not beat the non-regime model: stated, not hidden
    assert all(t["tier"] == "USEFUL" for t in R03["tasks"].values()) and R03["tasks"]["WESTERN_DISTURBANCE"]["auc"]["interval95"][0] > 0.5


CONF = load("reforecast_r05_confirmation.json")
CONF_RECORD, CONF_MANIFEST, AMEND3 = load("reforecast_confirmation_unseal_record.json"), load("reforecast_confirmation_manifest.json"), load("reforecast_protocol_v1_amendment_3.json")


def test_confirmation_chain_and_pre_registration():
    for name in ("reforecast_confirmation_unseal_record", "reforecast_confirmation_manifest", "reforecast_protocol_v1_amendment_3"):
        assert (PHASE15 / f"{name}.sha256").read_text(encoding="ascii").split()[0] == sha(PHASE15 / f"{name}.json"), name
    p = sha(PHASE15 / "reforecast_study_protocol_v1.json")
    assert CONF_MANIFEST["protocol_sha256"] == p and AMEND3["amends_protocol_sha256"] == p and CONF_MANIFEST["confirmation_record_sha256"] == sha(PHASE15 / "reforecast_confirmation_unseal_record.json")
    assert CONF_RECORD["written_before_any_2017_2019_observation_was_read_for_this_study"] is True and CONF_RECORD["years"] == [2017, 2018, 2019]
    assert CONF_RECORD["hashes"]["reforecast_protocol_v1_amendment_3.json"] == sha(PHASE15 / "reforecast_protocol_v1_amendment_3.json")
    assert CONF_RECORD["hashes"]["reforecast_r05_test.json"] == MANIFEST["files"]["reforecast_r05_test.json"]["sha256"]
    assert CONF_MANIFEST["files"]["reforecast_r05_confirmation.json"]["sha256"] == sha(PHASE15 / "reforecast_r05_confirmation.json")
    assert CONF["label"].startswith("CONFIRMATORY TEST 2017-2019") and "not an untouched" not in CONF["label"]
    assert "never described as an untouched holdout" in AMEND3["years_status"] and "No model is refit" in AMEND3["change"]


def test_delta_is_the_round_1_pooled_bias_and_the_decision_is_rederived():
    assert CONF["delta_mm"] == R05["pooled"]["B1"]["bias_mm"]
    like = {"bias_mm": CONF["pooled"]["B1_shifted"]["bias_mm"], "heavy": {"frequency_bias": CONF["exceedance"]["B1:heavy"]["test"]["frequency_bias"]}, "very_heavy": {"frequency_bias": CONF["exceedance"]["B1:very_heavy"]["test"]["frequency_bias"]}}
    assert CONF["bundle_decision"]["decision"] == rs.decide_candidate(CONF["bundle_decision"]["vs_raw"], like)
    d = CONF["bundle_decision"]["decision"]
    assert d["tier"] == "FULL" and d["BIAS_OK"] and d["improvements"] == ["IMPROVES_RMSE", "IMPROVES_HEAVY", "IMPROVES_VERY_HEAVY"]
    assert CONF["pooled"]["B1_uncorrected"]["bias_mm"] > 1.5 > abs(CONF["pooled"]["B1_shifted"]["bias_mm"]) and CONF["support"]["supported"] == {"heavy": True, "very_heavy": True}
    for key in ("rmse", "heavy_csi", "very_heavy_csi"):
        e = CONF["bundle_decision"]["vs_raw"][key]
        assert e["interval95"][0] <= e["point"] <= e["interval95"][1] and e["excludes_zero"]
    assert CONF["exceedance"]["B1:heavy"]["tau"] == load("reforecast_exceedance_freeze.json")["selection"]["B1:heavy"]["tau"]


def test_the_api_serves_the_confirmation_and_refuses_tampering(client, monkeypatch):
    body = client.get(f"{BASE}/r05-confirmation").json()
    assert body["payload"] == CONF and body["evidence_label"].startswith("CONFIRMATORY TEST 2017-2019") and any("not tuned on 2017-2019" in c for c in body["caveats"])
    api._confirmation.cache_clear()
    real = api.sha256_file
    monkeypatch.setattr(api, "sha256_file", lambda path: "0" * 64 if path.name == "reforecast_r05_confirmation.json" else real(path))
    response = client.get(f"{BASE}/r05-confirmation")
    assert response.status_code == 503 and response.json()["code"] == "SCIENCE_INTEGRITY_FAILURE"
    api._confirmation.cache_clear()
