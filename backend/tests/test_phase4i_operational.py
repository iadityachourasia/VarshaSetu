"""Read-only Phase 4I frozen-artifact, leakage and holdout checks."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest
from xgboost import XGBRegressor

from backend.app.ml.phase2b import safe_ridge_predict
from experiments.recent_historical.operational_model_protocol_v1.build_protocol import outer_membership
from experiments.recent_historical.phase4i_operational_model_development_v1.core import (
    DATA, HERE, PROTOCOL_DIR, load_year, read_json, sha256, verify_folds, verify_inputs,
)
from experiments.recent_historical.phase4i_operational_model_development_v1.features import broadcast_regime
from experiments.recent_historical.phase4i_operational_model_development_v1.freeze import verify_ready
from experiments.recent_historical.phase4i_operational_model_development_v1.probability import (
    _threshold_table, apply_calibrator, calibration_split, predict_logistic,
)
from experiments.recent_historical.phase4i_operational_model_development_v1.regime import (
    balanced_agreement, predict_proba,
)


def test_frozen_inputs_and_no_2025_observation_access() -> None:
    verify_inputs()
    assert verify_ready()["2025_outcome_status"] == "SEALED"
    with pytest.raises(PermissionError, match="2025 outcomes are SEALED"):
        load_year(2025)


def test_fold_verification_and_three_day_embargo() -> None:
    train = load_year(2023)
    folds = read_json(PROTOCOL_DIR / "crossfit_folds_2023.json")
    report = verify_folds(folds, train)
    assert [r["holdout_cases"] for r in report["folds"]] == [40, 39, 44, 43, 34]
    for fold in folds["folds"]:
        tr, held, embargo = outer_membership(folds, fold["fold_id"])
        assert len(set(tr) & set(held)) == 0
        assert len(set(tr) & set(embargo)) == 0
        assert len(tr) + len(held) + len(embargo) == 200
        assert train.row_mask(held).sum() == 1301 * len(held)


def test_oof_lineage_coverage_and_prediction_safety() -> None:
    train = load_year(2023)
    folds = read_json(PROTOCOL_DIR / "crossfit_folds_2023.json")
    regime_manifest = read_json(HERE / "oof_regime/manifest.json")
    rainfall_manifest = read_json(HERE / "oof_m2/manifest.json")
    regime = np.load(HERE / "oof_regime/probability.npy", allow_pickle=False)
    rain = np.load(HERE / "oof_m2/prediction.npy", allow_pickle=False)
    row_fit = np.load(HERE / "oof_m2/row_fit_index.npy", allow_pickle=False)
    assert regime.shape == (375, 3) and rain.shape == (260200,)
    assert regime_manifest["coverage"] == 375 and rainfall_manifest["coverage"] == 260200
    assert regime_manifest["missing_count"] == rainfall_manifest["missing_count"] == 0
    assert regime_manifest["duplicate_count"] == rainfall_manifest["duplicate_count"] == 0
    assert np.isfinite(regime).all() and np.allclose(regime.sum(axis=1), 1, atol=1e-12)
    assert np.isfinite(rain).all() and (rain >= 0).all()
    assert row_fit.shape == rain.shape and set(np.unique(row_fit)) == {1, 2, 3, 4, 5}
    assert rainfall_manifest["row_fit_index_sha256"] == sha256(HERE / "oof_m2/row_fit_index.npy")
    for index, record in enumerate(rainfall_manifest["folds"], start=1):
        assert np.all(row_fit[train.row_mask(record["heldout_case_ids"])] == index)
        assert rainfall_manifest["fit_id_by_index"][str(index)]["model_fit_id"] == record["model_sha256"]
    for records, population in ((regime_manifest["folds"], "regime_cases"), (rainfall_manifest["folds"], "deterministic_cases")):
        for row in records:
            tr, held, embargo = outer_membership(folds, row["fold_id"], population)
            assert row["train_case_ids"] == tr
            assert row["heldout_case_ids"] == held
            assert row["embargo_case_ids"] == embargo
            assert set(tr).isdisjoint(held)
    assert rainfall_manifest["case_ids"] == [c["case_id"] for c in train.cases]


def test_completed_2023_2024_feature_alignment() -> None:
    for year in (2023, 2024):
        data = load_year(year)
        matrix = np.load(HERE / f"probability_features/{year}/X_26.npy", allow_pickle=False)
        manifest = read_json(HERE / f"probability_features/{year}/manifest.json")
        correction = np.load(HERE / ("oof_m2/prediction.npy" if year == 2023 else "deterministic_models/M2_2024.npy"), allow_pickle=False)
        regime = np.load(HERE / ("oof_regime/probability.npy" if year == 2023 else "regime_models/2024_prospective_probability.npy"), allow_pickle=False)
        assert matrix.shape == (len(data.y), 26) and matrix.dtype == np.float32
        assert np.array_equal(matrix[:, :22], data.X)
        assert np.array_equal(matrix[:, 22], correction.astype(np.float32))
        assert np.array_equal(matrix[:, 23:], broadcast_regime(data, regime).astype(np.float32))
        assert manifest["X_26_sha256"] == sha256(HERE / f"probability_features/{year}/X_26.npy")
        assert manifest["case_ids"] == [c["case_id"] for c in data.cases]


def test_regime_model_and_safe_deterministic_serialization() -> None:
    valid = load_year(2024)
    common = read_json(DATA / "common_comparison_populations_2024.json")
    assert [c["case_id"] for c in valid.cases] == common["COMMON_DETERMINISTIC_2024"]["case_ids"]
    assert common["COMMON_DETERMINISTIC_2024"]["cell_count"] == len(valid.y) == 238083
    classifier = read_json(HERE / "regime_models/full_2023_classifier.json")
    stored = np.load(HERE / "regime_models/2024_prospective_probability.npy", allow_pickle=False)
    assert np.allclose(predict_proba(valid.regime_X, classifier), stored, rtol=0, atol=1e-12)
    ladder = read_json(HERE / "deterministic_models/validation_manifest.json")
    assert ladder["case_count"] == 183 and ladder["cell_count"] == 238083
    assert set(ladder["metrics"]) == {"M0", "M1", "M2", "M3", "M4"}
    for name, digest in ladder["prediction_sha256"].items():
        assert sha256(HERE / f"deterministic_models/{name}_2024.npy") == digest
    ridge = read_json(HERE / f"deterministic_models/M1_alpha_{ladder['selected_ridge_alpha']:g}.json")
    pred = np.load(HERE / "deterministic_models/M1_2024.npy", allow_pickle=False)
    assert np.allclose(safe_ridge_predict(ridge, valid.X), pred, rtol=1e-5, atol=1e-4)
    config = ladder["m2_upstream_config"]
    native = XGBRegressor()
    native.load_model(HERE / f"deterministic_models/M2_depth{config['max_depth']}_rounds{config['n_estimators']}.json")
    assert np.array_equal(np.maximum(0, native.predict(valid.X)).astype(np.float32),
                          np.load(HERE / "deterministic_models/M2_2024.npy", allow_pickle=False))
    assert all(not row["fallback"] for row in ladder["expert_records"])
    assert ladder["shared_experts_for_M3_M4"] is True


def test_calibration_split_and_selected_thresholds() -> None:
    valid = load_year(2024)
    split = read_json(HERE / "calibration/split_2024.json")
    assert split == calibration_split(valid)
    assert not set(split["calibration_case_ids"]) & set(split["selection_case_ids"])
    assert len(split["calibration_dates"]) == 72 and len(split["purged_dates"]) == 6
    assert len(split["selection_dates"]) == 47
    for target in ("heavy", "very_heavy"):
        report = read_json(HERE / f"validation/probability_{target}_2024.json")
        assert report["selected_calibration"] in ("identity", "sigmoid", "isotonic")
        assert report["selected_threshold"] in [round(i / 100, 2) for i in range(5, 100, 5)]
        table = report["threshold_table"]
        winner = min((row for row in table if row["CSI"] is not None),
                     key=lambda row: (-row["CSI"], row["threshold_probability"]))
        assert winner["threshold_probability"] == report["selected_threshold"]
        assert report["calibration_split_sha256"] == sha256(HERE / "calibration/split_2024.json")
        assert report["training_year"] == 2023


def test_probability_model_calibration_and_common_ensemble_population() -> None:
    valid = load_year(2024)
    X = np.load(HERE / "probability_features/2024/X_26.npy", allow_pickle=False)
    for target in ("heavy", "very_heavy"):
        report = read_json(HERE / f"validation/probability_{target}_2024.json")
        selected = next(c for c in report["candidate_models"] if c["id"] == report["selected_base_model_id"])
        if selected["kind"] == "logistic":
            model = read_json(HERE / selected["model_path"])
            raw = predict_logistic(X, model)
        else:
            raw = np.load(HERE / "probability_models" / target / f"{selected['id']}_2024.npy", allow_pickle=False)
        calibration = read_json(HERE / "calibration" / target / f"{selected['id']}_{report['selected_calibration']}.json")
        predicted = apply_calibrator(raw, calibration)
        stored = np.load(HERE / "probability_models" / target / "selected_2024_probability.npy", allow_pickle=False)
        assert np.allclose(predicted, stored, rtol=0, atol=1e-12)
        assert np.isfinite(stored).all() and ((stored >= 0) & (stored <= 1)).all()
        comparison = report["ensemble_common_comparison"]
        assert comparison["case_count"] == 67 and comparison["cell_count"] == 87167
        assert comparison["same_cell_mask"] is True
        assert comparison["five_member_fraction"]["sample_count"] == comparison["selected_ml"]["sample_count"] == 87167


def test_fss_and_final_ready_completeness() -> None:
    fss_report = read_json(HERE / "fss/2024.json")
    for threshold in ("heavy", "very_heavy"):
        for size in ("1", "3", "5", "9"):
            row = fss_report[threshold][size]
            assert row["all_common_cases"] == 183
            for name in ("raw", "selected", "matched_raw", "matched_selected"):
                score = row[name]["fss"]
                assert score is None or 0 <= score <= 1
    manifest = verify_ready()
    for key in ("phase4h_protocol_sha256", "phase4h_folds_sha256", "phase4g_feature_freeze_sha256",
                "phase4g_split_manifest_sha256", "oof_regime_probability_sha256", "oof_m2_correction_sha256",
                "probability_matrix_2023_sha256", "probability_matrix_2024_sha256",
                "metric_definitions_sha256", "evaluation_populations_sha256"):
        assert len(manifest[key]) == 64
    assert len(manifest["2025_eligible_forecast_only_case_ids"]) == 232
    assert manifest["2025_outcome_status"] == "SEALED"
    assert manifest["2025_observation_opened_by_phase4i"] is False


def test_balanced_agreement_fixed_classes() -> None:
    # A one-class inner block must not masquerade as perfect three-class agreement.
    assert balanced_agreement(np.array([0, 0]), np.array([0, 0])) == pytest.approx(1 / 3)
