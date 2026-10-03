"""Corpus v2 features (2021 development, 2022 sealed): the sealing guard holds and the arrays are internally and externally consistent (docs/128)."""

from __future__ import annotations

import inspect
import json
from pathlib import Path

import numpy as np
import pytest

from experiments.recent_historical.corpus2_features_v1 import build

FEATURES = build.OUT
PHASE7 = Path(__file__).resolve().parents[1] / "app/evidence_data/phase7"
needs_data = pytest.mark.skipif(not (FEATURES / "feature_generation_manifest_v1.json").exists(), reason="the derived feature arrays are local (gitignored)")


def test_observation_values_of_the_sealed_year_cannot_be_opened():
    assert build.OBSERVATION_YEARS == frozenset({2021}) and build.ROLES == {2021: "development", 2022: "sealed_forecast_only"}
    with pytest.raises(PermissionError):
        build.assert_observation_year_allowed(2022)
    with pytest.raises(PermissionError):
        build.development_observation(2022, "2022-06-01T00:00:00Z", "day1_24h")
    assert inspect.getsource(build).count("import load_imd_day") == 1            # the only reference to the IMD reader ...
    assert "import load_imd_day" in inspect.getsource(build.development_observation)   # ... is inside the guarded function


@needs_data
def test_the_2022_features_carry_no_target_label_or_observation_date():
    base = FEATURES / "2022" / "sealed_forecast_only"
    assert not any((base / "deterministic" / name).exists() for name in ("y_mm.npy", "heavy_label.npy", "very_heavy_label.npy"))
    cases = json.loads((base / "deterministic" / "cases.json").read_text(encoding="utf-8"))
    assert all(c["valid_observation_date"] is None for c in cases)
    report = json.loads((base / "year_manifest.json").read_text(encoding="utf-8"))
    assert report["observations_paired"] is False and "unseal" in report["cell_mask"]
    freeze = json.loads((FEATURES / "feature_generation_manifest_v1.json").read_text(encoding="utf-8"))
    assert freeze["observation_values_opened"] == {"2021": True, "2022": False} and freeze["model_training_or_inference"] is False and freeze["metrics_computed"] is False


@needs_data
@pytest.mark.parametrize("year", [2021, 2022])
def test_matrices_are_finite_nonnegative_and_match_the_case_index(year):
    base = FEATURES / str(year) / build.ROLES[year]
    x = np.load(base / "deterministic" / "X.npy")
    cases = json.loads((base / "deterministic" / "cases.json").read_text(encoding="utf-8"))
    assert x.shape == (sum(c["row_count"] for c in cases), 22) and np.isfinite(x).all() and (x[:, 0] >= 0).all()
    assert [c["row_start"] for c in cases] == list(np.cumsum([0] + [c["row_count"] for c in cases])[:-1])
    pixel = np.load(base / "deterministic" / "pixel_index.npy")
    lat_i, lon_i = np.divmod(pixel.astype(np.int64), 49)
    assert np.allclose(x[:, 19], 10 + lat_i / 4) and np.allclose(x[:, 20], 68 + lon_i / 4)
    regime = np.load(base / "regime" / "X.npy")
    assert regime.shape == (375, 12) and np.isfinite(regime).all()
    evidence = json.loads((Path(build.EVIDENCE)).read_text(encoding="utf-8"))["counts"]["by_year"][str(year)]
    assert len(cases) == evidence["deterministic_source_eligible"]
    ensemble = np.load(base / "ensemble_baseline" / "members_mm.npy")
    ens_cases = json.loads((base / "ensemble_baseline" / "cases.json").read_text(encoding="utf-8"))
    assert len(ens_cases) == evidence["full_five_member_rainfall_qc_pass"] and ensemble.shape[1] == 5 and np.isfinite(ensemble).all() and (ensemble >= 0).all()
    first = ens_cases[0]
    start = first["ensemble_row_start"]
    rows = x[first["row_start"]: first["row_start"] + first["row_count"], 0]
    assert np.array_equal(ensemble[start: start + first["row_count"], 0], rows)      # the control member is the deterministic rainfall feature


@needs_data
def test_2022_keeps_every_finite_forecast_cell_so_no_observation_mask_is_formed():
    cases = json.loads((FEATURES / "2022/sealed_forecast_only/deterministic/cases.json").read_text(encoding="utf-8"))
    assert {c["row_count"] for c in cases} == {2401}


@needs_data
def test_2021_paired_cells_are_exactly_the_independent_land_footprint_and_labels_follow_the_thresholds():
    base = FEATURES / "2021" / "development" / "deterministic"
    cases = json.loads((base / "cases.json").read_text(encoding="utf-8"))
    pixel = np.load(base / "pixel_index.npy")
    zone = json.loads((PHASE7 / "static_geography_v1.json").read_text(encoding="utf-8"))["fields"]["zone"]
    land = {i * 49 + j for i in range(49) for j in range(49) if zone[i][j] is not None}
    assert {c["row_count"] for c in cases} == {1301} and set(pixel.tolist()) == land      # IMD non-fill cells equal the terrain-derived land cells in every case
    y = np.load(base / "y_mm.npy")
    assert y.shape == (len(pixel),) and np.isfinite(y).all() and (y >= 0).all()
    assert np.array_equal(np.load(base / "heavy_label.npy"), y >= 64.5) and np.array_equal(np.load(base / "very_heavy_label.npy"), y >= 115.6)
    assert all(c["valid_observation_date"] for c in cases)
