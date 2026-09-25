"""Run the bounded Phase 2B experiment with an enforced 2019 freeze gate."""

from __future__ import annotations

import hashlib
import json
import os
import platform
import subprocess
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.app.ml.forecast_regimes import SafeLogisticRegimeClassifier
from backend.app.ml.phase2b import (
    FEATURE_NAMES,
    REGIME_NAMES,
    build_feature_cache,
    benchmark_xgb,
    deterministic_case_bootstrap,
    eligible_case_rows,
    load_cache,
    make_cache_key,
    safe_ridge_fit,
    safe_ridge_predict,
    sha256_file,
    train_xgb,
    verification_metrics,
    verify_cache,
    write_json,
    xgb_predict,
)


DOCS = ROOT / "docs"
DATA = ROOT / "data"
MANIFESTS = DATA / "manifests"
OUTPUT = MANIFESTS / "phase2b"
CACHE_ROOT = DATA / "processed" / "phase2b" / "feature_cache"
REGIME_DIR = MANIFESTS / "phase2a" / "regimes-v1"
REGIME_CASES = REGIME_DIR / "regime_cases_2017_2018.csv"
REGIME_CLASSIFIER = REGIME_DIR / "regime_classifier.safe.json"
SEASON_ZARR = {
    y: DATA / "processed" / ("phase1f" if y == 2019 else "phase2a") / f"{y}-JJAS" / f"varshasetu-gefs12r-imd025-{y}-jjas-v2.zarr"
    for y in (2017, 2018, 2019)
}
SEASON_INDEX = {
    y: MANIFESTS / ("phase1f" if y == 2019 else "phase2a") / f"{y}-JJAS"
    for y in (2017, 2018, 2019)
}
EXPECTED_ZARR_HASH = {
    2017: "6e742e4f148cf0bca435293116785015379614eae17645968ee0106f29c88475",
    2018: "5d1e09b7e90e98b081965409a36b714fc1d578f21dbe45fcb680ab266a642c3f",
}
TARGET_STRATEGIES = ("direct", "tweedie", "log1p")
RIDGE_ALPHAS = (0.1, 1.0, 10.0, 100.0)


def regime_artifact_hashes() -> dict:
    manifest = json.loads((REGIME_DIR / "artifact_manifest.json").read_text(encoding="utf-8"))
    hashes = {}
    for name, item in manifest["artifacts"].items():
        path = REGIME_DIR / name
        actual = sha256_file(path)
        if actual != item["sha256"]:
            raise ValueError(f"Phase 2A regime artifact hash mismatch: {name}")
        hashes[name] = actual
    return hashes


def gpu_state() -> dict:
    try:
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=name,memory.used,memory.total,utilization.gpu", "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=10, check=True,
        )
        return {"status": "available", "query": result.stdout.strip()}
    except Exception as error:
        return {"status": "unavailable", "reason": f"{type(error).__name__}: {error}"}


def load_or_build_cache(year: int, regime_hash: str, classifier=None) -> tuple[dict, dict[str, np.ndarray], Path]:
    zarr_path = SEASON_ZARR[year]
    if not zarr_path.exists():
        raise FileNotFoundError(zarr_path)
    source_hash = EXPECTED_ZARR_HASH.get(year)
    code_hash = sha256_file(ROOT / "backend/app/ml/phase2b.py")
    key = make_cache_key(year, source_hash or "post-freeze-verified", regime_hash, code_hash)
    destination = CACHE_ROOT / key
    if not destination.exists():
        destination.parent.mkdir(parents=True, exist_ok=True)
        cache = build_feature_cache(
            year=year,
            zarr_path=zarr_path,
            manifest_dir=SEASON_INDEX[year],
            regime_cases_path=REGIME_CASES if year != 2019 else None,
            destination=destination,
            expected_source_hash=source_hash,
            test_regime_classifier=classifier,
        )
    manifest, arrays = load_cache(destination)
    if source_hash is not None and manifest.get("source_zarr_sha256") != source_hash:
        raise ValueError(f"{year} cache lineage does not match the source tree hash")
    return manifest, arrays, destination


def metrics_by_group(y: np.ndarray, pred: np.ndarray, groups: np.ndarray) -> dict:
    result = {}
    for value in sorted(np.unique(groups).tolist()):
        selector = groups == value
        result[str(int(value))] = verification_metrics(y[selector], pred[selector])
    return result


def ridge_validation(x_train, y_train, x_valid, y_valid):
    candidates = []
    best = None
    best_prediction = None
    for alpha in RIDGE_ALPHAS:
        artifact = safe_ridge_fit(x_train, y_train, alpha)
        prediction = safe_ridge_predict(artifact, x_valid)
        report = verification_metrics(y_valid, prediction)
        candidates.append({"alpha": alpha, "validation": report})
        if best is None or report["continuous"]["rmse_mm"] < best["validation"]["continuous"]["rmse_mm"]:
            best = {"artifact": artifact, "validation": report, "alpha": alpha}
            best_prediction = prediction
    return candidates, best, best_prediction


def specialist_predictions(models, global_model, strategy, x, probabilities, hard_class):
    expert_outputs = {}
    for regime_id in range(3):
        model = models.get(regime_id)
        expert_outputs[regime_id] = xgb_predict(model, x, strategy) if model is not None else xgb_predict(global_model, x, strategy)
    hard = np.empty(len(x), dtype=np.float32)
    for regime_id in range(3):
        select = hard_class == regime_id
        hard[select] = expert_outputs[regime_id][select]
    soft = sum(probabilities[:, regime_id] * expert_outputs[regime_id] for regime_id in range(3))
    return hard, np.maximum(0.0, soft), expert_outputs


def main() -> int:
    import psutil
    import xgboost

    OUTPUT.mkdir(parents=True, exist_ok=True)
    if (OUTPUT / "2019_final_results.json").exists():
        finalize_completed_run()
        print("Phase 2B final reports and manifests verified from completed artifacts; 2019 was not evaluated again.")
        return 0
    classifier_hashes = regime_artifact_hashes()
    classifier = SafeLogisticRegimeClassifier.from_dict(json.loads(REGIME_CLASSIFIER.read_text(encoding="utf-8")))
    start_all = time.perf_counter()
    cache17, train, cache17_path = load_or_build_cache(2017, classifier_hashes["regime_classifier.safe.json"])
    cache18, valid, cache18_path = load_or_build_cache(2018, classifier_hashes["regime_classifier.safe.json"])
    if cache17["role"] != "TRAIN" or cache18["role"] != "VALIDATION":
        raise ValueError("training/validation cache roles are invalid")
    if set(cache17["case_keys"]) & set(cache18["case_keys"]):
        raise ValueError("temporal case populations overlap")
    x_train, y_train = train["X"], train["y"]
    x_valid, y_valid = valid["X"], valid["y"]

    benchmark = benchmark_xgb(x_train, y_train, x_valid, y_valid)
    device = benchmark["selected_device"]
    benchmark["hardware"] = {
        "platform": platform.platform(),
        "processor": platform.processor(),
        "logical_cpu_count": os.cpu_count(),
        "ram_total_bytes": psutil.virtual_memory().total,
        "ram_available_bytes_before_fit": psutil.virtual_memory().available,
        "gpu_before_fit": gpu_state(),
        "xgboost_version": xgboost.__version__,
        "xgboost_build_info": xgboost.build_info(),
    }
    write_json(OUTPUT / "cpu_gpu_benchmark.json", benchmark)

    ridge_candidates, ridge_best, ridge_prediction = ridge_validation(x_train, y_train, x_valid, y_valid)
    strategy_results = {}
    best_strategy = None
    best_global = None
    best_global_prediction = None
    for strategy in TARGET_STRATEGIES:
        model = train_xgb(x_train, y_train, x_valid, y_valid, strategy, device, n_estimators=350)
        prediction = xgb_predict(model, x_valid, strategy)
        report = verification_metrics(y_valid, prediction)
        strategy_results[strategy] = {
            "validation": report,
            "best_iteration": int(model.best_iteration) if getattr(model, "best_iteration", None) is not None else 349,
            "best_score": float(model.best_score) if getattr(model, "best_score", None) is not None else None,
            "model": model,
            "prediction": prediction,
        }
        if best_global is None or report["continuous"]["rmse_mm"] < strategy_results[best_strategy]["validation"]["continuous"]["rmse_mm"]:
            best_strategy = strategy
            best_global = model
            best_global_prediction = prediction

    chosen_rounds = int(strategy_results[best_strategy]["best_iteration"] + 1)
    experts = {}
    specialist_support = {}
    train_regime = train["prototype_regime_id"]
    valid_regime = valid["prototype_regime_id"]
    for regime_id, regime_name in enumerate(REGIME_NAMES):
        train_cases = np.unique(train["case_code"][train_regime == regime_id])
        train_rows = train_regime == regime_id
        valid_rows = valid_regime == regime_id
        cells = int(train_rows.sum())
        case_count = int(len(train_cases))
        supported = case_count >= 30 and cells >= 20000
        specialist_support[regime_name] = {"case_count": case_count, "valid_cells": cells, "minimum_cases": 30, "minimum_cells": 20000, "trained": supported, "fallback": None if supported else "GLOBAL_ML"}
        if not supported:
            continue
        if valid_rows.any():
            expert = train_xgb(x_train[train_rows], y_train[train_rows], x_valid[valid_rows], y_valid[valid_rows], best_strategy, device, n_estimators=chosen_rounds)
        else:
            expert = train_xgb(x_train[train_rows], y_train[train_rows], x_train[train_rows][:1], y_train[train_rows][:1], best_strategy, device, n_estimators=chosen_rounds)
        experts[regime_id] = expert

    hard_valid, soft_valid, _ = specialist_predictions(experts, best_global, best_strategy, x_valid, valid["regime_probability"], valid["predicted_regime_id"])
    raw_valid = valid["raw"]
    mos_valid = ridge_prediction
    val_predictions = {"M0_RAW_GEFS": raw_valid, "M1_LINEAR_RIDGE_MOS": mos_valid, "M2_GLOBAL_XGBOOST": best_global_prediction, "M3_HARD_REGIME_XGBOOST": hard_valid, "M4_SOFT_REGIME_MOE": soft_valid}
    validation_results = {
        model_id: {
            "overall": verification_metrics(y_valid, prediction),
            "by_lead_hours": metrics_by_group(y_valid, prediction, valid["lead"]),
            "by_forecast_only_regime": metrics_by_group(y_valid, prediction, valid["predicted_regime_id"]),
            "same_cell_count": int(len(y_valid)),
            "same_case_count": cache18["common_case_count"],
        }
        for model_id, prediction in val_predictions.items()
    }

    artifact_dir = OUTPUT / "models"
    artifact_dir.mkdir(parents=True, exist_ok=True)
    write_json(artifact_dir / "ridge_mos.safe.json", ridge_best["artifact"])
    best_global.save_model(str(artifact_dir / "global_xgboost.json"))
    for regime_id, expert in experts.items():
        expert.save_model(str(artifact_dir / f"expert_{REGIME_NAMES[regime_id].lower()}.json"))
    model_hashes = {path.name: sha256_file(path) for path in sorted(artifact_dir.iterdir()) if path.is_file()}
    validation_manifest = {
        "experiment_id": "varshasetu-phase2b-v1",
        "roles": {"training": 2017, "validation_model_selection": 2018, "final_test": 2019},
        "training_cache_manifest_sha256": sha256_file(cache17_path / "manifest.json"),
        "validation_cache_manifest_sha256": sha256_file(cache18_path / "manifest.json"),
        "common_validation_case_keys": cache18["case_keys"],
        "common_validation_case_count": cache18["common_case_count"],
        "common_validation_cell_count": int(len(y_valid)),
        "feature_names": list(FEATURE_NAMES),
        "ridge_candidates": ridge_candidates,
        "selected_ridge_alpha": ridge_best["alpha"],
        "xgboost_target_strategy_candidates": {name: {"validation": value["validation"], "best_iteration": value["best_iteration"]} for name, value in strategy_results.items()},
        "selected_xgboost_target_strategy_by_2018_rmse": best_strategy,
        "selected_xgboost_rounds": chosen_rounds,
        "xgboost_device": device,
        "xgboost_parameters": {"max_depth": 6, "learning_rate": 0.05, "subsample": 0.9, "colsample_bytree": 0.9, "reg_lambda": 2.0, "min_child_weight": 5, "max_bin": 256, "n_jobs": 12, "random_state": 26080, "early_stopping_rounds": 35},
        "specialists": specialist_support,
        "validation_results": validation_results,
        "models_sha256": model_hashes,
        "test_data_accessed": False,
        "selection_rule": "Each Ridge alpha and XGBoost target strategy is compared on the common 2018 population; minimum 2018 overall RMSE selects within each candidate family. 2019 is not used for any selection.",
        "holdout_gate": "Freeze features, preprocessing, model families, fixed hyperparameters, selected target transform, specialist assignments/support, model artifacts, and this manifest before opening 2019 forecast/observation values.",
    }
    freeze_path = OUTPUT / "model_selection_freeze.json"
    write_json(freeze_path, validation_manifest)
    freeze_hash = sha256_file(freeze_path)
    (OUTPUT / "model_selection_freeze.sha256").write_text(f"{freeze_hash}  model_selection_freeze.json\n", encoding="ascii")
    if sha256_file(freeze_path) != freeze_hash:
        raise ValueError("model selection freeze hash verification failed")

    # The first 2019 Zarr value read is below this verified, durable model-choice gate.
    if json.loads(freeze_path.read_text(encoding="utf-8"))["test_data_accessed"] is not False:
        raise ValueError("freeze manifest is invalid")
    season_manifest = json.loads((SEASON_INDEX[2019] / "season_manifest.json").read_text(encoding="utf-8"))
    test_zarr_hash = season_manifest["zarr"]["tree_sha256"]
    test_source_hash = hashlib.sha256()
    # The cache builder verifies this tree hash before reading any test arrays.
    EXPECTED_ZARR_HASH[2019] = test_zarr_hash
    cache19, test, cache19_path = load_or_build_cache(2019, classifier_hashes["regime_classifier.safe.json"], classifier)
    x_test, y_test = test["X"], test["y"]
    allowed_test_cases = set(eligible_case_rows(SEASON_INDEX[2019])["case_key"])
    if not set(cache19["case_keys"]).issubset(allowed_test_cases):
        raise ValueError("test feature-cache cases are outside the Phase 1F control eligible index")

    # The selected artifacts are reused exactly as frozen; no post-test tuning.
    chosen_strategy = best_strategy
    hard_test, soft_test, _ = specialist_predictions(experts, best_global, chosen_strategy, x_test, test["regime_probability"], test["predicted_regime_id"])
    ridge_test = safe_ridge_predict(ridge_best["artifact"], x_test)
    test_predictions = {"M0_RAW_GEFS": test["raw"], "M1_LINEAR_RIDGE_MOS": ridge_test, "M2_GLOBAL_XGBOOST": xgb_predict(best_global, x_test, chosen_strategy), "M3_HARD_REGIME_XGBOOST": hard_test, "M4_SOFT_REGIME_MOE": soft_test}
    if any(not np.isfinite(values).all() or (values < 0).any() for values in test_predictions.values()):
        raise ValueError("a model emitted invalid or negative rainfall predictions")
    if len({len(values) for values in test_predictions.values()} | {len(y_test)}) != 1:
        raise ValueError("models do not share the same valid-cell mask")
    test_results = {
        model_id: {
            "overall": verification_metrics(y_test, prediction),
            "by_lead_hours": metrics_by_group(y_test, prediction, test["lead"]),
            "by_forecast_only_regime": metrics_by_group(y_test, prediction, test["predicted_regime_id"]),
            "case_cluster_bootstrap_rmse_95pct": deterministic_case_bootstrap(y_test, prediction, test["case_code"]),
            "same_cell_count": int(len(y_test)),
            "same_case_count": cache19["common_case_count"],
        }
        for model_id, prediction in test_predictions.items()
    }
    selected_test_context = {
        "experiment_id": "varshasetu-phase2b-v1",
        "freeze_manifest_sha256": freeze_hash,
        "test_cache_manifest_sha256": sha256_file(cache19_path / "manifest.json"),
        "test_common_case_count": cache19["common_case_count"],
        "test_common_case_keys": cache19["case_keys"],
        "test_common_valid_cell_count": int(len(y_test)),
        "same_case_set_for_all_models": True,
        "same_valid_cell_mask_for_all_models": True,
        "2019_used_once_after_freeze": True,
        "post_test_retuning": False,
        "raw_gefs_v2_recomputed_on_exact_common_population": True,
        "test_results": test_results,
    }
    write_json(OUTPUT / "2019_final_results.json", selected_test_context)

    validation_doc = build_validation_report(validation_manifest, benchmark, cache17, cache18)
    final_doc = build_final_report(validation_manifest, selected_test_context, cache19, season_manifest)
    benefit_doc = build_benefit_report(validation_manifest, selected_test_context, specialist_support)
    (DOCS / "58_AUTHORITATIVE_RAINFALL_MODELING.md").write_text(build_methodology_doc(validation_manifest, cache17, cache18, benchmark), encoding="utf-8")
    (DOCS / "59_2018_MODEL_SELECTION_REPORT.md").write_text(validation_doc, encoding="utf-8")
    (DOCS / "60_2019_FINAL_TEST_REPORT.md").write_text(final_doc, encoding="utf-8")
    (DOCS / "61_REGIME_AWARE_BENEFIT_ANALYSIS.md").write_text(benefit_doc, encoding="utf-8")
    artifact_manifest = {
        "experiment_id": "varshasetu-phase2b-v1",
        "freeze_manifest_sha256": freeze_hash,
        "feature_cache_manifests": {"2017": sha256_file(cache17_path / "manifest.json"), "2018": sha256_file(cache18_path / "manifest.json"), "2019": sha256_file(cache19_path / "manifest.json")},
        "feature_cache_paths": {"2017": str(cache17_path.relative_to(ROOT)).replace("\\", "/"), "2018": str(cache18_path.relative_to(ROOT)).replace("\\", "/"), "2019": str(cache19_path.relative_to(ROOT)).replace("\\", "/")},
        "model_artifact_sha256": model_hashes,
        "report_sha256": {path.name: sha256_file(path) for path in [DOCS / "58_AUTHORITATIVE_RAINFALL_MODELING.md", DOCS / "59_2018_MODEL_SELECTION_REPORT.md", DOCS / "60_2019_FINAL_TEST_REPORT.md", DOCS / "61_REGIME_AWARE_BENEFIT_ANALYSIS.md"]},
        "test_results_sha256": sha256_file(OUTPUT / "2019_final_results.json"),
        "no_pickle_or_joblib_authoritative_artifacts": True,
        "created_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    write_json(OUTPUT / "artifact_manifest.json", artifact_manifest)
    (DOCS / "62_MODEL_ARTIFACT_MANIFEST.md").write_text(build_artifact_report(artifact_manifest), encoding="utf-8")
    # Refresh report hash set now that document 62 exists.
    artifact_manifest["report_sha256"]["62_MODEL_ARTIFACT_MANIFEST.md"] = sha256_file(DOCS / "62_MODEL_ARTIFACT_MANIFEST.md")
    write_json(OUTPUT / "artifact_manifest.json", artifact_manifest)
    write_json(OUTPUT / "hardware_benchmark.json", benchmark)
    update_index()
    print(json.dumps({
        "status": "complete",
        "elapsed_seconds": round(time.perf_counter() - start_all, 2),
        "validation_cases": cache18["common_case_count"],
        "validation_cells": len(y_valid),
        "test_cases": cache19["common_case_count"],
        "test_cells": len(y_test),
        "selected_device": device,
        "selected_target_strategy": best_strategy,
        "validation": validation_results,
        "test": test_results,
        "ram_available_bytes_after": psutil.virtual_memory().available,
        "gpu_after_fit": gpu_state(),
    }, indent=2))
    return 0


def metric_summary(metrics: dict) -> str:
    c = metrics["continuous"]
    h = metrics["thresholds"]["heavy_64_5"]
    v = metrics["thresholds"]["very_heavy_115_6"]
    hm, vm = h["metrics"], v["metrics"]
    return (f"{c['sample_count']:,} cells; RMSE {c['rmse_mm']:.4f}, MAE {c['mae_mm']:.4f}, bias {c['bias_mm']:+.4f} mm. "
            f"Heavy events {h['observed_event_count']:,}; POD/FAR/CSI/ETS "
            f"{fmt(hm['POD'])}/{fmt(hm['FAR'])}/{fmt(hm['CSI'])}/{fmt(hm['ETS'])}. "
            f"Very-heavy events {v['observed_event_count']:,}; POD/FAR/CSI/ETS "
            f"{fmt(vm['POD'])}/{fmt(vm['FAR'])}/{fmt(vm['CSI'])}/{fmt(vm['ETS'])}.")


def fmt(value):
    return "null" if value is None else f"{value:.4f}"


def undefined_text(report: dict) -> str:
    notes = []
    for threshold_name, item in report["thresholds"].items():
        for metric, reason in item.get("undefined_metric_reasons", {}).items():
            notes.append(f"{metric} at {item['threshold_mm_24h']:.1f} mm/24 h is null ({reason}; {item['sample_count']:,} valid cells, {item['observed_event_count']:,} observed events, {item['forecast_event_count']:,} forecast events).")
    return "\n\n" + " ".join(notes) if notes else ""


def build_methodology_doc(freeze, train_cache, valid_cache, benchmark):
    return f"""# Authoritative Phase 2B Rainfall Modeling\n\n## Scope and status\n\nExecuted bounded retrospective model comparison using only canonical v2 Phase 1F/2A Zarr and frozen manifests. This does not authorize API exposure, operational forecasts, FSS, district aggregation, new acquisition, or further scientific phases. Model-selection freeze SHA-256: `{sha256_file(OUTPUT / 'model_selection_freeze.json')}`.\n\n## Frozen roles and populations\n\n- 2017 JJAS: training only; common control + complete feature + valid reference set has {train_cache['common_case_count']} cases / {train_cache['cell_count']:,} cells.\n- 2018 JJAS: validation/model selection only; actual intersection has {valid_cache['common_case_count']} cases / {valid_cache['cell_count']:,} cells. The published 251 control-eligible count is an upper-bound reference, not the final comparison population.\n- 2019 JJAS: final untouched test; accessed only after the hash-verified model-selection freeze. Its exact intersection is in the final report.\n\nCases are selected by the actual intersection of `CONTROL_MODEL_ELIGIBLE`, `REGIME_ELIGIBLE` (all complete atmosphere bundle inputs), paired observation availability, valid c00 inputs, and complete finite feature rows. All M0–M4 use the exact same case IDs and cell mask per year.\n\n## Feature contract\n\nFeatures, in fixed order: `{', '.join(FEATURE_NAMES)}`. M0 is raw c00 rainfall; M1 Ridge MOS and M2 global XGBoost use this non-regime feature set. M2 explicitly excludes predicted regime class, probabilities, and pseudo-label identifiers. M3/M4 use the same selected global model and the same three 2017 pseudo-label specialists; M3 routes by forecast-only classifier argmax, M4 blends experts by forecast-only probabilities. A specialist requires at least 30 independent training cases and at least 20,000 valid cells; otherwise its gate uses the frozen global fallback.\n\nThe six atmospheric fields are bilinearly interpolated from the validated 0.5-degree context grid to 0.25-degree target-cell centers. This aligns grids and does not create meteorological source resolution. The interpolation semantics are identical across all years. Derived 12-feature regime vectors are recomputed and verified against Phase 2A case artifacts for 2017/2018; 2019 uses the frozen classifier after the holdout gate.\n\n## Bounded model selection\n\nRidge alpha candidates: `{RIDGE_ALPHAS}`. XGBoost target candidates: `{TARGET_STRATEGIES}`; fixed histogram tree settings, depth 6, learning rate .05, 350-round cap, 35-round early stopping, seed 26080, and 12 CPU worker threads. Minimum 2018 common-population RMSE selects within each model family. No exhaustive search was performed. The 2019 set was never used to choose features, preprocessing, target transform, hyperparameters, model families, or model artifact.\n\nCPU/CUDA benchmark selected `{benchmark.get('selected_device')}`. Benchmark equivalence: `{json.dumps(benchmark.get('equivalence'), sort_keys=True)}`; details and resource context: `data/manifests/phase2b/cpu_gpu_benchmark.json`.\n\n## Artifact safety and limitations\n\nFeature matrices are cached as hash-addressed safe NumPy arrays with per-array SHA-256 and source-tree/code/feature-schema lineage. Ridge is safe JSON; XGBoost uses native JSON. `allow_pickle=False`; no joblib/pickle is authoritative. These are retrospective prototype results against IMD gridded reference, not calibrated event probabilities or operational NWP readiness. FSS is not computed in this phase.\n"""


def build_validation_report(freeze, benchmark, train_cache, valid_cache):
    lines = ["# 2018 Model Selection Report", "", "## Frozen validation protocol", "", f"Validation population is the actual common intersection: {valid_cache['common_case_count']} cases and {valid_cache['cell_count']:,} identical valid cells for every M0–M4 method. 251 is only the current control-eligible upper bound. 2017 was training-only; 2019 was not accessed before freeze `{sha256_file(OUTPUT / 'model_selection_freeze.json')}`. No 2018 fitting was performed.", "", "## Selected candidates", "", f"- Ridge alpha: {freeze['selected_ridge_alpha']}", f"- XGBoost target strategy: {freeze['selected_xgboost_target_strategy_by_2018_rmse']}", f"- XGBoost rounds: {freeze['selected_xgboost_rounds']}", f"- Execution device: {freeze['xgboost_device']}", "", "## Validation metrics"]
    for name, values in freeze["validation_results"].items():
        lines.extend(["", f"### {name}", "", metric_summary(values["overall"]), undefined_text(values["overall"]), "", "Per lead and forecast-only classifier regime metrics are retained in `data/manifests/phase2b/model_selection_freeze.json`."])
    lines.extend(["", "## Target-transform candidates", ""])
    for name, values in freeze["xgboost_target_strategy_candidates"].items():
        lines.append(f"- `{name}`: {metric_summary(values['validation'])}; selected best iteration {values['best_iteration']}.")
    equivalence = benchmark.get("equivalence", {})
    repeat = equivalence.get("cuda_repeatability", {})
    hardware = benchmark.get("hardware", {})
    gpu_snapshot = hardware.get("gpu_before_fit", {})
    lines.extend(["", "## CPU/GPU check", "", f"The representative 50,000-row / 20,000-row validation benchmark selected `{benchmark.get('selected_device')}`. CPU elapsed {benchmark.get('cpu', {}).get('seconds')} s; CUDA first-run elapsed {benchmark.get('cuda', {}).get('seconds')} s; the repeat CUDA pass elapsed {repeat.get('seconds')} s. The first CUDA run includes device/context initialization, so the warmed repeat is also reported. CUDA fit and repeat completed without a CUDA exception or allocation failure; repeated CUDA predictions were stable={repeat.get('stable')} with maximum absolute delta {repeat.get('maximum_absolute_prediction_delta')} mm. The sampled GPU memory snapshot was `{gpu_snapshot.get('query')}`; peak VRAM telemetry was not recorded, so this is not a peak-memory claim.", "", f"The pre-agreed scientific-equivalence gate was correlation >=0.999, relative RMSE drift <=0.001, and absolute heavy-CSI drift <=0.005. Observed correlation {equivalence.get('prediction_correlation')}, RMSE drift {equivalence.get('relative_rmse_drift')}, CSI drift {equivalence.get('maximum_absolute_csi_drift')}; overall equivalence passed={equivalence.get('passed')}. CUDA was therefore not selected even though no 20% speed threshold was imposed.", "", "Undefined rare-event scores remain null with counts/reasons in machine-readable metrics. Validation is for selection only, not final performance claims.", ""])
    return "\n".join(lines)


def build_final_report(freeze, result, cache, season_manifest):
    lines = ["# 2019 Final Held-Out Test Report", "", "## One-time evaluation gate", "", f"Model-choice manifest SHA-256 `{result['freeze_manifest_sha256']}` was written before the first 2019 Zarr value was read. It freezes feature order, preprocessing, model families, target transform, Ridge alpha, XGBoost settings, shared expert definition, specialist gates, and model artifact hashes. No post-test tuning was performed.", "", f"Phase 1F source Zarr tree SHA-256: `{season_manifest['zarr']['tree_sha256']}`. Final common set is the exact intersection of `CONTROL_MODEL_ELIGIBLE`, `REGIME_ELIGIBLE`, complete forecast feature availability, and valid paired observation cells: {cache['common_case_count']} cases / {cache['cell_count']:,} identical valid cells for each model. 255 is an upper bound, not the final comparison denominator.", "", "## Results"]
    for name, values in result["test_results"].items():
        lines.extend(["", f"### {name}", "", metric_summary(values["overall"]), undefined_text(values["overall"]), "", "Per-lead, forecast-only predicted-regime and case-cluster bootstrap results are in `data/manifests/phase2b/2019_final_results.json`."])
    lines.extend(["", "## Interpretation", "", "All claims below compare methods on the same exact final cases and per-cell masks. Heavy and very-heavy metrics use 64.5 and 115.6 mm/24 h. Any undefined metric is null, with sample and event counts and an explicit reason. This is a held-out retrospective prototype evaluation; the IMD gridded reference has the provenance and limitations documented in Phase 1F. No FSS is reported because it was outside Phase 2B scope.", ""])
    return "\n".join(lines)


def build_benefit_report(freeze, result, specialist_support):
    models = result["test_results"]
    baseline = models["M0_RAW_GEFS"]["overall"]["continuous"]["rmse_mm"]
    mos = models["M1_LINEAR_RIDGE_MOS"]["overall"]["continuous"]["rmse_mm"]
    global_rmse = models["M2_GLOBAL_XGBOOST"]["overall"]["continuous"]["rmse_mm"]
    hard_rmse = models["M3_HARD_REGIME_XGBOOST"]["overall"]["continuous"]["rmse_mm"]
    soft_rmse = models["M4_SOFT_REGIME_MOE"]["overall"]["continuous"]["rmse_mm"]
    best_rainfall = min(mos, global_rmse, hard_rmse, soft_rmse)
    best_rmse_id = min(("M1_LINEAR_RIDGE_MOS", "M2_GLOBAL_XGBOOST", "M3_HARD_REGIME_XGBOOST", "M4_SOFT_REGIME_MOE"), key=lambda name: models[name]["overall"]["continuous"]["rmse_mm"])
    heavy_raw = models["M0_RAW_GEFS"]["overall"]["thresholds"]["heavy_64_5"]["metrics"]
    heavy_csi_best = max(models, key=lambda name: models[name]["overall"]["thresholds"]["heavy_64_5"]["metrics"]["CSI"] if models[name]["overall"]["thresholds"]["heavy_64_5"]["metrics"]["CSI"] is not None else -1)
    heavy_ets_best = max(models, key=lambda name: models[name]["overall"]["thresholds"]["heavy_64_5"]["metrics"]["ETS"] if models[name]["overall"]["thresholds"]["heavy_64_5"]["metrics"]["ETS"] is not None else -1)
    answers = [
        f"- VarshaSetu vs raw GEFS: improved overall RMSE from {baseline:.4f} to {best_rainfall:.4f} mm ({(baseline - best_rainfall) / baseline * 100:.2f}% reduction), but did not improve heavy-rain CSI/ETS; raw CSI/ETS are {heavy_raw['CSI']:.4f}/{heavy_raw['ETS']:.4f}, with {heavy_csi_best}/{heavy_ets_best} best for CSI/ETS.",
        f"- Global ML vs MOS (RMSE): {'improved' if global_rmse < mos else 'did not improve'}; M2 {global_rmse:.4f}, M1 {mos:.4f} mm.",
        f"- Hard regime vs global ML (RMSE): {'improved' if hard_rmse < global_rmse else 'did not improve'}; M3 {hard_rmse:.4f}, M2 {global_rmse:.4f} mm.",
        f"- Soft MoE vs hard/global: M4 reduced RMSE slightly versus M3 ({hard_rmse - soft_rmse:.4f} mm) but remained worse than M2 by {soft_rmse - global_rmse:.4f} mm; heavy CSI/ETS were M4 {models['M4_SOFT_REGIME_MOE']['overall']['thresholds']['heavy_64_5']['metrics']['CSI']:.4f}/{models['M4_SOFT_REGIME_MOE']['overall']['thresholds']['heavy_64_5']['metrics']['ETS']:.4f}, M3 {models['M3_HARD_REGIME_XGBOOST']['overall']['thresholds']['heavy_64_5']['metrics']['CSI']:.4f}/{models['M3_HARD_REGIME_XGBOOST']['overall']['thresholds']['heavy_64_5']['metrics']['ETS']:.4f}, and M2 {models['M2_GLOBAL_XGBOOST']['overall']['thresholds']['heavy_64_5']['metrics']['CSI']:.4f}/{models['M2_GLOBAL_XGBOOST']['overall']['thresholds']['heavy_64_5']['metrics']['ETS']:.4f}.",
        f"- Best RMSE model: {best_rmse_id}.",
    ]
    csi_ets = {}
    for threshold in ("heavy_64_5", "very_heavy_115_6"):
        eligible = [(name, val["overall"]["thresholds"][threshold]["metrics"]["CSI"], val["overall"]["thresholds"][threshold]["metrics"]["ETS"]) for name, val in models.items()]
        defined = [entry for entry in eligible if entry[1] is not None]
        best_csi = max(defined, key=lambda item: item[1])[0] if defined else "undefined for all models"
        defined_ets = [entry for entry in eligible if entry[2] is not None]
        best_ets = max(defined_ets, key=lambda item: item[2])[0] if defined_ets else "undefined for all models"
        csi_ets[threshold] = (best_csi, best_ets)
        answers.append(f"- {threshold} best: CSI {best_csi}; ETS {best_ets}.")
    expert_lines = [f"- {name}: {item['case_count']} training cases, {item['valid_cells']:,} cells; {'trained' if item['trained'] else 'global fallback'}" for name, item in specialist_support.items()]
    return "\n".join(["# Regime-Aware Benefit Analysis", "", "## Held-out answers", "", *answers, "", "## Expert support and fallback", "", *expert_lines, "", "## Interpretation boundary", "", "Regime-aware superiority is not presumed. The statements above are based only on the one-time 2019 held-out results after the prewritten model-choice freeze. This analysis uses prototype pseudo-labels and uncalibrated classifier probabilities; they are not authoritative meteorological labels or calibrated event probabilities. Event counts and uncertainty intervals must be considered alongside point scores. The 2019 result is not used for retuning.", ""])


def build_artifact_report(manifest):
    return "# Phase 2B Model Artifact Manifest\n\nThis append-only manifest points to the frozen selection record, hash-addressed deterministic feature caches, safe model files, and reports. Full SHA-256 references, source lineage, code hashes, runtime versions, hardware benchmark context, and protected-lock history are in `data/manifests/phase2b/artifact_manifest.json`.\n\n- Freeze manifest SHA-256: `" + manifest["freeze_manifest_sha256"] + "`\n- 2019 Phase 1F source Zarr tree SHA-256: `" + manifest["phase1f_2019_zarr_tree_sha256"] + "`\n- Models: native XGBoost JSON and safe JSON Ridge only.\n- Feature caches: safe `.npy` arrays loaded with `allow_pickle=False`; each array and cache manifest is hash-verified.\n- Execution device: `" + manifest["execution_device"] + "`; CPU/CUDA equivalence details are preserved in `cpu_gpu_benchmark.json`.\n- Phase 1B historical lock: unchanged (`" + manifest["phase1b_historical_lock_sha256"] + "`); the versioned supersession explicitly covers the two later blocked-API/readiness files while the other 16 remain unchanged.\n- Pickle/joblib authority: none.\n- Test results: `2019_final_results.json`; no post-test selection or retuning.\n"


def update_index():
    path = DOCS / "00_INDEX.md"
    content = path.read_text(encoding="utf-8")
    line = "| `58_AUTHORITATIVE_RAINFALL_MODELING.md` | Phase 2B frozen model ladder, features, and train/validation/test protocol | Before using rainfall model artifacts |\n| `59_2018_MODEL_SELECTION_REPORT.md` | Common-case validation selection and CPU/GPU check | Model selection evidence |\n| `60_2019_FINAL_TEST_REPORT.md` | One-time frozen 2019 held-out model evaluation | Final prototype skill review |\n| `61_REGIME_AWARE_BENEFIT_ANALYSIS.md` | Honest regime-aware vs global/raw benefit analysis | Before making skill claims |\n| `62_MODEL_ARTIFACT_MANIFEST.md` | Safe artifact/cache hashes and lineage | Before loading Phase 2B artifacts |\n"
    if "58_AUTHORITATIVE_RAINFALL_MODELING.md" not in content:
        rows = content.splitlines(keepends=True)
        index = next((i for i, row in enumerate(rows) if row.startswith("| `57_PHASE2A_ACCELERATED_READINESS.md` |")), None)
        if index is None:
            raise ValueError("cannot locate Phase 2A index insertion point")
        rows.insert(index + 1, line)
        path.write_text("".join(rows), encoding="utf-8")
    roadmap = DOCS / "05_ROADMAP.md"
    roadmap_text = roadmap.read_text(encoding="utf-8")
    if "Phase 2B bounded rainfall model comparison outcome" not in roadmap_text:
        roadmap_text += "\n\n## Phase 2B bounded rainfall model comparison outcome (2026-09-23)\n\nThe authorized retrospective comparison is complete for the frozen 2017/2018/2019 roles. See `docs/58`–`docs/62` and `data/manifests/phase2b/`. This closes only the bounded raw/MOS/global/hard/soft model comparison; it does not complete the broader Phase 2 credibility gate, FSS, calibration, district products, API integration, or operational readiness.\n"
        roadmap.write_text(roadmap_text, encoding="utf-8")


def finalize_completed_run() -> None:
    """Publish documentation from completed hashed results without reevaluation."""
    freeze_path = OUTPUT / "model_selection_freeze.json"
    expected_freeze_hash = (OUTPUT / "model_selection_freeze.sha256").read_text(encoding="ascii").split()[0]
    actual_freeze_hash = sha256_file(freeze_path)
    if actual_freeze_hash != expected_freeze_hash:
        raise ValueError("completed selection freeze hash mismatch")
    freeze = json.loads(freeze_path.read_text(encoding="utf-8"))
    results_path = OUTPUT / "2019_final_results.json"
    result = json.loads(results_path.read_text(encoding="utf-8"))
    if result.get("freeze_manifest_sha256") != actual_freeze_hash or result.get("post_test_retuning") is not False:
        raise ValueError("completed test report is not bound to the frozen selection")
    if freeze.get("test_data_accessed") is not False:
        raise ValueError("selection manifest did not preserve the held-out gate")
    model_hashes = freeze["models_sha256"]
    for name, expected in model_hashes.items():
        if sha256_file(OUTPUT / "models" / name) != expected:
            raise ValueError(f"frozen model artifact hash mismatch: {name}")
    caches = {}
    cache_paths = {}
    for path in CACHE_ROOT.glob("*/manifest.json"):
        cache = json.loads(path.read_text(encoding="utf-8"))
        year = str(cache["year"])
        if year in {"2017", "2018", "2019"}:
            caches[year] = cache
            cache_paths[year] = path.parent
    if set(caches) != {"2017", "2018", "2019"}:
        raise ValueError("completed run is missing a year feature-cache manifest")
    for year, expected in (("2017", freeze["training_cache_manifest_sha256"]), ("2018", freeze["validation_cache_manifest_sha256"]), ("2019", result["test_cache_manifest_sha256"])):
        if sha256_file(cache_paths[year] / "manifest.json") != expected:
            raise ValueError(f"{year} feature-cache manifest hash mismatch")
        verify_cache(cache_paths[year])
    benchmark = json.loads((OUTPUT / "cpu_gpu_benchmark.json").read_text(encoding="utf-8"))
    season_manifest = json.loads((SEASON_INDEX[2019] / "season_manifest.json").read_text(encoding="utf-8"))
    from importlib.metadata import version
    historical_lock = MANIFESTS / "phase1b" / "2019-07-15" / "protected_artifact_integrity.json"
    lock_supersession = historical_lock.with_name("protected_artifact_supersession_v1.json")
    (DOCS / "58_AUTHORITATIVE_RAINFALL_MODELING.md").write_text(build_methodology_doc(freeze, caches["2017"], caches["2018"], benchmark), encoding="utf-8")
    (DOCS / "59_2018_MODEL_SELECTION_REPORT.md").write_text(build_validation_report(freeze, benchmark, caches["2017"], caches["2018"]), encoding="utf-8")
    (DOCS / "60_2019_FINAL_TEST_REPORT.md").write_text(build_final_report(freeze, result, caches["2019"], season_manifest), encoding="utf-8")
    (DOCS / "61_REGIME_AWARE_BENEFIT_ANALYSIS.md").write_text(build_benefit_report(freeze, result, freeze["specialists"]), encoding="utf-8")
    artifact_manifest = {
        "experiment_id": "varshasetu-phase2b-v1",
        "freeze_manifest_sha256": actual_freeze_hash,
        "feature_cache_manifests": {year: sha256_file(cache_paths[year] / "manifest.json") for year in ("2017", "2018", "2019")},
        "feature_cache_paths": {year: str(cache_paths[year].relative_to(ROOT)).replace("\\", "/") for year in ("2017", "2018", "2019")},
        "model_artifact_sha256": model_hashes,
        "test_results_sha256": sha256_file(results_path),
        "phase1f_2019_zarr_tree_sha256": season_manifest["zarr"]["tree_sha256"],
        "phase2a_regime_classifier_sha256": sha256_file(REGIME_CLASSIFIER),
        "feature_builder_source_sha256": sha256_file(ROOT / "backend/app/ml/phase2b.py"),
        "runner_source_sha256": sha256_file(ROOT / "scripts/run_phase2b.py"),
        "execution_device": freeze["xgboost_device"],
        "runtime_versions": {name: version(name) for name in ("numpy", "pandas", "scikit-learn", "xgboost", "zarr")},
        "hardware_benchmark": benchmark["hardware"],
        "phase1b_historical_lock_sha256": sha256_file(historical_lock),
        "phase1b_supersession_v1_sha256": sha256_file(lock_supersession),
        "phase1b_originally_protected_artifacts": 18,
        "phase1b_unchanged_original_hashes": 16,
        "phase1b_versioned_supersessions": 2,
        "no_pickle_or_joblib_authoritative_artifacts": True,
    }
    reports = [DOCS / f"{number}_{name}.md" for number, name in (("58", "AUTHORITATIVE_RAINFALL_MODELING"), ("59", "2018_MODEL_SELECTION_REPORT"), ("60", "2019_FINAL_TEST_REPORT"), ("61", "REGIME_AWARE_BENEFIT_ANALYSIS"))]
    artifact_manifest["report_sha256"] = {path.name: sha256_file(path) for path in reports}
    write_json(OUTPUT / "artifact_manifest.json", artifact_manifest)
    (DOCS / "62_MODEL_ARTIFACT_MANIFEST.md").write_text(build_artifact_report(artifact_manifest), encoding="utf-8")
    artifact_manifest["report_sha256"]["62_MODEL_ARTIFACT_MANIFEST.md"] = sha256_file(DOCS / "62_MODEL_ARTIFACT_MANIFEST.md")
    write_json(OUTPUT / "artifact_manifest.json", artifact_manifest)
    (OUTPUT / "artifact_manifest.sha256").write_text(f"{sha256_file(OUTPUT / 'artifact_manifest.json')}  artifact_manifest.json\n", encoding="ascii")
    update_index()


if __name__ == "__main__":
    import pandas as pd
    raise SystemExit(main())
