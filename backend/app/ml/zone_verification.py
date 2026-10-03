"""Zone-stratified verification of frozen rainfall grids (coastal/orographic protocol v3, docs/115; Stage 1).

Pure, read-only arithmetic. Nothing here fits, tunes or selects a model. For every case it reduces the paired cells of each
static geographic-forcing zone to additive sufficient statistics, so pooled metrics and the paired whole-case bootstrap are
exact re-aggregations of the same numbers.

Per (zone, model) statistic vector, in this order (``STAT_NAMES``):
    n, sum_error, sum_abs_error, sum_sq_error  (error = forecast - observation, mm per 24 h)
    heavy_hits, heavy_misses, heavy_false_alarms, very_heavy_hits, very_heavy_misses, very_heavy_false_alarms
"""

from __future__ import annotations

import numpy as np

GRID_CELLS = 49 * 49
THRESHOLDS = (("heavy", 64.5), ("very_heavy", 115.6))
STAT_NAMES = ("n", "sum_error", "sum_abs_error", "sum_sq_error",
              "heavy_hits", "heavy_misses", "heavy_false_alarms",
              "very_heavy_hits", "very_heavy_misses", "very_heavy_false_alarms")
S = len(STAT_NAMES)
PRE_REGISTERED_ZONES = ("COASTAL", "OROGRAPHIC", "COASTAL_AND_OROGRAPHIC", "OTHER")
DESCRIPTIVE_ZONES = ("COASTAL_ANY", "OROGRAPHIC_ANY")      # overlapping views; never part of the decision rule
ZONES = ("ALL", *PRE_REGISTERED_ZONES, *DESCRIPTIVE_ZONES)
MIN_CELLS, MIN_CASES, MIN_EVENT_PAIRS = 20, 30, 30           # protocol v3 support gate
REPEATS, SEED = 2000, 26080


def zone_masks(zone_labels: list[list[str | None]]) -> dict[str, np.ndarray]:
    """Boolean flat-grid mask per zone from the artifact's 49x49 zone labels (row = south to north, flat = row * 49 + column)."""
    flat = np.array([label for row in zone_labels for label in row], dtype=object)
    if flat.shape != (GRID_CELLS,):
        raise ValueError("zone labels must be a 49x49 grid")
    footprint = np.array([label is not None for label in flat])
    masks = {"ALL": footprint}
    for name in PRE_REGISTERED_ZONES:
        masks[name] = np.array([label == name for label in flat])
    masks["COASTAL_ANY"] = masks["COASTAL"] | masks["COASTAL_AND_OROGRAPHIC"]
    masks["OROGRAPHIC_ANY"] = masks["OROGRAPHIC"] | masks["COASTAL_AND_OROGRAPHIC"]
    if sum(int(masks[n].sum()) for n in PRE_REGISTERED_ZONES) != int(footprint.sum()):
        raise ValueError("pre-registered zones must partition the footprint")
    return masks


def case_stats(observed: np.ndarray, forecasts: dict[str, np.ndarray], masks: dict[str, np.ndarray], names: tuple[str, ...] | list[str] = ZONES) -> np.ndarray:
    """Statistic array [stratum, model, S] for one case (strata = ``names``, default the zones). Inputs are flat 2401-cell fields, NaN off the paired cells."""
    valid = np.isfinite(observed)
    for name, field in forecasts.items():
        if not np.array_equal(valid, np.isfinite(field)):
            raise ValueError(f"{name}: forecast and observation cells differ")
    if np.any(valid & ~masks["ALL"]):
        raise ValueError("a paired cell lies outside the static geography footprint")
    out = np.zeros((len(names), len(forecasts), S), dtype=np.float64)
    for zi, zone in enumerate(names):
        cells = valid & masks[zone]
        if not cells.any():
            continue
        obs = observed[cells]
        for mi, field in enumerate(forecasts.values()):
            fc = field[cells]
            err = fc - obs
            row = [obs.size, err.sum(), np.abs(err).sum(), (err ** 2).sum()]
            for _, thr in THRESHOLDS:
                # the frozen metrics threshold float32 values against the float32-rounded cut-off; do exactly the same
                o, f = obs.astype(np.float32) >= np.float32(thr), fc.astype(np.float32) >= np.float32(thr)
                row += [np.count_nonzero(o & f), np.count_nonzero(o & ~f), np.count_nonzero(~o & f)]
            out[zi, mi] = row
    return out


def _idx(name: str) -> int:
    return STAT_NAMES.index(name)


def metrics(vector: np.ndarray) -> dict:
    """Pooled metrics from one summed statistic vector; undefined stays None, never 0."""
    n = vector[_idx("n")]
    result = {"cell_count": int(n),
              "rmse_mm": float(np.sqrt(vector[_idx("sum_sq_error")] / n)) if n else None,
              "mae_mm": float(vector[_idx("sum_abs_error")] / n) if n else None,
              "bias_mm": float(vector[_idx("sum_error")] / n) if n else None, "categorical": {}}
    for name, _ in THRESHOLDS:
        h, m, fa = (vector[_idx(f"{name}_{k}")] for k in ("hits", "misses", "false_alarms"))
        random_hits = (h + m) * (h + fa) / n if n else 0.0
        den = {"POD": h + m, "FAR": h + fa, "CSI": h + m + fa, "ETS": h + m + fa - random_hits}
        num = {"POD": h, "FAR": fa, "CSI": h, "ETS": h - random_hits}
        result["categorical"][name] = {
            "hits": int(h), "misses": int(m), "false_alarms": int(fa), "observed_event_count": int(h + m),
            "forecast_event_count": int(h + fa),
            "frequency_bias": float((h + fa) / (h + m)) if (h + m) else None,
            **{k: (float(num[k] / den[k]) if den[k] else None) for k in den}}
    return result


def support(stack: np.ndarray, cell_counts: dict[str, int]) -> dict:
    """Support gate (protocol v3): >= 20 cells, >= 30 cases and >= 30 observed event cell-case pairs for the threshold."""
    totals = stack.sum(axis=0)                                  # [zone, model, S]; observed events are model independent
    out = {}
    for zi, zone in enumerate(ZONES):
        cases = int(np.count_nonzero(stack[:, zi, 0, _idx("n")] > 0))
        block = {"cells": cell_counts[zone], "cases": cases}
        for name, _ in THRESHOLDS:
            events = int(totals[zi, 0, _idx(f"{name}_hits")] + totals[zi, 0, _idx(f"{name}_misses")])
            block[name] = {"observed_event_pairs": events,
                           "supported": bool(cell_counts[zone] >= MIN_CELLS and cases >= MIN_CASES and events >= MIN_EVENT_PAIRS)}
        block["continuous_supported"] = bool(cell_counts[zone] >= MIN_CELLS and cases >= MIN_CASES)
        out[zone] = block
    return out


def _metric(vector: np.ndarray, which: str) -> float:
    n = vector[_idx("n")]
    if not n:
        return np.nan
    if which == "rmse":
        return float(np.sqrt(vector[_idx("sum_sq_error")] / n))
    if which == "bias":
        return float(vector[_idx("sum_error")] / n)
    if which == "mae":
        return float(vector[_idx("sum_abs_error")] / n)
    name = "very_heavy" if which == "very_heavy_csi" else "heavy"
    h, m, fa = (vector[_idx(f"{name}_{k}")] for k in ("hits", "misses", "false_alarms"))
    if which == "heavy_fb":
        return float((h + fa) / (h + m)) if (h + m) else np.nan
    return float(h / (h + m + fa)) if (h + m + fa) else np.nan


Q1_METRICS = ("rmse", "bias", "heavy_csi", "very_heavy_csi")
Q2_METRICS = ("rmse", "heavy_csi", "very_heavy_csi")


def difference_statistics(totals: np.ndarray, models: list[str]) -> dict[tuple, float]:
    """Q1 and Q2 point statistics from summed [zone, model, S] totals.

    Q1: metric(zone, model) - metric(ALL, model).
    Q2: [metric(zone, model) - metric(zone, M0)] - [metric(ALL, model) - metric(ALL, M0)] for corrected models.
    """
    out = {}
    z = {name: i for i, name in enumerate(ZONES)}
    m = {name: i for i, name in enumerate(models)}
    for zone in ZONES[1:]:
        for model in models:
            for metric in Q1_METRICS:
                out[("q1", zone, model, metric)] = _metric(totals[z[zone], m[model]], metric) - _metric(totals[z["ALL"], m[model]], metric)
            if model == "M0":
                continue
            for metric in Q2_METRICS:
                zone_gain = _metric(totals[z[zone], m[model]], metric) - _metric(totals[z[zone], m["M0"]], metric)
                all_gain = _metric(totals[z["ALL"], m[model]], metric) - _metric(totals[z["ALL"], m["M0"]], metric)
                out[("q2", zone, model, metric)] = zone_gain - all_gain
    return out


def paired_bootstrap(stack: np.ndarray, models: list[str], *, statistic=None, repeats: int = REPEATS, seed: int = SEED, chunk: int = 100,
                     level: float = 0.95) -> dict[tuple, dict]:
    """Paired whole-case bootstrap of every Q1/Q2 statistic (same resampled cases for every statistic and model).

    Cells of a case stay together; consecutive days are serially correlated, so intervals are optimistic.
    ``level`` is the two-sided interval level. At the default 0.95 the output is exactly the historical one (key ``interval95``); at any other level the
    interval is stored under ``interval`` together with ``level`` so a 97.5 percent interval can never be mistaken for a 95 percent one.
    """
    if not 0.5 < level < 1:
        raise ValueError("level must lie in (0.5, 1)")
    statistic = statistic or difference_statistics
    n = stack.shape[0]
    if n < 2:
        return {}
    flat = stack.reshape(n, -1)
    shape = stack.shape[1:]
    point = statistic(stack.sum(axis=0), models)
    rng = np.random.default_rng(seed)
    draws = {key: [] for key in point}
    done = 0
    while done < repeats:
        size = min(chunk, repeats - done)
        weights = np.zeros((size, n))
        for r in range(size):
            weights[r] = np.bincount(rng.integers(0, n, size=n), minlength=n)
        sums = (weights @ flat).reshape(size, *shape)
        for r in range(size):
            for key, value in statistic(sums[r], models).items():
                draws[key].append(value)
        done += size
    result = {}
    for key, values in draws.items():
        arr = np.asarray(values, dtype=float)
        finite = arr[np.isfinite(arr)]
        if not np.isfinite(point[key]):
            result[key] = {"status": "undefined", "point": None}
        elif len(finite) < repeats * 0.9:
            result[key] = {"status": "unstable", "point": float(point[key]), "valid_draws": int(len(finite))}
        else:
            tail = (1 - level) / 2
            low, high = (float(np.quantile(finite, q)) for q in (tail, 1 - tail))
            name = "interval95" if level == 0.95 else "interval"
            result[key] = {"status": "ok", "point": float(point[key]), name: [low, high], "valid_draws": int(len(finite)), "excludes_zero": bool(low > 0 or high < 0)}
            if level != 0.95:
                result[key]["level"] = level
    return result


# ---------------------------------------------------------------------------
# Stage 2: forecast-time forcing strength (docs/118; spec zone_stage2_spec_v1.json)
# ---------------------------------------------------------------------------

STRATA = ("weak", "middle", "strong")
COMPONENTS = {"COASTAL": ("onshore",), "OROGRAPHIC": ("cross_barrier",), "COASTAL_AND_OROGRAPHIC": ("onshore", "cross_barrier")}
Q3_DECISION = ("heavy_fb", "heavy_csi")
Q3_DESCRIPTIVE = ("rmse", "bias")


def resample_to_target(field: np.ndarray, context_lat: np.ndarray, context_lon: np.ndarray, target_lat: np.ndarray, target_lon: np.ndarray) -> np.ndarray:
    """Bilinear resampling of one 51x81 context field to the flat 49x49 target-cell centres (no extrapolation)."""
    from scipy.interpolate import RegularGridInterpolator

    interpolator = RegularGridInterpolator((context_lat, context_lon), np.asarray(field, dtype=np.float64), method="linear", bounds_error=True)
    lat, lon = np.meshgrid(target_lat, target_lon, indexing="ij")
    return interpolator(np.stack([lat.ravel(), lon.ravel()], axis=-1))


def forcing_fields(u850: np.ndarray, v850: np.ndarray, pwat: np.ndarray, geometry: dict[str, np.ndarray]) -> dict[str, np.ndarray]:
    """Flat 2401-cell moisture-flux-proxy forcing from FORECAST fields and static geometry only.

    The signature deliberately has no observation argument. ``u850``, ``v850`` and ``pwat`` are already on the target grid (flat);
    ``geometry`` holds the static unit vectors (coast_landward_east/north, terrain_uphill_east/north).
    """
    onshore = np.maximum(0.0, u850 * geometry["coast_landward_east"] + v850 * geometry["coast_landward_north"])
    cross = np.maximum(0.0, u850 * geometry["terrain_uphill_east"] + v850 * geometry["terrain_uphill_north"])
    return {"onshore": onshore * pwat, "cross_barrier": cross * pwat}


def tercile_cut_points(values: np.ndarray) -> dict:
    values = np.asarray(values, dtype=np.float64)
    values = values[np.isfinite(values)]
    q1, q2 = (float(q) for q in np.quantile(values, [1 / 3, 2 / 3]))
    return {"q33": q1, "q67": q2, "pairs": int(values.size), "degenerate": bool(q1 >= q2)}


def stratum_masks(forcing: np.ndarray, zone_mask: np.ndarray, cuts: dict) -> dict[str, np.ndarray]:
    """weak <= q33 < middle <= q67 < strong, restricted to the zone; the three strata partition the zone's cells."""
    finite = np.isfinite(forcing)
    return {"weak": zone_mask & finite & (forcing <= cuts["q33"]),
            "middle": zone_mask & finite & (forcing > cuts["q33"]) & (forcing <= cuts["q67"]),
            "strong": zone_mask & finite & (forcing > cuts["q67"])}


def q3_statistics(totals: np.ndarray, models: list[str], keys: list[tuple[str, str]], names: list[str]) -> dict[tuple, float]:
    """strong minus weak per (zone, component), model and metric; ``totals`` is [stratum, model, S] indexed by ``names``."""
    index = {name: i for i, name in enumerate(names)}
    out = {}
    for zone, component in keys:
        weak, strong = index[f"{zone}|{component}|weak"], index[f"{zone}|{component}|strong"]
        for mi, model in enumerate(models):
            for metric in (*Q3_DECISION, *Q3_DESCRIPTIVE):
                out[("q3", f"{zone}|{component}", model, metric)] = _metric(totals[strong, mi], metric) - _metric(totals[weak, mi], metric)
    return out


def stratum_support(stack: np.ndarray, names: list[str]) -> dict:
    """Stage 2 gate: >= 30 cases with a cell, >= 600 cell-case pairs and, for categorical scores, >= 30 observed events."""
    totals = stack.sum(axis=0)
    out = {}
    for i, name in enumerate(names):
        pairs = int(totals[i, 0, _idx("n")])
        cases = int(np.count_nonzero(stack[:, i, 0, _idx("n")] > 0))
        events = int(totals[i, 0, _idx("heavy_hits")] + totals[i, 0, _idx("heavy_misses")])
        out[name] = {"cell_case_pairs": pairs, "cases": cases, "heavy_observed_event_pairs": events,
                     "continuous_supported": bool(cases >= MIN_CASES and pairs >= MIN_CELLS * MIN_CASES),
                     "heavy_supported": bool(cases >= MIN_CASES and pairs >= MIN_CELLS * MIN_CASES and events >= MIN_EVENT_PAIRS)}
    return out
