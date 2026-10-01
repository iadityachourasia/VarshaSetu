"""Pure functions of the geography-aware correction (M5a, protocol geoaware_protocol_v1.json, docs/124).

Everything here is deterministic arithmetic with no model library and no data access: feature assembly, event weights, the embargoed
cross-validation folds, the configuration grid and the guardrailed selection rule. The training and evaluation scripts call these so the
rules are tested on their own.
"""

from __future__ import annotations

from datetime import date, datetime
from itertools import product

import numpy as np

GRID_CELLS = 49 * 49
HEAVY_MM, VERY_HEAVY_MM = 64.5, 115.6
BASE_FEATURES = [
    "raw_c00_rain_mm", "forecast_u850", "forecast_v850", "forecast_q700", "forecast_z500", "forecast_mslp", "forecast_pwat", "pwat_area_mean", "q700_area_mean",
    "u850_area_mean", "v850_area_mean", "wind_speed_area_mean", "moisture_transport_area_mean", "mslp_area_mean", "mslp_minimum", "mslp_range", "z500_area_mean",
    "relative_vorticity_area_mean", "relative_vorticity_p90", "latitude_deg", "longitude_deg", "lead_hours",
]
STATIC_FEATURES = ["mean_elevation_m", "local_relief_m", "distance_to_coast_km", "slope_m_per_km", "terrain_uphill_east", "terrain_uphill_north", "coast_landward_east", "coast_landward_north"]
FORCING_FEATURES = ["onshore_flux", "cross_barrier_flux"]
ARMS = {"A0": BASE_FEATURES, "A1": BASE_FEATURES + STATIC_FEATURES, "A2": BASE_FEATURES + FORCING_FEATURES, "A3": BASE_FEATURES + STATIC_FEATURES + FORCING_FEATURES}
EVENT_WEIGHT_CAP = 10.0
EMBARGO_DAYS = 3
G2_MAX_ABS_BIAS_MM = 1.5
G3_MIN_VERY_HEAVY_FREQUENCY_BIAS = 0.05


# ---------------------------------------------------------------------------------------------------------------- features
def static_columns(static: dict[str, np.ndarray], pixel: np.ndarray) -> np.ndarray:
    """[rows, 8] static geography per row by target-grid cell. A cell whose value is undefined stays NaN (never imputed)."""
    pixel = np.asarray(pixel, dtype=np.int64)
    if pixel.min() < 0 or pixel.max() >= GRID_CELLS:
        raise ValueError("pixel index outside the 49x49 grid")
    columns = []
    for name in STATIC_FEATURES:
        field = np.asarray(static[name], dtype=np.float64)
        if field.shape != (GRID_CELLS,):
            raise ValueError(f"{name} must be a flat 2401-cell field")
        columns.append(field[pixel])
    return np.stack(columns, axis=1).astype(np.float32)


def forcing_columns(case_ranges: list[tuple[int, int]], forcing_by_case: list[dict[str, np.ndarray]], pixel: np.ndarray, rows: int) -> np.ndarray:
    """[rows, 2] forecast-time forcing per row. ``case_ranges`` are (row_start, row_count); every row must be covered exactly once."""
    out = np.full((rows, 2), np.nan, dtype=np.float32)
    covered = np.zeros(rows, dtype=bool)
    for (start, count), forcing in zip(case_ranges, forcing_by_case):
        sl = slice(start, start + count)
        if covered[sl].any():
            raise ValueError("a row belongs to more than one case")
        covered[sl] = True
        cells = np.asarray(pixel[sl], dtype=np.int64)
        for j, name in enumerate(FORCING_FEATURES):
            out[sl, j] = np.asarray(forcing[name], dtype=np.float64)[cells]
    if not covered.all():
        raise ValueError("some rows are not covered by any case")
    return out


def assemble(base: np.ndarray, static: np.ndarray | None, forcing: np.ndarray | None, arm: str) -> np.ndarray:
    """Feature matrix of one arm, columns in the frozen registry order."""
    if base.shape[1] != len(BASE_FEATURES):
        raise ValueError("the base matrix must have the 22 frozen deterministic features")
    parts = [base]
    if arm in ("A1", "A3"):
        if static is None:
            raise ValueError(f"arm {arm} needs the static columns")
        parts.append(static)
    if arm in ("A2", "A3"):
        if forcing is None:
            raise ValueError(f"arm {arm} needs the forcing columns")
        parts.append(forcing)
    if arm not in ARMS:
        raise ValueError(f"unknown arm {arm}")
    matrix = np.concatenate(parts, axis=1).astype(np.float32)
    if matrix.shape[1] != len(ARMS[arm]):
        raise ValueError("column count does not match the registry")
    return matrix


def event_weights(y: np.ndarray, cap: float = EVENT_WEIGHT_CAP) -> np.ndarray:
    """w = min(cap, 1 + y / 64.5), from the observed rainfall of a TRAINING row. Never used at inference."""
    y = np.asarray(y, dtype=np.float64)
    if np.any(y < 0) or not np.all(np.isfinite(y)):
        raise ValueError("training targets must be finite and non-negative")
    return np.minimum(cap, 1.0 + y / HEAVY_MM)


def effective_sample_size(weights: np.ndarray) -> float:
    weights = np.asarray(weights, dtype=np.float64)
    return float(weights.sum() ** 2 / (weights ** 2).sum())


# ---------------------------------------------------------------------------------------------------------------- folds
def _day(value: str) -> date:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).date()


def training_case_mask(initialization_utc: list[str], fold_id: list[str], held_out: str, embargo_days: int = EMBARGO_DAYS) -> np.ndarray:
    """Cases usable for training when ``held_out`` is the held-out block.

    All other blocks, excluding every initialization date within ``embargo_days`` initialization days before the held-out block's first date
    and after its last date. All leads of an initialization share one date, hence one fold and one embargo status.
    """
    days = [_day(v) for v in initialization_utc]
    held = [d for d, f in zip(days, fold_id) if f == held_out]
    if not held:
        raise ValueError(f"no case in fold {held_out}")
    ordered = sorted(set(days))
    index = {d: i for i, d in enumerate(ordered)}
    first, last = min(index[d] for d in held), max(index[d] for d in held)
    return np.array([f != held_out and not (first - embargo_days <= index[d] <= last + embargo_days) for d, f in zip(days, fold_id)])


def rows_of_cases(case_ranges: list[tuple[int, int]], case_mask: np.ndarray) -> np.ndarray:
    """Boolean row mask for the selected cases."""
    total = max(start + count for start, count in case_ranges)
    mask = np.zeros(total, dtype=bool)
    for (start, count), keep in zip(case_ranges, case_mask):
        if keep:
            mask[start:start + count] = True
    return mask


# ---------------------------------------------------------------------------------------------------------------- grid and selection
def configurations() -> list[dict]:
    """The 16 configurations of the frozen grid, in the frozen order (objective, weights, depth, rounds)."""
    out = []
    for objective, weights, depth, rounds in product(["reg:squarederror", "reg:tweedie"], ["none", "capped_event"], [4, 6], [200, 350]):
        out.append({"objective": objective, "weights": weights, "max_depth": depth, "n_estimators": rounds})
    return out


def pooled_metrics(y: np.ndarray, prediction: np.ndarray) -> dict:
    y, prediction = np.asarray(y, dtype=np.float64), np.maximum(0.0, np.asarray(prediction, dtype=np.float64))
    error = prediction - y
    result = {"rmse_mm": float(np.sqrt(np.mean(error ** 2))), "mae_mm": float(np.mean(np.abs(error))), "bias_mm": float(np.mean(error)), "cells": int(y.size)}
    for name, threshold in (("heavy", HEAVY_MM), ("very_heavy", VERY_HEAVY_MM)):
        observed, forecast = y.astype(np.float32) >= np.float32(threshold), prediction.astype(np.float32) >= np.float32(threshold)
        hits = int(np.count_nonzero(observed & forecast))
        misses = int(np.count_nonzero(observed & ~forecast))
        false_alarms = int(np.count_nonzero(~observed & forecast))
        result[name] = {"hits": hits, "misses": misses, "false_alarms": false_alarms, "observed_events": hits + misses,
                        "csi": hits / (hits + misses + false_alarms) if hits + misses + false_alarms else None,
                        "frequency_bias": (hits + false_alarms) / (hits + misses) if hits + misses else None}
    return result


def guardrails(metrics: dict, raw_heavy_csi: float) -> dict[str, bool]:
    """G1 heavy CSI at least Raw's, G2 |bias| at most 1.5 mm, G3 very-heavy frequency bias at least 0.05. Undefined never passes."""
    heavy_csi = metrics["heavy"]["csi"]
    very_fb = metrics["very_heavy"]["frequency_bias"]
    return {
        "G1": heavy_csi is not None and heavy_csi >= raw_heavy_csi,
        "G2": abs(metrics["bias_mm"]) <= G2_MAX_ABS_BIAS_MM,
        "G3": very_fb is not None and very_fb >= G3_MIN_VERY_HEAVY_FREQUENCY_BIAS,
    }


def select_configuration(results: list[dict], raw_heavy_csi: float) -> dict | None:
    """Among configurations passing every guardrail, the lowest pooled RMSE; ties go to the earlier grid position. None if nothing passes."""
    eligible = [(r["metrics"]["rmse_mm"], r["grid_index"], r) for r in results if all(guardrails(r["metrics"], raw_heavy_csi).values())]
    return min(eligible, key=lambda item: (item[0], item[1]))[2] if eligible else None
