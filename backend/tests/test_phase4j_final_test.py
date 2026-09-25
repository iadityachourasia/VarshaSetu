"""Read-only audit of the consumed one-time Phase 4J holdout."""

from __future__ import annotations

import numpy as np
import pytest

from backend.app.ml.phase2b import continuous_metrics, event_metrics
from backend.app.ml.phase2c import fss
from experiments.recent_historical.phase4i_operational_model_development_v1.freeze import verify_ready
from experiments.recent_historical.phase4j_operational_final_test_v1.governance import (
    AUTH, DATA, HERE, IMD, IMD_SHA, I, READY_SHA, read, require_unsealed, sha,
)
from experiments.recent_historical.phase4j_operational_final_test_v1.evaluate import _verified, evaluate_once
from experiments.recent_historical.phase4j_operational_final_test_v1.pairing import pair_and_freeze
from experiments.recent_historical.phase4j_operational_final_test_v1.audit import verify_inventory
import experiments.recent_historical.phase4j_operational_final_test_v1.governance as governance


def test_readiness_and_source_hashes_unchanged():
    ready = verify_ready()
    assert sha(I / "final_freeze/FINAL_TEST_READY.json") == READY_SHA
    assert ready["2025_outcome_status"] == "SEALED"  # historical Phase 4I record
    assert sha(IMD) == IMD_SHA


def test_unseal_transition_and_authorization():
    auth = read(AUTH)
    assert auth["test_status_before_authorization"] == "SEALED"
    assert auth["FINAL_TEST_READY_sha256"] == READY_SHA
    assert auth["IMD_2025_source_sha256"] == IMD_SHA
    assert read(HERE / "holdout_state_01_authorized.json")["authorization_sha256"] == sha(AUTH)
    assert read(HERE / "holdout_state_02_unsealed.json")["authorization_sha256"] == sha(AUTH)
    assert read(HERE / "holdout_state_03_completed.json")["FINAL_TEST_RESULT_sha256"] == sha(HERE / "FINAL_TEST_RESULT.json")
    require_unsealed()
    assert (HERE / "UNSEAL_AUTHORIZATION.sha256").read_text().strip() == sha(AUTH)


def test_observation_gate_rejects_missing_authorization(monkeypatch, tmp_path):
    monkeypatch.setattr(governance, "HERE", tmp_path)
    with pytest.raises(PermissionError, match="remain sealed"):
        governance.require_unsealed()


def test_frozen_population_precedes_scoring_and_masks_align():
    pop = read(HERE / "population/2025_population_manifest.json")
    result = read(HERE / "FINAL_TEST_RESULT.json")
    source = np.load(HERE / "pairing/source_row_index.npy", allow_pickle=False)
    pixels = np.load(HERE / "pairing/pixel_index.npy", allow_pickle=False)
    y = np.load(HERE / "pairing/observation_mm.npy", allow_pickle=False)
    assert pop["status"] == "FROZEN_BEFORE_SCORING"
    assert sha(HERE / "population/2025_population_manifest.json") == result["population_manifest_sha256"]
    assert (pop["deterministic_cases"], pop["deterministic_cells"], pop["full_ensemble_paired_cases"]) == (232, 301832, 75)
    assert len(source) == len(pixels) == len(y) == 301832
    assert np.all((pixels >= 0) & (pixels < 2401))
    assert np.all(np.diff(source) > 0)
    assert pop["rejected_cases"] == []
    for c in pop["paired_cases"]:
        sl = slice(c["row_start"], c["row_start"] + c["row_count"])
        assert c["row_count"] == 1301
        assert len(np.unique(pixels[sl])) == c["row_count"]


def test_frozen_models_calibrators_thresholds_and_lineage():
    ready = read(I / "final_freeze/FINAL_TEST_READY.json")
    result = read(HERE / "FINAL_TEST_RESULT.json")
    lineage = read(HERE / "predictions/lineage.json")
    selection = read(I / "final_freeze/model_selection_freeze.json")
    assert selection["selected_deterministic_model"] == "M1"
    assert result["model_sha256"] == ready["final_deterministic_models"]
    assert result["probability_model_sha256"] == ready["probability_model_artifact_sha256"]
    assert result["calibrator_sha256"] == ready["calibrator_artifact_sha256"]
    assert result["thresholds"] == {"heavy": 0.1, "very_heavy": 0.05}
    assert lineage["no_2025_observation_predictor"] is True
    assert lineage["population_sha256"] == result["population_manifest_sha256"]
    for name, digest in result["prediction_sha256"].items():
        assert sha(HERE / "predictions" / name) == digest
    for name, digest in result["metric_result_sha256"].items():
        assert sha(HERE / "metrics" / name) == digest


def test_common_m0_m4_population_and_exact_metrics():
    y = np.load(HERE / "pairing/observation_mm.npy", allow_pickle=False)
    result = read(HERE / "FINAL_TEST_RESULT.json")
    for m in ("M0", "M1", "M2", "M3", "M4"):
        pred = np.load(HERE / "predictions" / f"{m}.npy", allow_pickle=False)
        assert pred.shape == y.shape
        assert np.isfinite(pred).all() and np.all(pred >= 0)
        assert continuous_metrics(y, pred) == result["deterministic"][m]["continuous"]
        assert event_metrics(y, pred, 64.5) == result["deterministic"][m]["heavy"]
        assert event_metrics(y, pred, 115.6) == result["deterministic"][m]["very_heavy"]


def test_ensemble_common_population_and_probability_bounds():
    result = read(HERE / "FINAL_TEST_RESULT.json")
    pop = read(HERE / "population/2025_population_manifest.json")
    assert set(result["ensemble"]["case_ids"]) == set(pop["full_ensemble_paired_case_ids"])
    assert result["ensemble"]["cell_count"] == 75 * 1301
    for name in ("heavy", "very_heavy"):
        ml = np.load(HERE / "predictions" / f"{name}_probability.npy", allow_pickle=False)
        ens = np.load(HERE / "predictions" / f"{name}_ensemble_probability.npy", allow_pickle=False)
        assert ml.shape == (301832,) and ens.shape == (75 * 1301,)
        assert np.all((ml >= 0) & (ml <= 1)) and np.all((ens >= 0) & (ens <= 1))
        assert np.allclose(ens * 5, np.rint(ens * 5), atol=1e-6)


def test_fss_alignment_and_bounds():
    result = read(HERE / "FINAL_TEST_RESULT.json")
    for threshold in ("heavy", "very_heavy"):
        for size in ("1", "3", "5", "9"):
            row = result["fss"][threshold][size]
            assert 0 <= row["matched_case_count"] <= 232
            for key in ("raw", "selected", "matched_raw", "matched_selected"):
                value = row[key]["fss"]
                assert value is None or 0 <= value <= 1
    grid = np.zeros((49, 49), dtype=float)
    grid[10, 10] = 100
    assert fss(grid, grid, np.ones_like(grid, dtype=bool), 64.5, 3)["fss"] == 1


def test_result_complete_and_no_second_test():
    result = read(HERE / "FINAL_TEST_RESULT.json")
    assert result["status"] == "FINAL_TEST_COMPLETED"
    assert (HERE / "FINAL_TEST_RESULT.sha256").read_text().strip() == sha(HERE / "FINAL_TEST_RESULT.json")
    assert result["UNSEAL_AUTHORIZATION_sha256"] == sha(AUTH)
    assert result["2025_IMD_source_sha256"] == IMD_SHA
    assert result["primary"]["classification"] in {
        "SELECTED_MODEL_IMPROVED_RMSE", "SELECTED_MODEL_NEUTRAL_WITHIN_EXACT_EQUALITY",
        "SELECTED_MODEL_WORSENED_RMSE"}
    with pytest.raises(RuntimeError, match="FINAL_TEST_ALREADY_CONSUMED"):
        evaluate_once()
    with pytest.raises(RuntimeError, match="FINAL_TEST_ALREADY_CONSUMED"):
        pair_and_freeze(read(I / "final_freeze/FINAL_TEST_READY.json"))


def test_phase4j_artifact_inventory():
    assert verify_inventory() == 37


def test_tampered_model_hash_rejected(tmp_path):
    artifact = tmp_path / "artifact.json"
    artifact.write_text("{}", encoding="utf-8")
    with pytest.raises(RuntimeError, match="frozen model hash mismatch"):
        _verified(artifact, "0" * 64)
