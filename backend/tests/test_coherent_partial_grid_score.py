"""Paired probability scores retain observed counts and source-frozen rules."""

import numpy as np

from scripts import score_coherent_partial_grid as score
from scripts.score_partial_grid_candidate import metrics


def test_score_protocol_uses_frozen_event_cutoffs_and_climatology():
    rule, _ = score.verified_protocol()
    assert rule["probability_decision_thresholds"] == {"heavy": 0.1, "very_heavy": 0.05}
    assert rule["thresholds_mm_24h"] == {"heavy": 64.5, "very_heavy": 115.6}
    assert rule["excluded_years"] == [2025, 2026]


def test_group_score_uses_identical_cells_and_counts_for_models_and_events():
    rain = np.zeros((49, 49), dtype=float)
    rain[0, 0] = 120.0
    mask = np.ones((49, 49), dtype=bool)
    fields = {name: rain.copy() for name in ("M0", "M2", "M4")}
    base = {"cycle": "20240601", "product": "day1_24h", "cell_count": int(mask.sum()),
            "valid_mask": mask, "observed_field": rain,
            "models": {name: metrics(field, rain, mask) for name, field in fields.items()},
            "heavy_label": (rain[mask] >= 64.5).astype(np.uint8),
            "very_heavy_label": (rain[mask] >= 115.6).astype(np.uint8),
            "heavy_probability": np.where(rain[mask] >= 64.5, 0.8, 0.01),
            "very_heavy_probability": np.where(rain[mask] >= 115.6, 0.6, 0.001)}
    for name, field in fields.items():
        base[f"{name}_field"] = field
    rule, _ = score.verified_protocol()
    result = score.score_group([base], rule)
    assert result["paired_cells"] == 2401
    assert result["probability"]["heavy"]["observed_event_count"] == 1
    assert result["probability"]["very_heavy"]["observed_event_count"] == 1
    assert result["probability"]["heavy"]["categorical"]["hits"] == 1
    assert result["deterministic"]["models"]["M0"]["rmse_mm"] == 0
    assert result["heavy_fss_3x3"]["M2"]["fss"] == 1
    assert result["bss_date_bootstrap"]["reason"] == "fewer than two initialization dates"
