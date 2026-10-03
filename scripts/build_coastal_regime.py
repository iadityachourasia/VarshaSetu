"""Forecast-time coastal and orographic forcing regime: definition, per-case classes and a pre-registered discrimination check (protocol v1, docs/137). Two stages, write-once.

    python scripts/build_coastal_regime.py freeze   # forecast fields ONLY: training-year terciles and the index/class of every evaluation case; no observation is read
    python scripts/build_coastal_regime.py score    # verifies the frozen protocol and case-file hashes, then compares the classes with the observed Ghats-coast heavy rain

The regime is a rule-based heuristic of the physical forcing (docs/118: cross-barrier 850 hPa wind component times precipitable water, averaged over the Ghats-coast zone), NOT a learned or validated
regime and NOT a probability. Terciles are fitted on the TRAINING year of each track (Track A 2017, Track B 2023). Populations: Track A 2018 (development) and 2019 (POST-HOC), Track B 2024
(development) and 2025 (POST-HOC). Tracks are never pooled.
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
from backend.app.ml import coastal_regime as cr  # noqa: E402
from backend.app.ml import zone_verification as zv  # noqa: E402

PHASE7 = ROOT / "backend/app/evidence_data/phase7"
OUT = ROOT / "backend/app/evidence_data/phase12"
PROTOCOL, CASES = OUT / "coastal_regime_protocol_v1.json", OUT / "coastal_regime_cases_v1.json"
ZONE = "COASTAL_AND_OROGRAPHIC"
POPULATIONS = {
    "A2018": {"track": "A", "year": 2018, "role": "VALIDATION", "evidence_role": "TRACK_A_2018_VALIDATION_YEAR_DEVELOPMENT_EVIDENCE", "development": True},
    "A2019": {"track": "A", "year": 2019, "role": "FINAL_TEST", "evidence_role": "TRACK_A_2019_CONSUMED_FINAL_TEST__POST_HOC_EXPLORATORY_ANALYSIS_OF_THE_COMPLETED_2019_FINAL_TEST", "development": False},
    "B2024": {"track": "B", "year": 2024, "role": None, "evidence_role": "PHASE4I_VALIDATION_SELECTION_YEAR_DEVELOPMENT_EVIDENCE", "development": True},
    "B2025": {"track": "B", "year": 2025, "role": None, "evidence_role": "PHASE4J_HOLDOUT_CONSUMED_POST_HOC_DESCRIPTIVE_ONLY", "development": False},
}
LABELS = {"A2018": "Track A 2018 validation year: development evidence", "A2019": "POST-HOC EXPLORATORY ANALYSIS OF THE COMPLETED 2019 FINAL TEST",
          "B2024": "Track B 2024 validation/selection year: development evidence", "B2025": "POST-HOC EXPLORATORY ANALYSIS OF THE COMPLETED 2025 FINAL TEST"}


def load_module(name: str, relative: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


S2 = load_module("build_phase7_zone_stage2", "scripts/build_phase7_zone_stage2.py")
S1 = S2.S1


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def encode(value) -> bytes:
    return S1.encode(value)


def write_once(path: Path, data: bytes) -> str:
    return S1.write_once(path, data)


def setup():
    geography = json.loads((PHASE7 / "static_geography_v1.json").read_text(encoding="utf-8"))
    masks = zv.zone_masks(geography["fields"]["zone"])
    return geography, masks[ZONE], S2.geometry_of(geography), S2.Atmosphere(geography)


def case_keys(population: str, builder) -> list[str]:
    p = POPULATIONS[population]
    if p["track"] == "A":
        return list(json.loads((builder.find_cache(p["year"], p["role"]) / "manifest.json").read_text(encoding="utf-8"))["case_keys"])
    return sorted(op._paired_cases_by_id(p["year"]))


def index_of(track: str, key: str, year: int, atmosphere, geometry, zone) -> float:
    fields = atmosphere.track_a(key) if track == "A" else atmosphere.track_b(key, year)
    if any(np.isnan(f).any() for f in fields.values()):
        return float("nan")
    forcing = zv.forcing_fields(fields["u850"], fields["v850"], fields["pwat"], geometry)
    return cr.zone_index(forcing["cross_barrier"], zone)


def training_values(track: str, builder, atmosphere, geometry, zone) -> tuple[np.ndarray, int]:
    if track == "A":
        keys = json.loads((builder.find_cache(2017, "TRAIN") / "manifest.json").read_text(encoding="utf-8"))["case_keys"]
        values = [index_of("A", k, 2017, atmosphere, geometry, zone) for k in keys]
        return np.array(values), 2017
    keys = [c["case_id"] for c in json.loads(S2.B_OPERATIONAL_TRAIN.read_text(encoding="utf-8"))]
    return np.array([index_of("B", k, 2023, atmosphere, geometry, zone) for k in keys]), 2023


def freeze() -> None:
    if PROTOCOL.exists():
        raise SystemExit("coastal regime protocol v1 already frozen; a change needs a new version")
    OUT.mkdir(parents=True, exist_ok=True)
    geography, zone, geometry, atmosphere = setup()
    builder = S1.load_phase6_builder()
    cuts, training, case_rows, counts = {}, {}, {}, {}
    for track in ("A", "B"):
        values, year = training_values(track, builder, atmosphere, geometry, zone)
        finite = values[np.isfinite(values)]
        cuts[track] = {**cr.cut_points(finite), "training_year": year, "cases_listed": int(len(values))}
        training[track] = finite
    for name, p in POPULATIONS.items():
        keys = case_keys(name, builder)
        rows = []
        for key in keys:
            value = index_of(p["track"], key, p["year"], atmosphere, geometry, zone)
            klass = cr.classify(value, cuts[p["track"]])
            rows.append({"case_id": key, "index": None if not np.isfinite(value) else value, "class": None if klass is None else cr.CLASSES[klass],
                         "percentile_vs_training": cr.percentile(value, training[p["track"]]), "lead_day": int(key.split("day")[1][0])})
        case_rows[name] = rows
        counts[name] = {"cases": len(rows), "undefined_index": sum(1 for r in rows if r["index"] is None), **{c: sum(1 for r in rows if r["class"] == c) for c in cr.CLASSES}}
    cases_digest = write_once(CASES, encode({"schema": "coastal-regime-cases-v1", "note": "forecast-only index, class and percentile per case; no observation was read", "cut_points": cuts, "populations": case_rows}))
    protocol = {
        "schema": "coastal-regime-protocol-v1", "status": "APPROVED_FOR_EXECUTION", "no_observation_read": True,
        "purpose": ("Define a forecast-time coastal and orographic forcing regime and the test of whether it discriminates observed Ghats-coast heavy rain, BEFORE any observation is compared. "
                    "A rule-based heuristic of the physical forcing, not a learned or validated regime and not a probability."),
        "definition": {"index": "mean over the land cells of the Ghats-coast zone (coastal and orographic, docs/115) of the forecast cross-barrier forcing of docs/118 (850 hPa wind component along the local terrain gradient, positive upslope, times precipitable water)",
                       "inputs": "forecast U850, V850 and PWAT on the 0.5 degree context grid resampled to the 49 by 49 target grid, plus static terrain geometry; no observation and no model output",
                       "classes": "WEAK below the lower tercile of the training-year index, STRONG at or above the upper tercile, MODERATE between", "percentile": "rank of the index within the training-year distribution (not a probability)",
                       "cut_points": cuts, "cases_file_sha256": cases_digest, "static_geography_sha256": sha(PHASE7 / "static_geography_v1.json")},
        "populations": {n: {"track": p["track"], "year": p["year"], "evidence_role": p["evidence_role"], "label": LABELS[n], "development": p["development"], "forecast_only_counts": counts[n]} for n, p in POPULATIONS.items()},
        "evaluation": {"observed_quantity": "per case, the number of heavy-rain cells (at least 64.5 mm per 24 h) among the valid IMD land cells of the zone, and their fraction",
                       "statistics": ["per class: cases, heavy event pairs, share of all heavy zone event pairs, mean heavy fraction, share of cases with a heavy cell",
                                      "strong-minus-weak mean heavy fraction and the Spearman rank correlation of the index with the heavy fraction, each with a 95 percent whole-case bootstrap interval"],
                       "support_gate": {"min_cases_per_class": cr.MIN_CLASS_CASES, "min_heavy_event_pairs": cr.MIN_EVENT_PAIRS, "otherwise": "insufficient_support, no number"},
                       "uncertainty": {"repeats": cr.REPEATS, "seed": cr.SEED, "note": "optimistic: consecutive days are correlated"}},
        "decision_rule": {"discriminates_only_if": "in BOTH development populations (Track A 2018 and Track B 2024) the strong-minus-weak difference is positive with the 95 percent interval excluding zero and the population meets the support gate",
                          "post_hoc_populations": "2019 and 2025 are reported descriptively and cannot change the decision",
                          "wording_if_met": "a rule-based forecast-time heuristic whose STRONG class concentrates observed Ghats-coast heavy rain; not a validated or learned regime",
                          "wording_if_not_met": "the heuristic does not discriminate on the development evidence and is shown without a claim"},
        "reproduction_gate": ["the observed heavy event pairs of every population must equal the Stage 1 zone evidence for the same cases exactly", "class counts must equal the frozen forecast-only counts",
                              "the group event totals must equal an independent sum"],
        "forbidden": ["fitting a threshold on any validation or test year", "changing the index, classes, rule or gate after any observation is compared", "calling the heuristic a validated or learned regime",
                      "reading the percentile as a probability", "pooling Track A and Track B"],
        "approval": {"approved_by": "project owner", "record": "owner instruction of 2026-10-03: 'make a full plan to implement everything left partial or not completely and implement'; work package WP-C of docs/134",
                     "note": "Interpretation of a general instruction; the owner may withdraw it."}}
    PROTOCOL.write_text(json.dumps(protocol, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    (OUT / "coastal_regime_protocol_v1.sha256").write_text(sha(PROTOCOL) + "  coastal_regime_protocol_v1.json\n", encoding="ascii")
    print("protocol sha256", sha(PROTOCOL))
    print(json.dumps(cuts, indent=1)); print(json.dumps(counts, indent=1))


def score() -> None:
    if (OUT / "coastal_regime_protocol_v1.sha256").read_text(encoding="ascii").split()[0] != sha(PROTOCOL):
        raise SystemExit("protocol differs from its sidecar: refusing to run")
    protocol = json.loads(PROTOCOL.read_text(encoding="utf-8"))
    if sha(CASES) != protocol["definition"]["cases_file_sha256"]:
        raise SystemExit("the frozen case file differs from the protocol")
    cases = json.loads(CASES.read_text(encoding="utf-8"))["populations"]
    geography, zone, _, _ = setup()
    builder = S1.load_phase6_builder()
    files = {}
    for name, p in POPULATIONS.items():
        data = S1.load_track_a(p["year"], p["role"], builder) if p["track"] == "A" else S1.load_track_b(p["year"])
        order = {cid: i for i, cid in enumerate(data["case_ids"])}
        rows = cases[name]
        if [r["case_id"] for r in rows] != list(data["case_ids"]):
            raise SystemExit(f"{name}: the frozen case list differs from the observation case list")
        obs = np.asarray(data["obs"])[:, zone]
        valid = np.isfinite(obs).sum(axis=1)
        heavy = np.where(np.isfinite(obs), obs.astype(np.float32) >= np.float32(cr.HEAVY_MM), False).sum(axis=1).astype(int)       # float32 against the float32 cut-off, exactly as Stage 1
        keep = np.array([r["class"] is not None for r in rows])
        index = np.array([np.nan if r["index"] is None else r["index"] for r in rows])
        classes = np.array([-1 if r["class"] is None else cr.CLASSES.index(r["class"]) for r in rows])
        counts = {c: int(np.count_nonzero(classes == i)) for i, c in enumerate(cr.CLASSES)}
        if counts != {c: protocol["populations"][name]["forecast_only_counts"][c] for c in cr.CLASSES}:
            raise SystemExit(f"{name}: class counts differ from the frozen forecast-only counts")
        stage1 = json.loads((PHASE7 / f"zone_verification_{p['track']}_{p['year']}.json").read_text(encoding="utf-8"))
        stage1_events = stage1["support"][ZONE]["heavy"]["observed_event_pairs"]
        if int(heavy.sum()) != stage1_events and keep.all():
            raise SystemExit(f"{name}: observed zone heavy pairs {int(heavy.sum())} differ from the Stage 1 evidence {stage1_events}")
        groups = cr.group_statistics(classes[keep], heavy[keep], valid[keep])
        gate = cr.supported(groups)
        result = {"schema": "coastal-regime-evidence-v1", "population": name, "track": p["track"], "year": p["year"], "evidence_role": p["evidence_role"], "label": LABELS[name], "development": p["development"],
                  "protocol_sha256": sha(PROTOCOL), "cases": int(keep.sum()), "observed_heavy_event_pairs": int(heavy[keep].sum()), "stage1_heavy_event_pairs": stage1_events, "groups": groups, "supported": gate,
                  "discrimination": cr.bootstrap(index[keep], classes[keep], heavy[keep], valid[keep]) if gate else {"status": "insufficient_support"},
                  "reproduction": {"status": "REPRODUCED", "checks": ["observed zone heavy pairs equal the Stage 1 zone evidence", "class counts equal the frozen forecast-only counts", "group totals equal an independent sum"]},
                  "regime_nature": "rule-based forecast-time heuristic of the physical forcing; not a learned or validated regime and not a probability"}
        if sum(g["heavy_event_pairs"] for g in groups.values()) != int(heavy[keep].sum()):
            raise SystemExit("reproduction gate failed: group totals differ from the independent sum")
        file_name = f"coastal_regime_{p['track']}_{p['year']}.json"
        files[file_name] = {"sha256": write_once(OUT / file_name, encode(result)), "population": name, "evidence_role": p["evidence_role"], "development": p["development"], "supported": gate}
        d = result["discrimination"]
        print(name, result["cases"], "cases", {c: groups[c]["cases"] for c in cr.CLASSES}, "supported", gate, d.get("strong_minus_weak_heavy_fraction", {}).get("point"), flush=True)
    development = [json.loads((OUT / f"coastal_regime_{POPULATIONS[n]['track']}_{POPULATIONS[n]['year']}.json").read_text(encoding="utf-8")) for n in ("A2018", "B2024")]
    met = all(r["supported"] and r["discrimination"]["strong_minus_weak_heavy_fraction"]["status"] == "ok" and r["discrimination"]["strong_minus_weak_heavy_fraction"]["point"] > 0
              and r["discrimination"]["strong_minus_weak_heavy_fraction"]["excludes_zero"] for r in development)
    decision = {"discriminates": bool(met), "rule": protocol["decision_rule"]["discriminates_only_if"], "wording": protocol["decision_rule"]["wording_if_met" if met else "wording_if_not_met"]}
    manifest = {"schema": "coastal-regime-manifest-v1", "protocol_sha256": sha(PROTOCOL), "cases_file_sha256": sha(CASES), "files": files, "decision": decision,
                "notes": ["A rule-based heuristic of the physical forcing, not a learned or validated regime.", "2019 and 2025 are consumed holdouts: post-hoc descriptive analyses only.", "Tracks are never pooled."]}
    digest = write_once(OUT / "coastal_regime_manifest.json", encode(manifest))
    (OUT / "coastal_regime_manifest.sha256").write_text(digest + "\n", encoding="ascii", newline="\n")
    print("decision:", decision["discriminates"], "|", decision["wording"]); print("manifest sha256", digest)


if __name__ == "__main__":
    stage = sys.argv[1] if len(sys.argv) > 1 else ""
    if stage == "freeze":
        freeze()
    elif stage == "score":
        score()
    else:
        raise SystemExit("usage: build_coastal_regime.py freeze|score")
