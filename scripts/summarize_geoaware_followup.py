"""Derived, tracked summary of the follow-up development selection (docs/130). Write-once; descriptive only.

Reads the local cross-validation checkpoint (gitignored) written by scripts/train_geoaware_followup.py and the tracked selection freeze, and writes
backend/app/evidence_data/phase11/geoaware_followup_development_summary.json with every configuration's per-held-out-year metrics, the checkpoint's hash,
and the descriptive B1-versus-B0 comparison. No 2022 data are read. This is development evidence, not a test result.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PHASE11 = ROOT / "backend/app/evidence_data/phase11"
CHECKPOINT = ROOT / "experiments/geoaware_followup_v1/cv_results.jsonl"
TARGET = PHASE11 / "geoaware_followup_development_summary.json"
YEARS = ("2021", "2023", "2024")


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    if TARGET.exists():
        raise SystemExit("summary already written; it is write-once")
    freeze_path = PHASE11 / "geoaware_followup_selection_freeze.json"
    records = [json.loads(line) for line in CHECKPOINT.read_text(encoding="utf-8").splitlines() if line.strip()]
    by = {(r["arm"], r["grid_index"]): r for r in records}
    assert len(by) == 64, "the checkpoint must hold all 64 configurations"
    rows = []
    for (arm, index), r in sorted(by.items()):
        for year in YEARS:
            m = r["by_year"][year]
            rows.append({"arm": arm, "grid_index": index, "held_out_year": int(year), "rmse_mm": m["rmse_mm"], "bias_mm": m["bias_mm"], "heavy_csi": m["heavy"]["csi"],
                         "very_heavy_frequency_bias": m["very_heavy"]["frequency_bias"], "zone_heavy_csi": m["zone"]["heavy_csi"], "zone_heavy_frequency_bias": m["zone"]["heavy_frequency_bias"],
                         "guardrails": r["guardrails_by_year"][year]})
    comparison = []
    for index in range(16):
        b0, b1 = by[("B0", index)], by[("B1", index)]
        comparison.append({"grid_index": index, "zone_heavy_csi_b1_minus_b0": {y: b1["by_year"][y]["zone"]["heavy_csi"] - b0["by_year"][y]["zone"]["heavy_csi"] for y in YEARS},
                           "pooled_rmse_b1_minus_b0_mm": b1["pooled"]["rmse_mm"] - b0["pooled"]["rmse_mm"]})
    summary = {"schema": "geoaware-followup-development-summary-v1", "protocol_sha256": sha(PHASE11 / "geoaware_followup_protocol_v1.json"), "selection_freeze_sha256": sha(freeze_path),
               "checkpoint_sha256": sha(CHECKPOINT), "scope": "development evidence only (leave-one-year-out over 2021, 2023 and 2024); the sealed 2022 was not opened; not a test result",
               "rows": rows, "b1_versus_b0": comparison,
               "b1_versus_b0_counts": {"configurations": 16, "zone_heavy_csi_higher_in_every_held_out_year": sum(all(c["zone_heavy_csi_b1_minus_b0"][y] > 0 for y in YEARS) for c in comparison),
                                       "pooled_rmse_lower": sum(c["pooled_rmse_b1_minus_b0_mm"] < 0 for c in comparison)}}
    TARGET.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    (PHASE11 / "geoaware_followup_development_summary.sha256").write_text(sha(TARGET) + "  geoaware_followup_development_summary.json\n", encoding="ascii")
    print(summary["b1_versus_b0_counts"])


if __name__ == "__main__":
    main()
