"""Regime/lead-stratified categorical and FSS diagnostics for frozen M0-M4 grids (pure, read-only).

Nothing here fits, tunes or selects a model. Every score is a descriptive re-aggregation of
already-frozen predictions against already-paired IMD cells, using the frozen Phase 2B/2C metric
definitions. This is the tracked home of the code first written for Phase 4M (docs/106); it is shared
by the Track B (2024/2025) and Track A (2018/2019) evidence builders (docs/108).
"""

from __future__ import annotations

import re

import numpy as np
from scipy.ndimage import convolve

try:
    from backend.app.ml.phase2b import continuous_metrics, event_metrics
except ModuleNotFoundError:
    from app.ml.phase2b import continuous_metrics, event_metrics

MODELS = ("M0", "M1", "M2", "M3", "M4")
THRESHOLDS = (("heavy", 64.5), ("very_heavy", 115.6))
SCALES = (1, 3, 5, 9)
REGIMES = ("ACTIVE_MONSOON", "BREAK_WEAK_MONSOON", "LOW_DEPRESSION_INFLUENCED")
BOOT_PAIRS = (("M3", "M0"), ("M3", "M2"), ("M4", "M0"), ("M4", "M2"), ("M2", "M0"), ("M3", "M4"))
BOOT_SCALES = (3, 9)
GRID_CELLS = 49 * 49


def to_field(values: np.ndarray, pixel: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Scatter one case's paired cells onto the 49x49 target grid (flat index = row * 49 + column)."""
    if len(np.unique(pixel)) != len(pixel) or np.any((pixel < 0) | (pixel >= GRID_CELLS)):
        raise ValueError("invalid target-grid pixel mapping")
    grid = np.full(GRID_CELLS, np.nan, dtype=np.float32)
    grid[pixel] = values
    mask = np.zeros(GRID_CELLS, dtype=bool)
    mask[pixel] = True
    return grid.reshape(49, 49), mask.reshape(49, 49)


def fss_components(forecast: np.ndarray, observed: np.ndarray, mask: np.ndarray,
                   threshold: float, size: int) -> tuple[float, float] | None:
    """Per-case FSS (numerator, denominator); identical arithmetic to phase2c.fss_many.

    Summing these over cases and taking 1 - sum(num)/sum(den) reproduces fss_many.
    Returns None when the case contributes nothing (no valid centre or no event).
    """
    kernel = np.ones((size, size), dtype=float)
    count = convolve(mask.astype(float), kernel, mode="constant", cval=0)
    potential = convolve(np.ones(mask.shape), kernel, mode="constant", cval=0)
    centers = mask & (count >= 0.5 * potential) & (count > 0)
    if not centers.any():
        return None
    f = convolve(((forecast >= threshold) & mask).astype(float), kernel, mode="constant", cval=0) / np.maximum(count, 1)
    o = convolve(((observed >= threshold) & mask).astype(float), kernel, mode="constant", cval=0) / np.maximum(count, 1)
    denominator = float(np.sum(f[centers] ** 2 + o[centers] ** 2))
    if not denominator:
        return None
    return float(np.sum((f[centers] - o[centers]) ** 2)), denominator


def fss_from_components(components: list[tuple[float, float] | None]) -> dict:
    defined = [c for c in components if c is not None]
    denominator = sum(c[1] for c in defined)
    if not denominator:
        return {"fss": None, "case_count": 0, "reason": "no defined event neighborhoods"}
    return {"fss": float(np.clip(1 - sum(c[0] for c in defined) / denominator, 0, 1)),
            "case_count": len(defined), "reason": None}


def case_counts(forecast: np.ndarray, observed: np.ndarray, threshold: float) -> np.ndarray:
    """(hits, misses, false_alarms, n) for one case's valid cells."""
    obs, fcst = observed >= threshold, forecast >= threshold
    return np.array([np.count_nonzero(obs & fcst), np.count_nonzero(obs & ~fcst),
                     np.count_nonzero(~obs & fcst), obs.size], dtype=np.int64)


def categorical_from_counts(counts: np.ndarray) -> dict:
    """POD/FAR/CSI/ETS from pooled counts; same formulas as phase2b.event_metrics."""
    hits, misses, false_alarms, n = (int(x) for x in counts)
    random_hits = (hits + misses) * (hits + false_alarms) / n if n else 0.0
    den = {"POD": hits + misses, "FAR": hits + false_alarms, "CSI": hits + misses + false_alarms,
           "ETS": hits + misses + false_alarms - random_hits}
    num = {"POD": hits, "FAR": false_alarms, "CSI": hits, "ETS": hits - random_hits}
    return {"hits": hits, "misses": misses, "false_alarms": false_alarms, "sample_count": n,
            "observed_event_count": hits + misses, "forecast_event_count": hits + false_alarms,
            **{k: (float(num[k] / den[k]) if den[k] else None) for k in den}}


def assert_counts_match_event_metrics(observed: np.ndarray, predicted: np.ndarray, threshold: float) -> None:
    """Guard: the counts route must equal the frozen event_metrics on the same cells."""
    reference = event_metrics(observed, predicted, threshold)
    mine = categorical_from_counts(case_counts(predicted, observed, threshold))
    for key in ("POD", "FAR", "CSI", "ETS"):
        a, b = reference["metrics"][key], mine[key]
        if (a is None) != (b is None) or (a is not None and abs(a - b) > 1e-12):
            raise AssertionError(f"count-based {key} diverges from event_metrics: {a} vs {b}")


def paired_case_bootstrap(per_case: np.ndarray, statistic, *, repeats: int = 2000, seed: int = 26080) -> dict:
    """Paired case-cluster bootstrap of a scalar statistic.

    ``per_case`` has leading axis = case; all cells of a case stay together and every
    model/score is evaluated on the same resampled cases (paired). Cases within a season are
    serially correlated, so the intervals are optimistic.
    ``statistic(resampled_sum_over_cases) -> float | None``.
    """
    n = per_case.shape[0]
    if n < 2:
        return {"status": "insufficient_cases", "case_count": int(n)}
    rng = np.random.default_rng(seed)
    point = statistic(per_case.sum(axis=0))
    draws = []
    for _ in range(repeats):
        idx = rng.integers(0, n, size=n)
        value = statistic(per_case[idx].sum(axis=0))
        if value is not None and np.isfinite(value):
            draws.append(value)
    if len(draws) < repeats * 0.9:
        return {"status": "unstable", "point": point, "valid_draws": len(draws), "repeats": repeats}
    arr = np.asarray(draws)
    return {"status": "ok", "point": point, "repeats": repeats, "valid_draws": len(draws), "seed": seed,
            "interval95": [float(np.quantile(arr, 0.025)), float(np.quantile(arr, 0.975))],
            "fraction_positive": float(np.mean(arr > 0))}


class Population:
    """One population's frozen paired cells, frozen predictions and forecast-only regime assignment.

    ``cases`` are dicts with ``case_id``, ``row_start`` and ``row_count`` indexing contiguous rows of
    ``y``, ``pixel`` (flat 0..2400 grid index) and every array in ``preds``.
    """

    def __init__(self, year, cases, y, pixel, preds, regime_prob, lineage):
        self.year, self.cases, self.y, self.pixel, self.preds = year, cases, y, pixel, preds
        self.regime = np.array([int(np.argmax(p)) for p in regime_prob])
        self.lead = np.array([int(re.search(r"day([123])", c["case_id"]).group(1)) for c in cases])
        self.lineage = lineage

    def sl(self, c):
        return slice(int(c["row_start"]), int(c["row_start"]) + int(c["row_count"]))


def precompute(pop: Population):
    n = len(pop.cases)
    counts = np.zeros((n, len(THRESHOLDS), len(MODELS), 4), dtype=np.int64)
    comps = np.zeros((n, len(THRESHOLDS), len(SCALES), len(MODELS), 2), dtype=np.float64)
    defined = np.zeros((n, len(THRESHOLDS), len(SCALES), len(MODELS)), dtype=bool)
    for i, c in enumerate(pop.cases):
        sl = pop.sl(c)
        obs, mask = to_field(pop.y[sl], pop.pixel[sl])
        for mi, m in enumerate(MODELS):
            fc, _ = to_field(pop.preds[m][sl], pop.pixel[sl])
            for ti, (_, thr) in enumerate(THRESHOLDS):
                counts[i, ti, mi] = case_counts(pop.preds[m][sl], pop.y[sl], thr)
                for si, size in enumerate(SCALES):
                    r = fss_components(fc, obs, mask, thr, size)
                    if r is not None:
                        comps[i, ti, si, mi], defined[i, ti, si, mi] = r, True
    return counts, comps, defined


def _fss(comps, defined, idx, ti, si, mi):
    return fss_from_components([tuple(comps[i, ti, si, mi]) if defined[i, ti, si, mi] else None for i in idx])


def group_block(pop, counts, comps, defined, idx) -> dict:
    idx = list(idx)
    block = {"case_count": len(idx), "cell_count": int(sum(pop.cases[i]["row_count"] for i in idx)),
             "continuous": {}, "categorical": {}, "fss": {}}
    if not idx:
        return block
    rows = np.concatenate([np.arange(pop.sl(pop.cases[i]).start, pop.sl(pop.cases[i]).stop) for i in idx])
    for mi, m in enumerate(MODELS):
        block["continuous"][m] = continuous_metrics(pop.y[rows], pop.preds[m][rows])
    for ti, (name, thr) in enumerate(THRESHOLDS):
        block["categorical"][name] = {m: categorical_from_counts(counts[idx, ti, mi].sum(axis=0))
                                      for mi, m in enumerate(MODELS)}
        block["fss"][name] = {}
        for si, size in enumerate(SCALES):
            matched = [i for i in idx if defined[i, ti, si].all()]
            block["fss"][name][str(size)] = {
                "all_cases": {m: _fss(comps, defined, idx, ti, si, mi) for mi, m in enumerate(MODELS)},
                "matched_all_models": {"case_count": len(matched),
                                       **{m: _fss(comps, defined, matched, ti, si, mi)["fss"] for mi, m in enumerate(MODELS)}}}
    return block


def bootstrap_block(counts, comps, idx) -> dict:
    idx = np.asarray(list(idx))
    out = {}
    mi = {m: k for k, m in enumerate(MODELS)}
    for ti, (name, _) in enumerate(THRESHOLDS):
        out[name] = {}
        for a, b in BOOT_PAIRS:
            key = f"{a}_minus_{b}"

            def csi(total, a=a, b=b):
                def one(m):
                    h, ms, fa, _ = total[mi[m]]
                    return h / (h + ms + fa) if (h + ms + fa) else np.nan
                return one(a) - one(b)
            out[name][key] = {"CSI": paired_case_bootstrap(counts[idx, ti], csi)}
            for si, size in enumerate(SCALES):
                if size not in BOOT_SCALES:
                    continue

                def fss_diff(total, a=a, b=b):
                    def one(m):
                        num, den = total[mi[m]]
                        return float(np.clip(1 - num / den, 0, 1)) if den else np.nan
                    return one(a) - one(b)
                out[name][key][f"FSS_{size}x{size}"] = paired_case_bootstrap(comps[idx, ti, si], fss_diff)
    return out


def analyse(pop: Population) -> dict:
    counts, comps, defined = precompute(pop)
    # Guard: count-based categorical scores must equal the frozen event_metrics.
    for ti, (_, thr) in enumerate(THRESHOLDS):
        for m in MODELS:
            assert_counts_match_event_metrics(pop.y, pop.preds[m], thr)
    n = len(pop.cases)
    result = {"year": pop.year, "case_count": n,
              "overall": group_block(pop, counts, comps, defined, range(n)),
              "by_predicted_regime": {}, "by_lead_day": {},
              "bootstrap": {"overall": bootstrap_block(counts, comps, range(n)), "by_predicted_regime": {}}}
    for k, name in enumerate(REGIMES):
        idx = [i for i in range(n) if pop.regime[i] == k]
        result["by_predicted_regime"][name] = group_block(pop, counts, comps, defined, idx)
        result["bootstrap"]["by_predicted_regime"][name] = bootstrap_block(counts, comps, idx) if len(idx) > 1 else None
    for day in (1, 2, 3):
        result["by_lead_day"][f"day{day}"] = group_block(pop, counts, comps, defined, [i for i in range(n) if pop.lead[i] == day])
    return result
