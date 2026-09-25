import json
import joblib
import numpy as np
import pandas as pd
import subprocess
from datetime import datetime, timezone
from importlib.metadata import PackageNotFoundError, version

try:
    from backend.app.core.config import (
        SOURCE_CSV_PATH,
        MODELS_DIR,
        REPORTS_DIR,
        TARGET_COLUMN,
        NWP_COLUMN,
        LEGACY_THRESHOLDS_24H_MM,
        TARGET_ACCUMULATION_HOURS,
        RANDOM_SEED,
        REGIME_NAMES,
    )
    from backend.app.data.loader import load_source_dataset
    from backend.app.data.audit import datasetAudit
    from backend.app.data.splitter import create_chronological_splits
    from backend.app.data.readiness import (
        ScientificReadinessError,
        assess_training_readiness,
        require_training_ready,
    )
    from backend.app.ml.features import FEATURE_REGISTRY, prepare_features
    from backend.app.ml.MODELSS import (
        BaselineNWPModel,
        LinearMOSModel,
        XGBoost1000Model,
        HistGradientBoostingMLModel,
        RegimeClassifier,
        RegimeAwareMLModel,
        OracleRegimeMLModel,
        HeavyRainProbabilityModel,
    )
    from backend.app.verification.metrics import (
        compute_continuous_metrics,
        compute_contingency_table,
        compute_brier_score,
        compute_permutation_feature_importance,
    )
except ModuleNotFoundError:
    from app.core.config import (
        SOURCE_CSV_PATH,
        MODELS_DIR,
        REPORTS_DIR,
        TARGET_COLUMN,
        NWP_COLUMN,
        LEGACY_THRESHOLDS_24H_MM,
        TARGET_ACCUMULATION_HOURS,
        RANDOM_SEED,
        REGIME_NAMES,
    )
    from app.data.loader import load_source_dataset
    from app.data.audit import datasetAudit
    from app.data.splitter import create_chronological_splits
    from app.data.readiness import (
        ScientificReadinessError,
        assess_training_readiness,
        require_training_ready,
    )
    from app.ml.features import FEATURE_REGISTRY, prepare_features
    from app.ml.MODELSS import (
        BaselineNWPModel,
        LinearMOSModel,
        XGBoost1000Model,
        HistGradientBoostingMLModel,
        RegimeClassifier,
        RegimeAwareMLModel,
        OracleRegimeMLModel,
        HeavyRainProbabilityModel,
    )
    from app.verification.metrics import (
        compute_continuous_metrics,
        compute_contingency_table,
        compute_brier_score,
        compute_permutation_feature_importance,
    )

class ScientificPipelineService:
    """
    VarshaSetu scientific rainfall post-processing pipeline.

    Chronological design:
        TRAIN      = 2020-2023
        VALIDATION = 2024
        TEST       = 2025

    The 2025 test set is never used for model selection.
    """

    def __init__(self):
        self.df = None
        self.file_metadata = None
        self.audit_results = None
        self.splits = None
        self.feature_names = None

        self.baseline_model = BaselineNWPModel()
        self.mos_model = None
        self.global_ml = None

        self.xgb_1000 = None
        self.hist_gradient = None

        self.regime_classifier = None
        self.regime_aware_ml = None
        self.oracle_model = None

        self.heavy_rain_clf = None
        self.very_heavy_rain_clf = None

        self.final_report = None
        self.selected_global_model_name = None
        self.readiness = None

    def ensure_loaded(self):
        """Load data and only load artifacts proven to match a ready dataset."""
        if self.df is None:
            self.df, self.file_metadata = load_source_dataset()
            self.readiness = assess_training_readiness(self.df, self.file_metadata)

        if not self.readiness.ready:
            return
        
        report_path = REPORTS_DIR / "final_test_report.json"
        if report_path.exists() and self.final_report is None:
            with open(report_path, "r") as f:
                candidate_report = json.load(f)
            report_hash = candidate_report.get("file_metadata", {}).get("sha256")
            if report_hash == self.file_metadata["sha256"]:
                self.final_report = candidate_report
                
        mos_path = MODELS_DIR / "mos_model.pkl"
        if mos_path.exists() and self.regime_aware_ml is None:
            try:
                self.mos_model = joblib.load(mos_path)
                self.global_ml = joblib.load(MODELS_DIR / "global_ml.pkl")
                self.regime_classifier = joblib.load(MODELS_DIR / "regime_classifier.pkl")
                self.regime_aware_ml = joblib.load(MODELS_DIR / "regime_aware_ml.pkl")
                self.heavy_rain_clf = joblib.load(MODELS_DIR / "heavy_rain_clf.pkl")
                self.very_heavy_rain_clf = joblib.load(MODELS_DIR / "very_heavy_rain_clf.pkl")
            except Exception as e:
                print("Notice: Exception loading saved models:", e)

    def run_full_pipeline(self) -> dict:
        print("\n=== STEP 1: Loading Dataset & Auditing ===")
        self.df, self.file_metadata = load_source_dataset()
        self.readiness = assess_training_readiness(self.df, self.file_metadata)
        require_training_ready(self.df, self.file_metadata)
        self.audit_results = datasetAudit(self.df, self.file_metadata)
        print(f"Dataset rows: {len(self.df)}")

        print("\n=== STEP 2: Creating Chronological Partitions ===")
        self.splits = create_chronological_splits(self.df)
        train_df = self.splits["train_df"]
        val_df = self.splits["val_df"]
        test_df = self.splits["test_df"]
        unseen_df = self.splits["unseen_df"]

        print(f"TRAIN rows:      {len(train_df)}")
        print(f"VALIDATION rows: {len(val_df)}")
        print(f"TEST rows:       {len(test_df)}")
        print(f"UNSEEN rows:     {len(unseen_df)}")

        print("\n=== STEP 3: Engineering Features ===")
        X_train, self.feature_names = prepare_features(train_df)
        y_train = train_df[TARGET_COLUMN].values
        regime_train = train_df["regime_id"].values

        X_val, _ = prepare_features(val_df)
        y_val = val_df[TARGET_COLUMN].values
        regime_val = val_df["regime_id"].values

        X_test, _ = prepare_features(test_df)
        y_test = test_df[TARGET_COLUMN].values
        regime_test = test_df["regime_id"].values

        print("\n=== STEP 4: Training Models on TRAIN (2020-2023) ===")
        print("Training Linear MOS...")
        self.mos_model = LinearMOSModel().fit(X_train, y_train)

        print("Training XGBoost 1000 trees...")
        self.xgb_1000 = XGBoost1000Model().fit(X_train, y_train)

        print("Training HistGradientBoosting...")
        self.hist_gradient = HistGradientBoostingMLModel().fit(X_train, y_train)

        print("Training Weather Regime Classifier...")
        self.regime_classifier = RegimeClassifier().fit(X_train, regime_train)

        print("Training Regime-Aware ML...")
        self.regime_aware_ml = RegimeAwareMLModel(self.regime_classifier).fit(
            X_train, y_train, regime_train
        )

        self.oracle_model = OracleRegimeMLModel(self.regime_aware_ml)

        print("Training Heavy Rain classifier...")
        self.heavy_rain_clf = HeavyRainProbabilityModel(LEGACY_THRESHOLDS_24H_MM["heavy"]).fit(
            X_train, y_train
        )
        self.very_heavy_rain_clf = HeavyRainProbabilityModel(LEGACY_THRESHOLDS_24H_MM["very_heavy"]).fit(
            X_train, y_train
        )

        print("\n=== STEP 5: Model Selection on VALIDATION (2024) ===")
        val_nwp = self.baseline_model.predict(X_val)
        val_mos = self.mos_model.predict(X_val)
        val_xgb1000 = self.xgb_1000.predict(X_val)
        val_hgb = self.hist_gradient.predict(X_val)
        val_regime, _, _ = self.regime_aware_ml.predict(X_val)

        val_raw_metrics = compute_continuous_metrics(val_nwp, y_val)
        val_mos_metrics = compute_continuous_metrics(
            val_mos, y_val, val_raw_metrics["rmse"], val_raw_metrics["mae"]
        )
        val_xgb1000_metrics = compute_continuous_metrics(
            val_xgb1000, y_val, val_raw_metrics["rmse"], val_raw_metrics["mae"]
        )
        val_hgb_metrics = compute_continuous_metrics(
            val_hgb, y_val, val_raw_metrics["rmse"], val_raw_metrics["mae"]
        )
        val_regime_metrics = compute_continuous_metrics(
            val_regime, y_val, val_raw_metrics["rmse"], val_raw_metrics["mae"]
        )

        candidates = {
            "XGBoost_1000": (self.xgb_1000, val_xgb1000_metrics["rmse"]),
            "HistGradientBoosting": (self.hist_gradient, val_hgb_metrics["rmse"]),
        }

        self.selected_global_model_name = min(
            candidates, key=lambda name: candidates[name][1]
        )
        self.global_ml = candidates[self.selected_global_model_name][0]

        print(f"\nSELECTED GLOBAL MODEL: {self.selected_global_model_name}")
        print(f"Validation RMSE: {candidates[self.selected_global_model_name][1]:.4f}")

        print("\n=== STEP 6: Independent Evaluation on TEST (2025) ===")
        test_nwp = self.baseline_model.predict(X_test)
        test_mos = self.mos_model.predict(X_test)
        test_global = self.global_ml.predict(X_test)
        test_xgb1000 = self.xgb_1000.predict(X_test)
        test_hgb = self.hist_gradient.predict(X_test)

        test_regime, pred_regimes_test, regime_probas_test = self.regime_aware_ml.predict(X_test)
        test_oracle = self.oracle_model.predict(X_test, regime_test)

        test_heavy_prob = self.heavy_rain_clf.predict_proba(X_test)
        test_very_heavy_prob = self.very_heavy_rain_clf.predict_proba(X_test)

        test_metrics_nwp = compute_continuous_metrics(test_nwp, y_test)
        raw_rmse = test_metrics_nwp["rmse"]
        raw_mae = test_metrics_nwp["mae"]

        test_metrics_mos = compute_continuous_metrics(test_mos, y_test, raw_rmse, raw_mae)
        test_metrics_global = compute_continuous_metrics(test_global, y_test, raw_rmse, raw_mae)
        test_metrics_xgb1000 = compute_continuous_metrics(test_xgb1000, y_test, raw_rmse, raw_mae)
        test_metrics_hgb = compute_continuous_metrics(test_hgb, y_test, raw_rmse, raw_mae)
        test_metrics_regime = compute_continuous_metrics(test_regime, y_test, raw_rmse, raw_mae)
        test_metrics_oracle = compute_continuous_metrics(test_oracle, y_test, raw_rmse, raw_mae)

        print("\n=== STEP 7: Classifier Evaluation ===")
        acc = float(np.mean(pred_regimes_test == regime_test))
        per_regime_clf = {}

        for r in np.unique(regime_test):
            idx_true = regime_test == r
            idx_pred = pred_regimes_test == r

            tp = np.sum(idx_true & idx_pred)
            fp = np.sum(~idx_true & idx_pred)
            fn = np.sum(idx_true & ~idx_pred)

            precision = float(tp / (tp + fp)) if (tp + fp) > 0 else 0.0
            recall = float(tp / (tp + fn)) if (tp + fn) > 0 else 0.0
            f1 = float(2 * precision * recall / (precision + recall)) if (precision + recall) > 0 else 0.0

            per_regime_clf[int(r)] = {
                "regime_name": REGIME_NAMES.get(int(r), f"Regime {r}"),
                "sample_count": int(np.sum(idx_true)),
                "precision": round(precision, 4),
                "recall": round(recall, 4),
                "f1_score": round(f1, 4),
            }

        print("\n=== STEP 8: Threshold Metrics Evaluation ===")
        threshold_results = {}
        for name, thresh in LEGACY_THRESHOLDS_24H_MM.items():
            threshold_results[name] = {
                "raw_nwp": compute_contingency_table(test_nwp, y_test, thresh),
                "global_ml": compute_contingency_table(test_global, y_test, thresh),
                "xgb_1000": compute_contingency_table(test_xgb1000, y_test, thresh),
                "hist_gradient_boosting": compute_contingency_table(test_hgb, y_test, thresh),
                "regime_aware_ml": compute_contingency_table(test_regime, y_test, thresh),
            }

        print("\n=== STEP 9: Heavy Rain Calibration Evaluation ===")
        brier_heavy = compute_brier_score(test_heavy_prob, y_test, LEGACY_THRESHOLDS_24H_MM["heavy"])
        brier_very_heavy = compute_brier_score(test_very_heavy_prob, y_test, LEGACY_THRESHOLDS_24H_MM["very_heavy"])

        print("\n=== STEP 10: Regime-by-Regime Breakdown ===")
        regime_breakdown = {}
        for r in np.unique(regime_test):
            idx_r = regime_test == r
            sub_y = y_test[idx_r]
            sub_nwp = test_nwp[idx_r]
            sub_global = test_global[idx_r]
            sub_regime = test_regime[idx_r]

            sub_raw_metrics = compute_continuous_metrics(sub_nwp, sub_y)
            sub_raw_rmse = sub_raw_metrics["rmse"]
            sub_raw_mae = sub_raw_metrics["mae"]

            regime_breakdown[int(r)] = {
                "regime_name": REGIME_NAMES.get(int(r), f"Regime {r}"),
                "sample_count": int(np.sum(idx_r)),
                "classifier_performance": per_regime_clf.get(int(r), {}),
                "raw_nwp": sub_raw_metrics,
                "global_ml": compute_continuous_metrics(sub_global, sub_y, sub_raw_rmse, sub_raw_mae),
                "regime_aware_ml": compute_continuous_metrics(sub_regime, sub_y, sub_raw_rmse, sub_raw_mae),
                "heavy_rain_csi": compute_contingency_table(sub_regime, sub_y, LEGACY_THRESHOLDS_24H_MM["heavy"])["csi"],
            }

        print("\n=== STEP 11: Feature Importance ===")
        feat_importances = compute_permutation_feature_importance(
            self.global_ml.model, X_val, y_val
        )

        print("\n=== STEP 12: Ablation Study ===")
        no_terrain_cols = [
            c for c in X_train.columns
            if c not in ["latitude", "longitude", "elevation"]
        ]

        if self.selected_global_model_name == "XGBoost_1000":
            m_no_terrain = XGBoost1000Model()
        elif self.selected_global_model_name == "HistGradientBoosting":
            m_no_terrain = HistGradientBoostingMLModel()
        else:
            raise RuntimeError(f"Unsupported selected model: {self.selected_global_model_name}")

        m_no_terrain.fit(X_train[no_terrain_cols], y_train)
        preds_no_terrain = m_no_terrain.predict(X_test[no_terrain_cols])
        metrics_no_terrain = compute_continuous_metrics(preds_no_terrain, y_test, raw_rmse, raw_mae)

        ablation_study = [
            {"experiment": "A. Raw NWP Baseline", "model_type": "NWP Direct", "rmse": test_metrics_nwp["rmse"], "mae": test_metrics_nwp["mae"], "bias": test_metrics_nwp["bias"], "r2": test_metrics_nwp["r2"], "rmse_imp_pct": 0.0},
            {"experiment": "B. Linear MOS / Statistical", "model_type": "Ridge Regression", "rmse": test_metrics_mos["rmse"], "mae": test_metrics_mos["mae"], "bias": test_metrics_mos["bias"], "r2": test_metrics_mos["r2"], "rmse_imp_pct": test_metrics_mos.get("rmse_improvement_pct", 0.0)},
            {"experiment": "C. XGBoost 1000", "model_type": "XGBoost", "rmse": test_metrics_xgb1000["rmse"], "mae": test_metrics_xgb1000["mae"], "bias": test_metrics_xgb1000["bias"], "r2": test_metrics_xgb1000["r2"], "rmse_imp_pct": test_metrics_xgb1000.get("rmse_improvement_pct", 0.0)},
            {"experiment": "E. HistGradientBoosting", "model_type": "HistGradientBoosting", "rmse": test_metrics_hgb["rmse"], "mae": test_metrics_hgb["mae"], "bias": test_metrics_hgb["bias"], "r2": test_metrics_hgb["r2"], "rmse_imp_pct": test_metrics_hgb.get("rmse_improvement_pct", 0.0)},
            {"experiment": "F. Selected Global ML", "model_type": self.selected_global_model_name, "rmse": test_metrics_global["rmse"], "mae": test_metrics_global["mae"], "bias": test_metrics_global["bias"], "r2": test_metrics_global["r2"], "rmse_imp_pct": test_metrics_global.get("rmse_improvement_pct", 0.0)},
            {"experiment": "G. Global ML Without Terrain/Geo", "model_type": self.selected_global_model_name, "rmse": metrics_no_terrain["rmse"], "mae": metrics_no_terrain["mae"], "bias": metrics_no_terrain["bias"], "r2": metrics_no_terrain["r2"], "rmse_imp_pct": metrics_no_terrain.get("rmse_improvement_pct", 0.0)},
            {"experiment": "H. Regime-Aware ML", "model_type": "Classifier + Per-Regime ML", "rmse": test_metrics_regime["rmse"], "mae": test_metrics_regime["mae"], "bias": test_metrics_regime["bias"], "r2": test_metrics_regime["r2"], "rmse_imp_pct": test_metrics_regime.get("rmse_improvement_pct", 0.0)},
            {"experiment": "I. Oracle Regime ML", "model_type": "True Regime Oracle Routing", "rmse": test_metrics_oracle["rmse"], "mae": test_metrics_oracle["mae"], "bias": test_metrics_oracle["bias"], "r2": test_metrics_oracle["r2"], "rmse_imp_pct": test_metrics_oracle.get("rmse_improvement_pct", 0.0)},
        ]

        print("\n=== STEP 13: Compiling Final Report ===")
        report = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "experiment_id": "EXP_001_GOA_2020_2025_FINAL",
            "file_metadata": self.file_metadata,
            "dataset_audit": self.audit_results,
            "split_metadata": self.splits["metadata"],
            "selected_global_model": self.selected_global_model_name,
            "validation_2024_metrics": {
                "raw_nwp": val_raw_metrics,
                "linear_mos": val_mos_metrics,
                "xgb_1000": val_xgb1000_metrics,
                "hist_gradient_boosting": val_hgb_metrics,
                "regime_aware_ml": val_regime_metrics,
            },
            "test_2025_metrics": {
                "raw_nwp": test_metrics_nwp,
                "linear_mos": test_metrics_mos,
                "xgb_1000": test_metrics_xgb1000,
                "hist_gradient_boosting": test_metrics_hgb,
                "selected_global_ml": test_metrics_global,
                "regime_aware_ml": test_metrics_regime,
                "oracle_regime_ml": test_metrics_oracle,
            },
            "regime_classifier": {
                "overall_accuracy": round(acc, 4),
                "per_regime_metrics": per_regime_clf,
            },
            "threshold_metrics": threshold_results,
            "heavy_rain_calibration": {
                "heavy_64_5mm": brier_heavy,
                "very_heavy_115_5mm": brier_very_heavy,
            },
            "regime_breakdown": regime_breakdown,
            "feature_importances": feat_importances[:15],
            "ablation_study": ablation_study,
            "experiment_metadata": self._experiment_metadata(X_train),
        }

        self.final_report = report

        with open(REPORTS_DIR / "final_test_report.json", "w") as f:
            json.dump(report, f, indent=2)

        pd.DataFrame(ablation_study).to_csv(REPORTS_DIR / "final_test_report.csv", index=False)

        joblib.dump(self.mos_model, MODELS_DIR / "mos_model.pkl")
        joblib.dump(self.global_ml, MODELS_DIR / "global_ml.pkl")
        joblib.dump(self.xgb_1000, MODELS_DIR / "xgb_1000.pkl")
        joblib.dump(self.hist_gradient, MODELS_DIR / "hist_gradient_boosting.pkl")
        joblib.dump(self.regime_classifier, MODELS_DIR / "regime_classifier.pkl")
        joblib.dump(self.regime_aware_ml, MODELS_DIR / "regime_aware_ml.pkl")
        joblib.dump(self.heavy_rain_clf, MODELS_DIR / "heavy_rain_clf.pkl")
        joblib.dump(self.very_heavy_rain_clf, MODELS_DIR / "very_heavy_rain_clf.pkl")

        print("\n==============================================")
        print("PIPELINE EXECUTION COMPLETE")
        print("TRAIN      : 2020-2023")
        print("VALIDATION : 2024")
        print("TEST       : 2025")
        print(f"SELECTED GLOBAL MODEL : {self.selected_global_model_name}")
        print("==============================================\n")

        return report

    def _experiment_metadata(self, X_train: pd.DataFrame) -> dict:
        package_versions = {}
        for package in ("numpy", "pandas", "scikit-learn", "scipy", "xgboost"):
            try:
                package_versions[package] = version(package)
            except PackageNotFoundError:
                package_versions[package] = "not-installed"

        try:
            git_commit = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=str(REPORTS_DIR.parent.parent),
                capture_output=True,
                text=True,
                check=True,
            ).stdout.strip()
        except (OSError, subprocess.CalledProcessError):
            git_commit = "unavailable:not-a-git-checkout"

        return {
            "git_commit": git_commit,
            "data_hashes": {self.file_metadata["filename"]: self.file_metadata["sha256"]},
            "dataset_id": self.file_metadata["dataset_id"],
            "split": self.splits["metadata"],
            "model_hyperparameters": {
                "linear_mos": self.mos_model.model.get_params(),
                "xgboost_1000": self.xgb_1000.model.get_params(),
                "hist_gradient_boosting": self.hist_gradient.model.get_params(),
            },
            "feature_list": list(X_train.columns),
            "feature_registry": {name: FEATURE_REGISTRY[name] for name in X_train.columns},
            "thresholds": {
                "status": "blocked_accumulation_mismatch",
                "legacy_24h_mm": LEGACY_THRESHOLDS_24H_MM,
            },
            "target_accumulation_hours": TARGET_ACCUMULATION_HOURS,
            "random_seed": RANDOM_SEED,
            "package_versions": package_versions,
        }

    def get_forecast_for_record(self, station_id: int, date_str: str, time_str: str = None) -> dict:
        self.ensure_loaded()
        if not self.readiness or not self.readiness.ready or self.regime_aware_ml is None:
            blockers = self.readiness.blockers if self.readiness else ["Pipeline readiness is unknown."]
            raise ScientificReadinessError(blockers)

        df_sub = self.df[(self.df["location_id"] == station_id) & (self.df["date"] == date_str)]
        if len(df_sub) == 0:
            return {
                "error": f"No matching historical record for station {station_id} on {date_str}"
            }

        available_times = list(df_sub["time"].unique())
        if time_str is not None:
            if time_str not in available_times:
                return {
                    "error": f"No matching historical record at time {time_str}",
                    "available_times": available_times,
                }
            df_target = df_sub[df_sub["time"] == time_str]
        else:
            df_target = df_sub.iloc[0:1]

        row = df_target.iloc[0:1]
        X_row, _ = prepare_features(row)

        raw_nwp = float(row[NWP_COLUMN].values[0])
        obs_rain = float(row[TARGET_COLUMN].values[0]) if TARGET_COLUMN in row.columns else None

        ai_pred, pred_regime, probas = self.regime_aware_ml.predict(X_row)
        heavy_prob = float(self.heavy_rain_clf.predict_proba(X_row)[0])
        very_heavy_prob = float(self.very_heavy_rain_clf.predict_proba(X_row)[0])

        ai_val = float(ai_pred[0])
        err_nwp = abs(raw_nwp - obs_rain) if obs_rain is not None else None
        err_ai = abs(ai_val - obs_rain) if obs_rain is not None else None
        pred_regime_id = int(pred_regime[0])

        return {
            "station_id": int(row["location_id"].values[0]),
            "district_name": str(row["district_name"].values[0]),
            "taluka_name": str(row["taluka_name"].values[0]),
            "latitude": float(row["latitude"].values[0]),
            "longitude": float(row["longitude"].values[0]),
            "elevation_m": int(row["elevation (m)"].values[0]),
            "date": str(row["date"].values[0]),
            "time": str(row["time"].values[0]),
            "available_times": available_times,
            "raw_nwp_forecast_mm": round(raw_nwp, 2),
            "ai_corrected_forecast_mm": round(ai_val, 2),
            "observed_rain_mm": round(obs_rain, 2) if obs_rain is not None else None,
            "raw_nwp_abs_error": round(err_nwp, 2) if err_nwp is not None else None,
            "ai_abs_error": round(err_ai, 2) if err_ai is not None else None,
            "predicted_regime_id": pred_regime_id,
            "predicted_regime_name": REGIME_NAMES.get(pred_regime_id, f"Regime {pred_regime_id}"),
            "regime_probabilities": [round(float(p), 4) for p in probas[0]],
            "heavy_rain_probability": round(heavy_prob, 4),
            "very_heavy_rain_probability": round(very_heavy_prob, 4),
        }
