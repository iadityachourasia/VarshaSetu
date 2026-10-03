"""Train and select the reforecast heavy-rain models under the frozen protocol reforecast_study_protocol_v1.json (docs/142, R05). Development years only.

    python scripts/train_reforecast_models.py dev     # trains the 24-configuration grid for arms B0 and B1 on 2000-2011, evaluates on 2012-2013, selects, fits the regime arms (resumable checkpoint)
    python scripts/train_reforecast_models.py final   # refits the SELECTED configurations on 2000-2013, saves the models locally and writes the tracked selection freeze

No sealed-year (2014-2016) observation or label is read: the paired files of those years do not exist until the unseal record does. After ``final`` the script STOPS.
"""

from __future__ import annotations

import hashlib
import json
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import xgboost  # noqa: E402
from sklearn.linear_model import LogisticRegression  # noqa: E402
from xgboost import XGBRegressor  # noqa: E402

from backend.app.ml import reforecast_study as rs  # noqa: E402
from backend.app.ml.geoaware import static_columns  # noqa: E402

PHASE15 = ROOT / "backend/app/evidence_data/phase15"
PROTOCOL = PHASE15 / "reforecast_study_protocol_v1.json"
FREEZE = PHASE15 / "reforecast_selection_freeze.json"
PROC = ROOT / "data/processed/reforecast_control_v1"
WORK = ROOT / "experiments/reforecast_study_v1"
CHECKPOINT = WORK / "grid_results.jsonl"
DEV_FILE = WORK / "dev_state.json"
MODELS = WORK / "models"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def load_protocol() -> dict:
    if PROTOCOL.with_suffix(".sha256").read_text(encoding="ascii").split()[0] != sha256_file(PROTOCOL):
        raise SystemExit("protocol differs from its sidecar")
    return json.loads(PROTOCOL.read_text(encoding="utf-8"))


def load_years(years: tuple[int, ...]) -> dict:
    if set(years) & set(rs.SEALED_YEARS):
        raise SystemExit("a sealed year can never be loaded by the training script")
    geography = json.loads((ROOT / "backend/app/evidence_data/phase7/static_geography_v1.json").read_text(encoding="utf-8"))
    static_fields = {n: np.array([[np.nan if v is None else v for v in row] for row in geography["fields"][n]], dtype=np.float64).ravel() for n in rs.STATIC_FEATURES}
    xs, ys, pixels, year_of_row, case_of_row, regime, case_year, rows_per_case = [], [], [], [], [], [], [], []
    case_offset = 0
    for year in years:
        folder = PROC / str(year)
        pairs = json.loads((folder / "pairs.json").read_text(encoding="utf-8"))
        x, y, pixel = np.load(folder / "X.npy", allow_pickle=False), np.load(folder / "y_mm.npy", allow_pickle=False), np.load(folder / "pixel_index.npy", allow_pickle=False)
        regime_all = np.load(folder / "regime_X.npy", allow_pickle=False)
        rows = np.load(folder / "regime_rows.npy", allow_pickle=False)
        if x.shape != (len(y), 22) or not np.isfinite(y).all() or (y < 0).any() or len(rows) != len(pairs["cases"]):
            raise SystemExit(f"{year} paired arrays are inconsistent")
        xs.append(x), ys.append(y), pixels.append(pixel.astype(np.int64)), year_of_row.append(np.full(len(y), year))
        counts = np.array([c["row_count"] for c in pairs["cases"]])
        case_of_row.append(np.repeat(np.arange(len(counts)) + case_offset, counts))
        regime.append(regime_all[rows]), case_year.append(np.full(len(counts), year)), rows_per_case.append(counts)
        case_offset += len(counts)
    X, y, pixel = np.concatenate(xs), np.concatenate(ys), np.concatenate(pixels)
    return {"X": X, "y": y, "pixel": pixel, "year": np.concatenate(year_of_row), "case": np.concatenate(case_of_row), "static": static_columns(static_fields, pixel), "regime": np.concatenate(regime),
            "case_year": np.concatenate(case_year), "rows_per_case": np.concatenate(rows_per_case)}


def features(data: dict, arm: str) -> np.ndarray:
    full = np.concatenate([data["X"], data["static"]], axis=1)
    names = list(rs.BASE_FEATURES) + list(rs.STATIC_FEATURES)
    return full[:, [names.index(f) for f in rs.ARMS[arm]]].astype(np.float32)


def make_model(config: dict, spec: dict) -> XGBRegressor:
    fixed = spec["fixed"]
    params = dict(objective=config["objective"], n_estimators=config["n_estimators"], max_depth=config["max_depth"], learning_rate=fixed["learning_rate"], subsample=fixed["subsample"],
                  colsample_bytree=fixed["colsample_bytree"], reg_lambda=fixed["reg_lambda"], min_child_weight=fixed["min_child_weight"], tree_method=spec["tree_method"], device=spec["device"],
                  random_state=spec["seed"], n_jobs=spec["n_jobs"])
    if config["objective"] == "reg:tweedie":
        params["tweedie_variance_power"] = spec["tweedie_variance_power"]
    return XGBRegressor(**params)


def fit(config: dict, spec: dict, X: np.ndarray, y: np.ndarray) -> XGBRegressor:
    model = make_model(config, spec)
    model.fit(X, y, sample_weight=rs.row_weights(y, config["cap"]))
    return model


def predict(model: XGBRegressor, X: np.ndarray) -> np.ndarray:
    return np.maximum(0.0, model.predict(X)).astype(np.float32)


def done_results() -> dict:
    out = {}
    if CHECKPOINT.exists():
        for line in CHECKPOINT.read_text(encoding="utf-8").splitlines():
            if line.strip():
                r = json.loads(line)
                out[(r["arm"], r["grid_index"])] = r
    return out


def regime_arms(train: dict, valid: dict | None, config: dict, spec: dict, B0_train: np.ndarray, global_model: XGBRegressor, save_to: Path | None = None) -> dict:
    """Pseudo-label rule, classifier and three experts fitted on ``train`` with the selected B0 configuration; returns validation predictions if ``valid`` is given."""
    rule = rs.fit_pseudo_labeler(train["regime"])
    labels = rs.pseudo_labels(train["regime"], rule)
    mean, scale = train["regime"].mean(axis=0), train["regime"].std(axis=0)
    scale[scale == 0] = 1.0
    classifier = LogisticRegression(max_iter=2000, random_state=spec["seed"]).fit((train["regime"] - mean) / scale, labels)
    row_label = labels[train["case"] - train["case"].min()]
    experts, fallback = {}, {}
    for r in (0, 1, 2):
        rows = row_label == r
        if int(rows.sum()) < 100_000:
            experts[r], fallback[r] = global_model, True
        else:
            experts[r], fallback[r] = fit(config, spec, B0_train[rows], train["y"][rows]), False
        if save_to is not None and not fallback[r]:
            experts[r].save_model(str(save_to / f"expert_regime_{r}.json"))
    out = {"rule": rule, "classifier": {"mean": mean.tolist(), "scale": scale.tolist(), "coef": classifier.coef_.tolist(), "intercept": classifier.intercept_.tolist(), "classes": classifier.classes_.tolist()},
           "fallback": {str(k): v for k, v in fallback.items()}, "training_label_counts": {str(r): int((labels == r).sum()) for r in (0, 1, 2)}, "_experts": experts, "_clf": (mean, scale, classifier)}
    return out


def case_probabilities(arms: dict, regime: np.ndarray) -> np.ndarray:
    mean, scale, clf = arms["_clf"]
    return clf.predict_proba((regime - mean) / scale)


def dev(protocol: dict) -> None:
    spec = protocol["r05"]["model_spec"]
    WORK.mkdir(parents=True, exist_ok=True)
    train, valid = load_years(rs.TRAIN_YEARS), load_years(rs.VALIDATION_YEARS)
    raw = rs.pooled_metrics(valid["y"], valid["X"][:, 0])
    print(f"train rows {len(train['y'])}, validation rows {len(valid['y'])}, raw validation heavy CSI {raw['heavy']['csi']:.4f}, rmse {raw['rmse_mm']:.3f}", flush=True)
    grid, done = rs.configurations(), done_results()
    import os
    run_arms = [a for a in os.environ.get("REFORECAST_ARMS", ",".join(rs.ARMS)).split(",") if a in rs.ARMS]       # arms may be trained in parallel processes; the checkpoint is append-only
    for arm in run_arms:
        Xtr, Xva = features(train, arm), features(valid, arm)
        for index, config in enumerate(grid):
            if (arm, index) in done_results():
                continue
            t0 = time.time()
            prediction = predict(fit(config, spec, Xtr, train["y"]), Xva)
            record = {"arm": arm, "grid_index": index, "config": config, "validation": rs.pooled_metrics(valid["y"], prediction), "eligible": None, "seconds": round(time.time() - t0, 1)}
            record["eligible"] = rs.eligible(record["validation"], raw)
            with CHECKPOINT.open("a", encoding="utf-8", newline="\n") as stream:
                stream.write(json.dumps(record, sort_keys=True) + "\n")
            done[(arm, index)] = record
            v = record["validation"]
            print(f"{arm} #{index:02d} {config['objective']:16s} cap {config['cap']} d{config['max_depth']} n{config['n_estimators']}: rmse {v['rmse_mm']:.3f} heavy CSI {v['heavy']['csi']:.4f} very-heavy CSI {v['very_heavy']['csi']} "
                  f"eligible {record['eligible']} ({record['seconds']}s)", flush=True)
    done = done_results()
    missing = [(a, i) for a in rs.ARMS for i in range(len(grid)) if (a, i) not in done]
    if missing:
        print(f"{len(missing)} grid results are still missing (another arm is running); rerun `dev` when all arms are done", flush=True)
        return
    selection = {}
    for arm in rs.ARMS:
        chosen = rs.select_configuration([done[(arm, i)] for i in range(len(grid))], raw)
        selection[arm] = None if chosen is None else {"grid_index": chosen["grid_index"], "config": chosen["config"], "validation": chosen["validation"]}
        print(arm, "NO ELIGIBLE CANDIDATE" if chosen is None else f"selected #{chosen['grid_index']} {chosen['config']}", flush=True)
    state = {"raw_validation": raw, "selection": selection, "all_configurations": [{"arm": a, "grid_index": i, **done[(a, i)]["config"], "eligible": done[(a, i)]["eligible"], "validation": done[(a, i)]["validation"]} for a in rs.ARMS for i in range(len(grid))]}
    if selection["B0"] is not None:
        config = selection["B0"]["config"]
        Xtr, Xva = features(train, "B0"), features(valid, "B0")
        global_model = fit(config, spec, Xtr, train["y"])
        arms = regime_arms(train, valid, config, spec, Xtr, global_model)
        probs = case_probabilities(arms, valid["regime"])
        experts = {r: predict(m, Xva) for r, m in arms["_experts"].items()}
        counts = np.bincount(valid["case"] - valid["case"].min(), minlength=len(probs))
        state["regime_arms_validation"] = {"R_hard": rs.pooled_metrics(valid["y"], rs.route_hard(probs, experts, counts)), "R_soft": rs.pooled_metrics(valid["y"], rs.route_soft(probs, experts, counts)),
                                           "fallback": arms["fallback"], "training_label_counts": arms["training_label_counts"], "B0_global": rs.pooled_metrics(valid["y"], predict(global_model, Xva))}
    DEV_FILE.write_text(json.dumps(state, indent=1), encoding="utf-8")
    print("development stage complete; run `final` to refit and freeze", flush=True)


def final(protocol: dict) -> None:
    if FREEZE.exists():
        raise SystemExit("selection freeze already exists: refusing to retrain (write-once). A change needs a new protocol version.")
    spec = protocol["r05"]["model_spec"]
    state = json.loads(DEV_FILE.read_text(encoding="utf-8"))
    MODELS.mkdir(parents=True, exist_ok=True)
    data = load_years(rs.TRAIN_YEARS + rs.VALIDATION_YEARS)
    freeze = {"schema": "reforecast-selection-freeze-v1", "protocol_sha256": sha256_file(PROTOCOL), "libraries": {"xgboost": xgboost.__version__, "numpy": np.__version__},
              "development": {"train_years": list(rs.TRAIN_YEARS), "validation_years": list(rs.VALIDATION_YEARS), "rows_refit": int(len(data["y"])), "raw_validation": state["raw_validation"]},
              "selection": state["selection"], "all_configurations": state["all_configurations"], "regime_arms_validation": state.get("regime_arms_validation"),
              "builder_sha256": {"train_script": sha256_file(Path(__file__)), "pure_functions": sha256_file(ROOT / "backend/app/ml/reforecast_study.py")},
              "models": {}, "sealed_test": {"years": list(rs.SEALED_YEARS), "opened": False, "note": "no sealed-year observation, label or reanalysis value was read"}}
    fitted = {}
    for arm in rs.ARMS:
        block = state["selection"][arm]
        if block is None:
            continue
        X = features(data, arm)
        model = fit(block["config"], spec, X, data["y"])
        path = MODELS / f"{arm}.json"
        model.save_model(str(path))
        fitted[arm] = model
        freeze["models"][arm] = {"file": path.name, "sha256": sha256_file(path), "config": block["config"]}
    if "B0" in fitted:
        B0 = features(data, "B0")
        arms = regime_arms(data, None, state["selection"]["B0"]["config"], spec, B0, fitted["B0"], save_to=MODELS)
        classifier = {"rule": arms["rule"], "classifier": arms["classifier"], "fallback": arms["fallback"], "training_label_counts": arms["training_label_counts"]}
        (MODELS / "regime_arms.json").write_text(json.dumps(classifier, indent=1), encoding="utf-8")
        freeze["models"]["regime_arms"] = {"file": "regime_arms.json", "sha256": sha256_file(MODELS / "regime_arms.json"), "fallback": arms["fallback"],
                                           "experts": {str(r): (sha256_file(MODELS / f"expert_regime_{r}.json") if not arms["fallback"][str(r)] else "FALLBACK_TO_B0") for r in (0, 1, 2)}}
    FREEZE.write_bytes((json.dumps(freeze, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode("utf-8"))
    (PHASE15 / "reforecast_selection_freeze.sha256").write_text(sha256_file(FREEZE) + "  reforecast_selection_freeze.json\n", encoding="ascii")
    print("selection freeze written", sha256_file(FREEZE), flush=True)


if __name__ == "__main__":
    stage = sys.argv[1] if len(sys.argv) > 1 else ""
    proto = load_protocol()
    if stage == "dev":
        dev(proto)
    elif stage == "final":
        final(proto)
    else:
        raise SystemExit("usage: train_reforecast_models.py dev|final")
