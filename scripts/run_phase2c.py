"""Phase 2C: fit/freeze on 2017-18, then one-time 2019 evaluation.

Usage: python scripts/run_phase2c.py fit | evaluate | verify
"""

from __future__ import annotations

import json
import os
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import psutil
import zarr
from xgboost import XGBClassifier, XGBRegressor

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from backend.app.ml.phase2b import FEATURE_NAMES, load_cache, sha256_file, write_json, xgb_predict
from backend.app.ml.phase2c import (REGIMES, SCALES, THRESHOLDS, aggregate_districts,
    apply_calibration, district_weights, event_target, fit_calibration, fss, fss_many,
    probability_features, probability_metrics, safe_logistic_fit, safe_logistic_predict)

P2B = ROOT / "data/manifests/phase2b"
OUT = ROOT / "data/manifests/phase2c"
CASE_DIR = OUT / "cases"
GEOMETRY = ROOT / "data/static/phase2c/geoBoundaries-IND-ADM2_simplified.geojson"
EXPECTED_GEO_SHA = "d68db39cd3e2d0892af268e2b0454166368ce3b5b8a78fcda63069ec92a641db"
START = time.perf_counter()


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def source_guard() -> dict:
    manifest = read_json(P2B / "artifact_manifest.json")
    expected = manifest["freeze_manifest_sha256"]
    if sha256_file(P2B / "model_selection_freeze.json") != expected:
        raise ValueError("Phase 2B selection freeze hash mismatch")
    model = P2B / "models/global_xgboost.json"
    if sha256_file(model) != manifest["model_artifact_sha256"][model.name]:
        raise ValueError("frozen deterministic model hash mismatch")
    if sha256_file(GEOMETRY) != EXPECTED_GEO_SHA:
        raise ValueError("district source geometry hash mismatch")
    return manifest


def cache_for(year: int, p2b: dict):
    path = ROOT / p2b["feature_cache_paths"][str(year)]
    if sha256_file(path / "manifest.json") != p2b["feature_cache_manifests"][str(year)]:
        raise ValueError(f"{year} Phase 2B cache manifest hash mismatch")
    return load_cache(path)


def corrected_model() -> XGBRegressor:
    model = XGBRegressor(device="cpu", n_jobs=12)
    model.load_model(P2B / "models/global_xgboost.json")
    return model


def phase_features(arrays: dict, model: XGBRegressor) -> tuple[np.ndarray, np.ndarray]:
    corrected = xgb_predict(model, arrays["X"], "tweedie").astype(np.float32)
    return probability_features(arrays["X"], corrected, arrays["regime_probability"]), corrected


def initial_split(cases: list[str]) -> tuple[np.ndarray, np.ndarray]:
    # Entire forecast initializations, including all leads, remain in one 2018 fold.
    inits = sorted({key.split("|")[0] for key in cases})
    boundary = inits[int(len(inits) * 0.6)]
    by_case = np.asarray([key.split("|")[0] < boundary for key in cases], dtype=bool)
    return by_case, ~by_case


def predict_candidate(kind: str, artifact: dict | Path, x: np.ndarray) -> np.ndarray:
    if kind == "logistic":
        return safe_logistic_predict(artifact, x)
    model = XGBClassifier(device="cpu", n_jobs=12)
    model.load_model(artifact)
    return model.predict_proba(x)[:, 1]


def choose_threshold(y: np.ndarray, p: np.ndarray) -> float:
    from backend.app.ml.phase2b import event_metrics
    candidates = np.linspace(.05, .95, 19)
    scored = [(event_metrics(y, p, float(t))["metrics"]["CSI"] or 0.0, float(t)) for t in candidates]
    return max(scored, key=lambda item: (item[0], -item[1]))[1]


def fit() -> dict:
    p2b = source_guard()
    freeze_path = OUT / "probability_selection_freeze.json"
    sidecar = OUT / "probability_selection_freeze.sha256"
    if freeze_path.exists() and sidecar.exists():
        expected = sidecar.read_text(encoding="ascii").strip()
        if sha256_file(freeze_path) != expected:
            raise ValueError("existing Phase 2C freeze hash mismatch")
        return read_json(freeze_path)
    if freeze_path.exists() or sidecar.exists():
        raise ValueError("incomplete existing Phase 2C freeze; inspect before rerun")
    train_meta, train = cache_for(2017, p2b)
    valid_meta, valid = cache_for(2018, p2b)
    deterministic = corrected_model()
    xtrain, _ = phase_features(train, deterministic)
    xvalid, _ = phase_features(valid, deterministic)
    fit_case, select_case = initial_split(valid_meta["case_keys"])
    cal = fit_case[valid["case_code"]]
    selection = select_case[valid["case_code"]]
    OUT.mkdir(parents=True, exist_ok=True)
    decisions = {}
    validation = {"role": "2018 calibration/selection", "calibration_initialization_count": int(fit_case.sum()),
                  "selection_initialization_count": int(select_case.sum()), "targets": {}}
    for name, threshold in THRESHOLDS.items():
        ytrain = event_target(train["y"], threshold)
        yvalid = event_target(valid["y"], threshold)
        positive = int(ytrain.sum())
        if not 0 < positive < len(ytrain):
            raise ValueError(f"2017 {name} has only one class")
        climatology = positive / len(ytrain)
        candidates: list[tuple[str, dict | Path, Path]] = []
        log_path = OUT / f"{name}_logistic.safe.json"
        log_artifact = safe_logistic_fit(xtrain, ytrain)
        write_json(log_path, log_artifact)
        candidates.append(("logistic", log_artifact, log_path))
        xgb_path = OUT / f"{name}_xgboost.json"
        xgb = XGBClassifier(n_estimators=180, max_depth=4, learning_rate=.06, subsample=.9,
                            colsample_bytree=.9, reg_lambda=3, min_child_weight=10,
                            objective="binary:logistic", eval_metric="logloss", tree_method="hist",
                            device="cpu", n_jobs=12, random_state=26080, verbosity=0,
                            scale_pos_weight=(len(ytrain)-positive)/positive, early_stopping_rounds=20)
        xgb.fit(xtrain, ytrain, eval_set=[(xvalid[cal], yvalid[cal])], verbose=False)
        xgb.save_model(xgb_path)
        candidates.append(("xgboost", xgb_path, xgb_path))
        scores = []
        for kind, artifact, path in candidates:
            raw_p = predict_candidate(kind, artifact, xvalid)
            for method in ("identity", "sigmoid", "isotonic"):
                if method == "isotonic" and int(yvalid[cal].sum()) < 100:
                    continue
                calibration = fit_calibration(raw_p[cal], yvalid[cal], method)
                p = apply_calibration(calibration, raw_p[selection])
                brier = float(np.mean((p-yvalid[selection])**2))
                scores.append((brier, kind, method, calibration, path))
        best = min(scores, key=lambda item: (item[0], item[1], item[2]))
        _, kind, method, calibration, model_path = best
        calibration_path = OUT / f"{name}_calibration.safe.json"
        write_json(calibration_path, calibration)
        selected_artifact = log_artifact if kind == "logistic" else xgb_path
        raw_p = predict_candidate(kind, selected_artifact, xvalid)
        selected_p = apply_calibration(calibration, raw_p[selection])
        decision_threshold = choose_threshold(yvalid[selection], selected_p)
        decisions[name] = {"threshold_mm_24h": threshold, "training_events": positive,
                           "training_cells": len(ytrain), "climatology_2017": climatology,
                           "calibration_events": int(yvalid[cal].sum()),
                           "selection_events": int(yvalid[selection].sum()),
                           "model_kind": kind, "model_file": model_path.name,
                           "model_sha256": sha256_file(model_path), "calibration_method": method,
                           "calibration_file": calibration_path.name,
                           "calibration_sha256": sha256_file(calibration_path),
                           "decision_threshold": decision_threshold}
        validation["targets"][name] = {"selection_fold": probability_metrics(yvalid[selection], selected_p, decision_threshold, climatology),
                                       "candidate_brier": [{"model": s[1], "calibration": s[2], "selection_brier": s[0]} for s in scores],
                                       "calibration_fit_events": int(yvalid[cal].sum()),
                                       "selection_events": int(yvalid[selection].sum())}
    validation_path = OUT / "2018_validation.json"
    write_json(validation_path, validation)
    freeze = {"schema": "phase2c-probability-selection-v1", "training_year": 2017,
              "calibration_selection_year": 2018, "test_year": 2019, "test_values_accessed": False,
              "phase2b_freeze_sha256": p2b["freeze_manifest_sha256"],
              "phase2b_global_model_sha256": p2b["model_artifact_sha256"]["global_xgboost.json"],
              "training_cache_manifest_sha256": p2b["feature_cache_manifests"]["2017"],
              "validation_cache_manifest_sha256": p2b["feature_cache_manifests"]["2018"],
              "probability_feature_names": [*FEATURE_NAMES, "frozen_m2_corrected_mm", "regime_p_active", "regime_p_break_weak", "regime_p_low_depression"],
              "validation_policy": "2018 initializations chronological 60 percent calibration-fit; remaining 40 percent independent selection",
              "selection_objective": "minimum 2018 selection-fold Brier among bounded P1/P2 and identity/sigmoid/isotonic candidates",
              "threshold_objective": "maximum selection-fold CSI on fixed 0.05..0.95 grid; smallest threshold on ties",
              "targets": decisions, "validation_sha256": sha256_file(validation_path),
              "geometry_source_sha256": EXPECTED_GEO_SHA, "hardware": {"xgboost_device": "cpu", "threads": 12,
              "reason": "Phase 2B CPU/CUDA comparison failed scientific equivalence; new binary models use deterministic CPU hist"}}
    write_json(freeze_path, freeze)
    sidecar.write_text(sha256_file(freeze_path) + "\n", encoding="ascii")
    return freeze


def verified_freeze() -> dict:
    source_guard()
    path = OUT / "probability_selection_freeze.json"
    expected = (OUT / "probability_selection_freeze.sha256").read_text(encoding="ascii").strip()
    if sha256_file(path) != expected:
        raise ValueError("Phase 2C probability freeze mismatch")
    freeze = read_json(path)
    if freeze["test_values_accessed"] is not False or freeze["test_year"] != 2019:
        raise ValueError("invalid Phase 2C holdout gate")
    for target in freeze["targets"].values():
        for artifact, digest in ((target["model_file"], target["model_sha256"]),
                                 (target["calibration_file"], target["calibration_sha256"])):
            if sha256_file(OUT / artifact) != digest:
                raise ValueError(f"Phase 2C artifact mismatch: {artifact}")
    if sha256_file(OUT / "2018_validation.json") != freeze["validation_sha256"]:
        raise ValueError("2018 validation artifact mismatch")
    return freeze


def case_id(case_key: str) -> str:
    init, product = case_key.split("|")
    return datetime.fromisoformat(init.replace("Z", "+00:00")).strftime("%Y%m%dT%H%M%SZ") + "_" + product


def grid(values: np.ndarray, rows: np.ndarray, columns: np.ndarray) -> np.ndarray:
    output = np.full((49, 49), np.nan, dtype=np.float32)
    output[rows, columns] = values
    return output


def evaluate() -> dict:
    freeze = verified_freeze()  # 2019 values cannot be opened before this statement.
    final_path = OUT / "2019_final_results.json"
    if final_path.exists():
        manifest = OUT / "artifact_manifest.json"
        if not manifest.exists():
            raise ValueError("partial 2019 result exists; inspect before rerun")
        verify()
        return read_json(final_path)
    p2b = source_guard()
    meta, arrays = cache_for(2019, p2b)
    deterministic = corrected_model()
    x, corrected = phase_features(arrays, deterministic)
    model_predictions = {}
    result = {"schema": "phase2c-2019-held-out-v1", "probability_freeze_sha256": sha256_file(OUT / "probability_selection_freeze.json"),
              "case_count": meta["common_case_count"], "cell_count": meta["cell_count"], "targets": {}, "fss": {}, "p0_ensemble": {}}
    for name, spec in freeze["targets"].items():
        model_file = OUT / spec["model_file"]
        artifact = read_json(model_file) if spec["model_kind"] == "logistic" else model_file
        base = predict_candidate(spec["model_kind"], artifact, x)
        model_predictions[name] = apply_calibration(read_json(OUT / spec["calibration_file"]), base).astype(np.float32)
        target = event_target(arrays["y"], spec["threshold_mm_24h"])
        result["targets"][name] = probability_metrics(target, model_predictions[name], spec["decision_threshold"], spec["climatology_2017"])
    # Use the authoritative full target axes: the common valid mask may omit entire rows/columns.
    season = ROOT / "data/processed/phase1f/2019-JJAS/varshasetu-gefs12r-imd025-2019-jjas-v2.zarr"
    group = zarr.open_group(str(season), mode="r")
    lat = np.asarray(group["target_latitude"][:], dtype=float)
    lon = np.asarray(group["target_longitude"][:], dtype=float)
    if len(lat) != 49 or len(lon) != 49:
        raise ValueError("unexpected target-grid dimensions")
    districts, weights = district_weights(GEOMETRY, lat, lon)
    CASE_DIR.mkdir(parents=True, exist_ok=True)
    geo = {"type": "FeatureCollection", "features": [{"type": "Feature", "properties": {k: d[k] for k in ("district_id", "district_name")}, "geometry": d["geometry"]} for d in districts]}
    geo_path = OUT / "districts.geojson"
    write_json(geo_path, geo)
    weight_path = OUT / "district_weights.npy"
    np.save(weight_path, weights, allow_pickle=False)
    init_lookup = {datetime.fromtimestamp(int(t), timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"): n for n, t in enumerate(group["init_time_unix_seconds"][:])}
    full_index = pd.read_csv(ROOT / "data/manifests/phase1f/2019-JJAS/full_ensemble_index.csv")
    full_keys = {datetime.fromisoformat(row.initialization).astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ") + "|" + row.product
                 for row in full_index.itertuples() if row.FULL_ENSEMBLE_ELIGIBLE}
    all_case_meta = []
    raw_cases = []
    corrected_cases = []
    ensemble_y = {name: [] for name in THRESHOLDS}
    ensemble_p0 = {name: [] for name in THRESHOLDS}
    ensemble_selected = {name: [] for name in THRESHOLDS}
    for code, key in enumerate(meta["case_keys"]):
        selected = arrays["case_code"] == code
        rows, cols = arrays["pixel_i"][selected], arrays["pixel_j"][selected]
        mask = np.zeros((49, 49), dtype=bool)
        mask[rows, cols] = True
        observed = grid(arrays["y"][selected], rows, cols)
        raw = grid(arrays["raw"][selected], rows, cols)
        fixed = grid(corrected[selected], rows, cols)
        hp = grid(model_predictions["heavy"][selected], rows, cols)
        vp = grid(model_predictions["very_heavy"][selected], rows, cols)
        init, product = key.split("|")
        init_index, product_index = init_lookup[init], ("day1_24h", "day2_24h", "day3_24h").index(product)
        start_hours = int(group["window_start_hours"][product_index])
        end_hours = int(group["window_end_hours"][product_index])
        initialized = datetime.fromisoformat(init.replace("Z", "+00:00"))
        probabilities = arrays["regime_probability"][selected][0].astype(float)
        district_table = aggregate_districts(districts, weights, raw, fixed, hp, vp, mask)
        for record in district_table:
            record["dominant_regime"] = REGIMES[int(np.argmax(probabilities))]
        case_fss = {name: {str(scale): {"raw": fss(raw, observed, mask, threshold, scale),
                                             "corrected": fss(fixed, observed, mask, threshold, scale)}
                            for scale in SCALES} for name, threshold in THRESHOLDS.items()}
        identifier = case_id(key)
        data_path = CASE_DIR / f"{identifier}.npz"
        np.savez_compressed(data_path, raw=raw, corrected=fixed, observed=observed,
                            heavy_probability=hp, very_heavy_probability=vp, mask=mask)
        from backend.app.ml.phase2b import continuous_metrics
        case_record = {"case_id": identifier, "case_key": key, "initialization_utc": init,
                       "valid_period_start_utc": (initialized+timedelta(hours=start_hours)).isoformat().replace("+00:00", "Z"),
                       "valid_period_end_utc": (initialized+timedelta(hours=end_hours)).isoformat().replace("+00:00", "Z"),
                       "product": product, "lead_hours": int(arrays["lead"][selected][0]),
                       "regime_probabilities": dict(zip(REGIMES, map(float, probabilities))),
                       "dominant_regime": REGIMES[int(np.argmax(probabilities))],
                       "raw_rmse_mm": continuous_metrics(arrays["y"][selected], arrays["raw"][selected])["rmse_mm"],
                       "corrected_rmse_mm": continuous_metrics(arrays["y"][selected], corrected[selected])["rmse_mm"],
                       "observed_heavy_cells": int(np.sum(arrays["y"][selected] >= 64.5)),
                       "observed_very_heavy_cells": int(np.sum(arrays["y"][selected] >= 115.6)),
                       "mean_heavy_probability": float(np.mean(hp[mask])),
                       "mean_very_heavy_probability": float(np.mean(vp[mask])),
                       "fss": case_fss, "districts": district_table,
                       "array_file": data_path.name, "array_sha256": sha256_file(data_path)}
        case_path = CASE_DIR / f"{identifier}.json"
        write_json(case_path, case_record)
        all_case_meta.append({k: v for k, v in case_record.items() if k != "districts" and k != "fss"})
        raw_cases.append({"forecast": raw, "observed": observed, "mask": mask})
        corrected_cases.append({"forecast": fixed, "observed": observed, "mask": mask})
        if key in full_keys:
            ensemble = np.asarray(group["forecast_rain"][init_index, product_index], dtype=float)
            members_valid = mask & np.isfinite(ensemble).all(axis=0) & (ensemble >= 0).all(axis=0)
            for name, threshold in THRESHOLDS.items():
                ensemble_y[name].append((observed[members_valid] >= threshold).astype(np.uint8))
                ensemble_p0[name].append(np.mean(ensemble[:, members_valid] >= threshold, axis=0))
                selected_grid = hp if name == "heavy" else vp
                ensemble_selected[name].append(selected_grid[members_valid])
    for name, threshold in THRESHOLDS.items():
        result["fss"][name] = {str(scale): {"raw": fss_many(raw_cases, threshold, scale),
                                           "corrected": fss_many(corrected_cases, threshold, scale)} for scale in SCALES}
        label = np.concatenate(ensemble_y[name]) if ensemble_y[name] else np.array([], dtype=np.uint8)
        p0 = np.concatenate(ensemble_p0[name]) if ensemble_p0[name] else np.array([], dtype=float)
        selected = np.concatenate(ensemble_selected[name]) if ensemble_selected[name] else np.array([], dtype=float)
        spec = freeze["targets"][name]
        result["p0_ensemble"][name] = {"full_ensemble_case_count": sum(key in full_keys for key in meta["case_keys"]),
                                      "p0": probability_metrics(label, p0, spec["decision_threshold"], spec["climatology_2017"]),
                                      "selected_model_same_cells": probability_metrics(label, selected, spec["decision_threshold"], spec["climatology_2017"])}
    result["district_count"] = len(districts)
    result["district_geometry_sha256"] = sha256_file(geo_path)
    result["district_weights_sha256"] = sha256_file(weight_path)
    result["case_metadata"] = all_case_meta
    result["runtime_seconds"] = time.perf_counter() - START
    result["peak_process_rss_bytes"] = psutil.Process().memory_info().rss
    write_json(final_path, result)
    catalogue = sorted(all_case_meta, key=lambda c: (-c["observed_heavy_cells"], c["case_id"]))[:3]
    for lead in (24, 48, 72):
        candidates = [c for c in all_case_meta if c["lead_hours"] == lead]
        if candidates:
            catalogue.append(candidates[len(candidates)//2])
    unique = list({c["case_id"]: c for c in catalogue}.values())
    write_json(OUT / "video_case_catalogue.json", {"selection": "three highest observed-heavy-area cases plus middle chronological case at each lead; descriptive only, not skill selection", "cases": unique})
    artifact_manifest = {"schema": "phase2c-artifact-manifest-v1", "phase2c_freeze_sha256": result["probability_freeze_sha256"],
                         "phase2b_freeze_sha256": freeze["phase2b_freeze_sha256"], "geometry_source_sha256": EXPECTED_GEO_SHA,
                         "files": {str(path.relative_to(OUT)).replace("\\", "/"): sha256_file(path)
                                   for path in OUT.rglob("*") if path.is_file() and path.name not in ("artifact_manifest.json", "artifact_manifest.sha256")},
                         "readiness_state": "prototype_scientific_ready", "operational_ready": False}
    write_json(OUT / "artifact_manifest.json", artifact_manifest)
    (OUT / "artifact_manifest.sha256").write_text(sha256_file(OUT / "artifact_manifest.json") + "\n", encoding="ascii")
    return result


def verify() -> dict:
    verified_freeze()
    manifest = OUT / "artifact_manifest.json"
    expected = (OUT / "artifact_manifest.sha256").read_text(encoding="ascii").strip()
    if sha256_file(manifest) != expected:
        raise ValueError("Phase 2C artifact manifest mismatch")
    value = read_json(manifest)
    for relative, digest in value["files"].items():
        path = OUT / relative
        if sha256_file(path) != digest:
            raise ValueError(f"Phase 2C artifact mismatch: {relative}")
    return {"files_verified": len(value["files"]), "manifest_sha256": expected}


def ensemble_validation() -> dict:
    """Append-only 2018 P0 comparison; does not alter the model-selection freeze."""
    freeze = verified_freeze()
    output = OUT / "2018_p0_ensemble.json"
    if output.exists():
        return read_json(output)
    p2b = source_guard()
    meta, arrays = cache_for(2018, p2b)
    x, _ = phase_features(arrays, corrected_model())
    season = ROOT / "data/processed/phase2a/2018-JJAS/varshasetu-gefs12r-imd025-2018-jjas-v2.zarr"
    group = zarr.open_group(str(season), mode="r")
    init_lookup = {datetime.fromtimestamp(int(t), timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"): n for n, t in enumerate(group["init_time_unix_seconds"][:])}
    index = pd.read_csv(ROOT / "data/manifests/phase2a/2018-JJAS/full_ensemble_index.csv")
    full = {datetime.fromisoformat(row.initialization).astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ") + "|" + row.product
            for row in index.itertuples() if row.FULL_ENSEMBLE_ELIGIBLE}
    result = {"role": "2018 validation descriptive ensemble baseline; not used for probability-model selection", "targets": {}}
    for name, spec in freeze["targets"].items():
        artifact = read_json(OUT / spec["model_file"]) if spec["model_kind"] == "logistic" else OUT / spec["model_file"]
        selected_p = apply_calibration(read_json(OUT / spec["calibration_file"]),
                                       predict_candidate(spec["model_kind"], artifact, x))
        observed_blocks, p0_blocks, selected_blocks = [], [], []
        common_cases = 0
        for code, key in enumerate(meta["case_keys"]):
            if key not in full:
                continue
            common_cases += 1
            selected = arrays["case_code"] == code
            rows, cols = arrays["pixel_i"][selected], arrays["pixel_j"][selected]
            init, product = key.split("|")
            members = np.asarray(group["forecast_rain"][init_lookup[init], ("day1_24h", "day2_24h", "day3_24h").index(product)], dtype=float)
            cells = members[:, rows, cols]
            good = np.isfinite(cells).all(axis=0) & (cells >= 0).all(axis=0)
            observed_blocks.append(event_target(arrays["y"][selected][good], spec["threshold_mm_24h"]))
            p0_blocks.append(np.mean(cells[:, good] >= spec["threshold_mm_24h"], axis=0))
            selected_blocks.append(selected_p[selected][good])
        y = np.concatenate(observed_blocks)
        result["targets"][name] = {"full_ensemble_common_case_count": common_cases,
                                   "p0": probability_metrics(y, np.concatenate(p0_blocks), spec["decision_threshold"], spec["climatology_2017"]),
                                   "selected_model_same_cells": probability_metrics(y, np.concatenate(selected_blocks), spec["decision_threshold"], spec["climatology_2017"])}
    write_json(output, result)
    manifest_path = OUT / "artifact_manifest.json"
    if manifest_path.exists():
        old = read_json(manifest_path)
        old["files"][output.name] = sha256_file(output)
        write_json(manifest_path, old)
        (OUT / "artifact_manifest.sha256").write_text(sha256_file(manifest_path) + "\n", encoding="ascii")
    return result


def finalize_reporting() -> dict:
    """Record append-only descriptive artifacts without changing either freeze or 2019 scores."""
    verified_freeze()
    original = OUT / "artifact_manifest.json"
    old = read_json(original)
    supersession = read_json(OUT / "metric_semantics_supersession.json")
    if sha256_file(OUT / "2018_validation.json") != supersession["original_2018_validation_sha256"]:
        raise ValueError("2018 source report changed")
    if sha256_file(OUT / "2019_final_results.json") != supersession["original_2019_final_results_sha256"]:
        raise ValueError("2019 source report changed")
    if not (OUT / "2018_p0_ensemble.json").exists():
        raise ValueError("2018 P0 report missing")
    for name in ("metric_semantics_supersession.json", "2018_p0_ensemble.json"):
        old["files"][name] = sha256_file(OUT / name)
    write_json(original, old)
    (OUT / "artifact_manifest.sha256").write_text(sha256_file(original) + "\n", encoding="ascii")
    return verify()


if __name__ == "__main__":
    if len(sys.argv) != 2 or sys.argv[1] not in ("fit", "evaluate", "verify", "ensemble-validation", "finalize-reporting"):
        raise SystemExit("usage: run_phase2c.py fit|evaluate|verify|ensemble-validation|finalize-reporting")
    action = sys.argv[1]
    result = {"fit": fit, "evaluate": evaluate, "verify": verify,
              "ensemble-validation": ensemble_validation, "finalize-reporting": finalize_reporting}[action]()
    print(json.dumps({"action": action, "result": {k: v for k, v in result.items() if k not in ("targets", "case_metadata", "fss")}}, indent=2))
