"""Build the bounded homepage fallback from frozen, hash-checked 2019 artifacts."""

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
PHASE2B = ROOT / "data/manifests/phase2b"
PHASE2C = ROOT / "data/manifests/phase2c"
OUTPUT = ROOT / "frontend-v2/src/lib/benchmarks/reforecast-2019-overview.json"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    b_manifest = json.loads((PHASE2B / "artifact_manifest.json").read_text(encoding="utf-8"))
    c_manifest_path = PHASE2C / "artifact_manifest.json"
    c_manifest_hash = (PHASE2C / "artifact_manifest.sha256").read_text(encoding="ascii").strip()
    if digest(c_manifest_path) != c_manifest_hash:
        raise ValueError("Phase 2C manifest hash mismatch")
    c_manifest = json.loads(c_manifest_path.read_text(encoding="utf-8"))
    b_results_path = PHASE2B / "2019_final_results.json"
    c_results_path = PHASE2C / "2019_final_results.json"
    b_hash = digest(b_results_path)
    c_hash = digest(c_results_path)
    if b_hash != b_manifest["test_results_sha256"] or c_hash != c_manifest["files"]["2019_final_results.json"]:
        raise ValueError("Frozen 2019 results hash mismatch")

    b_results = json.loads(b_results_path.read_text(encoding="utf-8"))
    c_results = json.loads(c_results_path.read_text(encoding="utf-8"))
    count = c_results["case_count"]
    raw = b_results["test_results"]["M0_RAW_GEFS"]
    corrected = b_results["test_results"]["M2_GLOBAL_XGBOOST"]
    if b_results["test_common_case_count"] != count or len(c_results["case_metadata"]) != count:
        raise ValueError("2019 case populations differ")
    if raw["same_case_count"] != count or corrected["same_case_count"] != count:
        raise ValueError("2019 model populations differ")

    snapshot = {
        "source": "frozen Phase 2B/2C artifacts",
        "artifact_manifest_sha256": c_manifest_hash,
        "phase2b_results_sha256": b_hash,
        "phase2c_results_sha256": c_hash,
        "case_count": count,
        "raw_rmse_mm": raw["overall"]["continuous"]["rmse_mm"],
        "corrected_rmse_mm": corrected["overall"]["continuous"]["rmse_mm"],
        "cases": [
            {key: case[key] for key in ("case_id", "initialization_utc", "raw_rmse_mm", "corrected_rmse_mm")}
            for case in c_results["case_metadata"]
        ],
    }
    OUTPUT.write_text(json.dumps(snapshot, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
