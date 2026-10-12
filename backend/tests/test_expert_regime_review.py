from __future__ import annotations

import pytest

from backend.app.ml.expert_regime_review import TASKS, select_cases, validate_annotations


def _case(year: int, month: int, day: int, product: str, status: str = "INCLUDED") -> dict:
    return {"case_id": f"{year}{month:02}{day:02}_{product}", "initialization": f"{year}-{month:02}-{day:02}",
            "product": product, "status": status}


def test_select_cases_balances_calendar_and_lead_without_outcomes() -> None:
    cases = [_case(y, m, d, p) for y in (2014, 2015, 2016) for m in (6, 7, 8, 9)
             for p in ("day1_24h", "day2_24h", "day3_24h") for d in range(1, 5)]
    cases.append(_case(2014, 6, 5, "day1_24h", "EXCLUDED_RECONSTRUCTION"))
    a = select_cases(cases)
    b = select_cases(list(reversed(cases)))
    assert [c["case_id"] for c in a] == [c["case_id"] for c in b]
    assert len(a) == 72
    assert all(c["status"] == "INCLUDED" for c in a)


def test_sampling_rejects_duplicate_and_underfilled_strata() -> None:
    with pytest.raises(ValueError, match="duplicate"):
        select_cases([_case(2014, 6, 1, "day1_24h")] * 2)
    with pytest.raises(ValueError, match="insufficient"):
        select_cases([_case(2014, 6, 1, "day1_24h")])


def _review(case: str, reviewer: str) -> dict:
    row = {"case_id": case, "reviewer_id": reviewer, "annotation_utc": "2026-10-07T12:00:00Z", "rubric_version": "expert-regime-review-v1"}
    row.update({task: "absent" for task in TASKS})
    return row


def test_review_requires_two_distinct_reviewers_and_cited_positives() -> None:
    a, b = _review("case-1", "A"), _review("case-1", "B")
    assert validate_annotations([a, b], {"case-1"}, final=True)["cases_with_two_reviewers"] == 1
    with pytest.raises(ValueError, match="duplicate"):
        validate_annotations([a, a], {"case-1"}, final=True)
    with pytest.raises(ValueError, match="two independent"):
        validate_annotations([a], {"case-1"}, final=True)
    a["active_monsoon"] = "present"
    with pytest.raises(ValueError, match="uncited positive"):
        validate_annotations([a], {"case-1"})
    a["active_monsoon_rationale"] = "Broad monsoon flow and moist layer"
    a["active_monsoon_evidence"] = "local:bulletin-sha256:abc, issued 2014-07-01T00:00Z"
    assert validate_annotations([a], {"case-1"})["review_rows"] == 1


def test_review_requires_uncertainty_reason() -> None:
    row = _review("case-1", "A")
    row["western_disturbance"] = "uncertain"
    with pytest.raises(ValueError, match="unexplained uncertainty"):
        validate_annotations([row], {"case-1"})
