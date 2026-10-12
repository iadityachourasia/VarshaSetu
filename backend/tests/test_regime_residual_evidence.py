"""Re-derive the development result's categorical metrics and governance limits."""

import hashlib
import json
from pathlib import Path

import pytest

PHASE = Path(__file__).resolve().parents[1] / "app/evidence_data/phase18"
ROOT = Path(__file__).resolve().parents[2]


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_result_is_hash_pinned_and_never_masquerades_as_independent_skill():
    protocol = PHASE / "regime_residual_dev_protocol_v1.json"
    result = PHASE / "regime_residual_dev_result_v1.json"
    assert protocol.with_suffix(".sha256").read_text(encoding="ascii").split()[0] == sha(protocol)
    assert result.with_suffix(".sha256").read_text(encoding="ascii").split()[0] == sha(result)
    p, r = json.loads(protocol.read_text(encoding="utf-8")), json.loads(result.read_text(encoding="utf-8"))
    assert r["protocol_sha256"] == sha(protocol)
    assert r["status"] == "DEVELOPMENT_ONLY_NO_INDEPENDENT_TEST"
    assert r["evaluation_years"] == [2012, 2013]
    assert not set(r["evaluation_years"]) & set(p["year_roles"]["forbidden_for_fitting_selection_or_evaluation"])
    assert r["evaluation_cases"] == 511 and r["evaluation_cells"] == 664811
    observed_counts = set()
    for model in r["results"].values():
        pooled = model["pooled"]
        assert pooled["cells"] == r["evaluation_cells"]
        for threshold in ("heavy", "very_heavy"):
            event = pooled[threshold]
            hits, misses, false = (event[key] for key in ("hits", "misses", "false_alarms"))
            assert event["observed_events"] == hits + misses
            assert event["csi"] == pytest.approx(hits / (hits + misses + false))
            assert event["POD"] == pytest.approx(hits / (hits + misses))
            assert event["FAR"] == pytest.approx(false / (hits + false)) if hits + false else event["FAR"] is None
            observed_counts.add((threshold, event["observed_events"]))
        assert sum(row["cells"] for row in model["by_year"].values()) == r["evaluation_cells"]
    assert len(observed_counts) == 2  # one matched set of observed heavy and very-heavy events
    assert r["results"]["regime_soft_residual"]["pooled"]["heavy"]["csi"] < r["results"]["B1_base"]["pooled"]["heavy"]["csi"]


def test_local_model_files_match_the_recorded_hashes_when_available():
    result = json.loads((PHASE / "regime_residual_dev_result_v1.json").read_text(encoding="utf-8"))
    directory = ROOT / "experiments/regime_residual_dev_v1"
    if not directory.is_dir():
        pytest.skip("local development model files are not distributed")
    for name, digest in result["model_sha256"].items():
        assert sha(directory / name) == digest
