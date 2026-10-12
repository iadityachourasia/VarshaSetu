from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "data/manifests/research_pilot"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_source_review_addendum_is_hash_pinned_and_keeps_2026_closed() -> None:
    path = BASE / "2026_source_review_addendum_v1.json"
    assert path.with_suffix(".sha256").read_text(encoding="ascii").split() == [sha(path), path.name]
    record = json.loads(path.read_text(encoding="utf-8"))
    assert record["status"] == "OPEN_NO_CLEARANCE"
    assert record["prior_source_audit_sha256"] == sha(BASE / "2026_source_version_audit_v1.json")
    assert record["prior_gefs_source_audit_sha256"] == sha(BASE / "2026_gefs_version_source_audit_v1.json")
    assert record["selected_feature_manifest_sha256"] == sha(
        ROOT / "data/operational_derived/operational_features_2023_2025_v1/feature_generation_manifest_v1.json"
    )
    assert record["gefs_2026"]["actual_cycle_specific_executable_record_obtained"] is False
    assert record["gefs_2023"]["training_patch_confirmed"] is False
    assert record["selected_predictor_comparability"]["cross_version_numerical_equivalence_established"] is False
    assert all(record[key] is False for key in ("observation_values_read", "forecast_reference_paired", "score_run", "clearance_file_written"))
