"""Build or verify local-only east-coast static mask and district weights.

The development protocol must already be frozen. This command reads only the
pinned 2021 geometry, never forecasts, models, reanalysis or observations.
Its geometry is unsuitable for an official or distributed district product.
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

from backend.app.live.india_stages import FIRST_STAGE, GRID_SHAPE, IMD_LAT, IMD_LON, stage_mask  # noqa: E402
from backend.app.ml.phase2c import district_weights  # noqa: E402

BASE = ROOT / "data/manifests/research_pilot"
PROTOCOL = BASE / "east_coast_development_protocol_v1.json"
GEOMETRY = ROOT / "data/static/phase2c/geoBoundaries-IND-ADM2_simplified.geojson"
OUTPUT = ROOT / "data/processed/east_coast_static_v1"
MANIFEST = BASE / "east_coast_static_v1.json"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def protocol() -> tuple[dict, str]:
    digest = sha256(PROTOCOL)
    if PROTOCOL.with_suffix(".sha256").read_text(encoding="ascii").split() != [digest, PROTOCOL.name]:
        raise ValueError("development protocol hash is not frozen")
    data = json.loads(PROTOCOL.read_text(encoding="utf-8"))
    if data["stage"] != FIRST_STAGE or data["status"] != "PROTOCOL_FROZEN_BEFORE_STAGE_FIT_OR_PAIRING":
        raise ValueError("wrong stage or protocol status")
    if sha256(GEOMETRY) != data["geometry"]["source_sha256"]:
        raise ValueError("pinned geometry hash mismatch")
    return data, digest


def build() -> dict:
    data, protocol_hash = protocol()
    if OUTPUT.exists() or MANIFEST.exists() or MANIFEST.with_suffix(".sha256").exists():
        raise FileExistsError("stage static artifacts are write-once")
    stage_grid = data["grid"]
    lat_idx = np.flatnonzero((IMD_LAT >= stage_grid["latitude_start"]) & (IMD_LAT <= stage_grid["latitude_end"]))
    lon_idx = np.flatnonzero((IMD_LON >= stage_grid["longitude_start"]) & (IMD_LON <= stage_grid["longitude_end"]))
    districts, regional_weights = district_weights(GEOMETRY, IMD_LAT[lat_idx], IMD_LON[lon_idx])
    if regional_weights.shape != (len(districts), len(lat_idx) * len(lon_idx)):
        raise ValueError("regional district-weight shape mismatch")
    district_support = np.any(regional_weights > 0, axis=1)
    districts = [districts[i] for i in np.flatnonzero(district_support)]
    regional_weights = regional_weights[district_support]
    weights = np.zeros((len(districts), GRID_SHAPE[0] * GRID_SHAPE[1]), dtype=np.float32)
    pixel = np.array([int(i) * GRID_SHAPE[1] + int(j) for i in lat_idx for j in lon_idx])
    weights[:, pixel] = regional_weights
    mask = np.any(weights > 0, axis=0).reshape(GRID_SHAPE)
    if not mask.any() or not np.array_equal(stage_mask(FIRST_STAGE, mask), mask):
        raise ValueError("static mask escapes the frozen east-coast partition")
    if any(not name for name in (district["district_id"] for district in districts)) or len({d["district_id"] for d in districts}) != len(districts):
        raise ValueError("district identities are missing or duplicated")
    OUTPUT.mkdir(parents=True)
    np.save(OUTPUT / "land_mask.npy", mask, allow_pickle=False)
    np.save(OUTPUT / "district_weights.npy", weights, allow_pickle=False)
    (OUTPUT / "districts.json").write_text(json.dumps([
        {"district_id": d["district_id"], "district_name": d["district_name"]} for d in districts
    ], indent=2, sort_keys=True) + "\n", encoding="utf-8")
    manifest = {
        "schema": "varshasetu-east-coast-static-v1",
        "status": "LOCAL_RESEARCH_GEOMETRY_ONLY_NOT_OFFICIAL_NOT_PUBLISHED",
        "protocol_sha256": protocol_hash,
        "source_geometry_sha256": data["geometry"]["source_sha256"],
        "stage": FIRST_STAGE,
        "grid_shape": list(GRID_SHAPE),
        "latitude_indices": [int(lat_idx[0]), int(lat_idx[-1])],
        "longitude_indices": [int(lon_idx[0]), int(lon_idx[-1])],
        "static_land_cells": int(mask.sum()),
        "districts_intersecting_stage": len(districts),
        "files": {name: sha256(OUTPUT / name) for name in ("land_mask.npy", "district_weights.npy", "districts.json")},
        "forecast_values_read": False,
        "observation_values_read": False,
        "model_fitted": False,
        "paired_or_scored": False,
    }
    payload = (json.dumps(manifest, indent=2, sort_keys=True) + "\n").encode("utf-8")
    with MANIFEST.open("xb") as stream:
        stream.write(payload)
    MANIFEST.with_suffix(".sha256").write_text(f"{sha256(MANIFEST)}  {MANIFEST.name}\n", encoding="ascii")
    return manifest


def check() -> dict:
    data, protocol_hash = protocol()
    expected = MANIFEST.with_suffix(".sha256").read_text(encoding="ascii").split()
    if expected != [sha256(MANIFEST), MANIFEST.name]:
        raise ValueError("static manifest receipt mismatch")
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    if manifest["protocol_sha256"] != protocol_hash or manifest["source_geometry_sha256"] != data["geometry"]["source_sha256"]:
        raise ValueError("static lineage mismatch")
    for name, digest in manifest["files"].items():
        if sha256(OUTPUT / name) != digest:
            raise ValueError(f"static file hash mismatch: {name}")
    mask = np.load(OUTPUT / "land_mask.npy", allow_pickle=False)
    weights = np.load(OUTPUT / "district_weights.npy", allow_pickle=False, mmap_mode="r")
    districts = json.loads((OUTPUT / "districts.json").read_text(encoding="utf-8"))
    if (mask.shape != GRID_SHAPE or mask.dtype != np.bool_ or not np.array_equal(stage_mask(FIRST_STAGE, mask), mask)
            or int(mask.sum()) != manifest["static_land_cells"] or len(districts) != manifest["districts_intersecting_stage"]
            or weights.shape != (len(districts), mask.size) or np.any(weights[:, ~mask.ravel()] != 0)
            or np.any(weights < 0)):
        raise ValueError("static geometry shape, support or mask mismatch")
    return {"status": "VERIFIED_LOCAL_RESEARCH_STATIC", "static_land_cells": int(mask.sum()), "districts": len(districts)}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--build", action="store_true")
    group.add_argument("--check", action="store_true")
    args = parser.parse_args()
    print(json.dumps(build() if args.build else check(), sort_keys=True))


if __name__ == "__main__":
    main()
