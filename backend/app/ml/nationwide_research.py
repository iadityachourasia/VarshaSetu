"""Pure contracts for the separate, development-only nationwide Track B study."""

from __future__ import annotations

from datetime import date

import numpy as np

from backend.app.ml.all_india_raw import IMD_BOUNDS, region_masks


LATITUDE = np.arange(IMD_BOUNDS["south"], IMD_BOUNDS["north"] + 0.125, 0.25)
LONGITUDE = np.arange(IMD_BOUNDS["west"], IMD_BOUNDS["east"] + 0.125, 0.25)
CONTEXT_LATITUDE = np.arange(5.0, 40.0 + 0.25, 0.5)
CONTEXT_LONGITUDE = np.arange(60.0, 105.0 + 0.25, 0.5)
GRID_SHAPE = (129, 135)
REGIONS = (
    "INSIDE_MODEL_DOMAIN", "NORTH_OF_DOMAIN", "EAST_AND_NORTH_EAST",
    "EAST_COAST_PENINSULA", "SOUTH_OF_DOMAIN", "WEST_OF_DOMAIN",
)
LEADS = {"day1_24h": 24, "day2_24h": 48, "day3_24h": 72}


def partition(land_mask: np.ndarray) -> dict[str, np.ndarray]:
    """Versioned extension of the frozen Raw partition; it includes its west gap."""
    land = np.asarray(land_mask)
    if land.shape != GRID_SHAPE or land.dtype != np.bool_:
        raise ValueError("land mask must be a boolean 129 by 135 grid")
    old = region_masks(LATITUDE, LONGITUDE)
    result = {name: old[name].reshape(GRID_SHAPE) & land for name in REGIONS[:-1]}
    occupied = np.logical_or.reduce(list(result.values()))
    result["WEST_OF_DOMAIN"] = land & ~occupied
    count = np.sum(np.stack(list(result.values()), axis=0), axis=0)
    if not np.array_equal(count, land.astype(np.int64)):
        raise ValueError("national regions must partition every land cell exactly once")
    return result


def date_block_folds(case_ids: list[str], *, folds: int = 3, embargo_days: int = 3) -> list[dict]:
    """Chronological held blocks; every lead of an initialization stays together."""
    if len(case_ids) != len(set(case_ids)) or any(len(c) < 8 for c in case_ids):
        raise ValueError("case IDs must be unique and dated")
    days = sorted({date.fromisoformat(f"{c[:4]}-{c[4:6]}-{c[6:8]}") for c in case_ids})
    if len(days) < folds * (2 * embargo_days + 2):
        raise ValueError("too few initialization dates for embargoed folds")
    blocks = np.array_split(np.arange(len(days)), folds)
    result = []
    for i, block in enumerate(blocks):
        held = {days[int(j)] for j in block}
        train = {d for d in days if d not in held and min(abs((d - h).days) for h in held) > embargo_days}
        if not train:
            raise ValueError("embargo leaves an empty training fold")
        selected = lambda pool: [c for c in case_ids if date.fromisoformat(f"{c[:4]}-{c[4:6]}-{c[6:8]}") in pool]
        result.append({"fold": i, "train": selected(train), "held": selected(held)})
    if sorted(c for fold in result for c in fold["held"]) != sorted(case_ids):
        raise ValueError("held folds do not cover every case once")
    return result


def comparable_mask(land: np.ndarray, forecast: np.ndarray, reference: np.ndarray, reference_valid: np.ndarray) -> np.ndarray:
    """Never infer reference coverage from land geometry or fill missing truth."""
    arrays = [np.asarray(x) for x in (land, forecast, reference, reference_valid)]
    if any(x.shape != GRID_SHAPE for x in arrays) or arrays[0].dtype != np.bool_ or arrays[3].dtype != np.bool_:
        raise ValueError("national grid or mask mismatch")
    return arrays[0] & arrays[3] & np.isfinite(arrays[1]) & (arrays[1] >= 0) & np.isfinite(arrays[2]) & (arrays[2] >= 0)


def coherent_probabilities(heavy: np.ndarray, very_heavy: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    heavy, very_heavy = np.asarray(heavy, dtype=float), np.asarray(very_heavy, dtype=float)
    if heavy.shape != very_heavy.shape or not np.isfinite(heavy).all() or not np.isfinite(very_heavy).all():
        raise ValueError("probability arrays are incompatible")
    if np.any((heavy < 0) | (heavy > 1) | (very_heavy < 0) | (very_heavy > 1)):
        raise ValueError("probability is outside [0,1]")
    return heavy, np.minimum(very_heavy, heavy)
