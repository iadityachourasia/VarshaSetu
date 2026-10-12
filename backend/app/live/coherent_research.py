"""Research-only wrapper around frozen models; the live worker never imports it."""

from __future__ import annotations

import numpy as np

from backend.app.ml.coherent_probability import project_nested_probabilities
from backend.app.live.pipeline import FrozenModels, check_exceedance_order


class ProjectedFrozenModels:
    def __init__(self, frozen: FrozenModels):
        self.frozen = frozen
        self.hashes = frozen.hashes

    def apply(self, X: np.ndarray, regime_vector: np.ndarray) -> dict:
        output = self.frozen._apply_unchecked(X, regime_vector)
        heavy = output["heavy_probability"]
        very_heavy = output["very_heavy_probability"]
        violations = very_heavy > heavy
        gap = float(np.max((very_heavy - heavy)[violations])) if violations.any() else 0.0
        output["heavy_probability"], output["very_heavy_probability"] = project_nested_probabilities(heavy, very_heavy)
        check_exceedance_order(output["heavy_probability"], output["very_heavy_probability"])
        output["projection_modified_cells"] = int(violations.sum())
        output["projection_max_gap"] = gap
        return output
