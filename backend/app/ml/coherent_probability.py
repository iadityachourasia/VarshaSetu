"""Research diagnostic for nested 24-hour rainfall exceedance probabilities."""

from __future__ import annotations

import numpy as np


def project_nested_probabilities(heavy: np.ndarray, very_heavy: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Euclidean projection onto P(very heavy) <= P(heavy), row by row.

    This changes no fitting parameters and does not establish calibration.
    """
    h = np.asarray(heavy, dtype=np.float64)
    v = np.asarray(very_heavy, dtype=np.float64)
    if h.shape != v.shape or h.ndim != 1 or not np.isfinite(h).all() or not np.isfinite(v).all():
        raise ValueError("nested probability arrays must be matching finite vectors")
    if np.any((h < 0) | (h > 1) | (v < 0) | (v > 1)):
        raise ValueError("nested probability arrays must lie in [0, 1]")
    bad = v > h
    midpoint = (h[bad] + v[bad]) / 2
    projected_h, projected_v = h.copy(), v.copy()
    projected_h[bad] = midpoint
    projected_v[bad] = midpoint
    return projected_h, projected_v
