"""Verify two bounded forecast-only east-coast feature cases after protocol freeze.

This is a feasibility probe, not a training population or skill result. It
reads hash-verified GEFS rainfall and atmospheric arrays only. It never opens
IMD, targets, model predictions or 2026 data.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.app.live.india_stages import GRID_SHAPE, IMD_LAT, IMD_LON  # noqa: E402
from backend.app.ml.forecast_regimes import ATMOSPHERIC_VARIABLES, extract_regime_features  # noqa: E402
from backend.app.ml.phase2b import FEATURE_NAMES, bilinear_to_target  # noqa: E402
from scripts.build_east_coast_static import BASE, OUTPUT as STATIC, check as check_static, sha256  # noqa: E402

SOURCE = ROOT / "experiments/recent_historical/phase4f_payload_acquisition_v1"
RAW_LEDGER = ROOT / "backend/app/evidence_data/phase14/all_india_raw_ledger_v1.json"
RAW_PROTOCOL = ROOT / "backend/app/evidence_data/phase14/all_india_raw_protocol_v1.json"
REPORT = BASE / "east_coast_feature_probe_v1.json"
CASES = ((2023, "20230601_day1_24h", 24), (2024, "20240601_day2_24h", 48))
CONTEXT_LAT = np.linspace(5.0, 30.0, 51)
CONTEXT_LON = np.linspace(55.0, 95.0, 81)


def digest_array(value: np.ndarray) -> str:
    return hashlib.sha256(np.ascontiguousarray(value).tobytes()).hexdigest()


def case_probe(year: int, case_id: str, hour: int, mask: np.ndarray, ledger: dict,
               *, with_matrix: bool = False):
    rows = [row for row in ledger["populations"][str(year)] if row["case_id"] == case_id]
    if len(rows) != 1 or rows[0]["status"] != "INCLUDED":
        raise ValueError(f"Raw stage case not admitted: {case_id}")
    raw_path = ROOT / rows[0]["path"]
    if sha256(raw_path) != rows[0]["sha256"]:
        raise ValueError(f"Raw array hash mismatch: {case_id}")
    raw = np.load(raw_path, allow_pickle=False)
    if raw.shape != GRID_SHAPE:
        raise ValueError("Raw grid shape mismatch")
    source_manifest_path = SOURCE / "manifests" / f"{year}_source_manifest.json"
    source_manifest_sha = sha256(source_manifest_path)
    if source_manifest_path.with_suffix(".sha256").read_text(encoding="ascii").split() != [source_manifest_sha]:
        raise ValueError("atmospheric source manifest receipt mismatch")
    source_manifest = json.loads(source_manifest_path.read_text(encoding="utf-8"))
    day = case_id[:8]
    fields, hashes = [], {}
    for name in ATMOSPHERIC_VARIABLES:
        path = SOURCE / "atmospheric_qc" / str(year) / day / f"{name}_f{hour:03d}.npy"
        relative = path.relative_to(ROOT).as_posix()
        entry = source_manifest["files"].get(relative)
        if entry is None or sha256(path) != entry["sha256"] or path.stat().st_size != entry["bytes"]:
            raise ValueError(f"atmospheric cache hash mismatch: {case_id}, {name}")
        field = np.load(path, allow_pickle=False)
        if field.shape != (51, 81) or not np.isfinite(field).all():
            raise ValueError(f"atmospheric cache shape/values invalid: {case_id}, {name}")
        fields.append(field)
        hashes[name] = entry["sha256"]
    atmosphere = np.stack(fields)
    regime = extract_regime_features(atmosphere, CONTEXT_LAT, CONTEXT_LON)
    lat_idx, lon_idx = np.flatnonzero(mask.any(axis=1)), np.flatnonzero(mask.any(axis=0))
    latitude, longitude = IMD_LAT[lat_idx], IMD_LON[lon_idx]
    aligned = np.stack([bilinear_to_target(field, CONTEXT_LAT, CONTEXT_LON, latitude, longitude) for field in atmosphere])
    local_mask = mask[np.ix_(lat_idx, lon_idx)]
    local_raw = raw[np.ix_(lat_idx, lon_idx)]
    valid = local_mask & np.isfinite(local_raw) & (local_raw >= 0) & np.isfinite(aligned).all(axis=0)
    if not valid.any():
        raise ValueError(f"no valid forecast-only stage cells: {case_id}")
    lat_grid, lon_grid = np.meshgrid(latitude, longitude, indexing="ij")
    matrix = np.column_stack((local_raw[valid], aligned[:, valid].T,
        np.broadcast_to(regime, (int(valid.sum()), len(regime))), lat_grid[valid], lon_grid[valid],
        np.full(int(valid.sum()), hour, dtype=np.float64))).astype(np.float32)
    if matrix.shape != (int(valid.sum()), len(FEATURE_NAMES)) or not np.isfinite(matrix).all() or np.any(matrix[:, 0] < 0):
        raise ValueError("east-coast feature matrix invalid")
    report = {
        "case_id": case_id, "year_role": "fit_development" if year == 2023 else "consumed_selection_development",
        "lead_hours": hour, "source_manifest_sha256": source_manifest_sha,
        "raw_sha256": rows[0]["sha256"], "atmospheric_array_sha256": hashes,
        "static_land_cells": int(mask.sum()), "forecast_valid_cells": int(valid.sum()),
        "feature_columns": len(FEATURE_NAMES), "feature_names": list(FEATURE_NAMES),
        "feature_matrix_value_sha256": digest_array(matrix),
    }
    if with_matrix:
        full_valid = np.zeros(GRID_SHAPE, dtype=bool)
        full_valid[np.ix_(lat_idx, lon_idx)] = valid
        return report, matrix, full_valid, raw
    return report


def build() -> dict:
    if REPORT.exists() or REPORT.with_suffix(".sha256").exists():
        raise FileExistsError("feature probe is write-once")
    check_static()
    protocol = json.loads(RAW_PROTOCOL.read_text(encoding="utf-8"))
    if sha256(RAW_LEDGER) != protocol["definition"]["ledger_file_sha256"]:
        raise ValueError("all-India Raw ledger hash mismatch")
    ledger = json.loads(RAW_LEDGER.read_text(encoding="utf-8"))
    mask = np.load(STATIC / "land_mask.npy", allow_pickle=False)
    report = {
        "schema": "varshasetu-east-coast-forecast-feature-probe-v1",
        "status": "TWO_CASE_FORECAST_ONLY_FEASIBILITY_NO_TRAINING_OR_SKILL",
        "development_protocol_sha256": sha256(BASE / "east_coast_development_protocol_v1.json"),
        "static_manifest_sha256": sha256(BASE / "east_coast_static_v1.json"),
        "raw_ledger_sha256": sha256(RAW_LEDGER),
        "cases": [case_probe(year, case, hour, mask, ledger) for year, case, hour in CASES],
        "observation_values_read": False, "model_fitted": False, "reference_paired": False,
        "independent_skill_claim": False,
    }
    REPORT.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    REPORT.with_suffix(".sha256").write_text(f"{sha256(REPORT)}  {REPORT.name}\n", encoding="ascii")
    return report


def check() -> dict:
    if REPORT.with_suffix(".sha256").read_text(encoding="ascii").split() != [sha256(REPORT), REPORT.name]:
        raise ValueError("feature-probe receipt mismatch")
    report = json.loads(REPORT.read_text(encoding="utf-8"))
    if report["development_protocol_sha256"] != sha256(BASE / "east_coast_development_protocol_v1.json") or report["static_manifest_sha256"] != sha256(BASE / "east_coast_static_v1.json"):
        raise ValueError("feature-probe lineage mismatch")
    if report["observation_values_read"] or report["model_fitted"] or report["reference_paired"]:
        raise ValueError("forecast-only feature probe was contaminated")
    check_static()
    raw_protocol = json.loads(RAW_PROTOCOL.read_text(encoding="utf-8"))
    if sha256(RAW_LEDGER) != raw_protocol["definition"]["ledger_file_sha256"] or report["raw_ledger_sha256"] != sha256(RAW_LEDGER):
        raise ValueError("all-India Raw ledger hash mismatch")
    ledger = json.loads(RAW_LEDGER.read_text(encoding="utf-8"))
    mask = np.load(STATIC / "land_mask.npy", allow_pickle=False)
    reproduced = [case_probe(year, case, hour, mask, ledger) for year, case, hour in CASES]
    if reproduced != report["cases"]:
        raise ValueError("forecast-only feature probe did not reproduce")
    return {"status": "VERIFIED_FORECAST_ONLY_PROBE", "cases": len(report["cases"]),
            "valid_cells": [row["forecast_valid_cells"] for row in report["cases"]]}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--build", action="store_true")
    group.add_argument("--check", action="store_true")
    args = parser.parse_args()
    print(json.dumps(build() if args.build else check(), sort_keys=True))


if __name__ == "__main__":
    main()
