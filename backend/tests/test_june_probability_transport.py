"""No-refit June transport retains the frozen case and observation boundary."""

from types import SimpleNamespace

import numpy as np
import pytest

from scripts import run_june_probability_transport as forecast
from scripts import score_june_probability_transport as score


def test_transport_protocol_and_forecast_seal_are_observation_free():
    context = forecast.inputs()
    year, _ = forecast.checked(forecast.OUT)
    assert context["rule"]["excluded_years"] == [2025, 2026]
    assert year["observation_read"] is False
    assert year["lead_count"] == 90
    assert year["prior_ready_leads"] == 55
    assert year["newly_ready_leads"] == 35
    assert year["lead_aware_fit_seal_sha256"] == context["fit_seal_sha256"]


def test_transport_refuses_mask_drift_before_model_inference():
    masked = SimpleNamespace(valid_mask=np.ones((49, 49), dtype=bool),
                             rainfall_mm=np.ones((49, 49), dtype=float))
    prior_archive = {"valid_day1_24h": np.zeros((49, 49), dtype=np.uint8)}
    with pytest.raises(ValueError, match="mask differs"):
        forecast.candidate_fields(masked, {}, "day1_24h", None, {}, prior_archive)


def test_transport_score_reproduces_sealed_same_cell_result():
    saved, _ = forecast.checked(score.OUT)
    rebuilt = score.score()
    assert rebuilt == saved
    assert rebuilt["summary"]["all_ready"]["paired_cells"] == 116823
    assert rebuilt["role"] == "consumed_2024_no_refit_transport_diagnostic_not_independent_reliability"
