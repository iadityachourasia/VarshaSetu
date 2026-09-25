"""Focused tests for the read-only Phase 4C diagnostic, not a revised QC rule."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from experiments.recent_historical.phase4c_comparability_audit_v1.diagnose import (  # noqa: E402
    intervals_compatible,
    packing_bound,
    sha,
)


def test_packing_half_sum_is_not_fixed_0055() -> None:
    assert packing_bound(.1, .01) == pytest.approx(.055)
    assert packing_bound(.01, .01) == pytest.approx(.01)
    assert packing_bound(.1, .1) == pytest.approx(.1)
    with pytest.raises(ValueError):
        packing_bound(0, .01)


def test_accumulation_semantic_gate() -> None:
    intervals = [(0, 3), (0, 6), (6, 12), (12, 18), (18, 24), (24, 27)]
    rows = [{"start_step": start, "end_step": end, "step_type": "accum",
             "type_of_statistical_processing": 1, "length_of_time_range": end-start,
             "indicator_of_unit_for_time_range": 1} for start, end in intervals]
    assert intervals_compatible(rows)
    rows[1]["start_step"] = 3
    assert not intervals_compatible(rows)


def test_audit_artifacts_are_hashed_and_protected_manifest_is_unchanged() -> None:
    here = ROOT / "experiments/recent_historical/phase4c_comparability_audit_v1"
    manifest_path = here / "artifact_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert sha(manifest_path) == (here / "artifact_manifest.sha256").read_text().strip()
    for name, info in manifest["files"].items():
        path = here / name
        assert path.stat().st_size == info["bytes"]
        assert sha(path) == info["sha256"]
    phase4b = ROOT / "experiments/recent_historical/phase4b_20240718_20240724_v1"
    assert sha(phase4b / "artifact_manifest.json") == manifest["protected_phase4b_manifest_sha256"]
