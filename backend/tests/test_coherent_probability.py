"""Scientific invariants for the development-only nested probability projection."""

import numpy as np
import pytest

from backend.app.ml.coherent_probability import project_nested_probabilities


def test_projection_preserves_ordered_rows_and_uses_midpoint_on_violations():
    heavy = np.array([0.4, 0.2, 0.0, 1.0])
    very_heavy = np.array([0.1, 0.8, 0.0, 1.0])
    ph, pv = project_nested_probabilities(heavy, very_heavy)
    np.testing.assert_array_equal(ph, [0.4, 0.5, 0.0, 1.0])
    np.testing.assert_array_equal(pv, [0.1, 0.5, 0.0, 1.0])
    np.testing.assert_array_equal(heavy, [0.4, 0.2, 0.0, 1.0])
    assert np.all(pv <= ph)


@pytest.mark.parametrize("yh,yv", [(0, 0), (1, 0), (1, 1)])
def test_projection_never_increases_joint_brier_for_nested_truth(yh, yv):
    heavy = np.array([0.02, 0.2, 0.5, 0.95])
    very_heavy = np.array([0.7, 0.3, 0.8, 0.96])
    ph, pv = project_nested_probabilities(heavy, very_heavy)
    before = (heavy - yh) ** 2 + (very_heavy - yv) ** 2
    after = (ph - yh) ** 2 + (pv - yv) ** 2
    assert np.all(after <= before + 1e-15)


def test_projection_rejects_invalid_probability_inputs():
    with pytest.raises(ValueError):
        project_nested_probabilities(np.array([0.1]), np.array([np.nan]))
    with pytest.raises(ValueError):
        project_nested_probabilities(np.array([1.1]), np.array([0.1]))
    with pytest.raises(ValueError):
        project_nested_probabilities(np.array([0.1]), np.array([0.1, 0.2]))
