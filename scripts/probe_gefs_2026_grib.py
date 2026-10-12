"""Bounded 2026 JJAS GRIB semantics probe; forecast-only, no inference."""

from __future__ import annotations

import hashlib
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.app.live import pipeline  # noqa: E402

FOLDER = ROOT / "data/manifests/research_pilot"
PROTOCOL = FOLDER / "2026_gefs_grib_probe_protocol_v1.json"
INDEX_RESULT = FOLDER / "2026_gefs_probe_result_v1.json"
RESULT = FOLDER / "2026_gefs_grib_probe_result_v1.json"
GRIB_KEYS = ("centre", "subCentre", "typeOfGeneratingProcess", "generatingProcessIdentifier", "tablesVersion", "localTablesVersion",
             "productionStatusOfProcessedData", "typeOfProcessedData", "packingType", "bitsPerValue", "binaryScaleFactor", "decimalScaleFactor")


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def grib_metadata(payload: bytes) -> dict:
    from eccodes import codes_get, codes_new_from_message, codes_release

    handle = codes_new_from_message(payload)
    try:
        out = {}
        for key in GRIB_KEYS:
            try:
                value = codes_get(handle, key)
                out[key] = value.item() if hasattr(value, "item") else value
            except Exception:
                out[key] = None
        return out
    finally:
        codes_release(handle)


def run() -> dict:
    if PROTOCOL.with_suffix(".sha256").read_text(encoding="ascii").split()[0] != sha(PROTOCOL):
        raise ValueError("GRIB probe protocol hash mismatch")
    if INDEX_RESULT.with_suffix(".sha256").read_text(encoding="ascii").split()[0] != sha(INDEX_RESULT):
        raise ValueError("index probe result hash mismatch")
    if RESULT.exists():
        raise FileExistsError("GRIB probe result already exists")
    protocol = json.loads(PROTOCOL.read_text(encoding="utf-8"))
    prior = json.loads(INDEX_RESULT.read_text(encoding="utf-8"))
    if protocol["source_index_probe_sha256"] != sha(INDEX_RESULT) or [r["cycle"] for r in prior["cycles"]] != protocol["cycles"]:
        raise ValueError("GRIB probe does not match the frozen index probe")
    if protocol["observation_read"] is not False or protocol["model_inference"] is not False or protocol["role"] != "SOURCE_AND_GRIB_SEMANTICS_PROBE_ONLY":
        raise ValueError("GRIB probe scope changed")
    rows = []
    for date in protocol["cycles"]:
        source = pipeline.CachedHttpSource(date)
        entry = {"cycle": date, "observation_read": False, "model_inference": False}
        try:
            plan = source.plan()
            planned_bytes = sum(item["bytes"] for item in plan)
            entry["planned_selected_bytes"] = planned_bytes
            if len(plan) != 34 or planned_bytes > protocol["maximum_planned_bytes_per_cycle"]:
                raise ValueError("selected-message count or transfer guard failed")
            if shutil.disk_usage(pipeline.SOURCE_CACHE.parent).free < protocol["minimum_free_disk_bytes"]:
                raise ValueError("50 GiB free-space guard failed")
            decoded = pipeline.decode_cycle(source, date)
            sample = source.get("pgrb2sp25", 3, "rain")
            entry.update({"status": "DECODED", "source_messages": len(decoded["sources"]),
                          "products_passing_qc": sorted(decoded["rainfall"]),
                          "withheld_products": decoded["failed_products"],
                          "source_sha256": {f"{item['family']}:{item['hour']}:{item['variable']}": item["sha256"] for item in decoded["sources"]},
                          "sample_apcp_grib_metadata": grib_metadata(sample.payload), "model_version": "NOT_PROVEN_BY_GRIB_IDENTIFIERS"})
        except (pipeline.CycleRefused, OSError, ValueError) as error:
            entry.update({"status": "REFUSED", "reason": f"{type(error).__name__}: {error}"[:1200]})
        rows.append(entry)
    report = {"schema": "varshasetu-forecast-only-grib-probe-result-v1", "protocol_sha256": sha(PROTOCOL),
              "index_probe_sha256": sha(INDEX_RESULT), "created_at_utc": datetime.now(timezone.utc).isoformat(),
              "role": protocol["role"], "observation_read": False, "model_inference": False, "cycles": rows,
              "interpretation": "Decoded sample cycles test source semantics and QC only; no complete 2026 corpus, model transfer, independent test, or rainfall skill is established."}
    value = json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + "\n"
    RESULT.write_text(value, encoding="utf-8", newline="\n")
    RESULT.with_suffix(".sha256").write_text(sha(RESULT) + "  " + RESULT.name + "\n", encoding="ascii")
    return report


if __name__ == "__main__":
    result = run()
    print(json.dumps({"protocol_sha256": result["protocol_sha256"], "cycles": [
        {"cycle": row["cycle"], "status": row["status"], "products_passing_qc": row.get("products_passing_qc"),
         "withheld_products": row.get("withheld_products"), "reason": row.get("reason")}
        for row in result["cycles"]]}, indent=2))
