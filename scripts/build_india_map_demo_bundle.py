"""Bundle three hash-verified 2025-09-26 all-India Raw GEFS leads for an offline research demo.

Only stored NOAA Raw forecast arrays and their frozen ledger are read. No IMD
observation or corrected-model array is opened. The bundle is write-once and
small; the full local cache remains the source for the wider case catalogue.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PHASE14 = ROOT / "backend/app/evidence_data/phase14"
LEDGER = PHASE14 / "all_india_raw_ledger_v1.json"
BUNDLE = PHASE14 / "india_map_demo_v1"
MANIFEST = BUNDLE / "manifest.json"
CASE_IDS = ("20250926_day1_24h", "20250926_day2_24h", "20250926_day3_24h")


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def expected() -> dict:
    ledger = json.loads(LEDGER.read_text(encoding="utf-8"))
    rows = {entry["case_id"]: entry for entry in ledger["populations"]["2025"] if entry["status"] == "INCLUDED"}
    return {"schema": "india-map-raw-demo-v1", "source_track": "B_OPERATIONAL_GEFS", "role": "HISTORICAL_RAW_ONLY_NO_OBSERVATIONS_NO_CORRECTION",
            "ledger_sha256": digest(LEDGER),
            "cases": {case_id: {"filename": f"{case_id}.npy", "source_path": rows[case_id]["path"], "sha256": rows[case_id]["sha256"]} for case_id in CASE_IDS}}


def write() -> None:
    if BUNDLE.exists():
        raise FileExistsError("India map demo bundle is write-once")
    value = expected()
    BUNDLE.mkdir(parents=True)
    for item in value["cases"].values():
        source = ROOT / item["source_path"]
        if digest(source) != item["sha256"]:
            raise ValueError(f"Raw source hash mismatch: {source}")
        (BUNDLE / item["filename"]).write_bytes(source.read_bytes())
    MANIFEST.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    MANIFEST.with_suffix(".sha256").write_text(f"{digest(MANIFEST)}  {MANIFEST.name}\n", encoding="ascii")
    check()


def check() -> None:
    if MANIFEST.with_suffix(".sha256").read_text(encoding="ascii").split() != [digest(MANIFEST), MANIFEST.name]:
        raise ValueError("bundle manifest receipt mismatch")
    saved = json.loads(MANIFEST.read_text(encoding="utf-8"))
    if saved != expected():
        raise ValueError("bundle and frozen ledger differ")
    for item in saved["cases"].values():
        if digest(BUNDLE / item["filename"]) != item["sha256"]:
            raise ValueError(f"bundled Raw array mismatch: {item['filename']}")
    print(json.dumps({"status": "VERIFIED_RAW_ONLY", "cases": len(saved["cases"]), "manifest_sha256": digest(MANIFEST)}, sort_keys=True))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--write", action="store_true")
    group.add_argument("--check", action="store_true")
    args = parser.parse_args()
    write() if args.write else check()
