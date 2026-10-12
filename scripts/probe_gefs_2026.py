"""Frozen forecast-only 2026 JJAS NOAA index probe; no GRIB or observation read."""

from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.app.live.pipeline import CycleRefused, HttpSource, required_messages  # noqa: E402

FOLDER = ROOT / "data/manifests/research_pilot"
PROTOCOL = FOLDER / "2026_gefs_probe_protocol_v1.json"
RESULT = FOLDER / "2026_gefs_probe_result_v1.json"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run() -> dict:
    if PROTOCOL.with_suffix(".sha256").read_text(encoding="ascii").split()[0] != sha(PROTOCOL):
        raise ValueError("probe protocol hash mismatch")
    if RESULT.exists():
        raise FileExistsError("source probe result already exists")
    protocol = json.loads(PROTOCOL.read_text(encoding="utf-8"))
    if protocol["role"] != "SOURCE_AVAILABILITY_PROBE_ONLY" or protocol["observation_read"] is not False or protocol["forecast_payload_download"] is not False:
        raise ValueError("probe role or read restrictions changed")
    expected = set(required_messages())
    cycles = []
    for date in protocol["cycles"]:
        try:
            rows = HttpSource(date).plan()
            selected = {(r["family"], r["hour"], r["variable"]) for r in rows}
            if selected != expected or len(rows) != len(expected):
                raise ValueError("selected message identity differs from the frozen live rule")
            rows_json = json.dumps(rows, sort_keys=True, separators=(",", ":")).encode("utf-8")
            cycles.append({"cycle": date, "status": "COMPLETE_SELECTED_INDEX", "selected_messages": len(rows),
                           "planned_selected_bytes": sum(r["bytes"] for r in rows), "selected_index_rows_sha256": hashlib.sha256(rows_json).hexdigest(),
                           "model_version": "NOT_DECLARED_BY_INDEX"})
        except (CycleRefused, OSError, ValueError) as error:
            cycles.append({"cycle": date, "status": "INDEX_UNAVAILABLE_OR_CHANGED", "reason": str(error)[:500]})
    report = {"schema": "varshasetu-forecast-only-source-probe-result-v1", "protocol_sha256": sha(PROTOCOL),
              "created_at_utc": datetime.now(timezone.utc).isoformat(), "source": protocol["source"],
              "observation_read": False, "forecast_payload_download": False,
              "role": "SOURCE_AVAILABILITY_PROBE_ONLY", "cycles": cycles,
              "interpretation": "Index availability alone does not prove complete archive coverage, GRIB model version, comparable accumulation semantics, or independent 2026 test eligibility."}
    value = json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + "\n"
    RESULT.write_text(value, encoding="utf-8", newline="\n")
    RESULT.with_suffix(".sha256").write_text(sha(RESULT) + "  " + RESULT.name + "\n", encoding="ascii")
    return report


if __name__ == "__main__":
    print(json.dumps(run(), indent=2, sort_keys=True))
