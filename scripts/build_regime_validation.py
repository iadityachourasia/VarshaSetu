"""Independent, observation-based check of the forecast-only regime classifier: active and break against rainfall criteria (protocol v1, docs/136). Two stages, write-once.

    python scripts/build_regime_validation.py freeze   # reads IMD observations and case lists ONLY (no classifier prediction); writes the protocol with the climatology and the support counts
    python scripts/build_regime_validation.py score    # verifies the frozen protocol hash, recomputes the labels (reproduction gate), then scores the frozen classifier

Labels follow the style of Rajeevan et al. (2010) as described in docs/123, with documented deviations; this is NOT the published classification. Climatology: IMD RF25 1981-2016, which
shares no year with any evaluated population. Populations: Track A 2018 (development) and 2019 (POST-HOC), Track B 2024 (development) and 2025 (POST-HOC). Depression is not validated.
The IMD files are local-only (rights unresolved); only aggregate counts and scores are written.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
from datetime import date
from pathlib import Path

import numpy as np
from scipy.io import netcdf_file

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.app.api import operational as op  # noqa: E402
from backend.app.ml import regime_validation as rv  # noqa: E402

EVIDENCE = ROOT / "backend/app/evidence_data/phase6"
PROTOCOL = EVIDENCE / "regime_validation_protocol_v1.json"
CLIMATOLOGY_DIR = ROOT / "experiments/recent_historical/imd_climatology"
CLIMATOLOGY_YEARS = tuple(range(1981, 2017))
POPULATIONS = {
    "A2018": {"track": "A", "year": 2018, "imd": ROOT / "data/raw/observations/imd/2018/RF25_ind2018_rfp25.nc", "cache_role": "VALIDATION",
              "evidence_role": "TRACK_A_2018_VALIDATION_YEAR_DEVELOPMENT_EVIDENCE"},
    "A2019": {"track": "A", "year": 2019, "imd": ROOT / "data/raw/observations/imd/2019/RF25_ind2019_rfp25.nc", "cache_role": "FINAL_TEST",
              "evidence_role": "TRACK_A_2019_CONSUMED_FINAL_TEST__POST_HOC_EXPLORATORY_ANALYSIS_OF_THE_COMPLETED_2019_FINAL_TEST"},
    "B2024": {"track": "B", "year": 2024, "imd": ROOT / "experiments/recent_historical/imd/RF25_ind2024_rfp25.nc", "evidence_role": "PHASE4I_VALIDATION_SELECTION_YEAR_DEVELOPMENT_EVIDENCE"},
    "B2025": {"track": "B", "year": 2025, "imd": ROOT / "experiments/recent_historical/imd/RF25_ind2025_rfp25.nc", "evidence_role": "PHASE4J_HOLDOUT_CONSUMED_POST_HOC_DESCRIPTIVE_ONLY"},
}


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


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
        raise RuntimeError(f"frozen regime-validation evidence would change: {path}")
    path.write_bytes(data)
    return hashlib.sha256(data).hexdigest()


def year_series(path: Path) -> dict[tuple[int, int], float]:
    with netcdf_file(path, "r", mmap=False) as dataset:
        times = np.asarray(dataset.variables["TIME"].data, dtype=np.float64)
        lat = np.asarray(dataset.variables["LATITUDE"].data, dtype=np.float64)
        lon = np.asarray(dataset.variables["LONGITUDE"].data, dtype=np.float64)
        rainfall = np.asarray(dataset.variables["RAINFALL"].data, dtype=np.float64)
    return rv.season_series(rv.area_mean_series(rainfall, lat, lon), rv.dates_of(times))


def build_climatology() -> tuple[np.ndarray, float, dict, dict]:
    per_year, hashes = {}, {}
    for year in CLIMATOLOGY_YEARS:
        file = CLIMATOLOGY_DIR / f"RF25_ind{year}_rfp25.nc"
        manifest = CLIMATOLOGY_DIR / f"imd_{year}_manifest.json"
        if not file.is_file() or not manifest.is_file():
            raise SystemExit(f"climatology file for {year} is missing: run scripts/fetch_imd_climatology.py")
        digest = sha(file)
        if json.loads(manifest.read_text(encoding="utf-8"))["sha256"] != digest:
            raise SystemExit(f"climatology file for {year} differs from its manifest")
        hashes[str(year)] = digest
        per_year[year] = year_series(file)
    mean, sigma, info = rv.climatology(per_year)
    return mean, sigma, info, hashes


def parse_case(identifier: str) -> tuple[date, int]:
    """'20250714_day2_24h' or '2019-06-01T00:00:00Z|day1_24h' -> (initialization date, lead day)."""
    if "|" in identifier:
        init, product = identifier.split("|")
        return date.fromisoformat(init[:10]), int(product.split("day")[1][0])
    stamp, product = identifier.split("_day", 1)
    return date(int(stamp[:4]), int(stamp[4:6]), int(stamp[6:8])), int(product[0])


def case_lists() -> dict[str, list[str]]:
    """Case identifiers per population WITHOUT reading any classifier output (Track A: the cache case list; Track B: the frozen probability index)."""
    P6 = importlib.util.module_from_spec(importlib.util.spec_from_file_location("build_phase6_evidence", ROOT / "scripts/build_phase6_evidence.py"))
    P6.__spec__.loader.exec_module(P6)
    out = {}
    for name, p in POPULATIONS.items():
        if p["track"] == "A":
            cache_dir = P6.find_cache(p["year"], p["cache_role"])
            out[name] = list(json.loads((cache_dir / "manifest.json").read_text(encoding="utf-8"))["case_keys"])
        else:
            out[name] = sorted(op._REGIME_LOADER[p["year"]]())
    return out


def observed_states(population: str, identifiers: list[str], labels: dict[date, str]) -> list[tuple[str, date, str]]:
    """(identifier, initialization date, observed state) for every case whose paired IMD day falls in July or August."""
    rows = []
    for identifier in identifiers:
        init, lead = parse_case(identifier)
        day = rv.valid_date(init, lead)
        if day in labels:
            rows.append((identifier, init, labels[day]))
    return rows


def count_states(rows) -> dict[str, int]:
    return {state: sum(1 for _, _, s in rows if s == state) for state in rv.STATES}


def freeze() -> None:
    if PROTOCOL.exists():
        raise SystemExit("regime validation protocol v1 already frozen; a change needs a new version")
    mean, sigma, info, clim_hashes = build_climatology()
    cases = case_lists()
    populations, counts = {}, {}
    for name, p in POPULATIONS.items():
        series = year_series(p["imd"])
        z = rv.normalised_anomaly(series, mean, sigma)
        labels = rv.label_days(z, p["year"])
        rows = observed_states(name, cases[name], labels)
        day_counts = {state: sum(1 for s in labels.values() if s == state) for state in rv.STATES}
        case_counts = count_states(rows)
        spells = {"active_spells": int(sum(1 for i in range(len(z)) if rv.spell_mask(z, positive=True)[i] and (i == 0 or not rv.spell_mask(z, positive=True)[i - 1]))),
                  "break_spells": int(sum(1 for i in range(len(z)) if rv.spell_mask(z, positive=False)[i] and (i == 0 or not rv.spell_mask(z, positive=False)[i - 1])))}
        populations[name] = {"track": p["track"], "year": p["year"], "evidence_role": p["evidence_role"], "imd_file_sha256": sha(p["imd"]), "cases_listed": len(cases[name])}
        counts[name] = {"labelled_days": day_counts, "spells_in_season": spells, "cases_with_labelled_valid_day": len(rows), "cases_by_observed_state": case_counts,
                        "supported": rv.supported(case_counts)}
    protocol = {
        "schema": "regime-validation-protocol-v1", "status": "APPROVED_FOR_EXECUTION", "no_classifier_prediction_read": True,
        "purpose": ("Check the forecast-only regime classifier against observation-based rainfall criteria that are independent of the pseudo-labelling rule, BEFORE any agreement is computed. "
                    "Separate from, and never merged with, the agreement with the pseudo-labels."),
        "criteria": {"style": "Rajeevan, Gadgil and Bhate (2010) as described in docs/123: normalised core-zone rainfall anomaly at or beyond +1 (active) or -1 (break) for at least three consecutive days",
                     "core_zone_box": {"lat": list(rv.CMZ_LAT), "lon": list(rv.CMZ_LON)}, "threshold_sd": rv.THRESHOLD_SD, "min_spell_days": rv.MIN_SPELL_DAYS, "label_window_months": list(rv.WINDOW_MONTHS),
                     "area_mean": "cosine-latitude weighted mean over valid (non-fill, non-negative) IMD 0.25 degree cells of the box",
                     "climatology": {"years": [CLIMATOLOGY_YEARS[0], CLIMATOLOGY_YEARS[-1]], "smoothing": f"centred {rv.SMOOTH_DAYS}-day moving average of the daily mean, nearest-value edges",
                                     "sigma": "one pooled sample standard deviation of the July-August anomalies of the climatology years", "sigma_mm_per_day": sigma,
                                     "mean_mm_per_day_by_season_day": [float(x) for x in mean], "file_sha256": clim_hashes, "info": info},
                     "deviations_from_the_published_work": ["a latitude-longitude box approximates the core-zone polygon", "the IMD grid starts at 66.5 E, east of the box edge at 65 E",
                                                            "a moving-average climatology and one pooled sigma replace the published smoothing and normalisation",
                                                            "the criteria were read from summaries (docs/123) and not verified against the paper's text",
                                                            "the climatology is 36 years (1981-2016), not the published record"],
                     "not_the_published_classification": True},
        "populations": populations, "label_pairing": "a case is paired with the IMD day initialization date + lead day (Day 1 pairs with the next calendar day); only cases whose paired day is in July or August are scored",
        "classifier_output": "argmax of the frozen forecast-only classifier probability of each case (the class M3 hard-routes on)",
        "tasks": {"active_vs_not_active": "predicted ACTIVE_MONSOON versus observed ACTIVE", "break_vs_not_break": "predicted BREAK_WEAK_MONSOON versus observed BREAK",
                  "not_scored": "LOW_DEPRESSION_INFLUENCED: no observation-based depression label exists in this protocol; depression is NOT validated; the weak part of Break/Weak has no published criterion"},
        "metrics": ["3x3 confusion (predicted class by observed ACTIVE, BREAK, NEUTRAL)", "recall (POD)", "specificity", "precision", "balanced accuracy", "F1", "base rate"],
        "uncertainty": {"method": "bootstrap of whole initialization dates (all leads of a date together)", "repeats": rv.REPEATS, "seed": rv.SEED, "note": "optimistic: consecutive dates are correlated"},
        "support_gate": {"min_cases_per_side": rv.MIN_CLASS_CASES, "otherwise": "insufficient_support, no score"},
        "observation_only_counts": counts,
        "labels": {"A2018": "Track A 2018 validation year: development evidence", "A2019": "POST-HOC EXPLORATORY ANALYSIS OF THE COMPLETED 2019 FINAL TEST",
                   "B2024": "Track B 2024 validation/selection year: development evidence", "B2025": "POST-HOC EXPLORATORY ANALYSIS OF THE COMPLETED 2025 FINAL TEST"},
        "reproduction_gate": ["the labels recomputed in the score stage must reproduce the protocol's observation-only counts exactly", "the confusion table must sum to the number of labelled cases",
                              "the predicted class counts must equal an independent count from the frozen probabilities", "one binary metric must equal an independent loop"],
        "forbidden": ["changing a threshold, box, window, climatology or support rule after any score is computed", "calling these labels the published active/break classification", "claiming that depression is validated",
                      "merging this result with the pseudo-label agreement figures", "uploading or republishing the IMD files or the daily series"],
        "approval": {"approved_by": "project owner", "record": "owner instruction of 2026-10-03: 'make a full plan to implement everything left partial or not completely and implement'; work package WP-B of docs/134, source decisions of docs/123 section 5",
                     "note": ("Interpretation of a general instruction: the climatology download (36 IMD files, about 0.9 GB, local only) and a partial validation (active versus not active, break versus not break) were taken as approved. "
                              "The owner may withdraw this.")}}
    PROTOCOL.write_text(json.dumps(clean(protocol), indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    (EVIDENCE / "regime_validation_protocol_v1.sha256").write_text(sha(PROTOCOL) + "  regime_validation_protocol_v1.json\n", encoding="ascii")
    print("protocol sha256", sha(PROTOCOL), "sigma", round(sigma, 3))
    print(json.dumps(counts, indent=1))


def frozen_classes(population: str, identifiers: list[str]) -> tuple[dict[str, int], dict[str, np.ndarray]]:
    """Predicted class (argmax of the frozen probability) per case identifier, and the frozen probabilities."""
    p = POPULATIONS[population]
    if p["track"] == "B":
        probabilities = op._REGIME_LOADER[p["year"]]()
        return {i: int(np.argmax(probabilities[i])) for i in identifiers}, {i: np.asarray(probabilities[i]) for i in identifiers}
    P6 = importlib.util.module_from_spec(importlib.util.spec_from_file_location("build_phase6_evidence", ROOT / "scripts/build_phase6_evidence.py"))
    P6.__spec__.loader.exec_module(P6)
    cache_dir = P6.find_cache(p["year"], p["cache_role"])
    manifest, arrays = P6.load_cache(cache_dir)
    code = arrays["case_code"].astype(np.int64)
    starts = np.flatnonzero(np.r_[True, np.diff(code) != 0])
    keys = manifest["case_keys"]
    probs = {k: np.asarray(arrays["regime_probability"][s]) for k, s in zip(keys, starts)}
    classes = {k: int(arrays["predicted_regime_id"][s]) for k, s in zip(keys, starts)}
    for k in keys:
        if int(np.argmax(probs[k])) != classes[k]:
            raise RuntimeError("predicted_regime_id is not the argmax of the stored probability")
    return {i: classes[i] for i in identifiers}, {i: probs[i] for i in identifiers}


def score() -> None:
    if (EVIDENCE / "regime_validation_protocol_v1.sha256").read_text(encoding="ascii").split()[0] != sha(PROTOCOL):
        raise SystemExit("protocol differs from its sidecar: refusing to run")
    protocol = json.loads(PROTOCOL.read_text(encoding="utf-8"))
    mean, sigma, info, clim_hashes = build_climatology()
    if clim_hashes != protocol["criteria"]["climatology"]["file_sha256"] or abs(sigma - protocol["criteria"]["climatology"]["sigma_mm_per_day"]) > 1e-12 \
            or not np.allclose(mean, protocol["criteria"]["climatology"]["mean_mm_per_day_by_season_day"], atol=0, rtol=0):
        raise SystemExit("the recomputed climatology differs from the frozen protocol")
    cases = case_lists()
    files = {}
    for name, p in POPULATIONS.items():
        if sha(p["imd"]) != protocol["populations"][name]["imd_file_sha256"]:
            raise SystemExit(f"IMD file for {name} differs from the protocol")
        labels = rv.label_days(rv.normalised_anomaly(year_series(p["imd"]), mean, sigma), p["year"])
        rows = observed_states(name, cases[name], labels)
        reproduced = count_states(rows)
        want = protocol["observation_only_counts"][name]
        if reproduced != want["cases_by_observed_state"] or {s: sum(1 for v in labels.values() if v == s) for s in rv.STATES} != want["labelled_days"]:
            raise SystemExit(f"reproduction gate failed for {name}: labels differ from the protocol counts")
        identifiers = [r[0] for r in rows]
        predicted, probs = frozen_classes(name, identifiers)
        pred = np.array([predicted[i] for i in identifiers])
        observed = [r[2] for r in rows]
        clusters = [r[1] for r in rows]
        table = rv.confusion(pred, observed, op.REGIME_CLASSES)
        if sum(sum(v.values()) for v in table.values()) != len(rows):
            raise SystemExit("reproduction gate failed: the confusion table does not sum to the labelled cases")
        independent = np.bincount(np.array([int(np.argmax(probs[i])) for i in identifiers]), minlength=3).tolist()
        if independent != np.bincount(pred, minlength=3).tolist():
            raise SystemExit("reproduction gate failed: predicted class counts differ from the stored probabilities")
        tasks, task_arr = {}, rv.task_arrays(pred, observed, op.REGIME_CLASSES)
        gate = want["supported"]
        for task, (p_arr, o_arr) in task_arr.items():
            state = "ACTIVE" if task.startswith("active") else "BREAK"
            if not gate[state]:
                tasks[task] = {"status": "insufficient_support", "observed_cases": int(o_arr.sum()), "note": "fewer than the support gate on one side; no score"}
                continue
            m = rv.binary_metrics(p_arr, o_arr)
            loop_hits = sum(1 for a, b in zip(p_arr.tolist(), o_arr.tolist()) if a and b)
            if loop_hits != m["hits"]:
                raise SystemExit("reproduction gate failed: hits differ from an independent loop")
            by_lead = {}
            for lead in (1, 2, 3):
                sel = np.array([parse_case(i)[1] == lead for i in identifiers])
                by_lead[f"day{lead}"] = rv.binary_metrics(p_arr[sel], o_arr[sel]) if sel.any() else None
            tasks[task] = {"status": "scored", **m, "balanced_accuracy_bootstrap": rv.cluster_bootstrap_balanced_accuracy(p_arr, o_arr, clusters), "by_lead": by_lead}
        scored = [t for t in tasks.values() if t.get("status") == "scored"]
        macro = {"macro_balanced_accuracy": float(np.mean([t["balanced_accuracy"] for t in scored])) if scored else None,
                 "macro_f1": float(np.mean([t["f1"] for t in scored if t["f1"] is not None])) if scored and all(t["f1"] is not None for t in scored) else None,
                 "tasks_scored": len(scored)}
        result = {"schema": "regime-validation-v1", "population": name, "track": p["track"], "year": p["year"], "evidence_role": p["evidence_role"], "label": protocol["labels"][name],
                  "protocol_sha256": sha(PROTOCOL), "cases_listed": len(cases[name]), "cases_labelled": len(rows), "observed_state_counts": reproduced,
                  "confusion_predicted_class_by_observed_state": table, "tasks": tasks, "macro": macro, "depression": "NOT VALIDATED: no observation-based depression label in this protocol",
                  "reproduction": {"status": "REPRODUCED", "checks": ["labels equal the frozen counts", "confusion sums to the labelled cases", "predicted counts equal the stored probabilities", "hits equal an independent loop"]},
                  "pseudo_label_agreement_is_separate": True, "bootstrap": {"repeats": rv.REPEATS, "seed": rv.SEED, "unit": "initialization date"}}
        file_name = f"regime_validation_{p['track']}_{p['year']}.json"
        files[file_name] = {"sha256": write_once(EVIDENCE / file_name, encode(result)), "population": name, "evidence_role": p["evidence_role"], "cases_labelled": len(rows),
                            "reproduction": "REPRODUCED"}
        print(name, len(rows), "labelled cases", reproduced, {t: (v.get("balanced_accuracy"), v.get("status")) for t, v in tasks.items()}, flush=True)
    manifest = {"schema": "regime-validation-manifest-v1", "protocol_sha256": sha(PROTOCOL), "files": files,
                "notes": ["Observation-based check of active and break only; depression is not validated.", "Labels follow the style of Rajeevan et al. (2010) with documented deviations; not the published classification.",
                          "2019 and 2025 are consumed holdouts: post-hoc descriptive analyses only.", "Separate from the pseudo-label agreement figures."]}
    digest = write_once(EVIDENCE / "regime_validation_manifest.json", encode(manifest))
    (EVIDENCE / "regime_validation_manifest.sha256").write_text(digest + "\n", encoding="ascii", newline="\n")
    print("regime_validation_manifest.json sha256", digest)


if __name__ == "__main__":
    stage = sys.argv[1] if len(sys.argv) > 1 else ""
    if stage == "freeze":
        freeze()
    elif stage == "score":
        score()
    else:
        raise SystemExit("usage: build_regime_validation.py freeze|score")
