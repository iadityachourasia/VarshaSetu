import numpy as np
import pytest

from backend.app.data.accumulation import GriddedAccumulationMessage
from scripts.diagnose_gefs_2026_masked_coverage import diagnose_lead


def _messages(total_first: float) -> list[GriddedAccumulationMessage]:
    return [
        GriddedAccumulationMessage(0, 3, np.array([[1.0, 1.0]]), "a", 0.05),
        GriddedAccumulationMessage(0, 6, np.array([[total_first, 2.0]]), "b", 0.05),
    ]


def test_passing_lead_must_match_canonical_exactly():
    result = diagnose_lead(_messages(2.0), 3, 6, canonical_passed=True)
    assert result["valid_cells"] == 2
    assert result["invalid_cells"] == 0
    assert result["valid_fraction"] == 1.0


def test_withheld_lead_counts_only_affected_cells():
    result = diagnose_lead(_messages(0.93), 3, 6, canonical_passed=False)
    assert result["valid_cells"] == 1
    assert result["invalid_cells"] == 1
    assert result["valid_fraction"] == 0.5


def test_mismatched_case_status_refused():
    with pytest.raises(ValueError, match="recovered all cells"):
        diagnose_lead(_messages(2.0), 3, 6, canonical_passed=False)
