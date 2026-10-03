"""Train and select the geography-aware follow-up under the frozen protocol geoaware_followup_protocol_v1.json (docs/129).

Development only. Reads the three development years (2021, 2023, 2024) and never opens 2022: no 2022 feature file, target or observation is read here.
  1. verifies the protocol and every development input against the pinned hashes;
  2. builds the four arms (B0 control, B1 candidate, B0Z and B1Z sensitivity arms);
  3. runs the frozen 16-configuration grid per arm with leave-one-year-out cross-validation (resumable checkpoint);
  4. applies the guardrailed selection rule (G1 to G4 in every held-out year, lowest pooled out-of-fold RMSE);
  5. refits each selected configuration on all 562 development cases, saves the models locally (gitignored) and writes the tracked selection freeze.

The script then STOPS. Opening the 2022 observations needs a separate signed unseal record from the project owner.

    python scripts/train_geoaware_followup.py            # resumes from the checkpoint if one exists
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
from xgboost import XGBRegressor  # noqa: E402

from backend.app.ml import geoaware_followup as gf  # noqa: E402

PHASE7 = ROOT / "backend/app/evidence_data/phase7"
PHASE11 = ROOT / "backend/app/evidence_data/phase11"
PROTOCOL = PHASE11 / "geoaware_followup_protocol_v1.json"
FREEZE = PHASE11 / "geoaware_followup_selection_freeze.json"
WORK = ROOT / "experiments/geoaware_followup_v1"
CHECKPOINT = WORK / "cv_results.jsonl"
MODELS = WORK / "models"
V1 = ROOT / "data/operational_derived/operational_features_2023_2025_v1"
V2 = ROOT / "data/operational_derived/v2/features"
DATA = {2021: V2 / "2021/development/deterministic", 2023: V1 / "2023/train/deterministic", 2024: V1 / "2024/validation/deterministic"}
FILES = ("X.npy", "y_mm.npy", "pixel_index.npy", "cases.json")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def verify_inputs(protocol: dict) -> None:
    sidecar = (PROTOCOL.with_suffix(".sha256")).read_text(encoding="ascii").split()[0]
    if sha256_file(PROTOCOL) != sidecar:
        raise SystemExit("protocol hash differs from its sidecar")
    if protocol["parents"]["static_geography_sha256"] != sha256_file(PHASE7 / "static_geography_v1.json"):
        raise SystemExit("static geography does not match the protocol")
    if set(DATA) != set(gf.DEVELOPMENT_YEARS) or 2022 in DATA:
        raise SystemExit("the data map must contain exactly the development years")
    for year, folder in DATA.items():
        for name in FILES:
            if sha256_file(folder / name) != protocol["development_data_sha256"][str(year)][name]:
                raise SystemExit(f"{year} input {name} does not match the protocol")


def load_development() -> dict:
    geography = json.loads((PHASE7 / "static_geography_v1.json").read_text(encoding="utf-8"))
    static_fields = {name: np.array([[np.nan if v is None else v for v in row] for row in geography["fields"][name]], dtype=np.float64).ravel() for name in gf.STATIC_FEATURES}
    zone_flat = np.array([zone or "" for row in geography["fields"]["zone"] for zone in row], dtype=object)
    xs, ys, pixels, years, cases = [], [], [], [], {}
    for year, folder in DATA.items():
        x = np.load(folder / "X.npy", allow_pickle=False)
        y = np.load(folder / "y_mm.npy", allow_pickle=False).astype(np.float64)
        pixel = np.load(folder / "pixel_index.npy", allow_pickle=False).astype(np.int64)
        cases[year] = len(json.loads((folder / "cases.json").read_text(encoding="utf-8")))
        if x.shape != (len(y), 22) or pixel.shape != y.shape or not np.isfinite(y).all() or (y < 0).any():
            raise SystemExit(f"{year} development arrays are inconsistent")
        xs.append(x), ys.append(y), pixels.append(pixel), years.append(np.full(len(y), year))
    X, y, pixel, year_of_row = np.concatenate(xs), np.concatenate(ys), np.concatenate(pixels), np.concatenate(years)
    static = gf.static_columns(static_fields, pixel)
    return {"X": X, "y": y, "pixel": pixel, "year": year_of_row, "static": static, "zone_rows": zone_flat[pixel] == gf.ZONE, "cases": cases}


def make_model(config: dict, spec: dict) -> XGBRegressor:
    fixed = spec["fixed"]
    params = dict(objective=config["objective"], n_estimators=config["n_estimators"], max_depth=config["max_depth"], learning_rate=fixed["learning_rate"],
                  subsample=fixed["subsample"], colsample_bytree=fixed["colsample_bytree"], reg_lambda=fixed["reg_lambda"], min_child_weight=fixed["min_child_weight"],
                  tree_method=spec["tree_method"], device=spec["device"], random_state=spec["seed"], n_jobs=spec["n_jobs"])
    if config["objective"] == "reg:tweedie":
        params["tweedie_variance_power"] = spec["grid"]["tweedie_variance_power"]
    return XGBRegressor(**params)


def fit(config: dict, spec: dict, features: np.ndarray, y: np.ndarray) -> XGBRegressor:
    weights = gf.event_weights(y, spec["event_weight"]["cap"]) if config["weights"] == "capped_event" else None
    model = make_model(config, spec)
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
        raise SystemExit("selection freeze already exists: refusing to retrain (write-once). A change needs a new protocol version.")
    verify_inputs(protocol)
    data = load_development()
    X, y, year_of_row, zone_rows = data["X"], data["y"], data["year"], data["zone_rows"]
    spec = protocol["model"]
    if spec["event_weight"]["cap"] != gf.EVENT_WEIGHT_CAP:
        raise SystemExit("the code's event-weight cap differs from the protocol")
    raw_heavy_csi = {year: gf.pooled_metrics(y[year_of_row == year], X[year_of_row == year, 0])["heavy"]["csi"] for year in gf.DEVELOPMENT_YEARS}
    print(f"development rows {len(y)}, cases {data['cases']}, raw heavy CSI by year { {k: round(v, 4) for k, v in raw_heavy_csi.items()} }", flush=True)
    WORK.mkdir(parents=True, exist_ok=True)
    MODELS.mkdir(parents=True, exist_ok=True)
    done = load_done()
    configs = gf.configurations()
    for arm in gf.ARMS:
        features = gf.assemble(X, data["static"], arm)
        for index, config in enumerate(configs):
            if (arm, index) in done:
                continue
            started = time.time()
            oof = np.full(len(y), np.nan)
            for held in gf.DEVELOPMENT_YEARS:
                train, test = gf.leave_one_year_out_masks(year_of_row, held)
                oof[test] = fit(config, spec, features[train], y[train]).predict(features[test])
            if np.isnan(oof).any():
                raise SystemExit("an out-of-fold prediction is missing")
            by_year = {str(year): gf.year_metrics(y[year_of_row == year], oof[year_of_row == year], zone_rows[year_of_row == year]) for year in gf.DEVELOPMENT_YEARS}
            record = {"arm": arm, "grid_index": index, "config": config, "pooled": gf.pooled_metrics(y, oof), "by_year": by_year,
                      "guardrails_by_year": {str(year): gf.guardrails_for_year(by_year[str(year)], raw_heavy_csi[year]) for year in gf.DEVELOPMENT_YEARS},
                      "seconds": round(time.time() - started, 1)}
            with CHECKPOINT.open("a", encoding="utf-8", newline="\n") as stream:
                stream.write(json.dumps(record, sort_keys=True) + "\n")
            done[(arm, index)] = record
            failed = sorted({g for gs in record["guardrails_by_year"].values() for g, ok in gs.items() if not ok})
            print(f"{arm} #{index:02d} {config['objective']:16s} {config['weights']:13s} d{config['max_depth']} n{config['n_estimators']}: pooled rmse {record['pooled']['rmse_mm']:.3f} "
                  f"fails {','.join(failed) or 'none'} ({record['seconds']}s)", flush=True)

    selection = {}
    for arm in gf.ARMS:
        results = []
        for i in range(len(configs)):
            r = done[(arm, i)]
            results.append({**r, "by_year": {int(k): v for k, v in r["by_year"].items()}})
        chosen = gf.select_configuration(results, raw_heavy_csi)
        if chosen is None:
            selection[arm] = {"selected": None, "reason": "no configuration passed G1 to G4 in every held-out year"}
            continue
        features = gf.assemble(X, data["static"], arm)
        model = fit(chosen["config"], spec, features, y)
        path = MODELS / f"{arm}.json"
        model.save_model(str(path))
        weights = gf.event_weights(y, spec["event_weight"]["cap"]) if chosen["config"]["weights"] == "capped_event" else None
        selection[arm] = {"selected": {"grid_index": chosen["grid_index"], "config": chosen["config"], "pooled_out_of_fold": chosen["pooled"],
                                       "by_year": {str(k): v for k, v in chosen["by_year"].items()}, "model_sha256": sha256_file(path), "features": len(gf.ARMS[arm]),
                                       "event_weight_effective_sample_size": None if weights is None else round(float(weights.sum() ** 2 / (weights ** 2).sum()), 1)}}
    table = [{"arm": a, "grid_index": i, **done[(a, i)]["config"], "pooled_rmse_mm": done[(a, i)]["pooled"]["rmse_mm"],
              "guardrails_by_year": done[(a, i)]["guardrails_by_year"], "passes_in_every_year": all(all(g.values()) for g in done[(a, i)]["guardrails_by_year"].values())}
             for a in gf.ARMS for i in range(len(configs))]
    freeze = {"schema": "geoaware-followup-selection-freeze-v1", "protocol_sha256": sha256_file(PROTOCOL),
              "development": {"years": list(gf.DEVELOPMENT_YEARS), "cases": data["cases"], "rows": int(len(y)), "raw_heavy_csi_by_year": {str(k): v for k, v in raw_heavy_csi.items()},
                              "input_sha256": protocol["development_data_sha256"]},
              "builder_sha256": {"train_script": sha256_file(Path(__file__)), "pure_functions": sha256_file(ROOT / "backend/app/ml/geoaware_followup.py")},
              "libraries": {"xgboost": xgboost.__version__, "numpy": np.__version__}, "selection": selection, "all_configurations": table,
              "sealed_test": {"year": 2022, "opened": False, "note": "no 2022 feature, target or observation was read; unsealing needs a separate signed owner record"},
              "note": "Written before any 2022 value is opened. A change to anything here needs a new protocol version."}
    FREEZE.write_bytes((json.dumps(freeze, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode("utf-8"))
    (PHASE11 / "geoaware_followup_selection_freeze.sha256").write_text(sha256_file(FREEZE) + "  geoaware_followup_selection_freeze.json\n", encoding="ascii")
    for arm, block in selection.items():
        chosen = block["selected"]
        print(arm, "NO CANDIDATE" if chosen is None else f"selected #{chosen['grid_index']} {chosen['config']} pooled rmse {chosen['pooled_out_of_fold']['rmse_mm']:.3f}", flush=True)
    print("selection freeze written", sha256_file(FREEZE))


if __name__ == "__main__":
    main()
