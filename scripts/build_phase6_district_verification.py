"""Build the district-level verification evidence (protocol v1, docs/112) for Track B 2024 and 2025.

Read-only re-aggregation of FROZEN artifacts with the pinned Phase 2C district weights. Nothing is trained, tuned or selected.
The protocol was approved and hash-frozen before this script was run; the script refuses to run against any other protocol hash.

  2024 - validation/selection year (development evidence)
  2025 - consumed final test: POST-HOC EXPLORATORY ANALYSIS OF THE COMPLETED 2025 FINAL TEST

A reproduction gate must pass before anything is written (see ``reproduction``). Outputs are write-once.

    python scripts/build_phase6_district_verification.py
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

from backend.app.api import operational as op  # noqa: E402
from backend.app.ml.district_verification import (CORRECTED, MIN_CELLS, MODELS, Stack, analyse_districts,  # noqa: E402
                                                  case_district_stats)

EVIDENCE = ROOT / "backend/app/evidence_data/phase6"
PROTOCOL = EVIDENCE / "district_verification_protocol_v1.json"
PROTOCOL_SHA = "9b348063a6ac654e88a822694fd199d2f432d5d6b0bebafc19567f6be6e53365"
ROLES = {2024: "PHASE4I_VALIDATION_SELECTION_YEAR_DEVELOPMENT_EVIDENCE", 2025: "PHASE4J_HOLDOUT_CONSUMED_POST_HOC_DESCRIPTIVE_ONLY"}
REGIME_TEXT = ("argmax of the frozen forecast-only pseudo-regime classifier probability (M3 hard-routes on exactly this class); "
               "pseudo-labels, not observed meteorological truth")
REPEATS = 2000
SEED = 26080


def sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def clean(value):
    """NaN/inf -> None so the evidence is valid strict JSON (an undefined value is never written as 0)."""
    if isinstance(value, dict):
        return {k: clean(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [clean(v) for v in value]
    if isinstance(value, (np.floating, float)):
        return None if not np.isfinite(value) else float(value)
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.bool_,)):
        return bool(value)
    return value


def encode(value) -> bytes:
    return (json.dumps(clean(value), sort_keys=True, indent=2, ensure_ascii=False, allow_nan=False) + "\n").encode("utf-8")


def write_once(path: Path, data: bytes) -> str:
    if path.exists() and path.read_bytes() != data:
        raise RuntimeError(f"frozen district-verification evidence would change: {path}")
    path.write_bytes(data)
    return hashlib.sha256(data).hexdigest()


def district_latitudes(districts: list[dict]) -> np.ndarray:
    """Centroid latitude of each district polygon clipped to the 10-22N, 68-80E domain box (protocol region_rule)."""
    from shapely.geometry import box, shape

    geometry = json.loads((op.TRACK_A_ARTIFACTS / "districts.geojson").read_text(encoding="utf-8"))
    domain = box(68.0, 10.0, 80.0, 22.0)
    by_id = {f["properties"]["district_id"]: f["geometry"] for f in geometry["features"]}
    out = []
    for d in districts:
        polygon = shape(by_id[d["district_id"]])
        if not polygon.is_valid:
            polygon = polygon.buffer(0)
        clipped = polygon.intersection(domain)
        out.append(float((clipped if not clipped.is_empty else polygon).centroid.y))
    return np.array(out)


def lineage(year: int) -> dict:
    if year == 2025:
        base = op.PHASE4J
        files = {f"predictions/{m}.npy": base / f"predictions/{m}.npy" for m in MODELS}
        files.update({"pairing/observation_mm.npy": base / "pairing/observation_mm.npy", "pairing/pixel_index.npy": base / "pairing/pixel_index.npy"})
    else:
        files = {f"phase4i/deterministic_models/{m}_2024.npy": op.PHASE4I / f"deterministic_models/{m}_2024.npy" for m in MODELS}
        root = op.PHASE4G_ROOT / "2024" / "validation" / "deterministic"
        files.update({"phase4g/y_mm.npy": root / "y_mm.npy", "phase4g/pixel_index.npy": root / "pixel_index.npy"})
    return {name: sha(path) for name, path in files.items()}


def build_stack(year: int, districts, weights) -> tuple[Stack, np.ndarray]:
    case_ids = sorted(op._paired_cases_by_id(year))
    per_case, regimes = [], []
    loader = op._REGIME_LOADER[year]()
    for case_id in case_ids:
        base = op._district_case_fields(year, case_id, "m1", False)
        fields = {"obs": base["observed"], "M0": base["raw"], "M1": base["corrected"]}
        for model in ("m2", "m3", "m4"):
            other = op._district_case_fields(year, case_id, model, False)
            if not (np.array_equal(other["raw"], base["raw"], equal_nan=True) and np.array_equal(other["observed"], base["observed"], equal_nan=True)):
                raise RuntimeError(f"{case_id}: Raw/IMD differ between model loads")
            fields[model.upper()] = other["corrected"]
        per_case.append(case_district_stats(weights, fields))
        vector = loader.get(case_id)
        if vector is None:
            raise RuntimeError(f"{case_id}: no frozen regime probability")
        regimes.append(int(np.argmax(vector)))
    stack = Stack(per_case, case_ids, [d["district_id"] for d in districts], [d["district_name"] for d in districts],
                  district_latitudes(districts), np.array(regimes))
    return stack, np.array(case_ids)


def reproduction(year: int, stack: Stack, result: dict, districts, weights, protocol: dict) -> dict:
    checks = []

    def expect(label, got, want):
        ok = got == want
        checks.append({"check": label, "got": got, "expected": want, "ok": bool(ok)})
        if not ok:
            raise RuntimeError(f"reproduction gate failed: {label}: got {got}, expected {want}")

    # (a) the protocol's observation-only support counts must be reproduced exactly
    want = protocol["observation_only_support_counts"][str(year)]
    expect("district_case_pairs", result["inclusion"]["district_case_pairs"], want["district_case_pairs"])
    expect("districts_included", result["inclusion"]["districts_included"], protocol["observation_only_support_counts"]["districts_kept"])
    for key in ("heavy", "very_heavy"):
        for definition in ("E1", "E2", "E3"):
            expect(f"observed_events/{definition}/{key}", result["observed_events_pooled"][definition][key], want[key][definition]["event_pairs"])
    # (b) per-district observed events sum to the pooled count
    for definition in ("E1", "E2"):
        for key in ("heavy", "very_heavy"):
            expect(f"district_sum/{definition}/{key}", sum(e["categorical"][definition][key]["observed_events"] for e in result["districts"]),
                   result["observed_events_pooled"][definition][key])
    # (c) district means equal means recomputed from the ALREADY-SERVED 49x49 rainfall grids (independent path, API code)
    from fastapi.testclient import TestClient

    from backend.main import app

    client = TestClient(app)
    field_of = {"obs": "imd", "M0": "raw", "M1": "m1", "M2": "m2", "M3": "m3", "M4": "m4"}
    sample = np.linspace(0, len(stack.case_ids) - 1, 8).astype(int)
    worst = 0.0
    for ci in sample:
        grids = {}
        for name, endpoint in field_of.items():
            response = client.get(f"/api/science/operational/{year}/cases/{stack.case_ids[ci]}/rainfall", params={"field": endpoint})
            if response.status_code != 200:
                raise RuntimeError(response.text)
            grids[name] = np.array([[np.nan if v is None else v for v in row] for row in response.json()["values"]], float).ravel()
        valid = np.logical_and.reduce([np.isfinite(g) for g in grids.values()])
        for d in range(weights.shape[0]):
            active = (weights[d] > 0) & valid
            if not active.any():
                continue
            q = weights[d][active].astype(float) / weights[d][active].astype(float).sum()
            for name in field_of:
                diff = abs(float(q @ grids[name][active]) - float(stack.mean[name][ci, d]))
                worst = max(worst, diff)
    checks.append({"check": "district_means_vs_served_grids", "cases_sampled": int(len(sample)), "max_abs_diff_mm": worst, "ok": worst < 1e-3})
    if worst >= 1e-3:
        raise RuntimeError(f"reproduction gate failed: district means differ from served grids by {worst} mm")
    # (d) pooled Raw district-mean RMSE: vectorised path vs an independent per-pair loop
    total = count = 0.0
    for c in range(stack.cells.shape[0]):
        for d in range(stack.cells.shape[1]):
            if stack.included[c, d]:
                total += (float(stack.mean["M0"][c, d]) - float(stack.mean["obs"][c, d])) ** 2
                count += 1
    loop = float(np.sqrt(total / count))
    vectorised = result["continuous"]["pooled"]["all"]["M0"]["rmse_mm"]
    checks.append({"check": "pooled_raw_rmse_loop_vs_vectorised", "loop": loop, "vectorised": vectorised, "ok": abs(loop - vectorised) < 1e-9})
    if abs(loop - vectorised) >= 1e-9:
        raise RuntimeError("reproduction gate failed: pooled Raw RMSE loop differs from the vectorised value")
    return {"status": "REPRODUCED", "check_count": len(checks), "checks": checks}


def main() -> None:
    if sha(PROTOCOL) != PROTOCOL_SHA:
        raise RuntimeError("district verification protocol is not the approved, frozen version")
    protocol = json.loads(PROTOCOL.read_text(encoding="utf-8"))
    if protocol["status"] != "APPROVED_FOR_EXECUTION":
        raise RuntimeError("protocol is not approved")
    districts, weights, weights_sha, geometry_sha = op._district_static()
    files = {}
    for year in (2024, 2025):
        stack, _ = build_stack(year, districts, weights)
        result = analyse_districts(stack, op.REGIME_CLASSES, repeats=REPEATS, seed=SEED)
        result["reproduction"] = reproduction(year, stack, result, districts, weights, protocol)
        result.update({"schema": "phase6-district-verification-v1", "track": "B", "year": year, "evidence_role": ROLES[year],
                       "protocol_sha256": PROTOCOL_SHA, "regime_assignment": REGIME_TEXT, "models": list(MODELS), "corrected_models": list(CORRECTED),
                       "weights_sha256": weights_sha, "geometry_sha256": geometry_sha, "lineage_sha256": lineage(year),
                       "bootstrap": {"repeats": REPEATS, "seed": SEED, "resampling": "whole cases (all districts of a case together)"},
                       "min_valid_cells": MIN_CELLS})
        name = f"district_verification_B_{year}.json"
        digest = write_once(EVIDENCE / name, encode(result))
        files[name] = {"sha256": digest, "track": "B", "year": year, "evidence_role": ROLES[year], "cases": result["inclusion"]["cases"],
                       "district_case_pairs": result["inclusion"]["district_case_pairs"], "districts_included": result["inclusion"]["districts_included"],
                       "reproduction": result["reproduction"]["status"]}
        print(f"{year}: {result['inclusion']['cases']} cases, {result['inclusion']['district_case_pairs']} district-case pairs, "
              f"{result['inclusion']['districts_included']} districts; reproduction {result['reproduction']['status']} "
              f"({result['reproduction']['check_count']} checks) -> {name}", flush=True)
    manifest = {"schema": "phase6-district-verification-manifest-v1", "protocol_sha256": PROTOCOL_SHA, "files": files,
                "notes": ["Read-only re-aggregation of frozen artifacts under protocol v1 (docs/112); no model was trained, tuned or selected.",
                          "2025 is a consumed holdout: post-hoc descriptive analysis only.",
                          "Regimes are forecast-only pseudo-labels, not observed meteorological truth."]}
    digest = write_once(EVIDENCE / "district_verification_manifest.json", encode(manifest))
    (EVIDENCE / "district_verification_manifest.sha256").write_text(digest + "\n", encoding="ascii", newline="\n")
    print(f"district_verification_manifest.json sha256 {digest}")


if __name__ == "__main__":
    main()
