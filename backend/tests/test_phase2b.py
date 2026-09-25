import numpy as np

from app.ml.phase2b import (
    FEATURE_NAMES,
    bilinear_to_target,
    deterministic_case_bootstrap,
    event_metrics,
    eligible_case_rows,
    verification_metrics,
)


def test_bilinear_alignment_preserves_linear_field_at_target_centers():
    source_lat = np.array([0.0, 1.0, 2.0])
    source_lon = np.array([10.0, 11.0, 12.0])
    target_lat = np.array([0.25, 1.25])
    target_lon = np.array([10.5, 11.5])
    field = source_lat[:, None] * 2 + source_lon[None, :] * 3
    actual = bilinear_to_target(field, source_lat, source_lon, target_lat, target_lon)
    expected = target_lat[:, None] * 2 + target_lon[None, :] * 3
    assert np.allclose(actual, expected, rtol=0, atol=1e-12)
    assert "predicted_regime" not in FEATURE_NAMES
    assert "prototype_regime_id" not in FEATURE_NAMES


def test_event_metrics_report_undefined_values_as_null_with_reason_and_count():
    observed = np.array([1.0, 2.0, 0.0])
    predicted = np.array([0.0, 1.0, 0.0])
    result = event_metrics(observed, predicted, 64.5)
    assert result["sample_count"] == 3
    assert result["observed_event_count"] == 0
    assert result["metrics"]["POD"] is None
    assert result["metrics"]["FAR"] is None
    assert result["undefined_reason"] == "no observed events at this threshold"
    assert result["undefined_metric_reasons"]["POD"] == "no observed events"
    assert result["undefined_metric_reasons"]["FAR"] == "no forecast events"


def test_case_population_is_an_actual_eligibility_intersection(tmp_path):
    import pandas as pd

    control = pd.DataFrame([
        {"initialization": "2018-06-01T00:00:00+00:00", "product": "day1_24h", "CONTROL_MODEL_ELIGIBLE": True, "PAIR_VALID": True},
        {"initialization": "2018-06-02T00:00:00+00:00", "product": "day1_24h", "CONTROL_MODEL_ELIGIBLE": True, "PAIR_VALID": False},
        {"initialization": "2018-06-03T00:00:00+00:00", "product": "day1_24h", "CONTROL_MODEL_ELIGIBLE": True, "PAIR_VALID": True},
    ])
    regime = pd.DataFrame([
        {"initialization": "2018-06-01T00:00:00+00:00", "product": "day1_24h", "REGIME_ELIGIBLE": True},
        {"initialization": "2018-06-02T00:00:00+00:00", "product": "day1_24h", "REGIME_ELIGIBLE": True},
    ])
    control.to_csv(tmp_path / "control_model_index.csv", index=False)
    regime.to_csv(tmp_path / "regime_index.csv", index=False)
    result = eligible_case_rows(tmp_path)
    assert result["case_key"].tolist() == ["2018-06-01T00:00:00Z|day1_24h"]


def test_verification_rainfall_output_is_nonnegative_and_thresholds_are_24h():
    result = verification_metrics(np.array([0.0, 70.0]), np.array([0.0, 72.0]))
    assert set(result["thresholds"]) == {"heavy_64_5", "very_heavy_115_6"}
    assert result["thresholds"]["heavy_64_5"]["observed_event_count"] == 1


def test_case_bootstrap_is_deterministic_and_clustered_by_case():
    observed = np.array([0.0, 1.0, 3.0, 5.0])
    predicted = np.array([0.5, 1.5, 2.5, 4.5])
    cases = np.array([0, 0, 1, 1])
    first = deterministic_case_bootstrap(observed, predicted, cases, repeats=50)
    second = deterministic_case_bootstrap(observed, predicted, cases, repeats=50)
    assert first == second
    assert first["case_count"] == 2
