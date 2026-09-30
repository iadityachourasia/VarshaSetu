"""Pure district aggregation for the frozen Track B (operational-era) 49x49 grids.

Uses the same pinned, hash-verified Phase 2C area-overlap weight matrix as the
Track A district product (docs/65), so both tracks share one spatial definition.
Nothing here trains, recalibrates or re-infers; it only area-weights already-frozen
per-cell values over each district's valid paired cells.
"""

from __future__ import annotations

import numpy as np

HEAVY_MM = 64.5
VERY_HEAVY_MM = 115.6
GRID_CELLS = 49 * 49


def flat_field(values: np.ndarray, pixel_index: np.ndarray) -> np.ndarray:
    """Scatter one case's paired cells onto the 2401-cell grid; unpaired cells are NaN."""
    pixel = np.asarray(pixel_index)
    if len(np.unique(pixel)) != len(pixel) or np.any((pixel < 0) | (pixel >= GRID_CELLS)):
        raise ValueError("invalid target-grid pixel mapping")
    grid = np.full(GRID_CELLS, np.nan, dtype=np.float64)
    grid[pixel] = np.asarray(values, dtype=np.float64)
    return grid


def aggregate_operational_districts(districts: list[dict], weights: np.ndarray, *, raw: np.ndarray,
                                    corrected: np.ndarray, observed: np.ndarray,
                                    heavy_p: np.ndarray | None = None,
                                    very_heavy_p: np.ndarray | None = None) -> list[dict]:
    """Area-weighted district statistics over cells where every required field is finite.

    All field arguments are flat 2401-vectors with NaN outside the case's valid paired
    cells (see :func:`flat_field`). Probabilities are optional; when absent the
    probability fields are ``None``. Districts with no valid cell are omitted.
    Area fractions are the weighted share of valid cells at or above the IMD 24 h
    thresholds (inclusive), so they lie in [0, 1]. ``*_max_mm`` is a cell maximum, not
    an area-weighted extreme.
    """
    required = [np.asarray(x, dtype=float).ravel() for x in (raw, corrected, observed)]
    optional = {k: None if v is None else np.asarray(v, dtype=float).ravel()
                for k, v in (("heavy", heavy_p), ("very_heavy", very_heavy_p))}
    if weights.shape != (len(districts), GRID_CELLS) or any(len(x) != GRID_CELLS for x in required) \
            or any(v is not None and len(v) != GRID_CELLS for v in optional.values()):
        raise ValueError("district aggregation shape mismatch")
    valid = np.logical_and.reduce([np.isfinite(x) for x in required])
    for v in optional.values():
        if v is not None:
            valid &= np.isfinite(v)
    r, c, o = required
    result = []
    for d, w in zip(districts, weights):
        active = (w > 0) & valid
        total = float(w[active].sum())
        if total == 0:
            continue
        q = w[active] / total
        ca, oa = c[active], o[active]
        row = {"district_id": d["district_id"], "district_name": d["district_name"],
               "valid_grid_cells": int(active.sum()),
               "raw_mean_mm": float(q @ r[active]), "raw_max_mm": float(r[active].max()),
               "corrected_mean_mm": float(q @ ca), "corrected_max_mm": float(ca.max()),
               "heavy_probability": None if optional["heavy"] is None else float(q @ optional["heavy"][active]),
               "very_heavy_probability": None if optional["very_heavy"] is None else float(q @ optional["very_heavy"][active]),
               "heavy_area_fraction": float(q @ (ca >= HEAVY_MM)),
               "very_heavy_area_fraction": float(q @ (ca >= VERY_HEAVY_MM)),
               "observed_mean_mm": float(q @ oa), "observed_max_mm": float(oa.max()),
               "observed_heavy_area_fraction": float(q @ (oa >= HEAVY_MM)),
               "observed_very_heavy_area_fraction": float(q @ (oa >= VERY_HEAVY_MM))}
        result.append(row)
    return result
