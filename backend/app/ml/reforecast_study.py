"""Pure rules of the reforecast heavy-rain study (protocol reforecast_study_protocol_v1.json, docs/142): the configuration grid, the validation-only selection rule, the sealed-test decision
rules and the regime routing. No data access and no model library: the training script calls these so the rules are tested on their own.
"""

from __future__ import annotations

from itertools import product

import numpy as np

from backend.app.ml.forecast_regimes import FEATURE_NAMES as REGIME_FEATURES, _active_score, _low_score
from backend.app.ml.geoaware import BASE_FEATURES, STATIC_FEATURES, event_weights, pooled_metrics

__all__ = ["ARMS", "BASE_FEATURES", "STATIC_FEATURES", "TRAIN_YEARS", "VALIDATION_YEARS", "SEALED_YEARS", "CAPS", "configurations", "row_weights", "eligible", "select_configuration",
           "decide_candidate", "regime_adds_value", "EXCEED_THRESHOLDS", "exceedance_configurations", "best_tau", "exceedance_metrics", "select_exceedance", "fit_pseudo_labeler", "pseudo_labels", "route_hard", "route_soft", "pooled_metrics"]

TRAIN_YEARS = tuple(range(2000, 2012))
VALIDATION_YEARS = (2012, 2013)
SEALED_YEARS = (2014, 2015, 2016)
CAPS = (None, 4.0, 8.0)
G2_MAX_ABS_BIAS_MM = 1.5
MAX_HEAVY_FREQUENCY_BIAS = 2.0
MAX_VERY_HEAVY_FREQUENCY_BIAS = 3.0
ARMS = {"B0": list(BASE_FEATURES), "B1": list(BASE_FEATURES) + list(STATIC_FEATURES)}


def configurations() -> list[dict]:
    """The 24 configurations in the frozen order: objective, event-weight cap, depth, rounds."""
    return [{"objective": o, "cap": c, "max_depth": d, "n_estimators": n} for o, c, d, n in product(["reg:squarederror", "reg:tweedie"], CAPS, [4, 6], [200, 350])]


def row_weights(y: np.ndarray, cap: float | None) -> np.ndarray | None:
    """Training-row weights from the observed rainfall of a TRAINING row (never used at inference): none, or min(cap, 1 + y / 64.5)."""
    return None if cap is None else event_weights(y, cap)


def eligible(metrics: dict, raw: dict) -> bool:
    """Validation eligibility: RMSE no worse than Raw, heavy CSI at least Raw's, |bias| within 1.5 mm, no gross over-forecast of heavy or very-heavy rain. An undefined quantity never passes."""
    h, v = metrics["heavy"], metrics["very_heavy"]
    if h["csi"] is None or v["frequency_bias"] is None or h["frequency_bias"] is None:
        return False
    return bool(metrics["rmse_mm"] <= raw["rmse_mm"] and raw["heavy"]["csi"] is not None and h["csi"] >= raw["heavy"]["csi"] and abs(metrics["bias_mm"]) <= G2_MAX_ABS_BIAS_MM
                and h["frequency_bias"] <= MAX_HEAVY_FREQUENCY_BIAS and v["frequency_bias"] <= MAX_VERY_HEAVY_FREQUENCY_BIAS)


def _score(metrics: dict) -> float:
    h, v = metrics["heavy"]["csi"], metrics["very_heavy"]["csi"]
    return float("-inf") if h is None or v is None else float((h + v) / 2)


def select_configuration(results: list[dict], raw: dict) -> dict | None:
    """Among eligible configurations the highest mean of heavy and very-heavy CSI on the VALIDATION years; ties go to the lower RMSE, then the earlier grid position. None if nothing is eligible.

    ``results`` entries carry ``grid_index`` and ``validation`` (pooled metrics over the validation years)."""
    pool = [r for r in results if eligible(r["validation"], raw)]
    if not pool:
        return None
    return max(pool, key=lambda r: (_score(r["validation"]), -r["validation"]["rmse_mm"], -r["grid_index"]))


def _excludes(entry: dict | None, positive: bool) -> bool:
    return bool(entry and entry.get("status") == "ok" and entry["excludes_zero"] and (entry["point"] > 0) == positive)


def decide_candidate(vs_raw: dict, test: dict) -> dict:
    """Sealed-test decision for one candidate against Raw. ``vs_raw`` holds paired-bootstrap entries for rmse (95 percent) and heavy_csi / very_heavy_csi (97.5 percent); ``test`` the pooled test metrics.

    IMPROVES_RMSE, IMPROVES_HEAVY and IMPROVES_VERY_HEAVY each need a point change in the right direction whose interval excludes zero; BIAS_OK needs |bias| <= 1.5 mm and no gross over-forecast."""
    h, v = test["heavy"], test["very_heavy"]
    out = {"IMPROVES_RMSE": _excludes(vs_raw.get("rmse"), False), "IMPROVES_HEAVY": _excludes(vs_raw.get("heavy_csi"), True), "IMPROVES_VERY_HEAVY": _excludes(vs_raw.get("very_heavy_csi"), True),
           "BIAS_OK": bool(abs(test["bias_mm"]) <= G2_MAX_ABS_BIAS_MM and h["frequency_bias"] is not None and h["frequency_bias"] <= MAX_HEAVY_FREQUENCY_BIAS
                           and v["frequency_bias"] is not None and v["frequency_bias"] <= MAX_VERY_HEAVY_FREQUENCY_BIAS)}
    flags = [k for k in ("IMPROVES_RMSE", "IMPROVES_HEAVY", "IMPROVES_VERY_HEAVY") if out[k]]
    out["improvements"] = flags
    out["tier"] = ("FULL" if len(flags) == 3 and out["BIAS_OK"] else "RMSE_AND_HEAVY" if out["IMPROVES_RMSE"] and out["IMPROVES_HEAVY"] and out["BIAS_OK"]
                   else "PARTIAL" if flags and out["BIAS_OK"] else "NONE")
    return out


def regime_adds_value(regime_vs_global: dict) -> dict:
    """Regime-aware candidate against the best non-regime candidate: adds value only if heavy-rain CSI improves with an interval excluding zero (97.5 percent) and RMSE is not worse by more than 0.2 mm."""
    heavy = _excludes(regime_vs_global.get("heavy_csi"), True)
    rmse = regime_vs_global.get("rmse")
    not_worse = bool(rmse and rmse.get("status") == "ok" and rmse["interval95"][1] <= 0.2)
    return {"adds_value": bool(heavy and not_worse), "heavy_csi_improves": heavy, "rmse_not_worse_than_0_2_mm": not_worse}


def fit_pseudo_labeler(regime_features: np.ndarray) -> dict:
    """Forecast-only pseudo-labelling rule fitted on the TRAINING cases (the Phase 2A method: low-pressure score upper quartile, active score median of the rest). Labels: 0 active, 1 break/weak, 2 low/depression."""
    X = np.asarray(regime_features, dtype=np.float64)
    if X.ndim != 2 or X.shape[1] != len(REGIME_FEATURES) or not np.isfinite(X).all():
        raise ValueError("invalid regime inputs")
    mean, scale = X.mean(axis=0), X.std(axis=0)
    scale[scale == 0] = 1
    z = (X - mean) / scale
    low = _low_score(z)
    low_threshold = float(np.quantile(low, 0.75))
    return {"mean": mean.tolist(), "scale": scale.tolist(), "low_threshold": low_threshold, "active_threshold": float(np.median(_active_score(z)[low < low_threshold]))}


def pseudo_labels(regime_features: np.ndarray, rule: dict) -> np.ndarray:
    z = (np.asarray(regime_features, dtype=np.float64) - np.asarray(rule["mean"])) / np.asarray(rule["scale"])
    low, active = _low_score(z), _active_score(z)
    out = np.full(len(z), 1, dtype=np.int64)
    out[low >= rule["low_threshold"]] = 2
    out[(low < rule["low_threshold"]) & (active >= rule["active_threshold"])] = 0
    return out


def route_hard(case_probabilities: np.ndarray, expert_predictions: dict[int, np.ndarray], rows_per_case: np.ndarray) -> np.ndarray:
    """M3-style: every row of a case takes the expert of the case's most probable regime."""
    labels = np.repeat(np.argmax(case_probabilities, axis=1), rows_per_case)
    out = np.empty(len(labels), dtype=np.float32)
    for r, pred in expert_predictions.items():
        out[labels == r] = pred[labels == r]
    return out


def route_soft(case_probabilities: np.ndarray, expert_predictions: dict[int, np.ndarray], rows_per_case: np.ndarray) -> np.ndarray:
    """M4-style: the probability-weighted mixture of the experts, never negative."""
    expanded = np.repeat(case_probabilities, rows_per_case, axis=0)
    return np.maximum(0.0, sum(expanded[:, r] * pred for r, pred in expert_predictions.items())).astype(np.float32)


# ---------------------------------------------------------------------------
# Amendment 2: exceedance classifiers (docs/142). The regression arms under-forecast very-heavy rain on the validation years (frequency bias about 0.1), so the
# categorical question is also asked of a probability model: P(rain >= threshold), turned into a yes/no forecast at a validation-fixed probability threshold.
# ---------------------------------------------------------------------------

EXCEED_THRESHOLDS = {"heavy": 64.5, "very_heavy": 115.6}
FREQUENCY_BIAS_BOUNDS = {"heavy": (0.5, MAX_HEAVY_FREQUENCY_BIAS), "very_heavy": (0.5, MAX_VERY_HEAVY_FREQUENCY_BIAS)}


def exceedance_configurations() -> list[dict]:
    """The 8 configurations in the frozen order: depth, rounds, positive-class weighting (none or sqrt of the training imbalance)."""
    return [{"max_depth": d, "n_estimators": n, "pos_weight": w} for d, n, w in product([4, 6], [200, 350], ["none", "sqrt_balance"])]


def exceedance_metrics(prob: np.ndarray, y: np.ndarray, tau: float, threshold: float) -> dict:
    """Categorical scores of the forecast ``prob >= tau`` against the observed event ``y >= threshold`` (float32 comparison, as everywhere else)."""
    observed = np.asarray(y).astype(np.float32) >= np.float32(threshold)
    forecast = np.asarray(prob) >= tau
    hits, misses, false_alarms = int(np.count_nonzero(observed & forecast)), int(np.count_nonzero(observed & ~forecast)), int(np.count_nonzero(~observed & forecast))
    return {"tau": float(tau), "hits": hits, "misses": misses, "false_alarms": false_alarms, "observed_events": hits + misses,
            "csi": hits / (hits + misses + false_alarms) if hits + misses + false_alarms else None, "frequency_bias": (hits + false_alarms) / (hits + misses) if hits + misses else None}


def best_tau(prob: np.ndarray, y: np.ndarray, threshold: float, bounds: tuple[float, float], candidates: int = 400) -> dict | None:
    """The probability threshold that maximises CSI on the data given, among ``candidates`` score quantiles, subject to a frequency bias inside ``bounds``; ties go to the larger tau. None if no tau qualifies."""
    prob = np.asarray(prob, dtype=np.float64)
    taus = np.unique(np.quantile(prob, np.linspace(0.5, 0.99999, candidates)))
    best = None
    for tau in taus:
        m = exceedance_metrics(prob, y, float(tau), threshold)
        if m["csi"] is None or m["frequency_bias"] is None or not bounds[0] <= m["frequency_bias"] <= bounds[1]:
            continue
        if best is None or m["csi"] >= best["csi"]:
            best = m
    return best


def select_exceedance(results: list[dict], raw_csi: float | None) -> dict | None:
    """Among configurations whose validation tau qualified and whose CSI is at least Raw's, the highest validation CSI; ties go to the earlier grid position. None if nothing qualifies.

    ``results`` entries carry ``grid_index`` and ``validation`` (the :func:`best_tau` metrics, or None)."""
    pool = [r for r in results if r["validation"] is not None and raw_csi is not None and r["validation"]["csi"] >= raw_csi]
    return max(pool, key=lambda r: (r["validation"]["csi"], -r["grid_index"])) if pool else None
