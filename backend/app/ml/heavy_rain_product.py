"""Pure helpers for showing the frozen heavy-rain bundle (B1) in the 2019 map and district products (docs/143).

Nothing here fits, selects or tunes anything. The bundle is the frozen B1 regression (its output reduced by the one-parameter mean-error shift, clipped at zero) and the two frozen exceedance classifiers with
their frozen thresholds. The serving side (``backend/app/api/heavy_rain.py``) only needs the xgboost-free functions; ``load_bundle`` imports xgboost lazily and is used by the local builder.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np

try:
    from backend.app.ml import reforecast_study as rs
    from backend.app.ml.district_product import aggregate_operational_districts
    from backend.app.ml.geoaware import static_columns
except ModuleNotFoundError:
    from app.ml import reforecast_study as rs
    from app.ml.district_product import aggregate_operational_districts
    from app.ml.geoaware import static_columns

GRID_CELLS = 49 * 49
THRESHOLDS = rs.EXCEED_THRESHOLDS            # heavy 64.5 and very heavy 115.6 mm per 24 h
KEYS = {"heavy": "B1:heavy", "very_heavy": "B1:very_heavy"}


def bundle_matrix(x_base: np.ndarray, pixel: np.ndarray, static_fields: dict[str, np.ndarray]) -> np.ndarray:
    """The B1 feature matrix: the 22 forecast-side columns followed by the static geography of each row's cell, in the frozen order."""
    full = np.concatenate([np.asarray(x_base), static_columns(static_fields, pixel)], axis=1)
    names = list(rs.BASE_FEATURES) + list(rs.STATIC_FEATURES)
    return full[:, [names.index(f) for f in rs.ARMS["B1"]]].astype(np.float32)


def load_bundle(models_dir: Path, exceedance_freeze: dict) -> dict:
    from xgboost import XGBClassifier, XGBRegressor      # local, builder-side only

    regression = XGBRegressor()
    regression.load_model(str(models_dir / "B1.json"))
    classifiers = {}
    for name, key in KEYS.items():
        classifier = XGBClassifier()
        classifier.load_model(str(models_dir / exceedance_freeze["models"][key]["file"]))
        classifiers[name] = (classifier, float(exceedance_freeze["selection"][key]["tau"]))
    return {"regression": regression, "classifiers": classifiers}


def predict_bundle(bundle: dict, b1_matrix: np.ndarray, delta_mm: float) -> dict[str, np.ndarray]:
    """Shifted regression (mm per 24 h) and the two classifier scores, row by row."""
    raw = np.maximum(0.0, bundle["regression"].predict(b1_matrix)).astype(np.float32)
    return {"rainfall": np.maximum(0.0, raw - np.float32(delta_mm)).astype(np.float32),
            "heavy": bundle["classifiers"]["heavy"][0].predict_proba(b1_matrix)[:, 1].astype(np.float64),
            "very_heavy": bundle["classifiers"]["very_heavy"][0].predict_proba(b1_matrix)[:, 1].astype(np.float64)}


def decision(score: np.ndarray, tau: float) -> np.ndarray:
    """The frozen yes/no forecast: score at or above the frozen threshold. Undefined scores stay undefined (NaN), never a 'no'."""
    score = np.asarray(score, dtype=np.float64)
    return np.where(np.isfinite(score), (score >= tau).astype(np.float64), np.nan)


def categorical(score: np.ndarray, observed: np.ndarray, tau: float, threshold_mm: float) -> dict:
    """Hits, misses, false alarms and the derived scores of ``score >= tau`` against ``observed >= threshold`` (float32 comparison, as everywhere else)."""
    m = rs.exceedance_metrics(score, observed, tau, threshold_mm)
    hits, misses, false_alarms = m["hits"], m["misses"], m["false_alarms"]
    m["pod"] = hits / (hits + misses) if hits + misses else None
    m["far"] = false_alarms / (hits + false_alarms) if hits + false_alarms else None
    return m


def aggregate_b1_districts(districts: list[dict], weights: np.ndarray, *, raw: np.ndarray, observed: np.ndarray, b1_rainfall: np.ndarray, heavy_score: np.ndarray, very_heavy_score: np.ndarray,
                           taus: dict[str, float]) -> list[dict]:
    """The frozen district aggregation (area-weighted over the cells where every field is defined), applied to the B1 rainfall and the classifier scores.

    ``heavy_probability`` and ``very_heavy_probability`` carry the area-weighted classifier SCORE (not a calibrated probability). ``heavy_flag_area_fraction`` and ``very_heavy_flag_area_fraction`` are the area
    shares of the cells whose score reaches the frozen threshold: the classifier's yes/no forecast, aggregated the same way.
    """
    flat = [np.asarray(x, dtype=float).ravel() for x in (raw, observed, b1_rainfall, heavy_score, very_heavy_score)]
    raw_f, obs_f, b1_f, hs_f, vs_f = flat
    rows = aggregate_operational_districts(districts, weights, raw=raw_f, corrected=b1_f, observed=obs_f, heavy_p=hs_f, very_heavy_p=vs_f)
    valid = np.logical_and.reduce([np.isfinite(x) for x in flat])
    by_id = {d["district_id"]: w for d, w in zip(districts, weights)}
    for row in rows:
        w = by_id[row["district_id"]]
        active = (w > 0) & valid
        q = w[active] / float(w[active].sum())
        # the stored weights are 32-bit, so a share can come out one part in ten million above one; a share is a share, so it is capped
        row["heavy_flag_area_fraction"] = min(1.0, float(q @ (hs_f[active] >= taus["heavy"])))
        row["very_heavy_flag_area_fraction"] = min(1.0, float(q @ (vs_f[active] >= taus["very_heavy"])))
    return rows
