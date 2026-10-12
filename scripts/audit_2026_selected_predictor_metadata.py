"""Compare hash-verified forecast GRIB headers across selected 2023/2026 cycles.

This is a source-format diagnostic. It never decodes GRIB values, reads an
observation, runs inference, or writes a source/version clearance.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.app.live.pipeline import ATMOSPHERE, object_key  # noqa: E402

BASE = ROOT / "data/manifests/research_pilot"
PROTOCOL = BASE / "2026_selected_predictor_metadata_protocol_v1.json"
RESULT = BASE / "2026_selected_predictor_metadata_result_v1.json"


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def sealed(path: Path) -> tuple[dict, str]:
    sha = digest(path)
    if path.with_suffix(".sha256").read_text(encoding="ascii").split() != [sha, path.name]:
        raise ValueError(f"sealed receipt mismatch: {path.name}")
    return json.loads(path.read_text(encoding="utf-8")), sha


def source_path(cycle: str, field: str) -> Path:
    family = "pgrb2sp25" if field == "rain" else ATMOSPHERE[field][0]
    if cycle.startswith("2023"):
        return ROOT / f"data/operational_gefs/v1/2023/{cycle}/{family}/c00_f024_{field}.grib2"
    return ROOT / f"data/live/source_cache/{cycle}/{family}/f024_{field}.grib2"


def verified_source(path: Path, cycle: str, field: str, old_files: dict) -> str:
    sha = digest(path)
    if cycle.startswith("2023"):
        entry = old_files.get(path.relative_to(ROOT).as_posix())
        if not isinstance(entry, dict) or entry.get("sha256") != sha or entry.get("bytes") != path.stat().st_size:
            raise ValueError(f"2023 source manifest mismatch: {cycle} {field}")
    else:
        receipt = json.loads(Path(str(path) + ".receipt.json").read_text(encoding="utf-8"))
        family = path.parent.name
        expected_url = "https://noaa-gefs-pds.s3.amazonaws.com/" + object_key(cycle, family, 24)
        bounds = receipt.get("byte_range")
        if (receipt.get("url") != expected_url or receipt.get("sha256") != sha
                or receipt.get("byte_size") != path.stat().st_size
                or not isinstance(bounds, list) or len(bounds) != 2
                or bounds[1] - bounds[0] + 1 != path.stat().st_size):
            raise ValueError(f"2026 source receipt mismatch: {cycle} {field}")
    return sha


def header(payload: bytes, keys: tuple[str, ...], cycle: str) -> dict:
    from eccodes import codes_get, codes_new_from_message, codes_release

    if not payload.startswith(b"GRIB") or not payload.endswith(b"7777"):
        raise ValueError("GRIB envelope invalid")
    handle = codes_new_from_message(payload)
    try:
        if codes_get(handle, "edition") != 2 or codes_get(handle, "dataDate") != int(cycle):
            raise ValueError("GRIB edition or date mismatch")
        if codes_get(handle, "totalLength") != len(payload):
            raise ValueError("GRIB message length mismatch")
        result = {}
        for key in keys:
            try:
                value = codes_get(handle, key)
                result[key] = value.item() if hasattr(value, "item") else value
            except Exception:
                result[key] = None
        return result
    finally:
        codes_release(handle)


def differences(first: dict, second: dict, keys: tuple[str, ...]) -> dict:
    return {key: {"first": first.get(key), "second": second.get(key)}
            for key in keys if first.get(key) != second.get(key)}


def build() -> dict:
    protocol, protocol_sha = sealed(PROTOCOL)
    if (protocol.get("status") != "FORECAST_ONLY_DIAGNOSTIC_NO_VERSION_CLEARANCE_NO_SKILL"
            or protocol.get("cycles") != ["20230616", "20260615", "20260616"]
            or protocol.get("forecast_hour") != 24
            or protocol.get("selected_fields") != ["rain", "u850", "v850", "q700", "z500", "mslp", "pwat"]
            or protocol.get("observation_read") is not False
            or protocol.get("forecast_values_decoded") is not False
            or protocol.get("clearance_written") is not False):
        raise ValueError("predictor metadata protocol scope changed")
    manifest_path = ROOT / protocol["2023_source_manifest"]
    if digest(manifest_path) != protocol["2023_source_manifest_sha256"]:
        raise ValueError("2023 source manifest hash changed")
    if manifest_path.with_suffix(".sha256").read_text(encoding="ascii").strip() != digest(manifest_path):
        raise ValueError("2023 source manifest receipt mismatch")
    old_files = json.loads(manifest_path.read_text(encoding="utf-8"))["files"]
    identity = tuple(protocol["identity_keys"])
    encoding = tuple(protocol["encoding_keys"])
    rows = {}
    for field in protocol["selected_fields"]:
        field_rows = {}
        for cycle in protocol["cycles"]:
            path = source_path(cycle, field)
            sha = verified_source(path, cycle, field, old_files)
            field_rows[cycle] = {"source_path": path.relative_to(ROOT).as_posix(),
                                 "source_sha256": sha,
                                 "grib_header": header(path.read_bytes(), identity + encoding, cycle)}
        comparisons = {}
        for name, first_cycle, second_cycle in (("2023_to_pre", "20230616", "20260615"),
                                                  ("pre_to_post", "20260615", "20260616")):
            first = field_rows[first_cycle]["grib_header"]
            second = field_rows[second_cycle]["grib_header"]
            comparisons[name] = {"identity_differences": differences(first, second, identity),
                                 "encoding_differences": differences(first, second, encoding)}
        rows[field] = {"cycles": field_rows, "comparisons": comparisons}
    return {"schema": "varshasetu-selected-predictor-grib-metadata-result-v1",
            "status": "METADATA_DIAGNOSTIC_COMPLETE_SOURCE_CLEARANCE_OPEN",
            "protocol_sha256": protocol_sha,
            "2023_source_manifest_sha256": digest(manifest_path),
            "rows": rows,
            "observation_read": False,
            "forecast_values_decoded": False,
            "model_inference": False,
            "clearance_written": False,
            "interpretation_limit": "Header identity/encoding differences are processing evidence; matching headers do not prove numerical equivalence, executable identity or rainfall skill."}


def encode(record: dict) -> bytes:
    return (json.dumps(record, indent=2, sort_keys=True, allow_nan=False) + "\n").encode("utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("write", "check"))
    args = parser.parse_args()
    data = encode(build())
    receipt = RESULT.with_suffix(".sha256")
    if args.mode == "write":
        if RESULT.exists() or receipt.exists():
            raise FileExistsError("predictor metadata result is write-once")
        with RESULT.open("xb") as stream:
            stream.write(data)
        with receipt.open("x", encoding="ascii", newline="\n") as stream:
            stream.write(f"{hashlib.sha256(data).hexdigest()}  {RESULT.name}\n")
    else:
        saved, _ = sealed(RESULT)
        if encode(saved) != data:
            raise ValueError("selected-predictor metadata result no longer reproduces")
    result = json.loads(data)
    print(json.dumps({"status": result["status"], "fields": len(result["rows"]),
                      "protocol_sha256": result["protocol_sha256"],
                      "result_sha256": hashlib.sha256(data).hexdigest()}, sort_keys=True))


if __name__ == "__main__":
    main()
