import numpy as np
import pytest
from fastapi.testclient import TestClient

from app.core.config import TEST_YEARS, TRAIN_YEARS, UNSEEN_YEARS, VAL_YEARS
from app.data.audit import datasetAudit
from app.data.loader import load_source_dataset
from app.data.readiness import ScientificReadinessError, require_training_ready
from app.data.splitter import create_chronological_splits
from app.ml.features import prepare_features, validate_operational_features
from app.ml.leakage import checkForTargetLeakage
from app.verification.metrics import compute_brier_score, compute_contingency_table, compute_continuous_metrics
from main import app


EXPECTED_DATA_HASH = "7b01a5f35bd32a30c7998401c17d26d1e9b2180fca850b7b5bb56f06fe4cb241"


def test_checked_in_dataset_matches_manifest():
    df, metadata = load_source_dataset()
    assert metadata["dataset_id"] == "goa-clean-prototype-7b01a5f3"
    assert metadata["sha256"] == EXPECTED_DATA_HASH
    assert metadata["total_rows"] == 44_064
    assert metadata["total_columns"] == 26
    assert metadata["provenance_status"] == "unverified"
    assert metadata["training_eligible"] is False
    assert "regime_id" not in df.columns
    assert df["location_id"].nunique() == 12


def test_quality_audit_is_descriptive_not_operational_threshold_claim():
    df, metadata = load_source_dataset()
    audit = datasetAudit(df, metadata)
    assert audit["total_missing"] == 0
    assert audit["duplicate_rows"] == 0
    assert audit["quality_audit"]["non_negative_obs_pass"] is True
    obs = audit["observed_rainfall_stats"]
    assert obs["accumulation_hours"] == 6
    assert "not IMD 24-hour operational" in obs["threshold_warning"]


def test_temporal_split_follows_configuration():
    df, _ = load_source_dataset()
    splits = create_chronological_splits(df)
    expected = {
        "train": ("train_df", TRAIN_YEARS),
        "validation": ("val_df", VAL_YEARS),
        "test": ("test_df", TEST_YEARS),
        "unseen": ("unseen_df", UNSEEN_YEARS),
    }
    for name, (key, years) in expected.items():
        partition = splits[key]
        assert splits["metadata"][name]["years"] == years
        assert set(partition["year"].unique()) == set(years)

    assert splits["metadata"]["train"]["rows"] == 29_376
    assert splits["metadata"]["validation"]["rows"] == 7_344
    assert splits["metadata"]["test"]["rows"] == 7_344
    assert splits["metadata"]["unseen"]["rows"] == 0
    assert splits["metadata"]["unseen"]["start_date"] is None


def test_feature_builder_excludes_unknown_valid_time_atmosphere():
    df, _ = load_source_dataset()
    features, names = prepare_features(df.head(8))
    assert checkForTargetLeakage(names) is True
    assert list(features.columns) == names
    assert "temp_2m" not in names
    assert "relative_humidity" not in names
    assert "pressure_msl" not in names
    assert "nwp_temp_diff" not in names
    assert "orographic_terrain_wind_proxy" not in names
    with pytest.raises(ValueError, match="provenance is not verified"):
        validate_operational_features(names)


def test_training_is_explicitly_blocked():
    df, metadata = load_source_dataset()
    with pytest.raises(ScientificReadinessError) as exc:
        require_training_ready(df, metadata)
    message = str(exc.value)
    assert "regime_id is absent" in message
    assert "ineligible for training" in message
    assert "24-hour heavy/very-heavy" in message


def test_metric_formulas_and_event_counts():
    y_obs = np.array([0.0, 10.0, 70.0, 120.0])
    y_pred = y_obs.copy()
    metrics = compute_continuous_metrics(y_pred, y_obs)
    assert metrics["rmse"] == 0.0
    assert metrics["mae"] == 0.0
    assert metrics["r2"] == 1.0

    contingency = compute_contingency_table(y_pred, y_obs, 64.5)
    assert contingency["hits"] == 2
    assert contingency["misses"] == 0
    assert contingency["pod"] == 1.0
    assert contingency["observed_events"] == 2

    brier = compute_brier_score(np.array([0.0, 0.0, 1.0, 1.0]), y_obs, 64.5)
    assert brier["brier_score"] == 0.0
    assert brier["positive_cases"] == 2


def test_api_reports_degraded_status_and_blocks_legacy_metrics():
    client = TestClient(app)
    assert app.title == "VarshaSetu API"

    health = client.get("/api/health")
    assert health.status_code == 200
    assert health.json()["system"] == "VarshaSetu scientific prototype"

    status = client.get("/api/status")
    assert status.status_code == 200
    payload = status.json()
    assert payload["project"] == "VarshaSetu"
    assert payload["scientific_readiness"]["ready"] is False
    assert payload["legacy_report"]["status"] == "quarantined_unverified_legacy_artifact"

    metrics = client.get("/api/metrics/overall")
    assert metrics.status_code == 409
    assert metrics.json()["detail"]["status"] == "blocked_by_scientific_readiness_gate"


def test_predictions_are_nonnegative_for_raw_baseline():
    from app.ml.MODELSS import BaselineNWPModel

    predictions = BaselineNWPModel().predict(np.array([[-2.0], [0.0], [3.5]]))
    assert np.array_equal(predictions, np.array([0.0, 0.0, 3.5]))
