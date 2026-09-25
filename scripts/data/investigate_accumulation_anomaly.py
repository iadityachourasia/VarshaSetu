"""Forensically inspect the cached 2019-07-22 GEFS precipitation anomaly.

This script is deliberately cache-only.  It never writes or rewrites source GRIB
objects; its JSON output is a derived audit artifact.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import sys

import numpy as np
from eccodes import (
    codes_get,
    codes_get_array,
    codes_get_values,
    codes_grib_new_from_file,
    codes_release,
)

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.app.data.corpus_policy import (
    classify_negative_increment,
    maximum_independent_difference_error,
    negative_increment_admissible,
    packing_quantum,
)


MEMBERS = ("c00", "p01", "p02", "p03", "p04")
KEYS = (
    "shortName", "name", "units", "stepType", "stepRange", "startStep",
    "endStep", "forecastTime", "validityDate", "validityTime", "packingType",
    "dataRepresentationTemplateNumber", "bitsPerValue", "referenceValue",
    "binaryScaleFactor", "decimalScaleFactor", "packingError", "missingValue",
    "numberOfValues", "numberOfMissing", "minimum", "maximum",
    "orderOfSpatialDifferencing", "Ni", "Nj", "gridType",
)


def optional(handle, key: str):
    try:
        value = codes_get(handle, key)
        return value.item() if hasattr(value, "item") else value
    except Exception:
        return None


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def decode(path: Path) -> list[dict]:
    messages: list[dict] = []
    with path.open("rb") as stream:
        number = 0
        while (handle := codes_grib_new_from_file(stream)) is not None:
            number += 1
            try:
                ni, nj = int(codes_get(handle, "Ni")), int(codes_get(handle, "Nj"))
                values = np.asarray(codes_get_values(handle), dtype=np.float64).reshape(nj, ni)
                lat = np.asarray(codes_get_array(handle, "latitudes"), dtype=float).reshape(nj, ni)[:, 0]
                lon = np.asarray(codes_get_array(handle, "longitudes"), dtype=float).reshape(nj, ni)[0, :]
                if np.all(np.diff(lat) < 0):
                    lat, values = lat[::-1], values[::-1, :]
                messages.append({
                    "message_number": number,
                    "metadata": {key: optional(handle, key) for key in KEYS},
                    "values": values,
                    "latitude": lat,
                    "longitude": lon,
                })
            finally:
                codes_release(handle)
    return messages


def msg(messages: list[dict], start: int, end: int) -> dict:
    matches = [m for m in messages if m["metadata"]["startStep"] == start and m["metadata"]["endStep"] == end]
    if len(matches) != 1:
        raise RuntimeError(f"expected one {start}-{end} message; found {len(matches)}")
    return matches[0]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path("data/raw/phase1c/gefsv12/2019072200"))
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    decoded: dict[str, list[dict]] = {}
    paths: dict[str, Path] = {}
    for member in MEMBERS:
        path = args.root / member / "apcp_sfc" / f"selected_003_075_2019072200_{member}.grib2"
        paths[member] = path
        decoded[member] = decode(path)

    a, b = msg(decoded["p01"], 36, 39), msg(decoded["p01"], 36, 42)
    delta = b["values"] - a["values"]
    target = (
        (a["latitude"][:, None] >= 10) & (a["latitude"][:, None] <= 22)
        & (a["longitude"][None, :] >= 68) & (a["longitude"][None, :] <= 80)
    )
    bad = np.argwhere(target & (delta < -0.1000000001))

    cells = []
    for row, col in bad:
        cell = {"latitude": float(a["latitude"][row]), "longitude": float(a["longitude"][col])}
        member_values = {}
        for member in MEMBERS:
            left, right = msg(decoded[member], 36, 39), msg(decoded[member], 36, 42)
            member_values[member] = {
                "accumulation_36_39_mm": float(left["values"][row, col]),
                "accumulation_36_42_mm": float(right["values"][row, col]),
                "increment_39_42_mm": float(right["values"][row, col] - left["values"][row, col]),
                "packing_error_36_39_mm": left["metadata"]["packingError"],
                "packing_error_36_42_mm": right["metadata"]["packingError"],
            }
        neighbors = []
        for rr in range(max(0, row - 1), min(delta.shape[0], row + 2)):
            for cc in range(max(0, col - 1), min(delta.shape[1], col + 2)):
                neighbors.append({
                    "latitude": float(a["latitude"][rr]),
                    "longitude": float(a["longitude"][cc]),
                    "accumulation_36_39_mm": float(a["values"][rr, cc]),
                    "accumulation_36_42_mm": float(b["values"][rr, cc]),
                    "increment_39_42_mm": float(delta[rr, cc]),
                })
        cell["members"] = member_values
        cell["p01_3x3_neighborhood"] = neighbors
        cells.append(cell)

    p01_messages = []
    for item in decoded["p01"]:
        if 27 <= int(item["metadata"]["endStep"]) <= 51:
            p01_messages.append({"message_number": item["message_number"], **item["metadata"]})

    index_path = args.root / "p01" / "apcp_sfc" / "apcp_sfc_2019072200_p01.grib2.idx"
    receipt_path = index_path.with_name(index_path.name + ".receipt.json")
    index_text = index_path.read_text(encoding="utf-8")
    indexed_ranges = [tuple(map(int, match)) for match in re.findall(r":(\d+)-(\d+) hour acc fcst:", index_text)]
    direct_matches = [pair for pair in indexed_ranges if pair == (39, 42)]
    nested_matches = [
        {"total": [base, 42], "prefix": [base, 39]}
        for base in range(40)
        if (base, 42) in indexed_ranges and (base, 39) in indexed_ranges
    ]
    original_pair = {"total": [36, 42], "prefix": [36, 39]}
    alternative_nested_matches = [candidate for candidate in nested_matches if candidate != original_pair]
    index_receipt = json.loads(receipt_path.read_text(encoding="utf-8"))

    first_meta, second_meta = a["metadata"], b["metadata"]
    first_quantum = packing_quantum(first_meta["binaryScaleFactor"], first_meta["decimalScaleFactor"])
    second_quantum = packing_quantum(second_meta["binaryScaleFactor"], second_meta["decimalScaleFactor"])
    difference_error = maximum_independent_difference_error(
        first_meta["binaryScaleFactor"], first_meta["decimalScaleFactor"],
        second_meta["binaryScaleFactor"], second_meta["decimalScaleFactor"],
    )
    classification = classify_negative_increment(
        float(delta[target].min()), maximum_packing_error_mm=difference_error
    )

    result = {
        "investigation": "GEFSv12 2019-07-22 00Z p01 Day-2 +39-to-+42 increment",
        "cache_only": True,
        "source_files": {
            member: {"path": str(path), "sha256": sha256(path), "bytes": path.stat().st_size}
            for member, path in paths.items()
        },
        "p01_day2_participating_messages": p01_messages,
        "affected_cell_count": len(cells),
        "affected_cells": cells,
        "global_increment_min_mm": float(delta.min()),
        "global_cells_below_minus_0_1_mm": int((delta < -0.1000000001).sum()),
        "target_increment_min_mm": float(delta[target].min()),
        "target_cells_below_minus_0_1_mm": int((delta[target] < -0.1000000001).sum()),
        "quantization_analysis": {
            "decoded_value_formula": "Y = (referenceValue + X * 2^E) * 10^-D",
            "accumulation_36_39_quantum_mm": first_quantum,
            "accumulation_36_39_rounding_error_bound_mm": first_quantum / 2,
            "accumulation_36_42_quantum_mm": second_quantum,
            "accumulation_36_42_rounding_error_bound_mm": second_quantum / 2,
            "maximum_independent_difference_error_mm": difference_error,
            "operational_tolerance_mm": 0.1,
            "classification": classification.value,
            "operationally_admissible": negative_increment_admissible(
                float(delta[target].min()), maximum_packing_error_mm=difference_error
            ),
            "note": "ecCodes 2.48 does not expose packingError for these complex-packed messages; bounds are derived from the actual binary and decimal scales with exact zero references.",
        },
        "official_index_analysis": {
            "index_path": str(index_path),
            "index_sha256": sha256(index_path),
            "receipt_url": index_receipt["url"],
            "direct_39_42_matches": direct_matches,
            "original_nested_39_42_match": original_pair if original_pair in nested_matches else None,
            "alternative_nested_39_42_matches": alternative_nested_matches,
            "alternate_precipitation_representation_found": False,
            "conclusion": "No independent official reconstruction is present in the NOAA apcp_sfc index for this initialization/member.",
        },
    }
    rendered = json.dumps(result, indent=2, sort_keys=True)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)


if __name__ == "__main__":
    main()
