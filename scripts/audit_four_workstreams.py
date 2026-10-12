"""Reproduce the four-workstream disposition from sealed, local evidence only.

This audit never opens 2026 rainfall grids or model predictions. It cannot
clear a source, promote a model, or substitute for independent verification.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
BASE = ROOT / "data/manifests/research_pilot"
HANDOFF = ROOT / "data/processed/expert_regime_review_handoff_v1"
REPORT = BASE / "four_workstreams_closeout_v1.json"


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def sealed(name: str) -> tuple[dict, str]:
    path = BASE / name
    value = digest(path)
    if path.with_suffix(".sha256").read_text(encoding="ascii").split() != [value, path.name]:
        raise ValueError(f"receipt mismatch: {name}")
    return json.loads(path.read_text(encoding="utf-8")), value


def assessment() -> dict:
    source, source_hash = sealed("2026_source_version_audit_v1.json")
    source_addendum, source_addendum_hash = sealed("2026_source_review_addendum_v1.json")
    ordinal, ordinal_hash = sealed("extreme_ordinal_probability_score_v1.json")
    # The original winter readiness record predates sidecar receipts. Hash its
    # existing bytes without modifying or presenting it as a sealed corpus.
    winter_path = BASE / "winter_regime_readiness_v1.json"
    winter = json.loads(winter_path.read_text(encoding="utf-8"))
    winter_hash = digest(winter_path)
    rsmc, rsmc_hash = sealed("regime_support_docs_v1.json")
    stage, stage_hash = sealed("east_coast_development_result_v1.json")
    lead, lead_hash = sealed("east_coast_lead_breakdown_v1.json")
    fit, fit_hash = sealed("east_coast_fit_seal_v1.json")
    protocol, protocol_hash = sealed("east_coast_development_protocol_v2.json")
    if any((BASE / name).exists() for name in (
        "2026_imd_reference_clearance_v1.json", "2026_gefs_version_clearance_v1.json",
        "2026_track_b_score_v1.json")):
        raise ValueError("2026 gate state changed; this closeout must be revised")
    if (source["status"] != "OPEN_NO_CLEARANCE" or len(source["blockers"]) != 4
            or source["observation_values_read"] or source["forecast_pairing_or_scoring"]):
        raise ValueError("2026 source status is not the four-blocker sealed state")
    if (source_addendum["prior_source_audit_sha256"] != source_hash
            or source_addendum["status"] != "OPEN_NO_CLEARANCE"
            or source_addendum["observation_values_read"] or source_addendum["clearance_file_written"]):
        raise ValueError("2026 source addendum does not preserve the gate")
    if ordinal["prespecified_diagnostic_gate_passed"] or ordinal["promotion_eligible"]:
        raise ValueError("ordinal probability disposition changed")
    handoff = json.loads((HANDOFF / "handoff_manifest.json").read_text(encoding="utf-8"))
    if handoff["expert_labels"] != 0 or handoff["source_documents_admitted"] != 0:
        raise ValueError("handoff is no longer blank")
    for name, expected in handoff["forms"].items():
        if digest(HANDOFF / name) != expected:
            raise ValueError(f"handoff form changed: {name}")
    from backend.app.ml.regime_annotation_review import verify_frozen_material, verify_packet
    packet_path = BASE / "expert_regime_review_packet_v1.json"
    if digest(packet_path) != handoff["packet_sha256"]:
        raise ValueError("review handoff packet changed")
    verify_packet(packet_path, map_root=ROOT / "data/processed/expert_regime_review_v1")
    verify_frozen_material(
        json.loads((HANDOFF / "roster_template.json").read_text(encoding="utf-8")),
        rubric_path=ROOT / "docs/147_INDEPENDENT_REGIME_REVIEW_PROTOCOL.md",
        analysis_path=ROOT / "backend/app/ml/regime_annotation_review.py",
    )
    if rsmc["expert_labels"] != 0 or rsmc["annotation_source_ledger_entries"] != 0:
        raise ValueError("bibliographic source mistaken for a label")
    if winter["forecast_case_count"] != 0 or winter["independent_western_disturbance_label_count"] != 0:
        raise ValueError("winter status changed")
    if (stage["status"] != "CONSUMED_2024_DEVELOPMENT_ONLY_NO_PROMOTION"
            or stage["public_product_connected"] or stage["independent_skill_claim"]
            or stage["coverage_gate"]["eligible_for_review"]):
        raise ValueError("stage promotion boundary changed")
    if (stage["fit_seal_sha256"] != fit_hash or stage["protocol_sha256"] != protocol_hash
            or lead["result_sha256"] != stage_hash or lead["fit_seal_sha256"] != fit_hash
            or fit["2024_observation_values_read"] or protocol["roles"]["2026"] != "sealed_independent_test_no_access"):
        raise ValueError("stage lineage or observation seal changed")
    raw = stage["metrics"]["raw"]
    global_model = stage["metrics"]["global"]
    raw_csi = raw["events"]["heavy"]["metrics"]["CSI"]
    global_csi = global_model["events"]["heavy"]["metrics"]["CSI"]
    if not (global_model["continuous"]["rmse_mm"] > raw["continuous"]["rmse_mm"]
            and global_csi < raw_csi and global_model["events"]["very_heavy"]["forecast_event_count"] == 0):
        raise ValueError("stage failed-comparison facts changed")
    if sum(item["cases"] for item in lead["leads"].values()) != stage["same_case_population"]:
        raise ValueError("lead and aggregate case counts differ")
    if ('model: str = Query("M2"' not in (ROOT / "backend/app/api/live.py").read_text(encoding="utf-8")
            or 'useState<"M1" | "M2" | "M3" | "M4">("M2")' not in
            (ROOT / "frontend-v2/src/components/live/live-cycle.tsx").read_text(encoding="utf-8")):
        raise ValueError("regional live district model default is no longer M2")
    return {
        "schema": "varshasetu-four-workstreams-closeout-v1",
        "status": "INTEGRATED_WORK_COMPLETE_SCIENTIFIC_GATES_OPEN",
        "source_2026": {"disposition": "EXTERNALLY_BLOCKED_NO_SCORE", "evidence_sha256": [source_hash, source_addendum_hash],
                        "blockers": source["blockers"], "observation_values_opened": False},
        "extreme_probability": {"disposition": "FAILED_PRESPECIFIED_GATE_RESEARCH_ONLY", "evidence_sha256": ordinal_hash,
                                "promotion_eligible": False},
        "independent_regime": {"disposition": "HANDOFF_READY_EXPERT_VALIDATION_BLOCKED",
                               "evidence_sha256": [winter_hash, rsmc_hash, digest(HANDOFF / "handoff_manifest.json")],
                               "expert_labels": 0, "winter_cases": 0},
        "east_coast": {"disposition": "DEVELOPMENT_MODEL_FAILED_RAW_COMPARISON_NO_PRODUCT",
                       "evidence_sha256": [protocol_hash, fit_hash, stage_hash, lead_hash],
                       "same_case_count": stage["same_case_population"], "paired_cells": stage["same_cell_population"],
                       "raw_heavy_csi": raw_csi, "global_heavy_csi": global_csi,
                       "product_connected": False},
        "model_default": "regional M2 global non-regime; no research candidate promoted",
        "independent_2026_skill_claim": False,
        "public_warning_claim": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--write", action="store_true")
    group.add_argument("--check", action="store_true")
    args = parser.parse_args()
    value = assessment()
    if args.write:
        if REPORT.exists() or REPORT.with_suffix(".sha256").exists():
            raise FileExistsError("closeout is write-once")
        REPORT.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
        REPORT.with_suffix(".sha256").write_text(f"{digest(REPORT)}  {REPORT.name}\n", encoding="ascii")
    else:
        saved, _ = sealed(REPORT.name)
        if saved != value:
            raise ValueError("four-workstream closeout did not reproduce")
    print(json.dumps({"status": value["status"], "dispositions": {k: value[k]["disposition"] for k in
          ("source_2026", "extreme_probability", "independent_regime", "east_coast")}}, sort_keys=True))


if __name__ == "__main__":
    main()
