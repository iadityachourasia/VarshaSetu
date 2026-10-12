"""Write-once, observation-free retry of the official 2026 annual IMD NetCDF."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.probe_imd_2026_header import checked, probe  # noqa: E402

BASE = ROOT / "data/manifests/research_pilot"
PROTOCOL = BASE / "2026_imd_annual_retry_protocol_v3.json"
PREVIOUS = BASE / "2026_imd_header_probe_result_v2.json"
RESULT = BASE / "2026_imd_annual_retry_result_v3.json"


def main() -> None:
    rule, _ = checked(PROTOCOL)
    previous, previous_hash = checked(PREVIOUS)
    if rule["previous_result_sha256"] != previous_hash or previous["response_bytes"] != 0:
        raise ValueError("prior zero-byte response identity changed")
    if RESULT.exists():
        raise FileExistsError("annual retry result is write-once")
    result = probe(protocol=PROTOCOL, output=RESULT)
    result["schema"] = "varshasetu-2026-imd-annual-header-probe-result-v3"
    result["previous_result_sha256"] = previous_hash
    payload = json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n"
    with RESULT.open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(payload)
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    RESULT.with_suffix(".sha256").write_text(f"{digest}  {RESULT.name}\n", encoding="ascii")
    print(json.dumps({"status": result["status"], "http_status": result.get("http_status"),
                      "response_bytes": result.get("response_bytes"), "header": result.get("header")}, sort_keys=True))


if __name__ == "__main__":
    main()
