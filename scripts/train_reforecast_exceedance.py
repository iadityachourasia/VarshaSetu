"""Exceedance classifiers of the reforecast study (protocol amendment 2, docs/142). Development years only.

    EXC_JOBS=B0:heavy python scripts/train_reforecast_exceedance.py dev      # one (arm, threshold) job per process; several processes may run in parallel
    python scripts/train_reforecast_exceedance.py final                       # selects, refits on 2000-2013, saves the models and writes the tracked freeze

Each job trains the 8-configuration grid of XGBoost binary classifiers P(rain >= threshold) on 2000-2011, fixes for every configuration the probability threshold that maximises CSI on 2012-2013
(frequency bias within bounds) and records the validation scores. No sealed-year value is read.
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import xgboost  # noqa: E402
from xgboost import XGBClassifier  # noqa: E402

from backend.app.ml import reforecast_study as rs  # noqa: E402
from scripts.train_reforecast_models import features, load_years, sha256_file  # noqa: E402

PHASE15 = ROOT / "backend/app/evidence_data/phase15"
PROTOCOL = PHASE15 / "reforecast_study_protocol_v1.json"
FREEZE = PHASE15 / "reforecast_exceedance_freeze.json"
WORK = ROOT / "experiments/reforecast_study_v1"
CHECKPOINT = WORK / "exceedance_results.jsonl"
MODELS = WORK / "models"


def make(config: dict, spec: dict, y_event: np.ndarray) -> XGBClassifier:
    fixed = spec["fixed"]
    weight = 1.0 if config["pos_weight"] == "none" else float(np.sqrt((1 - y_event.mean()) / max(y_event.mean(), 1e-9)))
    return XGBClassifier(objective="binary:logistic", n_estimators=config["n_estimators"], max_depth=config["max_depth"], learning_rate=fixed["learning_rate"], subsample=fixed["subsample"],
                         colsample_bytree=fixed["colsample_bytree"], reg_lambda=fixed["reg_lambda"], min_child_weight=fixed["min_child_weight"], tree_method=spec["tree_method"], device=spec["device"],
                         random_state=spec["seed"], n_jobs=spec["n_jobs"], scale_pos_weight=weight)


def done() -> dict:
    out = {}
    if CHECKPOINT.exists():
        for line in CHECKPOINT.read_text(encoding="utf-8").splitlines():
            if line.strip():
                r = json.loads(line)
                out[(r["arm"], r["threshold"], r["grid_index"])] = r
    return out


def dev(spec: dict) -> None:
    WORK.mkdir(parents=True, exist_ok=True)
    jobs = [tuple(j.split(":")) for j in os.environ["EXC_JOBS"].split(",")]
    train, valid = load_years(rs.TRAIN_YEARS), load_years(rs.VALIDATION_YEARS)
    grid = rs.exceedance_configurations()
    for arm, name in jobs:
        T = rs.EXCEED_THRESHOLDS[name]
        Xtr, Xva = features(train, arm), features(valid, arm)
        ytr = (train["y"].astype(np.float32) >= np.float32(T)).astype(int)
        for index, config in enumerate(grid):
            if (arm, name, index) in done():
                continue
            t0 = time.time()
            model = make(config, spec, ytr).fit(Xtr, ytr)
            prob = model.predict_proba(Xva)[:, 1]
            best = rs.best_tau(prob, valid["y"], T, rs.FREQUENCY_BIAS_BOUNDS[name])
            record = {"arm": arm, "threshold": name, "grid_index": index, "config": config, "validation": best, "seconds": round(time.time() - t0, 1)}
            with CHECKPOINT.open("a", encoding="utf-8", newline="\n") as stream:
                stream.write(json.dumps(record, sort_keys=True) + "\n")
            print(f"{arm} {name} #{index} d{config['max_depth']} n{config['n_estimators']} {config['pos_weight']}: " + ("no qualifying tau" if best is None else f"CSI {best['csi']:.4f} fb {best['frequency_bias']:.2f} tau {best['tau']:.4f}") + f" ({record['seconds']}s)", flush=True)


def final(spec: dict) -> None:
    if FREEZE.exists():
        raise SystemExit("exceedance freeze already exists: refusing to retrain (write-once)")
    results, grid = done(), rs.exceedance_configurations()
    state = json.loads((WORK / "dev_state.json").read_text(encoding="utf-8"))
    raw = state["raw_validation"]
    data = load_years(rs.TRAIN_YEARS + rs.VALIDATION_YEARS)
    MODELS.mkdir(parents=True, exist_ok=True)
    freeze = {"schema": "reforecast-exceedance-freeze-v1", "protocol_sha256": sha256_file(PROTOCOL), "amendment_2": "reforecast_protocol_v1_amendment_2.json", "libraries": {"xgboost": xgboost.__version__},
              "raw_validation": {n: raw[n]["csi"] for n in ("heavy", "very_heavy")}, "selection": {}, "all_configurations": [], "models": {},
              "builder_sha256": {"script": sha256_file(Path(__file__)), "pure_functions": sha256_file(ROOT / "backend/app/ml/reforecast_study.py")}, "sealed_test": {"opened": False, "note": "no sealed-year value was read"}}
    for arm in rs.ARMS:
        X = features(data, arm)
        for name, T in rs.EXCEED_THRESHOLDS.items():
            rows = [results[(arm, name, i)] for i in range(len(grid))]
            freeze["all_configurations"] += [{"arm": arm, "threshold": name, "grid_index": r["grid_index"], **r["config"], "validation": r["validation"]} for r in rows]
            chosen = rs.select_exceedance(rows, raw[name]["csi"])
            key = f"{arm}:{name}"
            if chosen is None:
                freeze["selection"][key] = None
                continue
            y_event = (data["y"].astype(np.float32) >= np.float32(T)).astype(int)
            model = make(chosen["config"], spec, y_event).fit(X, y_event)
            path = MODELS / f"exceed_{arm}_{name}.json"
            model.save_model(str(path))
            freeze["selection"][key] = {"grid_index": chosen["grid_index"], "config": chosen["config"], "validation": chosen["validation"], "tau": chosen["validation"]["tau"]}
            freeze["models"][key] = {"file": path.name, "sha256": sha256_file(path)}
            print(key, "selected", chosen["grid_index"], chosen["config"], f"validation CSI {chosen['validation']['csi']:.4f} (Raw {raw[name]['csi']:.4f})", flush=True)
    FREEZE.write_bytes((json.dumps(freeze, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode("utf-8"))
    (PHASE15 / "reforecast_exceedance_freeze.sha256").write_text(sha256_file(FREEZE) + "  reforecast_exceedance_freeze.json\n", encoding="ascii")
    print("exceedance freeze written", sha256_file(FREEZE), flush=True)


if __name__ == "__main__":
    spec = json.loads(PROTOCOL.read_text(encoding="utf-8"))["r05"]["model_spec"]
    {"dev": dev, "final": final}[sys.argv[1]](spec)
