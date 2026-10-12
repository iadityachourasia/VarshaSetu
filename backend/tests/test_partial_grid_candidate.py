"""Missing cells never enter the model or a supported district value."""

import numpy as np
import pytest

from backend.app.live import partial_candidate as candidate
from scripts import run_partial_cell_development as prior


class StubModels:
    def __init__(self):
        self.seen = None

    def apply(self, X, regime):
        self.seen = X.copy()
        raw = X[:, 0].astype(np.float32)
        return {"M0": raw, "M2": raw + 1, "M4": raw + 2,
                "heavy_probability": np.full(len(X), .2), "very_heavy_probability": np.full(len(X), .1),
                "regime_probability": np.array([.2, .3, .5])}


def fake_features(rainfall, _atmosphere):
    product, grid = next(iter(rainfall.items()))
    X = np.zeros((2401, 22), dtype=np.float32)
    X[:, 0] = grid.ravel()
    return {product: {"X": X, "regime": np.zeros(9)}}


def test_protocol_is_sealed_and_keeps_live_worker_out_of_scope():
    path = prior.ROOT / "data/manifests/research_pilot/partial_grid_inference_protocol_v1.json"
    protocol, _ = prior.checked(path)
    assert protocol["excluded_years"] == [2025, 2026]
    assert protocol["model_ids"] == ["M0", "M2", "M4"]
    assert protocol["regional_minimum_valid_fraction"] == .99
    assert "No live worker" in protocol["no_promotion"]


def test_inference_slices_invalid_rows_before_model_call(monkeypatch):
    monkeypatch.setattr(candidate.pipeline, "build_features", fake_features)
    rain = np.ones((49, 49), dtype=float)
    mask = np.ones((49, 49), dtype=bool)
    mask[0, 0] = False
    rain[0, 0] = np.nan
    model = StubModels()
    result = candidate.infer_field(rain, mask, {}, "day1_24h", model)
    assert model.seen.shape == (2400, 22)
    assert np.isfinite(model.seen).all() and np.all(model.seen[:, 0] == 1)
    assert np.isnan(result["fields"]["M2"][0, 0])
    assert result["fields"]["M2"][0, 1] == 2
    assert result["invalid_cells"] == 1


def test_low_coverage_refused_and_district_suppressed(monkeypatch):
    monkeypatch.setattr(candidate.pipeline, "build_features", fake_features)
    rain = np.ones((49, 49), dtype=float)
    mask = np.ones((49, 49), dtype=bool)
    mask[0, 0] = False
    rain[0, 0] = np.nan
    with pytest.raises(ValueError, match="coverage"):
        candidate.infer_field(rain, mask, {}, "day1_24h", StubModels(), minimum_fraction=1)
    result = candidate.infer_field(rain, mask, {}, "day1_24h", StubModels())
    weights = np.zeros((2, 2401), dtype=float)
    weights[0, :2] = 1
    weights[1, 1:3] = 1
    districts = [{"district_id": "a", "district_name": "A"}, {"district_id": "b", "district_name": "B"}]
    rows = candidate.district_rows(districts, weights, result)
    assert rows[0]["coverage_fraction"] == .5 and rows[0]["supported"] is False
    assert rows[0]["M2_mean"] is None
    assert rows[1]["coverage_fraction"] == 1 and rows[1]["M2_mean"] == 2
