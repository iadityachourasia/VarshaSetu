"""District-level verification of the frozen Track B models (protocol v1, docs/112). Pure and read-only.

Nothing here trains, tunes or selects a model. It re-aggregates already-frozen per-case grids with the pinned
Phase 2C district weights (the same weights and valid-cell rule as docs/107 and docs/111) and scores them under the
event definitions fixed in ``district_verification_protocol_v1.json`` BEFORE any result existed.
"""

from __future__ import annotations

import numpy as np

try:
    from backend.app.ml.verification_extra import categorical_from_counts, paired_case_bootstrap
except ModuleNotFoundError:
    from app.ml.verification_extra import categorical_from_counts, paired_case_bootstrap

THRESHOLDS = (("heavy", 64.5), ("very_heavy", 115.6))
DEFINITIONS = ("E1", "E2", "E3")
MODELS = ("M0", "M1", "M2", "M3", "M4")
CORRECTED = ("M1", "M2", "M3", "M4")
FIELDS = ("obs",) + MODELS
AREA_FRACTION = 0.25
MIN_CELLS = 5
MIN_EVENTS = 30
MIN_CASES = 30
BAND_EDGES = (14.0, 18.0)
BAND_NAMES = ("10-14N", "14-18N", "18-22N")
CONTRASTS = (("M1", "M0"), ("M2", "M0"), ("M3", "M0"), ("M4", "M0"), ("M3", "M2"), ("M4", "M2"), ("M3", "M4"))
PER_DISTRICT_DEFINITIONS = ("E1", "E2")
GRID_CELLS = 49 * 49


def latitude_band(latitude: float) -> int:
    """Band index 0/1/2 for 10-14N / 14-18N / 18-22N; a centroid exactly on an edge belongs to the northern band."""
    return int(latitude >= BAND_EDGES[0]) + int(latitude >= BAND_EDGES[1])


def case_district_stats(weights: np.ndarray, fields: dict[str, np.ndarray]) -> dict[str, np.ndarray]:
    """Per-district statistics for ONE case with the shared weights and validity rule.

    ``fields`` maps ``obs`` and ``M0``..``M4`` to flat 2401-vectors that are NaN off the case's paired cells. A cell is valid
    only if EVERY field is finite there (all models share the same paired cells). Returns, per district: valid-cell count,
    and for each field the area-weighted mean, and for each threshold the area-weighted fraction >= threshold and the
    any-cell flag. Districts without a valid cell get cells == 0 (callers must not use their values).
    """
    arrays = {k: np.asarray(v, dtype=float).ravel() for k, v in fields.items()}
    if weights.ndim != 2 or weights.shape[1] != GRID_CELLS or any(a.shape != (GRID_CELLS,) for a in arrays.values()):
        raise ValueError("district statistics shape mismatch")
    valid = np.logical_and.reduce([np.isfinite(a) for a in arrays.values()])
    active = (weights > 0) & valid[None, :]
    weighted = np.where(active, weights.astype(float), 0.0)
    total = weighted.sum(axis=1)
    q = np.divide(weighted, total[:, None], out=np.zeros_like(weighted), where=total[:, None] > 0)
    out: dict[str, np.ndarray] = {"cells": active.sum(axis=1)}
    for name, values in arrays.items():
        clean = np.where(valid, values, 0.0)
        out[f"mean:{name}"] = q @ clean
        for key, threshold in THRESHOLDS:
            ge = (clean >= threshold) & valid
            out[f"frac:{name}:{key}"] = q @ ge.astype(float)
            out[f"any:{name}:{key}"] = (active & ge[None, :]).any(axis=1)
    return out


class Stack:
    """Case-stacked district statistics: every array has leading axes [case, district]."""

    def __init__(self, per_case: list[dict[str, np.ndarray]], case_ids: list[str], district_ids: list[str],
                 district_names: list[str], latitudes: np.ndarray, regime_by_case: np.ndarray):
        self.case_ids, self.district_ids, self.district_names = case_ids, district_ids, district_names
        self.cells = np.stack([s["cells"] for s in per_case])
        self.mean = {n: np.stack([s[f"mean:{n}"] for s in per_case]) for n in FIELDS}
        self.frac = {(n, k): np.stack([s[f"frac:{n}:{k}"] for s in per_case]) for n in FIELDS for k, _ in THRESHOLDS}
        self.any = {(n, k): np.stack([s[f"any:{n}:{k}"] for s in per_case]) for n in FIELDS for k, _ in THRESHOLDS}
        self.lead = np.array([int(cid.split("_day")[1][0]) for cid in case_ids])
        self.regime = np.asarray(regime_by_case, dtype=int)
        self.band = np.array([latitude_band(float(x)) for x in latitudes])
        positive = np.where(self.cells > 0, self.cells, np.nan)
        self.median_cells = np.array([float(np.nanmedian(positive[:, d])) if np.isfinite(positive[:, d]).any() else 0.0
                                      for d in range(self.cells.shape[1])])
        self.kept = self.median_cells >= MIN_CELLS
        self.included = (self.cells >= MIN_CELLS) & self.kept[None, :]

    def event(self, definition: str, name: str, threshold_key: str, threshold: float) -> np.ndarray:
        if definition == "E1":
            return self.any[(name, threshold_key)]
        if definition == "E2":
            return self.frac[(name, threshold_key)] >= AREA_FRACTION
        if definition == "E3":
            return self.mean[name] >= threshold
        raise ValueError(definition)


def _counts(stack: Stack, definition: str, model: str, key: str, threshold: float, mask: np.ndarray) -> np.ndarray:
    use = stack.included & mask
    obs = stack.event(definition, "obs", key, threshold)[use]
    fc = stack.event(definition, model, key, threshold)[use]
    return np.array([np.count_nonzero(obs & fc), np.count_nonzero(obs & ~fc), np.count_nonzero(~obs & fc), obs.size], dtype=np.int64)


def _continuous(stack: Stack, model: str, mask: np.ndarray) -> dict:
    use = stack.included & mask
    error = (stack.mean[model] - stack.mean["obs"])[use]
    if error.size == 0:
        return {"pairs": 0, "rmse_mm": None, "mae_mm": None, "bias_mm": None}
    return {"pairs": int(error.size), "rmse_mm": float(np.sqrt(np.mean(error ** 2))), "mae_mm": float(np.mean(np.abs(error))),
            "bias_mm": float(np.mean(error))}


def _groups(stack: Stack, regime_names: tuple[str, ...]) -> dict[str, dict[str, np.ndarray]]:
    n_cases, n_districts = stack.cells.shape
    full = np.ones((n_cases, n_districts), dtype=bool)
    return {
        "pooled": {"all": full},
        "by_lead": {f"day{d}": np.broadcast_to((stack.lead == d)[:, None], full.shape) for d in (1, 2, 3)},
        "by_regime": {name: np.broadcast_to((stack.regime == i)[:, None], full.shape) for i, name in enumerate(regime_names)},
        "by_region": {name: np.broadcast_to((stack.band == i)[None, :], full.shape) for i, name in enumerate(BAND_NAMES)},
    }


def _bootstrap_contrasts(stack: Stack, repeats: int, seed: int) -> dict:
    out: dict = {"categorical": {}, "continuous": {}}
    n_cases = stack.cells.shape[0]
    full = np.ones_like(stack.included)
    for definition in DEFINITIONS:
        out["categorical"][definition] = {}
        for key, threshold in THRESHOLDS:
            per_case = np.zeros((n_cases, len(MODELS), 4))
            for ci in range(n_cases):
                one = np.zeros_like(full)
                one[ci] = True
                for mi, model in enumerate(MODELS):
                    per_case[ci, mi] = _counts(stack, definition, model, key, threshold, one)
            block = {}
            for a, b in CONTRASTS:
                def csi_diff(total, a=a, b=b):
                    def csi(model):
                        h, m, f, _ = total[MODELS.index(model)]
                        return h / (h + m + f) if (h + m + f) else np.nan
                    return csi(a) - csi(b)
                block[f"{a}_minus_{b}"] = {"CSI": paired_case_bootstrap(per_case, csi_diff, repeats=repeats, seed=seed)}
            out["categorical"][definition][key] = block
    # continuous: mean of (|err_b| - |err_a|) over included pairs; positive = a is closer to IMD than b
    abs_err = {m: np.abs(stack.mean[m] - stack.mean["obs"]) for m in MODELS}
    for a, b in CONTRASTS:
        diff = np.where(stack.included, abs_err[b] - abs_err[a], 0.0)
        per_case = np.stack([diff.sum(axis=1), stack.included.sum(axis=1).astype(float)], axis=1)
        out["continuous"][f"{a}_vs_{b}"] = paired_case_bootstrap(
            per_case, lambda total: float(total[0] / total[1]) if total[1] else None, repeats=repeats, seed=seed)
    return out


def _district_improvement(stack: Stack, repeats: int, seed: int) -> dict[str, dict[str, np.ndarray]]:
    """Per-district mean improvement vs Raw with a paired whole-case bootstrap interval (one shared resample per draw)."""
    n_cases, n_districts = stack.cells.shape
    abs_raw = np.abs(stack.mean["M0"] - stack.mean["obs"])
    imp = {m: np.where(stack.included, abs_raw - np.abs(stack.mean[m] - stack.mean["obs"]), np.nan) for m in CORRECTED}
    rng = np.random.default_rng(seed)
    draws = rng.integers(0, n_cases, size=(repeats, n_cases))
    result: dict[str, dict[str, np.ndarray]] = {}
    for model in CORRECTED:
        values = imp[model]
        point_n = np.sum(~np.isnan(values), axis=0)
        point = np.where(point_n > 0, np.nansum(values, axis=0) / np.maximum(point_n, 1), np.nan)
        samples = np.empty((repeats, n_districts))
        for b in range(repeats):
            chosen = values[draws[b]]
            n = np.sum(~np.isnan(chosen), axis=0)
            samples[b] = np.where(n > 0, np.nansum(chosen, axis=0) / np.maximum(n, 1), np.nan)
        result[model] = {"point": point, "n": point_n, "low": np.nanquantile(samples, 0.025, axis=0), "high": np.nanquantile(samples, 0.975, axis=0)}
    return result


def _status(point: float, low: float, high: float) -> str:
    if not (np.isfinite(point) and np.isfinite(low) and np.isfinite(high)):
        return "undefined"
    if point > 0 and low > 0:
        return "improved"
    if point < 0 and high < 0:
        return "worsened"
    return "indeterminate"


def analyse_districts(stack: Stack, regime_names: tuple[str, ...], *, repeats: int = 2000, seed: int = 26080) -> dict:
    groups = _groups(stack, regime_names)
    result: dict = {
        "inclusion": {
            "cases": len(stack.case_ids), "districts_total": len(stack.district_ids), "districts_included": int(stack.kept.sum()),
            "districts_excluded": [{"district_id": stack.district_ids[i], "district_name": stack.district_names[i],
                                    "median_valid_cells": float(stack.median_cells[i])} for i in np.flatnonzero(~stack.kept)],
            "district_case_pairs": int(stack.included.sum()), "min_valid_cells": MIN_CELLS,
        },
        "continuous": {kind: {name: {m: _continuous(stack, m, mask) for m in MODELS} for name, mask in members.items()}
                       for kind, members in groups.items()},
        "categorical": {},
    }
    for definition in DEFINITIONS:
        result["categorical"][definition] = {}
        for key, threshold in THRESHOLDS:
            result["categorical"][definition][key] = {
                kind: {name: {m: categorical_from_counts(_counts(stack, definition, m, key, threshold, mask)) for m in MODELS}
                       for name, mask in members.items()} for kind, members in groups.items()}
    result["contrasts"] = _bootstrap_contrasts(stack, repeats, seed)

    improvement = _district_improvement(stack, repeats, seed)
    districts = []
    for d in np.flatnonzero(stack.kept):
        n_cases = int(stack.included[:, d].sum())
        entry: dict = {"district_id": stack.district_ids[d], "district_name": stack.district_names[d], "region": BAND_NAMES[int(stack.band[d])],
                       "included_cases": n_cases, "median_valid_cells": float(stack.median_cells[d])}
        one = np.zeros_like(stack.included)
        one[:, d] = True
        entry["continuous"] = {m: _continuous(stack, m, one) for m in MODELS} if n_cases >= MIN_CASES else "insufficient_support"
        entry["improvement"] = {m: {"mean_improvement_mm": float(improvement[m]["point"][d]), "interval95": [float(improvement[m]["low"][d]), float(improvement[m]["high"][d])],
                                    "status": _status(float(improvement[m]["point"][d]), float(improvement[m]["low"][d]), float(improvement[m]["high"][d]))}
                                for m in CORRECTED} if n_cases >= MIN_CASES else "insufficient_support"
        entry["categorical"] = {}
        for definition in PER_DISTRICT_DEFINITIONS:
            entry["categorical"][definition] = {}
            for key, threshold in THRESHOLDS:
                observed = int(np.count_nonzero(stack.event(definition, "obs", key, threshold)[stack.included & one]))
                supported = observed >= MIN_EVENTS
                entry["categorical"][definition][key] = {
                    "observed_events": observed, "status": "supported" if supported else "insufficient_support",
                    "models": {m: categorical_from_counts(_counts(stack, definition, m, key, threshold, one)) for m in MODELS} if supported else None}
        districts.append(entry)
    result["districts"] = districts

    tested = [e for e in districts if e["improvement"] != "insufficient_support"]
    result["improved_worsened"] = {
        m: {"tested_districts": len(tested),
            **{s: sum(1 for e in tested if e["improvement"][m]["status"] == s) for s in ("improved", "worsened", "indeterminate", "undefined")},
            "expected_by_chance_total": round(0.05 * len(tested), 1), "expected_by_chance_per_direction": round(0.025 * len(tested), 1)}
        for m in CORRECTED}
    result["supported_district_counts"] = {
        d: {k: sum(1 for e in districts if e["categorical"][d][k]["status"] == "supported") for k, _ in THRESHOLDS} for d in PER_DISTRICT_DEFINITIONS}
    result["observed_events_pooled"] = {
        d: {k: int(np.count_nonzero(stack.event(d, "obs", k, t)[stack.included])) for k, t in THRESHOLDS} for d in DEFINITIONS}
    return result
