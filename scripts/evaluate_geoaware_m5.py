"""Evaluate the selected geography-aware models against M0-M4 under the frozen protocol geoaware_protocol_v1.json (docs/124).

Runs only after scripts/train_geoaware_m5.py has written the selection freeze. It verifies the protocol, the freeze and every model hash, makes
predictions for Track B 2024 (development evidence) and 2025 (POST-HOC analysis of the completed final test, never used for any choice),
reproduces the published M0-M4 zone verification exactly (gate), then reports pooled metrics per zone, paired whole-case bootstrap
differences against M2 and against the internal control A0, the guardrails and the pre-registered decision. Outputs are write-once.

    python scripts/evaluate_geoaware_m5.py
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

from xgboost import XGBRegressor  # noqa: E402

from backend.app.api import operational as op  # noqa: E402
from backend.app.ml import geoaware as ga  # noqa: E402
from backend.app.ml import zone_verification as zv  # noqa: E402
from backend.app.ml.district_product import flat_field  # noqa: E402

PHASE7 = ROOT / "backend/app/evidence_data/phase7"
PHASE9 = ROOT / "backend/app/evidence_data/phase9"
PROTOCOL = PHASE9 / "geoaware_protocol_v1.json"
FREEZE = PHASE9 / "geoaware_selection_freeze.json"
MODELS = ROOT / "experiments/geoaware_m5_v1/models"
SCHEMA = "phase9-geoaware-evaluation-v1"
BASELINES = ["M0", "M1", "M2", "M3", "M4"]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def load_module(name: str, relative: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


S2 = load_module("build_phase7_zone_stage2", "scripts/build_phase7_zone_stage2.py")
S1 = S2.S1
clean, encode, write_once = S1.clean, S1.encode, S1.write_once


def year_inputs(year: int) -> dict:
    """Base features, pixel, observation and case row ranges of the PAIRED cells of one evaluation year, in one common layout."""
    if year == 2024:
        base = op.PHASE4G_ROOT / "2024" / "validation" / "deterministic"
        cases = json.loads((base / "cases.json").read_text(encoding="utf-8"))
        return {"X": np.load(base / "X.npy", allow_pickle=False), "pixel": np.load(base / "pixel_index.npy", allow_pickle=False).astype(np.int64),
                "y": np.load(base / "y_mm.npy", allow_pickle=False).astype(np.float64),
                "ranges": {c["case_id"]: (c["row_start"], c["row_count"]) for c in cases}}
    if year == 2025:
        full = np.load(op.PHASE4G_ROOT / "2025" / "test_sealed" / "deterministic" / "X.npy", mmap_mode="r", allow_pickle=False)
        source = np.load(op.PHASE4J / "pairing" / "source_row_index.npy", allow_pickle=False)
        population = op._phase4j_population_by_case()
        return {"X": np.asarray(full[source]), "pixel": np.load(op.PHASE4J / "pairing" / "pixel_index.npy", allow_pickle=False).astype(np.int64),
                "y": np.load(op.PHASE4J / "pairing" / "observation_mm.npy", allow_pickle=False).astype(np.float64),
                "ranges": {cid: (p["row_start"], p["row_count"]) for cid, p in population.items()}}
    raise ValueError(year)


def predict_year(year: int, selected: dict, geography: dict) -> tuple[dict, dict]:
    inputs = year_inputs(year)
    X, pixel, ranges = inputs["X"], inputs["pixel"], inputs["ranges"]
    static_fields = {n: np.array([[np.nan if v is None else v for v in row] for row in geography["fields"][n]], dtype=np.float64).ravel() for n in ga.STATIC_FEATURES}
    static = ga.static_columns(static_fields, pixel)
    atmosphere, geometry = S2.Atmosphere(geography), S2.geometry_of(geography)
    case_ids = list(ranges)
    forcing_by_case = []
    for cid in case_ids:
        fields = atmosphere.track_b(cid, year)
        if any(np.isnan(f).any() for f in fields.values()):
            raise SystemExit(f"{cid}: forecast fields unavailable")
        c = zv.forcing_fields(fields["u850"], fields["v850"], fields["pwat"], geometry)
        forcing_by_case.append({"onshore_flux": c["onshore"], "cross_barrier_flux": c["cross_barrier"]})
    forcing = ga.forcing_columns([ranges[c] for c in case_ids], forcing_by_case, pixel, len(X))
    predictions = {}
    for arm, block in selected.items():
        model = XGBRegressor()
        model.load_model(str(MODELS / f"{arm}.json"))
        predictions[arm] = np.maximum(0.0, model.predict(ga.assemble(X, static, forcing, arm))).astype(np.float64)
    return inputs, predictions


def attach(data: dict, inputs: dict, predictions: dict) -> dict:
    """Add each arm's flat per-case fields next to the frozen M0-M4 fields, with a hard check that the cells and Raw agree."""
    arms = list(predictions)
    fields = {arm: [] for arm in arms}
    for i, cid in enumerate(data["case_ids"]):
        start, count = inputs["ranges"][cid]
        sl = slice(start, start + count)
        obs = flat_field(inputs["y"][sl], inputs["pixel"][sl])
        raw = flat_field(inputs["X"][sl, 0].astype(np.float64), inputs["pixel"][sl])
        if not np.array_equal(obs, data["obs"][i], equal_nan=True):
            raise SystemExit(f"{cid}: observations differ from the published population")
        if not np.allclose(raw, data["fields"]["M0"][i], equal_nan=True, rtol=0, atol=1e-6):
            raise SystemExit(f"{cid}: Raw differs from the published population")
        for arm in arms:
            fields[arm].append(flat_field(predictions[arm][sl], inputs["pixel"][sl]))
    return {arm: np.array(v) for arm, v in fields.items()}


def comparison_statistic(models: list[str], pairs: list[tuple[str, str]]):
    index = {m: i for i, m in enumerate(models)}

    def statistic(totals: np.ndarray, _models: list[str]) -> dict:
        out = {}
        for z, zone in enumerate(zv.ZONES):
            for arm, comparator in pairs:
                for metric in ("heavy_csi", "rmse", "bias", "heavy_fb", "very_heavy_csi"):
                    out[("cmp", zone, f"{arm}-{comparator}", metric)] = zv._metric(totals[z, index[arm]], metric) - zv._metric(totals[z, index[comparator]], metric)
        return out
    return statistic


def analyse(year: int, data: dict, arm_fields: dict, stage1: dict, protocol: dict, freeze: dict, masks: dict) -> dict:
    models = BASELINES + list(arm_fields)
    n = len(data["case_ids"])
    stats = np.stack([zv.case_stats(data["obs"][i], {**{m: data["fields"][m][i] for m in BASELINES}, **{a: arm_fields[a][i] for a in arm_fields}}, masks) for i in range(n)])
    totals = stats.sum(axis=0)
    cell_counts = {z: int(masks[z].sum()) for z in zv.ZONES}
    gate = zv.support(stats, cell_counts)

    worst = 0.0                                                # reproduction gate: the published M0-M4 numbers must come back exactly
    for zone in zv.ZONES:
        for m in BASELINES:
            mine, ref = zv.metrics(totals[zv.ZONES.index(zone), models.index(m)]), stage1["pooled"][zone][m]
            if "rmse_mm" not in ref:
                continue
            if mine["cell_count"] != ref["cell_count"]:
                raise SystemExit(f"{year}/{zone}/{m}: cell count differs from the published evidence")
            worst = max(worst, abs(mine["rmse_mm"] - ref["rmse_mm"]), abs(mine["bias_mm"] - ref["bias_mm"]))
            ref_h = ref["categorical"].get("heavy", {})
            if "hits" in ref_h and any(mine["categorical"]["heavy"][k] != ref_h[k] for k in ("hits", "misses", "false_alarms")):
                raise SystemExit(f"{year}/{zone}/{m}: heavy counts differ from the published evidence")
    if worst > 1e-9:
        raise SystemExit(f"{year}: M0-M4 do not reproduce the published zone evidence (max abs diff {worst})")

    pooled = {}
    for zi, zone in enumerate(zv.ZONES):
        pooled[zone] = {}
        for mi, m in enumerate(models):
            block = zv.metrics(totals[zi, mi])
            if not gate[zone]["continuous_supported"]:
                block = {"cell_count": block["cell_count"], "status": "insufficient_support"}
            else:
                for name, _ in zv.THRESHOLDS:
                    if not gate[zone][name]["supported"]:
                        block["categorical"][name] = {"status": "insufficient_support", "observed_event_pairs": gate[zone][name]["observed_event_pairs"]}
            pooled[zone][m] = block

    arms = list(arm_fields)
    pairs = [(a_, c) for a_ in arms for c in ("M2", "M0")]
    if "A3" in arms and "A0" in arms:
        pairs.append(("A3", "A0"))
    pairs += [(a_, "A0") for a_ in arms if a_ not in ("A0", "A3") and "A0" in arms]
    if "A3" in arms and "A1" in arms:
        pairs.append(("A3", "A1"))                 # diagnostic: does forecast forcing add anything beyond static geography?
    pairs = list(dict.fromkeys(pairs))
    boot = zv.paired_bootstrap(stats, models, statistic=comparison_statistic(models, pairs))
    comparisons = {}
    for (_, zone, pair, metric), value in boot.items():
        heavy = metric in ("heavy_csi", "heavy_fb")
        very = metric == "very_heavy_csi"
        ok = gate[zone]["continuous_supported"] and (not heavy or gate[zone]["heavy"]["supported"]) and (not very or gate[zone]["very_heavy"]["supported"])
        comparisons.setdefault(zone, {}).setdefault(pair, {})[metric] = value if ok else {"status": "insufficient_support", "point": None}

    by_lead = {}
    leads = np.array([int(c.split("day")[1][0]) for c in data["case_ids"]])
    for day in (1, 2, 3):
        sub = stats[leads == day].sum(axis=0)
        by_lead[f"day{day}"] = {"cases": int((leads == day).sum()), "models": {m: zv.metrics(sub[zv.ZONES.index("ALL"), mi]) for mi, m in enumerate(models)}}

    raw_csi = zv.metrics(totals[zv.ZONES.index("ALL"), models.index("M0")])["categorical"]["heavy"]["CSI"]
    def for_guardrails(summary: dict) -> dict:
        return {"bias_mm": summary["bias_mm"], "heavy": {"csi": summary["categorical"]["heavy"]["CSI"]}, "very_heavy": {"frequency_bias": summary["categorical"]["very_heavy"]["frequency_bias"]}}
    guard = {a: ga.guardrails(for_guardrails(zv.metrics(totals[zv.ZONES.index("ALL"), models.index(a)])), raw_csi) for a in arms}
    return {"schema": SCHEMA, "track": "B", "year": year, "evidence_role": S1.ROLES[("B", year)], "case_count": n, "models": models,
            "protocol_sha256": sha256_file(PROTOCOL), "selection_freeze_sha256": sha256_file(FREEZE),
            "zones": {z: {"cells": cell_counts[z], "in_decision_rule": z in zv.PRE_REGISTERED_ZONES} for z in zv.ZONES}, "support": gate, "pooled": pooled,
            "comparisons": comparisons, "by_lead_all_cells": by_lead, "guardrails_on_evaluation_population": guard,
            "bootstrap": {"method": "paired whole-case bootstrap", "repeats": zv.REPEATS, "seed": zv.SEED, "note": "optimistic; cells in a case are correlated and consecutive days serially correlated"},
            "reproduction": {"status": "REPRODUCED", "m0_to_m4_equal_published_zone_evidence_max_abs_diff": worst, "stage1_file": f"zone_verification_B_{year}.json"},
            "fss": {"status": "not_reported", "reason": S1.FSS_TEXT},
            "limits": protocol["governance"]["limits_stated_on_every_output"]}


def decide(results: dict, freeze: dict, protocol: dict) -> dict:
    """The pre-registered decision rule (protocol decision_rule), applied literally."""
    a3 = freeze["selection"]["A3"]["selected"]
    out = {"rule": protocol["decision_rule"], "candidate": "A3", "candidate_selected": a3 is not None}
    if a3 is None:
        out.update({"adds_value": False, "reason": "A3 had no configuration passing the guardrails on the 2023 out-of-fold predictions, so there is no candidate to evaluate",
                    "geography_attribution": None, "coverage_status_consequence": "stays PARTIAL"})
        return out
    zone = "COASTAL_AND_OROGRAPHIC"
    per_year = {}
    for year, r in results.items():
        csi = r["comparisons"][zone]["A3-M2"]["heavy_csi"]
        rmse = r["comparisons"]["ALL"]["A3-M2"]["rmse"]
        csi_a0 = r["comparisons"][zone].get("A3-A0", {}).get("heavy_csi")
        guard = r["guardrails_on_evaluation_population"].get("A3", {})
        per_year[year] = {
            "heavy_csi_zone_A3_minus_M2": csi, "overall_rmse_A3_minus_M2": rmse, "heavy_csi_zone_A3_minus_A0": csi_a0, "guardrails_G1_G2_G3": guard,
            "csi_beats_M2": csi.get("status") == "ok" and csi["point"] > 0 and csi["excludes_zero"],
            "rmse_within_tolerance": rmse.get("status") == "ok" and rmse["point"] <= 0.2,
            "guardrails_pass": bool(guard) and all(guard.values()),
            "beats_control_A0": csi_a0 is not None and csi_a0.get("status") == "ok" and csi_a0["point"] > 0 and csi_a0["excludes_zero"],
        }
    y24, y25 = per_year[2024], per_year[2025]
    control_missing = freeze["selection"].get("A0", {}).get("selected") is None
    sign_agrees = y24["heavy_csi_zone_A3_minus_M2"].get("point") is not None and y25["heavy_csi_zone_A3_minus_M2"].get("point") is not None \
        and y24["heavy_csi_zone_A3_minus_M2"]["point"] * y25["heavy_csi_zone_A3_minus_M2"]["point"] > 0
    adds = bool(y24["csi_beats_M2"] and y24["rmse_within_tolerance"] and y24["guardrails_pass"] and sign_agrees)
    out.update({"per_year": per_year, "sign_agrees_2024_2025": bool(sign_agrees), "adds_value": adds,
                "geography_attribution": (None if not adds else ("undetermined" if control_missing else ("geography" if y24["beats_control_A0"] else "training recipe"))),
                "protocol_gap": ("The protocol attributes a gain to geography only if A3 beats the internal control A0, but it did not anticipate that A0 could have no configuration passing the guardrails; "
                                 "the comparison then cannot be made and attribution is recorded as undetermined rather than forced.") if control_missing else None,
                "coverage_status_consequence": "stays PARTIAL; a development-evidence candidate only" if adds else "stays PARTIAL; no evidence that geography-aware features improve on M2",
                "wording": "a candidate that improves on M2 in development evidence" if adds else "no evidence that geography-aware features improve on M2"})
    return out


def main() -> None:
    protocol = json.loads(PROTOCOL.read_text(encoding="utf-8"))
    if not FREEZE.exists():
        raise SystemExit("no selection freeze: run scripts/train_geoaware_m5.py first (2024 and 2025 must not be touched before it)")
    freeze = json.loads(FREEZE.read_text(encoding="utf-8"))
    if freeze["protocol_sha256"] != sha256_file(PROTOCOL) or (PHASE9 / "geoaware_selection_freeze.sha256").read_text(encoding="ascii").split()[0] != sha256_file(FREEZE):
        raise SystemExit("the freeze does not match the protocol")
    selected = {arm: block["selected"] for arm, block in freeze["selection"].items() if block["selected"]}
    for arm, block in selected.items():
        if sha256_file(MODELS / f"{arm}.json") != block["model_sha256"]:
            raise SystemExit(f"model {arm} does not match the freeze")
    geography = json.loads((PHASE7 / "static_geography_v1.json").read_text(encoding="utf-8"))
    masks = zv.zone_masks(geography["fields"]["zone"])
    results, files = {}, {}
    if not selected:
        # The frozen rule allows "no configuration passes the guardrails". That is a result, not an error: 2024 and 2025 are never opened.
        decision = decide({}, freeze, protocol)
        files["geoaware_decision.json"] = {"sha256": write_once(PHASE9 / "geoaware_decision.json", encode(decision)), "evidence_role": "PRE_REGISTERED_RULE_NO_CANDIDATE", "year": None, "cases": None, "reproduction": "n/a"}
        manifest = {"schema": "phase9-geoaware-manifest-v1", "protocol_sha256": sha256_file(PROTOCOL), "selection_freeze_sha256": sha256_file(FREEZE), "files": files,
                    "notes": ["No arm had a configuration that passed the guardrails on the 2023 out-of-fold predictions; no evaluation-year prediction was made.",
                              "Development-only (option D1(b)); no frozen M0-M4 artifact, feature registry v1 or earlier protocol was modified."]}
        digest = write_once(PHASE9 / "geoaware_manifest.json", encode(manifest))
        (PHASE9 / "geoaware_manifest.sha256").write_text(digest + "\n", encoding="ascii")
        print("no candidate:", decision["reason"])
        return
    for year in (2024, 2025):
        data = S1.load_track_b(year)
        stage1 = json.loads((PHASE7 / f"zone_verification_B_{year}.json").read_text(encoding="utf-8"))
        inputs, predictions = predict_year(year, selected, geography)
        arm_fields = attach(data, inputs, predictions)
        result = analyse(year, data, arm_fields, stage1, protocol, freeze, masks)
        results[year] = result
        name = f"geoaware_evaluation_B_{year}.json"
        files[name] = {"sha256": write_once(PHASE9 / name, encode(result)), "year": year, "evidence_role": result["evidence_role"], "cases": result["case_count"], "reproduction": "REPRODUCED"}
        print(f"{year}: {result['case_count']} cases, M0-M4 reproduce the published zone evidence -> {name}", flush=True)
    decision = decide(results, freeze, protocol)
    files["geoaware_decision.json"] = {"sha256": write_once(PHASE9 / "geoaware_decision.json", encode(decision)), "evidence_role": "PRE_REGISTERED_RULE_DEVELOPMENT_PLUS_POST_HOC", "year": None, "cases": None, "reproduction": "n/a"}
    manifest = {"schema": "phase9-geoaware-manifest-v1", "protocol_sha256": sha256_file(PROTOCOL), "selection_freeze_sha256": sha256_file(FREEZE), "files": files,
                "notes": ["Development-only (option D1(b)): no independent test exists; 2024 is a reused development year; 2025 is a post-hoc analysis of a completed final test.",
                          "No frozen M0-M4 artifact, feature registry v1 or earlier protocol was modified.", "Operational-era track only; historical replay, not warning skill."]}
    data = encode(manifest)
    digest = write_once(PHASE9 / "geoaware_manifest.json", data)
    (PHASE9 / "geoaware_manifest.sha256").write_text(digest + "\n", encoding="ascii")
    print("adds_value:", decision.get("adds_value"), "|", decision.get("wording") or decision.get("reason"))


if __name__ == "__main__":
    main()
