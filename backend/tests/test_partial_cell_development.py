"""Partial-cell experiment invariants, separate from the live QC path."""

import numpy as np

from scripts import run_partial_cell_development as study


def test_protocol_is_sealed_before_pairing_and_excludes_consumed_test_years():
    protocol, digest = study.checked(study.PROTOCOL)
    assert digest == study.sha(study.PROTOCOL)
    assert protocol["years"] == {"2023": "design_development", "2024": "validation_development"}
    assert "2025 consumed test" in protocol["excluded"]
    assert "2026 independent-test candidate" in protocol["excluded"]
    assert protocol["minimum_regional_coverage_fraction_for_future_consideration"] == 0.99


def test_missing_cells_never_enter_paired_rainfall_metrics():
    forecast = np.array([[70.0, np.nan], [0.0, 120.0]])
    observed = np.array([[80.0, 200.0], [0.0, 100.0]])
    valid = np.isfinite(forecast)
    result = study.case_measure(forecast, observed, valid, np.ones((2, 2), dtype=bool))
    assert result["paired_cells"] == 3
    assert result["squared_error_sum"] == 500.0
    assert result["events"]["64.5"] == {"hits": 2, "misses": 0, "false_alarms": 0, "correct_negatives": 1}
    assert result["events"]["115.6"]["misses"] == 0


def test_saved_result_if_present_preserves_development_only_semantics():
    if not study.OUT.is_file():
        return
    result, _ = study.checked(study.OUT)
    assert result["model_inference"] is False
    assert result["changes_canonical_qc"] is False
    assert result["source_track"] == "B_OPERATIONAL_GEFS_DEVELOPMENT_ONLY"
    assert [entry["year"] for entry in result["year_results"]] == [2023, 2024]
    assert sum(entry["case_count"] for entry in result["year_results"]) == 180
    rows = [row for year in result["year_results"] for row in year["rows"]]
    assert sum(row["strict_passed"] for row in rows) == result["strict_passing_leads"]
    assert sum(not row["strict_passed"] for row in rows) == result["strict_withheld_leads"]
    assert sum(row["valid_cells"] / 2401 >= .99 for row in rows) == result["masked_leads_with_at_least_99pct_regional_coverage"]
    assert all(row["raw_on_paired_cells"]["paired_cells"] == row["paired_valid_cells"] for row in rows)
    assert all(row["invalid_cells"] == 0 for row in rows if row["strict_passed"])
    assert all(row["invalid_cells"] > 0 for row in rows if not row["strict_passed"])
