"""The versioned score entrypoint refuses 2026 pairing until source review."""

from __future__ import annotations

from pathlib import Path

import pytest

from scripts import score_2026_with_clearance_gate_v2 as gate
from scripts.run_2026_frozen_inference import sealed, sha


def _approval() -> dict:
    return {
        "schema": "varshasetu-2026-source-review-approval-v2",
        "status": "APPROVED_FOR_ONE_SHOT_RESEARCH_VERIFICATION",
        "reviewed_utc": "2027-01-15T12:00:00Z",
        "reviewer_name": "Test reviewer",
        "review_notes": "Synthetic structural test; no source is cleared.",
        "imd_clearance_sha256": "a" * 64,
        "gefs_clearance_sha256": "b" * 64,
        "annual_reference_sha256": "c" * 64,
        "source_authenticity_and_rights_reviewed": True,
        "gefs_deployment_and_predictors_reviewed": True,
        "independent_test_seal_reconfirmed": True,
    }


def test_v2_protocol_pins_unchanged_v1_and_current_gate_code() -> None:
    protocol = sealed(gate.PROTOCOL)
    assert protocol["v1_score_protocol_sha256"] == sha(gate.frozen.PROTOCOL)
    assert protocol["v1_scorer_sha256"] == sha(Path(gate.frozen.__file__))
    assert protocol["supplemental_auditor_sha256"] == sha(Path(gate.audit.__file__))
    assert protocol["v2_entrypoint_sha256"] == sha(Path(gate.__file__))


def test_current_v2_preflight_blocks_without_observation_read() -> None:
    result = gate.preflight()
    assert result["status"] == "BLOCKED_BEFORE_OBSERVATION_READ"
    assert "IMD_2026_REFERENCE_CLEARANCE_MISSING" in result["reasons"]
    assert "GEFS_2026_VERSION_REVIEW_MISSING" in result["reasons"]
    assert "HUMAN_SOURCE_REVIEW_APPROVAL_MISSING" in result["reasons"]
    assert result["observation_read"] is False
    assert result["score_run"] is False


def test_approval_requires_explicit_review_and_exact_input_hashes() -> None:
    good = _approval()
    assert gate.validate_approval(
        good, reference_sha256="a" * 64, version_sha256="b" * 64,
        annual_sha256="c" * 64,
    ) == []
    weak = {**good, "source_authenticity_and_rights_reviewed": False,
            "imd_clearance_sha256": "d" * 64, "reviewer_name": " "}
    reasons = gate.validate_approval(
        weak, reference_sha256="a" * 64, version_sha256="b" * 64,
        annual_sha256="c" * 64,
    )
    assert "SOURCE_REVIEW_APPROVAL_IDENTITY_OR_DECISION_INVALID" in reasons
    assert "SOURCE_REVIEW_APPROVAL_INPUT_HASH_MISMATCH" in reasons
    assert "SOURCE_REVIEW_APPROVAL_SCOPE_INCOMPLETE" in reasons


def test_blocked_v2_score_never_invokes_frozen_score(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(gate.frozen, "score_once", lambda: pytest.fail("frozen score invoked"))
    with pytest.raises(RuntimeError, match="blocked before observation read"):
        gate.score_once()
    assert not gate.GATE_RESULT.exists()


def test_tampered_protocol_receipt_blocks(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    bad = tmp_path / "score_gate_protocol.json"
    bad.write_text("{}\n", encoding="utf-8")
    monkeypatch.setattr(gate, "PROTOCOL", bad)
    assert "V2_SCORE_GATE_PROTOCOL_SEAL_INVALID" in gate.preflight()["reasons"]
