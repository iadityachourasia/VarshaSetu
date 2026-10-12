"""Separate write-once nationwide probability repair study (2023 fit, consumed 2024 development).

Commands: prepare, fit, score, check. The 2024 predictions are sealed before
score can open the 2024 IMD reference. No 2025/2026 observation is accessed.
This does not replace the frozen national M0-M4 ladder or the product default.
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

from backend.app.ml.nationwide_probability_v2 import (  # noqa: E402
    apply_lead_calibration, case_indices, frequency_cutoff, validate_head_folds,
)
from backend.app.ml.nationwide_research import coherent_probabilities, comparable_mask, date_block_folds  # noqa: E402
from backend.app.ml.phase2c import probability_metrics  # noqa: E402
from scripts import nationwide_research as national  # noqa: E402

BASE = ROOT / "data/manifests/research_pilot"
OUT = ROOT / "data/processed/nationwide_probability_v2"
PROTOCOL = BASE / "nationwide_probability_protocol_v2.json"
SEAL = BASE / "nationwide_probability_fit_seal_v2.json"
SCORE = BASE / "nationwide_probability_score_v2.json"
HEADS = {"heavy": 64.5, "very_heavy": 115.6}


def _protocol() -> dict:
    protocol = json.loads(PROTOCOL.read_text(encoding="utf-8"))
    if (national.receipt(PROTOCOL) != national.sha(PROTOCOL)
            or protocol["code_sha256"] != {"runner": national.sha(Path(__file__)),
                                            "head_contract": national.sha(ROOT / "backend/app/ml/nationwide_probability_v2.py")}
            or protocol["sources"] != {"feature_manifest_sha256": national.receipt(national.FEATURES),
                                        "national_fit_seal_sha256": national.receipt(national.SEAL),
                                        "national_score_sha256": national.receipt(national.SCORE),
                                        "land_mask_sha256": national.sha(national.OUT / "research_land_mask.npy")}):
        raise ValueError("v2 frozen protocol/code/source mismatch")
    return protocol


def prepare() -> dict:
    """Freeze the new method and source identities without opening rainfall values."""
    if any(path.exists() for path in (PROTOCOL, SEAL, SCORE, OUT)):
        raise FileExistsError("probability v2 protocol/output is write-once")
    _, features, mask = national._feature_manifest()
    seal = json.loads(national.SEAL.read_text(encoding="utf-8"))
    if seal["fit_year"] != 2023 or len(seal["predictions"]) != sum(row["year"] == 2024 for row in features["cases"]):
        raise ValueError("national experiment population mismatch")
    protocol = {
        "schema": "nationwide-probability-repair-v2", "status": "FROZEN_BEFORE_V2_FIT_OR_2024_PAIRING",
        "purpose": "repair probability head fold dependence and warning cutoff scale in a distinct research-only candidate",
        "roles": {"2023": "fit_and_embargoed_date_block_oof_calibration_threshold",
                  "2024": "already_consumed_development_same_case_diagnostic_after_v2_prediction_seal",
                  "2025": "consumed_test_excluded", "2026": "sealed_test_excluded"},
        "inputs": "all 22 forecast-only national features, including Raw GEFS; no M2 prediction or observation-derived feature",
        "heads_mm_per_24h": HEADS, "model": "unweighted standardized LogisticRegression C=0.1 max_iter=1000",
        "folds": {"count": 3, "embargo_days": 3, "unit": "initialization date", "base_model_input": False},
        "calibration": "per-lead isotonic on 2023 out-of-fold head scores; identity only with fewer than 30 events or 30 nonevents",
        "coherence": "very-heavy probability clipped to heavy probability after calibration",
        "warning_cutoff": "smallest 0.01..0.50 by 0.01 giving 2023 calibrated/coherent OOF forecast/observed frequency nearest one",
        "score": "same 2024 cases/cells as v1; Brier, Brier skill, reliability, event frequency, CSI/POD/FAR/ETS; 1000 initialization-date bootstrap draws for paired v2-minus-v1 Brier",
        "uncertainty": {"bootstrap_seed": 26080, "repeats": 1000, "caveat": "date resampling retains spatial and serial dependence"},
        "decision": "no promotion or public warning regardless of consumed-2024 result; current regional M2 remains product default",
        "sources": {"feature_manifest_sha256": national.receipt(national.FEATURES),
                    "national_fit_seal_sha256": national.receipt(national.SEAL),
                    "national_score_sha256": national.receipt(national.SCORE),
                    "land_mask_sha256": national.sha(national.OUT / "research_land_mask.npy")},
        "code_sha256": {"runner": national.sha(Path(__file__)),
                        "head_contract": national.sha(ROOT / "backend/app/ml/nationwide_probability_v2.py")},
        "land_cells": int(mask.sum()), "2023_cases": sum(row["year"] == 2023 for row in features["cases"]),
        "2024_cases": sum(row["year"] == 2024 for row in features["cases"]),
        "observation_values_read": False,
    }
    digest = national.write_json(PROTOCOL, protocol)
    return {"status": protocol["status"], "protocol_sha256": digest}


def _calibrators(raw: np.ndarray, target: np.ndarray, leads: np.ndarray) -> dict:
    result = {}
    for lead in (24, 48, 72):
        selected = leads == lead
        events = int(target[selected].sum())
        nonevents = int(selected.sum()) - events
        if events >= 30 and nonevents >= 30:
            from sklearn.isotonic import IsotonicRegression
            fitted = IsotonicRegression(y_min=0, y_max=1, out_of_bounds="clip").fit(raw[selected], target[selected])
            result[str(lead)] = {"method": "isotonic", "x": fitted.X_thresholds_.tolist(),
                                 "y": fitted.y_thresholds_.tolist(), "events": events}
        else:
            result[str(lead)] = {"method": "identity_insufficient_events", "events": events}
    return result


def _predict(models: dict, x: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    leads = x[:, -1]
    values = {name: apply_lead_calibration(national._scale_predict(models[name]["head"], x), leads,
                                           models[name]["calibrators"]) for name in HEADS}
    return coherent_probabilities(values["heavy"], values["very_heavy"])


def fit() -> dict:
    protocol = _protocol()
    if SEAL.exists() or OUT.exists():
        raise FileExistsError("probability v2 fit is write-once")
    _, features, mask = national._feature_manifest()
    training = [row for row in features["cases"] if row["year"] == 2023]
    future = [row for row in features["cases"] if row["year"] == 2024]
    folds = date_block_folds([row["case_id"] for row in training], folds=3, embargo_days=3)
    validate_head_folds(folds, [row["case_id"] for row in training])
    xs, ys, case_slices = [], [], {}
    position = 0
    for row in training:
        x, _ = national._load_x(row)
        truth = national._reference(2023, row["case_id"], row["hour"])
        raw = np.full(national.GRID_SHAPE, np.nan)
        raw[mask] = x[:, 0]
        valid = comparable_mask(mask, raw, truth.rainfall_mm, truth.valid_mask)
        selected = valid[mask]
        if not np.array_equal(selected, truth.valid_mask[mask]):
            raise ValueError(f"unexpected non-reference fit exclusion: {row['case_id']}")
        xs.append(x[selected]); ys.append(truth.rainfall_mm[valid].astype(np.float32))
        case_slices[row["case_id"]] = slice(position, position + int(selected.sum()))
        position += int(selected.sum())
    X, y = np.concatenate(xs), np.concatenate(ys)
    if len(X) != len(y) or len(X) != json.loads(national.SEAL.read_text(encoding="utf-8"))["fit_cells"]:
        raise ValueError("v2 fit population differs from sealed national fit")
    leads = X[:, -1]
    raw_oof = {}
    for name, threshold in HEADS.items():
        target = (y >= threshold).astype(int)
        oof = np.full(len(y), np.nan)
        for fold in folds:
            tr, held = case_indices(case_slices, fold["train"]), case_indices(case_slices, fold["held"])
            if np.intersect1d(tr, held).size or len(np.unique(target[tr])) != 2:
                raise ValueError(f"invalid head fold: {name}, {fold['fold']}")
            oof[held] = national._scale_predict(national._scale_fit(X[tr], target[tr]), X[held])
        if not np.isfinite(oof).all():
            raise ValueError(f"incomplete head OOF: {name}")
        raw_oof[name] = oof
    models = {}
    calibrated = {}
    for name, threshold in HEADS.items():
        target = (y >= threshold).astype(int)
        cal = _calibrators(raw_oof[name], target, leads)
        calibrated[name] = apply_lead_calibration(raw_oof[name], leads, cal)
        models[name] = {"head": national._scale_fit(X, target), "calibrators": cal,
                        "training_climatology": float(target.mean()), "fit_event_count": int(target.sum())}
    coherent = coherent_probabilities(calibrated["heavy"], calibrated["very_heavy"])
    for name, values in zip(HEADS, coherent):
        models[name]["warning_cutoff_calibrated_coherent_2023_oof"] = frequency_cutoff(values, (y >= HEADS[name]).astype(int))
    temporary = OUT.with_name(OUT.name + ".partial")
    if temporary.exists():
        raise FileExistsError("incomplete v2 temporary output requires inspection")
    temporary.mkdir(parents=True)
    (temporary / "predictions").mkdir()
    model_path = temporary / "models.json"
    model_path.write_text(json.dumps(models, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
    prediction_rows = []
    for row in future:
        x, _ = national._load_x(row)
        heavy, very_heavy = _predict(models, x)
        file_name = row["case_id"] + ".npz"
        path = temporary / "predictions" / file_name
        np.savez(path, heavy_p=heavy.astype(np.float32), very_heavy_p=very_heavy.astype(np.float32))
        prediction_rows.append({"case_id": row["case_id"], "hour": row["hour"],
                                "file": (OUT / "predictions" / file_name).relative_to(ROOT).as_posix(),
                                "sha256": national.sha(path), "cells": len(x), "feature_sha256": row["feature_sha256"]})
    os.replace(temporary, OUT)
    seal = {"schema": "nationwide-probability-fit-seal-v2", "status": "2024_V2_PREDICTIONS_SEALED_BEFORE_2024_REFERENCE_READ",
            "protocol_sha256": national.sha(PROTOCOL), "feature_manifest_sha256": national.sha(national.FEATURES),
            "fit_year": 2023, "fit_cases": len(training), "fit_cells": len(y), "folds": folds,
            "model_file_sha256": national.sha(OUT / "models.json"), "predictions": prediction_rows,
            "2024_reference_values_read": False, "2025_2026_values_read": False,
            "product_default_unchanged": "regional_M2", "public_warning_allowed": False}
    digest = national.write_json(SEAL, seal)
    return {"status": seal["status"], "fit_cells": len(y), "2024_predictions": len(prediction_rows),
            "seal_sha256": digest}


def _sealed() -> tuple[dict, dict]:
    protocol = _protocol()
    seal = json.loads(SEAL.read_text(encoding="utf-8"))
    if (national.receipt(SEAL) != national.sha(SEAL) or seal["protocol_sha256"] != national.sha(PROTOCOL)
            or seal["feature_manifest_sha256"] != national.sha(national.FEATURES)
            or national.sha(OUT / "models.json") != seal["model_file_sha256"]
            or seal["2024_reference_values_read"] or seal["2025_2026_values_read"]):
        raise ValueError("v2 fit seal mismatch")
    for row in seal["predictions"]:
        if national.sha(ROOT / row["file"]) != row["sha256"]:
            raise ValueError(f"v2 prediction hash mismatch: {row['case_id']}")
    return protocol, seal


def score() -> dict:
    protocol, seal = _sealed()
    if SCORE.exists():
        raise FileExistsError("v2 2024 score is write-once")
    if national.sha(national.IMD / "RF25_ind2024_rfp25.nc") != national.IMD_SHA["2024"]:
        raise ValueError("2024 reference hash mismatch")
    _, features, mask = national._feature_manifest()
    by_case = {row["case_id"]: row for row in features["cases"] if row["year"] == 2024}
    if set(by_case) != {row["case_id"] for row in seal["predictions"]}:
        raise ValueError("v2 2024 case population mismatch")
    truth_store, pred_store = defaultdict(list), defaultdict(list)
    by_day = {name: defaultdict(lambda: np.zeros(3, dtype=np.float64)) for name in HEADS}
    for row in seal["predictions"]:
        case_id = row["case_id"]
        x, _ = national._load_x(by_case[case_id])
        truth = national._reference(2024, case_id, row["hour"])
        raw = np.full(national.GRID_SHAPE, np.nan); raw[mask] = x[:, 0]
        valid = comparable_mask(mask, raw, truth.rainfall_mm, truth.valid_mask)
        selected = valid[mask]
        if not np.array_equal(selected, truth.valid_mask[mask]):
            raise ValueError(f"unexpected non-reference score exclusion: {case_id}")
        old_row = next(item for item in json.loads(national.SEAL.read_text(encoding="utf-8"))["predictions"] if item["case_id"] == case_id)
        if national.sha(ROOT / old_row["file"]) != old_row["sha256"]:
            raise ValueError(f"v1 comparison array changed: {case_id}")
        with np.load(ROOT / row["file"], allow_pickle=False) as new, np.load(ROOT / old_row["file"], allow_pickle=False) as old:
            for name, threshold in HEADS.items():
                key = name + "_p"
                y = (truth.rainfall_mm[valid] >= threshold).astype(np.uint8)
                p, p_old = new[key][selected], old[key][selected]
                if not np.isfinite(p).all() or np.any((p < 0) | (p > 1)) or len(p) != len(y):
                    raise ValueError(f"v2 score population/probability invalid: {case_id}, {name}")
                truth_store[name].append(y); pred_store[name].append(p)
                day = by_day[name][case_id[:8]]
                day += [float(np.square(p - y).sum()), float(np.square(p_old - y).sum()), len(y)]
    models = json.loads((OUT / "models.json").read_text(encoding="utf-8"))
    baseline = json.loads(national.SCORE.read_text(encoding="utf-8"))["probability"]
    result = {}
    rng = np.random.default_rng(protocol["uncertainty"]["bootstrap_seed"])
    for name in HEADS:
        y, p = np.concatenate(truth_store[name]), np.concatenate(pred_store[name])
        metrics = probability_metrics(y, p, models[name]["warning_cutoff_calibrated_coherent_2023_oof"],
                                      models[name]["training_climatology"])
        if metrics["sample_count"] != baseline[name]["sample_count"] or metrics["observed_event_count"] != baseline[name]["observed_event_count"]:
            raise ValueError(f"v2/v1 score population differs: {name}")
        dates = np.stack(list(by_day[name].values()))
        draws = rng.integers(0, len(dates), size=(protocol["uncertainty"]["repeats"], len(dates)))
        sums = dates[draws].sum(axis=1)
        delta = (sums[:, 0] - sums[:, 1]) / sums[:, 2]
        paired_delta = float((dates[:, 0].sum() - dates[:, 1].sum()) / dates[:, 2].sum())
        result[name] = {"metrics": metrics, "v1_consumed_2024_brier": baseline[name]["brier"],
                        "paired_v2_minus_v1_brier": paired_delta,
                        "paired_delta_date_bootstrap_ci95": np.quantile(delta, [0.025, 0.975]).tolist(),
                        "warning_frequency_ratio": metrics["categorical"]["forecast_event_count"] / metrics["observed_event_count"]}
    report = {"schema": "nationwide-probability-development-score-v2",
              "status": "CONSUMED_2024_DEVELOPMENT_DIAGNOSTIC_ONLY", "protocol_sha256": national.sha(PROTOCOL),
              "fit_seal_sha256": national.sha(SEAL), "same_case_as_v1": True, "heads": result,
              "2025_2026_values_read": False, "independent_skill_claim": False,
              "product_default_unchanged": "regional_M2", "public_warning_allowed": False}
    digest = national.write_json(SCORE, report)
    return {"status": report["status"], "score_sha256": digest,
            "heads": {name: {"bss": block["metrics"]["bss"], "warning_frequency_ratio": block["warning_frequency_ratio"],
                             "paired_v2_minus_v1_brier": block["paired_v2_minus_v1_brier"]} for name, block in result.items()}}


def check() -> dict:
    _protocol()
    result = {"status": "V2_PROBABILITY_PROTOCOL_VERIFIED", "protocol_sha256": national.sha(PROTOCOL)}
    if SEAL.exists():
        _, seal = _sealed()
        result["sealed_2024_predictions"] = len(seal["predictions"])
    if SCORE.exists():
        report = json.loads(SCORE.read_text(encoding="utf-8"))
        if national.receipt(SCORE) != national.sha(SCORE) or report["fit_seal_sha256"] != national.sha(SEAL):
            raise ValueError("v2 score hash/lineage mismatch")
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
