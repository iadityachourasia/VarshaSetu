"""Prepare blank, validator-compatible forms from the frozen blind packet.

No expert identity, label, bulletin, or adjudication is supplied by this tool.
The output is a local draft; the roster and source ledger must be completed
and frozen by the review coordinator before any meteorologist annotates cases.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.app.ml.expert_regime_review import TASKS  # noqa: E402
from backend.app.ml.regime_annotation_review import RUBRIC, verify_packet  # noqa: E402

PACKET = ROOT / "data/manifests/research_pilot/expert_regime_review_packet_v1.json"
MAP_ROOT = ROOT / "data/processed/expert_regime_review_v1"
OUTPUT = ROOT / "data/processed/expert_regime_review_handoff_v1"
RUBRIC_PATH = ROOT / "docs/147_INDEPENDENT_REGIME_REVIEW_PROTOCOL.md"
VALIDATOR_PATH = ROOT / "backend/app/ml/regime_annotation_review.py"

REVIEW_FIELDS = [
    "case_id", "forecast_source", "source_version", "issue_utc", "lead_window_h",
    "region_id", "reviewer_id", "annotation_utc", "rubric_version",
    "blind_to_detector_outputs",
]
for task in TASKS:
    REVIEW_FIELDS.extend((task, f"{task}_rationale", f"{task}_evidence_ids", f"{task}_uncertainty_reason"))

ADJUDICATION_FIELDS = [
    "case_id", "task", "adjudicator_id", "decision", "adjudication_utc",
    "rationale", "evidence_ids", "uncertainty_reason", "blind_to_detector_outputs",
]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def prepare(packet_path: Path, map_root: Path, output: Path) -> dict:
    packet = verify_packet(packet_path, map_root=map_root)
    if output.exists():
        raise FileExistsError(f"write-once handoff already exists: {output}")
    output.mkdir(parents=True)
    written = []
    for name in ("reviewer_a_blank.csv", "reviewer_b_blank.csv"):
        path = output / name
        with path.open("x", newline="", encoding="utf-8") as stream:
            writer = csv.DictWriter(stream, fieldnames=REVIEW_FIELDS)
            writer.writeheader()
            for case in packet["cases"]:
                writer.writerow({
                    "case_id": case["case_id"],
                    "forecast_source": case["forecast_source"],
                    "source_version": case["source_version"],
                    "issue_utc": case["issue_utc"],
                    "lead_window_h": f"{case['lead_window_h'][0]}-{case['lead_window_h'][1]}",
                    "region_id": case["region_id"],
                    "rubric_version": RUBRIC,
                })
        written.append(path)
    with (output / "adjudications_blank.csv").open("x", newline="", encoding="utf-8") as stream:
        csv.DictWriter(stream, fieldnames=ADJUDICATION_FIELDS).writeheader()
    written.append(output / "adjudications_blank.csv")
    templates = {
        "roster_template.json": {
            "reviewer_ids": ["", ""], "adjudicator_id": "", "frozen_utc": "",
            "rubric_sha256": sha256(RUBRIC_PATH),
            "analysis_code_sha256": sha256(VALIDATOR_PATH),
        },
        "source_ledger_template.json": {"sources": []},
    }
    for name, value in templates.items():
        path = output / name
        path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        written.append(path)
    manifest = {
        "schema": "expert-regime-review-handoff-v1",
        "status": "DRAFT_AWAITING_REAL_REVIEWERS_AND_DATED_SOURCES",
        "packet_sha256": sha256(packet_path),
        "case_count": len(packet["cases"]),
        "expert_labels": 0,
        "source_documents_admitted": 0,
        "forms": {path.name: sha256(path) for path in written},
    }
    (output / "handoff_manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--packet", type=Path, default=PACKET)
    parser.add_argument("--map-root", type=Path, default=MAP_ROOT)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    args = parser.parse_args()
    print(json.dumps(prepare(args.packet, args.map_root, args.output), sort_keys=True))


if __name__ == "__main__":
    main()
