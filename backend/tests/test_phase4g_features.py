"""Phase 4G feature construction and sealed-holdout guards."""

from datetime import date

import numpy as np
import pytest

from experiments.recent_historical.phase4g_features_v1 import build
from experiments.recent_historical.phase4g_features_v1.finalize import verify_year
from backend.app.ml.phase2b import bilinear_to_target
from backend.app.ml.forecast_regimes import extract_regime_features


def test_frozen_feature_order_and_model_only_probability_tail():
    assert len(build.DETERMINISTIC_NAMES) == 22
    assert len(build.REGIME_NAMES) == 12
    assert build.DETERMINISTIC_NAMES[0] == "raw_c00_rain_mm"
    assert build.DETERMINISTIC_NAMES[-1] == "lead_hours"
    assert build.MISSING_MODEL_COLUMNS == (
        "frozen_m2_corrected_mm", "regime_p_active", "regime_p_break_weak", "regime_p_low_depression"
    )


def test_observation_mapping_and_holdout_access_denial():
    assert build.observation_date("2023-06-01T00:00:00Z", "day1_24h") == date(2023, 6, 2)
    assert build.observation_date("2024-10-03T00:00:00Z", "day3_24h") == date(2024, 10, 6)
    with pytest.raises(PermissionError):
        build.assert_observation_year_allowed(2025)
    with pytest.raises(ValueError):
        build.observation_date("2023-06-01T00:00:00Z", "day4_24h")


def test_inclusive_event_labels_and_invalid_target_denial():
    heavy, very_heavy = build.labels(np.array([0, 64.499, 64.5, 115.6]))
    assert heavy.tolist() == [False, False, True, True]
    assert very_heavy.tolist() == [False, False, False, True]
    with pytest.raises(ValueError):
        build.labels(np.array([-999.0]))


def test_bilinear_interpolation_aligns_without_resolution_claim():
    latitude = np.array([0., 1., 2.])
    longitude = np.array([0., 1., 2.])
    field = latitude[:, None] + 2 * longitude[None, :]
    aligned = bilinear_to_target(field, latitude, longitude, np.array([.5, 1.5]), np.array([.5, 1.5]))
    np.testing.assert_allclose(aligned, [[1.5, 3.5], [2.5, 4.5]])


def test_regime_diagnostics_are_forecast_only_and_ordered():
    fields = np.stack([np.full((51, 81), value) for value in (1., 2., .01, 5800., 100000., 50.)])
    result = extract_regime_features(fields, build.CONTEXT_LAT, build.CONTEXT_LON)
    assert result.shape == (12,)
    assert result[0] == pytest.approx(50.)
    assert result[1] == pytest.approx(.01)
    assert result[5] == pytest.approx(50 * np.hypot(1, 2))


def test_year_roles_are_disjoint_and_2025_never_maps_to_observation():
    assert build.ROLES == {2023: "train", 2024: "validation", 2025: "test_sealed"}
    assert len(set(build.ROLES.values())) == 3
    assert build.assert_observation_year_allowed(2023).name == "RF25_ind2023_rfp25.nc"
    with pytest.raises(PermissionError):
        build.assert_observation_year_allowed(2025)


def test_built_artifacts_have_matching_hashes_masks_and_sealed_target():
    if not (build.OUT / "feature_generation_manifest_v1.json").exists():
        pytest.skip("Phase 4G artifact corpus not installed")
    assert verify_year(2023)["deterministic_cases"] == 200
    assert verify_year(2024)["deterministic_cases"] == 183
    assert verify_year(2025)["deterministic_cases"] == 232
    assert not (build.OUT / "2025" / "test_sealed" / "deterministic" / "y_mm.npy").exists()


def test_frozen_stage_a_manifest_binds_source_code_and_split():
    path = build.OUT / "feature_generation_manifest_v1.json"
    if not path.exists():
        pytest.skip("Phase 4G artifact corpus not installed")
    import json
    freeze = json.loads(path.read_text(encoding="utf-8"))
    assert freeze["builder_sha256"] == build.sha256(build.Path(build.__file__))
    assert freeze["stage_a_year_manifest_sha256"]["2023"] == build.sha256(build.OUT / "2023/train/year_manifest.json")
    assert freeze["stage_a_year_manifest_sha256"]["2024"] == build.sha256(build.OUT / "2024/validation/year_manifest.json")
