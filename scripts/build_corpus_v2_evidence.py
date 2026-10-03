"""Copy the small governing records of the independent-years corpus v2 (2021-2022) from the gitignored experiments tree into tracked evidence.

Byte-exact copies plus one manifest that records every copied file's sha256 and the hashes of the heavy artifacts they govern (inventory closed set,
per-year source manifests, experiment manifest). Counts in the manifest are read from the copied files, not typed. Write-once.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXP = ROOT / "experiments/recent_historical"
OUT = ROOT / "backend/app/evidence_data/phase10"
INV = EXP / "corpus2_source_inventory_v1"
PAY = EXP / "corpus2_payload_acquisition_v1"
PROTO = EXP / "operational_corpus_protocol_v2"
IMD = EXP / "imd_v2"

COPIES = {
    "corpus_v2_protocol.json": PROTO / "protocol.json",
    "corpus_v2_feature_contract.json": PROTO / "feature_contract.json",
    "corpus_v2_imd_2021_manifest.json": IMD / "imd_2021_manifest.json",
    "corpus_v2_imd_2022_manifest.json": IMD / "imd_2022_manifest.json",
    "corpus_v2_inventory_cross_year_compatibility.json": INV / "cross_year_compatibility.json",
    "corpus_v2_inventory_size_estimates.json": INV / "size_estimates.json",
    "corpus_v2_payload_pinned_constants.json": PAY / "pinned_constants.json",
    "corpus_v2_payload_year_report_2021.json": PAY / "checkpoints/2021/year_report.json",
    "corpus_v2_payload_year_report_2022.json": PAY / "checkpoints/2022/year_report.json",
    "corpus_v2_payload_corpus_summary.json": PAY / "corpus_source_summary.json",
    "corpus_v2_payload_cross_year_compatibility.json": PAY / "cross_year_payload_compatibility.json",
    "corpus_v2_holdout_seal_audit.json": PAY / "holdout_seal_audit.json",
}


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def sidecar(path: Path) -> str:
    return path.read_text(encoding="ascii").split()[0]


def main() -> None:
    if (OUT / "corpus_v2_manifest.json").exists():
        raise SystemExit("corpus v2 evidence manifest already exists; it is write-once")
    OUT.mkdir(parents=True, exist_ok=True)
    for name, source in COPIES.items():
        (OUT / name).write_bytes(source.read_bytes())
    summary = json.loads((OUT / "corpus_v2_payload_corpus_summary.json").read_text(encoding="utf-8"))
    reports = {y: json.loads((OUT / f"corpus_v2_payload_year_report_{y}.json").read_text(encoding="utf-8")) for y in (2021, 2022)}
    manifest = {
        "schema": "corpus-v2-evidence-manifest-v1",
        "dataset_identifier": "operational_gefs_imd_2021_2022_v2",
        "protocol_sha256": sha(OUT / "corpus_v2_protocol.json"),
        "protocol_sidecar_sha256": sidecar(PROTO / "protocol.sha256"),
        "year_roles": json.loads((OUT / "corpus_v2_protocol.json").read_text(encoding="utf-8"))["split_policy"],
        "heavy_artifact_hashes": {
            "inventory_closed_set_manifest_sha256": sidecar(INV / "artifact_manifest.sha256"),
            "source_manifest_2021_sha256": sidecar(PAY / "manifests/2021_source_manifest.sha256"),
            "source_manifest_2022_sha256": sidecar(PAY / "manifests/2022_source_manifest.sha256"),
            "experiment_manifest_sha256": sidecar(PAY / "manifests/phase4f_experiment_manifest.sha256"),
            "acquisition_manifest_sha256": summary["acquisition_manifest_sha256"],
        },
        "counts": {"scheduled_initializations": summary["scheduled_initializations"], "scheduled_cases": summary["scheduled_cases"],
                   "planned_messages": summary["planned_messages"], "hash_verified_messages": summary["hash_verified_messages"],
                   "metadata_valid_messages": summary["metadata_valid_messages"], "verified_payload_bytes": summary["verified_payload_bytes"],
                   "by_year": {str(y): {"status": r["status"], "control_rainfall_qc_pass": r["qc"]["control_rainfall_qc_pass"],
                                        "deterministic_source_eligible": r["qc"]["deterministic_source_eligible"],
                                        "full_five_member_rainfall_qc_pass": r["qc"]["full_five_member_rainfall_qc_pass"],
                                        "atmospheric_qc_pass": r["qc"]["atmospheric_qc_pass"], "scheduled_cases": r["qc"]["scheduled_cases"]} for y, r in reports.items()}},
        "sealing": {"2022_imd_rainfall_values_read": False, "scoring_authorized": False,
                    "note": "Only forecast-side source and QC records exist for 2022; the observation file's header and dates were checked, its values were not read."},
        "files": {name: {"sha256": sha(OUT / name), "bytes": (OUT / name).stat().st_size} for name in COPIES},
        "scope": "governing records only; the heavy raw GRIB messages, indexes and QC arrays stay local (gitignored) and are covered by the hashes above",
    }
    path = OUT / "corpus_v2_manifest.json"
    path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    (OUT / "corpus_v2_manifest.sha256").write_text(sha(path) + "  corpus_v2_manifest.json\n", encoding="ascii")
    print(json.dumps(manifest["counts"], indent=1))


if __name__ == "__main__":
    main()
