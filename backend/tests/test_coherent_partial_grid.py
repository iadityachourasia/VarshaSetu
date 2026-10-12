"""The projected replay is isolated from the strict live probability gate."""

import numpy as np
import pytest
from pathlib import Path

from backend.app.live.coherent_research import ProjectedFrozenModels
from backend.app.live.pipeline import CycleRefused, FrozenModels
from scripts import run_coherent_partial_grid as replay


class FrozenStub:
    hashes = {"M2": "frozen"}

    def _apply_unchecked(self, X, _regime):
        return {"M0": X[:, 0].copy(), "M2": X[:, 0] + 1, "M4": X[:, 0] + 2,
                "heavy_probability": np.array([0.1, 0.9]),
                "very_heavy_probability": np.array([0.8, 0.2]),
                "regime_probability": np.array([0.2, 0.3, 0.5])}


def test_projected_replay_changes_only_incoherent_probability_rows():
    base = FrozenStub()
    wrapper = ProjectedFrozenModels(base)
    X = np.array([[1.0], [2.0]])
    with pytest.raises(CycleRefused, match="exceeds heavy"):
        FrozenModels.apply(base, X, np.zeros(3))
    out = wrapper.apply(X, np.zeros(3))
    np.testing.assert_array_equal(out["M2"], [2.0, 3.0])
    np.testing.assert_allclose(out["heavy_probability"], [0.45, 0.9])
    np.testing.assert_allclose(out["very_heavy_probability"], [0.45, 0.2])
    assert out["projection_modified_cells"] == 1
    assert out["projection_max_gap"] == pytest.approx(0.7)
    assert wrapper.hashes is base.hashes


def test_replay_protocol_is_sealed_and_has_no_reference_read():
    rule, _ = replay.checked_protocol()
    assert rule["forecast_only"] is True
    assert rule["reference_read"] is False
    assert rule["excluded_years"] == [2025, 2026]
    assert replay.PRODUCTS == ("day1_24h", "day2_24h", "day3_24h")


def test_replay_publication_retries_only_windows_access_denied(monkeypatch, tmp_path):
    monkeypatch.setattr(replay, "CACHE", tmp_path)
    monkeypatch.setattr(replay.time, "sleep", lambda _seconds: None)
    stage = tmp_path / ".stage-case"
    stage.mkdir()
    destination = tmp_path / "20240601"
    original_rename = Path.rename
    calls = []

    def intermittent_rename(self, target):
        calls.append(1)
        if len(calls) == 1:
            error = PermissionError("transient access denied")
            error.winerror = 5
            raise error
        return original_rename(self, target)

    monkeypatch.setattr(Path, "rename", intermittent_rename)
    replay.publish_stage(stage, destination)
    assert len(calls) == 2
    assert destination.is_dir() and not stage.exists()
