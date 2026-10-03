"""Build the 2019 heavy-rain product layer from the frozen B1 bundle (protocol: backend/app/evidence_data/phase17/heavy_rain_integration_protocol_v1.json, docs/143).

    python scripts/build_heavy_rain_product.py

Applies the frozen B1 regression (with its mean-error shift) and the two frozen exceedance classifiers to the 2019 cases of the existing product, writes one compressed array file and a manifest, and refuses to
run again once they exist. Local only: it needs the gitignored models, the forecast-side cache and the IMD files. Every gate in the protocol is checked BEFORE anything is written; a failed gate writes nothing.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.app.ml import heavy_rain_product as hp  # noqa: E402
from backend.app.ml import reforecast_study as rs  # noqa: E402

spec = importlib.util.spec_from_file_location("reforecast_confirmation", ROOT / "scripts/run_reforecast_confirmation.py")
rc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rc)                       # the helpers of the confirmatory round (same IMD reader, same case rules); its main is guarded

PHASE15, PHASE17 = rc.PHASE15, ROOT / "backend/app/evidence_data/phase17"
PROTOCOL = PHASE17 / "heavy_rain_integration_protocol_v1.json"
ARRAYS = PHASE17 / "heavy_rain_b1_2019_v1.npz"
MANIFEST = PHASE17 / "heavy_rain_b1_manifest.json"
APP = ROOT / "data/manifests/phase2c/cases"
YEAR = 2019
TOL = 1e-9


def sha(path: Path) -> str:
    return rc.sha(path)


def fail(message: str) -> None:
    raise SystemExit(f"GATE FAILED, nothing written: {message}")


def main() -> int:
    if ARRAYS.exists() or MANIFEST.exists():
        raise SystemExit("the outputs already exist; they are write-once")
    if PROTOCOL.with_suffix(".sha256").read_text(encoding="ascii").split()[0] != sha(PROTOCOL):
        fail("the protocol differs from its sidecar")
    protocol = json.loads(PROTOCOL.read_text(encoding="utf-8"))
    record = json.loads(rc.RECORD.read_text(encoding="utf-8"))
    if protocol["bundle"]["confirmation_record_sha256"] != sha(rc.RECORD):
        fail("the confirmation record changed after the protocol was written")
    for name, digest in record["model_files_sha256"].items():
        if sha(rc.MODELS / name) != digest:
            fail(f"model file {name} differs from the confirmation record")                       # gate 1
    exceedance = json.loads((PHASE15 / "reforecast_exceedance_freeze.json").read_text(encoding="utf-8"))
    round_one = json.loads((PHASE15 / "reforecast_r05_test.json").read_text(encoding="utf-8"))
    evidence = json.loads((PHASE15 / "reforecast_r05_confirmation.json").read_text(encoding="utf-8"))
    for key, file_key in (("round_one_evidence_sha256", "reforecast_r05_test.json"), ("confirmation_evidence_sha256", "reforecast_r05_confirmation.json"), ("exceedance_freeze_sha256", "reforecast_exceedance_freeze.json")):
        if protocol["bundle"][key] != sha(PHASE15 / file_key):
            fail(f"{file_key} changed after the protocol was written")
    delta = float(round_one["pooled"]["B1"]["bias_mm"])
    bundle = hp.load_bundle(rc.MODELS, exceedance)
    taus = {name: tau for name, (_, tau) in bundle["classifiers"].items()}
    geography = json.loads((ROOT / "backend/app/evidence_data/phase7/static_geography_v1.json").read_text(encoding="utf-8"))
    static_fields = {n: np.array([[np.nan if v is None else v for v in row] for row in geography["fields"][n]], dtype=np.float64).ravel() for n in rs.STATIC_FEATURES}

    # ---- the confirmatory rows, assembled exactly as the confirmatory round assembled them
    xs, ys, pixels, meta = [], [], [], []
    for year in rc.YEARS:
        cases = json.loads((rc.PROC / str(year) / "cases.json").read_text(encoding="utf-8"))["cases"]
        x_full = np.load(rc.PROC / str(year) / "X_full.npy", mmap_mode="r", allow_pickle=False)
        days, box, fill = rc.imd_year(year)
        for c in cases:
            if c["status"] != "INCLUDED":
                continue
            valid_day = date.fromisoformat(c["initialization"]) + timedelta(days=rc.OFFSET[c["product"]])
            if valid_day not in days:
                continue
            obs = box[days[valid_day]].ravel()
            valid = np.isfinite(obs) & (obs != fill) & (obs >= 0)
            if not valid.any():
                continue
            cells = np.flatnonzero(valid)
            xs.append(np.asarray(x_full[c["row"]])[cells]), ys.append(obs[cells]), pixels.append(cells.astype(np.int64))
            meta.append({"initialization": c["initialization"], "product": c["product"], "year": year, "rows": len(cells)})
    X, y, pixel = np.concatenate(xs), np.concatenate(ys), np.concatenate(pixels)
    counts = np.array([m["rows"] for m in meta])
    starts = np.concatenate([[0], np.cumsum(counts)[:-1]])
    predicted = hp.predict_bundle(bundle, hp.bundle_matrix(X, pixel, static_fields), delta)

    # ---- gate: the frozen confirmatory results are reproduced by this prediction function
    pooled = rs.pooled_metrics(y, predicted["rainfall"])
    frozen = evidence["pooled"]["B1_shifted"]
    for key in ("rmse_mm", "bias_mm", "mae_mm"):
        if abs(pooled[key] - frozen[key]) > TOL:
            fail(f"pooled {key} differs from the frozen confirmatory result")
    for name in ("heavy", "very_heavy"):
        again = rs.exceedance_metrics(predicted[name], y, taus[name], rs.EXCEED_THRESHOLDS[name])
        stored = evidence["exceedance"][f"B1:{name}"]["test"]
        for key in ("hits", "misses", "false_alarms"):
            if again[key] != stored[key]:
                fail(f"{name} {key} differs from the frozen confirmatory result")
        if abs(taus[name] - evidence["exceedance"][f"B1:{name}"]["tau"]) > TOL:
            fail(f"{name} threshold differs from the frozen evidence")
    in_year = np.repeat([m["year"] == YEAR for m in meta], counts)
    slice_metrics = rs.pooled_metrics(y[in_year], predicted["rainfall"][in_year])
    stored_year = evidence["by_year"][str(YEAR)]["B1_shifted"]
    for key in ("rmse_mm", "bias_mm", "mae_mm"):
        if abs(slice_metrics[key] - stored_year[key]) > TOL:
            fail(f"the {YEAR} slice {key} differs from the per-year entry of the confirmatory evidence")

    # ---- the product arrays, on exactly the product's cases and valid cells
    ids, b1, hs, vs, case_rmse, raw_all, m2_all, obs_all = [], [], [], [], [], [], [], []
    for i, m in enumerate(meta):
        if m["year"] != YEAR:
            continue
        case_id = f"{m['initialization'].replace('-', '')}T000000Z_{m['product']}"
        if not (APP / f"{case_id}.npz").exists():
            fail(f"no product case for {case_id}")
        with np.load(APP / f"{case_id}.npz", allow_pickle=False) as app:
            mask = app["mask"].ravel()
            product_obs, product_raw, product_m2 = app["observed"].ravel(), app["raw"].ravel(), app["corrected"].ravel()
        sl = slice(starts[i], starts[i] + counts[i])
        cells = pixel[sl]
        scored = np.zeros(hp.GRID_CELLS, dtype=bool)
        scored[cells] = True
        if not np.array_equal(scored, mask):
            fail(f"{case_id}: the cells scored are not the valid cells of the product case")
        if not np.allclose(product_obs[cells], y[sl], atol=1e-4):
            fail(f"{case_id}: the observed values differ from the product case")
        fields = {}
        for name, source in (("b1", predicted["rainfall"]), ("hs", predicted["heavy"]), ("vs", predicted["very_heavy"])):
            grid = np.full(hp.GRID_CELLS, np.nan, dtype=np.float32)
            grid[cells] = source[sl].astype(np.float32)
            fields[name] = grid.reshape(49, 49)
        ids.append(case_id), b1.append(fields["b1"]), hs.append(fields["hs"]), vs.append(fields["vs"])
        case_rmse.append(float(np.sqrt(np.mean((predicted["rainfall"][sl].astype(np.float64) - y[sl]) ** 2))))
        raw_all.append(product_raw[cells]), m2_all.append(product_m2[cells]), obs_all.append(product_obs[cells])
    app_cases = sorted(p.stem for p in APP.glob(f"{YEAR}*.json"))
    if sorted(ids) != app_cases or len(ids) != len(set(ids)):
        fail("the cases built are not exactly the product's cases")
    order = np.argsort(ids)
    ids = [ids[k] for k in order]
    b1, hs, vs = (np.stack([a[k] for k in order]) for a in (b1, hs, vs))
    case_rmse = np.array([case_rmse[k] for k in order])
    valid = np.isfinite(b1)
    if (b1[valid] < 0).any() or not np.isfinite(hs[valid]).all() or not np.isfinite(vs[valid]).all() or not (((hs[valid] >= 0) & (hs[valid] <= 1)).all() and ((vs[valid] >= 0) & (vs[valid] <= 1)).all()):
        fail("a rainfall value is negative or undefined, or a score is outside zero to one, on a valid cell")
    if not np.array_equal(np.isfinite(b1), np.isfinite(hs)) or not np.array_equal(np.isfinite(b1), np.isfinite(vs)):
        fail("the three layers do not share one valid-cell set")

    # ---- the 2019 summary shown beside the maps (descriptive; all three read the same cells)
    obs_cat, raw_cat, m2_cat = np.concatenate(obs_all), np.concatenate(raw_all), np.concatenate(m2_all)
    summary = {"cases": len(ids), "cells": int(len(obs_cat)),
               "rainfall": {"M0": rs.pooled_metrics(obs_cat, raw_cat), "M2": rs.pooled_metrics(obs_cat, m2_cat), "B1": slice_metrics},
               "classifier": {name: hp.categorical(predicted[name][in_year], y[in_year], taus[name], rs.EXCEED_THRESHOLDS[name]) for name in ("heavy", "very_heavy")}}
    PHASE17.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(ARRAYS, case_ids=np.array(ids), b1_rainfall=b1, heavy_score=hs, very_heavy_score=vs, case_rmse_b1=case_rmse)
    manifest = {"schema": "heavy-rain-b1-product-manifest-v1", "protocol_sha256": sha(PROTOCOL), "arrays_file": ARRAYS.name, "arrays_sha256": sha(ARRAYS), "year": YEAR, "cases": len(ids),
                "shift_mm": delta, "thresholds": taus, "model_files_sha256": record["model_files_sha256"], "confirmation_record_sha256": sha(rc.RECORD),
                "gates": {"models_match_record": True, "cases_and_cells_match_product": True, "confirmatory_pooled_results_reproduced": True, "product_year_slice_matches_evidence": True, "values_defined_and_in_range": True,
                          "tolerance": TOL, "reproduction_scope": "all confirmatory years, recomputed in memory with the same settings"},
                "summary_2019": summary, "evidence_roles": protocol["labels"], "built_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds")}
    MANIFEST.write_bytes((json.dumps(rc.clean(manifest), indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False) + "\n").encode("utf-8"))
    for p in (MANIFEST,):
        p.with_suffix(".sha256").write_text(sha(p) + f"  {p.name}\n", encoding="ascii")
    print(json.dumps(rc.clean({"cases": len(ids), "arrays_bytes": ARRAYS.stat().st_size, "shift_mm": delta, "taus": taus, "rmse": {k: v["rmse_mm"] for k, v in summary["rainfall"].items()},
                               "classifier_csi": {k: v["csi"] for k, v in summary["classifier"].items()}, "classifier_frequency_bias": {k: v["frequency_bias"] for k, v in summary["classifier"].items()}}), indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
