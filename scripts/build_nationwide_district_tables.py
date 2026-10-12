"""Forecast-only 2024 research district tables from sealed national predictions."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
from scipy.sparse import load_npz

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.build_nationwide_district_research import DESTINATION, MANIFEST as STATIC_MANIFEST, check as check_static  # noqa: E402
from scripts.nationwide_research import BASE, OUT, PROTOCOL, SEAL, _preflight, receipt, sha, write_json  # noqa: E402

TABLES = OUT / "district_tables"
MANIFEST = BASE / "nationwide_district_tables_v1.json"
FIELDS = ("M0", "M1", "M2", "M3", "M4", "heavy_p", "very_heavy_p")


def build() -> dict:
    _, mask = _preflight()
    check_static()
    if MANIFEST.exists() or TABLES.exists():
        raise FileExistsError("national research district tables are write-once")
    if receipt(SEAL) != sha(SEAL):
        raise ValueError("national prediction seal changed")
    seal = json.loads(SEAL.read_text(encoding="utf-8"))
    if seal["protocol_sha256"] != receipt(PROTOCOL):
        raise ValueError("national model/geometry protocol mismatch")
    weights = load_npz(DESTINATION / "weights.npz").tocsr()
    districts = json.loads((DESTINATION / "districts.json").read_text(encoding="utf-8"))
    if weights.shape != (len(districts), mask.size):
        raise ValueError("national district weight grid mismatch")
    denominator = np.asarray(weights.sum(axis=1)).ravel()
    if np.any(denominator <= 0):
        raise ValueError("district without sampled grid area")
    coverage = np.asarray(weights @ mask.ravel().astype(np.float32)).ravel() / denominator
    TABLES.mkdir(parents=True)
    receipts = []
    for prediction in seal["predictions"]:
        source = ROOT / prediction["file"]
        if sha(source) != prediction["sha256"]:
            raise ValueError(f"prediction changed: {prediction['case_id']}")
        with np.load(source, allow_pickle=False) as saved:
            if set(saved.files) != set(FIELDS):
                raise ValueError("district prediction fields missing")
            field_values = {}
            for field in FIELDS:
                value = saved[field]
                if value.shape != (int(mask.sum()),) or not np.isfinite(value).all() or np.any(value < 0):
                    raise ValueError(f"invalid district forecast: {prediction['case_id']}, {field}")
                full = np.zeros(mask.size, dtype=np.float32)
                full[mask.ravel()] = value
                field_values[field] = np.asarray(weights @ full).ravel() / denominator
        rows = []
        for index, district in enumerate(districts):
            supported = bool(coverage[index] >= 0.95)
            rows.append({"district_id": district["district_id"], "district_name": district["district_name"],
                         "weighted_grid_coverage_fraction": float(coverage[index]), "supported": supported,
                         **{field: float(field_values[field][index]) if supported else None for field in FIELDS}})
        file = TABLES / f"{prediction['case_id']}.json"
        file.write_text(json.dumps({"case_id": prediction["case_id"], "source_track": "B_OPERATIONAL_GEFS",
                                    "research_geometry_only": True, "rows": rows},
                                   sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
        receipts.append({"case_id": prediction["case_id"], "file": file.relative_to(ROOT).as_posix(),
                         "sha256": sha(file), "supported_districts": sum(r["supported"] for r in rows)})
    manifest = {"schema": "nationwide-forecast-only-district-tables-v1",
                "status": "2024_DEVELOPMENT_RESEARCH_ONLY_NOT_OFFICIAL",
                "protocol_sha256": sha(PROTOCOL), "fit_seal_sha256": sha(SEAL),
                "district_weights_manifest_sha256": receipt(STATIC_MANIFEST),
                "case_tables": receipts, "district_rows_per_case": len(districts),
                "coverage_rule": "at least 95% of sampled overlap weight on valid forecast cells",
                "geometry_rights_cleared": False, "public_product_allowed": False,
                "reference_values_read": False, "model_fitted": False}
    digest = write_json(MANIFEST, manifest)
    return {"status": manifest["status"], "cases": len(receipts), "districts": len(districts), "manifest_sha256": digest}


def check() -> dict:
    receipt(MANIFEST)
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    if manifest["fit_seal_sha256"] != receipt(SEAL) or manifest["district_weights_manifest_sha256"] != receipt(STATIC_MANIFEST):
        raise ValueError("research district table lineage mismatch")
    for row in manifest["case_tables"]:
        if sha(ROOT / row["file"]) != row["sha256"]:
            raise ValueError(f"district table changed: {row['case_id']}")
    if manifest["public_product_allowed"] or manifest["reference_values_read"]:
        raise ValueError("unsupported district/public claim")
    return {"status": manifest["status"], "cases": len(manifest["case_tables"]), "sha256": sha(MANIFEST)}


if __name__ == "__main__":
    command = sys.argv[1] if len(sys.argv) == 2 else ""
    if command not in ("build", "check"):
        raise SystemExit("usage: build_nationwide_district_tables.py build|check")
    print(json.dumps(build() if command == "build" else check(), sort_keys=True))
