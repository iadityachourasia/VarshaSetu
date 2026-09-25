"""Deterministic, leakage-gated Phase 2B rainfall-model experiment helpers.

This module deliberately keeps feature construction and evaluation on the
canonical Phase 2A/1F Zarr stores. It never imports or reads the legacy CSV or
joblib models.
"""

from __future__ import annotations

import hashlib
import json
import os
from types import SimpleNamespace
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd
import zarr

from backend.app.ml.forecast_regimes import (
    ATMOSPHERIC_VARIABLES,
    FEATURE_NAMES as REGIME_FEATURE_NAMES,
    SafeLogisticRegimeClassifier,
    extract_regime_features,
)


ROOT = Path(__file__).resolve().parents[3]
PRODUCTS = ("day1_24h", "day2_24h", "day3_24h")
FEATURE_NAMES = (
    "raw_c00_rain_mm",
    *[f"forecast_{name}" for name in ATMOSPHERIC_VARIABLES],
    *REGIME_FEATURE_NAMES,
    "latitude_deg",
    "longitude_deg",
    "lead_hours",
)
REGIME_NAMES = ("ACTIVE_MONSOON", "BREAK_WEAK_MONSOON", "LOW_DEPRESSION_INFLUENCED")
HEAVY_THRESHOLDS_MM = {"heavy_64_5": 64.5, "very_heavy_115_6": 115.6}
SCHEMA_VERSION = "phase2b-feature-matrix-v1"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def tree_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    for item in sorted(candidate for candidate in path.rglob("*") if candidate.is_file()):
        digest.update(item.relative_to(path).as_posix().encode("utf-8"))
        digest.update(bytes.fromhex(sha256_file(item)))
    return digest.hexdigest()


def write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".partial")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def file_sha256s(directory: Path) -> dict[str, str]:
    return {item.name: sha256_file(item) for item in sorted(directory.glob("*.npy"))}


def verify_cache(directory: Path) -> dict:
    manifest_path = directory / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("schema") != SCHEMA_VERSION:
        raise ValueError("feature cache schema mismatch")
    actual = file_sha256s(directory)
    if actual != manifest.get("arrays_sha256"):
        raise ValueError("feature cache array hashes do not match")
    return manifest


def _case_key(initialization: str, product: str) -> str:
    timestamp = pd.Timestamp(initialization).tz_convert("UTC").strftime("%Y-%m-%dT%H:%M:%SZ")
    return f"{timestamp}|{product}"


def eligible_case_rows(manifest_dir: Path) -> pd.DataFrame:
    control = pd.read_csv(manifest_dir / "control_model_index.csv")
    regime = pd.read_csv(manifest_dir / "regime_index.csv")
    control = control.loc[
        control["CONTROL_MODEL_ELIGIBLE"].astype(bool)
        & control["PAIR_VALID"].astype(bool)
    ]
    regime = regime.loc[regime["REGIME_ELIGIBLE"].astype(bool)]
    control_keys = set(zip(control["initialization"], control["product"]))
    regime_keys = set(zip(regime["initialization"], regime["product"]))
    keys = control_keys & regime_keys
    result = control.loc[
        [(row.initialization, row.product) in keys for row in control.itertuples()]
    ].copy()
    result["case_key"] = [_case_key(i, p) for i, p in zip(result["initialization"], result["product"])]
    return result.sort_values(["initialization", "product"], kind="stable").reset_index(drop=True)


def _bilinear_indices(source: np.ndarray, target: np.ndarray):
    if source.ndim != 1 or target.ndim != 1 or not np.all(np.diff(source) > 0):
        raise ValueError("bilinear interpolation requires increasing one-dimensional axes")
    upper = np.searchsorted(source, target, side="right")
    upper = np.clip(upper, 1, len(source) - 1)
    lower = upper - 1
    fraction = (target - source[lower]) / (source[upper] - source[lower])
    return lower, upper, fraction


def bilinear_to_target(
    field: np.ndarray,
    source_latitude: np.ndarray,
    source_longitude: np.ndarray,
    target_latitude: np.ndarray,
    target_longitude: np.ndarray,
) -> np.ndarray:
    """Interpolate context-grid values at target centers (alignment only)."""
    field = np.asarray(field, dtype=np.float64)
    slat = np.asarray(source_latitude, dtype=np.float64)
    slon = np.asarray(source_longitude, dtype=np.float64)
    tlat = np.asarray(target_latitude, dtype=np.float64)
    tlon = np.asarray(target_longitude, dtype=np.float64)
    if field.shape != (slat.size, slon.size):
        raise ValueError("source field does not align with context grid")
    y0, y1, wy = _bilinear_indices(slat, tlat)
    x0, x1, wx = _bilinear_indices(slon, tlon)
    v00 = field[np.ix_(y0, x0)]
    v01 = field[np.ix_(y0, x1)]
    v10 = field[np.ix_(y1, x0)]
    v11 = field[np.ix_(y1, x1)]
    return (
        (1 - wy[:, None]) * (1 - wx[None, :]) * v00
        + (1 - wy[:, None]) * wx[None, :] * v01
        + wy[:, None] * (1 - wx[None, :]) * v10
        + wy[:, None] * wx[None, :] * v11
    )


def make_cache_key(year: int, source_hash: str, regime_hash: str, code_hash: str) -> str:
    descriptor = {
        "schema": SCHEMA_VERSION,
        "year": year,
        "source_zarr_sha256": source_hash,
        "phase2a_regime_artifact_sha256": regime_hash,
        "feature_builder_sha256": code_hash,
        "features": list(FEATURE_NAMES),
        "bilinear": "regular-grid-bilinear-float64-then-float32-features-v1",
    }
    encoded = json.dumps(descriptor, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def build_feature_cache(
    *, year: int, zarr_path: Path, manifest_dir: Path, regime_cases_path: Path,
    destination: Path, expected_source_hash: str | None = None,
    test_regime_classifier: SafeLogisticRegimeClassifier | None = None,
) -> dict:
    """Build one hash-addressed cache; reads one eligible case at a time."""
    if destination.exists():
        return verify_cache(destination)
    observed_source_hash = tree_sha256(zarr_path)
    if expected_source_hash and observed_source_hash != expected_source_hash:
        raise ValueError(f"{year} source Zarr tree hash does not match its frozen manifest")
    regime_df = pd.read_csv(regime_cases_path) if regime_cases_path is not None else pd.DataFrame()
    if not regime_df.empty:
        regime_df = regime_df.loc[regime_df.year == year].copy()
    regime_lookup = {_case_key(row.initialization, row.product): row for row in regime_df.itertuples(index=False)}
    population = eligible_case_rows(manifest_dir)
    group = zarr.open_group(str(zarr_path), mode="r")
    context_lat = np.asarray(group["context_latitude"][:], dtype=np.float64)
    context_lon = np.asarray(group["context_longitude"][:], dtype=np.float64)
    target_lat = np.asarray(group["target_latitude"][:], dtype=np.float64)
    target_lon = np.asarray(group["target_longitude"][:], dtype=np.float64)
    inits = np.asarray(group["init_time_unix_seconds"][:], dtype=np.int64)
    init_lookup = {pd.Timestamp(value, unit="s", tz="UTC").strftime("%Y-%m-%dT%H:%M:%SZ"): i for i, value in enumerate(inits)}
    lead_to_index = {int(value): i for i, value in enumerate(group["lead_hours"][:])}
    product_to_index = {name: index for index, name in enumerate(PRODUCTS)}
    blocks: dict[str, list[np.ndarray]] = {name: [] for name in ("X", "y", "raw", "case_code", "lead", "regime_probability", "prototype_regime_id", "predicted_regime_id", "pixel_i", "pixel_j")}
    accepted_cases: list[dict] = []
    index_case_keys: list[str] = []
    for row in population.itertuples(index=False):
        key = row.case_key
        if key not in regime_lookup and year != 2019:
            continue
        timestamp, product = key.split("|")
        init_index = init_lookup.get(timestamp)
        product_index = product_to_index.get(product)
        if init_index is None or product_index is None:
            continue
        regime = regime_lookup.get(key)
        lead = int(regime.lead_hours) if regime is not None else int(group["lead_hours"][product_index])
        if lead not in lead_to_index:
            continue
        lead_index = lead_to_index[lead]
        rain = np.asarray(group["forecast_rain"][init_index, product_index, 0], dtype=np.float64)
        obs = np.asarray(group["observation_rain"][init_index, product_index], dtype=np.float64)
        mask = np.asarray(group["valid_mask"][init_index, product_index], dtype=bool)
        atmosphere = np.asarray(group["atmosphere"][init_index, lead_index], dtype=np.float64)
        if not np.isfinite(atmosphere).all() or np.any(atmosphere <= -999):
            continue
        aligned = np.stack([
            bilinear_to_target(field, context_lat, context_lon, target_lat, target_lon)
            for field in atmosphere
        ])
        derived = extract_regime_features(atmosphere, context_lat, context_lon)
        if regime is None:
            if test_regime_classifier is None:
                raise ValueError("2019 cache creation requires the frozen Phase 2A regime classifier")
            probabilities = test_regime_classifier.predict_proba(derived[None, :])[0].astype(np.float32)
            regime = SimpleNamespace(
                lead_hours=lead,
                prototype_regime_id=-1,
                predicted_regime_id=int(np.argmax(probabilities)),
                probability_active=float(probabilities[0]),
                probability_break_weak=float(probabilities[1]),
                probability_low_depression=float(probabilities[2]),
            )
        else:
            published_derived = np.asarray([getattr(regime, name) for name in REGIME_FEATURE_NAMES], dtype=np.float64)
            if not np.allclose(derived, published_derived, rtol=1e-8, atol=1e-8):
                raise ValueError(f"Phase 2A derived features mismatch for {key}")
        valid = mask & np.isfinite(obs) & (obs >= 0) & np.isfinite(rain) & (rain >= 0)
        valid &= np.isfinite(aligned).all(axis=0)
        if not valid.any():
            continue
        rows, cols = np.where(valid)
        n = len(rows)
        matrix = np.column_stack([
            rain[rows, cols], aligned[:, rows, cols].T,
            np.broadcast_to(derived, (n, len(derived))),
            target_lat[rows], target_lon[cols], np.full(n, lead, dtype=np.float64),
        ]).astype(np.float32)
        if matrix.shape[1] != len(FEATURE_NAMES) or not np.isfinite(matrix).all():
            raise ValueError(f"non-finite or malformed feature rows for {key}")
        probabilities = np.asarray([
            regime.probability_active, regime.probability_break_weak, regime.probability_low_depression
        ], dtype=np.float32)
        if probabilities.shape != (3,) or not np.isclose(probabilities.sum(), 1, atol=1e-6):
            raise ValueError(f"invalid Phase 2A regime probabilities for {key}")
        code = len(index_case_keys)
        index_case_keys.append(key)
        accepted_cases.append({"case_key": key, "product": product, "lead_hours": lead, "valid_cells": n})
        blocks["X"].append(matrix)
        blocks["y"].append(obs[rows, cols].astype(np.float32))
        blocks["raw"].append(rain[rows, cols].astype(np.float32))
        blocks["case_code"].append(np.full(n, code, dtype=np.int16))
        blocks["lead"].append(np.full(n, lead, dtype=np.int16))
        blocks["regime_probability"].append(np.broadcast_to(probabilities, (n, 3)).copy())
        blocks["prototype_regime_id"].append(np.full(n, int(regime.prototype_regime_id), dtype=np.int8))
        blocks["predicted_regime_id"].append(np.full(n, int(regime.predicted_regime_id), dtype=np.int8))
        blocks["pixel_i"].append(rows.astype(np.int8))
        blocks["pixel_j"].append(cols.astype(np.int8))
    if not accepted_cases:
        raise ValueError(f"no usable common cases for {year}")
    arrays = {name: np.concatenate(items, axis=0) for name, items in blocks.items()}
    destination.parent.mkdir(parents=True, exist_ok=True)
    staging = destination.with_name(destination.name + ".partial")
    staging.mkdir(parents=True, exist_ok=False)
    for name, array in arrays.items():
        np.save(staging / f"{name}.npy", array, allow_pickle=False)
    manifest = {
        "schema": SCHEMA_VERSION,
        "year": year,
        "role": {2017: "TRAIN", 2018: "VALIDATION", 2019: "FINAL_TEST"}[year],
        "source_zarr_sha256": observed_source_hash,
        "regime_cases_sha256": sha256_file(regime_cases_path) if regime_cases_path is not None else None,
        "feature_names": list(FEATURE_NAMES),
        "feature_count": len(FEATURE_NAMES),
        "candidate_cases": int(len(population)),
        "common_cases": accepted_cases,
        "common_case_count": len(accepted_cases),
        "cell_count": int(len(arrays["y"])),
        "arrays_sha256": file_sha256s(staging),
        "case_keys": index_case_keys,
        "valid_cell_rule": "valid_mask==1 AND observation is finite/nonnegative AND c00 rainfall finite/nonnegative AND every bilinearly aligned atmospheric feature finite",
        "interpolation": "bilinear alignment from the validated 0.5-degree context grid to 0.25-degree target-cell centers; no new meteorological source resolution is created",
    }
    write_json(staging / "manifest.json", manifest)
    os.replace(staging, destination)
    return verify_cache(destination)


def load_cache(directory: Path) -> tuple[dict, dict[str, np.ndarray]]:
    manifest = verify_cache(directory)
    arrays = {path.stem: np.load(path, allow_pickle=False) for path in directory.glob("*.npy")}
    return manifest, arrays


def continuous_metrics(observed: np.ndarray, predicted: np.ndarray) -> dict:
    error = np.asarray(predicted, dtype=np.float64) - np.asarray(observed, dtype=np.float64)
    if error.size == 0:
        return {"sample_count": 0, "rmse_mm": None, "mae_mm": None, "bias_mm": None}
    return {"sample_count": int(error.size), "rmse_mm": float(np.sqrt(np.mean(error**2))), "mae_mm": float(np.mean(np.abs(error))), "bias_mm": float(np.mean(error))}


def event_metrics(observed: np.ndarray, predicted: np.ndarray, threshold: float) -> dict:
    obs = np.asarray(observed) >= threshold
    fcst = np.asarray(predicted) >= threshold
    hits = int(np.count_nonzero(obs & fcst))
    misses = int(np.count_nonzero(obs & ~fcst))
    false_alarms = int(np.count_nonzero(~obs & fcst))
    event_count = int(obs.sum())
    forecast_event_count = int(fcst.sum())
    n = int(obs.size)
    random_hits = ((hits + misses) * (hits + false_alarms) / n) if n else 0.0
    denominators = {
        "POD": hits + misses,
        "FAR": hits + false_alarms,
        "CSI": hits + misses + false_alarms,
        "ETS": hits + misses + false_alarms - random_hits,
    }
    numerators = {"POD": hits, "FAR": false_alarms, "CSI": hits, "ETS": hits - random_hits}
    metrics = {}
    undefined_reasons = {}
    for name, denominator in denominators.items():
        if denominator == 0:
            metrics[name] = None
            undefined_reasons[name] = {
                "POD": "no observed events",
                "FAR": "no forecast events",
                "CSI": "no observed or forecast events",
                "ETS": "random-corrected event denominator is zero",
            }[name]
        else:
            metrics[name] = float(numerators[name] / denominator)
    reason = None if event_count else "no observed events at this threshold"
    if n == 0:
        reason = "no valid cells"
    return {
        "threshold_mm_24h": threshold,
        "sample_count": n,
        "observed_event_count": event_count,
        "forecast_event_count": forecast_event_count,
        "hits": hits,
        "misses": misses,
        "false_alarms": false_alarms,
        "metrics": metrics,
        "undefined_metric_reasons": undefined_reasons,
        "undefined_reason": reason,
    }


def verification_metrics(observed: np.ndarray, predicted: np.ndarray) -> dict:
    return {
        "continuous": continuous_metrics(observed, predicted),
        "thresholds": {
            name: event_metrics(observed, predicted, threshold)
            for name, threshold in HEAVY_THRESHOLDS_MM.items()
        },
    }


def safe_ridge_fit(x: np.ndarray, y: np.ndarray, alpha: float) -> dict:
    from sklearn.linear_model import Ridge

    mean = np.mean(x, axis=0, dtype=np.float64)
    scale = np.std(x, axis=0, dtype=np.float64)
    scale[scale == 0] = 1.0
    target_mean = float(np.mean(y, dtype=np.float64))
    model = Ridge(alpha=float(alpha), fit_intercept=True, solver="lsqr", tol=1e-5)
    model.fit(((x - mean) / scale).astype(np.float32), (y - target_mean).astype(np.float32))
    coefficients = np.asarray(model.coef_, dtype=np.float64)
    intercept = float(model.intercept_) + target_mean
    return {"format": "safe-json-standardized-ridge", "alpha": float(alpha), "feature_names": list(FEATURE_NAMES), "feature_mean": mean.tolist(), "feature_scale": scale.tolist(), "coefficients": coefficients.tolist(), "intercept": intercept, "training_target_mean": target_mean}


def safe_ridge_predict(artifact: dict, x: np.ndarray) -> np.ndarray:
    if artifact.get("format") != "safe-json-standardized-ridge" or artifact.get("feature_names") != list(FEATURE_NAMES):
        raise ValueError("invalid safe Ridge artifact")
    normalized = (x - np.asarray(artifact["feature_mean"])) / np.asarray(artifact["feature_scale"])
    return np.maximum(0.0, normalized @ np.asarray(artifact["coefficients"]) + float(artifact["intercept"]))


def xgb_target(y: np.ndarray, strategy: str) -> tuple[np.ndarray, str, dict]:
    if strategy == "direct":
        return y, "reg:squarederror", {}
    if strategy == "log1p":
        return np.log1p(y), "reg:squarederror", {"inverse": "expm1"}
    if strategy == "tweedie":
        return y, "reg:tweedie", {"tweedie_variance_power": 1.5}
    raise ValueError(f"unknown target strategy: {strategy}")


def xgb_predict(model, x: np.ndarray, strategy: str) -> np.ndarray:
    prediction = model.predict(x)
    if strategy == "log1p":
        prediction = np.expm1(prediction)
    return np.maximum(0.0, prediction)


def xgb_params(device: str, *, nthread: int = 12, n_estimators: int = 350, **overrides) -> dict:
    params = {
        "n_estimators": n_estimators,
        "max_depth": 6,
        "learning_rate": 0.05,
        "subsample": 0.9,
        "colsample_bytree": 0.9,
        "reg_lambda": 2.0,
        "min_child_weight": 5,
        "max_bin": 256,
        "tree_method": "hist",
        "device": device,
        "n_jobs": nthread,
        "random_state": 26080,
        "verbosity": 0,
    }
    params.update(overrides)
    return params


def train_xgb(x_train: np.ndarray, y_train: np.ndarray, x_valid: np.ndarray, y_valid: np.ndarray, strategy: str, device: str, n_estimators: int = 350):
    from xgboost import XGBRegressor

    target, objective, extra = xgb_target(y_train, strategy)
    target_valid, _, _ = xgb_target(y_valid, strategy)
    model = XGBRegressor(objective=objective, early_stopping_rounds=35, **xgb_params(device, n_estimators=n_estimators, **extra))
    model.fit(x_train, target, eval_set=[(x_valid, target_valid)], verbose=False)
    return model


def benchmark_xgb(
    x_train: np.ndarray, y_train: np.ndarray, x_valid: np.ndarray, y_valid: np.ndarray,
) -> dict:
    """Short fixed-workload CPU/CUDA benchmark with equivalence and stability gates."""
    import time
    from xgboost import XGBRegressor

    n_train = min(50000, len(y_train))
    n_valid = min(20000, len(y_valid))
    train_ix = np.linspace(0, len(y_train) - 1, n_train, dtype=np.int64)
    valid_ix = np.linspace(0, len(y_valid) - 1, n_valid, dtype=np.int64)
    records = {}
    models = {}
    for device in ("cpu", "cuda"):
        try:
            model = XGBRegressor(objective="reg:squarederror", **xgb_params(device, n_estimators=60, nthread=12, max_depth=6))
            start = time.perf_counter()
            model.fit(x_train[train_ix], y_train[train_ix], verbose=False)
            prediction = model.predict(x_valid[valid_ix])
            elapsed = time.perf_counter() - start
            if not np.isfinite(prediction).all():
                raise ValueError("non-finite predictions")
            records[device] = {"seconds": float(elapsed), "train_rows": n_train, "validation_rows": n_valid, "rounds": 60, "status": "ok"}
            models[device] = prediction
        except Exception as error:
            records[device] = {"status": "error", "error": f"{type(error).__name__}: {error}"}
    if "cpu" in models and "cuda" in models:
        cpu = models["cpu"]
        gpu = models["cuda"]
        correlation = float(np.corrcoef(cpu, gpu)[0, 1])
        cpu_metrics = verification_metrics(y_valid[valid_ix], cpu)
        gpu_metrics = verification_metrics(y_valid[valid_ix], gpu)
        rmse_drift = abs(cpu_metrics["continuous"]["rmse_mm"] - gpu_metrics["continuous"]["rmse_mm"]) / max(cpu_metrics["continuous"]["rmse_mm"], 1e-12)
        csi_drift = max(abs(cpu_metrics["thresholds"][k]["metrics"]["CSI"] - gpu_metrics["thresholds"][k]["metrics"]["CSI"]) for k in HEAVY_THRESHOLDS_MM)
        repeat = None
        try:
            repeated = XGBRegressor(objective="reg:squarederror", **xgb_params("cuda", n_estimators=60, nthread=12, max_depth=6))
            repeat_start = time.perf_counter()
            repeated.fit(x_train[train_ix], y_train[train_ix], verbose=False)
            repeated_prediction = repeated.predict(x_valid[valid_ix])
            repeat = {
                "status": "ok",
                "seconds": float(time.perf_counter() - repeat_start),
                "prediction_correlation": float(np.corrcoef(gpu, repeated_prediction)[0, 1]),
                "maximum_absolute_prediction_delta": float(np.max(np.abs(gpu - repeated_prediction))),
                "stable": bool(np.allclose(gpu, repeated_prediction, rtol=1e-6, atol=1e-6)),
            }
        except Exception as error:
            repeat = {"status": "error", "stable": False, "error": f"{type(error).__name__}: {error}"}
        equivalent = correlation >= 0.999 and rmse_drift <= 0.001 and csi_drift <= 0.005 and bool(repeat["stable"])
        records["equivalence"] = {"prediction_correlation": correlation, "relative_rmse_drift": rmse_drift, "maximum_absolute_csi_drift": csi_drift, "cuda_repeatability": repeat, "passed": bool(equivalent)}
        records["selected_device"] = "cuda" if equivalent and records["cuda"]["seconds"] < records["cpu"]["seconds"] else "cpu"
    else:
        records["equivalence"] = {"passed": False, "reason": "both CPU and CUDA paths did not complete"}
        records["selected_device"] = "cpu"
    return records


def deterministic_case_bootstrap(
    observed: np.ndarray, predicted: np.ndarray, case_codes: np.ndarray, *, repeats: int = 500, seed: int = 26080,
) -> dict:
    """Case-level bootstrap RMSE interval; all cells from a case move together."""
    codes = np.unique(case_codes)
    if len(codes) < 2:
        return {"status": "insufficient_cases", "case_count": int(len(codes)), "repeats": 0}
    by_case = {int(code): np.flatnonzero(case_codes == code) for code in codes}
    rng = np.random.default_rng(seed)
    samples = np.empty(repeats, dtype=np.float64)
    for repeat in range(repeats):
        chosen = rng.choice(codes, size=len(codes), replace=True)
        squared = np.concatenate([observed[by_case[int(code)]] - predicted[by_case[int(code)]] for code in chosen]) ** 2
        samples[repeat] = np.sqrt(np.mean(squared))
    return {"status": "ok", "case_count": int(len(codes)), "repeats": repeats, "seed": seed, "rmse_95_percentile_interval_mm": [float(np.quantile(samples, 0.025)), float(np.quantile(samples, 0.975))]}
