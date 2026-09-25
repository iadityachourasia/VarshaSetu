"""Restore two Phase 1F files overwritten by an interrupted background replay."""

from __future__ import annotations

import csv
import hashlib
import json
import os
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
MANIFEST_ROOT = ROOT / "data/manifests/phase1f/2019-JJAS"
EXPECTED = {
    "reconstruction_replay.csv": "7b38b6b21ae08d2dce06f7c5b502ff1f43cba9ad5d257686d45a1dc2db111b1e",
    "season_manifest.json": "ecdd9d722793ec2b07186de04477cb5ab14a0b2bf4d6bed079640ae39c27f9b0",
}
REPLAY_FIELDS = [
    "initialization", "month", "product", "member",
    "method_a_status", "method_a_reason", "method_b_status", "method_b_reason",
    "method_b_subtractions", "method_b_segments",
    "method_b_normalized_negative_count", "method_b_minimum_normalized_negative_mm",
    "method_b_formula", "both_pass_max_abs_difference_mm",
    "both_pass_mean_abs_difference_mm", "source_manifest", "source_manifest_sha256",
]


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical_row(row: dict) -> dict:
    restored = {field: row[field] for field in REPLAY_FIELDS}
    if restored["method_b_status"] != "PASS":
        for field in (
            "method_b_subtractions", "method_b_segments",
            "method_b_normalized_negative_count",
            "method_b_minimum_normalized_negative_mm",
        ):
            restored[field] = ""
    return restored


def main() -> None:
    replay_path = MANIFEST_ROOT / "reconstruction_replay.csv"
    with replay_path.open(newline="", encoding="utf-8") as handle:
        rows = [canonical_row(row) for row in csv.DictReader(handle)]
    replay_temp = replay_path.with_suffix(".csv.restore")
    with replay_temp.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=REPLAY_FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    if digest(replay_temp) != EXPECTED[replay_path.name]:
        raise ValueError("reconstructed replay does not match deterministic reference")

    season_path = MANIFEST_ROOT / "season_manifest.json"
    season = json.loads(season_path.read_text(encoding="utf-8"))
    season["method_b"]["subtraction_counts"] = {"": 362, "1": 1468}
    season["july22"] = [canonical_row(row) for row in season["july22"]]
    season_temp = season_path.with_suffix(".json.restore")
    season_temp.write_text(
        json.dumps(season, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    if digest(season_temp) != EXPECTED[season_path.name]:
        raise ValueError("reconstructed season manifest does not match deterministic reference")

    os.replace(replay_temp, replay_path)
    os.replace(season_temp, season_path)
    print(json.dumps({name: digest(MANIFEST_ROOT / name) for name in EXPECTED}, indent=2))


if __name__ == "__main__":
    main()
