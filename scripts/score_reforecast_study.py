"""Score the frozen reforecast models and regime classifiers on the sealed years 2014-2016, ONCE (docs/142). Needs the unseal record and the paired / labelled sealed files.

    python scripts/score_reforecast_study.py

Verifies every hash (protocol, selection freezes, model files, unseal record), applies the frozen artifacts without any change, writes write-once evidence under backend/app/evidence_data/phase15/ and a manifest.
"""

from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from xgboost import XGBClassifier, XGBRegressor  # noqa: E402

from backend.app.ml import reforecast_study as rs  # noqa: E402
from backend.app.ml import regime_tasks as rt  # noqa: E402
from backend.app.ml import zone_verification as zv  # noqa: E402

PHASE15 = ROOT / "backend/app/evidence_data/phase15"
PROC = ROOT / "data/processed/reforecast_control_v1"
TASKS = ROOT / "data/processed/regime_tasks_v1"
MODELS = ROOT / "experiments/reforecast_study_v1/models"
LABEL = "POST-UNSEAL SEALED TEST 2014-2016: first use of these years"
ROLE = "REFORECAST_SEALED_TEST_2014_2016_FIRST_USE"
S = zv.S
PAIRS = (("B0", "M0"), ("B1", "M0"), ("R_soft", "M0"), ("R_hard", "M0"), ("R_soft", "B0"), ("R_hard", "B0"), ("E_B0_h", "M0"), ("E_B0_vh", "M0"), ("E_B1_h", "M0"), ("E_B1_vh", "M0"))
PAIR_METRICS = {"E_B0_h": ("heavy_csi",), "E_B1_h": ("heavy_csi",), "E_B0_vh": ("very_heavy_csi",), "E_B1_vh": ("very_heavy_csi",)}


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def clean(v):
    if isinstance(v, dict):
        return {str(k) if not isinstance(k, str) else k: clean(x) for k, x in v.items()}
    if isinstance(v, (list, tuple)):
        return [clean(x) for x in v]
    if isinstance(v, (np.floating, float)):
        return None if not np.isfinite(v) else float(v)
    if isinstance(v, np.integer):
        return int(v)
    if isinstance(v, np.bool_):
        return bool(v)
    return v


def write_once(path: Path, value) -> str:
    data = (json.dumps(clean(value), sort_keys=True, indent=2, ensure_ascii=False, allow_nan=False) + "\n").encode("utf-8")
    if path.exists() and path.read_bytes() != data:
        raise SystemExit(f"frozen evidence would change: {path}")
    path.write_bytes(data)
    return hashlib.sha256(data).hexdigest()


def verify() -> dict:
    files = {"protocol": "reforecast_study_protocol_v1.json", "selection": "reforecast_selection_freeze.json", "regime_tasks": "regime_tasks_selection_freeze.json", "exceedance": "reforecast_exceedance_freeze.json", "unseal": "reforecast_unseal_record.json"}
    shas = {}
    for key, name in files.items():
        path = PHASE15 / name
        if not path.exists() or path.with_suffix(".sha256").read_text(encoding="ascii").split()[0] != sha(path):
            raise SystemExit(f"{name} is missing or differs from its sidecar")
        shas[key] = sha(path)
    record = json.loads((PHASE15 / files["unseal"]).read_text(encoding="utf-8"))
    if record["protocol_sha256"] != shas["protocol"] or record["selection_freeze_sha256"] != shas["selection"] or record["regime_tasks_freeze_sha256"] != shas["regime_tasks"] or record["exceedance_freeze_sha256"] != shas["exceedance"]:
        raise SystemExit("the unseal record does not match the frozen files")
    for name, digest in record["model_files_sha256"].items():
        if sha(MODELS / name) != digest:
            raise SystemExit(f"model file {name} differs from the unseal record")
    return {"shas": shas, "protocol": json.loads((PHASE15 / files["protocol"]).read_text(encoding="utf-8")), "selection": json.loads((PHASE15 / files["selection"]).read_text(encoding="utf-8")),
            "tasks": json.loads((PHASE15 / files["regime_tasks"]).read_text(encoding="utf-8")), "exceedance": json.loads((PHASE15 / files["exceedance"]).read_text(encoding="utf-8"))}


def stat_fn(models: list[str]):
    def statistic(totals: np.ndarray, _models: list[str]) -> dict:
        idx = {m: i for i, m in enumerate(models)}
        out = {}
        for a, b in PAIRS:
            if a in idx and b in idx:
                for metric in PAIR_METRICS.get(a, ("rmse", "heavy_csi", "very_heavy_csi")):
                    out[(a, b, metric)] = zv._metric(totals[idx[a]], metric) - zv._metric(totals[idx[b]], metric)
        return out
    return statistic


def score_r05(ctx: dict) -> dict:
    spec = ctx["protocol"]["r05"]["model_spec"]
    sel = ctx["selection"]
    years = rs.SEALED_YEARS
    xs, ys, pixels, case_ids, meta, regime = [], [], [], [], [], []
    for year in years:
        folder = PROC / str(year)
        pairs = json.loads((folder / "pairs.json").read_text(encoding="utf-8"))
        x, y, pixel = np.load(folder / "X.npy", allow_pickle=False), np.load(folder / "y_mm.npy", allow_pickle=False), np.load(folder / "pixel_index.npy", allow_pickle=False)
        rows = np.load(folder / "regime_rows.npy", allow_pickle=False)
        regime.append(np.load(folder / "regime_X.npy", allow_pickle=False)[rows])
        for c in pairs["cases"]:
            meta.append({**c, "year": year})
        xs.append(x), ys.append(y), pixels.append(pixel.astype(np.int64))
    X, y, pixel = np.concatenate(xs), np.concatenate(ys), np.concatenate(pixels)
    regime = np.concatenate(regime)
    counts = np.array([m["row_count"] for m in meta])
    starts = np.concatenate([[0], np.cumsum(counts)[:-1]])
    geography = json.loads((ROOT / "backend/app/evidence_data/phase7/static_geography_v1.json").read_text(encoding="utf-8"))
    from backend.app.ml.geoaware import static_columns
    static_fields = {n: np.array([[np.nan if v is None else v for v in row] for row in geography["fields"][n]], dtype=np.float64).ravel() for n in rs.STATIC_FEATURES}
    static = static_columns(static_fields, pixel)
    full = np.concatenate([X, static], axis=1)
    names = list(rs.BASE_FEATURES) + list(rs.STATIC_FEATURES)
    pred = {"M0": X[:, 0].astype(np.float32)}
    fitted = {}
    for arm in rs.ARMS:
        if sel["models"].get(arm):
            m = XGBRegressor()
            m.load_model(str(MODELS / sel["models"][arm]["file"]))
            fitted[arm] = m
            pred[arm] = np.maximum(0.0, m.predict(full[:, [names.index(f) for f in rs.ARMS[arm]]].astype(np.float32))).astype(np.float32)
    regime_block = None
    if "regime_arms" in sel["models"] and "B0" in fitted:
        ra = json.loads((MODELS / "regime_arms.json").read_text(encoding="utf-8"))
        c = ra["classifier"]
        z = (regime - np.array(c["mean"])) / np.array(c["scale"])
        logits = z @ np.array(c["coef"]).T + np.array(c["intercept"])
        logits -= logits.max(axis=1, keepdims=True)
        probs = np.exp(logits) / np.exp(logits).sum(axis=1, keepdims=True)
        B0 = full[:, [names.index(f) for f in rs.ARMS["B0"]]].astype(np.float32)
        experts = {}
        for r in (0, 1, 2):
            if ra["fallback"][str(r)]:
                experts[r] = pred["B0"]
            else:
                m = XGBRegressor()
                m.load_model(str(MODELS / f"expert_regime_{r}.json"))
                experts[r] = np.maximum(0.0, m.predict(B0)).astype(np.float32)
        pred["R_hard"], pred["R_soft"] = rs.route_hard(probs, experts, counts), rs.route_soft(probs, experts, counts)
        pseudo = rs.pseudo_labels(regime, ra["rule"])
        regime_block = {"fallback": ra["fallback"], "training_label_counts": ra["training_label_counts"], "test_case_pseudo_labels": {str(r): int((pseudo == r).sum()) for r in (0, 1, 2)}}
    cat, exceed_report = {}, {}
    exc = ctx["exceedance"]
    for arm in rs.ARMS:
        arm_X = full[:, [names.index(f) for f in rs.ARMS[arm]]].astype(np.float32)
        for name, suffix in (("heavy", "h"), ("very_heavy", "vh")):
            key = f"{arm}:{name}"
            chosen = exc["selection"].get(key)
            if not chosen:
                continue
            clf = XGBClassifier()
            clf.load_model(str(MODELS / exc["models"][key]["file"]))
            prob = clf.predict_proba(arm_X)[:, 1].astype(np.float64)
            T = rs.EXCEED_THRESHOLDS[name]
            event = y.astype(np.float32) >= np.float32(T)
            cat[f"E_{arm}_{suffix}"] = np.where(prob >= chosen["tau"], T, 0.0).astype(np.float32)
            exceed_report[key] = {"config": chosen["config"], "tau": chosen["tau"], "validation": chosen["validation"], "test": rs.exceedance_metrics(prob, y, chosen["tau"], T), "auc": rt.auc(prob, event),
                                  "brier_score": float(np.mean((prob - event) ** 2)), "base_rate": float(event.mean())}
    for k, v in pred.items():
        if v.shape != y.shape or not np.isfinite(v).all() or (v < 0).any():
            raise SystemExit(f"{k}: prediction bounds failure")
    models = list(pred) + list(cat)
    pooled = {m: rs.pooled_metrics(y, pred[m]) for m in pred}
    mask = np.ones(2401, dtype=bool)
    per_case = np.zeros((len(meta), len(models), S))
    for i, c in enumerate(meta):
        sl = slice(starts[i], starts[i] + counts[i])
        obs = np.full(2401, np.nan)
        obs[pixel[sl]] = y[sl]
        fields = {}
        for m in models:
            f = np.full(2401, np.nan)
            f[pixel[sl]] = (pred[m] if m in pred else cat[m])[sl]
            fields[m] = f
        per_case[i] = zv.case_stats(obs, fields, {"ALL": mask}, names=("ALL",))[0]
    if not np.isclose(per_case[:, 0, 3].sum(), (((pred["M0"] - y) ** 2).sum())):
        raise SystemExit("reproduction gate failed: case statistics do not add up to the pooled error")
    dates = sorted({m["initialization"] for m in meta})
    date_stack = np.stack([per_case[[i for i, m in enumerate(meta) if m["initialization"] == d]].sum(axis=0) for d in dates])
    fn = stat_fn(models)
    b95 = zv.paired_bootstrap(date_stack, models, statistic=fn, repeats=2000, seed=26080, level=0.95)
    b975 = zv.paired_bootstrap(date_stack, models, statistic=fn, repeats=2000, seed=26080, level=0.975)

    def entry(a, b, metric, table):
        e = table.get((a, b, metric))
        if e is None:
            return None
        e = dict(e)
        e["interval95"] = e.pop("interval", e.get("interval95"))
        return e
    support = {t: int(pooled["M0"][t]["observed_events"]) for t in ("heavy", "very_heavy")}
    supported = {t: n >= 30 for t, n in support.items()}
    decisions, bundles = {}, {}
    for arm in ("B0", "B1"):
        if arm in pred:
            vs = {"rmse": entry(arm, "M0", "rmse", b95), "heavy_csi": entry(arm, "M0", "heavy_csi", b975) if supported["heavy"] else None,
                  "very_heavy_csi": entry(arm, "M0", "very_heavy_csi", b975) if supported["very_heavy"] else None}
            decisions[arm] = {"vs_raw": vs, "decision": rs.decide_candidate(vs, pooled[arm])}
        h, v = exceed_report.get(f"{arm}:heavy"), exceed_report.get(f"{arm}:very_heavy")
        if arm in pred and h and v:
            vs = {"rmse": entry(arm, "M0", "rmse", b95), "heavy_csi": entry(f"E_{arm}_h", "M0", "heavy_csi", b975) if supported["heavy"] else None,
                  "very_heavy_csi": entry(f"E_{arm}_vh", "M0", "very_heavy_csi", b975) if supported["very_heavy"] else None}
            like = {"bias_mm": pooled[arm]["bias_mm"], "heavy": {"frequency_bias": h["test"]["frequency_bias"]}, "very_heavy": {"frequency_bias": v["test"]["frequency_bias"]}}
            bundles[arm] = {"vs_raw": vs, "decision": rs.decide_candidate(vs, like), "components": "RMSE and bias from the regression arm; heavy and very-heavy CSI from the exceedance classifiers (protocol amendment 2)"}
    regime_decisions = {}
    for arm in ("R_soft", "R_hard"):
        if arm in pred:
            vs = {"rmse": entry(arm, "B0", "rmse", b95), "heavy_csi": entry(arm, "B0", "heavy_csi", b975)}
            vs_raw = {"rmse": entry(arm, "M0", "rmse", b95), "heavy_csi": entry(arm, "M0", "heavy_csi", b975), "very_heavy_csi": entry(arm, "M0", "very_heavy_csi", b975)}
            regime_decisions[arm] = {"vs_b0": vs, "adds_value": rs.regime_adds_value(vs), "vs_raw": vs_raw, "decision_vs_raw": rs.decide_candidate(vs_raw, pooled[arm])}
    by_lead = {p: {m: rs.pooled_metrics(y[np.repeat([c["product"] == p for c in meta], counts)], pred[m][np.repeat([c["product"] == p for c in meta], counts)]) for m in pred} for p in ("day1_24h", "day2_24h", "day3_24h")}
    by_year = {str(yr): {m: rs.pooled_metrics(y[np.repeat([c["year"] == yr for c in meta], counts)], pred[m][np.repeat([c["year"] == yr for c in meta], counts)]) for m in pred} for yr in years}
    intervals = {f"{a}|{b}|{metric}": {"level_0.95": entry(a, b, metric, b95), "level_0.975": entry(a, b, metric, b975)} for a, b in PAIRS if (a in pred or a in cat) and b in pred for metric in PAIR_METRICS.get(a, ("rmse", "heavy_csi", "very_heavy_csi"))}
    return {"schema": "reforecast-r05-evidence-v1", "evidence_role": ROLE, "label": LABEL, "protocol_sha256": ctx["shas"]["protocol"], "unseal_record_sha256": ctx["shas"]["unseal"], "years": list(years),
            "cases": len(meta), "initialization_dates": len(dates), "rows": int(len(y)), "pooled": pooled, "support": {"observed_event_pairs": support, "supported": supported},
            "selected_configurations": {a: sel["models"][a]["config"] for a in rs.ARMS if sel["models"].get(a)}, "decisions": decisions, "bundle_decisions": bundles, "exceedance": exceed_report, "raw_categorical": {t: {k: pooled["M0"][t][k] for k in ("hits", "misses", "false_alarms", "csi", "frequency_bias")} for t in ("heavy", "very_heavy")}, "regime_decisions": regime_decisions, "regime_arms": regime_block,
            "paired_intervals": intervals, "by_lead": by_lead, "by_year": by_year,
            "bootstrap": {"repeats": 2000, "seed": 26080, "unit": "initialization date", "note": "optimistic: consecutive dates are correlated; 97.5 percent intervals for the two CSI differences, 95 percent for RMSE"},
            "reproduction": {"status": "REPRODUCED", "checks": ["every model and freeze hash matched the unseal record", "per-case statistics add up to the pooled squared error", "M0 equals the raw forecast column"]}}


def score_r03(ctx: dict) -> dict:
    spec = ctx["tasks"]
    names = spec["feature_names"]
    F, Y, meta = [], [], []
    for year in rs.SEALED_YEARS:
        m = json.loads((TASKS / f"features_{year}.json").read_text(encoding="utf-8"))
        F.append(np.load(TASKS / f"features_{year}.npy", allow_pickle=False))
        Y.append(np.load(TASKS / f"tasks_Y_{year}.npy", allow_pickle=False))
        meta += [{**c, "year": year} for c in m["cases"]]
    F, Y = np.concatenate(F), np.concatenate(Y)
    base_cols = [names.index(c) for c in spec["baseline_columns"]]
    out_tasks = {}
    for j, task in enumerate(rt.TASKS):
        block = spec["tasks"][task]
        defined = Y[:, j] >= 0
        label = Y[defined, j].astype(bool)
        record = {"cases": int(defined.sum()), "positives": int(label.sum()), "negatives": int((~label).sum()), "validation": {k: block.get(k) for k in ("validation_auc", "validation_balanced_accuracy", "C", "operating_threshold")}}
        if block["status"] != "FITTED" or not rt.supported(label):
            record.update({"tier": "INSUFFICIENT_SUPPORT", "validated": False, "useful": False, "reason": block.get("status") if block["status"] != "FITTED" else "fewer than 30 positive or 30 negative sealed-test cases"})
            out_tasks[task] = record
            continue
        model = {k: np.array(v) if isinstance(v, list) else v for k, v in block["model"].items()}
        bmodel = {k: np.array(v) if isinstance(v, list) else v for k, v in block["baseline_model"].items()}
        score = rt.score_logistic(model, F[defined])
        bscore = rt.score_logistic(bmodel, F[defined][:, base_cols])
        predicted = score >= block["operating_threshold"]
        clusters = [meta[i]["initialization"] for i in np.flatnonzero(defined)]
        stats = rt.bootstrap(score, bscore, label, predicted, clusters)
        record.update({"auc": stats["auc"], "balanced_accuracy": stats["balanced_accuracy"], "auc_over_baseline": stats["auc_over_baseline"], "baseline_auc": rt.auc(bscore, label),
                       "confusion": rt.confusion(predicted, label), "chance_balanced_accuracy": 0.5, **rt.verdict(stats, True)})
        by_lead = {}
        for p in ("day1_24h", "day2_24h", "day3_24h"):
            sel = np.array([meta[i]["product"] == p for i in np.flatnonzero(defined)])
            by_lead[p] = {"cases": int(sel.sum()), "auc": rt.auc(score[sel], label[sel])}
        record["by_lead"] = by_lead
        out_tasks[task] = record
    return {"schema": "reforecast-r03-evidence-v1", "evidence_role": ROLE, "label": LABEL, "protocol_sha256": ctx["shas"]["protocol"], "unseal_record_sha256": ctx["shas"]["unseal"],
            "years": list(rs.SEALED_YEARS), "label_nature": "objective rule-based labels (IMD and ERA5-derived), relative by construction; not expert analyses; the western-disturbance label compares a forecast trough with a reanalysis trough",
            "tasks": out_tasks, "bootstrap": {"repeats": 2000, "seed": 26080, "unit": "initialization date", "note": "optimistic"}}


def main() -> int:
    ctx = verify()
    files = {}
    for name, fn in (("reforecast_r05_test.json", score_r05), ("reforecast_r03_test.json", score_r03)):
        result = fn(ctx)
        files[name] = {"sha256": write_once(PHASE15 / name, result), "evidence_role": ROLE}
        print("wrote", name, flush=True)
    manifest = {"schema": "reforecast-manifest-v1", "protocol_sha256": ctx["shas"]["protocol"], "selection_freeze_sha256": ctx["shas"]["selection"], "regime_tasks_freeze_sha256": ctx["shas"]["regime_tasks"], "exceedance_freeze_sha256": ctx["shas"]["exceedance"],
                "unseal_record_sha256": ctx["shas"]["unseal"], "files": files, "scored_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds")}
    digest = write_once(PHASE15 / "reforecast_manifest.json", manifest)
    (PHASE15 / "reforecast_manifest.sha256").write_text(digest + "\n", encoding="ascii", newline="\n")
    print("manifest sha256", digest)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
