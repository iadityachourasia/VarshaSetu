from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from backend.app.ml.expert_regime_review import TASKS
from backend.app.ml.regime_annotation_review import (
    validate_adjudications,
    validate_reviews,
    validate_source_ledger,
    verify_frozen_material,
    verify_packet,
)


def _fixture() -> tuple[dict, list[dict], dict, dict]:
    packet = {"cases": [{"case_id": "20140609_day1_24h", "issue_utc": "2014-06-09T00:00:00Z",
                         "lead_window_h": [3, 27]}]}
    source = {"source_id": "b1", "kind": "dated_bulletin", "uri": "https://example.org/dated.pdf",
              "sha256": "a" * 64, "issued_utc": "2014-06-10T12:00:00Z",
              "valid_start_utc": "2014-06-09T00:00:00Z", "valid_end_utc": "2014-06-11T00:00:00Z",
              "use_rights": "local_review_only", "local_path": "bulletin.pdf"}
    sources = validate_source_ledger([source])
    roster = {"reviewer_ids": ["expert-a", "expert-b"], "adjudicator_id": "expert-c",
              "frozen_utc": "2014-06-01T00:00:00Z", "rubric_sha256": "a" * 64,
              "analysis_code_sha256": "c" * 64}
    reviews = []
    for reviewer in roster["reviewer_ids"]:
        row = {"case_id": "20140609_day1_24h", "reviewer_id": reviewer,
               "rubric_version": "expert-regime-review-v1", "annotation_utc": "2026-10-07T12:00:00Z",
               "blind_to_detector_outputs": "true"}
        row.update({task: "absent" for task in TASKS})
        reviews.append(row)
    return packet, reviews, roster, sources


def test_packet_hash_and_map_verification(tmp_path: Path) -> None:
    map_dir = tmp_path / "forecast_maps"
    map_dir.mkdir()
    (map_dir / "x.png").write_bytes(b"forecast-only map")
    map_hash = hashlib.sha256(b"forecast-only map").hexdigest()
    packet = {"schema": "expert-regime-review-packet-v1", "case_count": 1,
              "cases": [{"case_id": "x", "forecast_fields_png": "forecast_maps/x.png",
                         "forecast_fields_sha256": map_hash}]}
    path = tmp_path / "packet.json"
    path.write_text(json.dumps(packet), encoding="utf-8")
    path.with_suffix(".sha256").write_text(hashlib.sha256(path.read_bytes()).hexdigest() + "  packet.json\n")
    assert verify_packet(path, map_root=tmp_path)["case_count"] == 1
    (map_dir / "x.png").write_bytes(b"changed")
    with pytest.raises(ValueError, match="map hash mismatch"):
        verify_packet(path, map_root=tmp_path)


def test_complete_review_requires_real_evidence_and_distinct_reviewers() -> None:
    packet, reviews, roster, sources = _fixture()
    assert validate_reviews(packet, reviews, roster, sources)["review_count"] == 2
    reviews[0]["active_monsoon"] = "present"
    reviews[0]["active_monsoon_rationale"] = "Broad moist westerly flow"
    reviews[0]["active_monsoon_evidence_ids"] = "b1"
    assert validate_reviews(packet, reviews, roster, sources)["case_count"] == 1
    reviews[0]["active_monsoon_evidence_ids"] = "missing"
    with pytest.raises(ValueError, match="inventoried evidence"):
        validate_reviews(packet, reviews, roster, sources)
    reviews[0]["active_monsoon_evidence_ids"] = "b1"
    with pytest.raises(ValueError, match="incomplete independent review"):
        validate_reviews(packet, reviews[:1], roster, sources)
    roster["adjudicator_id"] = "expert-a"
    with pytest.raises(ValueError, match="distinct adjudicator"):
        validate_reviews(packet, reviews, roster, sources)


def test_adjudication_preserves_disagreement_and_requires_blind_third_reviewer() -> None:
    packet, reviews, roster, sources = _fixture()
    reviews[0]["low_depression"] = "present"
    reviews[0]["low_depression_rationale"] = "Closed circulation"
    reviews[0]["low_depression_evidence_ids"] = "b1"
    validate_reviews(packet, reviews, roster, sources)
    with pytest.raises(ValueError, match="unresolved disagreements"):
        validate_adjudications(packet, reviews, [], roster, sources)
    adjudication = {"case_id": "20140609_day1_24h", "task": "low_depression",
                    "adjudicator_id": "expert-c", "decision": "present",
                    "adjudication_utc": "2026-10-08T12:00:00Z", "rationale": "Bulletin and map agree",
                    "evidence_ids": "b1", "blind_to_detector_outputs": "true"}
    result = validate_adjudications(packet, reviews, [adjudication], roster, sources)
    assert result["disagreement_count"] == 1
    assert reviews[1]["low_depression"] == "absent"
    adjudication["adjudication_utc"] = "2026-10-06T12:00:00Z"
    with pytest.raises(ValueError, match="predates reviews"):
        validate_adjudications(packet, reviews, [adjudication], roster, sources)


def test_source_ledger_rejects_unconfirmed_rights_and_bad_validity() -> None:
    _, _, _, sources = _fixture()
    source = dict(sources["b1"])
    source["use_rights"] = "unknown"
    with pytest.raises(ValueError, match="rights unconfirmed"):
        validate_source_ledger([source])
    source["use_rights"] = "local_review_only"
    source["valid_end_utc"] = source["valid_start_utc"]
    with pytest.raises(ValueError, match="validity window"):
        validate_source_ledger([source])


def test_source_ledger_checks_actual_local_bytes(tmp_path: Path) -> None:
    _, _, _, sources = _fixture()
    source = dict(sources["b1"])
    (tmp_path / "bulletin.pdf").write_bytes(b"dated source")
    source["sha256"] = hashlib.sha256(b"dated source").hexdigest()
    assert validate_source_ledger([source], source_root=tmp_path)["b1"]["kind"] == "dated_bulletin"
    (tmp_path / "bulletin.pdf").write_bytes(b"tampered")
    with pytest.raises(ValueError, match="source file hash mismatch"):
        validate_source_ledger([source], source_root=tmp_path)


def test_postseason_source_is_allowed_but_must_predate_annotation() -> None:
    packet, reviews, roster, sources = _fixture()
    sources["b1"]["issued_utc"] = "2026-10-06T12:00:00Z"
    reviews[0]["active_monsoon"] = "present"
    reviews[0]["active_monsoon_rationale"] = "Broad moist westerly flow"
    reviews[0]["active_monsoon_evidence_ids"] = "b1"
    validate_reviews(packet, reviews, roster, sources)
    sources["b1"]["issued_utc"] = "2026-10-08T12:00:00Z"
    with pytest.raises(ValueError, match="issued after annotation"):
        validate_reviews(packet, reviews, roster, sources)


def test_every_cited_positive_source_must_overlap_case() -> None:
    packet, reviews, roster, sources = _fixture()
    outside = dict(sources["b1"])
    outside["source_id"] = "elsewhere"
    outside["valid_start_utc"] = "2014-07-01T00:00:00Z"
    outside["valid_end_utc"] = "2014-07-02T00:00:00Z"
    sources["elsewhere"] = outside
    reviews[0]["active_monsoon"] = "present"
    reviews[0]["active_monsoon_rationale"] = "Broad moist westerly flow"
    reviews[0]["active_monsoon_evidence_ids"] = "b1;elsewhere"
    with pytest.raises(ValueError, match="does not overlap case"):
        validate_reviews(packet, reviews, roster, sources)


def test_frozen_roster_hashes_are_verified_against_files(tmp_path: Path) -> None:
    rubric = tmp_path / "rubric.md"
    code = tmp_path / "analysis.py"
    rubric.write_bytes(b"rubric")
    code.write_bytes(b"analysis")
    roster = {"rubric_sha256": hashlib.sha256(b"rubric").hexdigest(),
              "analysis_code_sha256": hashlib.sha256(b"analysis").hexdigest()}
    verify_frozen_material(roster, rubric_path=rubric, analysis_path=code)
    code.write_bytes(b"changed")
    with pytest.raises(ValueError, match="analysis code hash mismatch"):
        verify_frozen_material(roster, rubric_path=rubric, analysis_path=code)
