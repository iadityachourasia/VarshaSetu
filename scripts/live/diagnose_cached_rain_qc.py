"""Read-only diagnosis of cached NOAA APCP nested differences.

This is a post-publication investigation. It verifies each selected byte-range
receipt and prints interval-level statistics; it never changes the canonical
reconstruction, source cache or a published bundle.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

import numpy as np  # noqa: E402

from backend.app.data_sources.noaa_gefs_monthly import crop_grid, decode_precipitation_message  # noqa: E402
from backend.app.live.pipeline import SOURCE_CACHE  # noqa: E402

PAIRS = ((3, 6), (27, 30), (51, 54))


def load(date: str, hour: int, cache_root: Path = SOURCE_CACHE) -> tuple[np.ndarray, float, str]:
    path = cache_root / date / "pgrb2sp25" / f"f{hour:03d}_rain.grib2"
    receipt = json.loads(path.with_name(path.name + ".receipt.json").read_text(encoding="utf-8"))
    payload = path.read_bytes()
    digest = hashlib.sha256(payload).hexdigest()
    if digest != receipt["sha256"] or len(payload) != receipt["byte_size"]:
        raise ValueError(f"cache receipt mismatch: {path}")
    accumulation, grid = decode_precipitation_message(payload, member="c00", description="ENS=low-res ctl", source_id=digest)
    if accumulation.end_hour != hour:
        raise ValueError(f"decoded accumulation does not end at +{hour} h")
    region = crop_grid(grid, south=10, north=22, west=68, east=80)
    return region.values, accumulation.packing_quantum_mm, digest


def diagnose(date: str, cache_root: Path = SOURCE_CACHE) -> dict:
    results = []
    for prefix_hour, total_hour in PAIRS:
        prefix, prefix_q, prefix_hash = load(date, prefix_hour, cache_root)
        total, total_q, total_hash = load(date, total_hour, cache_root)
        difference = total - prefix
        bound = (prefix_q + total_q) / 2.0
        results.append({"interval_hours": [prefix_hour, total_hour], "prefix_sha256": prefix_hash, "total_sha256": total_hash,
                        "prefix_quantum_mm": prefix_q, "total_quantum_mm": total_q, "packing_bound_mm": bound,
                        "minimum_difference_mm": float(difference.min()), "negative_cells": int(np.count_nonzero(difference < 0)),
                        "cells_below_negative_packing_bound": int(np.count_nonzero(difference < -(bound + 1e-12))),
                        "grid_cells": int(difference.size)})
    return {"cycle": date, "scope": "REGIONAL_10_TO_22_N_68_TO_80_E", "diagnostic_only": True,
            "observation_read": False, "intervals": results}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--date", required=True)
    parser.add_argument("--output", type=Path, help="optional write-once JSON evidence path")
    args = parser.parse_args()
    data = json.dumps(diagnose(args.date), indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open("x", encoding="utf-8", newline="\n") as stream:
            stream.write(data)
        args.output.with_suffix(".sha256").write_text(hashlib.sha256(data.encode("utf-8")).hexdigest() + "  " + args.output.name + "\n", encoding="ascii")
    else:
        print(data, end="")


if __name__ == "__main__":
    main()
