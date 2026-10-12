"""Pure, same-cell 2026 Track B scoring rules; no data access or fitting."""

from __future__ import annotations

from collections import defaultdict

import numpy as np

from backend.app.ml.phase2c import probability_metrics
from backend.app.ml.verification_extra import case_counts, categorical_from_counts, fss_components, fss_from_components

MODELS = ("M0", "M1", "M2", "M3", "M4")
EVENTS = {"heavy": 64.5, "very_heavy": 115.6}
SCALES = (1, 3, 5, 9)
LEADS = ("day1_24h", "day2_24h", "day3_24h")


def validate_case(case: dict) -> None:
    """Require one 49x49 paired grid and preserve missing reference cells."""
    if case["lead"] not in LEADS or len(case["cycle"]) != 8 or not case["cycle"].isdigit():
        raise ValueError("case identity or lead invalid")
    obs, mask = np.asarray(case["observed"]), np.asarray(case["valid_mask"], dtype=bool)
    if obs.shape != (49, 49) or mask.shape != obs.shape or not mask.any() or not np.isfinite(obs[mask]).all() or np.any(obs[mask] < 0):
        raise ValueError("observed grid or common mask invalid")
    if set(case["rainfall"]) != set(MODELS):
        raise ValueError("all five frozen rainfall models are required")
    for model in MODELS:
        values = np.asarray(case["rainfall"][model])
        if values.shape != obs.shape or not np.isfinite(values[mask]).all() or np.any(values[mask] < 0):
            raise ValueError(f"invalid forecast rainfall grid: {model}")
    for name in ("heavy_probability", "very_heavy_probability"):
        values = np.asarray(case[name])
        if values.shape != obs.shape or not np.isfinite(values[mask]).all() or np.any((values[mask] < 0) | (values[mask] > 1)):
            raise ValueError(f"invalid forecast probability grid: {name}")
    if int(case["nested_probability_violating_cells"]) < 0:
        raise ValueError("negative probability-order count")
    regime = np.asarray(case["regime_probability"])
    if regime.shape != (3,) or not np.isfinite(regime).all() or np.any((regime < 0) | (regime > 1)) or not np.isclose(regime.sum(), 1.0, atol=1e-8):
        raise ValueError("invalid forecast regime output")
    if case["version_stratum"] not in ("before_announced_change", "after_announced_change"):
        raise ValueError("invalid announced-version stratum")
    actual_violations = int(np.count_nonzero(case["very_heavy_probability"] > case["heavy_probability"] + 1e-12))
    if actual_violations != int(case["nested_probability_violating_cells"]):
        raise ValueError("probability-order count differs from archived arrays")


def _metrics(cases: list[dict], indices: list[int]) -> dict:
    out = {"case_count": len(indices), "initialization_dates": len({cases[i]["cycle"] for i in indices}),
           "paired_cells": int(sum(np.asarray(cases[i]["valid_mask"]).sum() for i in indices)),
           "deterministic": {}, "fss": {}}
    if not indices:
        return out
    for model in MODELS:
        n = error = square = 0.0
        counts = {event: np.zeros(4, dtype=np.int64) for event in EVENTS}
        for i in indices:
            c = cases[i]
            mask = c["valid_mask"]
            obs = c["observed"][mask].astype(np.float64)
            fc = c["rainfall"][model][mask].astype(np.float64)
            delta = fc - obs
            n += len(delta)
            error += float(delta.sum())
            square += float(np.dot(delta, delta))
            for event, threshold in EVENTS.items():
                counts[event] += case_counts(fc, obs, threshold)
        out["deterministic"][model] = {"rmse_mm": float(np.sqrt(square / n)), "bias_mm": error / n,
                                         **{event: categorical_from_counts(counts[event]) for event in EVENTS}}
    for event, threshold in EVENTS.items():
        out["fss"][event] = {}
        for scale in SCALES:
            per_model = {}
            for model in MODELS:
                components = [fss_components(cases[i]["rainfall"][model], cases[i]["observed"],
                                             cases[i]["valid_mask"], threshold, scale) for i in indices]
                per_model[model] = fss_from_components(components)
            out["fss"][event][str(scale)] = per_model
    return out


def _bootstrap(cases: list[dict], left: str, right: str, *, repeats: int, seed: int) -> dict:
    """Paired initialization-date bootstrap; both models and all leads share draws."""
    by_date: dict[str, list[dict]] = defaultdict(list)
    for c in cases:
        by_date[c["cycle"]].append(c)
    dates = sorted(by_date)
    if len(dates) < 2:
        return {"status": "insufficient_dates", "date_count": len(dates)}
    sums = np.zeros((len(dates), 2, 4), dtype=np.float64)
    for di, day in enumerate(dates):
        for c in by_date[day]:
            mask = c["valid_mask"]
            obs = c["observed"][mask]
            for mi, name in enumerate((left, right)):
                fc = c["rainfall"][name][mask]
                sums[di, mi] += case_counts(fc, obs, EVENTS["heavy"])

    def difference(total: np.ndarray) -> float | None:
        values = []
        for row in total:
            h, miss, fa, _ = row
            den = h + miss + fa
            if den == 0:
                return None
            values.append(h / den)
        return float(values[0] - values[1])

    point = difference(sums.sum(axis=0))
    rng = np.random.default_rng(seed)
    draws = []
    for _ in range(repeats):
        idx = rng.integers(0, len(dates), size=len(dates))
        value = difference(sums[idx].sum(axis=0))
        if value is not None:
            draws.append(value)
    if point is None or len(draws) < 0.9 * repeats:
        return {"status": "insufficient_event_support", "date_count": len(dates), "valid_draws": len(draws)}
    return {"status": "ok", "point": point, "interval97_5": [float(np.quantile(draws, 0.0125)), float(np.quantile(draws, 0.9875))],
            "date_count": len(dates), "repeats": repeats, "seed": seed, "valid_draws": len(draws)}


def score_cases(cases: list[dict], *, climatology: dict[str, float], probability_cutoffs: dict[str, float],
                repeats: int = 2000, seed: int = 26080) -> dict:
    if not cases or repeats < 10:
        raise ValueError("nonempty cases and at least ten bootstrap replicates required")
    seen = set()
    for c in cases:
        validate_case(c)
        key = (c["cycle"], c["lead"])
        if key in seen:
            raise ValueError("duplicate cycle/lead")
        seen.add(key)
    overall = _metrics(cases, list(range(len(cases))))
    by_lead = {lead: _metrics(cases, [i for i, c in enumerate(cases) if c["lead"] == lead]) for lead in LEADS}
    by_announced_boundary = {label: _metrics(cases, [i for i, c in enumerate(cases) if c["version_stratum"] == label])
                             for label in ("before_announced_change", "after_announced_change")}
    regime_groups = {str(i): _metrics(cases, [j for j, c in enumerate(cases) if int(np.argmax(c["regime_probability"])) == i]) for i in range(3)}
    coherent = [c for c in cases if c["nested_probability_violating_cells"] == 0]
    probability = {"eligible_case_count": len(coherent), "withheld_incoherent_case_count": len(cases) - len(coherent), "events": {}}
    for event, threshold in EVENTS.items():
        if not 0 <= climatology[event] <= 1 or not 0 <= probability_cutoffs[event] <= 1:
            raise ValueError("invalid frozen probability climatology/cutoff")
        obs = np.concatenate([(c["observed"][c["valid_mask"]] >= threshold).astype(np.uint8) for c in coherent]) if coherent else np.array([], dtype=np.uint8)
        pred = np.concatenate([c[f"{event}_probability"][c["valid_mask"]] for c in coherent]) if coherent else np.array([], dtype=np.float64)
        probability["events"][event] = probability_metrics(obs, pred, probability_cutoffs[event], climatology[event])
    primary = _bootstrap(cases, "M4", "M2", repeats=repeats, seed=seed)
    secondary = _bootstrap(cases, "M3", "M2", repeats=repeats, seed=seed + 1)
    event_dates = len({c["cycle"] for c in cases if np.any(c["observed"][c["valid_mask"]] >= EVENTS["heavy"])})
    m4, m2 = overall["deterministic"]["M4"], overall["deterministic"]["M2"]
    gates = {"heavy_event_bearing_dates_at_least_30": event_dates >= 30,
             "M4_heavy_CSI_adjusted_lower_gt_zero": primary.get("status") == "ok" and primary["interval97_5"][0] > 0,
             "M4_minus_M2_RMSE_at_most_0_2_mm": m4["rmse_mm"] - m2["rmse_mm"] <= 0.2,
             "M4_absolute_bias_at_most_1_5_mm": abs(m4["bias_mm"]) <= 1.5}
    return {"overall": overall, "by_lead": by_lead, "by_announced_boundary": by_announced_boundary,
            "by_forecast_regime_argmax": regime_groups, "probability": probability,
            "paired_date_bootstrap": {"M4_minus_M2_heavy_CSI": primary, "M3_minus_M2_heavy_CSI": secondary},
            "heavy_event_bearing_initialization_dates": event_dates, "promotion_gates": gates,
            "regime_promotion_eligible": all(gates.values()),
            "caveats": ["Forecast-regime classes are not independent expert truth", "Version strata are based on an announced boundary and are seasonally confounded", "Probability metrics exclude every lead with nested-event incoherence", "Date bootstrap preserves within-date cells and leads but not serial dependence across dates"]}
