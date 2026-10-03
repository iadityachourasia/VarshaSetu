"""Forecast-time coastal and orographic forcing regime (a rule-based heuristic, docs/137). Pure and read-only.

The per-case index is the mean of the forecast cross-barrier forcing (850 hPa wind component across the local terrain gradient, multiplied by precipitable water, as in docs/118)
over the land cells of the Ghats-coast zone (coastal AND orographic). It uses forecast fields only. The classes WEAK, MODERATE and STRONG are the terciles of that index over the
TRAINING year (never a validation or test year); the continuous percentile against the training distribution accompanies the class. This is a transparent heuristic of the
physical forcing, NOT a learned or validated regime and NOT a probability; whether it discriminates is a separate, pre-registered evidence question.
"""

from __future__ import annotations

import numpy as np
from scipy.stats import spearmanr

HEAVY_MM = 64.5
CLASSES = ("WEAK", "MODERATE", "STRONG")
MIN_CLASS_CASES = 30
MIN_EVENT_PAIRS = 30
REPEATS, SEED = 2000, 26080


def zone_index(field: np.ndarray, zone_mask: np.ndarray) -> float:
    """Mean of a flat 2401-cell forcing field over the zone cells; NaN if any zone cell is not finite (an incomplete forecast is never imputed)."""
    field, zone_mask = np.asarray(field, dtype=np.float64).ravel(), np.asarray(zone_mask, dtype=bool).ravel()
    values = field[zone_mask]
    return float(values.mean()) if values.size and np.isfinite(values).all() else float("nan")


def cut_points(training_values: np.ndarray) -> dict:
    """Tercile cut-points of the training-year index. ``degenerate`` flags equal cut-points (the middle class would be empty)."""
    values = np.asarray(training_values, dtype=np.float64)
    values = values[np.isfinite(values)]
    if values.size < 3 * MIN_CLASS_CASES:
        raise ValueError("too few training cases to fit terciles")
    q33, q67 = (float(x) for x in np.quantile(values, [1 / 3, 2 / 3]))
    return {"q33": q33, "q67": q67, "training_cases": int(values.size), "degenerate": bool(q33 >= q67)}


def classify(value: float, cuts: dict) -> int | None:
    """0 WEAK (below q33), 2 STRONG (at or above q67), 1 MODERATE otherwise; None for an undefined index."""
    if not np.isfinite(value):
        return None
    return 0 if value < cuts["q33"] else 2 if value >= cuts["q67"] else 1


def percentile(value: float, training_values: np.ndarray) -> float | None:
    """Fraction of training-year cases whose index is at or below ``value`` (a rank, not a probability)."""
    if not np.isfinite(value):
        return None
    values = np.asarray(training_values, dtype=np.float64)
    values = values[np.isfinite(values)]
    return float(np.count_nonzero(values <= value) / values.size)


def group_statistics(classes: np.ndarray, heavy_cells: np.ndarray, valid_cells: np.ndarray) -> dict:
    """Per class: cases, mean observed heavy fraction of the zone, share of all heavy zone cell-case pairs, and the share of cases with at least one heavy cell."""
    classes, heavy_cells, valid_cells = (np.asarray(a) for a in (classes, heavy_cells, valid_cells))
    fraction = np.divide(heavy_cells, valid_cells, out=np.full(heavy_cells.shape, np.nan), where=valid_cells > 0)
    total_events = int(heavy_cells.sum())
    out = {}
    for i, name in enumerate(CLASSES):
        sel = classes == i
        out[name] = {"cases": int(sel.sum()), "heavy_event_pairs": int(heavy_cells[sel].sum()),
                     "share_of_all_heavy_event_pairs": float(heavy_cells[sel].sum() / total_events) if total_events else None,
                     "mean_heavy_fraction": float(np.nanmean(fraction[sel])) if sel.any() else None,
                     "share_of_cases_with_a_heavy_cell": float((heavy_cells[sel] > 0).mean()) if sel.any() else None}
    return out


def supported(groups: dict) -> bool:
    """Support gate: every class has at least MIN_CLASS_CASES cases and the population has at least MIN_EVENT_PAIRS observed heavy pairs."""
    return bool(all(g["cases"] >= MIN_CLASS_CASES for g in groups.values()) and sum(g["heavy_event_pairs"] for g in groups.values()) >= MIN_EVENT_PAIRS)


def strong_minus_weak(classes: np.ndarray, heavy_cells: np.ndarray, valid_cells: np.ndarray) -> float:
    fraction = np.divide(heavy_cells, valid_cells, out=np.full(np.shape(heavy_cells), np.nan), where=np.asarray(valid_cells) > 0)
    strong, weak = fraction[classes == 2], fraction[classes == 0]
    if not len(strong) or not len(weak):
        return float("nan")
    return float(np.nanmean(strong) - np.nanmean(weak))


def rank_correlation(index: np.ndarray, heavy_cells: np.ndarray, valid_cells: np.ndarray) -> float:
    fraction = np.divide(heavy_cells, valid_cells, out=np.full(np.shape(heavy_cells), np.nan), where=np.asarray(valid_cells) > 0)
    keep = np.isfinite(index) & np.isfinite(fraction)
    if keep.sum() < 3 or np.ptp(fraction[keep]) == 0:
        return float("nan")
    return float(spearmanr(index[keep], fraction[keep]).statistic)


def bootstrap(index: np.ndarray, classes: np.ndarray, heavy_cells: np.ndarray, valid_cells: np.ndarray, *, repeats: int = REPEATS, seed: int = SEED) -> dict:
    """95 percent percentile intervals of (STRONG minus WEAK mean heavy fraction) and of the Spearman correlation, resampling whole cases. Optimistic: consecutive days are correlated."""
    n = len(index)
    rng = np.random.default_rng(seed)
    diffs, rhos = [], []
    for _ in range(repeats):
        pick = rng.integers(0, n, size=n)
        d = strong_minus_weak(classes[pick], heavy_cells[pick], valid_cells[pick])
        r = rank_correlation(index[pick], heavy_cells[pick], valid_cells[pick])
        if np.isfinite(d):
            diffs.append(d)
        if np.isfinite(r):
            rhos.append(r)
    out = {"repeats": repeats, "seed": seed}
    for name, draws, point in (("strong_minus_weak_heavy_fraction", diffs, strong_minus_weak(classes, heavy_cells, valid_cells)), ("spearman", rhos, rank_correlation(index, heavy_cells, valid_cells))):
        if len(draws) < repeats * 0.9 or not np.isfinite(point):
            out[name] = {"status": "undefined", "point": None if not np.isfinite(point) else point}
        else:
            low, high = (float(x) for x in np.quantile(draws, [0.025, 0.975]))
            out[name] = {"status": "ok", "point": point, "interval95": [low, high], "excludes_zero": bool(low > 0 or high < 0), "valid_draws": len(draws)}
    return out
