"""Frozen-artifact extreme probability, spatial and district verification helpers."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from scipy.ndimage import convolve
from sklearn.metrics import average_precision_score, roc_auc_score

from backend.app.ml.phase2b import event_metrics

THRESHOLDS = {"heavy": 64.5, "very_heavy": 115.6}
SCALES = (1, 3, 5, 9)
REGIMES = ("ACTIVE_MONSOON", "BREAK_WEAK_MONSOON", "LOW_DEPRESSION_INFLUENCED")


def event_target(observed_mm: np.ndarray, threshold_mm: float) -> np.ndarray:
    observed = np.asarray(observed_mm, dtype=np.float64)
    if not np.isfinite(observed).all() or np.any(observed < 0):
        raise ValueError("event target requires finite nonnegative 24-hour observations")
    return (observed >= threshold_mm).astype(np.uint8)


def probability_features(x: np.ndarray, corrected: np.ndarray, regime: np.ndarray) -> np.ndarray:
    if len(x) != len(corrected) or regime.shape != (len(x), 3):
        raise ValueError("probability feature shape mismatch")
    if not np.isfinite(x).all() or not np.isfinite(corrected).all() or not np.isfinite(regime).all():
        raise ValueError("nonfinite probability predictor")
    if np.any(corrected < 0) or np.any(regime < 0) or not np.allclose(regime.sum(axis=1), 1, atol=1e-5):
        raise ValueError("invalid forecast-only probability inputs")
    return np.column_stack((x, corrected, regime)).astype(np.float32)


def safe_logistic_fit(x: np.ndarray, y: np.ndarray) -> dict:
    from sklearn.linear_model import LogisticRegression

    mean = np.mean(x, axis=0, dtype=np.float64)
    scale = np.std(x, axis=0, dtype=np.float64)
    scale[scale == 0] = 1.0
    model = LogisticRegression(class_weight="balanced", max_iter=500, random_state=26080, solver="lbfgs")
    model.fit((x - mean) / scale, y)
    return {"format": "phase2c-safe-logistic-v1", "mean": mean.tolist(), "scale": scale.tolist(),
            "coefficient": model.coef_[0].tolist(), "intercept": float(model.intercept_[0]),
            "class_weight": "balanced", "training_year": 2017}


def safe_logistic_predict(model: dict, x: np.ndarray) -> np.ndarray:
    if model.get("format") != "phase2c-safe-logistic-v1" or model.get("training_year") != 2017:
        raise ValueError("invalid probability logistic artifact")
    z = ((x - np.asarray(model["mean"])) / np.asarray(model["scale"])) @ np.asarray(model["coefficient"])
    z += float(model["intercept"])
    return np.exp(-np.logaddexp(0, -z))


def fit_calibration(probability: np.ndarray, target: np.ndarray, method: str) -> dict:
    from sklearn.isotonic import IsotonicRegression
    from sklearn.linear_model import LogisticRegression

    if method == "identity":
        return {"format": "phase2c-calibration-v1", "method": method, "fit_year": 2018}
    if len(np.unique(target)) != 2:
        raise ValueError("calibration requires positive and negative 2018 examples")
    if method == "isotonic":
        model = IsotonicRegression(y_min=0, y_max=1, out_of_bounds="clip").fit(probability, target)
        return {"format": "phase2c-calibration-v1", "method": method, "fit_year": 2018,
                "x": model.X_thresholds_.tolist(), "y": model.y_thresholds_.tolist()}
    if method == "sigmoid":
        clipped = np.clip(probability, 1e-7, 1 - 1e-7)
        logit = np.log(clipped / (1 - clipped)).reshape(-1, 1)
        model = LogisticRegression(max_iter=500, random_state=26080).fit(logit, target)
        return {"format": "phase2c-calibration-v1", "method": method, "fit_year": 2018,
                "coefficient": float(model.coef_[0, 0]), "intercept": float(model.intercept_[0])}
    raise ValueError(method)


def apply_calibration(artifact: dict, probability: np.ndarray) -> np.ndarray:
    if artifact.get("format") != "phase2c-calibration-v1" or artifact.get("fit_year") != 2018:
        raise ValueError("invalid calibration artifact")
    p = np.asarray(probability, dtype=np.float64)
    method = artifact["method"]
    if method == "identity":
        result = p
    elif method == "isotonic":
        result = np.interp(p, artifact["x"], artifact["y"])
    elif method == "sigmoid":
        clipped = np.clip(p, 1e-7, 1 - 1e-7)
        z = artifact["coefficient"] * np.log(clipped / (1 - clipped)) + artifact["intercept"]
        result = np.exp(-np.logaddexp(0, -z))
    else:
        raise ValueError(method)
    if not np.isfinite(result).all():
        raise ValueError("nonfinite calibrated probabilities")
    return np.clip(result, 0, 1)


def reliability_bins(target: np.ndarray, probability: np.ndarray) -> list[dict]:
    bins = np.minimum((np.asarray(probability) * 10).astype(int), 9)
    return [{"bin_lower": i / 10, "bin_upper": (i + 1) / 10,
             "sample_count": int(np.sum(bins == i)),
             "mean_predicted_probability": float(np.mean(probability[bins == i])) if np.any(bins == i) else None,
             "observed_event_frequency": float(np.mean(target[bins == i])) if np.any(bins == i) else None}
            for i in range(10)]


def probability_metrics(target: np.ndarray, probability: np.ndarray, threshold: float, climatology: float) -> dict:
    y = np.asarray(target, dtype=np.uint8)
    p = np.asarray(probability, dtype=np.float64)
    if y.shape != p.shape or not np.isfinite(p).all() or np.any((p < 0) | (p > 1)):
        raise ValueError("invalid probability metric inputs")
    n, events = len(y), int(np.sum(y))
    brier = float(np.mean((p - y) ** 2)) if n else None
    reference = float(np.mean((climatology - y) ** 2)) if n else None
    clip = np.clip(p, 1e-15, 1 - 1e-15)
    categorical = event_metrics(y, p, threshold)
    categorical["decision_threshold_probability"] = categorical.pop("threshold_mm_24h")
    result = {"sample_count": n, "observed_event_count": events, "brier": brier,
              "brier_reference": reference, "bss": 1 - brier / reference if reference else None,
              "log_loss": float(-np.mean(y * np.log(clip) + (1 - y) * np.log1p(-clip))) if n else None,
              "roc_auc": float(roc_auc_score(y, p)) if 0 < events < n else None,
              "pr_auc": float(average_precision_score(y, p)) if events else None,
              "reliability": reliability_bins(y, p) if n else [],
              "decision_threshold": float(threshold),
              "categorical": categorical, "undefined_reasons": {}}
    if reference == 0:
        result["undefined_reasons"]["bss"] = "zero climatological reference Brier score"
    if not 0 < events < n:
        result["undefined_reasons"]["roc_auc"] = "only one observed class"
    if events == 0:
        result["undefined_reasons"]["pr_auc"] = "no observed events"
    return result


def fss(forecast_mm: np.ndarray, observed_mm: np.ndarray, valid_mask: np.ndarray,
        rain_threshold: float, size: int, min_valid_fraction: float = 0.5) -> dict:
    forecast = np.asarray(forecast_mm, dtype=np.float64)
    observed = np.asarray(observed_mm, dtype=np.float64)
    valid = np.asarray(valid_mask, dtype=bool) & np.isfinite(forecast) & np.isfinite(observed)
    if forecast.ndim != 2 or forecast.shape != observed.shape or valid.shape != observed.shape or size < 1 or size % 2 != 1:
        raise ValueError("FSS requires aligned 2-D grids and odd neighborhood")
    kernel = np.ones((size, size), dtype=np.float64)
    count = convolve(valid.astype(float), kernel, mode="constant", cval=0)
    potential = convolve(np.ones(valid.shape), kernel, mode="constant", cval=0)
    centers = valid & (count >= min_valid_fraction * potential) & (count > 0)
    if not centers.any():
        return {"fss": None, "reason": "no valid neighborhoods", "valid_centers": 0}
    f = convolve(((forecast >= rain_threshold) & valid).astype(float), kernel, mode="constant", cval=0) / np.maximum(count, 1)
    o = convolve(((observed >= rain_threshold) & valid).astype(float), kernel, mode="constant", cval=0) / np.maximum(count, 1)
    denominator = float(np.sum(f[centers] ** 2 + o[centers] ** 2))
    if denominator == 0:
        return {"fss": None, "reason": "no forecast or observed events in eligible neighborhoods", "valid_centers": int(centers.sum())}
    score = 1 - float(np.sum((f[centers] - o[centers]) ** 2)) / denominator
    return {"fss": float(np.clip(score, 0, 1)), "reason": None, "valid_centers": int(centers.sum())}


def fss_many(cases: list[dict], rain_threshold: float, size: int) -> dict:
    # Aggregate the FSS numerator and denominator over cases, not the mean of case scores.
    numer = denom = 0.0
    defined = 0
    for case in cases:
        a = np.asarray(case["forecast"], dtype=float)
        b = np.asarray(case["observed"], dtype=float)
        mask = np.asarray(case["mask"], dtype=bool)
        kernel = np.ones((size, size), dtype=float)
        count = convolve(mask.astype(float), kernel, mode="constant", cval=0)
        potential = convolve(np.ones(mask.shape), kernel, mode="constant", cval=0)
        centers = mask & (count >= 0.5 * potential) & (count > 0)
        if not centers.any():
            continue
        af = convolve(((a >= rain_threshold) & mask).astype(float), kernel, mode="constant", cval=0) / np.maximum(count, 1)
        bf = convolve(((b >= rain_threshold) & mask).astype(float), kernel, mode="constant", cval=0) / np.maximum(count, 1)
        d = float(np.sum(af[centers] ** 2 + bf[centers] ** 2))
        if d:
            numer += float(np.sum((af[centers] - bf[centers]) ** 2))
            denom += d
            defined += 1
    return {"fss": float(np.clip(1 - numer / denom, 0, 1)) if denom else None,
            "case_count": defined, "reason": None if denom else "no defined event neighborhoods"}


def district_weights(geojson_path: Path, latitudes: np.ndarray, longitudes: np.ndarray) -> tuple[list[dict], np.ndarray]:
    from shapely.geometry import box, shape
    from shapely.strtree import STRtree

    source = json.loads(geojson_path.read_text(encoding="utf-8"))
    cells = [box(float(lon) - .125, float(lat) - .125, float(lon) + .125, float(lat) + .125)
             for lat in latitudes for lon in longitudes]
    domain = box(float(longitudes.min()) - .125, float(latitudes.min()) - .125,
                 float(longitudes.max()) + .125, float(latitudes.max()) + .125)
    districts = []
    geometries = []
    for feature in source["features"]:
        polygon = shape(feature["geometry"])
        if not polygon.is_valid:
            polygon = polygon.buffer(0)
        if not polygon.intersects(domain):
            continue
        overlap = polygon.intersection(domain)
        if overlap.is_empty or overlap.area == 0:
            continue
        properties = feature["properties"]
        districts.append({"district_id": properties["shapeID"], "district_name": properties["shapeName"],
                          "geometry": feature["geometry"]})
        geometries.append(overlap)
    tree = STRtree(geometries)
    weights = np.zeros((len(districts), len(cells)), dtype=np.float32)
    for cell_index, cell in enumerate(cells):
        latitude = float(latitudes[cell_index // len(longitudes)])
        for district_index in tree.query(cell):
            area = geometries[int(district_index)].intersection(cell).area
            if area > 0:
                weights[int(district_index), cell_index] = area * np.cos(np.deg2rad(latitude))
    return districts, weights


def aggregate_districts(districts: list[dict], weights: np.ndarray, raw: np.ndarray,
                        corrected: np.ndarray, heavy_p: np.ndarray, very_heavy_p: np.ndarray,
                        mask: np.ndarray) -> list[dict]:
    valid = np.asarray(mask, dtype=bool).ravel()
    arrays = [np.asarray(x, dtype=float).ravel() for x in (raw, corrected, heavy_p, very_heavy_p)]
    if weights.shape != (len(districts), len(valid)) or any(len(x) != len(valid) for x in arrays):
        raise ValueError("district aggregation shape mismatch")
    valid &= np.logical_and.reduce([np.isfinite(x) for x in arrays])
    result = []
    for d, w in zip(districts, weights):
        active = (w > 0) & valid
        total = float(w[active].sum())
        if total == 0:
            continue
        q = w[active] / total
        r, c, hp, vp = (x[active] for x in arrays)
        result.append({"district_id": d["district_id"], "district_name": d["district_name"],
                       "valid_grid_cells": int(active.sum()), "raw_mean_mm": float(q @ r),
                       "corrected_mean_mm": float(q @ c), "corrected_max_mm": float(c.max()),
                       "heavy_probability": float(q @ hp), "very_heavy_probability": float(q @ vp),
                       "heavy_area_fraction": float(q @ (c >= 64.5)),
                       "very_heavy_area_fraction": float(q @ (c >= 115.6))})
    return result
