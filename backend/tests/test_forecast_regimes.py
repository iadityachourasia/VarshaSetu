import json

import numpy as np
import pytest

from backend.app.ml.forecast_regimes import (
    ATMOSPHERIC_VARIABLES,
    FEATURE_NAMES,
    FEATURE_REGISTRY,
    REGIME_NAMES,
    SafeLogisticRegimeClassifier,
    StaticGeographyInterface,
    TrainingOnlyPseudoLabeler,
    extract_regime_features,
    relative_vorticity,
    validate_forecast_feature_schema,
    validate_feature_registry,
    validate_temporal_roles,
)


def synthetic_features(rows=120):
    rng = np.random.default_rng(26080)
    base = rng.normal(size=(rows, len(FEATURE_NAMES)))
    base[:, FEATURE_NAMES.index("mslp_minimum")] += 100000.0
    base[:, FEATURE_NAMES.index("mslp_area_mean")] += 100500.0
    base[:, FEATURE_NAMES.index("z500_area_mean")] += 5800.0
    base[:, FEATURE_NAMES.index("pwat_area_mean")] += 45.0
    base[:, FEATURE_NAMES.index("q700_area_mean")] = (
        0.01 + base[:, FEATURE_NAMES.index("q700_area_mean")] * 0.001
    )
    return base


def test_regime_feature_extraction_is_forecast_only_and_deterministic():
    latitude = np.arange(5.0, 30.0 + 0.5, 0.5)
    longitude = np.arange(55.0, 95.0 + 0.5, 0.5)
    fields = np.zeros((len(ATMOSPHERIC_VARIABLES), latitude.size, longitude.size))
    fields[0] = 5.0
    fields[1] = 2.0
    fields[2] = 0.012
    fields[3] = 5800.0
    fields[4] = 100500.0
    fields[5] = 48.0
    first = extract_regime_features(fields, latitude, longitude)
    second = extract_regime_features(fields.copy(), latitude, longitude)
    assert np.array_equal(first, second)
    assert first.shape == (len(FEATURE_NAMES),)
    assert not any("rain" in name or "observation" in name for name in FEATURE_NAMES)
    assert np.allclose(relative_vorticity(fields[0], fields[1], latitude, longitude), 0)


def test_missing_atmospheric_predictor_fails_closed():
    latitude = np.arange(5.0, 30.0 + 0.5, 0.5)
    longitude = np.arange(55.0, 95.0 + 0.5, 0.5)
    fields = np.ones((6, latitude.size, longitude.size))
    fields[0, 0, 0] = -999.0
    with pytest.raises(ValueError, match="incomplete"):
        extract_regime_features(fields, latitude, longitude)


def test_leakage_schema_rejects_non_frozen_or_target_like_names():
    validate_forecast_feature_schema(FEATURE_NAMES)
    with pytest.raises(ValueError):
        validate_forecast_feature_schema(FEATURE_NAMES[:-1] + ("observed_rain",))


def test_feature_availability_classes_and_temporal_roles_are_frozen():
    validate_feature_registry()
    validate_temporal_roles(2017, 2018, 2019)
    allowed = [item for item in FEATURE_REGISTRY if item["regime_allowed"]]
    assert all(
        item["availability"] in {"FORECAST_TIME", "DERIVED_FORECAST_TIME"}
        for item in allowed
    )
    assert not any(item["name"] == "imd_observed_rainfall" for item in allowed)
    with pytest.raises(ValueError):
        validate_temporal_roles(2018, 2017, 2019)


def test_static_geography_interface_does_not_fabricate_unavailable_fields():
    static = StaticGeographyInterface(np.array([10.0, 10.25]), np.array([68.0, 68.25]))
    assert static.elevation_m is None
    assert static.terrain_gradient is None
    assert static.distance_to_coast_km is None
    assert static.district_membership is None
    with pytest.raises(ValueError, match="does not align"):
        StaticGeographyInterface(
            np.array([10.0, 10.25]),
            np.array([68.0, 68.25]),
            elevation_m=np.zeros((1, 1)),
        )


def test_pseudo_labels_are_training_only_deterministic_and_three_class():
    features = synthetic_features()
    labeler = TrainingOnlyPseudoLabeler.fit(features, fitted_year=2017)
    labels1, low1, active1 = labeler.transform(features)
    restored = TrainingOnlyPseudoLabeler.from_dict(
        json.loads(json.dumps(labeler.to_dict()))
    )
    labels2, low2, active2 = restored.transform(features)
    assert np.array_equal(labels1, labels2)
    assert np.array_equal(low1, low2)
    assert np.array_equal(active1, active2)
    assert set(labels1) == {0, 1, 2}
    with pytest.raises(ValueError, match="2017 only"):
        TrainingOnlyPseudoLabeler.fit(features, fitted_year=2018)


def test_safe_logistic_json_round_trip_and_probability_simplex():
    features = synthetic_features()
    labels, _, _ = TrainingOnlyPseudoLabeler.fit(features).transform(features)
    model = SafeLogisticRegimeClassifier.fit(features, labels)
    probability = model.predict_proba(features)
    restored = SafeLogisticRegimeClassifier.from_dict(
        json.loads(json.dumps(model.to_dict()))
    )
    assert len(REGIME_NAMES) == 3
    assert np.allclose(probability.sum(axis=1), 1.0, atol=1e-12)
    assert np.array_equal(model.predict(features), restored.predict(features))
    assert np.array_equal(probability, restored.predict_proba(features))
    assert model.to_dict()["unsafe_pickle_required"] is False
