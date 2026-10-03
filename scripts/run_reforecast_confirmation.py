"""Round 2 of the reforecast study (protocol amendment 3, docs/142): a confirmatory test of the frozen B1 bundle on 2017-2019.

    python scripts/run_reforecast_confirmation.py unseal   # writes the signed record BEFORE any 2017-2019 observation is read
    python scripts/run_reforecast_confirmation.py score    # applies the frozen models (no refit) with the one added parameter delta, pairs 2017-2019 with IMD in memory, scores once

The bundle is the frozen B1 regression (its output reduced by delta, the pooled mean error of that model on 2014-2016, and clipped at zero) plus the frozen B1 exceedance classifiers and their probability thresholds.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import numpy as np
from scipy.io import netcdf_file

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from xgboost import XGBClassifier, XGBRegressor  # noqa: E402

from backend.app.ml import reforecast_study as rs  # noqa: E402
from backend.app.ml import zone_verification as zv  # noqa: E402
from backend.app.ml.geoaware import static_columns  # noqa: E402

PHASE15 = ROOT / "backend/app/evidence_data/phase15"
PROC = ROOT / "data/processed/reforecast_control_v1"
MODELS = ROOT / "experiments/reforecast_study_v1/models"
YEARS = (2017, 2018, 2019)
IMD = {2017: "49786e2d2b661c5d3bcfb3ffd90385c1133ec27a8a04bf272ff2df5029106a9c", 2018: "26bd53aeb2d6f3f7d39516c41606db005dede474906b33462d1a0caef69cd6ec", 2019: "c551c563b3514d492a2de94c706c1c254d5826656738b4a8e7dbd83841344a5b"}
RECORD = PHASE15 / "reforecast_confirmation_unseal_record.json"
EVIDENCE = PHASE15 / "reforecast_r05_confirmation.json"
MANIFEST = PHASE15 / "reforecast_confirmation_manifest.json"
ROLE = "REFORECAST_CONFIRMATORY_TEST_2017_2019"
LABEL = "CONFIRMATORY TEST 2017-2019: no model of this study used these years (earlier Track A experiments did)"
OFFSET = {"day1_24h": 1, "day2_24h": 2, "day3_24h": 3}
S = zv.S


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


def sidecar_ok(path: Path) -> bool:
    if not path.exists():
        return False
    side = path.with_suffix(".sha256")
    if side.exists():
        return side.read_text(encoding="ascii").split()[0] == sha(path)
    manifest = json.loads((PHASE15 / "reforecast_manifest.json").read_text(encoding="utf-8"))          # a result file is pinned by the round-1 manifest, whose own sidecar is checked
    return path.name in manifest["files"] and manifest["files"][path.name]["sha256"] == sha(path)


def unseal(message: str) -> int:
    if RECORD.exists():
        raise SystemExit("a confirmation record already exists")
    names = ("reforecast_study_protocol_v1.json", "reforecast_selection_freeze.json", "reforecast_exceedance_freeze.json", "reforecast_protocol_v1_amendment_3.json", "reforecast_r05_test.json", "reforecast_manifest.json")
    for n in names:
        if not sidecar_ok(PHASE15 / n):
            raise SystemExit(f"{n} is missing or differs from its sidecar")
    for y in YEARS:
        if not (PROC / str(y) / "X_full.npy").exists() or (PROC / str(y) / "y_mm.npy").exists() or EVIDENCE.exists():
            raise SystemExit(f"forecast side for {y} missing, or an observation-paired file already exists")
    exc = json.loads((PHASE15 / "reforecast_exceedance_freeze.json").read_text(encoding="utf-8"))
    models = {"B1.json": sha(MODELS / "B1.json"), **{b["file"]: sha(MODELS / b["file"]) for k, b in exc["models"].items() if k.startswith("B1:")}}
    record = {"schema": "reforecast-confirmation-record-v1", "written_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"), "years": list(YEARS),
              "hashes": {n: sha(PHASE15 / n) for n in names}, "model_files_sha256": models, "written_before_any_2017_2019_observation_was_read_for_this_study": True,
              "owner_message": {"verbatim": message, "date": "2026-10-03"}, "label": LABEL,
              "what_is_authorised": ["pairing the 2017-2019 forecast-side corpus with IMD in memory", "scoring the frozen B1 bundle once with the one added parameter delta", "writing the evidence file"],
              "what_is_not_authorised": ["any refit, re-selection or change of a threshold, tau or rule", "a second scoring run with different settings", "using 2017-2019 for any fitting"],
              "disclosed_before_opening": ["round 1 failed only the mean-error guardrail (docs/142)", "delta is read from the round-1 evidence file, not tuned on these years"]}
    RECORD.write_bytes((json.dumps(record, indent=2, sort_keys=True) + "\n").encode("utf-8"))
    RECORD.with_suffix(".sha256").write_text(sha(RECORD) + "  reforecast_confirmation_unseal_record.json\n", encoding="ascii")
    print("confirmation record written", sha(RECORD))
    return 0


def imd_year(year: int):
    path = ROOT / f"data/raw/observations/imd/{year}/RF25_ind{year}_rfp25.nc"
    if sha(path) != IMD[year]:
        raise SystemExit(f"IMD file hash mismatch: {year}")
    with netcdf_file(path, "r", mmap=False) as ds:
        times = np.asarray(ds.variables["TIME"].data, dtype=np.float64)
        origin = date.fromisoformat(ds.variables["TIME"].units.decode().split("since ")[1].strip()[:10])
        lat, lon = np.asarray(ds.variables["LATITUDE"].data, dtype=np.float64), np.asarray(ds.variables["LONGITUDE"].data, dtype=np.float64)
        rain = np.asarray(ds.variables["RAINFALL"].data, dtype=np.float64)
        fill = float(ds.variables["RAINFALL"]._attributes["_FillValue"])
    li, lj = np.flatnonzero((lat >= 10) & (lat <= 22)), np.flatnonzero((lon >= 68) & (lon <= 80))
    if (len(li), len(lj)) != (49, 49):
        raise SystemExit("IMD box is not 49 by 49")
    return {origin + timedelta(days=int(t)): i for i, t in enumerate(times)}, rain[:, li[0]: li[-1] + 1, lj[0]: lj[-1] + 1], fill


def score() -> int:
    if not sidecar_ok(RECORD):
        raise SystemExit("the confirmation record is missing or differs from its sidecar")
    record = json.loads(RECORD.read_text(encoding="utf-8"))
    for n, digest in record["hashes"].items():
        if sha(PHASE15 / n) != digest:
            raise SystemExit(f"{n} changed after the record was written")
    for n, digest in record["model_files_sha256"].items():
        if sha(MODELS / n) != digest:
            raise SystemExit(f"model file {n} changed after the record was written")
    r1 = json.loads((PHASE15 / "reforecast_r05_test.json").read_text(encoding="utf-8"))
    exc = json.loads((PHASE15 / "reforecast_exceedance_freeze.json").read_text(encoding="utf-8"))
    delta = float(r1["pooled"]["B1"]["bias_mm"])
    geography = json.loads((ROOT / "backend/app/evidence_data/phase7/static_geography_v1.json").read_text(encoding="utf-8"))
    static_fields = {n: np.array([[np.nan if v is None else v for v in row] for row in geography["fields"][n]], dtype=np.float64).ravel() for n in rs.STATIC_FEATURES}
    xs, ys, pixels, meta = [], [], [], []
    for year in YEARS:
        cases = json.loads((PROC / str(year) / "cases.json").read_text(encoding="utf-8"))["cases"]
        x_full = np.load(PROC / str(year) / "X_full.npy", mmap_mode="r", allow_pickle=False)
        days, box, fill = imd_year(year)
        for c in cases:
            if c["status"] != "INCLUDED":
                continue
            valid_day = date.fromisoformat(c["initialization"]) + timedelta(days=OFFSET[c["product"]])
            if valid_day not in days:
                continue
            obs = box[days[valid_day]].ravel()
            valid = np.isfinite(obs) & (obs != fill) & (obs >= 0)
            if not valid.any():
                continue
            cells = np.flatnonzero(valid)
            xs.append(np.asarray(x_full[c["row"]])[cells]), ys.append(obs[cells]), pixels.append(cells.astype(np.int64))
            meta.append({"initialization": c["initialization"], "product": c["product"], "year": year, "row_count": len(cells)})
    X, y, pixel = np.concatenate(xs), np.concatenate(ys), np.concatenate(pixels)
    counts = np.array([m["row_count"] for m in meta])
    starts = np.concatenate([[0], np.cumsum(counts)[:-1]])
    full = np.concatenate([X, static_columns(static_fields, pixel)], axis=1)
    names = list(rs.BASE_FEATURES) + list(rs.STATIC_FEATURES)
    B1 = full[:, [names.index(f) for f in rs.ARMS["B1"]]].astype(np.float32)
    reg = XGBRegressor()
    reg.load_model(str(MODELS / "B1.json"))
    raw_pred = np.maximum(0.0, reg.predict(B1)).astype(np.float32)
    pred = {"M0": X[:, 0].astype(np.float32), "B1_uncorrected": raw_pred, "B1_shifted": np.maximum(0.0, raw_pred - np.float32(delta)).astype(np.float32)}
    cat, report = {}, {}
    for name, suffix in (("heavy", "h"), ("very_heavy", "vh")):
        key = f"B1:{name}"
        chosen = exc["selection"][key]
        clf = XGBClassifier()
        clf.load_model(str(MODELS / exc["models"][key]["file"]))
        prob = clf.predict_proba(B1)[:, 1].astype(np.float64)
        T = rs.EXCEED_THRESHOLDS[name]
        cat[f"E_B1_{suffix}"] = np.where(prob >= chosen["tau"], T, 0.0).astype(np.float32)
        report[key] = {"tau": chosen["tau"], "test": rs.exceedance_metrics(prob, y, chosen["tau"], T), "base_rate": float((y.astype(np.float32) >= np.float32(T)).mean())}
    models = list(pred) + list(cat)
    pooled = {m: rs.pooled_metrics(y, pred[m]) for m in pred}
    mask = np.ones(2401, dtype=bool)
    per_case = np.zeros((len(meta), len(models), S))
    for i in range(len(meta)):
        sl = slice(starts[i], starts[i] + counts[i])
        obs = np.full(2401, np.nan)
        obs[pixel[sl]] = y[sl]
        fields = {}
        for m in models:
            f = np.full(2401, np.nan)
            f[pixel[sl]] = (pred[m] if m in pred else cat[m])[sl]
            fields[m] = f
        per_case[i] = zv.case_stats(obs, fields, {"ALL": mask}, names=("ALL",))[0]
    dates = sorted({m["initialization"] for m in meta})
    date_stack = np.stack([per_case[[i for i, m in enumerate(meta) if m["initialization"] == d]].sum(axis=0) for d in dates])
    idx = {m: i for i, m in enumerate(models)}
    wanted = (("B1_shifted", "M0", "rmse"), ("B1_uncorrected", "M0", "rmse"), ("E_B1_h", "M0", "heavy_csi"), ("E_B1_vh", "M0", "very_heavy_csi"))

    def statistic(totals, _models):
        return {(a, b, k): zv._metric(totals[idx[a]], k) - zv._metric(totals[idx[b]], k) for a, b, k in wanted}
    b95 = zv.paired_bootstrap(date_stack, models, statistic=statistic, repeats=2000, seed=26080, level=0.95)
    b975 = zv.paired_bootstrap(date_stack, models, statistic=statistic, repeats=2000, seed=26080, level=0.975)

    def entry(key, table):
        e = dict(table[key])
        e["interval95"] = e.pop("interval", e.get("interval95"))
        return e
    support = {t: int(pooled["M0"][t]["observed_events"]) for t in ("heavy", "very_heavy")}
    vs = {"rmse": entry(("B1_shifted", "M0", "rmse"), b95), "heavy_csi": entry(("E_B1_h", "M0", "heavy_csi"), b975) if support["heavy"] >= 30 else None,
          "very_heavy_csi": entry(("E_B1_vh", "M0", "very_heavy_csi"), b975) if support["very_heavy"] >= 30 else None}
    like = {"bias_mm": pooled["B1_shifted"]["bias_mm"], "heavy": {"frequency_bias": report["B1:heavy"]["test"]["frequency_bias"]}, "very_heavy": {"frequency_bias": report["B1:very_heavy"]["test"]["frequency_bias"]}}
    by_year = {str(yr): {m: rs.pooled_metrics(y[np.repeat([c["year"] == yr for c in meta], counts)], pred[m][np.repeat([c["year"] == yr for c in meta], counts)]) for m in pred} for yr in YEARS}
    result = {"schema": "reforecast-r05-confirmation-v1", "evidence_role": ROLE, "label": LABEL, "protocol_sha256": record["hashes"]["reforecast_study_protocol_v1.json"], "confirmation_record_sha256": sha(RECORD),
              "unseal_record_sha256": sha(RECORD), "years": list(YEARS), "cases": len(meta), "initialization_dates": len(dates), "rows": int(len(y)), "delta_mm": delta,
              "delta_source": "pooled mean error of the selected B1 regression on 2014-2016 (reforecast_r05_test.json)", "pooled": pooled, "exceedance": report,
              "raw_categorical": {t: {k: pooled["M0"][t][k] for k in ("hits", "misses", "false_alarms", "csi", "frequency_bias")} for t in ("heavy", "very_heavy")},
              "support": {"observed_event_pairs": support, "supported": {t: n >= 30 for t, n in support.items()}},
              "bundle_decision": {"vs_raw": vs, "decision": rs.decide_candidate(vs, like), "components": "RMSE and bias from the shifted B1 regression; heavy and very-heavy CSI from the B1 exceedance classifiers (amendment 3)"},
              "uncorrected_rmse_difference": entry(("B1_uncorrected", "M0", "rmse"), b95), "by_year": by_year,
              "bootstrap": {"repeats": 2000, "seed": 26080, "unit": "initialization date", "note": "optimistic: consecutive dates are correlated"},
              "reproduction": {"status": "REPRODUCED", "checks": ["every model, amendment and round-1 evidence hash matched the confirmation record", "M0 equals the raw forecast column"]}}
    EVIDENCE.write_bytes((json.dumps(clean(result), sort_keys=True, indent=2, ensure_ascii=False, allow_nan=False) + "\n").encode("utf-8"))
    manifest = {"schema": "reforecast-confirmation-manifest-v1", "protocol_sha256": record["hashes"]["reforecast_study_protocol_v1.json"], "confirmation_record_sha256": sha(RECORD),
                "files": {EVIDENCE.name: {"sha256": sha(EVIDENCE), "evidence_role": ROLE}}, "scored_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds")}
    MANIFEST.write_bytes((json.dumps(manifest, sort_keys=True, indent=2) + "\n").encode("utf-8"))
    for p in (EVIDENCE, MANIFEST):
        p.with_suffix(".sha256").write_text(sha(p) + f"  {p.name}\n", encoding="ascii")
    print(json.dumps(clean({"delta": delta, "decision": result["bundle_decision"]["decision"], "vs_raw": {k: v and (v["point"], v["interval95"]) for k, v in vs.items()}, "pooled_bias": {m: pooled[m]["bias_mm"] for m in pooled}}), indent=1))
    return 0


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("command", choices=("unseal", "score"))
    p.add_argument("--owner-message", default="")
    a = p.parse_args()
    raise SystemExit(unseal(a.owner_message) if a.command == "unseal" else score())
