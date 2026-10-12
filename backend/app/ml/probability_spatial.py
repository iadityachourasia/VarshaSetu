"""Fractions-skill components for a thresholded probability field on a 2-D grid."""

from __future__ import annotations

import numpy as np
from scipy.ndimage import convolve


def warning_fss_components(
    probability: np.ndarray,
    observed_rain_mm: np.ndarray,
    valid_mask: np.ndarray,
    *,
    probability_cutoff: float,
    rain_threshold_mm: float,
    size: int,
    min_valid_fraction: float = 0.5,
) -> dict:
    """Return additive FSS sums, excluding missing cells from every neighborhood.

    The probability cutoff applies only to the forecast; the rainfall threshold
    applies only to the 24-hour reference. A caller must pass the same paired
    valid mask for all compared probability arms.
    """
    p = np.asarray(probability, dtype=np.float64)
    rain = np.asarray(observed_rain_mm, dtype=np.float64)
    valid = np.asarray(valid_mask, dtype=bool)
    if (p.ndim != 2 or p.shape != rain.shape or p.shape != valid.shape
            or size < 1 or size % 2 != 1
            or not 0 < probability_cutoff < 1
            or rain_threshold_mm <= 0
            or not 0 < min_valid_fraction <= 1):
        raise ValueError("invalid aligned probability FSS inputs")
    if (not np.isfinite(p[valid]).all() or not np.isfinite(rain[valid]).all()
            or np.any((p[valid] < 0) | (p[valid] > 1))
            or np.any(rain[valid] < 0)):
        raise ValueError("invalid probability or reference on paired cells")
    forecast_event = valid & (p >= probability_cutoff)
    observed_event = valid & (rain >= rain_threshold_mm)
    kernel = np.ones((size, size), dtype=np.float64)
    count = convolve(valid.astype(np.float64), kernel, mode="constant", cval=0)
    potential = convolve(np.ones(valid.shape, dtype=np.float64), kernel, mode="constant", cval=0)
    centers = valid & (count > 0) & (count >= min_valid_fraction * potential)
    forecast_fraction = convolve(forecast_event.astype(np.float64), kernel, mode="constant", cval=0) / np.maximum(count, 1)
    observed_fraction = convolve(observed_event.astype(np.float64), kernel, mode="constant", cval=0) / np.maximum(count, 1)
    numerator = float(np.square(forecast_fraction[centers] - observed_fraction[centers]).sum())
    denominator = float((np.square(forecast_fraction[centers]) + np.square(observed_fraction[centers])).sum())
    if numerator > denominator + 1e-8:
        raise ValueError("invalid FSS component relationship")
    return {
        "numerator": numerator,
        "denominator": denominator,
        "eligible_centers": int(centers.sum()),
        "paired_cells": int(valid.sum()),
        "forecast_events": int(forecast_event.sum()),
        "observed_events": int(observed_event.sum()),
        "hits": int((forecast_event & observed_event).sum()),
    }


def fss_from_sums(numerator: float, denominator: float) -> float | None:
    if not np.isfinite(numerator) or not np.isfinite(denominator) or numerator < 0 or denominator < 0:
        raise ValueError("invalid aggregate FSS sums")
    if denominator == 0:
        return None
    if numerator > denominator + 1e-8:
        raise ValueError("FSS numerator exceeds reference denominator")
    return float(np.clip(1 - numerator / denominator, 0, 1))
