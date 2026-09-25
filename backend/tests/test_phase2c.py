import json
from pathlib import Path

import numpy as np
import pytest
from fastapi.testclient import TestClient

from backend.app.ml.phase2b import sha256_file
from backend.app.ml.phase2c import (aggregate_districts, apply_calibration, district_weights,
    event_target, fit_calibration, fss, probability_metrics, reliability_bins,
    safe_logistic_fit, safe_logistic_predict)
from backend.main import app


def test_event_thresholds_are_24h_inclusive():
    y = np.array([64.49, 64.5, 115.59, 115.6])
    assert event_target(y, 64.5).tolist() == [0, 1, 1, 1]
    assert event_target(y, 115.6).tolist() == [0, 0, 0, 1]
    with pytest.raises(ValueError):
        event_target(np.array([np.nan]), 64.5)


def test_calibration_serialization_and_bounds():
    p = np.array([.01, .1, .4, .8, .9, .99])
    y = np.array([0, 0, 0, 1, 1, 1])
    for method in ("identity", "sigmoid", "isotonic"):
        artifact = json.loads(json.dumps(fit_calibration(p, y, method)))
        assert artifact["fit_year"] == 2018
        predicted = apply_calibration(artifact, p)
        assert np.isfinite(predicted).all()
        assert ((0 <= predicted) & (predicted <= 1)).all()
    with pytest.raises(ValueError):
        apply_calibration({"format": "phase2c-calibration-v1", "fit_year": 2019, "method": "identity"}, p)


def test_safe_logistic_no_pickle():
    x = np.array([[0.], [1.], [2.], [3.]])
    artifact = json.loads(json.dumps(safe_logistic_fit(x, np.array([0, 0, 1, 1]))))
    probability = safe_logistic_predict(artifact, x)
    assert probability.shape == (4,)
    assert ((probability >= 0) & (probability <= 1)).all()


def test_brier_rare_event_metrics_and_reliability():
    result = probability_metrics(np.array([0, 1]), np.array([.2, .8]), .5, .25)
    assert result["brier"] == pytest.approx(.04)
    assert result["pr_auc"] == 1
    assert result["categorical"]["decision_threshold_probability"] == .5
    assert "threshold_mm_24h" not in result["categorical"]
    assert sum(x["sample_count"] for x in result["reliability"]) == 2
    no_events = probability_metrics(np.array([0, 0]), np.array([.1, .2]), .5, .2)
    assert no_events["roc_auc"] is None and no_events["pr_auc"] is None
    assert no_events["undefined_reasons"]["pr_auc"] == "no observed events"
    assert len(reliability_bins(np.array([1]), np.array([1.]))) == 10


def test_fss_perfect_mismatch_bounds_and_no_events():
    event = np.zeros((5, 5)); event[2, 2] = 100
    empty = np.zeros((5, 5))
    mask = np.ones((5, 5), dtype=bool)
    assert fss(event, event, mask, 64.5, 1)["fss"] == 1
    assert fss(event, empty, mask, 64.5, 1)["fss"] == 0
    assert fss(empty, empty, mask, 64.5, 3)["fss"] is None
    for size in (1, 3, 5):
        score = fss(event, empty, mask, 64.5, size)["fss"]
        assert 0 <= score <= 1


def test_fss_mask_edge_policy():
    event = np.zeros((3, 3)); event[0, 0] = 100
    mask = np.ones((3, 3), bool)
    assert fss(event, event, mask, 64.5, 3)["fss"] == 1
    mask[0, 0] = False
    assert fss(event, event, mask, 64.5, 3)["fss"] is None
    assert fss(event, event, np.zeros((3, 3), bool), 64.5, 3)["reason"] == "no valid neighborhoods"


def test_district_overlap_and_mask(tmp_path: Path):
    source = {"type": "FeatureCollection", "features": [{"type": "Feature", "properties": {"shapeID": "D1", "shapeName": "A"},
        "geometry": {"type": "Polygon", "coordinates": [[[-.125, -.125], [.25, -.125], [.25, .125], [-.125, .125], [-.125, -.125]]]}}]}
    path = tmp_path / "districts.geojson"
    path.write_text(json.dumps(source), encoding="utf-8")
    districts, weights = district_weights(path, np.array([0.]), np.array([0., .25]))
    assert len(districts) == 1 and weights.shape == (1, 2)
    assert weights[0, 0] > weights[0, 1] > 0
    result = aggregate_districts(districts, weights, np.array([10., 20.]), np.array([70., 0.]),
                                  np.array([.7, .2]), np.array([.1, .01]), np.array([True, False]))
    assert result[0]["raw_mean_mm"] == 10
    assert result[0]["heavy_area_fraction"] == 1
    assert aggregate_districts(districts, weights, np.array([10., 20.]), np.array([70., 0.]),
                               np.array([.7, .2]), np.array([.1, .01]), np.array([False, False])) == []


def test_source_provenance_hash():
    root = Path(__file__).resolve().parents[2]
    source = json.loads((root / "data/static/phase2c/SOURCE.json").read_text(encoding="utf-8"))
    assert sha256_file(root / "data/static/phase2c/geoBoundaries-IND-ADM2_simplified.geojson") == source["source_sha256"]


def test_api_readonly_provenance_and_legacy_lock():
    client = TestClient(app)
    model_path = Path(__file__).resolve().parents[2] / "data/manifests/phase2b/models/global_xgboost.json"
    model_hash_before = sha256_file(model_path)
    status = client.get("/api/science/status")
    assert status.status_code == 200
    assert status.json()["readiness_state"] == "prototype_scientific_ready"
    assert status.json()["operational_ready"] is False
    cases = client.get("/api/science/cases").json()["cases"]
    assert len(cases) == 255 and "array_file" not in cases[0]
    identifier = cases[0]["case_id"]
    for suffix in ("", "/rainfall", "/regime", "/probabilities", "/fss", "/districts"):
        response = client.get(f"/api/science/cases/{identifier}{suffix}")
        assert response.status_code == 200
        assert response.json()["provenance"]["probability_freeze_sha256"]
    rainfall = client.get(f"/api/science/cases/{identifier}/rainfall").json()["data"]
    probability = client.get(f"/api/science/cases/{identifier}/probabilities").json()["data"]
    for payload in (rainfall, probability):
        grid = payload["grid"]
        assert grid["crs"] == "EPSG:4326"
        assert grid["shape"] == [49, 49]
        assert grid["latitude_centers"][0] == 10.0
        assert grid["longitude_centers"][-1] == 80.0
    assert len(rainfall["raw"]) == len(rainfall["valid_mask"]) == 49
    geometry = client.get("/api/science/geometry/districts")
    assert geometry.status_code == 200
    assert len(geometry.json()["geometry"]["features"]) == 188
    assert geometry.json()["license"] == "ODbL 1.0"
    demo = client.get("/api/science/demo-cases")
    assert demo.status_code == 200
    assert len(demo.json()["cases"]) == 6
    assert "array_file" not in demo.json()["cases"][0]
    comparison = client.get("/api/science/model-comparison")
    assert comparison.status_code == 200
    assert len(comparison.json()["results"]) == 5
    assert comparison.json()["results_sha256"] == sha256_file(
        Path(__file__).resolve().parents[2] / "data/manifests/phase2b/2019_final_results.json")
    assert client.get("/api/science/cases/not-a-case").status_code == 404
    assert client.get("/api/science/cases/..%2F..%2Ffoo").status_code in (404, 422)
    assert client.post("/api/science/cases").status_code == 405
    assert client.get("/api/forecast", params={"station_id": 1, "date": "2025-01-01"}).status_code == 409
    assert sha256_file(model_path) == model_hash_before
