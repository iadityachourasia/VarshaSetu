"""Pure Phase 1C sequence, spatial, event, and accounting helpers."""

from __future__ import annotations

import calendar
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone

import numpy as np
from scipy.interpolate import RegularGridInterpolator

from backend.app.data.regridding import grid_cell_areas
from backend.app.data.thresholds import HEAVY_24H_MIN_MM, VERY_HEAVY_24H_MIN_MM


UTC = timezone.utc
JULY_2019_START = date(2019, 7, 1)
JULY_2019_END = date(2019, 7, 31)
PRODUCT_WINDOWS = {
    "day1_24h": (3, 27),
    "day2_24h": (27, 51),
    "day3_24h": (51, 75),
}
ENSEMBLE_MEMBERS = ("c00", "p01", "p02", "p03", "p04")
ATMOSPHERIC_LEADS = (24, 48, 72)
TARGET_BOUNDS = {"south": 10.0, "north": 22.0, "west": 68.0, "east": 80.0}
CONTEXT_BOUNDS = {"south": 5.0, "north": 30.0, "west": 55.0, "east": 95.0}


def monthly_initializations(year: int = 2019, month: int = 7) -> list[datetime]:
    count = calendar.monthrange(year, month)[1]
    return [
        datetime.combine(date(year, month, day), time(), tzinfo=UTC)
        for day in range(1, count + 1)
    ]


def product_valid_date(initialization: datetime, product: str) -> date:
    if product not in PRODUCT_WINDOWS:
        raise ValueError(f"unknown rainfall product {product}")
    return (initialization + timedelta(hours=PRODUCT_WINDOWS[product][1])).date()


def product_window(initialization: datetime, product: str) -> tuple[datetime, datetime]:
    start, end = PRODUCT_WINDOWS[product]
    return initialization + timedelta(hours=start), initialization + timedelta(hours=end)


def context_coordinates() -> tuple[np.ndarray, np.ndarray]:
    latitude = np.arange(5.0, 30.0 + 0.5, 0.5, dtype=float)
    longitude = np.arange(55.0, 95.0 + 0.5, 0.5, dtype=float)
    return latitude, longitude


def bilinear_to_context(
    values: np.ndarray,
    source_latitude: np.ndarray,
    source_longitude: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    values = np.asarray(values, dtype=float)
    source_latitude = np.asarray(source_latitude, dtype=float)
    source_longitude = np.asarray(source_longitude, dtype=float)
    target_latitude, target_longitude = context_coordinates()
    if values.shape != (source_latitude.size, source_longitude.size):
        raise ValueError("atmospheric values and coordinates do not align")
    if not np.isfinite(values).all():
        raise ValueError("atmospheric source contains non-finite values")
    if (
        source_latitude[0] > target_latitude[0]
        or source_latitude[-1] < target_latitude[-1]
        or source_longitude[0] > target_longitude[0]
        or source_longitude[-1] < target_longitude[-1]
    ):
        raise ValueError("atmospheric source does not cover the context grid")
    interpolator = RegularGridInterpolator(
        (source_latitude, source_longitude),
        values,
        method="linear",
        bounds_error=True,
    )
    yy, xx = np.meshgrid(target_latitude, target_longitude, indexing="ij")
    target = interpolator(np.column_stack([yy.ravel(), xx.ravel()])).reshape(yy.shape)
    if not np.isfinite(target).all():
        raise ValueError("bilinear atmospheric output contains non-finite values")
    return target, target_latitude, target_longitude


def numeric_stats(values: np.ndarray) -> dict:
    values = np.asarray(values, dtype=float)
    return {
        "min": float(np.min(values)),
        "max": float(np.max(values)),
        "mean": float(np.mean(values)),
        "missing_fraction": float((~np.isfinite(values)).mean()),
    }


def observation_event_stats(
    rainfall_mm: np.ndarray,
    valid_mask: np.ndarray,
    latitude: np.ndarray,
    longitude: np.ndarray,
    *,
    valid_date: date,
) -> dict:
    rainfall_mm = np.asarray(rainfall_mm, dtype=float)
    valid_mask = np.asarray(valid_mask, dtype=bool)
    if rainfall_mm.shape != valid_mask.shape or not valid_mask.any():
        raise ValueError("observation field has no valid comparable cells")
    valid = rainfall_mm[valid_mask]
    if not np.isfinite(valid).all() or (valid < 0).any():
        raise ValueError("observation valid cells contain invalid rainfall")
    areas = grid_cell_areas(latitude, longitude)
    valid_area = float(np.sum(areas[valid_mask]))
    heavy = valid_mask & (rainfall_mm >= HEAVY_24H_MIN_MM)
    very_heavy = valid_mask & (rainfall_mm >= VERY_HEAVY_24H_MIN_MM)
    return {
        "valid_date": valid_date.isoformat(),
        "valid_cell_count": int(valid_mask.sum()),
        "masked_cell_count": int((~valid_mask).sum()),
        "min_mm": float(np.min(valid)),
        "max_mm": float(np.max(valid)),
        "mean_mm": float(np.mean(valid)),
        "p90_mm": float(np.percentile(valid, 90)),
        "p95_mm": float(np.percentile(valid, 95)),
        "heavy_cell_count": int(heavy.sum()),
        "very_heavy_cell_count": int(very_heavy.sum()),
        "heavy_valid_area_fraction": float(np.sum(areas[heavy]) / valid_area),
        "very_heavy_valid_area_fraction": float(np.sum(areas[very_heavy]) / valid_area),
        "heavy_threshold_mm": HEAVY_24H_MIN_MM,
        "very_heavy_threshold_mm": VERY_HEAVY_24H_MIN_MM,
    }


def summarize_initialization_status(case_statuses: list[str]) -> str:
    if not case_statuses:
        return "BLOCKED"
    statuses = set(case_statuses)
    if statuses == {"PASS"}:
        return "PASS"
    if statuses == {"BLOCKED"}:
        return "BLOCKED"
    if statuses == {"FAIL"}:
        return "FAIL"
    return "PARTIAL"


def projected_storage(measured_month_bytes: int) -> dict:
    if measured_month_bytes < 0:
        raise ValueError("measured bytes cannot be negative")
    july_days = 31
    jjas_days = 122
    return {
        "measured_july_bytes": measured_month_bytes,
        "bytes_per_initialization": measured_month_bytes / july_days,
        "projected_jjas_2019_bytes": round(measured_month_bytes * jjas_days / july_days),
        "projected_20_year_jjas_bytes": round(
            measured_month_bytes * jjas_days / july_days * 20
        ),
        "assumption": (
            "linear by initialization count from July 2019; excludes provider/version "
            "changes, retry variance, filesystem overhead changes, and future extra variables"
        ),
    }
