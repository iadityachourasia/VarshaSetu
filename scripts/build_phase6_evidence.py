"""Build the Phase 6 (docs/108) tracked evidence: regime/lead-stratified categorical + FSS for M0-M4.

Read-only re-aggregation of FROZEN artifacts. Nothing is trained, tuned or selected.

  Track A 2018  - validation year (development evidence): frozen models applied to the 2018 cache
  Track A 2019  - consumed final test: POST-HOC EXPLORATORY ANALYSIS OF THE COMPLETED 2019 FINAL TEST
  Track B 2024/2025 - Phase 4M results (docs/106) packaged byte-for-byte

A reproduction gate recomputes every per-model overall / per-lead / per-regime continuous and
threshold metric and requires exact agreement with the frozen Phase 2B results before anything is
written. Outputs are write-once: a re-run aborts if a file would change.

    python scripts/build_phase6_evidence.py
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from xgboost import XGBRegressor  # noqa: E402

from backend.app.ml.phase2b import REGIME_NAMES, load_cache, safe_ridge_predict, verification_metrics, xgb_predict  # noqa: E402
from backend.app.ml.verification_extra import MODELS, Population, analyse  # noqa: E402

PHASE2B = ROOT / "data/manifests/phase2b"
CACHE_ROOT = ROOT / "data/processed/phase2b/feature_cache"
# Inside the backend package so the existing Docker image (COPY backend/) ships it with no build changes.
OUT = ROOT / "backend/app/evidence_data/phase6"
PHASE4M = ROOT / "experiments/recent_historical/phase4m_regime_categorical_fss_v1/results"
SCHEMA = "phase6-regime-verification-v1"
MODEL_KEYS = {"M0": "M0_RAW_GEFS", "M1": "M1_LINEAR_RIDGE_MOS", "M2": "M2_GLOBAL_XGBOOST",
              "M3": "M3_HARD_REGIME_XGBOOST", "M4": "M4_SOFT_REGIME_MOE"}
ROLES = {
    2018: "TRACK_A_2018_VALIDATION_YEAR_DEVELOPMENT_EVIDENCE",
    2019: "TRACK_A_2019_CONSUMED_FINAL_TEST__POST_HOC_EXPLORATORY_ANALYSIS_OF_THE_COMPLETED_2019_FINAL_TEST",
}
REGIME_TEXT = ("argmax of the frozen forecast-only pseudo-regime classifier probability (M3 hard-routes on exactly "
               "this class); pseudo-labels, not observed meteorological truth")


def sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_once(path: Path, data: bytes) -> str:
    if path.exists() and path.read_bytes() != data:
        raise RuntimeError(f"frozen Phase 6 evidence would change: {path}")
    path.write_bytes(data)
    return hashlib.sha256(data).hexdigest()


def encode(value) -> bytes:
    return (json.dumps(value, sort_keys=True, indent=2, ensure_ascii=False, allow_nan=False) + "\n").encode("utf-8")


def find_cache(year: int, role: str) -> Path:
    for manifest in CACHE_ROOT.glob("*/manifest.json"):
        data = json.loads(manifest.read_text(encoding="utf-8"))
        if data["year"] == year and data["role"] == role:
            return manifest.parent
    raise FileNotFoundError(f"no {role} feature cache for {year} under {CACHE_ROOT}")


def verified_models(freeze: dict):
    expected = freeze["models_sha256"]
    for name, digest in expected.items():
        if sha(PHASE2B / "models" / name) != digest:
            raise RuntimeError(f"frozen model hash mismatch: {name}")
    strategy = freeze["selected_xgboost_target_strategy_by_2018_rmse"]

    def load(name):
        model = XGBRegressor()
        model.load_model(str(PHASE2B / "models" / name))
        return model
    experts = {i: load(f"expert_{REGIME_NAMES[i].lower()}.json") for i in range(3)}
    ridge = json.loads((PHASE2B / "models/ridge_mos.safe.json").read_text(encoding="utf-8"))
    return strategy, load("global_xgboost.json"), experts, ridge


def predictions(arrays, strategy, global_model, experts, ridge):
    x, prob, hard = arrays["X"], arrays["regime_probability"], arrays["predicted_regime_id"]
    outputs = {i: xgb_predict(experts[i], x, strategy) for i in range(3)}
    hard_pred = np.empty(len(x), dtype=np.float32)
    for i in range(3):
        hard_pred[hard == i] = outputs[i][hard == i]
    soft = np.maximum(0.0, sum(prob[:, i] * outputs[i] for i in range(3)))
    if not np.allclose(prob.sum(axis=1), 1.0, atol=1e-4):
        raise RuntimeError("regime probabilities do not sum to 1")
    preds = {"M0": arrays["raw"].astype(np.float32), "M1": safe_ridge_predict(ridge, x).astype(np.float32),
             "M2": xgb_predict(global_model, x, strategy).astype(np.float32),
             "M3": hard_pred, "M4": soft.astype(np.float32)}
    for name, values in preds.items():
        if values.shape != arrays["y"].shape or not np.isfinite(values).all() or float(values.min()) < 0.0:
            raise RuntimeError(f"{name}: predictions must be finite, non-negative and aligned with the observations")
    return preds


def build_population(year: int, role: str, manifest: dict, arrays: dict, preds: dict, lineage: dict) -> Population:
    code = arrays["case_code"].astype(np.int64)
    if not (np.diff(code) >= 0).all():
        raise RuntimeError("cache rows are not grouped by case")
    keys = manifest["case_keys"]
    cases, prob = [], []
    starts = np.flatnonzero(np.r_[True, np.diff(code) != 0])
    counts = np.diff(np.r_[starts, len(code)])
    if len(starts) != len(keys) or [c["valid_cells"] for c in manifest["common_cases"]] != counts.tolist():
        raise RuntimeError("case_code ordering does not match the manifest case list")
    for key, start, count in zip(keys, starts, counts):
        cases.append({"case_id": key, "row_start": int(start), "row_count": int(count)})
        prob.append(arrays["regime_probability"][start])
        if int(np.argmax(arrays["regime_probability"][start])) != int(arrays["predicted_regime_id"][start]):
            raise RuntimeError("predicted_regime_id is not the argmax of regime_probability")
    pixel = arrays["pixel_i"].astype(np.int64) * 49 + arrays["pixel_j"].astype(np.int64)
    return Population(year, cases, arrays["y"].astype(np.float32), pixel, preds, np.stack(prob), lineage)


def reproduction(pop: Population, arrays: dict, frozen_results: dict) -> dict:
    """Recompute every frozen per-model overall / per-lead / per-regime metric and require exact agreement."""
    lead, regime_id, y = arrays["lead"], arrays["predicted_regime_id"], pop.y
    checks, worst = [], 0.0

    def compare(label, frozen, mine):
        nonlocal worst
        for k in ("rmse_mm", "mae_mm", "bias_mm"):
            diff = abs(frozen["continuous"][k] - mine["continuous"][k])
            worst = max(worst, diff)
            checks.append({"check": f"{label}/{k}", "frozen": frozen["continuous"][k], "recomputed": mine["continuous"][k], "abs_diff": diff})
        for name, frozen_event in frozen["thresholds"].items():
            mine_event = mine["thresholds"][name]
            for k in ("hits", "misses", "false_alarms", "sample_count"):
                if frozen_event[k] != mine_event[k]:
                    raise RuntimeError(f"{label}/{name}/{k}: frozen {frozen_event[k]} != recomputed {mine_event[k]}")
            checks.append({"check": f"{label}/{name}/counts", "frozen": [frozen_event[k] for k in ("hits", "misses", "false_alarms")],
                           "recomputed": [mine_event[k] for k in ("hits", "misses", "false_alarms")], "abs_diff": 0.0})

    for model, key in MODEL_KEYS.items():
        frozen = frozen_results[key]
        p = pop.preds[model]
        compare(f"{model}/overall", frozen["overall"], verification_metrics(y, p))
        for hours, block in frozen["by_lead_hours"].items():
            sel = lead == int(hours)
            compare(f"{model}/lead{hours}", block, verification_metrics(y[sel], p[sel]))
        for rid, block in frozen["by_forecast_only_regime"].items():
            sel = regime_id == int(rid)
            compare(f"{model}/regime{rid}", block, verification_metrics(y[sel], p[sel]))
    # Counts must match exactly (checked above). Continuous metrics may differ only by float32
    # accumulation noise far below any reported precision (mm); the gate is 1e-6 mm.
    if worst > 1e-6:
        raise RuntimeError(f"{pop.year}: reproduction of frozen metrics failed (max abs diff {worst})")
    top = max(checks, key=lambda c: c["abs_diff"])
    return {"status": "REPRODUCED", "check_count": len(checks), "max_abs_diff": worst,
            "tolerance_mm": 1e-6, "counts_exact": True, "worst_check": top["check"], "checks": checks}


def build_track_a(year: int, role: str, frozen_results: dict, freeze: dict) -> tuple[dict, dict]:
    cache_dir = find_cache(year, role)
    manifest, arrays = load_cache(cache_dir)          # verifies every array hash against the cache manifest
    strategy, global_model, experts, ridge = verified_models(freeze)
    preds = predictions(arrays, strategy, global_model, experts, ridge)
    lineage = {"cache_manifest_sha256": sha(cache_dir / "manifest.json"),
               "cache_arrays_sha256": manifest["arrays_sha256"],
               "freeze_manifest_sha256": sha(PHASE2B / "model_selection_freeze.json"),
               "models_sha256": freeze["models_sha256"]}
    pop = build_population(year, role, manifest, arrays, preds, lineage)
    result = analyse(pop)
    result["reproduction"] = reproduction(pop, arrays, frozen_results)
    result.update({"schema": SCHEMA, "track": "A", "evidence_role": ROLES[year], "regime_assignment": REGIME_TEXT,
                   "lineage_sha256": lineage, "models_applied_without_retraining": True})
    return result, {"cases": len(pop.cases), "cells": int(len(pop.y))}


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    freeze = json.loads((PHASE2B / "model_selection_freeze.json").read_text(encoding="utf-8"))
    final = json.loads((PHASE2B / "2019_final_results.json").read_text(encoding="utf-8"))
    if final["freeze_manifest_sha256"] != sha(PHASE2B / "model_selection_freeze.json"):
        raise RuntimeError("2019 results do not reference the present freeze manifest")
    files = {}
    plan = [("A", 2018, "VALIDATION", freeze["validation_results"]), ("A", 2019, "FINAL_TEST", final["test_results"])]
    for track, year, role, frozen in plan:
        result, size = build_track_a(year, role, frozen, freeze)
        name = f"regime_verification_{track}_{year}.json"
        digest = write_once(OUT / name, encode(result))
        files[name] = {"sha256": digest, "track": track, "year": year, "evidence_role": result["evidence_role"],
                       "source": "scripts/build_phase6_evidence.py (frozen Phase 2B models + feature cache)", **size,
                       "reproduction": result["reproduction"]["status"]}
        print(f"Track A {year}: {size['cases']} cases, reproduction {result['reproduction']['status']} "
              f"({result['reproduction']['check_count']} checks, max diff {result['reproduction']['max_abs_diff']:.2e}) -> {name}", flush=True)
    for year in (2024, 2025):
        source = PHASE4M / f"{year}_regime_categorical_fss.json"
        data = source.read_bytes()
        parsed = json.loads(data)
        if parsed["reproduction"]["status"] != "REPRODUCED":
            raise RuntimeError(f"Phase 4M {year} result is not a reproduced result")
        name = f"regime_verification_B_{year}.json"
        digest = write_once(OUT / name, data)
        files[name] = {"sha256": digest, "track": "B", "year": year, "evidence_role": parsed["evidence_role"],
                       "source": f"experiments/recent_historical/phase4m_regime_categorical_fss_v1/results/{source.name} (byte-identical copy)",
                       "cases": parsed["case_count"], "cells": parsed["overall"]["cell_count"], "reproduction": "REPRODUCED"}
        print(f"Track B {year}: packaged {name} (sha256 {digest[:12]}…)", flush=True)
    manifest = {"schema": "phase6-evidence-manifest-v1", "files": files,
                "notes": ["Read-only re-aggregation of frozen artifacts; no model was trained, tuned or selected.",
                          "Consumed holdouts (Track A 2019, Track B 2025) are post-hoc descriptive analyses only.",
                          "Regimes are forecast-only pseudo-labels, not observed meteorological truth."]}
    data = encode(manifest)
    digest = write_once(OUT / "evidence_manifest.json", data)
    (OUT / "evidence_manifest.sha256").write_text(digest + "\n", encoding="ascii")
    print(f"evidence_manifest.json sha256 {digest}")


if __name__ == "__main__":
    main()
