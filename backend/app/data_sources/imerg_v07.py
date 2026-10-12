"""Exact 03-03 UTC accumulation of NASA IMERG V07 half-hourly rates.

This is a reference-data adapter for sensitivity studies. It is never a
forecast-time predictor and never silently substitutes for IMD rainfall.
Native 0.1-degree fields must be spatially aligned separately before scoring.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Iterable

import numpy as np

PRODUCT = "GPM_3IMERGHH_07"
STEP = timedelta(minutes=30)
STEPS_PER_DAY = 48


@dataclass(frozen=True)
class HalfHourRate:
    start_utc: datetime
    end_utc: datetime
    rate_mm_per_hour: np.ndarray
    product: str = PRODUCT


def accumulate_imd_window(fields: Iterable[HalfHourRate], start_utc: datetime) -> np.ndarray:
    """Return mm/24 h, preserving NaN wherever any half-hour is missing.

    ``start_utc`` must be 03:00 UTC. Each supplied field is the rate for its
    explicit [start,end) interval; 48 contiguous intervals are required. This
    does not infer interval placement from a file's nominal timestamp.
    """
    if start_utc.tzinfo is None or start_utc.utcoffset() != timedelta(0) or (start_utc.hour, start_utc.minute, start_utc.second) != (3, 0, 0):
        raise ValueError("IMERG accumulation must start at 03:00 UTC")
    expected = start_utc.astimezone(timezone.utc)
    total = None
    valid = None
    count = 0
    for field in fields:
        if count >= STEPS_PER_DAY or field.product != PRODUCT or field.start_utc != expected or field.end_utc != expected + STEP:
            raise ValueError(f"IMERG interval {count} is missing, duplicated, out of order or from the wrong product")
        rate = np.asarray(field.rate_mm_per_hour, dtype=np.float64)
        if rate.ndim != 2 or np.any(np.isfinite(rate) & (rate < 0)):
            raise ValueError("IMERG rate field must be a non-negative 2-D grid in mm/hour")
        if total is None:
            total = np.zeros(rate.shape, dtype=np.float64)
            valid = np.ones(rate.shape, dtype=bool)
        elif rate.shape != total.shape:
            raise ValueError("IMERG grid changed within the 24-hour window")
        finite = np.isfinite(rate)
        valid &= finite
        total += np.where(finite, rate, 0.0) * 0.5
        expected += STEP
        count += 1
    if count != STEPS_PER_DAY:
        raise ValueError(f"IMERG window has {count} intervals; 48 are required")
    total[~valid] = np.nan
    return total
