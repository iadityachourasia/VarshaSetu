"""Train and select the geography-aware correction (M5a) under the frozen protocol geoaware_protocol_v1.json (docs/124).

Reads only the 2023 TRAINING year. No 2024 or 2025 data are opened here. The script:
  1. verifies the protocol, the training inputs and the fold manifest against their pinned hashes;
  2. builds the four feature arms (A0 control, A1 static, A2 forcing, A3 candidate);
  3. runs the frozen 16-configuration grid per arm with the embargoed 2023 date-block folds (resumable checkpoint);
  4. applies the guardrailed selection rule on the pooled out-of-fold predictions;
  5. refits each selected configuration on all 200 training cases, saves the models locally (gitignored) and writes the tracked
     selection freeze. Only after that file exists may scripts/evaluate_geoaware_m5.py touch 2024 or 2025.

    python scripts/train_geoaware_m5.py            # resumes from the checkpoint if one exists
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import xgboost  # noqa: E402
from xgboost import XGBRegressor  # noqa: E402

from backend.app.ml import geoaware as ga  # noqa: E402
from backend.app.ml import zone_verification as zv  # noqa: E402

PHASE7 = ROOT / "backend/app/evidence_data/phase7"
PHASE9 = ROOT / "backend/app/evidence_data/phase9"
PROTOCOL = PHASE9 / "geoaware_protocol_v1.json"
FREEZE = PHASE9 / "geoaware_selection_freeze.json"
WORK = ROOT / "experiments/geoaware_m5_v1"
CHECKPOINT = WORK / "cv_results.jsonl"
MODELS = WORK / "models"
DATA = ROOT / "data/operational_derived/operational_features_2023_2025_v1/2023/train/deterministic"
FOLDS = ROOT / "experiments/recent_historical/operational_model_protocol_v1/crossfit_folds_2023.json"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def load_stage2_module():
    spec = importlib.util.spec_from_file_location("build_phase7_zone_stage2", ROOT / "scripts/build_phase7_zone_stage2.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def verify_inputs(protocol: dict) -> None:
    if protocol["parents"]["static_geography_sha256"] != sha256_file(PHASE7 / "static_geography_v1.json"):
        raise SystemExit("static geography does not match the protocol")
    if protocol["parents"]["crossfit_folds_2023_sha256"] != sha256_file(FOLDS):
        raise SystemExit("fold manifest does not match the protocol")
    for name, expected in protocol["training"]["data_sha256"].items():
        if sha256_file(DATA / name) != expected:
            raise SystemExit(f"training input {name} does not match the protocol")


def build_training(protocol: dict, stage2) -> dict:
    cases = json.loads((DATA / "cases.json").read_text(encoding="utf-8"))
    X = np.load(DATA / "X.npy", allow_pickle=False)
    y = np.load(DATA / "y_mm.npy", allow_pickle=False).astype(np.float64)
    pixel = np.load(DATA / "pixel_index.npy", allow_pickle=False).astype(np.int64)
    if X.shape != (protocol["training"]["rows"], 22) or len(cases) != protocol["training"]["cases"]:
        raise SystemExit("training matrix shape differs from the protocol")
    geography = json.loads((PHASE7 / "static_geography_v1.json").read_text(encoding="utf-8"))
    static_fields = {name: np.array([[np.nan if v is None else v for v in row] for row in geography["fields"][name]], dtype=np.float64).ravel() for name in ga.STATIC_FEATURES}
    geometry = stage2.geometry_of(geography)
    atmosphere = stage2.Atmosphere(geography)
    case_ranges = [(c["row_start"], c["row_count"]) for c in cases]
    forcing_by_case = []
    for case in cases:
        fields = atmosphere.track_b(case["case_id"], 2023)
        if any(np.isnan(f).any() for f in fields.values()):
            raise SystemExit(f"{case['case_id']}: forecast fields unavailable")
        components = zv.forcing_fields(fields["u850"], fields["v850"], fields["pwat"], geometry)
        forcing_by_case.append({"onshore_flux": components["onshore"], "cross_barrier_flux": components["cross_barrier"]})
    static = ga.static_columns(static_fields, pixel)
    forcing = ga.forcing_columns(case_ranges, forcing_by_case, pixel, len(y))
    fold_info = protocol["training"]["folds"]["case_fold"]
    order = [c["case_id"] for c in cases]
    missing = [c for c in order if c not in fold_info]
    if missing:
        raise SystemExit(f"cases without a fold: {missing[:3]}")
    return {"X": X, "y": y, "pixel": pixel, "static": static, "forcing": forcing, "case_ranges": case_ranges,
            "initialization_utc": [fold_info[c]["initialization_utc"] for c in order], "fold_id": [fold_info[c]["fold"] for c in order]}


def make_model(config: dict, model: dict) -> XGBRegressor:
    fixed = model["fixed"]
    params = dict(objective=config["objective"], n_estimators=config["n_estimators"], max_depth=config["max_depth"], learning_rate=fixed["learning_rate"],
                  subsample=fixed["subsample"], colsample_bytree=fixed["colsample_bytree"], reg_lambda=fixed["reg_lambda"], min_child_weight=fixed["min_child_weight"],
                  tree_method=model["tree_method"], device=model["device"], random_state=model["seed"], n_jobs=model["n_jobs"])
    if config["objective"] == "reg:tweedie":
        params["tweedie_variance_power"] = model["grid"]["tweedie_variance_power"]
    return XGBRegressor(**params)


def fit(config: dict, model_spec: dict, features: np.ndarray, y: np.ndarray) -> XGBRegressor:
    weights = ga.event_weights(y, model_spec["event_weight"]["cap"]) if config["weights"] == "capped_event" else None
    model = make_model(config, model_spec)
    model.fit(features, y, sample_weight=weights)
    return model


def load_done() -> dict[tuple[str, int], dict]:
    done = {}
    if CHECKPOINT.exists():
        for line in CHECKPOINT.read_text(encoding="utf-8").splitlines():
            if line.strip():
                record = json.loads(line)
                done[(record["arm"], record["grid_index"])] = record
    return done


def main() -> None:
    protocol = json.loads(PROTOCOL.read_text(encoding="utf-8"))
    if FREEZE.exists():
        raise SystemExit("selection freeze already exists: refusing to retrain (write-once). A change needs protocol v2.")
    verify_inputs(protocol)
    stage2 = load_stage2_module()
    data = build_training(protocol, stage2)
    y, X = data["y"], data["X"]
    model_spec = protocol["model"]
    raw_metrics = ga.pooled_metrics(y, X[:, 0])
    raw_heavy_csi = raw_metrics["heavy"]["csi"]
    print(f"training rows {len(y)}, raw heavy CSI {raw_heavy_csi:.4f}, raw very-heavy frequency bias {raw_metrics['very_heavy']['frequency_bias']:.4f}", flush=True)
    WORK.mkdir(parents=True, exist_ok=True)
    MODELS.mkdir(parents=True, exist_ok=True)
    done = load_done()
    fold_names = sorted(set(data["fold_id"]))
    case_rows = {f: ga.rows_of_cases(data["case_ranges"], np.array([fid == f for fid in data["fold_id"]])) for f in fold_names}
    train_rows = {f: ga.rows_of_cases(data["case_ranges"], ga.training_case_mask(data["initialization_utc"], data["fold_id"], f)) for f in fold_names}
    configs = ga.configurations()
    for arm in ga.ARMS:
        features = ga.assemble(X, data["static"], data["forcing"], arm)
        for index, config in enumerate(configs):
            if (arm, index) in done:
                continue
            started = time.time()
            oof = np.full(len(y), np.nan)
            for f in fold_names:
                model = fit(config, model_spec, features[train_rows[f]], y[train_rows[f]])
                oof[case_rows[f]] = model.predict(features[case_rows[f]])
            if np.isnan(oof).any():
                raise SystemExit("an out-of-fold prediction is missing")
            metrics = ga.pooled_metrics(y, oof)
            record = {"arm": arm, "grid_index": index, "config": config, "metrics": metrics, "guardrails": ga.guardrails(metrics, raw_heavy_csi),
                      "seconds": round(time.time() - started, 1)}
            with CHECKPOINT.open("a", encoding="utf-8", newline="\n") as stream:
                stream.write(json.dumps(record, sort_keys=True) + "\n")
            done[(arm, index)] = record
            print(f"{arm} #{index:02d} {config['objective']:16s} {config['weights']:13s} d{config['max_depth']} n{config['n_estimators']}: rmse {metrics['rmse_mm']:.3f} bias {metrics['bias_mm']:+.2f} "
                  f"heavyCSI {metrics['heavy']['csi']:.4f} vhFB {metrics['very_heavy']['frequency_bias']:.3f} guardrails {''.join(k for k, v in record['guardrails'].items() if v) or '-'} ({record['seconds']}s)", flush=True)

    selection, models = {}, {}
    for arm in ga.ARMS:
        results = [done[(arm, i)] for i in range(len(configs))]
        chosen = ga.select_configuration(results, raw_heavy_csi)
        if chosen is None:
            selection[arm] = {"selected": None, "reason": "no configuration passed G1, G2 and G3 on the pooled 2023 out-of-fold predictions"}
            continue
        features = ga.assemble(X, data["static"], data["forcing"], arm)
        model = fit(chosen["config"], model_spec, features, y)
        path = MODELS / f"{arm}.json"
        model.save_model(str(path))
        weights = ga.event_weights(y, model_spec["event_weight"]["cap"]) if chosen["config"]["weights"] == "capped_event" else None
        selection[arm] = {"selected": {"grid_index": chosen["grid_index"], "config": chosen["config"], "out_of_fold_metrics": chosen["metrics"], "guardrails": chosen["guardrails"],
                                       "model_sha256": sha256_file(path), "features": len(ga.ARMS[arm]),
                                       "event_weight_effective_sample_size": None if weights is None else round(ga.effective_sample_size(weights), 1)}}
    table = [{"arm": r["arm"], "grid_index": r["grid_index"], **r["config"], "rmse_mm": r["metrics"]["rmse_mm"], "bias_mm": r["metrics"]["bias_mm"], "heavy_csi": r["metrics"]["heavy"]["csi"],
              "very_heavy_frequency_bias": r["metrics"]["very_heavy"]["frequency_bias"], "passes_guardrails": all(r["guardrails"].values())} for r in sorted(done.values(), key=lambda r: (r["arm"], r["grid_index"]))]
    freeze = {"schema": "phase9-geoaware-selection-freeze-v1", "protocol_sha256": sha256_file(PROTOCOL),
              "training": {"cases": len(data["case_ranges"]), "rows": int(len(y)), "raw_out_of_fold_reference": {"heavy_csi": raw_heavy_csi, "bias_mm": raw_metrics["bias_mm"], "rmse_mm": raw_metrics["rmse_mm"]},
                           "input_sha256": protocol["training"]["data_sha256"]},
              "libraries": {"xgboost": xgboost.__version__, "numpy": np.__version__}, "selection": selection, "all_configurations": table,
              "note": "Written before any 2024 or 2025 prediction. A change to anything here needs protocol v2."}
    FREEZE.write_bytes((json.dumps(freeze, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode("utf-8"))
    (PHASE9 / "geoaware_selection_freeze.sha256").write_text(sha256_file(FREEZE) + "  geoaware_selection_freeze.json\n", encoding="ascii")
    for arm, block in selection.items():
        chosen = block["selected"]
        print(arm, "NO CANDIDATE" if chosen is None else f"selected #{chosen['grid_index']} {chosen['config']} rmse {chosen['out_of_fold_metrics']['rmse_mm']:.3f}", flush=True)
    print("selection freeze written", sha256_file(FREEZE))


if __name__ == "__main__":
    main()
