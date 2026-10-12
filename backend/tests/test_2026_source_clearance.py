"""The 2026 source audit must remain metadata-only and fail closed."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.probe_2026_source_clearance import INPUTS, assess, build, read_sealed


def test_current_evidence_cannot_clear_annual_or_version_gate() -> None:
    result = build()
    assert result["status"] == "OPEN_NO_CLEARANCE"
    assert result["blockers"] == [
        "COMPLETE_2026_IMD_ANNUAL_REFERENCE_NOT_OBTAINED",
        "ACTUAL_2026_GEFS_EXECUTABLE_TRANSITION_UNCONFIRMED",
        "EXACT_2023_TRAINING_GEFS_PATCH_UNCONFIRMED",
        "2023_TO_2026_PREDICTOR_COMPARABILITY_UNREVIEWED",
    ]
    assert result["annual_response_bytes"] == 0
    assert result["daily_candidate_dates_receipted"] == 125
    assert result["daily_candidate_is_annual_reference"] is False
    assert result["radiation_packing_change_observed"] is True
    assert result["radiation_probe_identifies_executable"] is False
    assert result["observation_values_read"] is False
    assert result["forecast_pairing_or_scoring"] is False
    assert result["clearance_manifests_written"] is False
    assert set(result["evidence_sha256"]) == set(INPUTS)


def test_receipt_tamper_refused(tmp_path: Path) -> None:
    source = tmp_path / "evidence.json"
    source.write_text(json.dumps({"status": "OPEN"}), encoding="utf-8")
    source.with_suffix(".sha256").write_text("0" * 64 + "  evidence.json\n", encoding="ascii")
    with pytest.raises(ValueError, match="mismatched SHA-256 receipt"):
        read_sealed(source)


def test_metadata_only_contract_refuses_claimed_value_access() -> None:
    annual = {"observation_rainfall_values_read": True, "response_bytes": 0}
    daily = {"observation_values_decoded": False}
    gefs = {}
    radiation = {"observation_read": False, "model_inference": False}
    protocol = {"reference_clearance_required": "annual", "model_version_clearance_required": "version"}
    with pytest.raises(ValueError, match="must not consume 2026 rainfall values"):
        assess(annual, daily, gefs, radiation, protocol)
