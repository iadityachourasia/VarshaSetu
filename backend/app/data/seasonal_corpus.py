"""Pure policies and verification helpers for a JJAS prototype corpus."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import StrEnum
from typing import Iterable

import numpy as np

from backend.app.verification.metrics import compute_contingency_table


UTC = timezone.utc
JJAS_MONTHS = (6, 7, 8, 9)


class SeasonAdmission(StrEnum):
    SEASON_ACCEPTED = "SEASON_ACCEPTED"
    SEASON_ACCEPTED_WITH_QUARANTINED_SAMPLES = "SEASON_ACCEPTED_WITH_QUARANTINED_SAMPLES"
    SEASON_REJECTED = "SEASON_REJECTED"


def seasonal_initializations(year: int) -> tuple[datetime, ...]:
    result: list[datetime] = []
    for month, days in ((6, 30), (7, 31), (8, 31), (9, 30)):
        result.extend(datetime(year, month, day, tzinfo=UTC) for day in range(1, days + 1))
    return tuple(result)


def seasonal_admission(monthly_outcomes: Iterable[str]) -> SeasonAdmission:
    outcomes = tuple(monthly_outcomes)
    if len(outcomes) != 4:
        raise ValueError("JJAS requires exactly four monthly outcomes")
    allowed = {
        "MONTH_ACCEPTED",
        "MONTH_ACCEPTED_WITH_QUARANTINED_SAMPLES",
        "MONTH_REJECTED",
    }
    if any(item not in allowed for item in outcomes):
        raise ValueError("unknown monthly admission outcome")
    if "MONTH_REJECTED" in outcomes:
        return SeasonAdmission.SEASON_REJECTED
    if "MONTH_ACCEPTED_WITH_QUARANTINED_SAMPLES" in outcomes:
        return SeasonAdmission.SEASON_ACCEPTED_WITH_QUARANTINED_SAMPLES
    return SeasonAdmission.SEASON_ACCEPTED


def raw_control_verification(
    forecast: np.ndarray,
    observation: np.ndarray,
    valid_mask: np.ndarray,
    *,
    thresholds_mm: tuple[float, ...] = (64.5, 115.6, 204.5),
) -> dict:
    forecast = np.asarray(forecast, dtype=float)
    observation = np.asarray(observation, dtype=float)
    valid_mask = np.asarray(valid_mask, dtype=bool)
    if forecast.shape != observation.shape or forecast.shape != valid_mask.shape:
        raise ValueError("forecast, observation, and mask must align")
    comparable = valid_mask & np.isfinite(forecast) & np.isfinite(observation)
    if not comparable.any():
        raise ValueError("no valid comparable cells")
    predicted, observed = forecast[comparable], observation[comparable]
    if (predicted < 0).any() or (observed < 0).any():
        raise ValueError("verification rainfall must be nonnegative")
    difference = predicted - observed
    return {
        "n": int(difference.size),
        "rmse_mm": float(np.sqrt(np.mean(difference ** 2))),
        "mae_mm": float(np.mean(np.abs(difference))),
        "bias_mm": float(np.mean(difference)),
        "contingency": {
            str(threshold): compute_contingency_table(predicted, observed, threshold)
            for threshold in thresholds_mm
        },
    }


def validate_seasonal_zarr_shape(
    *,
    forecast_shape: tuple[int, ...],
    observation_shape: tuple[int, ...],
    mask_shape: tuple[int, ...],
    atmosphere_shape: tuple[int, ...],
) -> None:
    if forecast_shape != (122, 3, 5, 49, 49):
        raise ValueError("unexpected seasonal forecast shape")
    if observation_shape != (122, 3, 49, 49) or mask_shape != observation_shape:
        raise ValueError("unexpected seasonal observation/mask shape")
    if atmosphere_shape != (122, 3, 6, 51, 81):
        raise ValueError("unexpected seasonal atmosphere shape")


def eligibility_index_row(
    *, initialization: str,
    product: str,
    valid_date: str,
    eligibility: dict[str, bool],
    reasons: Iterable[str],
    source_manifest: str,
) -> dict:
    required = {
        "SOURCE_VALID", "PAIR_VALID", "CONTROL_MODEL_ELIGIBLE",
        "FULL_ENSEMBLE_ELIGIBLE", "REGIME_ELIGIBLE",
        "EXTREME_EVENT_ELIGIBLE", "FSS_ELIGIBLE", "REJECTED",
    }
    if set(eligibility) != required:
        raise ValueError("eligibility index requires every frozen tier")
    if not source_manifest:
        raise ValueError("source manifest lineage is required")
    return {
        "initialization": initialization,
        "product": product,
        "valid_date": valid_date,
        **eligibility,
        "quarantine_reason": "; ".join(reason for reason in reasons if reason),
        "source_manifest": source_manifest,
    }
