"""Decode one official GEFSv12 GRIB message in memory for acquisition QC.

This probe never writes the downloaded message. It is intentionally unsuitable
for bulk acquisition; the production adapter must add retry/inventory/manifests.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from urllib.request import Request, urlopen

import numpy as np
from eccodes import codes_get, codes_get_array, codes_get_values, codes_new_from_message, codes_release


DEFAULT_GRIB_URL = (
    "https://noaa-gefs-retrospective.s3.amazonaws.com/GEFSv12/reforecast/2000/"
    "2000010100/c00/Days%3A1-10/apcp_sfc_2000010100_c00.grib2"
)


def fetch_bytes(url: str, byte_range: tuple[int, int] | None = None) -> bytes:
    headers = {}
    if byte_range is not None:
        headers["Range"] = f"bytes={byte_range[0]}-{byte_range[1]}"
    request = Request(url, headers=headers)
    with urlopen(request, timeout=60) as response:
        data = response.read()
        if byte_range is not None:
            expected = byte_range[1] - byte_range[0] + 1
            if len(data) != expected:
                raise ValueError(f"expected {expected} range bytes, received {len(data)}")
        return data


def first_message_range(index_text: str) -> tuple[int, int]:
    rows = [row for row in index_text.splitlines() if row.strip()]
    if len(rows) < 2:
        raise ValueError("index needs at least two messages to bound the first range")
    first_offset = int(rows[0].split(":", 2)[1])
    second_offset = int(rows[1].split(":", 2)[1])
    if first_offset != 0 or second_offset <= first_offset:
        raise ValueError("unexpected GRIB index offsets")
    return first_offset, second_offset - 1


def decode_probe(message: bytes, bounds: tuple[float, float, float, float]) -> dict:
    handle = codes_new_from_message(message)
    try:
        latitudes = np.asarray(codes_get_array(handle, "latitudes"))
        longitudes = np.asarray(codes_get_array(handle, "longitudes"))
        values = np.asarray(codes_get_values(handle))
        south, north, west, east = bounds
        mask = (
            (latitudes >= south)
            & (latitudes <= north)
            & (longitudes >= west)
            & (longitudes <= east)
        )
        if not mask.any():
            raise ValueError("requested geographic subset contains no grid points")
        subset = values[mask]
        return {
            "edition": int(codes_get(handle, "edition")),
            "short_name": str(codes_get(handle, "shortName")),
            "name": str(codes_get(handle, "name")),
            "units": str(codes_get(handle, "units")),
            "type_of_level": str(codes_get(handle, "typeOfLevel")),
            "data_date": int(codes_get(handle, "dataDate")),
            "data_time": int(codes_get(handle, "dataTime")),
            "step_range": str(codes_get(handle, "stepRange")),
            "forecast_time": int(codes_get(handle, "forecastTime")),
            "grid_type": str(codes_get(handle, "gridType")),
            "ni": int(codes_get(handle, "Ni")),
            "nj": int(codes_get(handle, "Nj")),
            "global_point_count": int(values.size),
            "subset_bounds_south_north_west_east": list(bounds),
            "subset_point_count": int(subset.size),
            "subset_min": float(np.nanmin(subset)),
            "subset_max": float(np.nanmax(subset)),
            "subset_nonfinite_count": int((~np.isfinite(subset)).sum()),
        }
    finally:
        codes_release(handle)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--grib-url", default=DEFAULT_GRIB_URL)
    parser.add_argument("--south", type=float, default=10.0)
    parser.add_argument("--north", type=float, default=22.0)
    parser.add_argument("--west", type=float, default=68.0)
    parser.add_argument("--east", type=float, default=80.0)
    args = parser.parse_args()

    index_url = args.grib_url + ".idx"
    index_bytes = fetch_bytes(index_url)
    byte_range = first_message_range(index_bytes.decode("utf-8"))
    message = fetch_bytes(args.grib_url, byte_range)
    result = {
        "grib_url": args.grib_url,
        "index_url": index_url,
        "index_byte_size": len(index_bytes),
        "index_sha256": hashlib.sha256(index_bytes).hexdigest(),
        "message_byte_range": list(byte_range),
        "message_byte_size": len(message),
        "message_sha256": hashlib.sha256(message).hexdigest(),
        "decoded": decode_probe(
            message, (args.south, args.north, args.west, args.east)
        ),
        "persistence": "none; index and GRIB message were held in memory only",
    }
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
