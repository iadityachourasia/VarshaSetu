"""Stage 2 of the coastal/orographic protocol v3 (docs/118): forecast-time forcing-strength strata and the Q3 comparison.

Read-only re-aggregation of FROZEN grids; nothing is trained, tuned or selected. Governed by the hash-frozen execution spec
backend/app/evidence_data/phase7/zone_stage2_spec_v1.json; the script refuses to run against any other protocol, geography,
Stage 1 or spec hash, and refuses to write unless the strata reproduce the Stage 1 zone totals exactly. Outputs are write-once.

    python scripts/build_phase7_zone_stage2.py
"""

from __future__ import annotations

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

PHASE7 = ROOT / "backend/app/evidence_data/phase7"
SPEC = PHASE7 / "zone_stage2_spec_v1.json"
SPEC_SHA = "3755e06cc48f04e553ac204ea6534de1c2856ff4e2f7d438186ebc5e11e133ff"
SCHEMA = "phase7-zone-stage2-v1"
FIELDS = ("u850", "v850", "pwat")
A_ZARR = ROOT / "data/processed/phase1f/2019-JJAS/varshasetu-gefs12r-imd025-2019-jjas-v2.zarr"
A_ORDER = ("u850", "v850", "q700", "z500", "mslp", "pwat")
B_OPERATIONAL_TRAIN = ROOT / "data/operational_derived/operational_features_2023_2025_v1/2023/train/deterministic/cases.json"


def load_stage1_module():
    spec = importlib.util.spec_from_file_location("build_phase7_zone_verification", ROOT / "scripts/build_phase7_zone_verification.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


S1 = load_stage1_module()
sha, encode, write_once = S1.sha, S1.encode, S1.write_once


class Atmosphere:
    """Forecast U850, V850 and PWAT of one case on the target grid (flat 2401 cells). Reads forecast fields only."""

    def __init__(self, geography: dict):
        self.target_lat = np.array(geography["grid"]["latitude_centers"], dtype=float)
        self.target_lon = np.array(geography["grid"]["longitude_centers"], dtype=float)
        self.context_lat = np.linspace(5.0, 30.0, 51)
        self.context_lon = np.linspace(55.0, 95.0, 81)
        self._zarr = None
        self._zarr_index = None

    def _target(self, grid: np.ndarray) -> np.ndarray:
        grid = np.where(np.isfinite(grid) & (np.abs(grid) < 1e10), grid, np.nan)
        if np.isnan(grid).any():
            return np.full(zv.GRID_CELLS, np.nan)
        return zv.resample_to_target(grid, self.context_lat, self.context_lon, self.target_lat, self.target_lon)

    def track_a(self, case_key: str) -> dict[str, np.ndarray]:
        init, day = case_key.split("|")[0], int(case_key.split("day")[1][0])
        year = int(init[:4])
        lead_hours = 24 * day
        if year in (2017, 2018):
            import scipy.io

            path = ROOT / f"data/processed/phase2a/{init[:7]}/daily/atmosphere_context_{init[:10].replace('-', '')}00.nc"
            with scipy.io.netcdf_file(path, mmap=False) as handle:
                lat, lon = np.array(handle.variables["latitude"][:]), np.array(handle.variables["longitude"][:])
                if not (np.allclose(lat, self.context_lat) and np.allclose(lon, self.context_lon)):
                    raise RuntimeError(f"{path.name}: unexpected context grid")
                leads = np.array(handle.variables["lead_hours"][:]).astype(int).tolist()
                k = leads.index(lead_hours)
                grids = {name: np.array(handle.variables[name].data[k], dtype=np.float64) for name in FIELDS}
        else:
            import datetime

            import zarr

            if self._zarr is None:
                self._zarr = zarr.open_group(str(A_ZARR), mode="r")
                times = np.asarray(self._zarr["init_time_unix_seconds"][:])
                self._zarr_index = {datetime.datetime.fromtimestamp(int(t), datetime.timezone.utc).strftime("%Y-%m-%d"): i for i, t in enumerate(times)}
                if not (np.allclose(self._zarr["context_latitude"][:], self.context_lat) and np.allclose(self._zarr["context_longitude"][:], self.context_lon)):
                    raise RuntimeError("unexpected 2019 context grid")
                self._lead = np.asarray(self._zarr["lead_hours"][:]).astype(int).tolist()
            block = np.asarray(self._zarr["atmosphere"][self._zarr_index[init[:10]], self._lead.index(lead_hours)], dtype=np.float64)
            grids = {name: block[A_ORDER.index(name)] for name in FIELDS}
        return {name: self._target(grid) for name, grid in grids.items()}

    def track_b(self, case_id: str, year: int) -> dict[str, np.ndarray]:
        date8, day = case_id[:8], int(case_id.split("day")[1][0])
        hour = f"{24 * day:03d}"
        grids = {name: np.load(op.PHASE4F / "atmospheric_qc" / str(year) / date8 / f"{name}_f{hour}.npy", allow_pickle=False).astype(np.float64) for name in FIELDS}
        for grid in grids.values():
            if grid.shape != (51, 81):
                raise RuntimeError(f"{case_id}: unexpected atmospheric grid shape {grid.shape}")
        return {name: self._target(grid) for name, grid in grids.items()}


def geometry_of(geography: dict) -> dict[str, np.ndarray]:
    return {name: np.array([[0.0 if v is None else v for v in row] for row in geography["fields"][name]], dtype=float).ravel()
            for name in ("coast_landward_east", "coast_landward_north", "terrain_uphill_east", "terrain_uphill_north")}


def fit_cut_points(track: str, atmosphere: Atmosphere, geometry: dict, masks: dict) -> dict:
    """Tercile cut-points per zone and component from the TRAINING year only (no observation is read)."""
    if track == "A":
        builder = S1.load_phase6_builder()
        manifest = json.loads((builder.find_cache(2017, "TRAIN") / "manifest.json").read_text(encoding="utf-8"))
        keys = manifest["case_keys"]
        fetch = atmosphere.track_a
        year = 2017
    else:
        keys = [c["case_id"] for c in json.loads(B_OPERATIONAL_TRAIN.read_text(encoding="utf-8"))]
        fetch = lambda cid: atmosphere.track_b(cid, 2023)       # noqa: E731
        year = 2023
    pooled = {(zone, comp): [] for zone, comps in zv.COMPONENTS.items() for comp in comps}
    used = 0
    for key in keys:
        fields = fetch(key)
        if any(np.isnan(f).any() for f in fields.values()):
            continue
        used += 1
        forcing = zv.forcing_fields(fields["u850"], fields["v850"], fields["pwat"], geometry)
        for (zone, comp), bucket in pooled.items():
            bucket.append(forcing[comp][masks[zone]])
    out = {"year": year, "cases_listed": len(keys), "cases_used": used, "cut_points": {}}
    for (zone, comp), bucket in pooled.items():
        out["cut_points"][f"{zone}|{comp}"] = zv.tercile_cut_points(np.concatenate(bucket))
    return out


def analyse_year(track: str, year: int, data: dict, atmosphere: Atmosphere, geometry: dict, masks: dict, fit: dict, stage1: dict) -> dict:
    models = S1.MODELS[track]
    keys = [(zone, comp) for zone, comps in zv.COMPONENTS.items() for comp in comps if not fit["cut_points"][f"{zone}|{comp}"]["degenerate"]]
    names = ["ALL", *zv.PRE_REGISTERED_ZONES] + [f"{zone}|{comp}|{stratum}" for zone, comp in keys for stratum in zv.STRATA]
    missing = []
    stats = []
    for i, case_id in enumerate(data["case_ids"]):
        fields = atmosphere.track_a(case_id) if track == "A" else atmosphere.track_b(case_id, year)
        if any(np.isnan(f).any() for f in fields.values()):
            missing.append(case_id)
        forcing = zv.forcing_fields(fields["u850"], fields["v850"], fields["pwat"], geometry)
        case_masks = {"ALL": masks["ALL"], **{z: masks[z] for z in zv.PRE_REGISTERED_ZONES}}
        for zone, comp in keys:
            cuts = fit["cut_points"][f"{zone}|{comp}"]
            for stratum, mask in zv.stratum_masks(forcing[comp], masks[zone], cuts).items():
                case_masks[f"{zone}|{comp}|{stratum}"] = mask
        stats.append(zv.case_stats(data["obs"][i], {m: data["fields"][m][i] for m in models}, case_masks, names))
    if missing:
        raise RuntimeError(f"{track}{year}: forecast fields unavailable for {len(missing)} cases, e.g. {missing[:3]}")
    stack = np.stack(stats)
    totals = stack.sum(axis=0)
    index = {name: k for k, name in enumerate(names)}

    # reproduction gate: strata partition each zone, and the zones equal the Stage 1 evidence
    for zone, comp in keys:
        parts = sum(totals[index[f"{zone}|{comp}|{s}"]] for s in zv.STRATA)
        if not np.allclose(parts, totals[index[zone]]):
            raise RuntimeError(f"{track}{year}: strata of {zone}|{comp} do not add up to the zone")
    worst = 0.0
    for zone in ("ALL", *zv.PRE_REGISTERED_ZONES):
        for mi, model in enumerate(models):
            mine = zv.metrics(totals[index[zone], mi])
            ref = stage1["pooled"][zone][model]
            if mine["cell_count"] != ref["cell_count"]:
                raise RuntimeError(f"{track}{year}/{zone}/{model}: cell count differs from Stage 1")
            worst = max(worst, abs(mine["rmse_mm"] - ref["rmse_mm"]), abs(mine["bias_mm"] - ref["bias_mm"]))
            ref_h = ref["categorical"]["heavy"]
            if "hits" in ref_h and any(mine["categorical"]["heavy"][k] != ref_h[k] for k in ("hits", "misses", "false_alarms")):
                raise RuntimeError(f"{track}{year}/{zone}/{model}: heavy counts differ from Stage 1")
    if worst > 1e-9:
        raise RuntimeError(f"{track}{year}: zones differ from Stage 1 evidence (max abs diff {worst})")

    gate = zv.stratum_support(stack, names)
    pooled = {}
    for name in names[1 + len(zv.PRE_REGISTERED_ZONES):]:
        pooled[name] = {}
        for mi, model in enumerate(models):
            block = zv.metrics(totals[index[name], mi])
            if not gate[name]["continuous_supported"]:
                block = {"cell_count": block["cell_count"], "status": "insufficient_support"}
            else:
                block["categorical"].pop("very_heavy", None)
                if not gate[name]["heavy_supported"]:
                    block["categorical"]["heavy"] = {"status": "insufficient_support", "observed_event_pairs": gate[name]["heavy_observed_event_pairs"]}
            pooled[name][model] = block

    def statistic(sum_totals, mdls):
        return zv.q3_statistics(sum_totals, mdls, keys, names)
    boot = zv.paired_bootstrap(stack, models, statistic=statistic)
    q3 = {}
    for (_, label, model, metric), value in boot.items():
        zone, comp = label.split("|")
        weak, strong = gate[f"{zone}|{comp}|weak"], gate[f"{zone}|{comp}|strong"]
        decisive = metric in zv.Q3_DECISION
        heavy = metric in ("heavy_fb", "heavy_csi")
        ok = (weak["heavy_supported"] and strong["heavy_supported"]) if heavy else (weak["continuous_supported"] and strong["continuous_supported"])
        q3.setdefault(label, {}).setdefault(model, {})[metric] = (value if ok else {"status": "insufficient_support", "point": None}) | {"in_decision_rule": decisive}

    return {"schema": SCHEMA, "track": track, "year": year, "evidence_role": S1.ROLES[(track, year)], "case_count": len(data["case_ids"]),
            "models": models, "spec_sha256": SPEC_SHA, "protocol_sha256": S1.PROTOCOL_SHA, "static_geography_sha256": sha(S1.GEOGRAPHY),
            "forcing_cut_points": fit, "support": {k: v for k, v in gate.items() if "|" in k}, "pooled": pooled, "q3": q3,
            "bootstrap": {"repeats": zv.REPEATS, "seed": zv.SEED, "note": "paired whole-case bootstrap; optimistic"},
            "definitions": {"strata": "weak <= q33 < middle <= q67 < strong of forcing = component x PWAT, cut-points fitted on the training year only",
                            "q3": "metric(strong) - metric(weak) per model; heavy_fb = forecast heavy events / observed heavy events",
                            "components": "COASTAL: onshore; OROGRAPHIC: cross_barrier; COASTAL_AND_OROGRAPHIC: both reported separately; OTHER: not stratified"},
            "fss": {"status": "not_reported", "reason": S1.FSS_TEXT},
            "reproduction": {"status": "REPRODUCED", "strata_partition_zones": True, "zones_equal_stage1_max_abs_diff": worst,
                             "stage1_file": f"zone_verification_{track}_{year}.json", "stage1_sha256": sha(PHASE7 / f"zone_verification_{track}_{year}.json")},
            "forcing_inputs": {"fields": list(FIELDS), "observations_read": False}}


def decision_summary(results: dict) -> dict:
    out = {"rule": "Q3 analogue of the protocol rule: development interval of (strong - weak) excludes zero and the final-test point estimate has the same sign; "
                   "decision metrics heavy frequency bias and heavy CSI; descriptive only, does not change the Stage 3 recommendation of Q1/Q2",
           "tracks": {}}
    for track, (dev_year, final_year) in S1.PAIRS.items():
        dev, final = results[(track, dev_year)], results[(track, final_year)]
        rows, tests = [], 0
        for label, by_model in dev["q3"].items():
            for model, by_metric in by_model.items():
                for metric, d in by_metric.items():
                    if metric not in zv.Q3_DECISION:
                        continue
                    f = final["q3"].get(label, {}).get(model, {}).get(metric)
                    if d.get("status") != "ok" or not f or f.get("status") != "ok":
                        continue
                    tests += 1
                    same = bool(d["point"] * f["point"] > 0)
                    if d["excludes_zero"]:
                        rows.append({"stratum": label, "model": model, "metric": metric, "development_point": d["point"], "development_interval95": d["interval95"],
                                     "final_point": f["point"], "final_interval95": f["interval95"], "final_interval_excludes_zero": f["excludes_zero"],
                                     "same_sign": same, "forcing_gap": same})
        out["tracks"][track] = {"development_year": dev_year, "final_test_year": final_year, "tests": tests, "development_significant": len(rows),
                                "forcing_gaps": sum(r["forcing_gap"] for r in rows), "expected_development_significant_by_chance": round(0.05 * tests, 1),
                                "expected_gaps_by_chance": round(0.025 * tests, 1),
                                "caveat": "tests share cases and models and are strongly dependent; intervals are optimistic", "rows": rows}
    return out


def main() -> None:
    if sha(SPEC) != SPEC_SHA:
        raise SystemExit("Stage 2 spec hash mismatch: refusing to run")
    spec = json.loads(SPEC.read_text(encoding="utf-8"))
    if spec["parent"]["protocol_v3_sha256"] != S1.PROTOCOL_SHA or sha(S1.PROTOCOL) != S1.PROTOCOL_SHA:
        raise SystemExit("protocol hash mismatch")
    if spec["parent"]["static_geography_sha256"] != sha(S1.GEOGRAPHY) or spec["parent"]["stage1_manifest_sha256"] != sha(PHASE7 / "zone_verification_manifest.json"):
        raise SystemExit("geography or Stage 1 evidence does not match the spec: refusing to run")
    geography = json.loads(S1.GEOGRAPHY.read_text(encoding="utf-8"))
    masks = zv.zone_masks(geography["fields"]["zone"])
    geometry = geometry_of(geography)
    atmosphere = Atmosphere(geography)
    builder = S1.load_phase6_builder()
    fits = {}
    for track in ("A", "B"):
        fits[track] = fit_cut_points(track, atmosphere, geometry, masks)
        cps = {k: (round(v["q33"], 1), round(v["q67"], 1)) for k, v in fits[track]["cut_points"].items()}
        print(f"Track {track}: cut-points fitted on {fits[track]['year']} ({fits[track]['cases_used']}/{fits[track]['cases_listed']} cases): {cps}", flush=True)
    results, files = {}, {}
    plan = [("A", 2018, "VALIDATION"), ("A", 2019, "FINAL_TEST"), ("B", 2024, None), ("B", 2025, None)]
    for track, year, role in plan:
        data = S1.load_track_a(year, role, builder) if track == "A" else S1.load_track_b(year)
        stage1 = json.loads((PHASE7 / f"zone_verification_{track}_{year}.json").read_text(encoding="utf-8"))
        result = analyse_year(track, year, data, atmosphere, geometry, masks, fits[track], stage1)
        results[(track, year)] = result
        name = f"zone_stage2_{track}_{year}.json"
        digest = write_once(PHASE7 / name, encode(result))
        files[name] = {"sha256": digest, "track": track, "year": year, "evidence_role": result["evidence_role"], "cases": result["case_count"], "reproduction": "REPRODUCED"}
        print(f"{track} {year}: {result['case_count']} cases, strata partition zones and reproduce Stage 1 -> {name}", flush=True)
    summary = decision_summary(results)
    files["zone_stage2_summary.json"] = {"sha256": write_once(PHASE7 / "zone_stage2_summary.json", encode(summary)),
                                         "evidence_role": "Q3_RULE_APPLICATION_DEVELOPMENT_PLUS_POST_HOC", "cases": None, "reproduction": "n/a"}
    manifest = {"schema": "phase7-zone-stage2-manifest-v1", "spec_sha256": SPEC_SHA, "protocol_sha256": S1.PROTOCOL_SHA, "static_geography_sha256": sha(S1.GEOGRAPHY), "files": files,
                "notes": ["Read-only re-aggregation of frozen artifacts; no model was trained, tuned or selected.",
                          "Consumed holdouts (Track A 2019, Track B 2025) are post-hoc descriptive analyses only.",
                          "Forcing uses forecast U850, V850, PWAT and static geometry only; cut-points come from the training year only."]}
    data = encode(manifest)
    digest = write_once(PHASE7 / "zone_stage2_manifest.json", data)
    (PHASE7 / "zone_stage2_manifest.sha256").write_text(digest + "\n", encoding="ascii")
    for track, block in summary["tracks"].items():
        print(f"Track {track}: {block['tests']} Q3 decision tests, {block['development_significant']} development-significant "
              f"(chance ~{block['expected_development_significant_by_chance']}), {block['forcing_gaps']} gaps (chance ~{block['expected_gaps_by_chance']})")


if __name__ == "__main__":
    main()
