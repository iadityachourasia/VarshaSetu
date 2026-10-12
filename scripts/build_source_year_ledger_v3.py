"""Append the successful-endpoint/empty-response IMD retry to the v2 ledger."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts import build_source_year_ledger_v2 as previous  # noqa: E402

OUT = ROOT / "data/manifests/research_pilot/source_year_ledger_v3.json"
PROBE = ROOT / "data/manifests/research_pilot/2026_imd_header_probe_result_v2.json"
PROBE_V1 = ROOT / "data/manifests/research_pilot/2026_imd_header_probe_result_v1.json"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build() -> dict:
    prior_path = previous.OUT
    prior = json.loads(prior_path.read_text(encoding="utf-8"))
    if prior != previous.build() or prior_path.with_suffix(".sha256").read_text(encoding="ascii").split()[0] != sha(prior_path):
        raise ValueError("v2 source ledger does not reproduce")
    if PROBE.with_suffix(".sha256").read_text(encoding="ascii").split()[0] != sha(PROBE):
        raise ValueError("v2 IMD probe hash mismatch")
    probe = json.loads(PROBE.read_text(encoding="utf-8"))
    if (probe["previous_result_sha256"] != sha(PROBE_V1)
            or probe["forecast_year_sha256"] != prior["2026_forecast_year_sha256"]
            or probe["observation_rainfall_values_read"] is not False
            or probe["forecast_observation_pairing"] is not False):
        raise ValueError("v2 IMD probe lineage or no-rainfall gate differs")
    rows = [dict(row) for row in prior["rows"]]
    candidates = [row for row in rows if row["track"] == "B_OPERATIONAL_GEFS" and row["year"] == 2026]
    if len(candidates) != 1:
        raise ValueError("expected one 2026 Track B row")
    row = candidates[0]
    row["imd_reference"] = {
        "status": "not_local" if probe["status"] != "LOCAL_REFERENCE_HEADER_READY_UNSCORED" else "local_unscored",
        "path": probe.get("local_path"),
        "sha256": probe.get("response_sha256") if probe.get("local_path") else None,
        "bytes": probe.get("response_bytes") if probe.get("local_path") else None,
        "header_probe_status": probe["status"],
        "header_probe_http_status": probe.get("http_status"),
        "header_probe_response_bytes": probe.get("response_bytes"),
        "header_probe_sha256": sha(PROBE),
    }
    return {**prior, "schema": "source-year-ledger-v3", "previous_ledger_sha256": sha(prior_path),
            "2026_imd_probe_retry_sha256": sha(PROBE), "rows": rows,
            "meaning": "Forecast-only 2026 side sealed; official IMD 2026 POST returned an empty body, so no independent-year rainfall score exists"}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    value = json.dumps(build(), indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    if args.check:
        if not OUT.is_file() or OUT.read_text(encoding="utf-8") != value or OUT.with_suffix(".sha256").read_text(encoding="ascii").split()[0] != sha(OUT):
            raise ValueError("v3 source ledger differs from local evidence")
        print(f"verified {OUT.relative_to(ROOT)}")
        return
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(value)
    OUT.with_suffix(".sha256").write_text(hashlib.sha256(value.encode("utf-8")).hexdigest() + "  " + OUT.name + "\n", encoding="ascii")
    print(f"wrote {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
