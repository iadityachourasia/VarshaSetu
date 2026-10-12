"""Local-only research district weights and coverage; never an official boundary product."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
from scipy.sparse import csr_matrix, save_npz, load_npz

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.app.ml.nationwide_research import GRID_SHAPE, LATITUDE, LONGITUDE  # noqa: E402
from backend.app.ml.phase2c import district_weights  # noqa: E402
from scripts.nationwide_research import BASE, GEOMETRY, OUT, PROTOCOL, STATIC, _preflight, receipt, sha, write_json  # noqa: E402

DESTINATION = OUT / "district_research"
MANIFEST = BASE / "nationwide_district_research_v1.json"


def build() -> dict:
    protocol, mask = _preflight()
    if MANIFEST.exists() or DESTINATION.exists():
        raise FileExistsError("national research district weights are write-once")
    if protocol["sources"]["static_manifest_sha256"] != receipt(STATIC):
        raise ValueError("static research lineage mismatch")
    districts, dense = district_weights(GEOMETRY, LATITUDE, LONGITUDE)
    if dense.shape != (len(districts), mask.size) or len(districts) != 735:
        raise ValueError("district geometry count or weight grid changed")
    if np.any(dense[:, ~mask.ravel()] > 0) or np.any(dense < 0):
        raise ValueError("district overlap weights escape national land footprint")
    represented = np.sum(dense, axis=1) > 0
    ids = [districts[i]["district_id"] for i in np.flatnonzero(represented)]
    names = [districts[i]["district_name"] for i in np.flatnonzero(represented)]
    if not ids or len(ids) != len(set(ids)):
        raise ValueError("district identity/coverage invalid")
    DESTINATION.mkdir(parents=True)
    matrix = csr_matrix(dense[represented], dtype=np.float32)
    weights_file = DESTINATION / "weights.npz"
    save_npz(weights_file, matrix, compressed=True)
    table_file = DESTINATION / "districts.json"
    table_file.write_text(json.dumps([{"district_id": a, "district_name": b} for a, b in zip(ids, names)],
                                     indent=2, sort_keys=True) + "\n", encoding="utf-8")
    manifest = {"schema": "nationwide-research-district-weights-v1",
                "status": "LOCAL_RESEARCH_ONLY_NONOFFICIAL_GEOMETRY_RIGHTS_OPEN",
                "protocol_sha256": sha(PROTOCOL), "static_sha256": sha(STATIC),
                "geometry_sha256": sha(GEOMETRY), "grid_shape": list(GRID_SHAPE),
                "source_features": 735, "represented_districts": len(ids),
                "unrepresented_districts": [districts[i]["district_id"] for i in np.flatnonzero(~represented)],
                "weights_shape": list(matrix.shape), "nonzero_weights": int(matrix.nnz),
                "files": {"weights.npz": sha(weights_file), "districts.json": sha(table_file)},
                "weights_meaning": "cos(latitude)-adjusted polygon/grid-cell overlap; not official area or boundary",
                "observation_values_read": False, "model_fitted": False,
                "redistribution_rights_cleared": False, "public_district_product_allowed": False}
    digest = write_json(MANIFEST, manifest)
    return {"status": manifest["status"], "represented_districts": len(ids),
            "unrepresented_districts": len(manifest["unrepresented_districts"]), "manifest_sha256": digest}


def check() -> dict:
    receipt(MANIFEST)
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    _, mask = _preflight()
    if manifest["protocol_sha256"] != receipt(PROTOCOL) or manifest["static_sha256"] != receipt(STATIC):
        raise ValueError("national research district lineage mismatch")
    for name, digest in manifest["files"].items():
        if sha(DESTINATION / name) != digest:
            raise ValueError(f"district research file changed: {name}")
    weights = load_npz(DESTINATION / "weights.npz")
    rows = json.loads((DESTINATION / "districts.json").read_text(encoding="utf-8"))
    if weights.shape != (len(rows), mask.size) or weights.nnz != manifest["nonzero_weights"] or len(rows) != manifest["represented_districts"]:
        raise ValueError("research district matrix/table mismatch")
    return {"status": manifest["status"], "represented_districts": len(rows), "sha256": sha(MANIFEST)}


if __name__ == "__main__":
    command = sys.argv[1] if len(sys.argv) == 2 else ""
    if command not in ("build", "check"):
        raise SystemExit("usage: build_nationwide_district_research.py build|check")
    print(json.dumps(build() if command == "build" else check(), sort_keys=True))
