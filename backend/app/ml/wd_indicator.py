"""Forecast-time western-disturbance indicator (a rule-based heuristic, docs/138). Pure and read-only.

The indicator is the mean geostrophic relative vorticity at 500 hPa over north-west India and its neighbourhood, computed from the forecast 500 hPa geopotential height alone (zeta = g / f * del-squared Z
on the sphere). A western disturbance is an upper-level trough, so cyclonic (positive) vorticity there is the physical signature the heuristic follows. It is NOT a validated detection of western
disturbances (no label source exists, docs/122) and its flag is relative: the upper tercile of the training-year distribution. Whether it relates to observed rainfall in the region where these
systems act is a separate, pre-registered, descriptive question.
"""

from __future__ import annotations

import numpy as np
from scipy.stats import spearmanr

GRAVITY = 9.80665
EARTH_RADIUS_M = 6_371_000.0
OMEGA = 7.2921e-5
WD_BOX = (25.0, 38.0, 62.0, 78.0)            # south, north, west, east: where the trough signature is read
RAIN_BOX = (28.0, 36.0, 70.0, 80.0)          # south, north, west, east: where western-disturbance rainfall is observed
MIN_CASES = 30
REPEATS, SEED = 2000, 26080


def geostrophic_vorticity(z: np.ndarray, lat: np.ndarray, lon: np.ndarray) -> np.ndarray:
    """Geostrophic relative vorticity (s^-1) of a geopotential height field (gpm) on a regular latitude-longitude grid, by centred differences on the sphere.

    ``z`` is [lat, lon] with ascending latitude and longitude; the outermost rows and columns are NaN (they have no centred difference)."""
    z, lat, lon = np.asarray(z, dtype=np.float64), np.asarray(lat, dtype=np.float64), np.asarray(lon, dtype=np.float64)
    if z.shape != (lat.size, lon.size) or lat.size < 3 or lon.size < 3 or not np.all(np.diff(lat) > 0) or not np.all(np.diff(lon) > 0):
        raise ValueError("z must be [lat, lon] on ascending axes with at least three points each")
    phi, dphi, dlam = np.deg2rad(lat), np.deg2rad(np.diff(lat).mean()), np.deg2rad(np.diff(lon).mean())
    a2 = EARTH_RADIUS_M ** 2
    cos = np.cos(phi)[:, None]
    out = np.full(z.shape, np.nan)
    d_lon2 = (z[1:-1, 2:] - 2 * z[1:-1, 1:-1] + z[1:-1, :-2]) / (dlam ** 2)
    # (1 / cos) d/dphi (cos dZ/dphi), with the flux evaluated at the half-points
    cos_n, cos_s = np.cos(0.5 * (phi[1:-1] + phi[2:]))[:, None], np.cos(0.5 * (phi[1:-1] + phi[:-2]))[:, None]
    d_lat = (cos_n * (z[2:, 1:-1] - z[1:-1, 1:-1]) - cos_s * (z[1:-1, 1:-1] - z[:-2, 1:-1])) / (dphi ** 2)
    laplacian = (d_lat / cos[1:-1] + d_lon2 / (cos[1:-1] ** 2)) / a2
    f = (2 * OMEGA * np.sin(phi[1:-1]))[:, None]
    out[1:-1, 1:-1] = GRAVITY / f * laplacian
    return out


def box_mean(field: np.ndarray, lat: np.ndarray, lon: np.ndarray, box: tuple[float, float, float, float]) -> float:
    """Cosine-weighted mean of the finite values of ``field`` inside ``box``; NaN if there is none or the box touches a NaN (an incomplete field is never patched)."""
    south, north, west, east = box
    inside = ((lat >= south) & (lat <= north))[:, None] & ((lon >= west) & (lon <= east))[None, :]
    values = field[inside]
    if values.size == 0 or not np.isfinite(values).all():
        return float("nan")
    weights = np.broadcast_to(np.cos(np.deg2rad(lat))[:, None], field.shape)[inside]
    return float((values * weights).sum() / weights.sum())


def index_from_z500(z500: np.ndarray, lat: np.ndarray, lon: np.ndarray) -> float:
    """The indicator: mean geostrophic vorticity (units of 1e-5 s^-1) over the north-west India box. Positive is cyclonic."""
    return box_mean(geostrophic_vorticity(z500, lat, lon), lat, lon, WD_BOX) * 1e5


def upper_tercile(training_values: np.ndarray) -> dict:
    values = np.asarray(training_values, dtype=np.float64)
    values = values[np.isfinite(values)]
    if values.size < 3 * MIN_CASES:
        raise ValueError("too few training cases to fit the threshold")
    return {"threshold": float(np.quantile(values, 2 / 3)), "training_cases": int(values.size), "training_mean": float(values.mean()), "training_std": float(values.std(ddof=1))}


def flag(value: float, cut: dict) -> bool | None:
    return None if not np.isfinite(value) else bool(value >= cut["threshold"])


def group_statistics(flagged: np.ndarray, rain: np.ndarray) -> dict:
    flagged, rain = np.asarray(flagged, dtype=bool), np.asarray(rain, dtype=np.float64)
    out = {}
    for name, sel in (("flagged", flagged), ("not_flagged", ~flagged)):
        values = rain[sel]
        out[name] = {"cases": int(sel.sum()), "mean_rain_mm_per_day": float(values.mean()) if values.size else None,
                     "share_of_cases_with_rain_at_least_1mm": float((values >= 1.0).mean()) if values.size else None}
    return out


def supported(groups: dict) -> bool:
    return bool(groups["flagged"]["cases"] >= MIN_CASES and groups["not_flagged"]["cases"] >= MIN_CASES)


def _difference(flagged: np.ndarray, rain: np.ndarray) -> float:
    if not flagged.any() or flagged.all():
        return float("nan")
    return float(rain[flagged].mean() - rain[~flagged].mean())


def _rho(index: np.ndarray, rain: np.ndarray) -> float:
    if len(index) < 3 or np.ptp(rain) == 0 or np.ptp(index) == 0:
        return float("nan")
    return float(spearmanr(index, rain).statistic)


def bootstrap(index: np.ndarray, flagged: np.ndarray, rain: np.ndarray, clusters: list, *, repeats: int = REPEATS, seed: int = SEED) -> dict:
    """95 percent percentile intervals of (flagged minus not-flagged mean rainfall) and of the Spearman correlation, resampling whole initialization dates. Optimistic."""
    unique = sorted(set(clusters))
    members = {c: np.flatnonzero([x == c for x in clusters]) for c in unique}
    rng = np.random.default_rng(seed)
    diffs, rhos = [], []
    for _ in range(repeats):
        pick = np.concatenate([members[unique[i]] for i in rng.integers(0, len(unique), size=len(unique))])
        d, r = _difference(flagged[pick], rain[pick]), _rho(index[pick], rain[pick])
        if np.isfinite(d):
            diffs.append(d)
        if np.isfinite(r):
            rhos.append(r)
    out = {"repeats": repeats, "seed": seed, "unit": "initialization date"}
    for name, draws, point in (("flagged_minus_not_flagged_mean_rain", diffs, _difference(flagged, rain)), ("spearman", rhos, _rho(index, rain))):
        if len(draws) < repeats * 0.9 or not np.isfinite(point):
            out[name] = {"status": "undefined", "point": None if not np.isfinite(point) else point}
        else:
            low, high = (float(x) for x in np.quantile(draws, [0.025, 0.975]))
            out[name] = {"status": "ok", "point": point, "interval95": [low, high], "excludes_zero": bool(low > 0 or high < 0), "valid_draws": len(draws)}
    return out
