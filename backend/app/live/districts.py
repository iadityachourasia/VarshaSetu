"""Forecast-only district aggregation over the existing pinned regional geometry.

This module reads no observation and does no inference. It refuses a geometry or
weight file whose bytes differ from the frozen Phase 2C manifest.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from backend.app.live.bundle import BundleError, sha256_file
from backend.app.ml.phase2c import aggregate_districts

ARTIFACTS = Path(__file__).resolve().parents[3] / "data/manifests/phase2c"
GRID_CELLS = 49 * 49
MIN_REPRESENTED_COVERAGE = 0.95


def verified_weights(root: Path = ARTIFACTS) -> tuple[list[dict], np.ndarray, dict]:
    manifest_path = root / "artifact_manifest.json"
    sidecar = root / "artifact_manifest.sha256"
    if not manifest_path.is_file() or not sidecar.is_file() or sidecar.read_text(encoding="ascii").split()[0] != sha256_file(manifest_path):
        raise BundleError("district artifact manifest is missing or differs from its sidecar")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    for name in ("districts.geojson", "district_weights.npy"):
        path = root / name
        if not path.is_file() or sha256_file(path) != manifest["files"][name]:
            raise BundleError(f"district artifact hash mismatch: {name}")
    geometry = json.loads((root / "districts.geojson").read_text(encoding="utf-8"))
    districts = [feature["properties"] for feature in geometry["features"]]
    weights = np.load(root / "district_weights.npy", allow_pickle=False)
    if weights.shape != (len(districts), GRID_CELLS) or not np.isfinite(weights).all() or np.any(weights < 0):
        raise BundleError("district weight matrix is invalid")
    return districts, weights, {"geometry_sha256": manifest["files"]["districts.geojson"], "weights_sha256": manifest["files"]["district_weights.npy"]}


def aggregate_live(districts: list[dict], weights: np.ndarray, *, raw: np.ndarray, corrected: np.ndarray,
                   heavy_p: np.ndarray, very_heavy_p: np.ndarray) -> list[dict]:
    fields = [np.asarray(field, dtype=np.float64).reshape(-1) for field in (raw, corrected, heavy_p, very_heavy_p)]
    if any(field.shape != (GRID_CELLS,) for field in fields):
        raise BundleError("live district fields must be complete 49 by 49 grids")
    if weights.shape != (len(districts), GRID_CELLS) or not np.isfinite(weights).all() or np.any(weights < 0):
        raise BundleError("live district weights are invalid")
    if any(np.isinf(field).any() for field in fields):
        raise BundleError("live district fields contain infinite values")
    valid = np.logical_and.reduce([np.isfinite(field) for field in fields])
    if (any(np.any(field[valid] < 0) for field in fields)
            or any(np.any(field[valid] > 1) for field in fields[2:])):
        raise BundleError("live district fields contain out-of-range values")
    coverage = {}
    for district, row in zip(districts, weights):
        total = float(row.sum())
        coverage[district["district_id"]] = float(row[valid].sum() / total) if total > 0 else 0.0
    rows = aggregate_districts(districts, weights, *fields, mask=valid)
    return [{**row, "weighted_grid_coverage_fraction": coverage[row["district_id"]]}
            for row in rows if coverage[row["district_id"]] >= MIN_REPRESENTED_COVERAGE]


__all__ = ["verified_weights", "aggregate_live", "ARTIFACTS"]
