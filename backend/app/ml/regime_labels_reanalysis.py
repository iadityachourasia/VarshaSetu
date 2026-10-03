"""Objective retrospective regime labels from ERA5 geopotential (docs/142). Pure functions, no data access beyond the arrays passed in.

ERA5 is a reanalysis: it is used ONLY to label past days (AGENTS.md section 3.5), never as a forecast input. The labels are objective, rule-based and frozen in a protocol before any score; they are in the style
of the published feature-tracking work (Hunt et al. 2018 for western disturbances, Hurley and Boos 2015 for monsoon lows) but they are NOT those trackers and NOT an expert analysis. Both use the geostrophic relative
vorticity of the geopotential at one level, the same quantity the forecast-time western-disturbance indicator uses (``wd_indicator``), so label and forecast describe the same physical feature.

* western disturbance day: the box maximum of 500 hPa geostrophic vorticity over 20-36.5 N, 60-80 E reaches a threshold at any of the four daily times, on at least two consecutive days;
* monsoon low / depression day: the box maximum of 850 hPa geostrophic vorticity over 15-25 N, 70-95 E reaches a threshold at any of the four daily times, on at least two consecutive days.

The thresholds are percentiles of the daily-maximum distribution over the TRAINING years only (relative labels: a fixed share of days is labelled by construction), fixed before any forecast is compared.
"""

from __future__ import annotations

import numpy as np

from backend.app.ml.wd_indicator import GRAVITY, geostrophic_vorticity

WD_BOX = (20.0, 36.5, 60.0, 80.0)            # south, north, west, east (the Hunt et al. 2018 tracking region)
LPS_BOX = (15.0, 25.0, 70.0, 95.0)       # north of 25 N the 850 hPa level is below the Himalayan foothills and the extrapolated geopotential gives spurious vorticity
LEVELS_HPA = (50, 100, 150, 200, 250, 300, 400, 500, 600, 700, 850, 925, 1000)
STEPS_PER_DAY = 4
MIN_DAYS = 2
PERCENTILE = 0.85


def decode_chunk(raw: bytes, shape: tuple[int, ...] = (8, 13, 240, 121)) -> np.ndarray:
    """One zarr v2 blosc chunk [time, level, lon, lat] -> float64 [time, level, lat, lon] (geopotential, m2 s-2)."""
    from numcodecs import Blosc
    flat = np.frombuffer(Blosc().decode(raw), dtype="<f4")
    if flat.size != int(np.prod(shape)):
        raise ValueError("chunk size does not match the zarr metadata")
    return flat.reshape(shape).transpose(0, 1, 3, 2).astype(np.float64)


def level_vorticity(geopotential: np.ndarray, level_index: int, lat: np.ndarray, lon: np.ndarray) -> np.ndarray:
    """Geostrophic relative vorticity (1e-5 s-1) of one level for every time of ``geopotential`` [time, level, lat, lon]. Outermost rows and columns are NaN."""
    out = np.empty((geopotential.shape[0], lat.size, lon.size))
    with np.errstate(divide="ignore", invalid="ignore"):          # the equatorial row has no geostrophic vorticity; it is never inside a label box
        for t in range(geopotential.shape[0]):
            out[t] = geostrophic_vorticity(geopotential[t, level_index] / GRAVITY, lat, lon) * 1e5
    return out


def box_maximum(field: np.ndarray, lat: np.ndarray, lon: np.ndarray, box: tuple[float, float, float, float]) -> np.ndarray:
    """Maximum of ``field`` [time, lat, lon] inside the box, per time; NaN if the box holds a NaN (an incomplete field is never patched)."""
    south, north, west, east = box
    inside = ((lat >= south) & (lat <= north))[:, None] & ((lon >= west) & (lon <= east))[None, :]
    values = field[:, inside]
    if values.size == 0:
        raise ValueError("the box contains no grid point")
    out = values.max(axis=1)
    out[~np.isfinite(values).all(axis=1)] = np.nan
    return out


def daily_maximum(series: np.ndarray) -> np.ndarray:
    """Daily maximum of a 6-hourly series (four times per day, starting at 00 UTC). Any NaN time makes the day NaN."""
    if series.size % STEPS_PER_DAY:
        raise ValueError("the series must hold whole days")
    return series.reshape(-1, STEPS_PER_DAY).max(axis=1)


def percentile_threshold(training_daily_max: np.ndarray, q: float = PERCENTILE) -> float:
    values = np.asarray(training_daily_max, dtype=np.float64)
    values = values[np.isfinite(values)]
    if values.size < 500:
        raise ValueError("too few training days to fix the threshold")
    return float(np.quantile(values, q))


def persistent_days(daily_max: np.ndarray, threshold: float, min_days: int = MIN_DAYS) -> np.ndarray:
    """Boolean per day: at or above the threshold and part of a run of at least ``min_days`` consecutive such days. A NaN day is never flagged and ends a run."""
    above = np.isfinite(daily_max) & (daily_max >= threshold)
    out = np.zeros(above.shape, dtype=bool)
    i = 0
    while i < len(above):
        if above[i]:
            j = i
            while j + 1 < len(above) and above[j + 1]:
                j += 1
            if j - i + 1 >= min_days:
                out[i: j + 1] = True
            i = j + 1
        else:
            i += 1
    return out
