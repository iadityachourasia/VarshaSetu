"""The 2026 source probe is immutable forecast-only evidence, not a test score."""

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2] / "data/manifests/research_pilot"


def _verified(name: str) -> tuple[dict, str]:
    path = ROOT / name
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    assert path.with_suffix(".sha256").read_text(encoding="ascii").split()[0] == digest
    return json.loads(path.read_text(encoding="utf-8")), digest


def test_2026_index_probe_has_no_observations_or_payload_and_no_model_version_claim():
    protocol, protocol_hash = _verified("2026_gefs_probe_protocol_v1.json")
    result, _ = _verified("2026_gefs_probe_result_v1.json")
    assert result["protocol_sha256"] == protocol_hash
    assert result["observation_read"] is False and result["forecast_payload_download"] is False
    assert result["role"] == protocol["role"] == "SOURCE_AVAILABILITY_PROBE_ONLY"
    assert [entry["cycle"] for entry in result["cycles"]] == protocol["cycles"]
    for entry in result["cycles"]:
        if entry["status"] == "COMPLETE_SELECTED_INDEX":
            assert entry["selected_messages"] == 34
            assert entry["planned_selected_bytes"] > 0
            assert entry["model_version"] == "NOT_DECLARED_BY_INDEX"


def test_2026_grib_probe_keeps_qc_exclusions_and_no_skill_claim():
    protocol, protocol_hash = _verified("2026_gefs_grib_probe_protocol_v1.json")
    result, _ = _verified("2026_gefs_grib_probe_result_v1.json")
    _, index_hash = _verified("2026_gefs_probe_result_v1.json")
    assert result["protocol_sha256"] == protocol_hash
    assert result["index_probe_sha256"] == protocol["source_index_probe_sha256"] == index_hash
    assert result["observation_read"] is False and result["model_inference"] is False
    assert result["role"] == "SOURCE_AND_GRIB_SEMANTICS_PROBE_ONLY"
    assert [entry["cycle"] for entry in result["cycles"]] == protocol["cycles"]
    assert sum(len(entry["products_passing_qc"]) for entry in result["cycles"] if entry["status"] == "DECODED") == 8
    for entry in result["cycles"]:
        if entry["status"] == "DECODED":
            assert entry["source_messages"] == 34 and len(entry["source_sha256"]) == 34
            assert entry["model_version"] == "NOT_PROVEN_BY_GRIB_IDENTIFIERS"
            assert entry["observation_read"] is False and entry["model_inference"] is False


def test_2026_evaluation_protocol_is_candidate_only_and_preserves_track_separation():
    protocol, _ = _verified("2026_track_b_evaluation_protocol_v1.json")
    assert protocol["status"] == "FROZEN_BEFORE_2026_OBSERVATION_PAIRING_CANDIDATE_NOT_CLEARED"
    assert protocol["track"] == "B_OPERATIONAL_GEFS_ONLY"
    assert protocol["primary_regime_comparison"].startswith("M4_soft_regime minus M2_global_XGBoost")
    assert protocol["promotion_gate"]["if_any_gate_fails"].startswith("Keep M2")
    assert protocol["thresholds_mm_per_24h"] == {"heavy": 64.5, "very_heavy": 115.6}
    assert any("No pooling" in rule for rule in protocol["prohibited"])
