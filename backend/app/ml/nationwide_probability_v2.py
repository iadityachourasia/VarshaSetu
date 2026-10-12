"""Pure guards for the separate, forecast-only nationwide probability study."""

from __future__ import annotations

import numpy as np


def case_indices(case_slices: dict[str, slice], case_ids: list[str]) -> np.ndarray:
    if not case_ids or len(case_ids) != len(set(case_ids)):
        raise ValueError("fold cases are empty or duplicated")
    if any(case_id not in case_slices for case_id in case_ids):
        raise ValueError("fold contains unknown case")
    return np.concatenate([np.arange(case_slices[case_id].start, case_slices[case_id].stop) for case_id in case_ids])


def validate_head_folds(folds: list[dict], case_ids: list[str]) -> None:
    """Reject head folds that overlap held cases or omit any case."""
    if sorted(case_id for fold in folds for case_id in fold["held"]) != sorted(case_ids):
        raise ValueError("held cases must partition the fit population")
    for fold in folds:
        if set(fold["train"]) & set(fold["held"]):
            raise ValueError("head training contains held cases")
        if not fold["train"] or not fold["held"]:
            raise ValueError("head fold is empty")


def apply_lead_calibration(raw: np.ndarray, leads: np.ndarray, calibrators: dict) -> np.ndarray:
    raw = np.asarray(raw, dtype=np.float64)
    leads = np.asarray(leads)
    if raw.shape != leads.shape or not np.isfinite(raw).all() or np.any((raw < 0) | (raw > 1)):
        raise ValueError("invalid uncalibrated probability")
    result = np.empty_like(raw)
    for lead in np.unique(leads):
        cal = calibrators[str(int(lead))]
        selected = leads == lead
        result[selected] = (np.interp(raw[selected], cal["x"], cal["y"])
                            if cal["method"] == "isotonic" else raw[selected])
    if not np.isfinite(result).all() or np.any((result < 0) | (result > 1)):
        raise ValueError("invalid calibrated probability")
    return result


def frequency_cutoff(calibrated: np.ndarray, target: np.ndarray) -> float:
    """Select on the same calibrated/coherent scale used for display."""
    calibrated = np.asarray(calibrated, dtype=np.float64)
    target = np.asarray(target)
    if (calibrated.shape != target.shape or calibrated.ndim != 1 or not np.isfinite(calibrated).all()
            or np.any((calibrated < 0) | (calibrated > 1)) or not np.isin(target, [0, 1]).all()
            or not 0 < int(target.sum()) < len(target)):
        raise ValueError("invalid threshold selection population")
    candidates = np.arange(0.01, 0.501, 0.01)
    events = int(target.sum())
    return float(min(candidates, key=lambda t: (abs(np.count_nonzero(calibrated >= t) / events - 1), t)))
