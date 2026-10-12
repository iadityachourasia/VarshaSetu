import numpy as np
import pytest

from backend.app.ml.extreme_ordinal_probability import fit_ordinal, predict_ordinal
from scripts import experiment_extreme_ordinal_fit as fit
from scripts.experiment_extreme_ordinal_score import date_bootstrap, score_target


def test_ordinal_fit_is_coherent_and_deterministic():
    heavy = np.tile(np.array([0.005, 0.03, 0.15, 0.5]), 60)
    very_heavy = np.tile(np.array([0.001, 0.01, 0.08, 0.3]), 60)
    yh = np.tile(np.array([0, 0, 1, 1]), 60)
    yv = np.tile(np.array([0, 0, 0, 1]), 60)
    model = fit_ordinal(heavy, very_heavy, yh, yv)
    ph, pv = predict_ordinal(heavy, very_heavy, model)
    assert model == fit_ordinal(heavy, very_heavy, yh, yv)
    assert np.all((0 <= pv) & (pv <= ph) & (ph <= 1))
    assert ph[0] < ph[3] and pv[0] < pv[3]
    assert model["heavy"]["fit_rows"] == 240
    assert model["very_heavy_given_heavy"]["fit_rows"] == 120


def test_ordinal_rejects_bad_inputs_and_labels():
    base = np.array([0.1, 0.2, 0.7, 0.9])
    with pytest.raises(ValueError, match="nested"):
        fit_ordinal(base, base, [0, 0, 1, 1], [1, 0, 0, 1])
    with pytest.raises(ValueError, match="matching"):
        fit_ordinal(base, [0.1, np.nan, 0.7, 0.9], [0, 0, 1, 1], [0, 0, 0, 1])
    with pytest.raises(ValueError, match="both logistic"):
        fit_ordinal(base, base, [0, 0, 1, 1], [0, 0, 0, 0])


def test_protocol_sidecar_and_event_metrics():
    rule, digest = fit.checked(fit.PROTOCOL)
    assert len(digest) == 64
    assert rule["excluded_years"] == [2025, 2026]
    assert rule["fixed_warning_cutoffs"] == {"heavy": 0.1, "very_heavy": 0.05}
    result = score_target(np.array([0, 0, 1, 1], dtype=np.uint8),
                          np.array([0.01, 0.2, 0.1, 0.9]), 0.05, 0.2)
    assert result["observed_event_cells"] == 2
    assert result["forecast_warning_cells"] == 3
    assert result["warning_frequency_ratio"] == 1.5


def test_date_bootstrap_keeps_case_rows_together():
    cases = [
        {"row_start": 0, "initialization_utc": "2024-08-01T00:00:00Z"},
        {"row_start": 1301, "initialization_utc": "2024-08-02T00:00:00Z"},
    ]
    mask = np.ones(2602, dtype=bool)
    labels = {"heavy": np.zeros(2602, dtype=np.uint8),
              "very_heavy": np.zeros(2602, dtype=np.uint8)}
    labels["heavy"][[0, 1301]] = 1
    labels["very_heavy"][[0, 1301]] = 1
    arrays = {f"{arm}_{target}": np.full(2602, 0.01)
              for arm in ("frozen", "global", "ordinal")
              for target in ("heavy", "very_heavy")}
    result = date_bootstrap(mask, cases, labels, arrays, repeats=10)
    assert result["dates"] == 2
    assert result["zero_event_replicates"] == 0
    assert result["brier_difference_intervals"]["ordinal_minus_frozen"]["joint_brier_95pct"] == [0.0, 0.0]
