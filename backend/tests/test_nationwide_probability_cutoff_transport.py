"""Reproduce the forecast-only diagnosis of the failed v2 warning policy."""

from __future__ import annotations

import json

import numpy as np
import pytest

from scripts import diagnose_nationwide_probability_cutoff_transport as diagnostic
from scripts import nationwide_research as national


def test_stage_count_uses_inclusive_cutoff_and_rejects_invalid_values() -> None:
    found = diagnostic.stage_counts(np.array([0.0, 0.03, 0.1]), 0.03)
    assert found == {"cells": 3, "maximum": 0.1, "mean": pytest.approx(0.13 / 3), "warnings": 2}
    with pytest.raises(ValueError, match="invalid probability"):
        diagnostic.stage_counts(np.array([0.1, np.nan]), 0.03)


def test_sealed_diagnostic_reproduces_without_reference_loader(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(national, "_reference", lambda *_args, **_kwargs: pytest.fail("IMD value read"))
    assert diagnostic.check()["status"] == "CUTOFF_DIAGNOSTIC_REPRODUCED"


def test_result_locates_zero_very_heavy_warnings_after_calibration() -> None:
    report = json.loads(diagnostic.RESULT.read_text(encoding="utf-8"))
    assert report["reference_values_read_by_diagnostic"] is False
    assert report["model_refitted"] is False
    assert report["warning_threshold_changed"] is False
    cutoff = report["cutoffs"]["very_heavy"]
    assert cutoff == 0.03
    for lead in (24, 48, 72):
        stages = report["counts_by_head_lead_and_stage"]["very_heavy"][str(lead)]
        assert stages["raw_head"]["warnings"] > 0
        assert stages["lead_calibrated"]["maximum"] < cutoff
        assert stages["lead_calibrated"]["warnings"] == 0
        assert stages["coherent_saved"]["warnings"] == 0
