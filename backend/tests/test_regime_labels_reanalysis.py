"""Objective reanalysis regime labels (docs/142): persistence rule, threshold fitted on training days only, box maxima and decoding against analytic and stored data."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from backend.app.ml import regime_labels_reanalysis as rl

CHUNK_DIR = Path(__file__).resolve().parents[2] / "data/raw/era5_wb2_1p5_geopotential_v1/geopotential"


def test_persistence_requires_consecutive_days_and_nan_breaks_a_run():
    s = np.array([0, 5, 0, 5, 5, 0, 5, 5, 5, np.nan, 5, 5], dtype=float)
    out = rl.persistent_days(s, 4.0)
    assert out.tolist() == [False, False, False, True, True, False, True, True, True, False, True, True]
    assert rl.persistent_days(np.array([5.0, 0, 5.0]), 4.0).tolist() == [False, False, False]
    assert rl.persistent_days(np.array([5.0, 5.0]), 4.0, min_days=3).tolist() == [False, False]
    assert not rl.persistent_days(np.array([np.nan, np.nan]), 0.0).any()


def test_the_threshold_is_a_training_percentile_and_needs_enough_days():
    values = np.arange(1000, dtype=float)
    assert rl.percentile_threshold(values) == pytest.approx(np.quantile(values, 0.85))
    assert rl.percentile_threshold(np.r_[values, np.full(50, np.nan)]) == rl.percentile_threshold(values)
    with pytest.raises(ValueError):
        rl.percentile_threshold(np.arange(100.0))


def test_daily_maximum_and_box_maximum_never_patch_missing_values():
    series = np.array([1, 2, 3, 4, 5, np.nan, 7, 8], dtype=float)
    out = rl.daily_maximum(series)
    assert out[0] == 4 and np.isnan(out[1])
    with pytest.raises(ValueError):
        rl.daily_maximum(np.ones(6))
    lat, lon = np.arange(0.0, 40.0, 1.5), np.arange(50.0, 90.0, 1.5)
    field = np.zeros((2, lat.size, lon.size))
    field[0, 20, 20] = 9.0
    field[1, 20, 20] = np.nan
    result = rl.box_maximum(field, lat, lon, rl.WD_BOX)
    assert result[0] == 9.0 and np.isnan(result[1])
    with pytest.raises(ValueError):
        rl.box_maximum(field, lat, lon, (100.0, 101.0, 0.0, 1.0))


def test_a_geopotential_trough_gives_a_positive_box_vorticity_maximum_in_the_right_box():
    lat, lon = np.arange(-90.0, 90.1, 1.5), np.arange(0.0, 360.0, 1.5)
    la, lo = np.meshgrid(lat, lon, indexing="ij")
    g = 9.80665
    levels = np.full((1, 13, lat.size, lon.size), 5500.0 * g)
    trough = 5500.0 - 200.0 * np.exp(-(((la - 30.0) / 5.0) ** 2 + ((lo - 70.0) / 6.0) ** 2))        # a trough over north-west India at 500 hPa
    levels[0, rl.LEVELS_HPA.index(500)] = trough * g
    zeta = rl.level_vorticity(levels, rl.LEVELS_HPA.index(500), lat, lon)
    in_wd, in_lps = rl.box_maximum(zeta, lat, lon, rl.WD_BOX)[0], rl.box_maximum(zeta, lat, lon, rl.LPS_BOX)[0]
    assert in_wd > 3.0 and in_wd > in_lps                                                          # strong cyclonic vorticity, mostly inside the WD box
    ridge = levels.copy()
    ridge[0, rl.LEVELS_HPA.index(500)] = (5500.0 + 200.0 * np.exp(-(((la - 30.0) / 5.0) ** 2 + ((lo - 70.0) / 6.0) ** 2))) * g
    assert rl.box_maximum(rl.level_vorticity(ridge, rl.LEVELS_HPA.index(500), lat, lon), lat, lon, rl.WD_BOX)[0] < in_wd


_CHUNKS = sorted(CHUNK_DIR.glob("*.0.0.0")) if CHUNK_DIR.exists() else []


@pytest.mark.skipif(not _CHUNKS, reason="no ERA5 chunk is on disk")
def test_a_stored_chunk_decodes_to_plausible_geopotential():
    chunk = rl.decode_chunk(_CHUNKS[0].read_bytes())
    assert chunk.shape == (8, 13, 121, 240) and np.isfinite(chunk).all()
    assert chunk[0, rl.LEVELS_HPA.index(500)].mean() == pytest.approx(5.0e4, rel=0.1)             # 500 hPa geopotential about 5500 m x g
    assert chunk[0, rl.LEVELS_HPA.index(850)].mean() == pytest.approx(1.4e4, rel=0.25)
    assert (chunk[:, rl.LEVELS_HPA.index(500)] > chunk[:, rl.LEVELS_HPA.index(850)]).all()
