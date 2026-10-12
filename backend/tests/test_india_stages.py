"""Bounded India-stage forecast, pairing and district refusal rules."""

from dataclasses import replace

import numpy as np
import pytest

from backend.app.live import india_stages as stages
from backend.app.ml.all_india_raw import region_masks


def example():
    land = np.ones(stages.GRID_SHAPE, dtype=bool)
    footprint = stages.stage_mask(stages.FIRST_STAGE, land)
    valid = np.zeros(stages.GRID_SHAPE, dtype=bool)
    cells = np.flatnonzero(footprint.ravel())[:3]
    valid.ravel()[cells] = True
    raw = np.full(stages.GRID_SHAPE, np.nan)
    corrected = raw.copy()
    raw.ravel()[cells] = [5, 70, 120]
    corrected.ravel()[cells] = [7, 65, 110]
    lineage = stages.StageLineage("20240601_day1_24h", "a" * 64, "b" * 64, stages.FIRST_STAGE, "c" * 64)
    forecast = stages.forecast_field(stages.FIRST_STAGE, land, raw, corrected, valid, lineage)
    return forecast, cells, land, raw, corrected, valid, lineage


def test_stage_is_the_existing_frozen_raw_partition():
    land = np.ones(stages.GRID_SHAPE, dtype=bool)
    expected = region_masks(stages.IMD_LAT, stages.IMD_LON)[stages.FIRST_STAGE].reshape(stages.GRID_SHAPE)
    assert np.array_equal(stages.stage_mask(stages.FIRST_STAGE, land), expected)
    assert not np.any(expected & region_masks(stages.IMD_LAT, stages.IMD_LON)["INSIDE_MODEL_DOMAIN"].reshape(stages.GRID_SHAPE))
    with pytest.raises(ValueError, match="first bounded"):
        stages.stage_mask("NORTH_OF_DOMAIN", land)


def test_forecast_requires_stage_specific_model_joint_validity_and_nonnegative_rain():
    forecast, cells, land, raw, corrected, valid, lineage = example()
    assert forecast["valid_cells"] == 3
    assert "observation" not in forecast
    with pytest.raises(ValueError, match="not trained"):
        stages.forecast_field(stages.FIRST_STAGE, land, raw, corrected, valid, replace(lineage, model_training_domain="INSIDE_MODEL_DOMAIN"))
    bad = corrected.copy()
    bad.ravel()[cells[1]] = np.nan
    with pytest.raises(ValueError, match="same valid cells"):
        stages.forecast_field(stages.FIRST_STAGE, land, raw, bad, valid, lineage)
    bad = corrected.copy()
    bad.ravel()[cells[1]] = -1
    with pytest.raises(ValueError, match="same valid cells"):
        stages.forecast_field(stages.FIRST_STAGE, land, raw, bad, valid, lineage)
    bad = corrected.copy()
    bad.ravel()[0] = 0
    with pytest.raises(ValueError, match="same valid cells"):
        stages.forecast_field(stages.FIRST_STAGE, land, raw, bad, valid, lineage)


def test_reference_pair_uses_identical_cells_and_counts_events():
    forecast, cells, *_ = example()
    observed = np.full(stages.GRID_SHAPE, np.nan)
    mask = np.zeros(stages.GRID_SHAPE, dtype=bool)
    mask.ravel()[cells[:2]] = True
    observed.ravel()[cells[:2]] = [6, 80]
    paired = stages.pair_reference(forecast, observed, mask)
    assert paired["paired_cells"] == 2
    assert paired["observed_events"] == {"heavy": 1, "very_heavy": 0}
    assert paired["raw_squared_error"] == pytest.approx(101)
    assert paired["global_squared_error"] == pytest.approx(226)
    mask[:] = False
    with pytest.raises(ValueError, match="no forecast/reference"):
        stages.pair_reference(forecast, np.full(stages.GRID_SHAPE, np.nan), mask)
    mask.ravel()[cells[:2]] = True
    boundary = np.full(stages.GRID_SHAPE, np.nan)
    boundary.ravel()[cells[:2]] = [64.5, 115.6]
    assert stages.pair_reference(forecast, boundary, mask)["observed_events"] == {"heavy": 2, "very_heavy": 1}


def test_district_coverage_withholds_unsupported_mean():
    forecast, cells, *_ = example()
    weights = np.zeros((2, np.prod(stages.GRID_SHAPE)))
    weights[0, cells] = [1, 1, 1]
    weights[1, cells] = [1, 1, 1]
    extra = np.flatnonzero(forecast["footprint"].ravel() & ~forecast["valid_mask"].ravel())[0]
    weights[1, extra] = 1
    districts = [{"district_id": "one", "district_name": "One"}, {"district_id": "two", "district_name": "Two"}]
    rows = stages.district_rows(forecast, districts, weights)
    assert rows[0]["supported"] and rows[0]["raw_mean_mm"] == pytest.approx(65)
    assert not rows[1]["supported"] and rows[1]["global_mean_mm"] is None
    assert rows[1]["coverage_fraction"] == pytest.approx(0.75)
    outside = np.flatnonzero(~forecast["footprint"].ravel())[0]
    weights[0, outside] = 1
    with pytest.raises(ValueError, match="weights"):
        stages.district_rows(forecast, districts, weights)


def test_evidence_gate_refuses_consumed_test_low_support_and_unreviewed_geometry():
    forecast, cells, *_ = example()
    observed = np.full(stages.GRID_SHAPE, np.nan)
    mask = forecast["valid_mask"]
    observed.ravel()[cells] = [6, 80, 130]
    pair = stages.pair_reference(forecast, observed, mask)
    tables = {pair["case_id"]: [{"district_id": "one", "coverage_fraction": 1.0, "supported": True}]}
    result = stages.evidence_gate([pair], tables, independent_year=False, consumed_test=True,
                                  geometry_version="2021-simplified", geometry_sha256="d" * 64, rights_reviewed=False)
    assert result["cases"] == 1 and result["observed_events"] == {"heavy": 2, "very_heavy": 1}
    assert not result["eligible_for_review"] and len(result["reasons"]) == 3
    with pytest.raises(ValueError, match="unique"):
        stages.evidence_gate([pair, pair], tables, independent_year=True, consumed_test=False,
                              geometry_version="v1", geometry_sha256="d" * 64, rights_reviewed=True)
    tables[pair["case_id"]][0].update(coverage_fraction=0.5, supported=False)
    result = stages.evidence_gate([pair], tables, independent_year=True, consumed_test=False,
                                  geometry_version="v1", geometry_sha256="d" * 64, rights_reviewed=True)
    assert not result["eligible_for_review"] and any("district" in reason for reason in result["reasons"])
    tables[pair["case_id"]][0]["supported"] = True
    with pytest.raises(ValueError, match="disagrees"):
        stages.evidence_gate([pair], tables, independent_year=True, consumed_test=False,
                              geometry_version="v1", geometry_sha256="d" * 64, rights_reviewed=True)
