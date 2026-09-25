import joblib
import numpy as np
import pandas as pd
from pathlib import Path

from sklearn.linear_model import Ridge, LogisticRegression
from sklearn.ensemble import (
    HistGradientBoostingRegressor,
    HistGradientBoostingClassifier,
    RandomForestClassifier
)
from sklearn.calibration import CalibratedClassifierCV
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline

from xgboost import XGBRegressor

try:
    from backend.app.core.config import (
        TARGET_COLUMN,
        MODELS_DIR,
        RANDOM_SEED,
    )
except ModuleNotFoundError:
    from app.core.config import (
        TARGET_COLUMN,
        MODELS_DIR,
        RANDOM_SEED,
    )

# 5 Conceptual Synoptic Weather Regimes
REGIMES_5 = [
    "Active Monsoon",
    "Break Monsoon",
    "Monsoon Low/Depression",
    "Coastal/Orographic",
    "Transitional/Western Disturbance"
]

def calculate_physics_regime_scores(row) -> dict:
    """
    Physics-Informed Meteorological Scoring Engine for Western Ghats / Indian Monsoon.
    Uses real synoptic atmospheric variables (pressure, wind, humidity, TPW, elevation, location, month).
    """
    scores = {r: 0.0 for r in REGIMES_5}
    
    # Extract atmospheric parameters
    pressure = float(row.get("pressure_msl (hPa)", row.get("pressure_msl", row.get("raw_nwp_pressure_msl_forecast (hPa)", 1010.0))))
    wind = float(row.get("wind_speed_10m (km/h)", row.get("wind_speed_10m", row.get("raw_nwp_wind_speed_forecast (km/h)", 10.0))))
    elevation = float(row.get("elevation (m)", row.get("elevation", 10.0)))
    rh = float(row.get("relative_humidity_2m (%)", row.get("relative_humidity", 80.0)))
    tpw = float(row.get("total_column_integrated_water_vapour (kg/m?)", row.get("tcwv", 50.0)))
    month = int(row.get("month", 7))
    longitude = float(row.get("longitude", 73.8))
    
    monsoon = month in [6, 7, 8, 9]

    # 1. MONSOON LOW / DEPRESSION
    scores["Monsoon Low/Depression"] += max(0, 1007 - pressure) * 1.8
    scores["Monsoon Low/Depression"] += max(0, wind - 18) * 0.35
    scores["Monsoon Low/Depression"] += max(0, rh - 90) * 0.08
    scores["Monsoon Low/Depression"] += max(0, tpw - 65) * 0.08
    if monsoon:
        scores["Monsoon Low/Depression"] += 1.0

    # 2. ACTIVE MONSOON
    scores["Active Monsoon"] += max(0, 1011 - pressure) * 0.75
    scores["Active Monsoon"] += max(0, wind - 10) * 0.32
    scores["Active Monsoon"] += max(0, tpw - 55) * 0.10
    scores["Active Monsoon"] += max(0, rh - 82) * 0.04
    if monsoon:
        scores["Active Monsoon"] += 1.5

    # 3. BREAK MONSOON
    scores["Break Monsoon"] += max(0, pressure - 1009) * 0.95
    scores["Break Monsoon"] += max(0, 14 - wind) * 0.28
    scores["Break Monsoon"] += max(0, 78 - rh) * 0.05
    scores["Break Monsoon"] += max(0, 55 - tpw) * 0.06
    if not monsoon:
        scores["Break Monsoon"] += 1.0

    # 4. COASTAL / OROGRAPHIC
    scores["Coastal/Orographic"] += max(0, 74.5 - longitude) * 1.7
    scores["Coastal/Orographic"] += max(0, 55 - elevation) * 0.015
    scores["Coastal/Orographic"] += max(0, wind - 10) * 0.22
    scores["Coastal/Orographic"] += max(0, rh - 82) * 0.025

    # 5. TRANSITIONAL / WESTERN DISTURBANCE
    if month in [5, 10, 11]:
        scores["Transitional/Western Disturbance"] += 4.0
    scores["Transitional/Western Disturbance"] += max(0, pressure - 1007) * 0.18
    scores["Transitional/Western Disturbance"] += max(0, 18 - wind) * 0.08
    scores["Transitional/Western Disturbance"] += max(0, 65 - rh) * 0.04
    scores["Transitional/Western Disturbance"] += max(0, 55 - tpw) * 0.04

    # SYNOPTIC LOW OVERRIDE
    if pressure <= 1005 and wind >= 18:
        scores["Monsoon Low/Depression"] += 4.0
        scores["Coastal/Orographic"] *= 0.55
        scores["Transitional/Western Disturbance"] *= 0.35

    # OROGRAPHIC BOOST
    if elevation >= 100:
        scores["Coastal/Orographic"] += 3.5
    if elevation >= 250:
        scores["Coastal/Orographic"] += 2.0

    # NON-MONSOON BREAK-LIKE CONDITIONS
    if not monsoon and pressure > 1010 and wind < 10:
        scores["Break Monsoon"] += 2.0

    return scores

def compute_physics_softmax_probabilities(row) -> tuple[str, float, dict]:
    """Return unvalidated normalized heuristic scores for offline diagnostics.

    These values are not calibrated probabilities or confidence and must not be
    exposed by scientific APIs without independent validation.
    """
    scores = calculate_physics_regime_scores(row)
    values = np.array([max(0, scores[r]) for r in REGIMES_5])
    max_score = np.max(values)
    exp_scores = np.exp(values - max_score)
    probabilities = exp_scores / np.sum(exp_scores)
    best_index = np.argmax(probabilities)
    
    pred_regime = REGIMES_5[best_index]
    confidence = float(probabilities[best_index])
    proba_dict = {r: float(probabilities[i]) for i, r in enumerate(REGIMES_5)}
    
    return pred_regime, confidence, proba_dict

# ============================================================
# MODEL 1: RAW NWP BASELINE
# ============================================================

class BaselineNWPModel:
    """Model 1: Raw NWP Baseline."""

    def predict(self, X_df: pd.DataFrame) -> np.ndarray:
        if isinstance(X_df, pd.DataFrame) and "nwp_rain" in X_df.columns:
            vals = X_df["nwp_rain"].values
        elif isinstance(X_df, pd.DataFrame):
            vals = X_df.iloc[:, 0].values
        else:
            vals = np.asarray(X_df)[:, 0]
        return np.maximum(0.0, vals)

# ============================================================
# MODEL 2: LINEAR MOS
# ============================================================

class LinearMOSModel:
    """Model 2: Statistical Model Output Statistics."""

    def __init__(self):
        self.scaler = StandardScaler()
        self.model = Ridge(
            alpha=1.0,
            random_state=RANDOM_SEED
        )

    def fit(self, X_df: pd.DataFrame, y: np.ndarray):
        X_vals = X_df.values if isinstance(X_df, pd.DataFrame) else np.asarray(X_df)
        X_scaled = self.scaler.fit_transform(X_vals)
        self.model.fit(X_scaled, y)
        return self

    def predict(self, X_df: pd.DataFrame) -> np.ndarray:
        X_vals = X_df.values if isinstance(X_df, pd.DataFrame) else np.asarray(X_df)
        X_scaled = self.scaler.transform(X_vals)
        preds = self.model.predict(X_scaled)
        return np.maximum(0.0, preds)

# ============================================================
# MODEL 3: GLOBAL XGBOOST
# ============================================================

class GlobalMLModel:
    """Model 3: Global XGBoost rainfall bias-correction model."""

    def __init__(self):
        self.model = XGBRegressor(
            n_estimators=1000,
            learning_rate=0.1,
            max_depth=6,
            min_child_weight=2,
            subsample=0.85,
            colsample_bytree=0.90,
            objective="reg:squarederror",
            reg_alpha=0.0,
            reg_lambda=1.0,
            random_state=RANDOM_SEED,
            n_jobs=-1,
            tree_method="hist"
        )

    def fit(self, X_df: pd.DataFrame, y: np.ndarray):
        X_vals = X_df.values if isinstance(X_df, pd.DataFrame) else np.asarray(X_df)
        self.model.fit(X_vals, y)
        return self

    def predict(self, X_df: pd.DataFrame) -> np.ndarray:
        X_vals = X_df.values if isinstance(X_df, pd.DataFrame) else np.asarray(X_df)
        preds = self.model.predict(X_vals)
        return np.maximum(0.0, preds)

# ============================================================
# MODEL 3B: HISTOGRAM GRADIENT BOOSTING
# ============================================================

class HistGradientBoostingMLModel:
    """Additional global model: HistGradientBoostingRegressor."""

    def __init__(self):
        self.model = HistGradientBoostingRegressor(
            max_iter=1000,
            learning_rate=0.1,
            max_leaf_nodes=31,
            min_samples_leaf=20,
            l2_regularization=0.1,
            random_state=RANDOM_SEED
        )

    def fit(self, X_df: pd.DataFrame, y: np.ndarray):
        X_vals = X_df.values if isinstance(X_df, pd.DataFrame) else np.asarray(X_df)
        self.model.fit(X_vals, y)
        return self

    def predict(self, X_df: pd.DataFrame) -> np.ndarray:
        X_vals = X_df.values if isinstance(X_df, pd.DataFrame) else np.asarray(X_df)
        preds = self.model.predict(X_vals)
        return np.maximum(0.0, preds)

# ============================================================
# MODEL 3C: XGBOOST 1000 TREE VARIANT
# ============================================================

class XGBoost1000Model:
    """XGBoost 1000-tree variant."""

    def __init__(self):
        self.model = XGBRegressor(
            n_estimators=1000,
            learning_rate=0.1,
            max_depth=6,
            min_child_weight=2,
            subsample=0.85,
            colsample_bytree=0.90,
            objective="reg:squarederror",
            reg_alpha=0.0,
            reg_lambda=1.0,
            random_state=RANDOM_SEED,
            n_jobs=-1,
            tree_method="hist"
        )

    def fit(self, X_df: pd.DataFrame, y: np.ndarray):
        X_vals = X_df.values if isinstance(X_df, pd.DataFrame) else np.asarray(X_df)
        self.model.fit(X_vals, y)
        return self

    def predict(self, X_df: pd.DataFrame) -> np.ndarray:
        X_vals = X_df.values if isinstance(X_df, pd.DataFrame) else np.asarray(X_df)
        preds = self.model.predict(X_vals)
        return np.maximum(0.0, preds)

# ============================================================
# REGIME CLASSIFIER
# ============================================================

class RegimeClassifier:
    """
    Weather Regime Classifier with sigmoid probability calibration.

    Statistical reliability has not been established for the legacy artifact,
    and current training is blocked until regime labels are reproducible.
    """

    def __init__(self):
        base_hgb = HistGradientBoostingClassifier(
            max_iter=150,
            learning_rate=0.08,
            random_state=RANDOM_SEED
        )
        self.classifier = CalibratedClassifierCV(
            estimator=base_hgb,
            cv=3,
            method="sigmoid"
        )

    def fit(self, X_df: pd.DataFrame, y_regime: np.ndarray):
        X_vals = X_df.values if isinstance(X_df, pd.DataFrame) else np.asarray(X_df)
        self.classifier.fit(X_vals, y_regime)
        return self

    def predict(self, X_df: pd.DataFrame) -> np.ndarray:
        X_vals = X_df.values if isinstance(X_df, pd.DataFrame) else np.asarray(X_df)
        return self.classifier.predict(X_vals)

    def predict_proba(self, X_df: pd.DataFrame) -> np.ndarray:
        X_vals = X_df.values if isinstance(X_df, pd.DataFrame) else np.asarray(X_df)
        return self.classifier.predict_proba(X_vals)

# ============================================================
# MODEL 4: REGIME-AWARE ML
# ============================================================

class RegimeAwareMLModel:
    """
    Model 4: Regime-Aware ML Model.
    Each predicted weather regime gets its own HistGradientBoosting rainfall model.
    """

    def __init__(self, classifier: RegimeClassifier):
        self.classifier = classifier
        self.regime_models = {}

    def fit(self, X_df: pd.DataFrame, y: np.ndarray, regime_ids: np.ndarray):
        unique_regimes = np.unique(regime_ids)
        X_vals = X_df.values if isinstance(X_df, pd.DataFrame) else np.asarray(X_df)

        for r in unique_regimes:
            idx = (regime_ids == r)
            if np.sum(idx) >= 30:
                m = HistGradientBoostingRegressor(
                    max_iter=100,
                    learning_rate=0.1,
                    max_leaf_nodes=31,
                    random_state=RANDOM_SEED
                )
                m.fit(X_vals[idx], y[idx])
                self.regime_models[r] = m
            else:
                self.regime_models[r] = None
        return self

    def predict(self, X_df: pd.DataFrame) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        pred_regimes = self.classifier.predict(X_df)
        probas = self.classifier.predict_proba(X_df)

        X_vals = X_df.values if isinstance(X_df, pd.DataFrame) else np.asarray(X_df)
        nwp_vals = X_df["nwp_rain"].values if isinstance(X_df, pd.DataFrame) and "nwp_rain" in X_df.columns else X_vals[:, 0]

        preds = np.zeros(len(X_vals))

        for r, model in self.regime_models.items():
            idx = (pred_regimes == r)
            if np.any(idx):
                if model is not None:
                    preds[idx] = model.predict(X_vals[idx])
                else:
                    preds[idx] = nwp_vals[idx]

        return np.maximum(0.0, preds), pred_regimes, probas

# ============================================================
# ORACLE REGIME MODEL
# ============================================================

class OracleRegimeMLModel:
    """Diagnostic upper-bound model using TRUE regime labels."""

    def __init__(self, regime_aware_model: RegimeAwareMLModel):
        self.regime_models = regime_aware_model.regime_models

    def predict(self, X_df: pd.DataFrame, true_regimes: np.ndarray) -> np.ndarray:
        X_vals = X_df.values if isinstance(X_df, pd.DataFrame) else np.asarray(X_df)
        nwp_vals = X_df["nwp_rain"].values if isinstance(X_df, pd.DataFrame) and "nwp_rain" in X_df.columns else X_vals[:, 0]

        preds = np.zeros(len(X_vals))

        for r, model in self.regime_models.items():
            idx = (true_regimes == r)
            if np.any(idx):
                if model is not None:
                    preds[idx] = model.predict(X_vals[idx])
                else:
                    preds[idx] = nwp_vals[idx]

        return np.maximum(0.0, preds)

# ============================================================
# HEAVY RAIN PROBABILITY MODEL
# ============================================================

class HeavyRainProbabilityModel:
    """Probability classifier with sigmoid fitting; reliability needs evaluation."""

    def __init__(self, threshold: float):
        self.threshold = threshold
        self.scaler = StandardScaler()
        base_clf = LogisticRegression(
            max_iter=200,
            random_state=RANDOM_SEED,
            solver="lbfgs"
        )
        self.calibrated_clf = CalibratedClassifierCV(
            estimator=base_clf,
            cv=3,
            method="sigmoid"
        )

    def fit(self, X_df: pd.DataFrame, y_obs: np.ndarray):
        X_vals = X_df.values if isinstance(X_df, pd.DataFrame) else np.asarray(X_df)
        X_scaled = self.scaler.fit_transform(X_vals)
        y_binary = (y_obs >= self.threshold).astype(int)

        if len(np.unique(y_binary)) > 1:
            self.calibrated_clf.fit(X_scaled, y_binary)
        return self

    def predict_proba(self, X_df: pd.DataFrame) -> np.ndarray:
        X_vals = X_df.values if isinstance(X_df, pd.DataFrame) else np.asarray(X_df)
        X_scaled = self.scaler.transform(X_vals)

        if hasattr(self.calibrated_clf, "classes_") and len(self.calibrated_clf.classes_) > 1:
            probas = self.calibrated_clf.predict_proba(X_scaled)
            idx_1 = np.where(self.calibrated_clf.classes_ == 1)[0]
            if len(idx_1) > 0:
                return probas[:, idx_1[0]]

        return np.zeros(len(X_vals))
