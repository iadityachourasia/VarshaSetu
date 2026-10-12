"""Forecast-only multi-label regime vectors and soft residual correction.

This is an experimental Track A method. A detected regime may overlap another;
scores are never softmaxed into mutually exclusive weather classes. Fitting is
performed only by an explicitly versioned development protocol.
"""

from __future__ import annotations

import numpy as np
from sklearn.linear_model import Ridge

from backend.app.ml import regime_tasks

TASKS = regime_tasks.TASKS
MIN_LABEL_CASES = 30
MIN_WEIGHTED_CASES = 30.0
SHRINKAGE_CASES = 30.0
RIDGE_ALPHA = 100.0


def fit_detectors(features: np.ndarray, labels: np.ndarray) -> dict:
    """Fit five independent logistic heads on training years only."""
    X, Y = np.asarray(features, dtype=np.float64), np.asarray(labels)
    if X.ndim != 2 or Y.shape != (len(X), len(TASKS)) or not np.isfinite(X).all():
        raise ValueError("invalid regime detector training arrays")
    heads = {}
    for j, name in enumerate(TASKS):
        eligible = Y[:, j] >= 0
        target = Y[eligible, j]
        positives = int(np.count_nonzero(target == 1))
        negatives = int(np.count_nonzero(target == 0))
        if positives < MIN_LABEL_CASES or negatives < MIN_LABEL_CASES:
            raise ValueError(f"{name}: insufficient observed labels for a detector")
        fitted = regime_tasks.fit_logistic(X[eligible], target, C=1.0)
        heads[name] = {k: (v.tolist() if hasattr(v, "tolist") else v) for k, v in fitted.items()}
        heads[name]["training_positive_cases"] = positives
        heads[name]["training_negative_cases"] = negatives
    return {"tasks": list(TASKS), "heads": heads, "calibration_status": "UNCALIBRATED_LOGISTIC_OUTPUT", "label_source": "objective retrospective labels"}


def score_detectors(bundle: dict, features: np.ndarray) -> np.ndarray:
    X = np.asarray(features, dtype=np.float64)
    if bundle.get("tasks") != list(TASKS) or X.ndim != 2 or not np.isfinite(X).all():
        raise ValueError("regime detector identity or forecast feature matrix is invalid")
    scores = np.column_stack([regime_tasks.score_logistic(bundle["heads"][name], X) for name in TASKS])
    if not np.isfinite(scores).all() or np.any((scores < 0) | (scores > 1)):
        raise ValueError("regime detector scores left [0, 1]")
    return scores


def residual_features(base: np.ndarray, forecast: np.ndarray) -> np.ndarray:
    """Identical inputs for global and specialist residual fits."""
    base, forecast = np.asarray(base, dtype=np.float64).reshape(-1), np.asarray(forecast, dtype=np.float64)
    if forecast.ndim != 2 or forecast.shape[0] != len(base) or forecast.shape[1] != 22:
        raise ValueError("residual input shapes disagree")
    # The X registry fixes these column names. No observation or reanalysis enters.
    from backend.app.ml.phase2b import FEATURE_NAMES
    indices = [FEATURE_NAMES.index(name) for name in ("latitude_deg", "longitude_deg", "lead_hours")]
    out = np.column_stack([base, forecast[:, 0], forecast[:, indices]])
    if not np.isfinite(out).all():
        raise ValueError("residual predictors are not finite")
    return out


def _fit_ridge(X: np.ndarray, target: np.ndarray, weights: np.ndarray | None = None) -> dict:
    model = Ridge(alpha=RIDGE_ALPHA, solver="cholesky")
    model.fit(X, target, sample_weight=weights)
    return {"coef": np.asarray(model.coef_, dtype=float).tolist(), "intercept": float(model.intercept_)}


def _predict_ridge(model: dict, X: np.ndarray) -> np.ndarray:
    return X @ np.asarray(model["coef"], dtype=np.float64) + model["intercept"]


def fit_correction(base: np.ndarray, forecast: np.ndarray, observed: np.ndarray, case_scores: np.ndarray, rows_per_case: np.ndarray) -> dict:
    """Fit global and five probability-weighted residual models on the same rows."""
    X = residual_features(base, forecast)
    y = np.asarray(observed, dtype=np.float64).reshape(-1)
    scores = np.asarray(case_scores, dtype=np.float64)
    counts = np.asarray(rows_per_case, dtype=np.int64)
    if len(y) != len(X) or len(counts) != len(scores) or scores.shape[1] != len(TASKS) or counts.sum() != len(y) or np.any(counts <= 0):
        raise ValueError("residual rows and regime cases are not aligned")
    if not np.isfinite(y).all() or np.any(y < 0) or not np.isfinite(scores).all() or np.any((scores < 0) | (scores > 1)):
        raise ValueError("invalid residual targets or regime scores")
    mean, scale = X.mean(axis=0), X.std(axis=0)
    scale[scale == 0] = 1.0
    Z = (X - mean) / scale
    residual = y - np.asarray(base, dtype=np.float64)
    global_model = _fit_ridge(Z, residual)
    specialists = {}
    for j, name in enumerate(TASKS):
        p = scores[:, j]
        mass = float(p.sum())
        effective = float(mass * mass / np.square(p).sum()) if np.square(p).sum() else 0.0
        if mass < MIN_WEIGHTED_CASES or effective < MIN_WEIGHTED_CASES:
            specialists[name] = {"status": "FALLBACK_GLOBAL_INSUFFICIENT_CASES", "weighted_case_mass": mass, "effective_cases": effective, "shrinkage": 0.0}
            continue
        weights = np.repeat(p, counts)
        specialist = _fit_ridge(Z, residual, weights)
        specialists[name] = {"status": "FITTED", "weighted_case_mass": mass, "effective_cases": effective,
                             "shrinkage": effective / (effective + SHRINKAGE_CASES), "model": specialist}
    return {"feature_names": ["base_corrected_mm", "raw_forecast_mm", "latitude_deg", "longitude_deg", "lead_hours"],
            "mean": mean.tolist(), "scale": scale.tolist(), "global": global_model, "specialists": specialists,
            "method": "probability-weighted residual ridge; effective-case shrinkage; overlapping regimes"}


def predict_correction(bundle: dict, base: np.ndarray, forecast: np.ndarray, case_scores: np.ndarray, rows_per_case: np.ndarray) -> dict[str, np.ndarray]:
    X = residual_features(base, forecast)
    counts = np.asarray(rows_per_case, dtype=np.int64)
    scores = np.asarray(case_scores, dtype=np.float64)
    if scores.shape != (len(counts), len(TASKS)) or counts.sum() != len(X) or not np.isfinite(scores).all():
        raise ValueError("prediction case scores do not align with forecast rows")
    Z = (X - np.asarray(bundle["mean"])) / np.asarray(bundle["scale"])
    global_residual = _predict_ridge(bundle["global"], Z)
    adjustment = np.zeros(len(X), dtype=np.float64)
    mass = np.zeros(len(X), dtype=np.float64)
    for j, name in enumerate(TASKS):
        specialist = bundle["specialists"][name]
        if specialist["status"] != "FITTED":
            continue
        weight = np.repeat(scores[:, j] * specialist["shrinkage"], counts)
        adjustment += weight * (_predict_ridge(specialist["model"], Z) - global_residual)
        mass += weight
    # Keep one unit of global support so small or uncertain regime scores have
    # proportionally small influence instead of becoming a hard expert switch.
    soft_residual = global_residual + adjustment / (1.0 + mass)
    baseline = np.maximum(0.0, np.asarray(base, dtype=np.float64) + global_residual).astype(np.float32)
    soft = np.maximum(0.0, np.asarray(base, dtype=np.float64) + soft_residual).astype(np.float32)
    return {"global_residual": baseline, "regime_soft_residual": soft}
