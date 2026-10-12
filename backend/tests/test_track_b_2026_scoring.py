from __future__ import annotations

from datetime import date

import numpy as np
import pytest
from scipy.io import netcdf_file

from backend.app.ml.track_b_2026_scoring import score_cases, validate_case
from scripts import score_2026_frozen_inference as runner
from scripts.score_2026_frozen_inference import ImdYear


def _case(cycle: str, *, incoherent: bool = False) -> dict:
    observed = np.zeros((49, 49), dtype=np.float64)
    observed[20, 20] = 80.0
    mask = np.ones((49, 49), dtype=bool)
    mask[0, 0] = False
    observed[0, 0] = np.nan
    rain = {name: np.zeros((49, 49), dtype=np.float32) for name in ("M0", "M1", "M2", "M3", "M4")}
    rain["M0"][20, 20] = 80
    rain["M4"][20, 20] = 80
    heavy = np.full((49, 49), 0.2)
    very = np.full((49, 49), 0.1)
    if incoherent:
        very[20, 20] = 0.3
    return {"cycle": cycle, "lead": "day1_24h", "version_stratum": "before_announced_change" if cycle < "20260616" else "after_announced_change",
            "observed": observed, "valid_mask": mask, "rainfall": rain,
            "heavy_probability": heavy, "very_heavy_probability": very,
            "regime_probability": np.array([0.3, 0.2, 0.5]),
            "nested_probability_violating_cells": int(incoherent)}


def test_same_cell_scoring_and_probability_refusal() -> None:
    cases = [_case("20260610"), _case("20260620", incoherent=True)]
    result = score_cases(cases, climatology={"heavy": 0.01, "very_heavy": 0.001},
                         probability_cutoffs={"heavy": 0.1, "very_heavy": 0.05}, repeats=20)
    assert result["overall"]["paired_cells"] == 2 * (49 * 49 - 1)
    assert result["overall"]["deterministic"]["M4"]["heavy"]["CSI"] == 1.0
    assert result["overall"]["deterministic"]["M2"]["heavy"]["CSI"] == 0.0
    assert result["probability"]["eligible_case_count"] == 1
    assert result["probability"]["withheld_incoherent_case_count"] == 1
    assert result["paired_date_bootstrap"]["M4_minus_M2_heavy_CSI"]["point"] == 1.0
    assert result["regime_promotion_eligible"] is False  # only two event-bearing dates


def test_scoring_rejects_duplicate_or_changed_order_metadata() -> None:
    case = _case("20260610")
    with pytest.raises(ValueError, match="duplicate"):
        score_cases([case, case], climatology={"heavy": 0.01, "very_heavy": 0.001},
                    probability_cutoffs={"heavy": 0.1, "very_heavy": 0.05}, repeats=10)
    case["nested_probability_violating_cells"] = 1
    with pytest.raises(ValueError, match="order count differs"):
        validate_case(case)


def test_one_open_imd_reader_preserves_missing_cells(tmp_path) -> None:
    path = tmp_path / "imd.nc"
    with netcdf_file(path, "w") as dataset:
        dataset.createDimension("TIME", 1)
        dataset.createDimension("LATITUDE", 49)
        dataset.createDimension("LONGITUDE", 49)
        time = dataset.createVariable("TIME", "f8", ("TIME",))
        time.units = b"days since 2026-06-01 00:00:00"
        time[:] = [0]
        lat = dataset.createVariable("LATITUDE", "f8", ("LATITUDE",))
        lat[:] = np.linspace(10, 22, 49)
        lon = dataset.createVariable("LONGITUDE", "f8", ("LONGITUDE",))
        lon[:] = np.linspace(68, 80, 49)
        rain = dataset.createVariable("RAINFALL", "f4", ("TIME", "LATITUDE", "LONGITUDE"))
        rain._FillValue = -999.0
        rain.missing_value = -999.0
        values = np.full((1, 49, 49), 2.0, dtype=np.float32)
        values[0, 0, 0] = -999.0
        rain[:] = values
    with ImdYear(path) as reader:
        field, mask = reader.day(date(2026, 6, 1))
        assert field.shape == (49, 49) and mask.sum() == 2400
        assert field[1, 1] == 2.0
        with pytest.raises(ValueError, match="date missing"):
            reader.day(date(2026, 6, 2))


def test_score_refuses_before_opening_observation_when_gates_missing(monkeypatch) -> None:
    monkeypatch.setattr(runner, "preflight", lambda: {"status": "BLOCKED_BEFORE_OBSERVATION_READ", "reasons": ["IMD_REFERENCE_MISSING"]})

    class ForbiddenReader:
        def __init__(self, *_args, **_kwargs):
            raise AssertionError("observation was opened before preflight cleared")

    monkeypatch.setattr(runner, "ImdYear", ForbiddenReader)
    with pytest.raises(RuntimeError, match="IMD_REFERENCE_MISSING"):
        runner.score_once()
