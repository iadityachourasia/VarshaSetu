"""Replay source: an already-acquired historical cycle read from the hash-verified raw store, fed through exactly the same pipeline as a live cycle (the scientific gate, docs/139).

Needs the local acquisition tree (gitignored); every payload is hash-checked against its receipt, so a modified file refuses the replay.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from backend.app.live.pipeline import ATMOSPHERE, CycleRefused, Message

ROOT = Path(__file__).resolve().parents[3]
P4E = ROOT / "experiments/recent_historical/phase4e_source_inventory_v1"
P4F = ROOT / "experiments/recent_historical/phase4f_payload_acquisition_v1"


class StoredSource:
    def __init__(self, date: str):
        self.date = date
        manifest = P4E / "planned_acquisition_manifest.jsonl"
        if not manifest.is_file() or not (P4E / "dates" / f"{date}.json").is_file():
            raise CycleRefused(f"no stored acquisition for {date}")
        stamp = f"{date[:4]}-{date[4:6]}-{date[6:]}T00:00:00Z"
        self._rows = {}
        for line in manifest.read_text(encoding="utf-8").splitlines():
            if stamp not in line or '"c00"' not in line:
                continue
            row = json.loads(line)
            if row["initialization"] == stamp and row["member"] == "c00":
                self._rows[(row["product_family"], row["forecast_hour"], row["variable"])] = row
        checkpoint = json.loads((P4E / "dates" / f"{date}.json").read_text(encoding="utf-8"))
        self._lines = {}
        for obj in checkpoint["objects"]:
            for field in obj["fields"]:
                if obj["member"] == "c00" and field["message"]:
                    self._lines[(obj["family"], obj["hour"], field["variable"])] = field["message"]["raw"]

    def get(self, family: str, hour: int, variable: str) -> Message:
        name = "rain" if variable == "rain" else variable
        row, line = self._rows.get((family, hour, name)), self._lines.get((family, hour, name))
        if row is None or line is None:
            raise CycleRefused(f"stored cycle {self.date} lacks {family} {name} f{hour:03d}")
        path = ROOT / row["expected_local_relative_path"]
        receipt = P4F / "receipts" / str(row["year"]) / self.date / f"{self.date}_{family}_c00_f{hour:03d}_{name}.json"
        if not path.is_file() or not receipt.is_file():
            raise CycleRefused(f"stored payload or receipt missing: {path.name}")
        saved = json.loads(receipt.read_text(encoding="utf-8"))
        payload = path.read_bytes()
        digest = hashlib.sha256(payload).hexdigest()
        if saved.get("state") != "HASH_VERIFIED" or digest != saved["sha256"]:
            raise CycleRefused(f"stored payload hash differs from its receipt: {path.name}")
        return Message(family, hour, variable, row["noaa_object_key"], line, row["byte_start"], row["byte_end"], payload, digest)
