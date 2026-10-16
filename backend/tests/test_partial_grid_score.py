"""Same-cell scoring and sealed population invariants for partial grids."""

import numpy as np

from scripts import score_partial_grid_candidate as study


def test_metrics_exclude_missing_cells_and_use_24hour_event_thresholds():
    forecast = np.array([[70.0, np.nan], [0.0, 120.0]])
    observed = np.array([[80.0, 200.0], [0.0, 100.0]])
    mask = np.array([[True, False], [True, True]])
    # The generic metric function requires aligned two-dimensional arrays but
    # does not depend on the 49x49 production grid for this pure calculation.
    big_f = np.zeros((49, 49))
    big_o = np.zeros((49, 49))
    big_m = np.zeros((49, 49), dtype=bool)
    big_f[:2, :2], big_o[:2, :2], big_m[:2, :2] = forecast, observed, mask
    result = study.metrics(big_f, big_o, big_m)
    assert result["paired_cells"] == 3
    assert result["squared_error_sum"] == 500
    assert result["events"]["64.5"] == {"hits": 2, "misses": 0, "false_alarms": 0, "correct_negatives": 1}
    assert result["events"]["115.6"]["false_alarms"] == 1


def test_aggregate_requires_same_cells_for_all_models():
    base = {"paired_cells": 2, "squared_error_sum": 8.0, "error_sum": 0.0,
            "events": {"64.5": {"hits": 1, "misses": 0, "false_alarms": 0, "correct_negatives": 1},
                       "115.6": {"hits": 0, "misses": 0, "false_alarms": 0, "correct_negatives": 2}}}
    row = {"cycle": "20240601", "models": {name: dict(base) for name in study.MODELS}}
    report = study.aggregate([row])
    assert report["paired_cells"] == 2
    assert report["models"]["M2"]["rmse_mm"] == 2
    assert report["models"]["M2"]["events"]["64.5"]["csi"] == 1
    row["models"]["M4"] = {**base, "paired_cells": 1}
    try:
        study.aggregate([row])
    except ValueError as error:
        assert "different paired cells" in str(error)
    else:
        raise AssertionError("same-case guard did not reject mismatched cells")


def test_sealed_forecast_population_if_present():
    if not study.forecast.OUT.exists():
        return
    year, digest = study.checked(study.forecast.OUT)
    assert year["observation_read"] is False
    assert year["lead_count"] == 90
    assert year["model_ready_leads"] + year["model_refused_leads"] == 90
    assert digest == study.forecast.sha(study.forecast.OUT)
    assert all(not case["cycle"].startswith("2025") for case in year["cases"])
    for date in ("20240601", "20240621"):
        case_dir = study.forecast.CACHE / date
        if not case_dir.exists():
            continue
        case = study.forecast.verify_case(case_dir, year["protocol_sha256"])
        assert case["observation_read"] is False


def test_saved_same_case_score_recomputes_from_case_counts():
    if not study.OUT.exists():
        return
    result, _ = study.checked(study.OUT)
    assert result["source_track"] == "B_OPERATIONAL_GEFS_DEVELOPMENT_VALIDATION_ONLY"
    assert result["ready_case_count"] + result["refused_case_count"] == 90
    assert result["common_cell_comparison"] is True
    assert study.aggregate(result["cases"]) == result["summary"]["all_ready"]
    withheld = [case for case in result["cases"] if not case["strict_passed"]]
    assert study.aggregate(withheld) == result["summary"]["strict_withheld_ready"]
    assert all(case["models"]["M0"]["paired_cells"] == case["models"]["M2"]["paired_cells"] == case["models"]["M4"]["paired_cells"] for case in result["cases"])
