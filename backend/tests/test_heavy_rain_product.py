"""The frozen heavy-rain bundle in the 2019 map and district products (docs/143): protocol, integrity chain, served values, and an independent recomputation of the district numbers."""

from __future__ import annotations

import json
import re
import shutil
from pathlib import Path

import numpy as np
import pytest
from fastapi.testclient import TestClient

from backend.app.api import evidence, heavy_rain
from backend.app.ml import heavy_rain_product as hp

ROOT = Path(__file__).resolve().parents[2]
PHASE15 = ROOT / "backend/app/evidence_data/phase15"
PHASE17 = ROOT / "backend/app/evidence_data/phase17"
PRODUCT = ROOT / "data/manifests/phase2c"
HAS_PRODUCT = (PRODUCT / "artifact_manifest.json").is_file()
NEEDS_PRODUCT = pytest.mark.skipif(not HAS_PRODUCT, reason="requires the serving-data bundle (the Track A product artifacts), which is not in this checkout")
LOCAL_MODELS = pytest.mark.skipif(not (ROOT / "experiments/reforecast_study_v1/models/B1.json").is_file() or not (ROOT / "data/processed/reforecast_control_v1/2019/X_full.npy").is_file(),
                                  reason="the trained models and the forecast-side cache are local (gitignored)")
PROTOCOL = json.loads((PHASE17 / "heavy_rain_integration_protocol_v1.json").read_text(encoding="utf-8"))
MANIFEST = json.loads((PHASE17 / "heavy_rain_b1_manifest.json").read_text(encoding="utf-8"))
CASE = "20190802T000000Z_day3_24h"


@pytest.fixture(scope="module")
def client() -> TestClient:
    from backend.main import app
    return TestClient(app)


@pytest.fixture(autouse=True)
def _fresh():
    heavy_rain._chain.cache_clear()
    yield
    heavy_rain._chain.cache_clear()


def _sha(path: Path) -> str:
    return heavy_rain.sha256_file(path)


# ------------------------------------------------------------------------------ protocol and chain
def test_the_protocol_was_frozen_before_the_outputs_and_the_chain_hangs_together():
    assert PROTOCOL["written_before_any_product_prediction_was_computed"] is True
    assert (PHASE17 / "heavy_rain_integration_protocol_v1.sha256").read_text(encoding="ascii").split()[0] == _sha(PHASE17 / "heavy_rain_integration_protocol_v1.json")
    assert (PHASE17 / "heavy_rain_b1_manifest.sha256").read_text(encoding="ascii").split()[0] == _sha(PHASE17 / "heavy_rain_b1_manifest.json")
    assert MANIFEST["protocol_sha256"] == _sha(PHASE17 / "heavy_rain_integration_protocol_v1.json")
    assert MANIFEST["arrays_sha256"] == _sha(PHASE17 / MANIFEST["arrays_file"])
    assert PROTOCOL["written_at_utc"] < MANIFEST["built_at_utc"]
    for key, name in (("confirmation_evidence_sha256", "reforecast_r05_confirmation.json"), ("round_one_evidence_sha256", "reforecast_r05_test.json"), ("exceedance_freeze_sha256", "reforecast_exceedance_freeze.json"),
                      ("confirmation_record_sha256", "reforecast_confirmation_unseal_record.json")):
        assert PROTOCOL["bundle"][key] == _sha(PHASE15 / name), name
    assert PROTOCOL["bundle"]["model_files_sha256"] == json.loads((PHASE15 / "reforecast_confirmation_unseal_record.json").read_text(encoding="utf-8"))["model_files_sha256"]


def test_the_protocol_text_carries_no_typed_numbers():
    texts = [PROTOCOL["authorisation"]["interpretation"], PROTOCOL["labels"]["wording"], *PROTOCOL["gates"], *PROTOCOL["must_state_wherever_shown"], *PROTOCOL["not_authorised"], *PROTOCOL["scope"]["layers"],
             *PROTOCOL["scope"]["surfaces"]]
    standalone = r"(?<![A-Za-z0-9])\d"                              # a number, not a model name such as B1
    assert all(not re.search(standalone, t) for t in texts), [t for t in texts if re.search(standalone, t)]


def test_the_thresholds_and_the_shift_are_the_frozen_ones():
    freeze = json.loads((PHASE15 / "reforecast_exceedance_freeze.json").read_text(encoding="utf-8"))
    round_one = json.loads((PHASE15 / "reforecast_r05_test.json").read_text(encoding="utf-8"))
    assert MANIFEST["thresholds"] == {"heavy": freeze["selection"]["B1:heavy"]["tau"], "very_heavy": freeze["selection"]["B1:very_heavy"]["tau"]}
    assert MANIFEST["shift_mm"] == round_one["pooled"]["B1"]["bias_mm"]
    assert all(MANIFEST["gates"][g] is True for g in ("models_match_record", "cases_and_cells_match_product", "confirmatory_pooled_results_reproduced", "product_year_slice_matches_evidence", "values_defined_and_in_range"))


# ------------------------------------------------------------------------------ served values
def test_overview_states_the_label_the_frozen_numbers_and_every_caveat(client):
    body = client.get("/api/science/heavy-rain/overview").json()
    assert body["evidence_label"] == evidence.EVIDENCE_LABELS[PROTOCOL["labels"]["track_a_2019_role"]] == "POST-HOC EXPLORATORY ANALYSIS OF THE COMPLETED 2019 FINAL TEST"
    assert body["decision_thresholds"] == MANIFEST["thresholds"] and body["shift_mm"] == MANIFEST["shift_mm"] and body["cases"] == 255
    confirmation = json.loads((PHASE15 / "reforecast_r05_confirmation.json").read_text(encoding="utf-8"))
    assert body["confirmation"]["tier"] == confirmation["bundle_decision"]["decision"]["tier"]
    assert body["confirmation"]["exceedance"]["B1:heavy"]["csi"] == confirmation["exceedance"]["B1:heavy"]["test"]["csi"]
    text = " ".join(body["caveats"])
    for phrase in ("not calibrated probabilities", "over-forecasts", "reforecast control member", "failed its mean-error guardrail", "regime-aware routing is not part"):
        assert phrase in text
    assert body["bias_guardrail_mm"] > 0 and body["slice_bias_within_limit"] == (abs(body["summary"]["rainfall"]["B1"]["bias_mm"]) <= body["bias_guardrail_mm"])
    assert body["summary"]["classifier"]["heavy"]["frequency_bias"] > 1 and body["summary"]["classifier"]["very_heavy"]["frequency_bias"] > 1


def test_a_case_serves_fields_whose_decisions_are_exactly_score_at_or_above_the_frozen_threshold(client):
    body = client.get(f"/api/science/heavy-rain/cases/{CASE}").json()
    for name in ("heavy", "very_heavy"):
        score, decision = np.array(body[f"{name}_score"], dtype=float), np.array(body[f"{name}_decision"], dtype=float)
        valid = np.isfinite(score)
        assert np.array_equal(np.isfinite(decision), valid)
        assert np.array_equal(decision[valid], (score[valid] >= body["decision_thresholds"][name]).astype(float))
        assert ((score[valid] >= 0) & (score[valid] <= 1)).all()
    rain = np.array(body["b1_rainfall_mm"], dtype=float)
    assert np.array_equal(np.isfinite(rain), np.isfinite(np.array(body["heavy_score"], dtype=float))) and (rain[np.isfinite(rain)] >= 0).all()
    assert body["evidence_label"].startswith("POST-HOC EXPLORATORY ANALYSIS")


@NEEDS_PRODUCT
def test_every_case_covers_exactly_the_products_cases_and_valid_cells(client):
    ids = sorted(p.stem for p in (PRODUCT / "cases").glob("2019*.json"))
    assert ids == sorted(str(x) for x in np.load(PHASE17 / MANIFEST["arrays_file"], allow_pickle=False)["case_ids"])
    for case_id in ids[::25] + [CASE]:
        mask = np.load(PRODUCT / "cases" / f"{case_id}.npz")["mask"]
        served = np.array(client.get(f"/api/science/heavy-rain/cases/{case_id}").json()["b1_rainfall_mm"], dtype=float)
        assert np.array_equal(np.isfinite(served), mask), case_id


def test_an_unknown_case_is_not_found(client):
    assert client.get("/api/science/heavy-rain/cases/20190101T000000Z_day1_24h").status_code == 404
    assert client.get("/api/science/heavy-rain/cases/not-a-case").status_code == 404


@NEEDS_PRODUCT
def test_district_rows_equal_an_independent_loop_over_the_cells(client):
    body = client.get(f"/api/science/heavy-rain/cases/{CASE}/districts").json()
    served = np.load(PHASE17 / MANIFEST["arrays_file"], allow_pickle=False)
    i = [str(x) for x in served["case_ids"]].index(CASE)
    b1, hs, vs = (served[k][i].ravel().astype(np.float64) for k in ("b1_rainfall", "heavy_score", "very_heavy_score"))
    app = np.load(PRODUCT / "cases" / f"{CASE}.npz")
    raw, obs = app["raw"].ravel().astype(np.float64), app["observed"].ravel().astype(np.float64)
    geometry = json.loads((PRODUCT / "districts.geojson").read_text(encoding="utf-8"))
    weights = np.load(PRODUCT / "district_weights.npy", allow_pickle=False)
    valid = np.isfinite(b1) & np.isfinite(hs) & np.isfinite(vs) & np.isfinite(raw) & np.isfinite(obs)
    by_id = {r["district_id"]: r for r in body["districts"]}
    assert len(by_id) > 150 and body["evidence_label"].startswith("POST-HOC")
    for feature, w in zip(geometry["features"], weights):
        d = feature["properties"]["district_id"]
        active = (w > 0) & valid
        if not active.any():
            assert d not in by_id
            continue
        total = sum(float(w[k]) for k in np.flatnonzero(active))
        mean = sum(float(w[k]) * b1[k] for k in np.flatnonzero(active)) / total
        score = sum(float(w[k]) * hs[k] for k in np.flatnonzero(active)) / total
        flag = sum(float(w[k]) * float(hs[k] >= MANIFEST["thresholds"]["heavy"]) for k in np.flatnonzero(active)) / total
        row = by_id[d]
        # the frozen district weights are stored in 32-bit floats, so the product's own aggregation agrees with an exact double-precision loop to about seven digits
        assert row["corrected_mean_mm"] == pytest.approx(mean, rel=1e-5)
        assert row["heavy_probability"] == pytest.approx(score, rel=1e-5)
        assert row["heavy_flag_area_fraction"] == pytest.approx(flag, abs=1e-5)
        assert 0 <= row["heavy_flag_area_fraction"] <= 1 and 0 <= row["very_heavy_flag_area_fraction"] <= 1


# ------------------------------------------------------------------------------ integrity
@pytest.mark.parametrize("victim", ["arrays", "manifest", "protocol", "sidecar"])
def test_tampering_with_any_part_of_the_chain_is_an_integrity_failure(client, monkeypatch, tmp_path, victim):
    work = tmp_path / "phase17"
    shutil.copytree(PHASE17, work)
    arrays = work / MANIFEST["arrays_file"]
    if victim == "arrays":
        arrays.write_bytes(arrays.read_bytes()[:-8] + b"tampered")
    elif victim == "manifest":
        (work / "heavy_rain_b1_manifest.json").write_text((work / "heavy_rain_b1_manifest.json").read_text(encoding="utf-8").replace('"cases": 255', '"cases": 254'), encoding="utf-8")
    elif victim == "protocol":
        (work / "heavy_rain_integration_protocol_v1.json").write_text((work / "heavy_rain_integration_protocol_v1.json").read_text(encoding="utf-8") + " ", encoding="utf-8")
    else:
        (work / "heavy_rain_b1_manifest.sha256").write_text("0" * 64 + "  heavy_rain_b1_manifest.json\n", encoding="ascii")
    monkeypatch.setattr(heavy_rain, "PHASE17", work)
    monkeypatch.setattr(heavy_rain, "PROTOCOL", work / "heavy_rain_integration_protocol_v1.json")
    monkeypatch.setattr(heavy_rain, "MANIFEST", work / "heavy_rain_b1_manifest.json")
    for path in ("overview", f"cases/{CASE}"):
        response = client.get(f"/api/science/heavy-rain/{path}")
        assert response.status_code == 503 and response.json()["code"] == "SCIENCE_INTEGRITY_FAILURE", (victim, path)


# ------------------------------------------------------------------------------ pure functions
def test_a_decision_keeps_an_undefined_score_undefined_and_is_inclusive_at_the_threshold():
    out = hp.decision(np.array([0.2, 0.5, 0.7, np.nan]), 0.5)
    assert out[0] == 0 and out[1] == 1 and out[2] == 1 and np.isnan(out[3])


def test_categorical_counts_hits_misses_false_alarms_and_the_derived_scores():
    score = np.array([0.9, 0.9, 0.1, 0.1, 0.9])
    observed = np.array([100.0, 10.0, 100.0, 10.0, 80.0])
    m = hp.categorical(score, observed, 0.5, 64.5)
    assert (m["hits"], m["misses"], m["false_alarms"]) == (2, 1, 1)
    assert m["pod"] == pytest.approx(2 / 3) and m["far"] == pytest.approx(1 / 3) and m["csi"] == pytest.approx(2 / 4) and m["frequency_bias"] == pytest.approx(3 / 3)


@LOCAL_MODELS
def test_the_stored_arrays_equal_a_fresh_prediction_of_the_frozen_models():
    from backend.app.ml import reforecast_study as rs
    freeze = json.loads((PHASE15 / "reforecast_exceedance_freeze.json").read_text(encoding="utf-8"))
    bundle = hp.load_bundle(ROOT / "experiments/reforecast_study_v1/models", freeze)
    geography = json.loads((ROOT / "backend/app/evidence_data/phase7/static_geography_v1.json").read_text(encoding="utf-8"))
    static = {n: np.array([[np.nan if v is None else v for v in row] for row in geography["fields"][n]], dtype=np.float64).ravel() for n in rs.STATIC_FEATURES}
    stored = np.load(PHASE17 / MANIFEST["arrays_file"], allow_pickle=False)
    cases = json.loads((ROOT / "data/processed/reforecast_control_v1/2019/cases.json").read_text(encoding="utf-8"))["cases"]
    x_full = np.load(ROOT / "data/processed/reforecast_control_v1/2019/X_full.npy", mmap_mode="r", allow_pickle=False)
    for c in [c for c in cases if c["status"] == "INCLUDED"][::40]:
        case_id = f"{c['initialization'].replace('-', '')}T000000Z_{c['product']}"
        i = [str(x) for x in stored["case_ids"]].index(case_id)
        cells = np.flatnonzero(np.isfinite(stored["b1_rainfall"][i].ravel()))
        out = hp.predict_bundle(bundle, hp.bundle_matrix(np.asarray(x_full[c["row"]])[cells], cells.astype(np.int64), static), MANIFEST["shift_mm"])
        assert np.array_equal(out["rainfall"], stored["b1_rainfall"][i].ravel()[cells])
        assert np.array_equal(out["heavy"].astype(np.float32), stored["heavy_score"][i].ravel()[cells])
