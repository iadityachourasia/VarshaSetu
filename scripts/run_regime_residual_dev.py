"""Run the frozen, development-only Track A regime-residual comparison.

No consumed test year is read. The output is write-once and contains aggregate
metrics and hashes, not IMD fields. This does not authorize model promotion.
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.app.ml import regime_residual as rr  # noqa: E402
from backend.app.ml import reforecast_study as rs  # noqa: E402
from scripts import train_reforecast_models as previous  # noqa: E402

PHASE = ROOT / "backend/app/evidence_data/phase18"
PROTOCOL = PHASE / "regime_residual_dev_protocol_v1.json"
OUTPUT = PHASE / "regime_residual_dev_result_v1.json"
WORK = ROOT / "experiments/regime_residual_dev_v1"
TASK_DATA = ROOT / "data/processed/regime_tasks_v1"
FORECAST_DATA = ROOT / "data/processed/reforecast_control_v1"
BASE_YEARS = tuple(range(2000, 2011))
RESIDUAL_YEARS = (2011,)
VALID_YEARS = (2012, 2013)


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def checked_protocol() -> dict:
    if PROTOCOL.with_suffix(".sha256").read_text(encoding="ascii").split()[0] != sha(PROTOCOL):
        raise ValueError("development protocol hash mismatch")
    protocol = json.loads(PROTOCOL.read_text(encoding="utf-8"))
    roles = protocol["year_roles"]
    if roles["global_base_training"] != list(BASE_YEARS) or roles["regime_detector_training"] != list(BASE_YEARS) \
            or roles["residual_training"] != list(RESIDUAL_YEARS) or roles["development_evaluation"] != list(VALID_YEARS):
        raise ValueError("year roles differ from the frozen development protocol")
    if set(BASE_YEARS + RESIDUAL_YEARS + VALID_YEARS) & set(roles["forbidden_for_fitting_selection_or_evaluation"]):
        raise ValueError("a forbidden year entered the development run")
    return protocol


def task_features(years: tuple[int, ...]) -> tuple[np.ndarray, np.ndarray, list[str]]:
    matrices, labels, paths = [], [], []
    for year in years:
        folder = FORECAST_DATA / str(year)
        paired = json.loads((folder / "pairs.json").read_text(encoding="utf-8"))["cases"]
        meta_path = TASK_DATA / f"features_{year}.json"
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        if [row["case_id"] for row in paired] != [row["case_id"] for row in meta["cases"]]:
            raise ValueError(f"{year}: regime detector cases differ from the paired rainfall cases")
        feature_path, label_path = TASK_DATA / f"features_{year}.npy", TASK_DATA / f"tasks_Y_{year}.npy"
        X, Y = np.load(feature_path, allow_pickle=False), np.load(label_path, allow_pickle=False)
        if len(X) != len(paired) or Y.shape != (len(paired), len(rr.TASKS)):
            raise ValueError(f"{year}: detector row count differs from paired cases")
        matrices.append(X), labels.append(Y)
        paths.extend((meta_path, feature_path, label_path, folder / "pairs.json", folder / "X.npy", folder / "y_mm.npy", folder / "pixel_index.npy"))
    return np.concatenate(matrices), np.concatenate(labels), [path.relative_to(ROOT).as_posix() for path in paths]


def case_blocks(years: tuple[int, ...]) -> list[dict]:
    blocks = []
    offset = 0
    for year in years:
        cases = json.loads((FORECAST_DATA / str(year) / "pairs.json").read_text(encoding="utf-8"))["cases"]
        for case in cases:
            blocks.append({"year": year, "lead": case["product"], "date": case["initialization"],
                           "start": offset + case["row_start"], "count": case["row_count"]})
        offset += sum(case["row_count"] for case in cases)
    return blocks


def categorical(y: np.ndarray, prediction: np.ndarray, threshold: float) -> dict:
    observed = np.asarray(y, dtype=np.float32) >= np.float32(threshold)
    forecast = np.asarray(prediction, dtype=np.float32) >= np.float32(threshold)
    hits = int(np.count_nonzero(observed & forecast))
    misses = int(np.count_nonzero(observed & ~forecast))
    false = int(np.count_nonzero(~observed & forecast))
    total = len(observed)
    random_hits = (hits + misses) * (hits + false) / total if total else 0.0
    return {"hits": hits, "misses": misses, "false_alarms": false, "observed_events": hits + misses,
            "POD": hits / (hits + misses) if hits + misses else None,
            "FAR": false / (hits + false) if hits + false else None,
            "ETS": (hits - random_hits) / (hits + misses + false - random_hits) if hits + misses + false > random_hits else None}


def score(y: np.ndarray, prediction: np.ndarray) -> dict:
    out = rs.pooled_metrics(y, prediction)
    for name, threshold in (("heavy", 64.5), ("very_heavy", 115.6)):
        out[name].update(categorical(y, prediction, threshold))
    return out


def run() -> dict:
    protocol = checked_protocol()
    if OUTPUT.exists():
        raise FileExistsError("development result already exists; never overwrite it")
    selection = json.loads((ROOT / "backend/app/evidence_data/phase15/reforecast_selection_freeze.json").read_text(encoding="utf-8"))
    prior_protocol = previous.load_protocol()
    config = selection["selection"]["B1"]["config"]
    spec = dict(prior_protocol["r05"]["model_spec"])
    spec["n_jobs"] = 8
    task_train_X, task_train_Y, train_paths = task_features(BASE_YEARS)
    task_residual_X, _, residual_paths = task_features(RESIDUAL_YEARS)
    task_valid_X, _, valid_paths = task_features(VALID_YEARS)
    detectors = rr.fit_detectors(task_train_X, task_train_Y)
    residual_scores = rr.score_detectors(detectors, task_residual_X)
    valid_scores = rr.score_detectors(detectors, task_valid_X)
    train = previous.load_years(BASE_YEARS)
    residual = previous.load_years(RESIDUAL_YEARS)
    valid = previous.load_years(VALID_YEARS)
    if len(residual_scores) != len(residual["rows_per_case"]) or len(valid_scores) != len(valid["rows_per_case"]):
        raise ValueError("regime scores do not align with rainfall cases")
    base_model = previous.fit(config, spec, previous.features(train, "B1"), train["y"])
    base_residual = previous.predict(base_model, previous.features(residual, "B1"))
    base_valid = previous.predict(base_model, previous.features(valid, "B1"))
    correction = rr.fit_correction(base_residual, residual["X"], residual["y"], residual_scores, residual["rows_per_case"])
    predictions = rr.predict_correction(correction, base_valid, valid["X"], valid_scores, valid["rows_per_case"])
    predictions = {"Raw": valid["X"][:, 0], "B1_base": base_valid, **predictions}
    blocks = case_blocks(VALID_YEARS)
    results = {name: {"pooled": score(valid["y"], values),
                      "by_year": {str(year): score(valid["y"][valid["year"] == year], values[valid["year"] == year]) for year in VALID_YEARS},
                      "by_lead": {lead: score(valid["y"][np.concatenate([np.arange(b["start"], b["start"] + b["count"]) for b in blocks if b["lead"] == lead])],
                                             values[np.concatenate([np.arange(b["start"], b["start"] + b["count"]) for b in blocks if b["lead"] == lead])])
                                  for lead in ("day1_24h", "day2_24h", "day3_24h")}}
               for name, values in predictions.items()}
    WORK.mkdir(parents=True, exist_ok=True)
    model_path = WORK / "B1_base_2000_2010.json"
    correction_path = WORK / "correction_2011.json"
    detectors_path = WORK / "regime_detectors_2000_2010.json"
    if any(path.exists() for path in (model_path, correction_path, detectors_path)):
        raise FileExistsError("development model artifact already exists; refusing to overwrite")
    base_model.save_model(str(model_path))
    correction_path.write_text(json.dumps(correction, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    detectors_path.write_text(json.dumps(detectors, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    inputs = sorted(set(train_paths + residual_paths + valid_paths))
    report = {"schema": "regime-residual-development-result-v1", "status": "DEVELOPMENT_ONLY_NO_INDEPENDENT_TEST",
              "protocol_sha256": sha(PROTOCOL), "prior_selection_sha256": sha(ROOT / "backend/app/evidence_data/phase15/reforecast_selection_freeze.json"),
              "training_years": list(BASE_YEARS), "residual_training_years": list(RESIDUAL_YEARS), "evaluation_years": list(VALID_YEARS),
              "base_config": config, "detector_calibration_status": detectors["calibration_status"],
              "input_sha256": {name: sha(ROOT / name) for name in inputs},
              "model_sha256": {path.name: sha(path) for path in (model_path, correction_path, detectors_path)},
              "evaluation_cases": len(blocks), "evaluation_cells": len(valid["y"]), "results": results,
              "interpretation": "No promotion or regime-skill claim follows from development years; compare the candidate with global_residual, not Raw alone.",
              "limitations": ["Objective regime labels are not independent expert annotations.",
                              "Detector logistic scores have not been independently calibrated.",
                              "2012-2013 were used for earlier model development and are not an untouched test.",
                              "The GEFSv12 reforecast population is separate from operational GEFS."]}
    text = json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + "\n"
    OUTPUT.write_text(text, encoding="utf-8", newline="\n")
    OUTPUT.with_suffix(".sha256").write_text(sha(OUTPUT) + "  " + OUTPUT.name + "\n", encoding="ascii")
    return report


if __name__ == "__main__":
    result = run()
    for name, block in result["results"].items():
        p = block["pooled"]
        print(name, "RMSE", round(p["rmse_mm"], 3), "heavy CSI", p["heavy"]["csi"], "bias", round(p["bias_mm"], 3), flush=True)
