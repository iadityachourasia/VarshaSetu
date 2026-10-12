"""Pure calibration and fold guards for a development-only nonlinear head."""

from __future__ import annotations

from datetime import date

import numpy as np
from scipy.special import expit, logit


def validate_nested_folds(case_ids: list[str], outer: list[dict], inner_by_outer: dict[str, list[dict]],
                          *, embargo_days: int) -> None:
    """Every held case has a disjoint, embargoed training path at both levels."""
    if not case_ids or len(case_ids) != len(set(case_ids)) or embargo_days < 1:
        raise ValueError("invalid nested fold population or embargo")
    if set(inner_by_outer) != {str(fold["fold"]) for fold in outer}:
        raise ValueError("every outer fold needs inner folds")

    def verify(population: list[str], folds: list[dict]) -> None:
        if sorted(c for fold in folds for c in fold["held"]) != sorted(population):
            raise ValueError("held cases do not partition the population")
        for fold in folds:
            if (not fold["train"] or not fold["held"] or
                    set(fold["train"]) & set(fold["held"]) or
                    not set(fold["train"]).issubset(population)):
                raise ValueError("nested fold overlap or empty block")
            held_dates = {date.fromisoformat(c[:4] + "-" + c[4:6] + "-" + c[6:8]) for c in fold["held"]}
            for case in fold["train"]:
                training_date = date.fromisoformat(case[:4] + "-" + case[4:6] + "-" + case[6:8])
                if min(abs((training_date - held).days) for held in held_dates) <= embargo_days:
                    raise ValueError("nested fold embargo violated")

    verify(case_ids, outer)
    for fold in outer:
        verify(fold["train"], inner_by_outer[str(fold["fold"])])


def fit_platt(raw: np.ndarray, target: np.ndarray, leads: np.ndarray) -> dict:
    """Natural-frequency, monotone lead-specific Platt map on head OOF scores."""
    from sklearn.linear_model import LogisticRegression

    raw = np.asarray(raw, dtype=np.float64)
    target = np.asarray(target, dtype=np.uint8)
    leads = np.asarray(leads)
    if (raw.ndim != 1 or raw.shape != target.shape or raw.shape != leads.shape or
            not np.isfinite(raw).all() or np.any((raw < 0) | (raw > 1)) or
            not np.isin(target, (0, 1)).all() or set(np.unique(leads)) != {24, 48, 72}):
        raise ValueError("invalid Platt calibration population")
    result = {}
    scores = logit(np.clip(raw, 1e-6, 1 - 1e-6))
    for lead in (24, 48, 72):
        selected = leads == lead
        events = int(target[selected].sum())
        count = int(selected.sum())
        if events < 30 or count - events < 30:
            raise ValueError(f"insufficient calibration events at lead {lead}")
        model = LogisticRegression(C=1.0, max_iter=1000, random_state=26080)
        model.fit(scores[selected, None], target[selected])
        slope = float(model.coef_[0, 0])
        if not np.isfinite(slope) or slope <= 0:
            raise ValueError(f"nonmonotone Platt slope at lead {lead}")
        result[str(lead)] = {"slope": slope, "intercept": float(model.intercept_[0]),
                             "events": events, "cells": count}
    return result


def apply_platt(raw: np.ndarray, leads: np.ndarray, calibration: dict) -> np.ndarray:
    raw = np.asarray(raw, dtype=np.float64)
    leads = np.asarray(leads)
    if (raw.ndim != 1 or raw.shape != leads.shape or not np.isfinite(raw).all() or
            np.any((raw < 0) | (raw > 1)) or set(np.unique(leads)) - {24, 48, 72}):
        raise ValueError("invalid probability input to Platt map")
    scores = logit(np.clip(raw, 1e-6, 1 - 1e-6))
    result = np.empty_like(raw)
    for lead in np.unique(leads):
        parameters = calibration[str(int(lead))]
        if not np.isfinite(parameters["slope"]) or parameters["slope"] <= 0:
            raise ValueError("invalid monotone Platt slope")
        selected = leads == lead
        result[selected] = expit(parameters["slope"] * scores[selected] + parameters["intercept"])
    return result


def frequency_cutoff_persisted(probability: np.ndarray, target: np.ndarray) -> float:
    """Choose on the same float32 bytes and float64 comparison used in score."""
    values = np.asarray(probability, dtype=np.float32).astype(np.float64)
    target = np.asarray(target)
    if (values.ndim != 1 or values.shape != target.shape or not np.isfinite(values).all()
            or np.any((values < 0) | (values > 1)) or not np.isin(target, (0, 1)).all()
            or not 0 < int(target.sum()) < len(target)):
        raise ValueError("invalid persisted cutoff selection population")
    events = int(target.sum())
    choices = np.arange(0.01, 0.501, 0.01)
    return float(min(choices, key=lambda cutoff: (abs(np.count_nonzero(values >= cutoff) / events - 1), cutoff)))
