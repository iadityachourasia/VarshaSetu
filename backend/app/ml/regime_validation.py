"""Independent, observation-based check of the forecast-only regime classifier (docs/123, docs/136). Pure and read-only.

Labels follow the *style* of Rajeevan, Gadgil and Bhate (2010): the daily rainfall anomaly averaged over the monsoon core zone, normalised, is at least +1 for at
least three consecutive days (active spell) or at most -1 (break spell), labelled for July and August only. This is an implementation of the criteria as described
in ``docs/123`` with documented deviations (a box instead of the exact core-zone polygon, a moving-average climatology, one pooled standard deviation); it is NOT the
published classification and the criteria were not verified against the paper's text. Depression has no observation-based label here and is not validated.

Nothing in this module fits or tunes anything; it counts and scores.
"""

from __future__ import annotations

from datetime import date, timedelta

import numpy as np

CMZ_LAT = (18.0, 28.0)
CMZ_LON = (65.0, 88.0)
THRESHOLD_SD = 1.0
MIN_SPELL_DAYS = 3
SMOOTH_DAYS = 15
WINDOW_MONTHS = (7, 8)
SEASON_MONTHS = (6, 7, 8, 9)
EPOCH = date(1900, 12, 31)                       # IMD RF25 TIME is "days since 1900-12-31"
STATES = ("ACTIVE", "BREAK", "NEUTRAL")
MIN_CLASS_CASES = 30
REPEATS, SEED = 2000, 26080


def dates_of(times: np.ndarray) -> list[date]:
    return [EPOCH + timedelta(days=int(t)) for t in np.asarray(times)]


def area_mean_series(rainfall: np.ndarray, lat: np.ndarray, lon: np.ndarray, *, lat_box: tuple[float, float] = CMZ_LAT, lon_box: tuple[float, float] = CMZ_LON) -> np.ndarray:
    """Cosine-latitude weighted mean rainfall (mm/day) over the valid (non-fill, non-negative, finite) cells of the box, one value per day; NaN if a day has no valid cell."""
    rainfall = np.asarray(rainfall, dtype=np.float64)
    inside = ((lat >= lat_box[0]) & (lat <= lat_box[1]))[:, None] & ((lon >= lon_box[0]) & (lon <= lon_box[1]))[None, :]
    valid = np.isfinite(rainfall) & (rainfall >= 0) & (rainfall != -999.0) & inside[None, :, :]
    weight = np.broadcast_to(np.cos(np.deg2rad(lat))[None, :, None], rainfall.shape) * valid
    total = weight.sum(axis=(1, 2))
    numerator = (np.where(valid, rainfall, 0.0) * weight).sum(axis=(1, 2))
    return np.divide(numerator, total, out=np.full(rainfall.shape[0], np.nan), where=total > 0)


def season_days() -> list[tuple[int, int]]:
    """The calendar days (month, day) of 1 June to 30 September, in order (122 days; 29 February is never in the season)."""
    out, d = [], date(2001, 6, 1)
    while d <= date(2001, 9, 30):
        out.append((d.month, d.day))
        d += timedelta(days=1)
    return out


def season_series(series: np.ndarray, days: list[date]) -> dict[tuple[int, int], float]:
    return {(d.month, d.day): float(v) for d, v in zip(days, series) if d.month in SEASON_MONTHS and np.isfinite(v)}


def climatology(per_year: dict[int, dict[tuple[int, int], float]], smooth_days: int = SMOOTH_DAYS) -> tuple[np.ndarray, float, dict]:
    """Smoothed daily climatological mean over the season and one pooled standard deviation of the July-August anomalies.

    The daily mean over the climatology years is smoothed with a centred moving average (edges use the nearest value). Returns (mean[122], sigma, info)."""
    calendar = season_days()
    values = np.array([[per_year[y].get(day, np.nan) for day in calendar] for y in sorted(per_year)], dtype=np.float64)
    if np.isnan(values).any():
        raise ValueError("a climatology year has missing days in the season")
    raw_mean = values.mean(axis=0)
    half = smooth_days // 2
    padded = np.concatenate([np.full(half, raw_mean[0]), raw_mean, np.full(half, raw_mean[-1])])
    smooth = np.convolve(padded, np.ones(2 * half + 1) / (2 * half + 1), mode="valid")
    window = np.array([m in WINDOW_MONTHS for m, _ in calendar])
    anomalies = (values - smooth[None, :])[:, window]
    sigma = float(anomalies.std(ddof=1))
    return smooth, sigma, {"years": sorted(per_year), "smooth_days": smooth_days, "window_days": int(window.sum()), "sigma_mm_per_day": sigma}


def normalised_anomaly(year_series: dict[tuple[int, int], float], mean: np.ndarray, sigma: float) -> np.ndarray:
    calendar = season_days()
    return np.array([(year_series.get(day, np.nan) - mean[i]) / sigma for i, day in enumerate(calendar)], dtype=np.float64)


def spell_mask(z: np.ndarray, *, positive: bool, threshold: float = THRESHOLD_SD, min_days: int = MIN_SPELL_DAYS) -> np.ndarray:
    """True on every day of a run of at least ``min_days`` consecutive days with z >= +threshold (positive) or z <= -threshold. NaN days break a run."""
    flag = (z >= threshold) if positive else (z <= -threshold)
    flag = np.where(np.isfinite(z), flag, False)
    out = np.zeros(len(z), dtype=bool)
    start = None
    for i in range(len(z) + 1):
        on = i < len(z) and flag[i]
        if on and start is None:
            start = i
        elif not on and start is not None:
            if i - start >= min_days:
                out[start:i] = True
            start = None
    return out


def label_days(z: np.ndarray, year: int) -> dict[date, str]:
    """ACTIVE / BREAK / NEUTRAL for every July-August day of ``year``; days outside the window are not labelled (absent)."""
    calendar = season_days()
    active, brk = spell_mask(z, positive=True), spell_mask(z, positive=False)
    if (active & brk).any():
        raise ValueError("a day cannot be both active and break")
    labels = {}
    for i, (month, day) in enumerate(calendar):
        if month in WINDOW_MONTHS and np.isfinite(z[i]):
            labels[date(year, month, day)] = "ACTIVE" if active[i] else "BREAK" if brk[i] else "NEUTRAL"
    return labels


def valid_date(initialization: date, lead_day: int) -> date:
    """The IMD day a case is paired with: initialization plus its lead day (Day 1 pairs with the next calendar day), as in the observation pairing of docs/84."""
    return initialization + timedelta(days=lead_day)


def binary_metrics(predicted: np.ndarray, observed: np.ndarray) -> dict:
    """Contingency counts and scores of one binary task. Undefined values stay None, never 0."""
    predicted, observed = np.asarray(predicted, dtype=bool), np.asarray(observed, dtype=bool)
    hits, misses = int(np.count_nonzero(predicted & observed)), int(np.count_nonzero(~predicted & observed))
    false_alarms, correct_negatives = int(np.count_nonzero(predicted & ~observed)), int(np.count_nonzero(~predicted & ~observed))
    positives, negatives = hits + misses, false_alarms + correct_negatives
    recall = hits / positives if positives else None
    specificity = correct_negatives / negatives if negatives else None
    precision = hits / (hits + false_alarms) if hits + false_alarms else None
    balanced = (recall + specificity) / 2 if recall is not None and specificity is not None else None
    f1 = 2 * precision * recall / (precision + recall) if precision is not None and recall is not None and precision + recall > 0 else (0.0 if precision is not None and recall is not None else None)
    return {"hits": hits, "misses": misses, "false_alarms": false_alarms, "correct_negatives": correct_negatives, "observed_positive": positives, "predicted_positive": hits + false_alarms,
            "recall": recall, "specificity": specificity, "precision": precision, "balanced_accuracy": balanced, "f1": f1, "base_rate": positives / (positives + negatives) if positives + negatives else None}


def confusion(predicted_class: np.ndarray, observed_state: list[str], class_names: tuple[str, ...]) -> dict:
    """Counts of predicted regime class (rows) by observed state (columns ACTIVE, BREAK, NEUTRAL)."""
    table = {name: {state: 0 for state in STATES} for name in class_names}
    for p, o in zip(predicted_class, observed_state):
        table[class_names[int(p)]][o] += 1
    return table


def task_arrays(predicted_class: np.ndarray, observed_state: list[str], class_names: tuple[str, ...]) -> dict[str, tuple[np.ndarray, np.ndarray]]:
    """The two pre-registered binary tasks: predicted ACTIVE_MONSOON vs observed ACTIVE, and predicted BREAK_WEAK_MONSOON vs observed BREAK."""
    predicted_class = np.asarray(predicted_class, dtype=int)
    obs = np.array(observed_state)
    return {"active_vs_not_active": (predicted_class == class_names.index("ACTIVE_MONSOON"), obs == "ACTIVE"),
            "break_vs_not_break": (predicted_class == class_names.index("BREAK_WEAK_MONSOON"), obs == "BREAK")}


def cluster_bootstrap_balanced_accuracy(predicted: np.ndarray, observed: np.ndarray, clusters: list, *, repeats: int = REPEATS, seed: int = SEED) -> dict | None:
    """95 percent percentile interval of the balanced accuracy, resampling whole initialization dates (all leads of a date together). Optimistic: consecutive dates are correlated."""
    predicted, observed = np.asarray(predicted, dtype=bool), np.asarray(observed, dtype=bool)
    unique = sorted(set(clusters))
    index = {c: np.flatnonzero([x == c for x in clusters]) for c in unique}
    rng = np.random.default_rng(seed)
    draws = []
    for _ in range(repeats):
        chosen = np.concatenate([index[unique[i]] for i in rng.integers(0, len(unique), size=len(unique))])
        value = binary_metrics(predicted[chosen], observed[chosen])["balanced_accuracy"]
        if value is not None:
            draws.append(value)
    if len(draws) < repeats * 0.9:
        return None
    low, high = np.quantile(draws, [0.025, 0.975])
    return {"interval95": [float(low), float(high)], "valid_draws": len(draws), "repeats": repeats, "seed": seed}


def supported(observed_counts: dict[str, int]) -> dict[str, bool]:
    """Support gate: a task is scored only if its observed class has at least MIN_CLASS_CASES cases (and the rest has at least that many too)."""
    total = sum(observed_counts.values())
    return {state: bool(observed_counts[state] >= MIN_CLASS_CASES and total - observed_counts[state] >= MIN_CLASS_CASES) for state in ("ACTIVE", "BREAK")}
