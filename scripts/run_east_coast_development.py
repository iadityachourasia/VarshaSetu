"""Write-once east-coast 2023-fit / consumed-2024 development experiment.

The fit command seals every 2024 prediction before the score command may read
2024 IMD values. This script never accesses 2025 or 2026 reference data.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import date, timedelta
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.app.data_sources.imd_rainfall import load_imd_day  # noqa: E402
from backend.app.live.india_stages import (  # noqa: E402
    FIRST_STAGE, GRID_SHAPE, IMD_LAT, IMD_LON, StageLineage, district_rows,
    evidence_gate, forecast_field, pair_reference,
)
from backend.app.ml.phase2b import continuous_metrics, event_metrics  # noqa: E402
from backend.app.ml.phase2c import fss_many  # noqa: E402
from scripts.build_east_coast_static import BASE, OUTPUT as STATIC, check as static_check, sha256  # noqa: E402
from scripts.probe_east_coast_features import (  # noqa: E402
    RAW_LEDGER, RAW_PROTOCOL, case_probe, check as feature_check,
)

PROTOCOL = BASE / "east_coast_development_protocol_v2.json"
OUTPUT = ROOT / "data/processed/east_coast_development_v1"
FIT = BASE / "east_coast_fit_seal_v1.json"
RESULT = BASE / "east_coast_development_result_v1.json"
IMD = ROOT / "experiments/recent_historical/imd"
HOURS = {"day1_24h": 24, "day2_24h": 48, "day3_24h": 72}


def receipt(path: Path) -> str:
    digest = sha256(path)
    if path.with_suffix(".sha256").read_text(encoding="ascii").split() != [digest, path.name]:
        raise ValueError(f"receipt mismatch: {path}")
    return digest


def write_once(path: Path, value: dict) -> None:
    if path.exists() or path.with_suffix(".sha256").exists():
        raise FileExistsError(f"write-once artifact exists: {path}")
    payload = json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n"
    temporary = path.with_name(path.name + ".partial")
    temporary.write_text(payload, encoding="utf-8")
    os.replace(temporary, path)
    path.with_suffix(".sha256").write_text(f"{sha256(path)}  {path.name}\n", encoding="ascii")


def cases(ledger: dict, year: int) -> list[tuple[str, int]]:
    rows = [row for row in ledger["populations"][str(year)] if row["status"] == "INCLUDED"]
    result = sorted((row["case_id"], HOURS[row["product"]]) for row in rows)
    if len(result) != len(set(result)) or not result:
        raise ValueError("empty or duplicate admitted cases")
    return result


def preflight() -> tuple[dict, dict, np.ndarray, dict]:
    protocol_hash = receipt(PROTOCOL)
    protocol = json.loads(PROTOCOL.read_text(encoding="utf-8"))
    if protocol["status"] != "PROTOCOL_FROZEN_BEFORE_STAGE_TRAINING_OR_OBSERVATION_PAIRING":
        raise ValueError("development protocol is not frozen")
    if protocol["static_manifest_sha256"] != receipt(BASE / "east_coast_static_v1.json"):
        raise ValueError("static lineage mismatch")
    if protocol["forecast_feature_probe_sha256"] != receipt(BASE / "east_coast_feature_probe_v1.json"):
        raise ValueError("feature-probe lineage mismatch")
    static_check()
    feature_check()
    raw_protocol = json.loads(RAW_PROTOCOL.read_text(encoding="utf-8"))
    if sha256(RAW_LEDGER) != raw_protocol["definition"]["ledger_file_sha256"]:
        raise ValueError("Raw ledger lineage mismatch")
    ledger = json.loads(RAW_LEDGER.read_text(encoding="utf-8"))
    mask = np.load(STATIC / "land_mask.npy", allow_pickle=False)
    if mask.shape != GRID_SHAPE or mask.dtype != bool:
        raise ValueError("invalid static mask")
    for year in (2023, 2024):
        source = IMD / f"RF25_ind{year}_rfp25.nc"
        if sha256(source) != protocol["reference_sha256"][str(year)]:
            raise ValueError(f"IMD {year} file hash mismatch")
    return protocol, ledger, mask, {"status": "READY_WITHOUT_OBSERVATION_VALUES", "protocol_sha256": protocol_hash,
                                    "2023_cases": len(cases(ledger, 2023)), "2024_cases": len(cases(ledger, 2024))}


def reference(year: int, case_id: str, hour: int):
    valid = date.fromisoformat(f"{case_id[:4]}-{case_id[4:6]}-{case_id[6:8]}") + timedelta(days=hour // 24)
    field = load_imd_day(IMD / f"RF25_ind{year}_rfp25.nc", valid, south=6.5, north=38.5, west=66.5, east=100.0)
    if field.rainfall_mm.shape != GRID_SHAPE or not np.array_equal(field.latitude, IMD_LAT) or not np.array_equal(field.longitude, IMD_LON):
        raise ValueError("IMD grid alignment mismatch")
    return field


def fit() -> dict:
    protocol, ledger, mask, info = preflight()
    if OUTPUT.exists() or FIT.exists() or FIT.with_suffix(".sha256").exists():
        raise FileExistsError("development fit is write-once")
    from xgboost import XGBRegressor

    features, targets, fit_rows = [], [], []
    for case_id, hour in cases(ledger, 2023):
        probe, matrix, valid, _ = case_probe(2023, case_id, hour, mask, ledger, with_matrix=True)
        truth = reference(2023, case_id, hour)
        paired = valid & truth.valid_mask
        if not paired.any():
            raise ValueError(f"2023 fit case has no reference: {case_id}")
        features.append(matrix[truth.valid_mask[valid]])
        targets.append(truth.rainfall_mm[paired].astype(np.float32))
        fit_rows.append({"case_id": case_id, "paired_cells": int(paired.sum()), "feature_matrix_sha256": probe["feature_matrix_value_sha256"]})
    x = np.concatenate(features)
    y = np.concatenate(targets)
    if len(x) != len(y) or not np.isfinite(y).all() or (y < 0).any():
        raise ValueError("invalid fit matrix/target")
    recipe = {k: v for k, v in protocol["model"].items() if k in (
        "objective", "tree_method", "device", "n_estimators", "max_depth", "learning_rate",
        "subsample", "colsample_bytree", "reg_lambda", "min_child_weight", "max_bin", "random_state", "n_jobs")}
    model = XGBRegressor(**recipe)
    model.fit(x, y)
    OUTPUT.mkdir(parents=True)
    model_path = OUTPUT / "stage_global_xgb.json"
    model.save_model(model_path)
    model_hash = sha256(model_path)
    forecast_rows = []
    for case_id, hour in cases(ledger, 2024):
        probe, matrix, valid, raw = case_probe(2024, case_id, hour, mask, ledger, with_matrix=True)
        prediction = np.maximum(np.asarray(model.predict(matrix), dtype=np.float64), 0)
        if not np.isfinite(prediction).all():
            raise ValueError(f"nonfinite model prediction: {case_id}")
        field = np.full(GRID_SHAPE, np.nan)
        field[valid] = prediction
        path = OUTPUT / f"{case_id}.npy"
        np.save(path, field, allow_pickle=False)
        forecast_rows.append({"case_id": case_id, "lead_hours": hour, "file": path.relative_to(ROOT).as_posix(),
                              "sha256": sha256(path), "raw_sha256": probe["raw_sha256"],
                              "feature_matrix_sha256": probe["feature_matrix_value_sha256"],
                              "forecast_valid_cells": int(valid.sum())})
    manifest = {"schema": "varshasetu-east-coast-fit-seal-v1", "status": "2024_PREDICTIONS_SEALED_BEFORE_2024_OBSERVATION_READ",
                "protocol_sha256": info["protocol_sha256"], "model_sha256": model_hash,
                "model_path": model_path.relative_to(ROOT).as_posix(), "model_training_domain": FIRST_STAGE,
                "fit_year": 2023, "fit_cases": fit_rows, "fit_cells": len(y),
                "fit_observed_heavy": int((y >= 64.5).sum()), "fit_observed_very_heavy": int((y >= 115.6).sum()),
                "forecast_year": 2024, "forecasts": forecast_rows, "2024_observation_values_read": False,
                "2025_or_2026_values_read": False, "independent_skill_claim": False}
    write_once(FIT, manifest)
    return {"status": manifest["status"], "fit_cases": len(fit_rows), "fit_cells": len(y),
            "2024_forecasts": len(forecast_rows), "model_sha256": model_hash}


def score() -> dict:
    protocol, ledger, mask, info = preflight()
    if RESULT.exists() or RESULT.with_suffix(".sha256").exists():
        raise FileExistsError("development result is write-once")
    fit_hash = receipt(FIT)
    sealed = json.loads(FIT.read_text(encoding="utf-8"))
    if (sealed["protocol_sha256"] != info["protocol_sha256"] or sealed["2024_observation_values_read"]
            or sealed["model_training_domain"] != FIRST_STAGE or sha256(ROOT / sealed["model_path"]) != sealed["model_sha256"]):
        raise ValueError("fit/prediction seal invalid")
    if [row["case_id"] for row in sealed["forecasts"]] != [case for case, _ in cases(ledger, 2024)]:
        raise ValueError("prediction population differs from protocol")
    # Verify *all* forecast files before the first 2024 observation is opened.
    for row in sealed["forecasts"]:
        if sha256(ROOT / row["file"]) != row["sha256"]:
            raise ValueError(f"sealed forecast hash mismatch: {row['case_id']}")
    districts = json.loads((STATIC / "districts.json").read_text(encoding="utf-8"))
    weights = np.load(STATIC / "district_weights.npy", allow_pickle=False)
    raw_values, corrected_values, truth_values, pairs, tables, case_events = [], [], [], [], {}, []
    fss_cases = {name: {"raw": [], "global": []} for name in ("heavy", "very_heavy")}
    for row in sealed["forecasts"]:
        case_id, hour = row["case_id"], row["lead_hours"]
        probe, _, valid, raw = case_probe(2024, case_id, hour, mask, ledger, with_matrix=True)
        if probe["raw_sha256"] != row["raw_sha256"] or probe["feature_matrix_value_sha256"] != row["feature_matrix_sha256"]:
            raise ValueError("forecast-time feature lineage changed")
        raw_field = np.full(GRID_SHAPE, np.nan)
        raw_field[valid] = raw[valid]
        corrected = np.load(ROOT / row["file"], allow_pickle=False)
        forecast = forecast_field(FIRST_STAGE, mask, raw_field, corrected, valid,
                                  StageLineage(case_id, row["raw_sha256"], sealed["model_sha256"],
                                               FIRST_STAGE, sha256(STATIC / "land_mask.npy")))
        tables[case_id] = district_rows(forecast, districts, weights)
        observed = reference(2024, case_id, hour)
        obs = observed.rainfall_mm.copy()
        obs[~observed.valid_mask] = np.nan
        paired = pair_reference(forecast, obs, observed.valid_mask)
        pairs.append(paired)
        selection = paired["paired_mask"]
        raw_values.append(raw_field[selection])
        corrected_values.append(corrected[selection])
        truth_values.append(obs[selection])
        event_row = {"case_id": case_id, "date": case_id[:8], "lead_hours": hour,
                     "paired_cells": int(selection.sum()), "observed_events": paired["observed_events"]}
        for name, threshold in (("heavy", 64.5), ("very_heavy", 115.6)):
            event_row[name] = {arm: {k: event_metrics(obs[selection], field[selection], threshold)[k]
                                     for k in ("hits", "misses", "false_alarms")}
                               for arm, field in (("raw", raw_field), ("global", corrected))}
            for arm, field in (("raw", raw_field), ("global", corrected)):
                fss_cases[name][arm].append({"forecast": field[:63, 55:87], "observed": obs[:63, 55:87],
                                             "mask": selection[:63, 55:87]})
        case_events.append(event_row)
    actual = np.concatenate(truth_values)
    metric = {arm: {"continuous": continuous_metrics(actual, np.concatenate(values)),
                    "events": {name: event_metrics(actual, np.concatenate(values), threshold)
                               for name, threshold in (("heavy", 64.5), ("very_heavy", 115.6))},
                    "fss": {name: {str(size): fss_many(fss_cases[name][arm], threshold, size)
                                   for size in (1, 3, 5)}
                            for name, threshold in (("heavy", 64.5), ("very_heavy", 115.6))}}
              for arm, values in (("raw", raw_values), ("global", corrected_values))}
    gate = evidence_gate(pairs, tables, independent_year=False, consumed_test=True,
                         geometry_version="geoBoundaries-IND-ADM2-simplified-2021-research",
                         geometry_sha256=sha256(ROOT / "data/static/phase2c/geoBoundaries-IND-ADM2_simplified.geojson"),
                         rights_reviewed=False)
    by_day = {}
    for row in case_events:
        day = by_day.setdefault(row["date"], {arm: np.zeros(3, dtype=np.int64) for arm in ("raw", "global")})
        for arm in day:
            day[arm] += np.array([row["heavy"][arm][key] for key in ("hits", "misses", "false_alarms")])
    rng = np.random.default_rng(protocol["date_bootstrap"]["seed"])
    day_values = list(by_day.values())
    delta = []
    for _ in range(protocol["date_bootstrap"]["repeats"]):
        sampled = rng.integers(0, len(day_values), len(day_values))
        aggregate = {arm: np.sum([day_values[i][arm] for i in sampled], axis=0) for arm in ("raw", "global")}
        csi = {arm: (v[0] / v.sum() if v.sum() else np.nan) for arm, v in aggregate.items()}
        if np.isfinite(csi["raw"]) and np.isfinite(csi["global"]):
            delta.append(float(csi["global"] - csi["raw"]))
    result = {"schema": "varshasetu-east-coast-development-result-v1",
              "status": "CONSUMED_2024_DEVELOPMENT_ONLY_NO_PROMOTION", "protocol_sha256": info["protocol_sha256"],
              "fit_seal_sha256": fit_hash, "model_sha256": sealed["model_sha256"],
              "same_case_population": len(pairs), "same_cell_population": len(actual),
              "metrics": metric, "coverage_gate": gate,
              "heavy_csi_delta_global_minus_raw_date_bootstrap": {
                  "point": (metric["global"]["events"]["heavy"]["metrics"]["CSI"] - metric["raw"]["events"]["heavy"]["metrics"]["CSI"]),
                  "interval_95_percentile": np.percentile(delta, [2.5, 97.5]).tolist() if delta else None,
                  "repeats_defined": len(delta), "initialization_dates": len(by_day),
                  "caveat": "Date blocks do not remove spatial or serial dependence"},
              "district_count": len(districts), "independent_skill_claim": False,
              "official_geometry_claim": False, "public_product_connected": False}
    write_once(RESULT, result)
    return {"status": result["status"], "cases": len(pairs), "cells": len(actual),
            "observed_events": gate["observed_events"], "eligible_for_review": gate["eligible_for_review"],
            "heavy_csi_delta": result["heavy_csi_delta_global_minus_raw_date_bootstrap"]}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    for name in ("preflight", "fit", "score", "check"):
        group.add_argument(f"--{name}", action="store_true")
    args = parser.parse_args()
    if args.preflight:
        output = preflight()[3]
    elif args.fit:
        output = fit()
    elif args.score:
        output = score()
    else:
        output = preflight()[3]
        if FIT.exists():
            output["fit_seal_sha256"] = receipt(FIT)
            sealed = json.loads(FIT.read_text(encoding="utf-8"))
            if sha256(ROOT / sealed["model_path"]) != sealed["model_sha256"] or any(
                sha256(ROOT / row["file"]) != row["sha256"] for row in sealed["forecasts"]
            ):
                raise ValueError("sealed model/forecast hash mismatch")
        if RESULT.exists():
            output["result_sha256"] = receipt(RESULT)
    print(json.dumps(output, sort_keys=True, allow_nan=False))


if __name__ == "__main__":
    main()
