"""The RSMC page finder produces bibliographic leads, not case labels."""

from datetime import date

import pytest

from scripts.build_regime_report_page_index import _verified_json, candidate_pages


def test_exact_day_month_and_matching_explicit_year_only():
    pages = ["10 June 2014: event", "June 10, 2014", "10th Jun: context",
             "10 June 2013: old comparison", "11 June 2014", "1 June 2014"]
    assert candidate_pages(pages, date(2014, 6, 10)) == [1, 2, 3]


def test_zero_hits_are_not_synthetic_absence():
    assert candidate_pages(["A 10-12 June range", "No dated source here"], date(2015, 6, 11)) == []
    assert candidate_pages(["September 1, 2015", "01 Sept 2015"], date(2015, 9, 1)) == [1, 2]


def test_json_receipt_tamper_is_refused(tmp_path):
    item = tmp_path / "index.json"
    item.write_text('{"case_count": 72}\n', encoding="utf-8")
    item.with_suffix(".sha256").write_text("0" * 64 + "  index.json\n", encoding="utf-8")
    with pytest.raises(RuntimeError, match="checksum mismatch"):
        _verified_json(item)
