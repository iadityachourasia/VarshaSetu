"""Masked QC is diagnostic only and preserves canonical results when valid."""

import numpy as np
import pytest

from backend.app.data.accumulation import GriddedAccumulationMessage, reconstruct_minimal_accumulation_window
from backend.app.data.accumulation_masked import reconstruct_masked_diagnostic


def _messages(total_first_cell: float):
    return [GriddedAccumulationMessage(0, 3, np.array([[1.0, 1.0], [0.0, 0.0]]), "p", 0.01),
            GriddedAccumulationMessage(0, 6, np.array([[total_first_cell, 2.0], [0.0, 0.0]]), "t", 0.1),
            GriddedAccumulationMessage(6, 9, np.array([[2.0, 3.0], [0.0, 0.0]]), "d", 0.01)]


def test_masked_diagnostic_equals_canonical_on_valid_fields():
    messages = _messages(1.5)
    canonical = reconstruct_minimal_accumulation_window(messages, window_start_hour=3, window_end_hour=9)
    diagnostic = reconstruct_masked_diagnostic(messages, window_start_hour=3, window_end_hour=9)
    assert diagnostic.invalid_cells == 0 and diagnostic.valid_mask.all()
    assert np.array_equal(diagnostic.rainfall_mm, canonical.rainfall_mm)
    assert diagnostic.subtraction_count == canonical.subtraction_count


def test_material_negative_is_missing_not_zero_and_canonical_still_refuses():
    messages = _messages(0.93)
    with pytest.raises(ValueError, match="negative difference exceeds packing bound"):
        reconstruct_minimal_accumulation_window(messages, window_start_hour=3, window_end_hour=9)
    diagnostic = reconstruct_masked_diagnostic(messages, window_start_hour=3, window_end_hour=9)
    assert diagnostic.invalid_cells == 1
    assert np.isnan(diagnostic.rainfall_mm[0, 0]) and not diagnostic.valid_mask[0, 0]
    assert diagnostic.valid_mask[0, 1] and diagnostic.rainfall_mm[0, 1] == 4.0
    assert diagnostic.segments[0]["invalid_cells"] == 1


def test_masked_diagnostic_requires_complete_nonambiguous_window():
    with pytest.raises(ValueError, match="no exact"):
        reconstruct_masked_diagnostic(_messages(1.5)[:1], window_start_hour=3, window_end_hour=9)
