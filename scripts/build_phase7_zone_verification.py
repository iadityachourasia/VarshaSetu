"""Stage 1 of the coastal/orographic protocol v3 (docs/115, docs/117): zone-stratified verification of the FROZEN M0-M4 grids.

Read-only re-aggregation. Nothing is trained, tuned or selected. The script refuses to run against any protocol or geography hash other
than the frozen ones, and refuses to write unless every reproduction check passes. Outputs are write-once.

  Track A 2018 - validation year (development evidence)            Track A 2019 - POST-HOC EXPLORATORY ANALYSIS OF THE COMPLETED 2019 FINAL TEST
  Track B 2024 - validation/selection year (development evidence)   Track B 2025 - POST-HOC EXPLORATORY ANALYSIS OF THE COMPLETED 2025 FINAL TEST

    python scripts/build_phase7_zone_verification.py
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
from backend.app.ml import zone_verification as zv  # noqa: E402
from backend.app.ml.district_product import flat_field  # noqa: E402

PHASE6 = ROOT / "backend/app/evidence_data/phase6"
PHASE7 = ROOT / "backend/app/evidence_data/phase7"
PROTOCOL = PHASE6 / "coastal_orographic_protocol_v3.json"
PROTOCOL_SHA = "a9ff78173ddb6026e6b297c2da2128dde2fdcf825ae8b0c368c5f5fa79d199fd"
GEOGRAPHY = PHASE7 / "static_geography_v1.json"
SCHEMA = "phase7-zone-verification-v1"
MODELS = {"A": ["M0", "M2", "M3", "M4"], "B": ["M0", "M1", "M2", "M3", "M4"]}      # protocol models_verified
ROLES = {("A", 2018): "TRACK_A_2018_VALIDATION_YEAR_DEVELOPMENT_EVIDENCE",
         ("A", 2019): "TRACK_A_2019_CONSUMED_FINAL_TEST__POST_HOC_EXPLORATORY_ANALYSIS_OF_THE_COMPLETED_2019_FINAL_TEST",
         ("B", 2024): "PHASE4I_VALIDATION_SELECTION_YEAR_DEVELOPMENT_EVIDENCE",
         ("B", 2025): "PHASE4J_HOLDOUT_CONSUMED_POST_HOC_DESCRIPTIVE_ONLY"}
PAIRS = {"A": (2018, 2019), "B": (2024, 2025)}
REGIME_NAMES = ("ACTIVE_MONSOON", "BREAK_WEAK_MONSOON", "LOW_DEPRESSION_INFLUENCED")
DECISION_METRICS = {"q1": ("rmse", "bias", "heavy_csi"), "q2": ("rmse", "heavy_csi")}      # protocol decision_rule: RMSE, heavy CSI or bias
FSS_TEXT = ("Not reported in Stage 1: the protocol reports FSS only where a zone is spatially contiguous enough; the zones are scattered "
            "cell sets (coast strip, escarpment, mixed interior), so a neighbourhood score would mix zone and non-zone cells.")


def sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def clean(value):
    if isinstance(value, dict):
        return {k: clean(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [clean(v) for v in value]
    if isinstance(value, (np.floating, float)):
        return None if not np.isfinite(value) else float(value)
    if isinstance(value, np.integer):
        return int(value)
    if isinstance(value, np.bool_):
        return bool(value)
    return value


def encode(value) -> bytes:
    return (json.dumps(clean(value), sort_keys=True, indent=2, ensure_ascii=False, allow_nan=False) + "\n").encode("utf-8")


def write_once(path: Path, data: bytes) -> str:
    if path.exists() and path.read_bytes() != data:
        raise RuntimeError(f"frozen zone-verification evidence would change: {path}")
    path.write_bytes(data)
    return hashlib.sha256(data).hexdigest()


def load_phase6_builder():
    spec = importlib.util.spec_from_file_location("build_phase6_evidence", ROOT / "scripts/build_phase6_evidence.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_track_a(year: int, role: str, builder) -> dict:
    freeze = json.loads((builder.PHASE2B / "model_selection_freeze.json").read_text(encoding="utf-8"))
    cache_dir = builder.find_cache(year, role)
    manifest, arrays = builder.load_cache(cache_dir)
    strategy, global_model, experts, ridge = builder.verified_models(freeze)
    preds = builder.predictions(arrays, strategy, global_model, experts, ridge)
    pop = builder.build_population(year, role, manifest, arrays, preds, {})
    case_ids, obs, fields, regimes = [], [], {m: [] for m in MODELS["A"]}, []
    for k, case in enumerate(pop.cases):
        sl = pop.sl(case)
        case_ids.append(case["case_id"])
        obs.append(flat_field(pop.y[sl], pop.pixel[sl]))
        for m in MODELS["A"]:
            fields[m].append(flat_field(pop.preds[m][sl], pop.pixel[sl]))
        regimes.append(int(pop.regime[k]))
    return {"case_ids": case_ids, "obs": np.array(obs), "fields": {m: np.array(v) for m, v in fields.items()}, "regime": np.array(regimes),
            "lead": np.array([int(c.split("day")[1][0]) for c in case_ids]),
            "lineage": {"cache_manifest_sha256": sha(cache_dir / "manifest.json"), "freeze_manifest_sha256": sha(builder.PHASE2B / "model_selection_freeze.json")}}


def load_track_b(year: int) -> dict:
    case_ids = sorted(op._paired_cases_by_id(year))
    loader = op._REGIME_LOADER[year]()
    obs, fields, regimes = [], {m: [] for m in MODELS["B"]}, []
    for case_id in case_ids:
        base = op._district_case_fields(year, case_id, "m1", False)
        obs.append(base["observed"])
        fields["M0"].append(base["raw"])
        fields["M1"].append(base["corrected"])
        for model in ("m2", "m3", "m4"):
            other = op._district_case_fields(year, case_id, model, False)
            if not (np.array_equal(other["raw"], base["raw"], equal_nan=True) and np.array_equal(other["observed"], base["observed"], equal_nan=True)):
                raise RuntimeError(f"{case_id}: Raw/IMD differ between model loads")
            fields[model.upper()].append(other["corrected"])
        vector = loader.get(case_id)
        if vector is None:
            raise RuntimeError(f"{case_id}: no frozen regime probability")
        regimes.append(int(np.argmax(vector)))
    return {"case_ids": case_ids, "obs": np.array(obs), "fields": {m: np.array(v) for m, v in fields.items()}, "regime": np.array(regimes),
            "lead": np.array([int(c.split("day")[1][0]) for c in case_ids]), "lineage": {}}


def reproduction(track: str, year: int, totals: np.ndarray, models: list[str], masks: dict) -> dict:
    """The ALL-zone totals must equal the already-published frozen evidence (continuous within 1e-6 mm, counts exactly)."""
    reference = json.loads((PHASE6 / f"regime_verification_{track}_{year}.json").read_text(encoding="utf-8"))["overall"]
    checks, worst = [], 0.0
    all_index = zv.ZONES.index("ALL")
    for mi, model in enumerate(models):
        mine = zv.metrics(totals[all_index, mi])
        ref = reference["continuous"][model]
        for mine_key, ref_key in (("rmse_mm", "rmse_mm"), ("mae_mm", "mae_mm"), ("bias_mm", "bias_mm")):
            diff = abs(mine[mine_key] - ref[ref_key])
            worst = max(worst, diff)
            checks.append({"check": f"{model}/{mine_key}", "abs_diff": diff})
        if mine["cell_count"] != reference["cell_count"]:
            raise RuntimeError(f"{track}{year}/{model}: cell count {mine['cell_count']} != {reference['cell_count']}")
        for name, _ in zv.THRESHOLDS:
            ref_counts = reference["categorical"][name][model]
            got = mine["categorical"][name]
            for key, ref_key in (("hits", "hits"), ("misses", "misses"), ("false_alarms", "false_alarms")):
                if got[key] != ref_counts[ref_key]:
                    raise RuntimeError(f"{track}{year}/{model}/{name}/{key}: {got[key]} != {ref_counts[ref_key]}")
            checks.append({"check": f"{model}/{name}/counts", "abs_diff": 0.0})
    if worst > 1e-6:
        raise RuntimeError(f"{track}{year}: reproduction failed (max abs diff {worst})")
    parts = sum(totals[zv.ZONES.index(z)] for z in zv.PRE_REGISTERED_ZONES)
    if not np.allclose(parts, totals[all_index]):
        raise RuntimeError("pre-registered zones do not add up to the all-cell totals")
    return {"status": "REPRODUCED", "check_count": len(checks), "max_abs_diff": worst, "tolerance_mm": 1e-6, "counts_exact": True,
            "zones_partition_all_cells": True, "reference_file": f"regime_verification_{track}_{year}.json",
            "reference_sha256": sha(PHASE6 / f"regime_verification_{track}_{year}.json")}


def analyse_year(track: str, year: int, data: dict, masks: dict, artifact: dict) -> dict:
    models = MODELS[track]
    n = len(data["case_ids"])
    stack = np.stack([zv.case_stats(data["obs"][i], {m: data["fields"][m][i] for m in models}, masks) for i in range(n)])
    cell_counts = {z: int(masks[z].sum()) for z in zv.ZONES}
    totals = stack.sum(axis=0)
    gate = zv.support(stack, cell_counts)

    pooled = {}
    for zi, zone in enumerate(zv.ZONES):
        pooled[zone] = {}
        for mi, model in enumerate(models):
            block = zv.metrics(totals[zi, mi])
            if not gate[zone]["continuous_supported"]:
                block = {"cell_count": block["cell_count"], "status": "insufficient_support"}
            else:
                for name, _ in zv.THRESHOLDS:
                    if not gate[zone][name]["supported"]:
                        block["categorical"][name] = {"status": "insufficient_support", "observed_event_pairs": gate[zone][name]["observed_event_pairs"]}
            pooled[zone][model] = block

    boot = zv.paired_bootstrap(stack, models)
    differences = {"q1": {}, "q2": {}}
    for (question, zone, model, metric), value in boot.items():
        needs = {"heavy_csi": "heavy", "very_heavy_csi": "very_heavy"}.get(metric)
        supported = gate[zone]["continuous_supported"] and (needs is None or gate[zone][needs]["supported"])
        entry = value if supported else {"status": "insufficient_support", "point": None}
        differences[question].setdefault(zone, {}).setdefault(model, {})[metric] = entry

    by_regime = {}
    for ri, regime in enumerate(REGIME_NAMES):
        idx = np.flatnonzero(data["regime"] == ri)
        by_regime[regime] = {"case_count": int(len(idx)), "zones": {}}
        if not len(idx):
            continue
        sub_totals = stack[idx].sum(axis=0)
        sub_gate = zv.support(stack[idx], cell_counts)
        for zi, zone in enumerate(zv.PRE_REGISTERED_ZONES):
            z = zv.ZONES.index(zone)
            block = {"cases": sub_gate[zone]["cases"], "models": {}}
            for mi, model in enumerate(models):
                m = zv.metrics(sub_totals[z, mi])
                if not sub_gate[zone]["continuous_supported"]:
                    block["models"][model] = {"status": "insufficient_support"}
                    continue
                if not sub_gate[zone]["heavy"]["supported"]:
                    m["categorical"]["heavy"] = {"status": "insufficient_support", "observed_event_pairs": sub_gate[zone]["heavy"]["observed_event_pairs"]}
                m["categorical"].pop("very_heavy", None)
                block["models"][model] = m
            by_regime[regime]["zones"][zone] = block

    return {
        "schema": SCHEMA, "track": track, "year": year, "evidence_role": ROLES[(track, year)], "case_count": n,
        "models": models, "protocol_sha256": PROTOCOL_SHA, "static_geography_sha256": sha(GEOGRAPHY),
        "zones": {z: {"cells": cell_counts[z], "in_decision_rule": z in zv.PRE_REGISTERED_ZONES} for z in zv.ZONES},
        "support": gate, "pooled": pooled, "differences": differences, "by_pseudo_regime": by_regime,
        "bootstrap": {"method": "paired whole-case bootstrap (cells of a case stay together, same resamples for every model and statistic)",
                      "repeats": zv.REPEATS, "seed": zv.SEED, "note": "optimistic: cells within a case are spatially correlated and consecutive days are serially correlated"},
        "definitions": {"q1": "metric(zone, model) - metric(all cells, model); bias = forecast - observation",
                        "q2": "[metric(zone, model) - metric(zone, Raw)] - [metric(all cells, model) - metric(all cells, Raw)]; rmse and CSI",
                        "all_cells": "every paired cell of the case population (zones are subsets of it)",
                        "regime_assignment": "argmax of the frozen forecast-only pseudo-regime classifier probability; pseudo-labels, not meteorological truth"},
        "fss": {"status": "not_reported", "reason": FSS_TEXT},
        "reproduction": reproduction(track, year, totals, models, masks), "lineage": data["lineage"],
    }


def decision_summary(results: dict) -> dict:
    """Apply the protocol's decision rule: development interval excludes zero AND the final-test point estimate has the same sign."""
    out = {"rule": "geographic gap = paired interval of (zone value - all-cell value) excludes zero in the development year and the sign of the "
                   "consumed final-test year's point estimate is the same (post-hoc); decision metrics: RMSE, heavy-event CSI, bias",
           "tracks": {}}
    for track, (dev_year, final_year) in PAIRS.items():
        dev, final = results[(track, dev_year)], results[(track, final_year)]
        rows, tests = [], 0
        for question, metrics in DECISION_METRICS.items():
            for zone in zv.PRE_REGISTERED_ZONES:
                for model, by_metric in dev["differences"][question][zone].items():
                    for metric in metrics:
                        d = by_metric.get(metric)
                        f = final["differences"][question][zone].get(model, {}).get(metric)
                        if not d or d.get("status") != "ok" or not f or f.get("status") != "ok":
                            continue
                        tests += 1
                        same_sign = bool(d["point"] * f["point"] > 0)
                        gap = bool(d["excludes_zero"] and same_sign)
                        if d["excludes_zero"] or gap:
                            rows.append({"question": question, "zone": zone, "model": model, "metric": metric, "development_point": d["point"],
                                         "development_interval95": d["interval95"], "final_point": f["point"], "final_interval95": f["interval95"],
                                         "final_interval_excludes_zero": f["excludes_zero"], "same_sign": same_sign, "geographic_gap": gap})
        gaps = [r for r in rows if r["geographic_gap"]]
        out["tracks"][track] = {"development_year": dev_year, "final_test_year": final_year, "tests": tests,
                                "development_significant": len(rows),               # rows hold exactly the tests whose development interval excludes zero
                                "geographic_gaps": len(gaps), "expected_development_significant_by_chance": round(0.05 * tests, 1),
                                "expected_gaps_by_chance": round(0.025 * tests, 1),
                                "caveat": "tests share cases and models and are strongly dependent, so the chance counts are only a rough guide; intervals are optimistic",
                                "rows": rows}
    out["stage_3_recommended"] = any(t["geographic_gaps"] > 0 for t in out["tracks"].values())
    return out


def main() -> None:
    if sha(PROTOCOL) != PROTOCOL_SHA:
        raise SystemExit("protocol v3 hash mismatch: refusing to run")
    artifact = json.loads(GEOGRAPHY.read_text(encoding="utf-8"))
    if artifact["protocol"]["sha256"] != PROTOCOL_SHA or not artifact["qa"]["criteria_met"]:
        raise SystemExit("static geography artifact does not match the frozen protocol or failed QA: refusing to run")
    masks = zv.zone_masks(artifact["fields"]["zone"])
    PHASE7.mkdir(parents=True, exist_ok=True)
    builder = load_phase6_builder()
    results, files = {}, {}
    plan = [("A", 2018, "VALIDATION"), ("A", 2019, "FINAL_TEST"), ("B", 2024, None), ("B", 2025, None)]
    for track, year, role in plan:
        data = load_track_a(year, role, builder) if track == "A" else load_track_b(year)
        result = analyse_year(track, year, data, masks, artifact)
        results[(track, year)] = result
        name = f"zone_verification_{track}_{year}.json"
        digest = write_once(PHASE7 / name, encode(result))
        files[name] = {"sha256": digest, "track": track, "year": year, "evidence_role": result["evidence_role"], "cases": result["case_count"],
                       "reproduction": result["reproduction"]["status"]}
        print(f"{track} {year}: {result['case_count']} cases, reproduction {result['reproduction']['status']} "
              f"(max diff {result['reproduction']['max_abs_diff']:.2e}) -> {name}", flush=True)
    summary = decision_summary(results)
    digest = write_once(PHASE7 / "zone_decision_summary.json", encode(summary))
    files["zone_decision_summary.json"] = {"sha256": digest, "evidence_role": "DECISION_RULE_APPLICATION_DEVELOPMENT_PLUS_POST_HOC", "cases": None, "reproduction": "n/a"}
    manifest = {"schema": "phase7-zone-verification-manifest-v1", "protocol_sha256": PROTOCOL_SHA, "static_geography_sha256": sha(GEOGRAPHY), "files": files,
                "notes": ["Read-only re-aggregation of frozen artifacts; no model was trained, tuned or selected.",
                          "Consumed holdouts (Track A 2019, Track B 2025) are post-hoc descriptive analyses only.",
                          "Zones are a rule-based convention, not a validated regime; regimes are forecast-only pseudo-labels."]}
    data = encode(manifest)
    digest = write_once(PHASE7 / "zone_verification_manifest.json", data)
    (PHASE7 / "zone_verification_manifest.sha256").write_text(digest + "\n", encoding="ascii")
    for track, block in summary["tracks"].items():
        print(f"Track {track}: {block['tests']} tests, {block['development_significant']} development-significant "
              f"(chance ~{block['expected_development_significant_by_chance']}), {block['geographic_gaps']} gaps (chance ~{block['expected_gaps_by_chance']})")
    print("stage_3_recommended:", summary["stage_3_recommended"])


if __name__ == "__main__":
    main()
