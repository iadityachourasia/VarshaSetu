from __future__ import annotations

import numpy as np
import pytest

from scripts.run_2026_frozen_inference import validate_outputs


def _valid() -> tuple[dict, np.ndarray]:
    X = np.zeros((2401, 22), dtype=np.float32)
    X[:, 0] = 1
    output = {name: np.ones(2401, dtype=np.float32) for name in ("M0", "M1", "M2", "M3", "M4")}
    output.update(heavy_probability=np.full(2401, 0.2), very_heavy_probability=np.full(2401, 0.1),
                  regime_probability=np.array([0.2, 0.3, 0.5]))
    return output, X


def test_valid_inference_preserves_incoherence_as_count() -> None:
    output, X = _valid()
    assert validate_outputs(output, X) == 0
    output["very_heavy_probability"][0] = 0.3
    assert validate_outputs(output, X) == 1


def test_invalid_rain_raw_probability_and_regime_fail_closed() -> None:
    output, X = _valid()
    output["M2"][0] = -0.1
    with pytest.raises(ValueError, match="nonnegative rainfall"):
        validate_outputs(output, X)
    output, X = _valid()
    output["M0"][0] = 2
    with pytest.raises(ValueError, match="Raw output"):
        validate_outputs(output, X)
    output, X = _valid()
    output["heavy_probability"][0] = 1.1
    with pytest.raises(ValueError, match="probability field"):
        validate_outputs(output, X)
    output, X = _valid()
    output["regime_probability"][:] = 0.1
    with pytest.raises(ValueError, match="regime class"):
        validate_outputs(output, X)
