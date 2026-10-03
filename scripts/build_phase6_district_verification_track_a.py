"""District-level verification for Track A (the 2017-2019 GEFSv12 reforecast corpus), protocol A v1 (docs/135). Two stages, write-once.

    python scripts/build_phase6_district_verification_track_a.py freeze   # observation-only: writes the protocol with its support counts, NO model value is read
    python scripts/build_phase6_district_verification_track_a.py run      # verifies the frozen protocol hash, then computes the evidence

Everything is carried over from the approved Track B protocol v1 (docs/112): event definitions E1/E2/E3, thresholds, coverage rule, support thresholds, contrasts, latitude bands.
Only the populations change: 2018 is the validation year (development evidence), 2019 the consumed final test (POST-HOC EXPLORATORY ANALYSIS OF THE COMPLETED 2019 FINAL TEST).
Read-only re-aggregation of FROZEN artifacts with the pinned Phase 2C weights; nothing is trained, tuned or selected. Track A and Track B are never pooled.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.app.api import operational as op  # noqa: E402
from backend.app.ml import district_verification as dv  # noqa: E402
from backend.app.ml.district_product import flat_field  # noqa: E402
from backend.app.ml.district_verification import Stack, analyse_districts, case_district_stats  # noqa: E402

EVIDENCE = ROOT / "backend/app/evidence_data/phase6"
PROTOCOL_B = EVIDENCE / "district_verification_protocol_v1.json"
PROTOCOL_A = EVIDENCE / "district_verification_protocol_A_v1.json"
ROLES = {2018: "TRACK_A_2018_VALIDATION_YEAR_DEVELOPMENT_EVIDENCE",
         2019: "TRACK_A_2019_CONSUMED_FINAL_TEST__POST_HOC_EXPLORATORY_ANALYSIS_OF_THE_COMPLETED_2019_FINAL_TEST"}
CACHE_ROLE = {2018: "VALIDATION", 2019: "FINAL_TEST"}
REGIME_TEXT = ("argmax of the frozen forecast-only pseudo-regime classifier probability (M3 hard-routes on exactly this class); "
               "pseudo-labels, not observed meteorological truth")
REPEATS, SEED = 2000, 26080


def load_module(name: str, relative: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


B6 = load_module("build_phase6_district_verification", "scripts/build_phase6_district_verification.py")      # reuse clean/encode/write_once/district_latitudes
P6 = load_module("build_phase6_evidence", "scripts/build_phase6_evidence.py")                              # reuse the Track A cache and frozen-model loaders
sha, encode, write_once = B6.sha, B6.encode, B6.write_once


def api_case_id(key: str) -> str:
    """'2019-06-01T00:00:00Z|day1_24h' (cache key) -> '20190601T000000Z_day1_24h' (the id the API and the district Stack use)."""
    initialization, product = key.split("|")
    return initialization.replace("-", "").replace(":", "") + "_" + product


def obs_only(year: int) -> dict:
    """Observations and the paired-cell mask of every case, read from the cached arrays WITHOUT computing any model value."""
    cache_dir = P6.find_cache(year, CACHE_ROLE[year])
    manifest, arrays = P6.load_cache(cache_dir)
    code = arrays["case_code"].astype(np.int64)
    starts = np.flatnonzero(np.r_[True, np.diff(code) != 0])
    counts = np.diff(np.r_[starts, len(code)])
    pixel = arrays["pixel_i"].astype(np.int64) * 49 + arrays["pixel_j"].astype(np.int64)
    keys = manifest["case_keys"]
    if len(keys) != len(starts):
        raise RuntimeError("case list does not match the cache")
    obs = [flat_field(arrays["y"][s:s + c].astype(np.float32), pixel[s:s + c]) for s, c in zip(starts, counts)]
    return {"case_ids": list(keys), "obs": obs, "lineage": {"cache_manifest_sha256": sha(cache_dir / "manifest.json")}}


def observation_counts(years: tuple[int, ...], weights: np.ndarray) -> dict:
    """The protocol's observation-only support counts (no model value is read), by the same rules as Track B."""
    per_year, kept_by_year = {}, {}
    for year in years:
        data = obs_only(year)
        stats = [case_district_stats(weights, {"obs": o}) for o in data["obs"]]
        cells = np.stack([s["cells"] for s in stats])
        positive = np.where(cells > 0, cells, np.nan)
        median = np.array([float(np.nanmedian(positive[:, d])) if np.isfinite(positive[:, d]).any() else 0.0 for d in range(cells.shape[1])])
        kept = median >= dv.MIN_CELLS
        included = (cells >= dv.MIN_CELLS) & kept[None, :]
        kept_by_year[year] = kept
        block = {"cases": len(stats), "district_case_pairs": int(included.sum()), "median_valid_cells": int(np.median(median[kept]))}
        for key, threshold in dv.THRESHOLDS:
            block[key] = {}
            for definition in dv.DEFINITIONS:
                if definition == "E1":
                    event = np.stack([s[f"any:obs:{key}"] for s in stats])
                elif definition == "E2":
                    event = np.stack([s[f"frac:obs:{key}"] for s in stats]) >= dv.AREA_FRACTION
                else:
                    event = np.stack([s["mean:obs"] for s in stats]) >= threshold
                per_district = (event & included).sum(axis=0)
                block[key][definition] = {"event_pairs": int((event & included).sum()), "districts_ge_30": int(((per_district >= dv.MIN_EVENTS) & kept).sum())}
        per_year[str(year)] = block
    kept_all = np.logical_and.reduce(list(kept_by_year.values()))
    return {"note": "Computed from IMD observations and the frozen valid-cell mask only; no model value was read. Counts after the >= 5 valid-cell rule.",
            "districts_total": int(weights.shape[0]), "districts_kept": int(kept_all.sum()), "districts_excluded": int((~kept_all).sum()), **per_year}


def freeze() -> None:
    if PROTOCOL_A.exists():
        raise SystemExit("protocol A v1 already frozen; a change needs a new version")
    districts, weights, weights_sha, geometry_sha = op._district_static()
    counts = observation_counts((2018, 2019), weights)
    b = json.loads(PROTOCOL_B.read_text(encoding="utf-8"))
    p = json.loads(json.dumps(b))
    p["schema"] = "phase6-district-verification-protocol-A-v1"
    p["status"] = "APPROVED_FOR_EXECUTION"
    p["no_results_computed"] = True
    p["purpose"] = ("Define district-level verification of the frozen Track A (2017-2019 reforecast) models BEFORE any district-level skill score is computed for that track. "
                    "Every definition, threshold and rule is carried over unchanged from the approved Track B protocol v1 (docs/112).")
    p["derived_from"] = {"protocol_v1_sha256": sha(PROTOCOL_B), "what_changes": "only the populations, the frozen inputs and the observation-only support counts; no definition, threshold, support or coverage rule is changed"}
    p["populations"] = {"2018": {"role": ROLES[2018], "label": "Track A 2018 validation year: development evidence (used for early stopping and model selection; not a holdout)"},
                        "2019": {"role": ROLES[2019], "label": "POST-HOC EXPLORATORY ANALYSIS OF THE COMPLETED 2019 FINAL TEST"}}
    p["frozen_inputs"] = dict(b["frozen_inputs"], fields="frozen Track A M0-M4 predictions (reconstructed from the frozen Phase 2B models and cached features, hash-verified) and IMD observations on the paired valid cells (cache roles VALIDATION and FINAL_TEST)",
                              weights=f"Phase 2C overlap weights (sha256 {weights_sha}), shared with Track B", geometry_sha256=geometry_sha)
    p["observation_only_support_counts"] = counts
    p["approval"] = {"approved_by": "project owner",
                     "record": "owner instruction of 2026-10-03: 'make a full plan to implement everything left partial or not completely and implement'; the work package is WP-A of docs/134",
                     "decisions": dict(b["approval"]["decisions"]),
                     "note": ("All decisions are the owner's earlier approvals for Track B protocol v1 (primary event definition E1, at least 30 observed events per district, at least 5 valid cells, three latitude bands), "
                              "carried over unchanged. The wording of this approval is an interpretation of a general instruction and the owner may withdraw it.")}
    p["reproduction_gate"] = ["builder recomputes the observation-only support counts and must match the protocol's counts exactly",
                              "district means for Raw, IMD and the served corrected field of the 2019 cases the API serves must equal the means recomputed from the already-served 49x49 grids (2018 is not served by the API)",
                              "pooled district-mean RMSE for Raw computed by the vectorised path must equal an independent per-district loop",
                              "sum over districts of observed events equals the pooled observed event count"]
    p["forbidden"] = list(b["forbidden"])
    p["reporting_rules"] = [r.replace("2025 is a consumed holdout: results are POST-HOC EXPLORATORY ANALYSIS OF THE COMPLETED 2025 FINAL TEST",
                                      "2019 is a consumed holdout: results are POST-HOC EXPLORATORY ANALYSIS OF THE COMPLETED 2019 FINAL TEST") for r in b["reporting_rules"]]
    PROTOCOL_A.write_text(json.dumps(p, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    (EVIDENCE / "district_verification_protocol_A_v1.sha256").write_text(sha(PROTOCOL_A) + "  district_verification_protocol_A_v1.json\n", encoding="ascii")
    print("protocol A v1 sha256", sha(PROTOCOL_A))
    print(json.dumps({k: v for k, v in counts.items() if k != "note"}, indent=1)[:1600])


def build_stack(year: int, districts, weights, builder_state) -> tuple[Stack, dict]:
    freeze_json, strategy, global_model, experts, ridge = builder_state
    cache_dir = P6.find_cache(year, CACHE_ROLE[year])
    manifest, arrays = P6.load_cache(cache_dir)
    preds = P6.predictions(arrays, strategy, global_model, experts, ridge)
    pop = P6.build_population(year, CACHE_ROLE[year], manifest, arrays, preds, {})
    per_case, regimes, case_ids = [], [], []
    for k, case in enumerate(pop.cases):
        sl = pop.sl(case)
        fields = {"obs": flat_field(pop.y[sl], pop.pixel[sl])}
        for m in dv.MODELS:
            fields[m] = flat_field(pop.preds[m][sl], pop.pixel[sl])
        per_case.append(case_district_stats(weights, fields))
        regimes.append(int(pop.regime[k]))
        case_ids.append(api_case_id(case["case_id"]))
    stack = Stack(per_case, case_ids, [d["district_id"] for d in districts], [d["district_name"] for d in districts], B6.district_latitudes(districts), np.array(regimes))
    return stack, {"cache_manifest_sha256": sha(cache_dir / "manifest.json"), "freeze_manifest_sha256": sha(P6.PHASE2B / "model_selection_freeze.json"), "cases": case_ids}


def reproduction(year: int, stack: Stack, result: dict, weights, protocol: dict) -> dict:
    checks = []

    def expect(label, got, want):
        ok = got == want
        checks.append({"check": label, "got": got, "expected": want, "ok": bool(ok)})
        if not ok:
            raise RuntimeError(f"reproduction gate failed: {label}: got {got}, expected {want}")

    want = protocol["observation_only_support_counts"][str(year)]
    expect("district_case_pairs", result["inclusion"]["district_case_pairs"], want["district_case_pairs"])
    expect("districts_included", result["inclusion"]["districts_included"], protocol["observation_only_support_counts"]["districts_kept"])
    for key in ("heavy", "very_heavy"):
        for definition in dv.DEFINITIONS:
            expect(f"observed_events/{definition}/{key}", result["observed_events_pooled"][definition][key], want[key][definition]["event_pairs"])
    for definition in dv.PER_DISTRICT_DEFINITIONS:
        for key in ("heavy", "very_heavy"):
            expect(f"district_sum/{definition}/{key}", sum(e["categorical"][definition][key]["observed_events"] for e in result["districts"]), result["observed_events_pooled"][definition][key])
    served_checked = 0
    worst = 0.0
    if year == 2019:                                       # the only year the Track A API serves
        from fastapi.testclient import TestClient

        from backend.main import app

        client = TestClient(app)
        sample = np.linspace(0, len(stack.case_ids) - 1, 8).astype(int)
        for ci in sample:
            response = client.get(f"/api/science/cases/{stack.case_ids[ci]}/rainfall")
            if response.status_code != 200:
                raise RuntimeError(response.text)
            data = response.json()["data"]
            grids = {name: np.array([[np.nan if v is None else v for v in row] for row in data[key]], float).ravel() for name, key in (("M0", "raw"), ("obs", "observed"))}
            corrected = np.array([[np.nan if v is None else v for v in row] for row in data["corrected"]], float).ravel()
            valid = np.isfinite(grids["M0"]) & np.isfinite(grids["obs"]) & np.isfinite(corrected)
            for d in range(weights.shape[0]):
                active = (weights[d] > 0) & valid
                if not active.any():
                    continue
                q = weights[d][active].astype(float) / weights[d][active].astype(float).sum()
                for name in ("M0", "obs"):
                    worst = max(worst, abs(float(q @ grids[name][active]) - float(stack.mean[name][ci, d])))
            served_checked += 1
        checks.append({"check": "district_means_vs_served_grids", "fields": ["M0 (raw)", "IMD"], "cases_sampled": served_checked, "max_abs_diff_mm": worst, "ok": worst < 1e-3})
        if worst >= 1e-3:
            raise RuntimeError(f"reproduction gate failed: district means differ from served grids by {worst} mm")
    total = count = 0.0
    for c in range(stack.cells.shape[0]):
        for d in range(stack.cells.shape[1]):
            if stack.included[c, d]:
                total += (float(stack.mean["M0"][c, d]) - float(stack.mean["obs"][c, d])) ** 2
                count += 1
    loop, vectorised = float(np.sqrt(total / count)), result["continuous"]["pooled"]["all"]["M0"]["rmse_mm"]
    checks.append({"check": "pooled_raw_rmse_loop_vs_vectorised", "loop": loop, "vectorised": vectorised, "ok": abs(loop - vectorised) < 1e-9})
    if abs(loop - vectorised) >= 1e-9:
        raise RuntimeError("reproduction gate failed: pooled Raw RMSE loop differs from the vectorised value")
    return {"status": "REPRODUCED", "check_count": len(checks), "checks": checks}


def run() -> None:
    sidecar = (EVIDENCE / "district_verification_protocol_A_v1.sha256").read_text(encoding="ascii").split()[0]
    if sha(PROTOCOL_A) != sidecar:
        raise SystemExit("protocol A v1 differs from its sidecar: refusing to run")
    protocol = json.loads(PROTOCOL_A.read_text(encoding="utf-8"))
    if protocol["status"] != "APPROVED_FOR_EXECUTION" or protocol["schema"] != "phase6-district-verification-protocol-A-v1":
        raise SystemExit("protocol A v1 is not the approved version")
    districts, weights, weights_sha, geometry_sha = op._district_static()
    freeze_json = json.loads((P6.PHASE2B / "model_selection_freeze.json").read_text(encoding="utf-8"))
    state = (freeze_json, *P6.verified_models(freeze_json))
    files = {}
    for year in (2018, 2019):
        stack, lineage = build_stack(year, districts, weights, state)
        result = analyse_districts(stack, op.REGIME_CLASSES, repeats=REPEATS, seed=SEED)
        result["reproduction"] = reproduction(year, stack, result, weights, protocol)
        result.update({"schema": "phase6-district-verification-v1", "track": "A", "year": year, "evidence_role": ROLES[year], "protocol_sha256": sha(PROTOCOL_A),
                       "regime_assignment": REGIME_TEXT, "models": list(dv.MODELS), "corrected_models": list(dv.CORRECTED), "weights_sha256": weights_sha, "geometry_sha256": geometry_sha,
                       "lineage_sha256": {k: v for k, v in lineage.items() if k != "cases"}, "bootstrap": {"repeats": REPEATS, "seed": SEED, "resampling": "whole cases (all districts of a case together)"},
                       "min_valid_cells": dv.MIN_CELLS})
        name = f"district_verification_A_{year}.json"
        digest = write_once(EVIDENCE / name, encode(result))
        files[name] = {"sha256": digest, "track": "A", "year": year, "evidence_role": ROLES[year], "cases": result["inclusion"]["cases"],
                       "district_case_pairs": result["inclusion"]["district_case_pairs"], "districts_included": result["inclusion"]["districts_included"],
                       "reproduction": result["reproduction"]["status"]}
        print(f"{year}: {result['inclusion']['cases']} cases, {result['inclusion']['district_case_pairs']} district-case pairs, {result['inclusion']['districts_included']} districts; "
              f"reproduction {result['reproduction']['status']} ({result['reproduction']['check_count']} checks) -> {name}", flush=True)
    manifest = {"schema": "phase6-district-verification-manifest-A-v1", "protocol_sha256": sha(PROTOCOL_A), "files": files,
                "notes": ["Read-only re-aggregation of frozen Track A artifacts under protocol A v1 (docs/135); no model was trained, tuned or selected.",
                          "2019 is a consumed holdout: post-hoc descriptive analysis only.", "Regimes are forecast-only pseudo-labels, not observed meteorological truth.",
                          "Track A and Track B are never pooled."]}
    digest = write_once(EVIDENCE / "district_verification_manifest_A.json", encode(manifest))
    (EVIDENCE / "district_verification_manifest_A.sha256").write_text(digest + "\n", encoding="ascii", newline="\n")
    print("district_verification_manifest_A.json sha256", digest)


if __name__ == "__main__":
    stage = sys.argv[1] if len(sys.argv) > 1 else ""
    if stage == "freeze":
        freeze()
    elif stage == "run":
        run()
    else:
        raise SystemExit("usage: build_phase6_district_verification_track_a.py freeze|run")
