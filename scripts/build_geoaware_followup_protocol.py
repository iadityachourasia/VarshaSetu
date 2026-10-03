"""Freeze the geography-aware follow-up protocol (docs/129) as a machine-readable, hash-pinned record. Write-once.

Every input hash is computed from the files on disk. Run before any training. The 2022 sealed observation file is not opened here.
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.app.ml import geoaware_followup as gf  # noqa: E402

OUT = ROOT / "backend/app/evidence_data/phase11"
V1 = ROOT / "data/operational_derived/operational_features_2023_2025_v1"
V2 = ROOT / "data/operational_derived/v2/features"
DATA = {"2021": V2 / "2021/development/deterministic", "2023": V1 / "2023/train/deterministic", "2024": V1 / "2024/validation/deterministic"}
FILES = ("X.npy", "y_mm.npy", "pixel_index.npy", "cases.json")


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def main() -> None:
    target = OUT / "geoaware_followup_protocol_v1.json"
    if target.exists():
        raise SystemExit("follow-up protocol already frozen; a change needs a new version")
    corpus = json.loads((ROOT / "backend/app/evidence_data/phase10/corpus_v2_manifest.json").read_text(encoding="utf-8"))
    protocol = {
        "schema_id": "geoaware_followup_protocol_v1",
        "title": "Geography-aware correction, follow-up with an independent test (docs/129)",
        "status": "APPROVED_FOR_DEVELOPMENT_SELECTION_ONLY_TEST_SEALED",
        "approval": {
            "approved_before_any_training": True,
            "record": "project owner reply 'continue do thing' (2026-10-03) to a message that listed decisions 1 to 6 of docs/129 section 10 and said the work would stop before unsealing 2022",
            "interpretation": ("treated as approval of decisions 1 to 4 exactly as written in docs/129: year roles, the four arms and the single recipe change (event-weight cap 4), "
                               "guardrails G1 to G4, and the decision rule P1 to P4. It is not an explicit item-by-item approval, and the owner may revise any of it before 2022 is unsealed."),
            "not_approved": {"scoring_of_frozen_M1_to_M4_on_2022": "decision 5 was not answered and defaults to NO; nothing in this protocol authorises it",
                             "D2_imd_redistribution": "unresolved; everything stays local and nothing derived from IMD values may leave this machine"},
            "unseal": "opening the 2022 IMD values requires a separate signed unseal record from the owner after the selection freeze exists; this protocol authorises development selection only"},
        "parents": {
            "design": "docs/129_GEOGRAPHY_AWARE_FOLLOWUP_PROTOCOL_PROPOSAL.md",
            "v1_experiment": "docs/126_GEOGRAPHY_AWARE_MODEL_RESULTS.md (pre-registered rule not met)",
            "corpus_v2_protocol_sha256": corpus["protocol_sha256"], "corpus_v2_evidence_manifest_sha256": sha(ROOT / "backend/app/evidence_data/phase10/corpus_v2_manifest.json"),
            "feature_generation_manifest_v2_sha256": sha(V2 / "feature_generation_manifest_v1.json"),
            "static_geography_sha256": sha(ROOT / "backend/app/evidence_data/phase7/static_geography_v1.json"),
            "geoaware_protocol_v1_sha256": sha(ROOT / "backend/app/evidence_data/phase9/geoaware_protocol_v1.json")},
        "contamination_disclosure": ("The design uses the 2024 and 2025 results of docs/126 (forcing arms dropped, cap lowered, G4 added). Only the sealed 2022 may be called independent; "
                                     "results on 2021, 2023 and 2024 are development evidence."),
        "track": "operational-era (Track B) only; never pooled with the reforecast track",
        "years": {"development": list(gf.DEVELOPMENT_YEARS), "sealed_test": 2022},
        "development_data_sha256": {year: {name: sha(folder / name) for name in FILES} for year, folder in DATA.items()},
        "feature_registry": {"arms": gf.ARMS, "arm_roles": gf.ARM_ROLES, "forecast_time_forcing": "not carried over (added nothing in docs/126)",
                             "static_geography": "allowed at forecast time (AGENTS.md section 3.4)"},
        "model": {"family": "xgboost", "device": "cpu", "tree_method": "hist", "seed": 26080, "n_jobs": 12, "configurations_per_arm": 16,
                  "fixed": {"learning_rate": 0.05, "subsample": 0.9, "colsample_bytree": 0.9, "reg_lambda": 2.0, "min_child_weight": 5},
                  "grid": {"max_depth": [4, 6], "n_estimators": [200, 350], "objective": ["reg:squarederror", "reg:tweedie"], "tweedie_variance_power": 1.5, "weights": ["none", "capped_event"]},
                  "event_weight": {"cap": gf.EVENT_WEIGHT_CAP, "formula": "w = min(cap, 1 + y / 64.5) on training rows only (never at inference)",
                                   "change_from_v1": "cap 10 -> 4; the only recipe change"},
                  "output": "prediction clipped at zero", "gpu": "not used"},
        "selection": {
            "folds": "leave-one-year-out over 2021, 2023 and 2024: fit on the other two years, predict the held-out year; the sealed year can never enter",
            "guardrails": {"G1": "heavy-rain CSI (64.5 mm per 24 h) at least the Raw value on the same held-out year (all cells)",
                           "G2": "absolute bias at most 1.5 mm on the held-out year (all cells)",
                           "G3": "very-heavy (115.6 mm per 24 h) forecast frequency bias at least 0.05 on the held-out year",
                           "G4": f"heavy-rain forecast frequency bias in the coastal-and-orographic zone at most {gf.G4_MAX_ZONE_HEAVY_FREQUENCY_BIAS} on the held-out year (a loose floor; it would not have flagged 1.28)"},
            "rule": "per arm, among the configurations that pass G1 to G4 in EVERY held-out year, the lowest pooled out-of-fold RMSE (all three held-out years together); ties in grid order; none passing means the arm has no candidate and that is reported",
            "final_fit": "the selected configuration refit on all 562 development cases; model hashes written to the selection freeze before any 2022 value is opened"},
        "decision_rule": {
            "primary_comparator": "B0 selected under the same rule; if B0 has no candidate, the frozen M2 is the comparator and attribution to geography is recorded as undetermined (P4)",
            "adds_value_requires_all": [
                "P1: B1 beats the comparator on heavy-rain CSI in the coastal-and-orographic zone on 2022, paired whole-case 95 percent interval of (B1 minus comparator) excluding zero in the positive direction",
                "P2: overall RMSE of B1 not worse than the comparator's by more than 0.2 mm",
                "P3: B1 passes G1 to G4 on 2022",
                "P4: the comparator rule above is applied and stated"],
            "reported_not_decisive": ["B1Z against B1 (sensitivity to the 500 hPa height offset)", "frozen M0 to M4 on 2022 only if the owner approves decision 5", "by lead and by zone", "very-heavy skill"],
            "multiplicity": "one primary question; no adjustment needed",
            "if_not_met": "no independent evidence that geography-aware features improve on the pipeline without them, reported with the same prominence as a success"},
        "evaluation": {
            "thresholds_mm_per_24h": {"heavy": 64.5, "very_heavy": 115.6},
            "support_gate": {"min_cases": 30, "min_cells": 20, "min_observed_event_pairs": 30, "otherwise": "insufficient_support, no number; if the zone fails it the primary test is unevaluable, not a pass or fail"},
            "uncertainty": {"method": "paired whole-case bootstrap", "repeats": 2000, "seed": 26080, "note": "optimistic: cells within a case and consecutive days are correlated"},
            "reproduction_gate": "recomputed frozen M0 to M4 pooled values must reproduce the published values on the paired cells exactly where they apply, before any new number is written",
            "mask": "finite forecast cells intersected with IMD non-fill cells, applied only at unseal for 2022",
            "label_for_2022": "INDEPENDENT TEST: first use of this year"},
        "immutability": "selection outputs are write-once; any change to this protocol needs a new version and a new record"}
    OUT.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(protocol, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    (OUT / "geoaware_followup_protocol_v1.sha256").write_text(sha(target) + "  geoaware_followup_protocol_v1.json\n", encoding="ascii")
    print("protocol sha256", sha(target))


if __name__ == "__main__":
    main()
