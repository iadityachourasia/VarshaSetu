"""Raw GEFS verification over the whole IMD grid (docs/140). Pure, read-only arithmetic: no model is fitted, tuned or applied; only the unmodified control-member rainfall is compared with IMD.

The regional corpus stops at 22 N and 80 E; the verification domain of the problem statement is India. This module partitions the IMD land grid into a frozen set of regions and reduces each case to the
additive statistics of ``zone_verification`` so pooled metrics and the whole-case bootstrap are exact re-aggregations. Region membership is a fixed rule of latitude and longitude, written before any
observation was compared; it is a description of where the forecast is checked, not a meteorological regime.
"""

from __future__ import annotations

import numpy as np

from backend.app.ml import zone_verification as zv

REGIONS = ("INSIDE_MODEL_DOMAIN", "NORTH_OF_DOMAIN", "EAST_AND_NORTH_EAST", "EAST_COAST_PENINSULA", "SOUTH_OF_DOMAIN")
NAMES = ("ALL_INDIA", *REGIONS)
IMD_BOUNDS = {"south": 6.5, "north": 38.5, "west": 66.5, "east": 100.0}
MODEL_BOX = {"south": 10.0, "north": 22.0, "west": 68.0, "east": 80.0}
MIN_CELLS, MIN_CASES, MIN_EVENT_PAIRS = zv.MIN_CELLS, zv.MIN_CASES, zv.MIN_EVENT_PAIRS
METRICS = ("rmse", "bias", "mae", "heavy_csi", "very_heavy_csi", "heavy_fb")


def region_of(lat: float, lon: float) -> str | None:
    """The first matching region, in this order. Cells of the IMD grid that match none (west of 68 E between 10 and 22 N) are not scored."""
    if MODEL_BOX["south"] <= lat <= MODEL_BOX["north"] and MODEL_BOX["west"] <= lon <= MODEL_BOX["east"]:
        return "INSIDE_MODEL_DOMAIN"
    if lat > MODEL_BOX["north"] and lon <= 88.0:
        return "NORTH_OF_DOMAIN"
    if lon > 88.0:
        return "EAST_AND_NORTH_EAST"
    if lat <= MODEL_BOX["north"] and 80.0 < lon <= 88.0:
        return "EAST_COAST_PENINSULA"
    if lat < MODEL_BOX["south"] and lon <= 80.0:
        return "SOUTH_OF_DOMAIN"
    return None


def region_masks(lat: np.ndarray, lon: np.ndarray) -> dict[str, np.ndarray]:
    """Flat boolean masks over the [lat, lon] grid (row-major). ``ALL_INDIA`` is the union of the scored regions; regions never overlap."""
    flat = np.array([region_of(float(a), float(b)) for a in lat for b in lon], dtype=object)
    masks = {name: np.array([label == name for label in flat]) for name in REGIONS}
    masks["ALL"] = np.array([label is not None for label in flat])         # case_stats expects the footprint under this key
    if sum(int(m.sum()) for m in (masks[r] for r in REGIONS)) != int(masks["ALL"].sum()):
        raise ValueError("regions must partition the footprint")
    return masks


def unscored_cells(observed: np.ndarray, masks: dict[str, np.ndarray]) -> int:
    """Paired cells that lie in no region (west of 68 E between 10 and 22 N). They are dropped, never reassigned, and counted so the evidence can state how many."""
    return int(np.count_nonzero(np.isfinite(observed) & ~masks["ALL"]))


def case_stats(observed: np.ndarray, raw: np.ndarray, masks: dict[str, np.ndarray]) -> np.ndarray:
    """[stratum (NAMES), S] statistics of one case for the Raw forecast; observed and raw are flat fields with NaN off the paired cells. Cells in no region are excluded."""
    if not np.array_equal(np.isfinite(observed), np.isfinite(raw)):
        raise ValueError("forecast and observation cells differ")
    inside = masks["ALL"]
    observed, raw = np.where(inside, observed, np.nan), np.where(inside, raw, np.nan)
    local = {**masks, "ALL_INDIA": masks["ALL"]}
    return zv.case_stats(observed, {"M0": raw}, local, names=NAMES)[:, 0, :]


def region_metrics(totals: np.ndarray) -> dict[str, dict]:
    """Pooled metrics of each stratum from summed statistics [stratum, S]."""
    return {name: zv.metrics(totals[i]) for i, name in enumerate(NAMES)}


def support(stack: np.ndarray, cell_counts: dict[str, int]) -> dict[str, dict]:
    """Support gate per stratum: at least 20 cells, 30 cases and 30 observed event pairs (the same gate as the zone protocol). ``stack`` is [case, stratum, S]."""
    totals = stack.sum(axis=0)
    out = {}
    for i, name in enumerate(NAMES):
        cases = int(np.count_nonzero(stack[:, i, 0] > 0))
        block = {"cells": cell_counts[name], "cases": cases}
        for threshold, _ in zv.THRESHOLDS:
            events = int(totals[i, zv._idx(f"{threshold}_hits")] + totals[i, zv._idx(f"{threshold}_misses")])
            block[threshold] = {"observed_event_pairs": events, "supported": bool(cell_counts[name] >= MIN_CELLS and cases >= MIN_CASES and events >= MIN_EVENT_PAIRS)}
        block["continuous_supported"] = bool(cell_counts[name] >= MIN_CELLS and cases >= MIN_CASES)
        out[name] = block
    return out


def _statistic(totals: np.ndarray, models: list[str]) -> dict[tuple, float]:
    """Point statistics of every stratum and metric from summed [stratum, model, S] totals."""
    return {(name, metric): zv._metric(totals[i, 0], metric) for i, name in enumerate(NAMES) for metric in METRICS}


def bootstrap(stack: np.ndarray, *, repeats: int = zv.REPEATS, seed: int = zv.SEED) -> dict[tuple, dict]:
    """95 percent whole-case bootstrap intervals of each stratum's metrics (cells of a case stay together; optimistic because consecutive dates are correlated).

    ``stack`` is [case, stratum, S]; ``cases`` should already be grouped by initialization date by the caller (a date contributes up to three leads)."""
    return zv.paired_bootstrap(stack[:, :, None, :], ["M0"], statistic=_statistic, repeats=repeats, seed=seed)
