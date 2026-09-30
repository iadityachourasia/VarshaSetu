"""Track B district product: pure aggregation, cross-path consistency with the frozen grids, and contract."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest
from fastapi.testclient import TestClient

from backend.app.ml.district_product import (GRID_CELLS, HEAVY_MM, VERY_HEAVY_MM, aggregate_operational_districts,
                                             flat_field)
from backend.app.ml.phase2c import aggregate_districts, district_weights

ROOT = Path(__file__).resolve().parents[2]
PHASE2C = ROOT / "data/manifests/phase2c"
SOURCE = ROOT / "data/static/phase2c/geoBoundaries-IND-ADM2_simplified.geojson"
needs_data = pytest.mark.skipif(not (PHASE2C / "district_weights.npy").exists(), reason="frozen Phase 2C artifacts absent")


def _districts(n):
    return [{"district_id": f"D{i}", "district_name": f"District {i}"} for i in range(n)]


def _random_inputs(seed=0, n=5):
    rng = np.random.default_rng(seed)
    weights = np.where(rng.random((n, GRID_CELLS)) > 0.97, rng.random((n, GRID_CELLS)), 0).astype(np.float32)
    mask = rng.random(GRID_CELLS) > 0.4
    fields = {k: rng.uniform(0, 140, GRID_CELLS) for k in ("raw", "corrected", "observed")}
    fields["heavy"], fields["very_heavy"] = rng.random(GRID_CELLS), rng.random(GRID_CELLS) * .3
    return weights, mask, fields


def _masked(fields, mask):
    return {k: np.where(mask, v, np.nan) for k, v in fields.items()}


def test_reproduces_track_a_aggregation_on_shared_statistics():
    weights, mask, f = _random_inputs()
    districts = _districts(len(weights))
    mine = aggregate_operational_districts(districts, weights, raw=_masked(f, mask)["raw"],
                                           corrected=_masked(f, mask)["corrected"], observed=_masked(f, mask)["observed"],
                                           heavy_p=_masked(f, mask)["heavy"], very_heavy_p=_masked(f, mask)["very_heavy"])
    frozen = aggregate_districts(districts, weights, f["raw"], f["corrected"], f["heavy"], f["very_heavy"], mask)
    assert [r["district_id"] for r in mine] == [r["district_id"] for r in frozen] and mine
    for a, b in zip(mine, frozen):
        for key in ("valid_grid_cells", "raw_mean_mm", "corrected_mean_mm", "corrected_max_mm", "heavy_probability",
                    "very_heavy_probability", "heavy_area_fraction", "very_heavy_area_fraction"):
            assert a[key] == pytest.approx(b[key], abs=1e-9), key


def test_observed_statistics_and_bounds():
    weights, mask, f = _random_inputs(3)
    m = _masked(f, mask)
    rows = aggregate_operational_districts(_districts(len(weights)), weights, raw=m["raw"], corrected=m["corrected"],
                                           observed=m["observed"], heavy_p=m["heavy"], very_heavy_p=m["very_heavy"])
    for row, w in zip(rows, weights):
        active = (w > 0) & mask
        q = w[active] / w[active].sum()
        assert row["observed_mean_mm"] == pytest.approx(float(q @ f["observed"][active]))
        assert row["observed_max_mm"] == pytest.approx(float(f["observed"][active].max()))
        assert row["observed_mean_mm"] <= row["observed_max_mm"] + 1e-9
        for key in ("heavy_area_fraction", "very_heavy_area_fraction", "observed_heavy_area_fraction",
                    "observed_very_heavy_area_fraction", "heavy_probability", "very_heavy_probability"):
            assert 0 <= row[key] <= 1
        assert row["observed_heavy_area_fraction"] >= row["observed_very_heavy_area_fraction"]


def test_uniform_field_and_thresholds_are_inclusive():
    weights = np.zeros((1, GRID_CELLS), dtype=np.float32)
    weights[0, :4] = [1, 2, 3, 4]
    flat = np.full(GRID_CELLS, np.nan)
    flat[:4] = [HEAVY_MM, HEAVY_MM - 0.01, VERY_HEAVY_MM, 0.0]
    row = aggregate_operational_districts(_districts(1), weights, raw=flat, corrected=flat, observed=flat)[0]
    assert row["heavy_area_fraction"] == pytest.approx((1 + 3) / 10)        # 64.5 and 115.6 count, 64.49 does not
    assert row["very_heavy_area_fraction"] == pytest.approx(3 / 10)
    assert row["heavy_probability"] is None and row["very_heavy_probability"] is None


def test_districts_without_valid_cells_are_omitted_and_shape_errors_raise():
    weights = np.zeros((2, GRID_CELLS), dtype=np.float32)
    weights[0, 0], weights[1, 1] = 1.0, 1.0
    flat = np.full(GRID_CELLS, np.nan)
    flat[0] = 5.0                                      # only cell 0 is valid
    rows = aggregate_operational_districts(_districts(2), weights, raw=flat, corrected=flat, observed=flat)
    assert [r["district_id"] for r in rows] == ["D0"]
    with pytest.raises(ValueError):
        aggregate_operational_districts(_districts(3), weights, raw=flat, corrected=flat, observed=flat)
    with pytest.raises(ValueError):
        aggregate_operational_districts(_districts(2), weights, raw=flat[:10], corrected=flat, observed=flat)


def test_a_cell_missing_any_required_field_gets_no_weight():
    weights = np.zeros((1, GRID_CELLS), dtype=np.float32)
    weights[0, :2] = 1.0
    raw, corr, obs = (np.full(GRID_CELLS, np.nan) for _ in range(3))
    raw[:2], corr[:2], obs[0] = 10.0, 20.0, 30.0          # observation missing at cell 1
    row = aggregate_operational_districts(_districts(1), weights, raw=raw, corrected=corr, observed=obs)[0]
    assert row["valid_grid_cells"] == 1 and row["observed_mean_mm"] == 30.0


def test_flat_field_rejects_bad_pixel_maps():
    with pytest.raises(ValueError):
        flat_field(np.ones(2), np.array([7, 7]))
    with pytest.raises(ValueError):
        flat_field(np.ones(1), np.array([GRID_CELLS]))
    field = flat_field(np.array([1.0, 2.0]), np.array([0, 2400]))
    assert np.isfinite(field).sum() == 2 and field[2400] == 2.0


@needs_data
def test_shared_weights_equal_independent_recomputation_from_pinned_geometry():
    lat, lon = np.arange(10, 22.01, .25), np.arange(68, 80.01, .25)
    districts, weights = district_weights(SOURCE, lat, lon)
    stored = np.load(PHASE2C / "district_weights.npy", allow_pickle=False)
    geometry = json.loads((PHASE2C / "districts.geojson").read_text(encoding="utf-8"))
    assert [d["district_id"] for d in districts] == [f["properties"]["district_id"] for f in geometry["features"]]
    assert np.array_equal(weights, stored)


# ---------------------------------------------------------------------------------------------
# API: cross-path consistency with the already-served frozen grids
# ---------------------------------------------------------------------------------------------

CASES = {2025: "20250714_day2_24h", 2024: "20240718_day2_24h"}


@pytest.fixture(scope="module")
def client() -> TestClient:
    from backend.main import app
    return TestClient(app)


def _grid(client, year, case, field):
    response = client.get(f"/api/science/operational/{year}/cases/{case}/rainfall", params={"field": field})
    assert response.status_code == 200, response.text
    return np.array([[np.nan if v is None else v for v in row] for row in response.json()["values"]], float).ravel()


def _probability(client, year, case, target):
    response = client.get(f"/api/science/operational/{year}/cases/{case}/probability/{target}")
    assert response.status_code == 200, response.text
    return np.array([[np.nan if v is None else v for v in row] for row in response.json()["values"]], float).ravel()


@needs_data
@pytest.mark.parametrize("year", [2024, 2025])
@pytest.mark.parametrize("model", ["m1", "m3"])
def test_district_endpoint_equals_independent_recomputation_from_served_grids(client, year, model):
    case = CASES[year]
    response = client.get(f"/api/science/operational/{year}/cases/{case}/districts", params={"model": model})
    assert response.status_code == 200, response.text
    body = response.json()
    weights = np.load(PHASE2C / "district_weights.npy", allow_pickle=False)
    ids = [f["properties"]["district_id"] for f in
           json.loads((PHASE2C / "districts.geojson").read_text(encoding="utf-8"))["features"]]
    imd, corrected = _grid(client, year, case, "imd"), _grid(client, year, case, model)
    raw = _grid(client, year, case, "raw")
    hp, vp = _probability(client, year, case, "heavy"), _probability(client, year, case, "very_heavy")
    valid = np.isfinite(imd) & np.isfinite(corrected) & np.isfinite(hp) & np.isfinite(vp)
    assert valid.sum() == 1301 and np.isfinite(raw[valid]).all()
    by_id = {r["district_id"]: r for r in body["districts"]}
    expected_ids = []
    for district_id, w in zip(ids, weights):
        active = (w > 0) & valid
        if w[active].sum() == 0:
            continue
        expected_ids.append(district_id)
        q = w[active] / w[active].sum()
        row = by_id[district_id]
        assert row["valid_grid_cells"] == int(active.sum())
        assert row["observed_mean_mm"] == pytest.approx(float(q @ imd[active]), abs=1e-3)
        assert row["corrected_mean_mm"] == pytest.approx(float(q @ corrected[active]), abs=1e-3)
        assert row["raw_mean_mm"] == pytest.approx(float(q @ raw[active]), abs=1e-3)
        assert row["heavy_probability"] == pytest.approx(float(q @ hp[active]), abs=1e-6)
        assert row["very_heavy_area_fraction"] == pytest.approx(float(q @ (corrected[active] >= VERY_HEAVY_MM)), abs=1e-9)
        assert row["observed_max_mm"] == pytest.approx(float(imd[active].max()), abs=1e-3)
    assert sorted(by_id) == sorted(expected_ids)
    assert body["year"] == year and body["model"] == model and body["source_district_count"] == 188
    assert body["predicted_regime"] in ("ACTIVE_MONSOON", "BREAK_WEAK_MONSOON", "LOW_DEPRESSION_INFLUENCED")
    assert "not a live district forecast" in body["method"]
    assert len(body["weights_sha256"]) == 64 and len(body["geometry_sha256"]) == 64


@needs_data
def test_district_endpoint_errors_and_model_roles(client):
    base = "/api/science/operational"
    assert client.get(f"{base}/2025/cases/{CASES[2025]}/districts", params={"model": "m9"}).status_code == 422
    unavailable = client.get(f"{base}/2023/cases/20230714_day2_24h/districts")
    assert unavailable.status_code == 404 and unavailable.json()["code"] == "SCIENCE_PRODUCT_UNAVAILABLE"
    mismatch = client.get(f"{base}/2024/cases/{CASES[2025]}/districts")
    assert mismatch.status_code == 404
    assert "pre-registered primary" in client.get(f"{base}/2025/cases/{CASES[2025]}/districts").json()["model_role"]
    assert "selected 2024" in client.get(f"{base}/2024/cases/{CASES[2024]}/districts").json()["model_role"]
    m2 = client.get(f"{base}/2025/cases/{CASES[2025]}/districts", params={"model": "m2"}).json()
    assert "pre-registered" not in m2["model_role"]
