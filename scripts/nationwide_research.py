"""Write-once, local Track B nationwide development study; never opens 2025/2026 truth.

Commands: prepare, features, fit, score, check. Every step is separate so the
2024 forecast seal exists before score may read 2024 IMD values. Outputs in
data/processed are local research artifacts, not a live/public product.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sys
from datetime import date, timedelta
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.app.data_sources.imd_rainfall import load_imd_day  # noqa: E402
from backend.app.data_sources.noaa_gefs_monthly import ATMOSPHERIC_SPECS, crop_grid, decode_atmospheric_message  # noqa: E402
from backend.app.live.pipeline import ATMOSPHERE, _grib_extra, validate_message  # noqa: E402
from backend.app.live.stored import StoredSource  # noqa: E402
from backend.app.ml.forecast_regimes import ATMOSPHERIC_VARIABLES, extract_regime_features  # noqa: E402
from backend.app.ml.nationwide_research import (  # noqa: E402
    CONTEXT_LATITUDE, CONTEXT_LONGITUDE, GRID_SHAPE, LATITUDE, LEADS, LONGITUDE,
    REGIONS, coherent_probabilities, comparable_mask, date_block_folds, partition,
)
from backend.app.ml.phase2b import FEATURE_NAMES, bilinear_to_target, continuous_metrics, event_metrics, safe_ridge_fit, safe_ridge_predict  # noqa: E402
from backend.app.ml.phase2c import fss_many, probability_metrics  # noqa: E402
from experiments.recent_historical.phase4i_operational_model_development_v1.regime import (  # noqa: E402
    fit_classifier, fit_labeler, label, predict_proba,
)

BASE = ROOT / "data/manifests/research_pilot"
OUT = ROOT / "data/processed/nationwide_research_v1"
PHASE14 = ROOT / "backend/app/evidence_data/phase14"
LEDGER = PHASE14 / "all_india_raw_ledger_v1.json"
RAW_PROTOCOL = PHASE14 / "all_india_raw_protocol_v1.json"
GEOMETRY = ROOT / "data/static/phase2c/geoBoundaries-IND-ADM2_simplified.geojson"
SOURCE = ROOT / "experiments/recent_historical/phase4f_payload_acquisition_v1"
IMD = ROOT / "experiments/recent_historical/imd"
PROTOCOL = BASE / "nationwide_research_protocol_v1.json"
STATIC = BASE / "nationwide_research_static_v1.json"
FEATURES = BASE / "nationwide_research_features_v1.json"
SEAL = BASE / "nationwide_research_fit_seal_v1.json"
SCORE = BASE / "nationwide_research_score_v1.json"
IMD_SHA = {
    "2023": "1fa0cbcb56769fd3cd2702e36dc3ee1b81b74755b77c7f058c70dfc3afb82831",
    "2024": "1ef02aeba5694dbb57a6cca23a3c2cc11740affb185137c1eacbeab59893228a",
}
MODEL_SPEC = {"n_estimators": 200, "max_depth": 4, "learning_rate": 0.05,
              "subsample": 0.9, "colsample_bytree": 0.9, "reg_lambda": 2.0,
              "min_child_weight": 5, "max_bin": 256, "tree_method": "hist",
              "device": "cpu", "random_state": 26080, "n_jobs": 8}


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def write_json(path: Path, data: dict) -> str:
    if path.exists() or path.with_suffix(".sha256").exists():
        raise FileExistsError(f"write-once evidence exists: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = (json.dumps(data, sort_keys=True, indent=2, allow_nan=False) + "\n").encode("utf-8")
    temporary = path.with_name(path.name + ".partial")
    temporary.write_bytes(payload)
    os.replace(temporary, path)
    digest = sha(path)
    path.with_suffix(".sha256").write_text(f"{digest}  {path.name}\n", encoding="ascii")
    return digest


def receipt(path: Path) -> str:
    digest = sha(path)
    if path.with_suffix(".sha256").read_text(encoding="ascii").split() != [digest, path.name]:
        raise ValueError(f"evidence receipt mismatch: {path}")
    return digest


def _static_mask() -> np.ndarray:
    from shapely import area, box, intersection, union_all
    from shapely.geometry import shape

    if sha(GEOMETRY) != "d68db39cd3e2d0892af268e2b0454166368ce3b5b8a78fcda63069ec92a641db":
        raise ValueError("research geometry source changed")
    source = json.loads(GEOMETRY.read_text(encoding="utf-8"))
    shapes = []
    for feature in source["features"]:
        polygon = shape(feature["geometry"])
        shapes.append(polygon if polygon.is_valid else polygon.buffer(0))
    country = union_all(shapes)
    lon, lat = np.meshgrid(LONGITUDE, LATITUDE)
    cells = box(lon - 0.125, lat - 0.125, lon + 0.125, lat + 0.125)
    return np.asarray(area(intersection(country, cells)) > 0, dtype=bool)


def _case_rows(year: int) -> list[dict]:
    ledger = json.loads(LEDGER.read_text(encoding="utf-8"))
    rows = sorted((r for r in ledger["populations"][str(year)] if r["status"] == "INCLUDED"), key=lambda r: r["case_id"])
    if not rows or len({r["case_id"] for r in rows}) != len(rows):
        raise ValueError("national Raw case population is empty or duplicated")
    return rows


def prepare() -> dict:
    """No GRIB or observation value is opened here."""
    if any(p.exists() for p in (PROTOCOL, STATIC, FEATURES, SEAL, SCORE)):
        raise FileExistsError("nationwide protocol/static evidence is write-once")
    raw = json.loads(RAW_PROTOCOL.read_text(encoding="utf-8"))
    if sha(LEDGER) != raw["definition"]["ledger_file_sha256"] or receipt(RAW_PROTOCOL) != sha(RAW_PROTOCOL):
        raise ValueError("frozen Raw ledger/protocol mismatch")
    mask = _static_mask()
    regions = partition(mask)
    BASE.mkdir(parents=True, exist_ok=True)
    OUT.mkdir(parents=True, exist_ok=True)
    mask_path = OUT / "research_land_mask.npy"
    np.save(mask_path, mask, allow_pickle=False)
    static = {"schema": "nationwide-research-static-v1", "geometry_sha256": sha(GEOMETRY),
              "geometry_status": "2021 geoBoundaries ODbL research-only, not official current districts",
              "mask_sha256": sha(mask_path), "land_cells": int(mask.sum()),
              "regions": {k: int(v.sum()) for k, v in regions.items()},
              "full_land_partition": int(sum(v.sum() for v in regions.values())) == int(mask.sum())}
    static_hash = write_json(STATIC, static)
    sources = {}
    for year in (2023, 2024):
        path = SOURCE / "manifests" / f"{year}_source_manifest.json"
        if path.with_suffix(".sha256").read_text(encoding="ascii").split() != [sha(path)]:
            raise ValueError(f"{year} source manifest receipt mismatch")
        sources[str(year)] = sha(path)
        if sha(IMD / f"RF25_ind{year}_rfp25.nc") != IMD_SHA[str(year)]:
            raise ValueError(f"{year} IMD annual source hash mismatch")
    protocol = {
        "schema": "varshasetu-nationwide-track-b-research-v1",
        "status": "FROZEN_BEFORE_NATIONAL_FEATURE_DECODING_FIT_OR_PAIRING",
        "purpose": "Separate JJAS Day1-3 nationwide development ladder; no independent or operational claim",
        "roles": {"2023": "fit_and_embargoed_date_block_selection", "2024": "consumed_development_score_after_prediction_seal",
                  "2025": "consumed_test_excluded", "2026": "sealed_test_excluded"},
        "grid": {"latitude": [6.5, 38.5, 0.25], "longitude": [66.5, 100.0, 0.25], "shape": list(GRID_SHAPE),
                 "context_latitude": [5.0, 40.0, 0.5], "context_longitude": [60.0, 105.0, 0.5],
                 "mask": "pinned research geometry positive cell-area overlap, not IMD reference validity"},
        "sources": {"track": "B_OPERATIONAL_GEFS_C00", "raw_ledger_sha256": sha(LEDGER),
                    "raw_protocol_sha256": sha(RAW_PROTOCOL), "static_manifest_sha256": static_hash,
                    "source_manifest_sha256": sources, "imd_annual_sha256": IMD_SHA,
                    "forecast_features": list(FEATURE_NAMES), "forecast_hour_by_product": LEADS,
                    "windows_hours": {"day1_24h": [3, 27], "day2_24h": [27, 51], "day3_24h": [51, 75]}},
        "admission": {"raw_status": "INCLUDED", "six_atmospheric_messages": "hash-verified c00 GRIB and complete finite context",
                      "forecast_mask": "finite nonnegative Raw on static land, all six forecast fields finite",
                      "reference": "valid finite nonnegative annual IMD at fit or score only; no zero fill",
                      "same_cases_cells_all_arms": True},
        "selection": {"folds": 3, "embargo_days": 3, "m2_candidates": ["direct", "residual"],
                      "primary": "2023 OOF heavy CSI, require at least Raw heavy CSI",
                      "guardrail": "2023 OOF RMSE <= Raw RMSE + 0.2 mm and abs(bias) <= 5 mm",
                      "tie_break": "lower RMSE then direct; if none passes, retain Raw as research control and fit candidates without promotion"},
        "models": {"M0": "Raw GEFS", "M1": {"estimator": "standardized Ridge", "alpha": 100.0},
                   "M2": {"estimator": "XGBRegressor", "fixed": MODEL_SPEC,
                          "direct": "reg:squarederror observed mm", "residual": "reg:squarederror observed-minus-Raw mm, clip output to zero"},
                   "M3_M4": {"method": "three pseudo-regime residual specialists over selected M2, hard or soft weighting",
                             "expert_fixed": {**MODEL_SPEC, "n_estimators": 100, "max_depth": 3},
                             "minimum_training_cases": 30, "minimum_heavy_event_cells": 30,
                             "shrinkage": "n_cases/(n_cases+100); weak experts contribute zero residual",
                             "regime_labels": "forecast-derived pseudo-labels, not independent expert truth"}},
        "probability": {"inputs": "Raw, out-of-fold M2 prediction, latitude, longitude, lead; 2023 only",
                        "heads": [64.5, 115.6], "estimator": "unweighted standardized LogisticRegression C=0.1",
                        "calibration": "lead-specific isotonic on embargoed date-block out-of-fold head probabilities, minimum 30 positives and negatives, otherwise identity",
                        "coherence": "P(very heavy)=min(P(very heavy),P(heavy))",
                        "warning_threshold": "smallest of 0.01..0.50 step 0.01 with forecast/observed frequency nearest 1 on 2023 OOF; research only"},
        "metrics": ["RMSE", "bias", "CSI", "POD", "FAR", "ETS", "FSS_1_3_5", "Brier", "BSS", "reliability"],
        "uncertainty": {"bootstrap_unit": "initialization_date", "repeats": 1000, "seed": 26080,
                        "caveat": "date resampling does not remove spatial or serial dependence"},
        "release": "2024 development research view only; M2 regional remains live default; no public warning, official district or independent skill claim",
        "code_sha256": {"pure_contract": sha(ROOT / "backend/app/ml/nationwide_research.py")},
    }
    digest = write_json(PROTOCOL, protocol)
    return {"status": protocol["status"], "protocol_sha256": digest, "land_cells": int(mask.sum()),
            "2023_cases": len(_case_rows(2023)), "2024_cases": len(_case_rows(2024))}


def _preflight() -> tuple[dict, np.ndarray]:
    protocol = json.loads(PROTOCOL.read_text(encoding="utf-8"))
    if receipt(PROTOCOL) != sha(PROTOCOL) or protocol["code_sha256"] != {
        "pure_contract": sha(ROOT / "backend/app/ml/nationwide_research.py")
    }:
        raise ValueError("frozen nationwide code/protocol mismatch")
    if protocol["sources"]["raw_ledger_sha256"] != sha(LEDGER) or protocol["sources"]["static_manifest_sha256"] != receipt(STATIC):
        raise ValueError("frozen nationwide source/static mismatch")
    static = json.loads(STATIC.read_text(encoding="utf-8"))
    mask_path = OUT / "research_land_mask.npy"
    if sha(mask_path) != static["mask_sha256"] or sha(GEOMETRY) != static["geometry_sha256"]:
        raise ValueError("research land mask/geometry changed")
    mask = np.load(mask_path, allow_pickle=False)
    partition(mask)
    return protocol, mask


def _feature_case(row: dict, year: int, mask: np.ndarray) -> tuple[np.ndarray, np.ndarray, dict[str, str]]:
    case_id, hour = row["case_id"], LEADS[row["product"]]
    raw_path = ROOT / row["path"]
    if sha(raw_path) != row["sha256"]:
        raise ValueError(f"Raw hash mismatch: {case_id}")
    raw = np.load(raw_path, allow_pickle=False)
    if raw.shape != GRID_SHAPE or not np.isfinite(raw).all() or (raw < 0).any():
        raise ValueError(f"Raw grid invalid: {case_id}")
    source = StoredSource(case_id[:8])
    fields = []
    source_hashes = {}
    for name in ATMOSPHERIC_VARIABLES:
        family = ATMOSPHERE[name][0]
        message = source.get(family, hour, name)
        source_hashes[name] = message.sha256
        grid = decode_atmospheric_message(message.payload, member="c00", description=message.description,
                                          spec=ATMOSPHERIC_SPECS[name], lead_hour=hour)
        validate_message(message, case_id[:8], grid.metadata, _grib_extra(message.payload))
        crop = crop_grid(grid, south=5, north=40, west=60, east=105)
        if (crop.values.shape != (len(CONTEXT_LATITUDE), len(CONTEXT_LONGITUDE))
                or not np.array_equal(crop.latitude, CONTEXT_LATITUDE)
                or not np.array_equal(crop.longitude, CONTEXT_LONGITUDE)
                or not np.isfinite(crop.values).all()):
            raise ValueError(f"national atmospheric context invalid: {case_id}, {name}")
        fields.append(crop.values)
    atmosphere = np.stack(fields)
    regime = extract_regime_features(atmosphere, CONTEXT_LATITUDE, CONTEXT_LONGITUDE)
    aligned = np.stack([bilinear_to_target(f, CONTEXT_LATITUDE, CONTEXT_LONGITUDE, LATITUDE, LONGITUDE) for f in atmosphere])
    valid = mask & np.isfinite(raw) & (raw >= 0) & np.isfinite(aligned).all(axis=0)
    if not valid.any():
        raise ValueError(f"no valid national forecast cells: {case_id}")
    lat, lon = np.meshgrid(LATITUDE, LONGITUDE, indexing="ij")
    x = np.column_stack((raw[valid], aligned[:, valid].T,
                         np.broadcast_to(regime, (int(valid.sum()), len(regime))),
                         lat[valid], lon[valid], np.full(int(valid.sum()), hour))).astype(np.float32)
    if x.shape != (int(valid.sum()), len(FEATURE_NAMES)) or not np.isfinite(x).all() or (x[:, 0] < 0).any():
        raise ValueError(f"national feature matrix invalid: {case_id}")
    return x, regime, source_hashes


def features() -> dict:
    protocol, mask = _preflight()
    if FEATURES.exists():
        raise FileExistsError("national forecast feature manifest is write-once")
    if shutil.disk_usage(ROOT).free < 50 * (1 << 30):
        raise RuntimeError("free disk is below 50 GiB")
    directory = OUT / "features"
    directory.mkdir(parents=True, exist_ok=True)
    checkpoint = directory / "checkpoint.jsonl"
    cases = [json.loads(line) for line in checkpoint.read_text(encoding="utf-8").splitlines()] if checkpoint.exists() else []
    done = {row["case_id"]: row for row in cases}
    if len(done) != len(cases):
        raise ValueError("duplicate forecast-feature checkpoint case")
    for row in cases:
        if sha(ROOT / row["feature_file"]) != row["feature_sha256"]:
            raise ValueError(f"checkpoint feature changed: {row['case_id']}")
    for year in (2023, 2024):
        source_manifest = SOURCE / "manifests" / f"{year}_source_manifest.json"
        if sha(source_manifest) != protocol["sources"]["source_manifest_sha256"][str(year)]:
            raise ValueError("source manifest changed")
        for row in _case_rows(year):
            if row["case_id"] in done:
                continue
            x, regime, source_hashes = _feature_case(row, year, mask)
            path = directory / f"{row['case_id']}.npz"
            if path.exists():
                raise FileExistsError(f"unreceipted feature file exists: {path}")
            np.savez(path, X=x, regime=regime)
            entry = {"case_id": row["case_id"], "year": year, "product": row["product"],
                          "hour": LEADS[row["product"]], "raw_sha256": row["sha256"],
                          "atmospheric_message_sha256": source_hashes,
                          "feature_file": path.relative_to(ROOT).as_posix(), "feature_sha256": sha(path),
                          "forecast_valid_cells": len(x)}
            with checkpoint.open("a", encoding="utf-8", newline="\n") as stream:
                stream.write(json.dumps(entry, sort_keys=True) + "\n")
            cases.append(entry)
        print(f"forecast-only features complete: {year}, {sum(c['year']==year for c in cases)} cases", flush=True)
    cases.sort(key=lambda row: row["case_id"])
    manifest = {"schema": "nationwide-forecast-features-v1", "protocol_sha256": sha(PROTOCOL),
                "builder_sha256": sha(Path(__file__)),
                "status": "FORECAST_ONLY_NO_REFERENCE_VALUES", "cases": cases,
                "observation_values_read": False, "model_fitted": False}
    digest = write_json(FEATURES, manifest)
    return {"status": manifest["status"], "cases": len(cases), "manifest_sha256": digest}


def _feature_manifest() -> tuple[dict, dict, np.ndarray]:
    protocol, mask = _preflight()
    manifest = json.loads(FEATURES.read_text(encoding="utf-8"))
    if receipt(FEATURES) != sha(FEATURES) or manifest["protocol_sha256"] != sha(PROTOCOL) or manifest["observation_values_read"]:
        raise ValueError("forecast-only feature manifest changed")
    if sorted(c["case_id"] for c in manifest["cases"] if c["year"] == 2023) != sorted(r["case_id"] for r in _case_rows(2023)):
        raise ValueError("2023 feature case population changed")
    if sorted(c["case_id"] for c in manifest["cases"] if c["year"] == 2024) != sorted(r["case_id"] for r in _case_rows(2024)):
        raise ValueError("2024 feature case population changed")
    for row in manifest["cases"]:
        if sha(ROOT / row["feature_file"]) != row["feature_sha256"]:
            raise ValueError(f"feature file hash mismatch: {row['case_id']}")
    return protocol, manifest, mask


def _reference(year: int, case_id: str, hour: int):
    valid = date.fromisoformat(f"{case_id[:4]}-{case_id[4:6]}-{case_id[6:8]}") + timedelta(days=hour // 24)
    field = load_imd_day(IMD / f"RF25_ind{year}_rfp25.nc", valid, south=6.5, north=38.5, west=66.5, east=100.0)
    if field.rainfall_mm.shape != GRID_SHAPE or not np.array_equal(field.latitude, LATITUDE) or not np.array_equal(field.longitude, LONGITUDE):
        raise ValueError("IMD reference grid mismatch")
    return field


def _load_x(row: dict) -> tuple[np.ndarray, np.ndarray]:
    with np.load(ROOT / row["feature_file"], allow_pickle=False) as data:
        x, regime = data["X"], data["regime"]
    if x.shape != (row["forecast_valid_cells"], 22) or regime.shape != (12,) or not np.isfinite(x).all():
        raise ValueError(f"feature cache invalid: {row['case_id']}")
    return x, regime


def _xgb(strategy: str, spec: dict):
    from xgboost import XGBRegressor
    return XGBRegressor(objective="reg:squarederror", **spec)


def _predict_xgb(model, x: np.ndarray, strategy: str) -> np.ndarray:
    prediction = np.asarray(model.predict(x), dtype=np.float64)
    if strategy == "residual":
        prediction = x[:, 0] + prediction
    return np.maximum(prediction, 0)


def _fit_xgb(x: np.ndarray, y: np.ndarray, strategy: str, spec: dict):
    return _xgb(strategy, spec).fit(x, y if strategy == "direct" else y - x[:, 0])


def _metric_pair(y: np.ndarray, pred: np.ndarray) -> dict:
    return {"continuous": continuous_metrics(y, pred), "heavy": event_metrics(y, pred, 64.5),
            "very_heavy": event_metrics(y, pred, 115.6)}


def _scale_fit(x: np.ndarray, y: np.ndarray) -> dict:
    from sklearn.linear_model import LogisticRegression
    mean, scale = x.mean(axis=0), x.std(axis=0)
    scale[scale == 0] = 1
    model = LogisticRegression(C=0.1, max_iter=1000, random_state=26080).fit((x - mean) / scale, y)
    return {"mean": mean.tolist(), "scale": scale.tolist(), "coefficient": model.coef_[0].tolist(),
            "intercept": float(model.intercept_[0])}


def _scale_predict(model: dict, x: np.ndarray) -> np.ndarray:
    z = ((x - np.asarray(model["mean"])) / np.asarray(model["scale"])) @ np.asarray(model["coefficient"])
    z += model["intercept"]
    return np.exp(-np.logaddexp(0, -z))


def fit() -> dict:
    protocol, feature_manifest, mask = _feature_manifest()
    if SEAL.exists() or (OUT / "models").exists() or (OUT / "predictions").exists():
        raise FileExistsError("nationwide fit/predictions are write-once")
    for year in (2023, 2024):
        if sha(IMD / f"RF25_ind{year}_rfp25.nc") != protocol["sources"]["imd_annual_sha256"][str(year)]:
            raise ValueError("IMD annual source hash mismatch")
    training = [r for r in feature_manifest["cases"] if r["year"] == 2023]
    future = [r for r in feature_manifest["cases"] if r["year"] == 2024]
    folds = date_block_folds([r["case_id"] for r in training], folds=3, embargo_days=3)
    xs, ys, case_slices, regimes = [], [], {}, []
    position = 0
    for row in training:
        x, r = _load_x(row)
        truth = _reference(2023, row["case_id"], row["hour"])
        raw = np.full(GRID_SHAPE, np.nan)
        raw[mask] = x[:, 0]
        valid = comparable_mask(mask, raw, truth.rainfall_mm, truth.valid_mask)
        selected = truth.valid_mask[mask]
        if int(selected.sum()) != int(valid.sum()):
            raise ValueError("forecast/reference fit mask mismatch")
        x = x[selected]
        y = truth.rainfall_mm[valid].astype(np.float32)
        xs.append(x); ys.append(y); regimes.append(r)
        case_slices[row["case_id"]] = slice(position, position + len(y))
        position += len(y)
    X, y, regime = np.concatenate(xs), np.concatenate(ys), np.stack(regimes)
    if len(y) != len(X) or np.any(y < 0) or not np.isfinite(y).all():
        raise ValueError("training target invalid")
    raw_metric = _metric_pair(y, X[:, 0])
    candidates, oof_by_strategy = {}, {}
    for strategy in protocol["selection"]["m2_candidates"]:
        oof = np.full(len(y), np.nan)
        for fold in folds:
            train_idx = np.concatenate([np.arange(case_slices[c].start, case_slices[c].stop) for c in fold["train"]])
            held_idx = np.concatenate([np.arange(case_slices[c].start, case_slices[c].stop) for c in fold["held"]])
            model = _fit_xgb(X[train_idx], y[train_idx], strategy, MODEL_SPEC)
            oof[held_idx] = _predict_xgb(model, X[held_idx], strategy)
        if not np.isfinite(oof).all():
            raise ValueError("OOF correction missing cells")
        metrics = _metric_pair(y, oof)
        csi = metrics["heavy"]["metrics"]["CSI"]
        passes = (csi is not None and csi >= raw_metric["heavy"]["metrics"]["CSI"]
                  and metrics["continuous"]["rmse_mm"] <= raw_metric["continuous"]["rmse_mm"] + 0.2
                  and abs(metrics["continuous"]["bias_mm"]) <= 5)
        candidates[strategy] = {"metrics": metrics, "passes": bool(passes)}
        oof_by_strategy[strategy] = oof
        print(f"2023 OOF M2 {strategy}: heavy CSI {csi}, gate {passes}", flush=True)
    passed = [s for s in protocol["selection"]["m2_candidates"] if candidates[s]["passes"]]
    selected = sorted(passed, key=lambda s: (-candidates[s]["metrics"]["heavy"]["metrics"]["CSI"],
                                             candidates[s]["metrics"]["continuous"]["rmse_mm"],
                                             0 if s == "direct" else 1))[0] if passed else None
    research_strategy = selected or "residual"
    oof = oof_by_strategy[research_strategy]
    ridge = safe_ridge_fit(X, y, alpha=100.0)
    global_model = _fit_xgb(X, y, research_strategy, MODEL_SPEC)
    rule = fit_labeler(regime)
    regime_labels = label(regime, rule)
    classifier = fit_classifier(regime, regime_labels, 0.1)
    experts, support = {}, {}
    for r in range(3):
        ids = [row["case_id"] for row, cls in zip(training, regime_labels) if cls == r]
        idx = np.concatenate([np.arange(case_slices[c].start, case_slices[c].stop) for c in ids]) if ids else np.array([], dtype=int)
        heavy = int(np.count_nonzero(y[idx] >= 64.5))
        allowed = len({c[:8] for c in ids}) >= 30 and heavy >= 30
        support[str(r)] = {"case_count": len(ids), "initialization_dates": len({c[:8] for c in ids}),
                           "heavy_event_cells": heavy, "trained": allowed}
        if allowed:
            expert_spec = {**MODEL_SPEC, "n_estimators": 100, "max_depth": 3}
            experts[r] = _fit_xgb(X[idx], y[idx] - oof[idx], "direct", expert_spec)
    # Probability heads use cross-fitted base predictions, then an independent
    # date-block cross-fit of the heads to fit lead-specific calibrators.
    qx = np.column_stack((X[:, 0], oof, X[:, -3:])).astype(np.float64)
    probability = {}
    for name, threshold in (("heavy", 64.5), ("very_heavy", 115.6)):
        target = (y >= threshold).astype(int)
        head_oof = np.full(len(y), np.nan)
        for fold in folds:
            tr = np.concatenate([np.arange(case_slices[c].start, case_slices[c].stop) for c in fold["train"]])
            held = np.concatenate([np.arange(case_slices[c].start, case_slices[c].stop) for c in fold["held"]])
            if len(np.unique(target[tr])) != 2:
                raise ValueError(f"probability head fold has one class: {name}")
            head_oof[held] = _scale_predict(_scale_fit(qx[tr], target[tr]), qx[held])
        calibrators = {}
        for hour in (24, 48, 72):
            keep = X[:, -1] == hour
            events = int(target[keep].sum())
            if events >= 30 and len(target[keep]) - events >= 30:
                from sklearn.isotonic import IsotonicRegression
                iso = IsotonicRegression(y_min=0, y_max=1, out_of_bounds="clip").fit(head_oof[keep], target[keep])
                calibrators[str(hour)] = {"method": "isotonic", "x": iso.X_thresholds_.tolist(), "y": iso.y_thresholds_.tolist(), "events": events}
            else:
                calibrators[str(hour)] = {"method": "identity_insufficient_events", "events": events}
        full_head = _scale_fit(qx, target)
        threshold_candidates = np.arange(0.01, 0.501, 0.01)
        cutoff = float(min(threshold_candidates, key=lambda t: (abs(np.count_nonzero(head_oof >= t) / max(1, target.sum()) - 1), t)))
        probability[name] = {"head": full_head, "calibrators": calibrators, "warning_cutoff_2023_oof": cutoff,
                             "oof_event_count": int(target.sum()), "training_climatology": float(target.mean()),
                             "oof_head_brier": float(np.mean((head_oof - target) ** 2))}
    model_dir, prediction_dir = OUT / "models", OUT / "predictions"
    model_dir.mkdir(parents=True)
    prediction_dir.mkdir(parents=True)
    (model_dir / "ridge.json").write_text(json.dumps(ridge, sort_keys=True) + "\n", encoding="utf-8")
    global_model.save_model(model_dir / "global.json")
    (model_dir / "regime.json").write_text(json.dumps({"rule": rule, "classifier": classifier}, sort_keys=True) + "\n", encoding="utf-8")
    (model_dir / "probability.json").write_text(json.dumps(probability, sort_keys=True) + "\n", encoding="utf-8")
    for r, model in experts.items():
        model.save_model(model_dir / f"expert_{r}.json")
    model_hashes = {p.name: sha(p) for p in sorted(model_dir.iterdir())}
    prediction_rows = []
    for row in future:
        x, r = _load_x(row)
        global_pred = _predict_xgb(global_model, x, research_strategy)
        rp = predict_proba(r[None, :], classifier)[0]
        corrections = []
        for k in range(3):
            if k in experts:
                n = support[str(k)]["case_count"]
                shrink = n / (n + 100)
                corrections.append(shrink * experts[k].predict(x))
            else:
                corrections.append(np.zeros(len(x)))
        corrections = np.stack(corrections)
        hard = np.maximum(global_pred + corrections[int(rp.argmax())], 0)
        soft = np.maximum(global_pred + rp @ corrections, 0)
        p_inputs = np.column_stack((x[:, 0], global_pred, x[:, -3:]))
        p = {}
        for name in ("heavy", "very_heavy"):
            head = probability[name]
            values = _scale_predict(head["head"], p_inputs)
            cal = head["calibrators"][str(row["hour"])]
            if cal["method"] == "isotonic":
                values = np.interp(values, cal["x"], cal["y"])
            p[name] = values
        p["heavy"], p["very_heavy"] = coherent_probabilities(p["heavy"], p["very_heavy"])
        fields = {"M0": x[:, 0], "M1": safe_ridge_predict(ridge, x), "M2": global_pred,
                  "M3": hard, "M4": soft, "heavy_p": p["heavy"], "very_heavy_p": p["very_heavy"]}
        if any(not np.isfinite(v).all() or np.any(v < 0) for v in fields.values()):
            raise ValueError(f"invalid forecast-only prediction: {row['case_id']}")
        path = prediction_dir / f"{row['case_id']}.npz"
        np.savez(path, **{k: np.asarray(v, dtype=np.float32) for k, v in fields.items()})
        prediction_rows.append({"case_id": row["case_id"], "year": 2024, "hour": row["hour"],
                                "file": path.relative_to(ROOT).as_posix(), "sha256": sha(path),
                                "cells": len(x), "feature_sha256": row["feature_sha256"]})
    seal = {"schema": "nationwide-research-fit-seal-v1", "status": "2024_PREDICTIONS_SEALED_BEFORE_2024_REFERENCE_READ",
            "fit_builder_sha256": sha(Path(__file__)),
            "protocol_sha256": sha(PROTOCOL), "feature_manifest_sha256": sha(FEATURES),
            "fit_year": 2023, "fit_cases": len(training), "fit_cells": len(y),
            "fit_observed_heavy_cells": int(np.count_nonzero(y >= 64.5)),
            "fit_observed_very_heavy_cells": int(np.count_nonzero(y >= 115.6)),
            "folds": folds, "raw_2023": raw_metric, "m2_candidates": candidates,
            "m2_selected": selected, "m2_research_strategy": research_strategy,
            "regime_support": support, "model_hashes": model_hashes, "predictions": prediction_rows,
            "2024_reference_values_read": False, "2025_2026_values_read": False,
            "independent_skill_claim": False, "promotion_eligible": False}
    digest = write_json(SEAL, seal)
    return {"status": seal["status"], "fit_cases": len(training), "fit_cells": len(y),
            "2024_forecasts": len(prediction_rows), "m2_selected": selected, "seal_sha256": digest}


def score() -> dict:
    protocol, feature_manifest, mask = _feature_manifest()
    if SCORE.exists():
        raise FileExistsError("national development score is write-once")
    seal = json.loads(SEAL.read_text(encoding="utf-8"))
    if receipt(SEAL) != sha(SEAL) or seal["protocol_sha256"] != sha(PROTOCOL) or seal["2024_reference_values_read"]:
        raise ValueError("prediction seal invalid")
    for name, digest in seal["model_hashes"].items():
        if sha(OUT / "models" / name) != digest:
            raise ValueError(f"model changed: {name}")
    for row in seal["predictions"]:
        if sha(ROOT / row["file"]) != row["sha256"]:
            raise ValueError(f"prediction changed: {row['case_id']}")
    if sha(IMD / "RF25_ind2024_rfp25.nc") != protocol["sources"]["imd_annual_sha256"]["2024"]:
        raise ValueError("2024 reference changed")
    by_id = {r["case_id"]: r for r in feature_manifest["cases"] if r["year"] == 2024}
    regions = partition(mask)
    names = ("ALL_INDIA", *REGIONS)
    stores = {(region, lead, model): {"truth": [], "pred": [], "cases": 0, "fss_heavy": [], "fss_very_heavy": []}
              for region in names for lead in (0, 24, 48, 72) for model in ("M0", "M1", "M2", "M3", "M4")}
    probs = {name: {"truth": [], "pred": []} for name in ("heavy", "very_heavy")}
    case_counts = []
    for row in seal["predictions"]:
        base = by_id[row["case_id"]]
        x, _ = _load_x(base)
        truth = _reference(2024, row["case_id"], row["hour"])
        raw = np.full(GRID_SHAPE, np.nan)
        raw[mask] = x[:, 0]
        valid = comparable_mask(mask, raw, truth.rainfall_mm, truth.valid_mask)
        with np.load(ROOT / row["file"], allow_pickle=False) as saved:
            data = {k: saved[k] for k in saved.files}
        if any(len(value) != int(mask.sum()) for value in data.values()):
            raise ValueError("model prediction grid population changed")
        if not np.array_equal(data["M0"], x[:, 0]):
            raise ValueError("Raw case prediction differs from forecast features")
        case_counts.append({"case_id": row["case_id"], "lead_hours": row["hour"],
                            "paired_cells": int(valid.sum()),
                            "heavy_observed": int(np.count_nonzero(truth.rainfall_mm[valid] >= 64.5)),
                            "very_heavy_observed": int(np.count_nonzero(truth.rainfall_mm[valid] >= 115.6))})
        for region_name in names:
            region = mask if region_name == "ALL_INDIA" else regions[region_name]
            selected = valid & region
            if not selected.any():
                continue
            reference = truth.rainfall_mm[selected]
            for model_name in ("M0", "M1", "M2", "M3", "M4"):
                values = np.full(GRID_SHAPE, np.nan)
                values[mask] = data[model_name]
                forecast = values[selected]
                for lead in (0, row["hour"]):
                    store = stores[(region_name, lead, model_name)]
                    store["truth"].append(reference); store["pred"].append(forecast); store["cases"] += 1
                    store["fss_heavy"].append({"forecast": values, "observed": truth.rainfall_mm, "mask": selected})
                    store["fss_very_heavy"].append({"forecast": values, "observed": truth.rainfall_mm, "mask": selected})
        selected_flat = truth.valid_mask[mask]
        for name, threshold in (("heavy", 64.5), ("very_heavy", 115.6)):
            probs[name]["truth"].append((truth.rainfall_mm[valid] >= threshold).astype(np.uint8))
            probs[name]["pred"].append(data[f"{name}_p"][selected_flat])
    results = {}
    for (region, lead, model), store in stores.items():
        if not store["truth"]:
            continue
        y, pred = np.concatenate(store["truth"]), np.concatenate(store["pred"])
        results.setdefault(region, {}).setdefault(str(lead), {})[model] = {
            "cases": store["cases"], "cells": len(y), "metrics": _metric_pair(y, pred),
            "fss": {name: {str(size): fss_many(store[f"fss_{name}"], threshold, size)
                            for size in (1, 3, 5)}
                    for name, threshold in (("heavy", 64.5), ("very_heavy", 115.6))}}
    probability_result = {}
    fitted_probabilities = json.loads((OUT / "models" / "probability.json").read_text(encoding="utf-8"))
    for name in probs:
        y, p = np.concatenate(probs[name]["truth"]), np.concatenate(probs[name]["pred"])
        model = fitted_probabilities[name]
        probability_result[name] = probability_metrics(y, p, model["warning_cutoff_2023_oof"], model["training_climatology"])
    report = {"schema": "nationwide-research-development-score-v1", "score_builder_sha256": sha(Path(__file__)),
              "status": "CONSUMED_2024_DEVELOPMENT_ONLY_NO_INDEPENDENT_SKILL",
              "protocol_sha256": sha(PROTOCOL), "fit_seal_sha256": sha(SEAL),
              "cases": len(case_counts), "case_event_counts": case_counts,
              "same_case_cell_metrics": results, "probability": probability_result,
              "model_default_unchanged": "regional_M2", "independent_skill_claim": False,
              "public_warning_allowed": False, "official_district_claim": False}
    digest = write_json(SCORE, report)
    return {"status": report["status"], "cases": len(case_counts),
            "all_india": results["ALL_INDIA"]["0"], "score_sha256": digest}


def check() -> dict:
    protocol, mask = _preflight()
    result = {"status": "NATIONWIDE_PROTOCOL_VERIFIED", "protocol_sha256": sha(PROTOCOL),
              "land_cells": int(mask.sum()), "partition": {k: int(v.sum()) for k, v in partition(mask).items()}}
    if FEATURES.exists():
        _, manifest, _ = _feature_manifest()
        result["features"] = len(manifest["cases"])
    if SEAL.exists():
        result["fit_seal_sha256"] = receipt(SEAL)
        seal = json.loads(SEAL.read_text(encoding="utf-8"))
        for name, digest in seal["model_hashes"].items():
            if sha(OUT / "models" / name) != digest:
                raise ValueError(f"model hash mismatch: {name}")
        for row in seal["predictions"]:
            if sha(ROOT / row["file"]) != row["sha256"]:
                raise ValueError(f"prediction hash mismatch: {row['case_id']}")
        result["2024_predictions"] = len(seal["predictions"])
    if SCORE.exists():
        result["score_sha256"] = receipt(SCORE)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("prepare", "features", "fit", "score", "check"))
    args = parser.parse_args()
    response = {"prepare": prepare, "features": features, "fit": fit, "score": score, "check": check}[args.command]()
    print(json.dumps(response, sort_keys=True, allow_nan=False))


if __name__ == "__main__":
    main()
