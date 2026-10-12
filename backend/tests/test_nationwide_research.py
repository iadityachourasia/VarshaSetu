"""Scientific invariants for the separate nationwide development track."""

from __future__ import annotations

from datetime import date, timedelta

import numpy as np
import pytest

from backend.app.ml.nationwide_research import (
    GRID_SHAPE, LATITUDE, LONGITUDE, coherent_probabilities, comparable_mask,
    date_block_folds, partition,
)


def test_partition_covers_every_static_land_cell_once_including_west_gap():
    land = np.zeros(GRID_SHAPE, dtype=bool)
    land[np.where(LATITUDE == 15)[0][0], np.where(LONGITUDE == 67)[0][0]] = True
    land[np.where(LATITUDE == 20)[0][0], np.where(LONGITUDE == 75)[0][0]] = True
    regions = partition(land)
    assert regions["WEST_OF_DOMAIN"].sum() == 1
    assert regions["INSIDE_MODEL_DOMAIN"].sum() == 1
    assert np.array_equal(np.sum(np.stack(list(regions.values())), axis=0), land.astype(int))


def test_date_folds_keep_leads_together_and_purge_adjacent_dates():
    start = date(2023, 6, 1)
    cases = [f"{(start + timedelta(days=i)):%Y%m%d}_{lead}" for i in range(30) for lead in ("day1_24h", "day2_24h", "day3_24h")]
    folds = date_block_folds(cases)
    assert sorted(c for fold in folds for c in fold["held"]) == sorted(cases)
    for fold in folds:
        train_dates = {date.fromisoformat(f"{c[:4]}-{c[4:6]}-{c[6:8]}") for c in fold["train"]}
        held_dates = {date.fromisoformat(f"{c[:4]}-{c[4:6]}-{c[6:8]}") for c in fold["held"]}
        assert min(abs((t - h).days) for t in train_dates for h in held_dates) > 3


def test_reference_mask_cannot_fill_missing_with_zero():
    land = np.zeros(GRID_SHAPE, dtype=bool)
    land[1, 1] = land[1, 2] = True
    forecast = np.full(GRID_SHAPE, np.nan)
    reference = np.full(GRID_SHAPE, np.nan)
    forecast[1, 1:3] = [0.0, 1.0]
    reference[1, 1] = 0.0
    reference_valid = np.zeros(GRID_SHAPE, dtype=bool)
    reference_valid[1, 1] = True
    result = comparable_mask(land, forecast, reference, reference_valid)
    assert result.sum() == 1 and result[1, 1] and not result[1, 2]


def test_coherent_probabilities_reject_invalid_and_enforce_nesting():
    heavy, very_heavy = coherent_probabilities(np.array([0.2, 0.8]), np.array([0.5, 0.3]))
    assert np.array_equal(heavy, [0.2, 0.8])
    assert np.array_equal(very_heavy, [0.2, 0.3])
    with pytest.raises(ValueError):
        coherent_probabilities(np.array([1.1]), np.array([0.1]))
