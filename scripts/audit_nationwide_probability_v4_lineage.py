"""Read-only lineage audit and write-once corrigendum for failed v3/v4 study.

This does not refit, score, or change any frozen probability artifact.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import nationwide_probability_v3 as v3
from scripts import nationwide_probability_v4 as v4
from scripts import nationwide_research as national

OUT = ROOT / "data/manifests/research_pilot/nationwide_probability_v4_lineage_audit_v1.json"
SCIENCE_KEYS = (
    "motivation", "roles", "inputs", "heads_mm_per_24h", "model_spec",
    "nested_validation", "calibration", "coherence", "cutoff", "comparison",
    "uncertainty", "sources", "libraries", "2023_cases", "2024_cases",
    "land_cells", "product_default", "release",
)
FIT_FILES = ("heavy_head.json", "very_heavy_head.json", "nested_oof_float32.npz", "models.json")


def scientific_contract_equal(protocol_v3: dict, protocol_v4: dict) -> bool:
    """Ignore only the arm name in an otherwise identical promotion gate."""
    if any(protocol_v3.get(key) != protocol_v4.get(key) for key in SCIENCE_KEYS):
        return False
    gate_v3 = protocol_v3.get("diagnostic_gate")
    gate_v4 = protocol_v4.get("diagnostic_gate")
    return isinstance(gate_v3, str) and isinstance(gate_v4, str) and gate_v3 == gate_v4.replace("v4", "v3")


def audit() -> dict:
    v3.check()
    v4.check()
    protocol_v3 = json.loads(v3.PROTOCOL.read_text(encoding="utf-8"))
    protocol_v4 = json.loads(v4.PROTOCOL.read_text(encoding="utf-8"))
    if not scientific_contract_equal(protocol_v3, protocol_v4):
        raise ValueError("v3/v4 scientific contracts differ")
    if (v3.SEAL.exists() or v3.SCORE.exists()
            or not (v3.OUT.with_name(v3.OUT.name + ".partial") / "predictions").is_dir()):
        raise ValueError("v3 failed execution state changed")
    partial = v3.OUT.with_name(v3.OUT.name + ".partial")
    if list((partial / "predictions").glob("*.npz")):
        raise ValueError("v3 unexpectedly produced 2024 predictions")
    fit_hashes = {}
    for name in FIT_FILES:
        earlier = national.sha(partial / name)
        repaired = national.sha(v4.OUT / name)
        if earlier != repaired:
            raise ValueError(f"v3/v4 fitted artifact changed: {name}")
        fit_hashes[name] = earlier
    if (protocol_v4.get("observation_values_read_before_freeze") is not False
            or not protocol_v4.get("v3_failed_execution")
            or not v4.SEAL.exists() or not v4.SCORE.exists()):
        raise ValueError("v4 lineage premise changed")
    # V4's frozen protocol pins both prior 2024 scores. V3's pinned fit code
    # reads 2023 reference values before writing the byte-identical heads.
    if not all(protocol_v4["sources"].get(key) for key in ("national_score_sha256", "v2_score_sha256")):
        raise ValueError("prior consumed 2024 score lineage missing")
    return {
        "schema": "nationwide-probability-v4-lineage-audit-v1",
        "status": "V4_FREEZE_FLAG_SCOPE_CORRIGENDUM",
        "v3_protocol_sha256": national.sha(v3.PROTOCOL),
        "v4_protocol_sha256": national.sha(v4.PROTOCOL),
        "v4_fit_seal_sha256": national.sha(v4.SEAL),
        "v4_score_sha256": national.sha(v4.SCORE),
        "science_contract_equivalent": True,
        "fit_artifact_sha256_identical": fit_hashes,
        "v3_2024_predictions": 0,
        "v3_fit_seal_exists": False,
        "v3_score_exists": False,
        "frozen_field": {"name": "observation_values_read_before_freeze", "value": False,
                         "global_interpretation_valid": False,
                         "correct_scope": "v4.prepare itself did not open reference values"},
        "known_prior_reference_use": {
            "2023": "v3 fit read the 2023 reference before the v4 freeze",
            "2024": "v1 and v2 consumed-development scores existed and were pinned before the v4 freeze",
        },
        "v4_forecasts_sealed_before_its_2024_score": True,
        "scientific_decision": "v4 remains failed consumed-2024 development evidence; no product promotion",
        "2026_observation_values_read_by_audit": False,
    }


def write() -> dict:
    result = audit()
    digest = national.write_json(OUT, result)
    return {"status": result["status"], "audit_sha256": digest}


def check() -> dict:
    expected = audit()
    if national.receipt(OUT) != national.sha(OUT):
        raise ValueError("lineage audit receipt changed")
    if json.loads(OUT.read_text(encoding="utf-8")) != expected:
        raise ValueError("lineage audit content changed")
    return {"status": expected["status"], "audit_sha256": national.sha(OUT)}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("write", "check"))
    args = parser.parse_args()
    print(json.dumps({"write": write, "check": check}[args.command](), sort_keys=True))
