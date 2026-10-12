"""Write-once nonlinear national probability development study.

2023 alone fits the two XGBoost heads, nested date-block Platt calibration,
and persisted-precision warning cutoffs. The 2024 predictions are sealed
before the separate consumed-development score opens its IMD reference.
2025/2026 are excluded. Commands: prepare, fit, score, check.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.app.ml.nationwide_probability_v2 import case_indices  # noqa: E402
from backend.app.ml.nationwide_probability_v3 import (  # noqa: E402
    apply_platt, fit_platt, frequency_cutoff_persisted, validate_nested_folds,
)
from backend.app.ml.nationwide_research import (  # noqa: E402
    coherent_probabilities, comparable_mask, date_block_folds,
)
from backend.app.ml.phase2b import event_metrics  # noqa: E402
from backend.app.ml.phase2c import probability_metrics  # noqa: E402
from scripts import nationwide_probability_v2 as v2  # noqa: E402
from scripts import nationwide_research as national  # noqa: E402

BASE = ROOT / "data/manifests/research_pilot"
OUT = ROOT / "data/processed/nationwide_probability_v3"
PROTOCOL = BASE / "nationwide_probability_protocol_v3.json"
SEAL = BASE / "nationwide_probability_fit_seal_v3.json"
SCORE = BASE / "nationwide_probability_score_v3.json"
HEADS = {"heavy": 64.5, "very_heavy": 115.6}
MODEL_SPEC = {
    "n_estimators": 80, "max_depth": 3, "learning_rate": 0.05,
    "subsample": 0.85, "colsample_bytree": 0.9, "min_child_weight": 20,
    "reg_lambda": 5.0, "max_bin": 128, "tree_method": "hist", "device": "cpu",
    "n_jobs": 4, "random_state": 26080, "objective": "binary:logistic",
    "eval_metric": "logloss",
}
COMMON_DISPLAY_CUTOFF = 0.05


def _protocol() -> dict:
    if national.receipt(PROTOCOL) != national.sha(PROTOCOL):
        raise ValueError("v3 protocol receipt mismatch")
    protocol = json.loads(PROTOCOL.read_text(encoding="utf-8"))
    expected = {
        "runner": national.sha(Path(__file__)),
        "calibration_contract": national.sha(ROOT / "backend/app/ml/nationwide_probability_v3.py"),
    }
    sources = {
        "feature_manifest_sha256": national.sha(national.FEATURES),
        "national_fit_seal_sha256": national.sha(national.SEAL),
        "national_score_sha256": national.sha(national.SCORE),
        "v2_protocol_sha256": national.sha(v2.PROTOCOL),
        "v2_fit_seal_sha256": national.sha(v2.SEAL),
        "v2_score_sha256": national.sha(v2.SCORE),
        "land_mask_sha256": national.sha(national.OUT / "research_land_mask.npy"),
    }
    if (protocol.get("status") != "FROZEN_BEFORE_V3_FIT_OR_2024_PAIRING"
            or protocol.get("code_sha256") != expected or protocol.get("sources") != sources
            or protocol.get("model_spec") != MODEL_SPEC
            or protocol.get("heads_mm_per_24h") != HEADS):
        raise ValueError("v3 frozen protocol/code/source mismatch")
    return protocol


def prepare() -> dict:
    """Pin recipe and source identities without opening any reference value."""
    if any(path.exists() for path in (PROTOCOL, SEAL, SCORE, OUT)):
        raise FileExistsError("v3 protocol or output already exists")
    _, features, mask = national._feature_manifest()
    v2.check()
    from importlib.metadata import version

    protocol = {
        "schema": "nationwide-probability-nonlinear-development-v3",
        "status": "FROZEN_BEFORE_V3_FIT_OR_2024_PAIRING",
        "freeze_date": "2026-10-09",
        "motivation": "The repaired v2 linear head underfit nonlinear forecast interactions and its lead-isotonic 2024 outputs all fell below the very-heavy warning cutoff; test one fixed nonlinear head with monotone Platt calibration, not a threshold retune.",
        "roles": {"2023": "fit_and_nested_date_block_calibration_threshold",
                  "2024": "already_consumed_development_same_case_score_only_after_prediction_seal",
                  "2025": "consumed_test_excluded", "2026": "sealed_test_excluded"},
        "inputs": "Exactly the 22 sealed national forecast-time features; no fitted M2, observation-derived or valid-time reanalysis feature",
        "heads_mm_per_24h": HEADS,
        "model_spec": MODEL_SPEC,
        "nested_validation": {"outer_folds": 3, "inner_folds_per_outer": 2,
                              "final_calibration_inner_folds": 3,
                              "embargo_days": 3, "unit": "initialization date",
                              "outer_held_never_in_its_head_or_calibrator_fit": True},
        "calibration": "Per-lead, natural-frequency, monotone logistic Platt map on clipped head logits; C=1.0, no class weights; at least 30 events and nonevents per lead; nonpositive slope fails closed",
        "coherence": "P(very heavy)=min(calibrated very-heavy, calibrated heavy)",
        "cutoff": "Choose one per head on nested outer OOF coherent probabilities after float32 persistence; 0.01 to 0.50 in 0.01 steps, nearest forecast/observed event frequency, lower tie break. Also report a common fixed 0.05 cutoff for all arms. No 2024 threshold tuning.",
        "comparison": "same 2024 cases and paired cells as v1 and v2; primary very-heavy Brier against both, heavy guardrail, BSS, ten-bin reliability, CSI/POD/FAR/ETS and event frequencies by lead; date-block paired uncertainty",
        "diagnostic_gate": "v3 very-heavy Brier must beat both v1 and v2 with each 95% paired date-bootstrap interval below zero, v3 very-heavy BSS positive, v3 heavy Brier <= min(v1,v2)+0.0001, and very-heavy nested-cutoff forecast/observed frequency between 0.5 and 2.0; even a pass is development only",
        "uncertainty": {"bootstrap_unit": "initialization date", "repeats": 1000,
                        "seed": 26080, "caveat": "date resampling does not remove spatial or serial dependence"},
        "sources": {"feature_manifest_sha256": national.receipt(national.FEATURES),
                    "national_fit_seal_sha256": national.receipt(national.SEAL),
                    "national_score_sha256": national.receipt(national.SCORE),
                    "v2_protocol_sha256": national.receipt(v2.PROTOCOL),
                    "v2_fit_seal_sha256": national.receipt(v2.SEAL),
                    "v2_score_sha256": national.receipt(v2.SCORE),
                    "land_mask_sha256": national.sha(national.OUT / "research_land_mask.npy")},
        "code_sha256": {"runner": national.sha(Path(__file__)),
                        "calibration_contract": national.sha(ROOT / "backend/app/ml/nationwide_probability_v3.py")},
        "libraries": {name: version(name) for name in ("numpy", "scikit-learn", "xgboost")},
        "2023_cases": sum(row["year"] == 2023 for row in features["cases"]),
        "2024_cases": sum(row["year"] == 2024 for row in features["cases"]),
        "land_cells": int(mask.sum()),
        "observation_values_read_before_freeze": False,
        "product_default": "regional_M2_unchanged",
        "release": "research-only regardless of consumed-2024 score; no API/live/public warning promotion",
    }
    digest = national.write_json(PROTOCOL, protocol)
    return {"status": protocol["status"], "protocol_sha256": digest}


def _train(x: np.ndarray, target: np.ndarray):
    from xgboost import XGBClassifier

    if len(x) != len(target) or len(np.unique(target)) != 2:
        raise ValueError("nonlinear head fit needs both classes")
    return XGBClassifier(**MODEL_SPEC).fit(x, target)


def _head_probability(model, x: np.ndarray) -> np.ndarray:
    values = np.asarray(model.predict_proba(x)[:, 1], dtype=np.float64)
    if not np.isfinite(values).all() or np.any((values < 0) | (values > 1)):
        raise ValueError("invalid nonlinear head probability")
    return values


def _oof_head(x: np.ndarray, target: np.ndarray, slices: dict[str, slice], folds: list[dict]) -> np.ndarray:
    result = np.full(len(target), np.nan, dtype=np.float64)
    covered = np.concatenate([case_indices(slices, fold["held"]) for fold in folds])
    if len(covered) != len(np.unique(covered)):
        raise ValueError("head OOF held rows overlap")
    for fold in folds:
        tr = case_indices(slices, fold["train"])
        held = case_indices(slices, fold["held"])
        if np.intersect1d(tr, held).size or np.isfinite(result[held]).any():
            raise ValueError("head OOF fold leakage or overlap")
        result[held] = _head_probability(_train(x[tr], target[tr]), x[held])
    if not np.isfinite(result[covered]).all():
        raise ValueError("head OOF population incomplete")
    return result


def _fit_nested(x: np.ndarray, target: np.ndarray, leads: np.ndarray,
                slices: dict[str, slice], outer: list[dict], inner: dict[str, list[dict]]):
    outer_calibrated = np.full(len(target), np.nan, dtype=np.float64)
    for fold in outer:
        outer_train = case_indices(slices, fold["train"])
        outer_held = case_indices(slices, fold["held"])
        inner_oof = _oof_head(x, target, slices, inner[str(fold["fold"])])
        if not np.isfinite(inner_oof[outer_train]).all():
            raise ValueError("inner OOF missing outer-training rows")
        calibration = fit_platt(inner_oof[outer_train], target[outer_train], leads[outer_train])
        outer_raw = _head_probability(_train(x[outer_train], target[outer_train]), x[outer_held])
        outer_calibrated[outer_held] = apply_platt(outer_raw, leads[outer_held], calibration)
    if not np.isfinite(outer_calibrated).all():
        raise ValueError("nested outer population incomplete")
    return outer_calibrated


def fit() -> dict:
    """The only bounded CPU-intensive job; 2024 truth is unopened."""
    protocol = _protocol()
    if SEAL.exists() or OUT.exists():
        raise FileExistsError("v3 fit is write-once")
    if national.sha(national.IMD / "RF25_ind2023_rfp25.nc") != national.IMD_SHA["2023"]:
        raise ValueError("2023 fit reference changed")
    _, features, mask = national._feature_manifest()
    training = [row for row in features["cases"] if row["year"] == 2023]
    future = [row for row in features["cases"] if row["year"] == 2024]
    case_ids = [row["case_id"] for row in training]
    outer = date_block_folds(case_ids, folds=3, embargo_days=3)
    inner = {str(fold["fold"]): date_block_folds(fold["train"], folds=2, embargo_days=3)
             for fold in outer}
    validate_nested_folds(case_ids, outer, inner, embargo_days=3)
    final_inner = date_block_folds(case_ids, folds=3, embargo_days=3)
    x_parts, y_parts, slices = [], [], {}
    position = 0
    for row in training:
        x, _ = national._load_x(row)
        truth = national._reference(2023, row["case_id"], row["hour"])
        raw = np.full(national.GRID_SHAPE, np.nan, dtype=np.float32)
        raw[mask] = x[:, 0]
        valid = comparable_mask(mask, raw, truth.rainfall_mm, truth.valid_mask)
        selected = valid[mask]
        if not np.array_equal(selected, truth.valid_mask[mask]):
            raise ValueError(f"2023 fit eligibility changed: {row['case_id']}")
        x_parts.append(x[selected].astype(np.float32, copy=False))
        y_parts.append(truth.rainfall_mm[valid].astype(np.float32))
        slices[row["case_id"]] = slice(position, position + int(selected.sum()))
        position += int(selected.sum())
    x, rainfall = np.concatenate(x_parts), np.concatenate(y_parts)
    if len(x) != len(rainfall) or len(x) != json.loads(national.SEAL.read_text(encoding="utf-8"))["fit_cells"]:
        raise ValueError("v3 fit cells differ from sealed nationwide fit")
    leads = x[:, -1]
    temporary = OUT.with_name(OUT.name + ".partial")
    if temporary.exists():
        raise FileExistsError("partial v3 output requires inspection")
    temporary.mkdir(parents=True)
    (temporary / "predictions").mkdir()
    models = {}
    nested = {}
    for name, threshold in HEADS.items():
        target = (rainfall >= threshold).astype(np.uint8)
        nested[name] = _fit_nested(x, target, leads, slices, outer, inner)
        final_oof = _oof_head(x, target, slices, final_inner)
        calibration = fit_platt(final_oof, target, leads)
        model = _train(x, target)
        path = temporary / f"{name}_head.json"
        model.save_model(path)
        models[name] = {"calibration": calibration, "model_file": f"{name}_head.json",
                        "model_sha256": national.sha(path),
                        "fit_events": int(target.sum()), "fit_cells": len(target),
                        "training_climatology": float(target.mean())}
    nested_heavy, nested_very_heavy = coherent_probabilities(nested["heavy"], nested["very_heavy"])
    for name, values in (("heavy", nested_heavy), ("very_heavy", nested_very_heavy)):
        models[name]["warning_cutoff_nested_oof_persisted"] = frequency_cutoff_persisted(
            values, (rainfall >= HEADS[name]).astype(np.uint8))
    np.savez(temporary / "nested_oof_float32.npz", heavy_p=nested_heavy.astype(np.float32),
             very_heavy_p=nested_very_heavy.astype(np.float32))
    (temporary / "models.json").write_text(json.dumps(models, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
    loaded = {name: _load_head(temporary / models[name]["model_file"]) for name in HEADS}
    predictions = []
    for row in future:
        features_x, _ = national._load_x(row)
        heavy, very_heavy = _predict(loaded, models, features_x)
        path = temporary / "predictions" / f"{row['case_id']}.npz"
        np.savez(path, heavy_p=heavy.astype(np.float32), very_heavy_p=very_heavy.astype(np.float32))
        predictions.append({"case_id": row["case_id"], "hour": row["hour"],
                            "file": (OUT / "predictions" / path.name).relative_to(ROOT).as_posix(),
                            "sha256": national.sha(path), "cells": len(features_x),
                            "feature_sha256": row["feature_sha256"]})
    os.replace(temporary, OUT)
    seal = {
        "schema": "nationwide-probability-fit-seal-v3",
        "status": "2024_V3_PREDICTIONS_SEALED_BEFORE_2024_REFERENCE_READ",
        "protocol_sha256": national.sha(PROTOCOL),
        "feature_manifest_sha256": national.sha(national.FEATURES),
        "fit_year": 2023, "fit_cases": len(training), "fit_cells": len(rainfall),
        "nested_outer_folds": outer, "nested_inner_folds": inner,
        "final_calibration_inner_folds": final_inner,
        "models_sha256": national.sha(OUT / "models.json"),
        "oof_sha256": national.sha(OUT / "nested_oof_float32.npz"),
        "model_files_sha256": {name: info["model_sha256"] for name, info in models.items()},
        "predictions": predictions,
        "2024_reference_values_read": False, "2025_2026_values_read": False,
        "product_default_unchanged": "regional_M2", "public_warning_allowed": False,
    }
    digest = national.write_json(SEAL, seal)
    return {"status": seal["status"], "fit_cells": len(rainfall),
            "2024_predictions": len(predictions), "seal_sha256": digest}


def _load_head(path: Path):
    from xgboost import XGBClassifier

    model = XGBClassifier()
    model.load_model(path)
    return model


def _predict(loaded: dict, models: dict, x: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    lead = x[:, -1]
    calibrated = {name: apply_platt(_head_probability(loaded[name], x), lead, models[name]["calibration"])
                  for name in HEADS}
    return coherent_probabilities(calibrated["heavy"], calibrated["very_heavy"])


def _sealed() -> tuple[dict, dict, dict]:
    protocol = _protocol()
    seal = json.loads(SEAL.read_text(encoding="utf-8"))
    if (national.receipt(SEAL) != national.sha(SEAL)
            or seal.get("protocol_sha256") != national.sha(PROTOCOL)
            or seal.get("feature_manifest_sha256") != national.sha(national.FEATURES)
            or seal.get("2024_reference_values_read") is not False
            or seal.get("2025_2026_values_read") is not False
            or seal.get("fit_cases") != protocol["2023_cases"]
            or len(seal.get("predictions", [])) != protocol["2024_cases"]):
        raise ValueError("v3 fit seal or case population changed")
    models_path = OUT / "models.json"
    if (national.sha(models_path) != seal["models_sha256"]
            or national.sha(OUT / "nested_oof_float32.npz") != seal["oof_sha256"]):
        raise ValueError("v3 model or nested OOF hash changed")
    models = json.loads(models_path.read_text(encoding="utf-8"))
    for name in HEADS:
        if (national.sha(OUT / models[name]["model_file"]) != models[name]["model_sha256"]
                or models[name]["model_sha256"] != seal["model_files_sha256"][name]):
            raise ValueError("v3 nonlinear head hash changed")
    for row in seal["predictions"]:
        if national.sha(ROOT / row["file"]) != row["sha256"]:
            raise ValueError(f"v3 prediction hash changed: {row['case_id']}")
    return protocol, seal, models


def score() -> dict:
    """Consumed-2024 same-cell diagnostic, never an independent validation."""
    protocol, seal, models = _sealed()
    if SCORE.exists() or SCORE.with_suffix(".sha256").exists():
        raise FileExistsError("v3 development score is write-once")
    if national.sha(national.IMD / "RF25_ind2024_rfp25.nc") != national.IMD_SHA["2024"]:
        raise ValueError("2024 development reference changed")
    _, features, mask = national._feature_manifest()
    by_case = {row["case_id"]: row for row in features["cases"] if row["year"] == 2024}
    _, v2_seal = v2._sealed()
    v2_rows = {row["case_id"]: row for row in v2_seal["predictions"]}
    v1_seal = json.loads(national.SEAL.read_text(encoding="utf-8"))
    if national.receipt(national.SEAL) != national.sha(national.SEAL):
        raise ValueError("national v1 fit seal changed")
    v1_rows = {row["case_id"]: row for row in v1_seal["predictions"]}
    population = {row["case_id"] for row in seal["predictions"]}
    if len(population) != len(seal["predictions"]) or population != set(by_case) or population != set(v1_rows) or population != set(v2_rows):
        raise ValueError("v1/v2/v3 2024 case population differs")
    values = {name: {"target": [], "v1": [], "v2": [], "v3": [], "lead": []} for name in HEADS}
    date_sse = {name: defaultdict(lambda: np.zeros(4, dtype=np.float64)) for name in HEADS}
    for row in seal["predictions"]:
        case_id = row["case_id"]
        x, _ = national._load_x(by_case[case_id])
        truth = national._reference(2024, case_id, row["hour"])
        raw = np.full(national.GRID_SHAPE, np.nan, dtype=np.float32)
        raw[mask] = x[:, 0]
        valid = comparable_mask(mask, raw, truth.rainfall_mm, truth.valid_mask)
        selected = valid[mask]
        if not np.array_equal(selected, truth.valid_mask[mask]):
            raise ValueError(f"2024 paired eligibility changed: {case_id}")
        for source_row in (v1_rows[case_id], v2_rows[case_id]):
            if national.sha(ROOT / source_row["file"]) != source_row["sha256"]:
                raise ValueError(f"comparison prediction changed: {case_id}")
        with (np.load(ROOT / row["file"], allow_pickle=False) as a3,
              np.load(ROOT / v1_rows[case_id]["file"], allow_pickle=False) as a1,
              np.load(ROOT / v2_rows[case_id]["file"], allow_pickle=False) as a2):
            for name, threshold in HEADS.items():
                target = (truth.rainfall_mm[valid] >= threshold).astype(np.uint8)
                field = values[name]
                field["target"].append(target)
                field["lead"].append(np.full(len(target), row["hour"], dtype=np.int16))
                arrays = {"v1": a1, "v2": a2, "v3": a3}
                probabilities = {}
                for arm, archive in arrays.items():
                    p = archive[name + "_p"][selected].astype(np.float64)
                    if (len(p) != len(target) or not np.isfinite(p).all()
                            or np.any((p < 0) | (p > 1))):
                        raise ValueError(f"invalid same-cell {arm} probability: {case_id}/{name}")
                    field[arm].append(p)
                    probabilities[arm] = p
                day = date_sse[name][case_id[:8]]
                day += [*(float(np.square(probabilities[arm] - target).sum())
                          for arm in ("v1", "v2", "v3")), len(target)]
    report_heads = {}
    rng = np.random.default_rng(protocol["uncertainty"]["seed"])
    original = json.loads(national.SCORE.read_text(encoding="utf-8"))["probability"]
    repaired = json.loads(v2.SCORE.read_text(encoding="utf-8"))["heads"]
    for name in HEADS:
        field = {key: np.concatenate(parts) for key, parts in values[name].items()}
        y, p3 = field["target"], field["v3"]
        cutoff = models[name]["warning_cutoff_nested_oof_persisted"]
        metrics = probability_metrics(y, p3, cutoff, models[name]["training_climatology"])
        if (metrics["sample_count"] != original[name]["sample_count"]
                or metrics["observed_event_count"] != original[name]["observed_event_count"]
                or metrics["sample_count"] != repaired[name]["metrics"]["sample_count"]):
            raise ValueError(f"v3/v1/v2 same-cell score population differs: {name}")
        brier = {arm: float(np.mean(np.square(field[arm] - y))) for arm in ("v1", "v2", "v3")}
        if (not np.isclose(brier["v1"], original[name]["brier"], atol=1e-12)
                or not np.isclose(brier["v2"], repaired[name]["metrics"]["brier"], atol=1e-12)):
            raise ValueError(f"v1/v2 frozen Brier did not reproduce: {name}")
        days = np.stack(list(date_sse[name].values()))
        draws = rng.integers(0, len(days), size=(protocol["uncertainty"]["repeats"], len(days)))
        sampled = days[draws].sum(axis=1)
        deltas = {}
        for arm, column in (("v1", 0), ("v2", 1)):
            distribution = (sampled[:, 2] - sampled[:, column]) / sampled[:, 3]
            deltas["v3_minus_" + arm] = {
                "estimate": brier["v3"] - brier[arm],
                "date_bootstrap_ci95": np.quantile(distribution, (0.025, 0.975)).tolist(),
            }
        lead_metrics = {}
        for lead in (24, 48, 72):
            selected = field["lead"] == lead
            lead_metrics[str(lead)] = {
                "cases": sum(row["hour"] == lead for row in seal["predictions"]),
                "observed_events": int(y[selected].sum()),
                "sample_count": int(selected.sum()),
                "brier": {arm: float(np.mean(np.square(field[arm][selected] - y[selected])))
                          for arm in ("v1", "v2", "v3")},
                "v3_nested_cutoff_categorical": event_metrics(y[selected], p3[selected], cutoff),
            }
        report_heads[name] = {
            "v3_metrics": metrics, "same_cell_brier": brier,
            "paired_deltas": deltas, "lead": lead_metrics,
            "common_0p05_categorical": {arm: event_metrics(y, field[arm], COMMON_DISPLAY_CUTOFF)
                                        for arm in ("v1", "v2", "v3")},
            "nested_cutoff_warning_frequency_ratio":
                metrics["categorical"]["forecast_event_count"] / metrics["observed_event_count"],
        }
    vh = report_heads["very_heavy"]
    heavy = report_heads["heavy"]
    gate = {
        "very_heavy_vs_v1_interval_below_zero": vh["paired_deltas"]["v3_minus_v1"]["date_bootstrap_ci95"][1] < 0,
        "very_heavy_vs_v2_interval_below_zero": vh["paired_deltas"]["v3_minus_v2"]["date_bootstrap_ci95"][1] < 0,
        "very_heavy_bss_positive": vh["v3_metrics"]["bss"] > 0,
        "heavy_brier_guardrail": heavy["same_cell_brier"]["v3"] <= min(heavy["same_cell_brier"]["v1"], heavy["same_cell_brier"]["v2"]) + 0.0001,
        "very_heavy_warning_frequency_supported": 0.5 <= vh["nested_cutoff_warning_frequency_ratio"] <= 2.0,
    }
    report = {
        "schema": "nationwide-probability-development-score-v3",
        "status": "CONSUMED_2024_DEVELOPMENT_DIAGNOSTIC_ONLY",
        "protocol_sha256": national.sha(PROTOCOL), "fit_seal_sha256": national.sha(SEAL),
        "same_case_as_v1_v2": True, "heads": report_heads,
        "prespecified_diagnostic_gate": gate, "diagnostic_gate_pass": all(gate.values()),
        "2025_2026_values_read": False, "independent_skill_claim": False,
        "product_default_unchanged": "regional_M2", "public_warning_allowed": False,
    }
    digest = national.write_json(SCORE, report)
    return {"status": report["status"], "score_sha256": digest,
            "diagnostic_gate_pass": report["diagnostic_gate_pass"],
            "heads": {name: {"brier": block["same_cell_brier"],
                             "bss": block["v3_metrics"]["bss"],
                             "warning_frequency_ratio": block["nested_cutoff_warning_frequency_ratio"]}
                      for name, block in report_heads.items()}}


def check() -> dict:
    _protocol()
    result = {"status": "V3_PROBABILITY_PROTOCOL_VERIFIED", "protocol_sha256": national.sha(PROTOCOL)}
    if SEAL.exists():
        _, seal, _ = _sealed()
        result["sealed_2024_predictions"] = len(seal["predictions"])
    if SCORE.exists():
        report = json.loads(SCORE.read_text(encoding="utf-8"))
        if (national.receipt(SCORE) != national.sha(SCORE)
                or report["protocol_sha256"] != national.sha(PROTOCOL)
                or report["fit_seal_sha256"] != national.sha(SEAL)):
            raise ValueError("v3 score hash or lineage changed")
        result["score_sha256"] = national.sha(SCORE)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("prepare", "fit", "score", "check"))
    args = parser.parse_args()
    print(json.dumps({"prepare": prepare, "fit": fit, "score": score, "check": check}[args.command](),
                     sort_keys=True, allow_nan=False))


if __name__ == "__main__":
    main()
