"""Deterministic, outcome-blind sampling and annotation checks for regime review."""

from __future__ import annotations

import hashlib
from collections import Counter, defaultdict
from datetime import datetime, timezone

TASKS = ("active_monsoon", "break_weak_monsoon", "low_depression", "coastal_orographic", "western_disturbance")
LABELS = {"present", "absent", "uncertain"}


def select_cases(cases: list[dict], per_stratum: int = 2) -> list[dict]:
    """Choose by year, JJAS month and lead using only immutable case metadata."""
    if per_stratum < 1:
        raise ValueError("per_stratum must be positive")
    strata: dict[tuple[int, int, str], list[dict]] = defaultdict(list)
    seen: set[str] = set()
    for case in cases:
        case_id = case["case_id"]
        if case_id in seen:
            raise ValueError(f"duplicate case ID: {case_id}")
        seen.add(case_id)
        if case["status"] != "INCLUDED":
            continue
        issue = case["initialization"]
        year, month = int(issue[:4]), int(issue[5:7])
        if month not in (6, 7, 8, 9) or case["product"] not in ("day1_24h", "day2_24h", "day3_24h"):
            raise ValueError(f"unexpected JJAS case: {case_id}")
        strata[(year, month, case["product"])].append(case)
    chosen = []
    for key, group in sorted(strata.items()):
        if len(group) < per_stratum:
            raise ValueError(f"insufficient cases in stratum {key}")
        chosen.extend(sorted(group, key=lambda c: (hashlib.sha256(c["case_id"].encode("ascii")).hexdigest(), c["case_id"]))[:per_stratum])
    return sorted(chosen, key=lambda c: c["case_id"])


def validate_annotations(rows: list[dict], packet_case_ids: set[str], *, final: bool = False) -> dict:
    """Validate blind first-pass forms; never inspect detector outputs or outcomes."""
    seen: set[tuple[str, str]] = set()
    counts: Counter[str] = Counter()
    for row in rows:
        case_id, reviewer = row.get("case_id", ""), row.get("reviewer_id", "").strip()
        if case_id not in packet_case_ids or not reviewer:
            raise ValueError("unknown case or empty reviewer ID")
        key = (case_id, reviewer)
        if key in seen:
            raise ValueError(f"duplicate independent review: {key}")
        seen.add(key)
        counts[case_id] += 1
        if not row.get("annotation_utc", "").strip():
            raise ValueError(f"missing annotation time: {key}")
        try:
            stamp = datetime.fromisoformat(row["annotation_utc"].replace("Z", "+00:00"))
        except ValueError as error:
            raise ValueError(f"invalid annotation time: {key}") from error
        if stamp.tzinfo is None or stamp.astimezone(timezone.utc).utcoffset() is None:
            raise ValueError(f"annotation time needs timezone: {key}")
        if row.get("rubric_version") != "expert-regime-review-v1":
            raise ValueError(f"incorrect rubric version: {key}")
        for task in TASKS:
            label = row.get(task, "")
            if label not in LABELS:
                raise ValueError(f"invalid {task} label: {key}")
            if label == "present" and (not row.get(f"{task}_rationale", "").strip() or not row.get(f"{task}_evidence", "").strip()):
                raise ValueError(f"uncited positive {task}: {key}")
            if label == "uncertain" and not row.get(f"{task}_uncertainty_reason", "").strip():
                raise ValueError(f"unexplained uncertainty {task}: {key}")
    if final and (set(counts) != packet_case_ids or min(counts.values(), default=0) < 2):
        raise ValueError("at least two independent reviewers are required for every case")
    return {"cases_reviewed": len(counts), "review_rows": len(rows), "cases_with_two_reviewers": sum(n >= 2 for n in counts.values())}
