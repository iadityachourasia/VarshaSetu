"""IMERG V07 temporal alignment and missing-data semantics."""

from datetime import datetime, timedelta, timezone

import numpy as np
import pytest

from backend.app.data_sources.imerg_v07 import HalfHourRate, accumulate_imd_window

START = datetime(2024, 7, 1, 3, tzinfo=timezone.utc)


def fields():
    return [HalfHourRate(START + timedelta(minutes=30 * i), START + timedelta(minutes=30 * (i + 1)),
                         np.array([[2.0, 1.0], [0.0, 4.0]])) for i in range(48)]


def test_exact_imd_window_converts_rates_and_preserves_any_missing_cell():
    source = fields()
    source[12].rate_mm_per_hour[0, 1] = np.nan
    result = accumulate_imd_window(source, START)
    assert result.shape == (2, 2) and result[0, 0] == 48.0 and result[1, 0] == 0.0 and result[1, 1] == 96.0
    assert np.isnan(result[0, 1])  # never fill an absent satellite interval as zero rain


def test_missing_duplicate_shifted_or_wrong_version_intervals_are_refused():
    with pytest.raises(ValueError, match="48 are required"):
        accumulate_imd_window(fields()[:-1], START)
    broken = fields()
    broken[1] = broken[0]
    with pytest.raises(ValueError, match="missing, duplicated"):
        accumulate_imd_window(broken, START)
    broken = fields()
    broken[2] = HalfHourRate(broken[2].start_utc, broken[2].end_utc, broken[2].rate_mm_per_hour, product="GPM_3IMERGHH_06")
    with pytest.raises(ValueError, match="wrong product"):
        accumulate_imd_window(broken, START)
    with pytest.raises(ValueError, match="03:00 UTC"):
        accumulate_imd_window(fields(), START + timedelta(hours=1))
