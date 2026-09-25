"""Phase 4B predeclaration, source parsing, and protected frozen contract checks."""

from __future__ import annotations

import ast
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pytest

from backend.app.data.accumulation import GriddedAccumulationMessage, reconstruct_minimal_accumulation_window
from backend.app.ml.phase2b import FEATURE_NAMES, sha256_file
from backend.app.ml.phase2b import xgb_predict
from experiments.recent_historical.phase4b_20240718_20240724_v1 import run


def test_predeclared_window_and_hash() -> None:
    protocol = run.read_json(run.HERE / "protocol.json")
    assert sha256_file(run.HERE / "protocol.json") == (run.HERE / "protocol.sha256").read_text().strip()
    assert len(run.DATES) == 7
    assert protocol["initialization_dates_utc"] == [date(int(d[:4]), int(d[4:6]), int(d[6:])).isoformat() for d in run.DATES]
    assert [date(int(d[:4]), int(d[4:6]), int(d[6:])) + timedelta(days=1) for d in run.DATES] == [date(2024, 7, day) for day in range(19, 26)]
    assert protocol["forecast_window_hours"] == [3, 27]
    assert tuple(protocol["rainfall_members"]) == run.MEMBERS


def test_no_fitting_or_observation_in_inference_stage() -> None:
    tree = ast.parse((run.HERE / "run.py").read_text(encoding="utf-8"))
    inference = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "infer_one")
    calls = [node for node in ast.walk(inference) if isinstance(node, ast.Call)]
    names = {node.func.attr for node in calls if isinstance(node.func, ast.Attribute)}
    assert not {"fit", "fit_transform", "load_imd_day", "recalibrate"} & names
    assert "load_imd_day" not in ast.get_source_segment((run.HERE / "run.py").read_text(encoding="utf-8"), inference)


def test_index_range_parsing_and_ambiguity() -> None:
    rows = run.index_rows(b"1:0:d=2024071800:APCP:surface:0-3 hour acc fcst:\n2:100:d=2024071800:TMP:surface:3 hour fcst:\n")
    assert rows[0]["start"] == 0 and rows[0]["end"] == 99
    with pytest.raises(ValueError):
        run.index_rows(b"malformed\n")


def test_unchanged_canonical_packing_rejection() -> None:
    values = np.ones((2, 2))
    messages = [
        GriddedAccumulationMessage(0, 3, values, "f003", 0.01),
        GriddedAccumulationMessage(0, 6, values - 0.1, "f006", 0.01),
        GriddedAccumulationMessage(6, 12, values, "f012", 0.01),
        GriddedAccumulationMessage(12, 18, values, "f018", 0.01),
        GriddedAccumulationMessage(18, 24, values, "f024", 0.01),
        GriddedAccumulationMessage(24, 27, values, "f027", 0.01),
    ]
    with pytest.raises(ValueError, match="packing|negative"):
        reconstruct_minimal_accumulation_window(messages, window_start_hour=3, window_end_hour=27)


def test_frozen_feature_contract_and_model_hash_loading() -> None:
    selection, pfreeze, _, ridge, models = run.frozen_models()
    assert selection["feature_names"] == list(FEATURE_NAMES)
    assert len(pfreeze["probability_feature_names"]) == 26
    assert ridge["feature_names"] == list(FEATURE_NAMES)
    assert len(models) == 4
    assert pfreeze["targets"]["heavy"]["threshold_mm_24h"] == 64.5
    assert pfreeze["targets"]["very_heavy"]["threshold_mm_24h"] == 115.6


def test_seven_day_ledger_retains_rejections_and_common_masks() -> None:
    ledger = run.read_json(run.HERE / "seven_day_ledger.json")
    assert ledger["protocol_sha256"] == sha256_file(run.HERE / "protocol.json")
    assert [row["initialization"][:10].replace("-", "") for row in ledger["rows"]] == list(run.DATES)
    assert {row["status"] for row in ledger["rows"]} == {"ADMITTED", "RAINFALL_QC_FAILED"}
    assert sum(row["status"] == "ADMITTED" for row in ledger["rows"]) == 4
    for row in ledger["rows"]:
        if row["status"] == "ADMITTED":
            assert row["paired_valid_cells"] == 1301
            assert row["deterministic_eligible"] and row["probability_eligible"]
        else:
            assert row["paired_valid_cells"] == 0 and row["reason"]
        assert not row["ensemble_baseline_eligible"]


def test_actual_source_diagnostics_and_pooled_metrics() -> None:
    audit = run.read_json(run.HERE / "source_audit.json")
    summary = run.read_json(run.HERE / "aggregate_summary.json")
    assert audit["index_receipt_count"] == 224
    assert len(audit["rainfall_member_diagnostics"]) == 35
    rejected = [d for d in audit["rainfall_member_diagnostics"] if d["status"] == "rejected"]
    assert len(rejected) == 14
    assert all(d["packing_bound_violations"] > 0 for d in rejected)
    assert all(d["final_negative_cells"] is None for d in rejected)
    assert summary["admitted_dates"] == 4 and summary["paired_cells"] == 4 * 1301
    assert summary["models"]["M0"]["continuous"]["sample_count"] == summary["models"]["M2"]["continuous"]["sample_count"]
    assert summary["dates_improved_m2_rmse"] + summary["dates_worsened_m2_rmse"] + summary["dates_tied_m2_rmse"] == 4
    for target in ("heavy", "very_heavy"):
        assert summary["probabilities"][target]["sample_count"] == summary["paired_cells"]
        for size in ("1", "3", "5", "9"):
            for model in ("M0", "M2"):
                result = summary["fss"][target][size][model]
                assert result["fss"] is None or 0 <= result["fss"] <= 1


def test_frozen_m2_reproducible_from_saved_forecast_features() -> None:
    selection, _, _, _, models = run.frozen_models()
    strategy = selection["selected_xgboost_target_strategy_by_2018_rmse"]
    ledger = run.read_json(run.HERE / "seven_day_ledger.json")
    for row in ledger["rows"]:
        if row["status"] != "ADMITTED":
            continue
        day = row["initialization"][:10].replace("-", "")
        case_dir = run.HERE / "cases" / day
        inference = run.read_json(case_dir / "inference.json")
        features = np.load(case_dir / "features.npy", allow_pickle=False)
        original = np.load(case_dir / "prediction_M2.npy", allow_pickle=False)
        repeated = xgb_predict(models["global_xgboost.json"], features, strategy).reshape(49, 49).astype(np.float32)
        assert np.array_equal(repeated, original)
        assert sha256_file(case_dir / "prediction_M2.npy") == inference["prediction_hashes"]["M2"]
