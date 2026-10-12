"""Bounded forecast-only GRIB packing probe around the announced GEFS change.

The control-member radiation field is deliberately outside the VarshaSetu
predictor set. This probes source history, not model skill or equivalence.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import URLError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from backend.app.live.pipeline import parse_index  # noqa: E402
from scripts.probe_gefs_2026_grib import grib_metadata  # noqa: E402
from scripts.run_2026_frozen_inference import sealed, sha  # noqa: E402

BASE = ROOT / "data/manifests/research_pilot"
PROTOCOL = BASE / "2026_gefs_radiation_transition_protocol_v1.json"
RESULT = BASE / "2026_gefs_radiation_transition_result_v1.json"
RAW = ROOT / "data/raw/evidence/noaa_gefs_2026/radiation_transition_v1"
HOST = "https://noaa-gefs-pds.s3.amazonaws.com"
MARKER = ":DSWRF:surface:18-24 hour ave fcst:ENS=low-res ctl"


def _url(cycle: str) -> str:
    return f"{HOST}/gefs.{cycle}/00/atmos/pgrb2sp25/gec00.t00z.pgrb2s.0p25.f024"


def _fetch(url: str, limit: int, start: int | None = None, end: int | None = None) -> tuple[bytes, dict]:
    headers = {"User-Agent": "VarshaSetu-research/1.0 (forecast-only source audit)"}
    if start is not None and end is not None:
        headers["Range"] = f"bytes={start}-{end}"
    for attempt in range(1, 4):
        try:
            with urlopen(Request(url, headers=headers), timeout=60) as response:
                if response.status != (206 if start is not None else 200):
                    raise ValueError(f"unexpected HTTP {response.status}")
                if start is not None:
                    content_range = response.headers.get("Content-Range", "")
                    if not content_range.startswith(f"bytes {start}-{end}/"):
                        raise ValueError("byte-range response mismatch")
                data = response.read(limit + 1)
                if len(data) > limit or (start is not None and len(data) != end - start + 1):
                    raise ValueError("response exceeded cap or was short")
                return data, {"http_status": response.status, "content_type": response.headers.get("Content-Type"),
                              "content_range": response.headers.get("Content-Range"), "attempts": attempt,
                              "retrieved_utc": datetime.now(timezone.utc).isoformat(timespec="seconds")}
        except (URLError, OSError):
            if attempt == 3:
                raise
            time.sleep(attempt * 2)


def _metadata(payload: bytes) -> dict:
    from eccodes import codes_get, codes_new_from_message, codes_release

    handle = codes_new_from_message(payload)
    try:
        result = grib_metadata(payload)
        for key in ("shortName", "stepRange", "dataDate", "dataTime", "totalLength", "edition",
                    "numberOfValues", "numberOfMissing", "referenceValue"):
            value = codes_get(handle, key)
            result[key] = value.item() if hasattr(value, "item") else value
        if result["shortName"] not in ("dswrf", "sdswrf") or result["totalLength"] != len(payload) or result["edition"] != 2 or result["stepRange"] != "18-24":
            raise ValueError("decoded GRIB identity or length mismatch")
        return result
    finally:
        codes_release(handle)


def _check_cached(row: dict) -> None:
    for item in (row["index"], row["message"]):
        path = ROOT / item["local_path"]
        if not path.is_file() or path.stat().st_size != item["byte_size"] or sha(path) != item["sha256"]:
            raise ValueError(f"cached NOAA evidence changed: {path}")


def run() -> dict:
    protocol = sealed(PROTOCOL)
    if RESULT.exists():
        raise FileExistsError("radiation transition result is write-once")
    if protocol["cycles"] != ["20230616", "20260615", "20260616"] or protocol["marker"] != MARKER or protocol["observation_read"] is not False:
        raise ValueError("probe differs from frozen protocol")
    if shutil.disk_usage(ROOT).free < protocol["minimum_free_disk_bytes"]:
        raise ValueError("free-space guard failed")
    RAW.mkdir(parents=True, exist_ok=True)
    rows = []
    for cycle in protocol["cycles"]:
        url = _url(cycle)
        index, index_transport = _fetch(url + ".idx", protocol["maximum_index_bytes"])
        lines = parse_index(index.decode("ascii"))
        matches = [i for i, line in enumerate(lines) if line[2].endswith(MARKER)]
        if len(matches) != 1 or matches[0] == len(lines) - 1:
            raise ValueError(f"DSWRF control field not uniquely located: {cycle}")
        i = matches[0]
        start, end = lines[i][1], lines[i + 1][1] - 1
        if end < start or end - start + 1 > protocol["maximum_message_bytes"]:
            raise ValueError("planned message exceeds bounded transfer")
        payload, message_transport = _fetch(url, protocol["maximum_message_bytes"], start, end)
        if payload[:4] != b"GRIB" or payload[-4:] != b"7777":
            raise ValueError("GRIB envelope invalid")
        metadata = _metadata(payload)
        if metadata["dataDate"] != int(cycle) or metadata["dataTime"] != 0:
            raise ValueError("GRIB cycle identity mismatch")
        artifacts = {}
        for name, data, transport, suffix in (("index", index, index_transport, "idx"),
                                               ("message", payload, message_transport, "grib2")):
            path = RAW / f"{cycle}_dswrf_f024.{suffix}"
            if path.exists():
                if path.read_bytes() != data:
                    raise ValueError(f"previous NOAA cache differs: {path}")
            else:
                with path.open("xb") as stream:
                    stream.write(data)
            artifacts[name] = {"local_path": path.relative_to(ROOT).as_posix(), "byte_size": len(data),
                               "sha256": hashlib.sha256(data).hexdigest(), **transport}
        rows.append({"cycle": cycle, "source_url": url, "index_line": lines[i][2],
                     "byte_start": start, "byte_end": end, "index": artifacts["index"],
                     "message": artifacts["message"], "grib_metadata": metadata})
    result = {"schema": "varshasetu-gefs-radiation-transition-v1", "protocol_sha256": sha(PROTOCOL),
              "observation_read": False, "model_inference": False, "rows": rows,
              "interpretation_limit": "Observed GRIB packing metadata cannot establish the exact GEFS software version, predictor equivalence, or rainfall skill."}
    for row in rows:
        _check_cached(row)
    with RESULT.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(result, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write("\n")
    RESULT.with_suffix(".sha256").write_text(f"{sha(RESULT)}  {RESULT.name}\n", encoding="ascii")
    return result


def check() -> dict:
    result = sealed(RESULT)
    if result["protocol_sha256"] != sha(PROTOCOL) or result["observation_read"] is not False:
        raise ValueError("result lineage changed")
    for row in result["rows"]:
        _check_cached(row)
        if _metadata((ROOT / row["message"]["local_path"]).read_bytes()) != row["grib_metadata"]:
            raise ValueError("GRIB metadata changed")
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    report = check() if args.check else run()
    print(json.dumps({"status": "VERIFIED" if args.check else "ACQUIRED", "protocol_sha256": report["protocol_sha256"],
                      "rows": [{"cycle": row["cycle"], "grib_metadata": row["grib_metadata"]} for row in report["rows"]]}, sort_keys=True))
