"""Date-paired spatial FSS aggregation without scientific data fixtures."""

from scripts import score_nationwide_probability_spatial as spatial


def test_spatial_sums_and_date_bootstrap_keep_arms_paired() -> None:
    rows = []
    for day in ("20240601", "20240602", "20240603"):
        for arm, numerator in (("v1", 1.0), ("v2", 1.5), ("v4", 0.5)):
            rows.append({"case_id": day + "_day1_24h", "arm": arm,
                         "numerator": numerator, "denominator": 2.0,
                         "eligible_centers": 4, "paired_cells": 4,
                         "forecast_events": 2, "observed_events": 2,
                         "hits": 1})
    v4 = spatial._sum_records([row for row in rows if row["arm"] == "v4"])
    assert v4["fss"] == 0.75
    assert v4["contributing_cases"] == 3
    bootstrap = spatial._bootstrap(rows, seed=26080, repeats=50)
    assert bootstrap["status"] == "defined"
    assert bootstrap["initialization_dates"] == 3
    assert bootstrap["v4_minus_v1_ci95"] == [0.25, 0.25]
    assert bootstrap["v4_minus_v2_ci95"] == [0.5, 0.5]
