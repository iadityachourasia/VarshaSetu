"""Blind, provenance-checked independent regime annotation review.

This module handles human annotations only. It never infers a label from a
forecast, bulletin text, pseudo-label, rainfall observation, or detector score.
"""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from backend.app.ml.expert_regime_review import LABELS, TASKS

RUBRIC = "expert-regime-review-v1"
SOURCE_KINDS = {"dated_bulletin", "forecast_map", "other_dated_synoptic_record"}
DECISIONS = {"present", "absent", "uncertain"}


def _utc(value: str, name: str) -> datetime:
    try:
        result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (AttributeError, ValueError) as error:
        raise ValueError(f"invalid {name}") from error
    if result.tzinfo is None:
        raise ValueError(f"{name} must have a timezone")
    return result.astimezone(timezone.utc)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify_frozen_material(roster: dict, *, rubric_path: Path, analysis_path: Path) -> None:
    """Bind the supplied pre-review roster to the actual rubric and validator."""
    if _sha256(rubric_path) != roster.get("rubric_sha256"):
        raise ValueError("frozen rubric hash mismatch")
    if _sha256(analysis_path) != roster.get("analysis_code_sha256"):
        raise ValueError("frozen analysis code hash mismatch")


def verify_packet(packet_path: Path, *, map_root: Path | None = None) -> dict:
    """Verify the frozen packet and optionally every locally available map."""
    expected = packet_path.with_suffix(".sha256").read_text(encoding="ascii").split()[0]
    if _sha256(packet_path) != expected:
        raise ValueError("packet SHA-256 sidecar mismatch")
    packet = json.loads(packet_path.read_text(encoding="utf-8"))
    cases = packet["cases"]
    if packet["schema"] != "expert-regime-review-packet-v1" or packet["case_count"] != len(cases):
        raise ValueError("unexpected packet schema or count")
    if len({case["case_id"] for case in cases}) != len(cases):
        raise ValueError("duplicate packet case ID")
    if map_root is not None:
        root = map_root.resolve()
        for case in cases:
            relative = Path(case["forecast_fields_png"])
            if relative.is_absolute() or ".." in relative.parts:
                raise ValueError("unsafe map path")
            target = (root / relative).resolve()
            if not target.is_relative_to(root):
                raise ValueError("map path escapes packet directory")
            if _sha256(target) != case["forecast_fields_sha256"]:
                raise ValueError(f"forecast map hash mismatch: {case['case_id']}")
    return packet


def validate_source_ledger(sources: list[dict], *, source_root: Path | None = None) -> dict[str, dict]:
    """Validate metadata, never the content or authority of a bulletin."""
    indexed: dict[str, dict] = {}
    for source in sources:
        source_id = source["source_id"].strip()
        if not source_id or source_id in indexed:
            raise ValueError("empty or duplicate source ID")
        if source["kind"] not in SOURCE_KINDS:
            raise ValueError(f"unknown source kind: {source_id}")
        if not source.get("uri", "").strip():
            raise ValueError(f"missing source URI: {source_id}")
        digest = source.get("sha256", "")
        if len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest):
            raise ValueError(f"missing or invalid source hash: {source_id}")
        _utc(source["issued_utc"], "issued_utc")
        start = _utc(source["valid_start_utc"], "valid_start_utc")
        end = _utc(source["valid_end_utc"], "valid_end_utc")
        if not start < end:
            raise ValueError(f"invalid source validity window: {source_id}")
        # A post-season report can describe an earlier case. Its issue time is
        # retained so it cannot be mistaken for forecast-time information.
        if source.get("use_rights") not in {"local_review_only", "redistribution_permitted"}:
            raise ValueError(f"source rights unconfirmed: {source_id}")
        if source_root is not None:
            relative = Path(source.get("local_path", ""))
            if str(relative) == "." or relative.is_absolute() or ".." in relative.parts:
                raise ValueError(f"unsafe or missing source file path: {source_id}")
            root = source_root.resolve()
            target = (root / relative).resolve()
            if not target.is_relative_to(root):
                raise ValueError(f"source path escapes source directory: {source_id}")
            if _sha256(target) != digest:
                raise ValueError(f"source file hash mismatch: {source_id}")
        indexed[source_id] = source
    return indexed


def validate_reviews(packet: dict, reviews: list[dict], roster: dict, sources: dict[str, dict]) -> dict:
    """Require two distinct, complete first-pass reviews for each frozen case."""
    cases = {case["case_id"]: case for case in packet["cases"]}
    reviewers = roster.get("reviewer_ids", [])
    adjudicator = roster.get("adjudicator_id")
    if len(reviewers) != 2 or len(set(reviewers)) != 2 or not all(isinstance(x, str) and x.strip() for x in reviewers) or not adjudicator or adjudicator in reviewers:
        raise ValueError("two independent reviewers and a distinct adjudicator required")
    if not roster.get("frozen_utc") or not roster.get("rubric_sha256") or not roster.get("analysis_code_sha256"):
        raise ValueError("roster, rubric and analysis code must be frozen before review")
    for name in ("rubric_sha256", "analysis_code_sha256"):
        digest = roster[name]
        if len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest):
            raise ValueError(f"invalid {name}")
    frozen = _utc(roster["frozen_utc"], "frozen_utc")
    expected = {(case_id, reviewer) for case_id in cases for reviewer in reviewers}
    seen: set[tuple[str, str]] = set()
    for row in reviews:
        key = (row.get("case_id"), row.get("reviewer_id"))
        if key not in expected or key in seen:
            raise ValueError(f"unknown or duplicate case/reviewer: {key}")
        seen.add(key)
        if row.get("rubric_version") != RUBRIC:
            raise ValueError(f"rubric mismatch: {key}")
        if row.get("blind_to_detector_outputs") != "true":
            raise ValueError(f"review blinding declaration missing: {key}")
        annotated = _utc(row["annotation_utc"], "annotation_utc")
        if annotated <= frozen:
            raise ValueError(f"review precedes roster freeze: {key}")
        for task in TASKS:
            label = row.get(task)
            if label not in LABELS:
                raise ValueError(f"missing or invalid {task}: {key}")
            if label == "uncertain" and not row.get(f"{task}_uncertainty_reason", "").strip():
                raise ValueError(f"uncertainty requires reason: {key}, {task}")
            if label == "present":
                if not row.get(f"{task}_rationale", "").strip():
                    raise ValueError(f"positive requires physical rationale: {key}, {task}")
                evidence_ids = [part.strip() for part in row.get(f"{task}_evidence_ids", "").split(";") if part.strip()]
                if not evidence_ids or any(source_id not in sources for source_id in evidence_ids):
                    raise ValueError(f"positive requires inventoried evidence: {key}, {task}")
                if not all(_overlaps_case(cases[key[0]], sources[source_id]) for source_id in evidence_ids):
                    raise ValueError(f"evidence does not overlap case: {key}, {task}")
                if any(_utc(sources[source_id]["issued_utc"], "issued_utc") > annotated for source_id in evidence_ids):
                    raise ValueError(f"evidence issued after annotation: {key}, {task}")
    if seen != expected:
        raise ValueError(f"incomplete independent review: {len(seen)}/{len(expected)}")
    return {"case_count": len(cases), "review_count": len(reviews), "reviewer_ids": sorted(reviewers)}


def _overlaps_case(case: dict, source: dict) -> bool:
    case_start = _utc(case["issue_utc"], "issue_utc")
    # Source can be a later retrospective report, but must concern the case's
    # forecast window; it can never become a forecast-time model predictor.
    end_hour = case["lead_window_h"][1]
    from datetime import timedelta

    case_end = case_start + timedelta(hours=end_hour)
    return _utc(source["valid_start_utc"], "valid_start_utc") < case_end and _utc(source["valid_end_utc"], "valid_end_utc") > case_start


def validate_adjudications(packet: dict, reviews: list[dict], adjudications: list[dict], roster: dict,
                           sources: dict[str, dict]) -> dict:
    """Adjudicate disagreements without altering either original review."""
    by_key = {(row["case_id"], row["reviewer_id"]): row for row in reviews}
    reviewer_a, reviewer_b = roster["reviewer_ids"]
    disagreements = {(case["case_id"], task) for case in packet["cases"] for task in TASKS
                     if by_key[(case["case_id"], reviewer_a)][task] != by_key[(case["case_id"], reviewer_b)][task]}
    seen: set[tuple[str, str]] = set()
    for row in adjudications:
        key = (row.get("case_id"), row.get("task"))
        if key not in disagreements or key in seen:
            raise ValueError(f"unrequested or duplicate adjudication: {key}")
        seen.add(key)
        if row.get("adjudicator_id") != roster["adjudicator_id"]:
            raise ValueError(f"wrong adjudicator: {key}")
        if row.get("blind_to_detector_outputs") != "true":
            raise ValueError(f"adjudication blinding declaration missing: {key}")
        if row.get("decision") not in DECISIONS or not row.get("rationale", "").strip():
            raise ValueError(f"decision and rationale required: {key}")
        adjudicated = _utc(row["adjudication_utc"], "adjudication_utc")
        if adjudicated <= max(
            _utc(by_key[(key[0], reviewer_a)]["annotation_utc"], "annotation_utc"),
            _utc(by_key[(key[0], reviewer_b)]["annotation_utc"], "annotation_utc"),
        ):
            raise ValueError(f"adjudication predates reviews: {key}")
        evidence_ids = [part.strip() for part in row.get("evidence_ids", "").split(";") if part.strip()]
        if row["decision"] == "present":
            if not evidence_ids or any(source_id not in sources for source_id in evidence_ids):
                raise ValueError(f"positive adjudication needs inventoried evidence: {key}")
            case = next(case for case in packet["cases"] if case["case_id"] == key[0])
            if not all(_overlaps_case(case, sources[source_id]) for source_id in evidence_ids):
                raise ValueError(f"adjudication evidence does not overlap case: {key}")
            if any(_utc(sources[source_id]["issued_utc"], "issued_utc") > adjudicated for source_id in evidence_ids):
                raise ValueError(f"adjudication evidence issued after adjudication: {key}")
        if row["decision"] == "uncertain" and not row.get("uncertainty_reason", "").strip():
            raise ValueError(f"uncertain adjudication needs reason: {key}")
    if seen != disagreements:
        raise ValueError(f"unresolved disagreements: {len(disagreements - seen)}")
    agreement = Counter()
    for case in packet["cases"]:
        for task in TASKS:
            a = by_key[(case["case_id"], reviewer_a)][task]
            b = by_key[(case["case_id"], reviewer_b)][task]
            agreement[task] += int(a == b)
    return {"disagreement_count": len(disagreements), "adjudication_count": len(seen),
            "exact_agreement_by_task": dict(agreement), "case_count": len(packet["cases"]),
            "status": "ADJUDICATED_BLIND_REVIEW_ONLY_NO_DETECTOR_SCORE"}
