"""Versioned, forecast-time lead-aware recalibration for research diagnostics."""

from __future__ import annotations

import numpy as np
from sklearn.linear_model import LogisticRegression

CLIP = 1e-6


def design_matrix(base_probability: np.ndarray, lead_day: np.ndarray, *, lead_aware: bool) -> np.ndarray:
    probability = np.asarray(base_probability, dtype=np.float64)
    lead = np.asarray(lead_day, dtype=np.int8)
    if (probability.ndim != 1 or lead.shape != probability.shape or not np.isfinite(probability).all()
            or np.any((probability < 0) | (probability > 1)) or np.any(~np.isin(lead, [1, 2, 3]))):
        raise ValueError("base probabilities and forecast leads are invalid")
    clipped = np.clip(probability, CLIP, 1 - CLIP)
    logit = np.log(clipped / (1 - clipped))
    if not lead_aware:
        return logit[:, None]
    return np.column_stack((logit, (lead == 2).astype(float), (lead == 3).astype(float)))


def fit_recalibrator(base_probability: np.ndarray, lead_day: np.ndarray, target: np.ndarray,
                     *, lead_aware: bool) -> dict:
    y = np.asarray(target, dtype=np.uint8)
    X = design_matrix(base_probability, lead_day, lead_aware=lead_aware)
    if y.shape != (len(X),) or set(np.unique(y)) != {0, 1}:
        raise ValueError("calibration requires aligned binary labels with both classes")
    model = LogisticRegression(C=0.1, solver="lbfgs", max_iter=500,
                               random_state=26080).fit(X, y)
    if not model.n_iter_[0] < 500:
        raise RuntimeError("lead-aware calibrator did not converge")
    return {"format": "varshasetu-lead-aware-logistic-calibrator-v1",
            "lead_aware": lead_aware, "base_score_clip": CLIP, "C": 0.1,
            "feature_names": ["base_logit"] + (["day2_offset", "day3_offset"] if lead_aware else []),
            "coefficient": model.coef_[0].tolist(), "intercept": float(model.intercept_[0]),
            "fit_rows": int(len(y)), "fit_events": int(y.sum()),
            "solver": "lbfgs", "max_iter": 500, "iterations": int(model.n_iter_[0])}


def apply_recalibrator(base_probability: np.ndarray, lead_day: np.ndarray, artifact: dict) -> np.ndarray:
    if (artifact.get("format") != "varshasetu-lead-aware-logistic-calibrator-v1"
            or artifact.get("C") != 0.1 or artifact.get("base_score_clip") != CLIP):
        raise ValueError("unknown lead-aware calibrator artifact")
    X = design_matrix(base_probability, lead_day, lead_aware=artifact["lead_aware"])
    coefficient = np.asarray(artifact["coefficient"], dtype=np.float64)
    if coefficient.shape != (X.shape[1],):
        raise ValueError("calibrator coefficient dimension differs")
    z = X @ coefficient + float(artifact["intercept"])
    output = np.exp(-np.logaddexp(0, -z))
    if not np.isfinite(output).all() or np.any((output < 0) | (output > 1)):
        raise ValueError("recalibration left probability range")
    return output
