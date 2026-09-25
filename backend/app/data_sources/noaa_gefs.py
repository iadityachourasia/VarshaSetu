"""Minimal NOAA GEFSv12 reforecast adapter for the one-window pilot."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen

import numpy as np
from eccodes import codes_get, codes_get_array, codes_get_values, codes_new_from_message, codes_release

from backend.app.data.accumulation import GriddedAccumulationMessage


INDEX_PATTERN = re.compile(r"^(\d+):(\d+):.*:(\d+)-(\d+) hour acc fcst:")


@dataclass(frozen=True)
class IndexEntry:
    message_number: int
    byte_start: int
    byte_end: int
    start_step: int
    end_step: int
    description: str


@dataclass(frozen=True)
class DecodedMessage:
    accumulation: GriddedAccumulationMessage
    latitude: np.ndarray
    longitude: np.ndarray
    metadata: dict


def gefs_object_url(initialization: datetime, member: str = "c00") -> str:
    if initialization.tzinfo is None or initialization.utcoffset() != timezone.utc.utcoffset(initialization):
        raise ValueError("GEFS initialization must be timezone-aware UTC")
    stamp = initialization.strftime("%Y%m%d%H")
    return (
        "https://noaa-gefs-retrospective.s3.amazonaws.com/GEFSv12/reforecast/"
        f"{initialization:%Y}/{stamp}/{member}/Days%3A1-10/apcp_sfc_{stamp}_{member}.grib2"
    )


def fetch_url(url: str, byte_range: tuple[int, int] | None = None) -> tuple[bytes, dict]:
    headers = {}
    if byte_range is not None:
        headers["Range"] = f"bytes={byte_range[0]}-{byte_range[1]}"
    request = Request(url, headers=headers)
    with urlopen(request, timeout=120) as response:
        payload = response.read()
        response_headers = {key.lower(): value for key, value in response.headers.items()}
        status = getattr(response, "status", None)
    if byte_range is not None:
        expected = byte_range[1] - byte_range[0] + 1
        if len(payload) != expected:
            raise ValueError(f"expected {expected} range bytes, received {len(payload)}")
        if status != 206:
            raise ValueError(f"NOAA server did not honor byte range; HTTP status {status}")
    return payload, {"http_status": status, "headers": response_headers}


def parse_index(index_text: str, object_size: int | None = None) -> list[IndexEntry]:
    raw_rows = [row for row in index_text.splitlines() if row.strip()]
    parsed: list[tuple[int, int, int, int, str]] = []
    for row in raw_rows:
        match = INDEX_PATTERN.match(row)
        if not match:
            raise ValueError(f"unrecognized GEFS index row: {row}")
        parsed.append(
            (
                int(match.group(1)),
                int(match.group(2)),
                int(match.group(3)),
                int(match.group(4)),
                row,
            )
        )
    entries: list[IndexEntry] = []
    for index, (number, start, start_step, end_step, description) in enumerate(parsed):
        if index + 1 < len(parsed):
            end = parsed[index + 1][1] - 1
        elif object_size is not None:
            end = object_size - 1
        else:
            end = -1
        entries.append(IndexEntry(number, start, end, start_step, end_step, description))
    return entries


def _get(handle, key: str):
    try:
        return codes_get(handle, key)
    except Exception:
        return None


def decode_message(payload: bytes, source_id: str) -> DecodedMessage:
    handle = codes_new_from_message(payload)
    try:
        ni = int(codes_get(handle, "Ni"))
        nj = int(codes_get(handle, "Nj"))
        values = np.asarray(codes_get_values(handle), dtype=float).reshape(nj, ni)
        lat2d = np.asarray(codes_get_array(handle, "latitudes"), dtype=float).reshape(nj, ni)
        lon2d = np.asarray(codes_get_array(handle, "longitudes"), dtype=float).reshape(nj, ni)
        latitude = lat2d[:, 0]
        longitude = lon2d[0, :]
        if not np.allclose(lat2d, latitude[:, None]) or not np.allclose(lon2d, longitude[None, :]):
            raise ValueError("GEFS pilot expects a rectilinear regular latitude/longitude grid")
        if np.all(np.diff(latitude) < 0):
            latitude = latitude[::-1]
            values = values[::-1, :]
        elif not np.all(np.diff(latitude) > 0):
            raise ValueError("GEFS latitude coordinate is not monotonic")
        if not np.all(np.diff(longitude) > 0):
            raise ValueError("GEFS longitude coordinate is not ascending")

        start_step = int(codes_get(handle, "startStep"))
        end_step = int(codes_get(handle, "endStep"))
        metadata = {
            "forecast_init": f"{int(codes_get(handle, 'dataDate')):08d}T{int(codes_get(handle, 'dataTime')):04d}Z",
            "forecast_step": int(_get(handle, "forecastTime") or 0),
            "step_range": str(codes_get(handle, "stepRange")),
            "start_step": start_step,
            "end_step": end_step,
            "step_type": str(codes_get(handle, "stepType")),
            "valid_date": int(codes_get(handle, "validityDate")),
            "valid_time": int(codes_get(handle, "validityTime")),
            "units": str(codes_get(handle, "units")),
            "member": "c00",
            "grid": {
                "grid_type": str(codes_get(handle, "gridType")),
                "ni": ni,
                "nj": nj,
                "latitude_first": float(latitude[0]),
                "latitude_last": float(latitude[-1]),
                "longitude_first": float(longitude[0]),
                "longitude_last": float(longitude[-1]),
                "latitude_orientation": "ascending_after_canonicalization",
                "longitude_convention": "0_to_360",
            },
            "parameter_name": str(codes_get(handle, "name")),
            "short_name": str(codes_get(handle, "shortName")),
            "archive_object_family": "apcp_sfc",
            "packing_type": str(codes_get(handle, "packingType")),
            "bits_per_value": int(codes_get(handle, "bitsPerValue")),
            "binary_scale_factor": int(codes_get(handle, "binaryScaleFactor")),
            "decimal_scale_factor": int(codes_get(handle, "decimalScaleFactor")),
        }
        if metadata["step_type"] != "accum":
            raise ValueError("GEFS precipitation message is not an accumulation")
        if metadata["short_name"] != "tp" or metadata["parameter_name"] != "Total Precipitation":
            raise ValueError("unexpected GEFS precipitation identity")
        if metadata["units"] not in {"kg m**-2", "kg m-2"}:
            raise ValueError(f"unsupported GEFS precipitation units: {metadata['units']}")
        return DecodedMessage(
            accumulation=GriddedAccumulationMessage(
                start_hour=start_step,
                end_hour=end_step,
                values_mm=values,
                source_id=source_id,
            ),
            latitude=latitude,
            longitude=longitude,
            metadata=metadata,
        )
    finally:
        codes_release(handle)


def crop_message(
    decoded: DecodedMessage, *, south: float, north: float, west: float, east: float
) -> DecodedMessage:
    lat_mask = (decoded.latitude >= south) & (decoded.latitude <= north)
    lon_mask = (decoded.longitude >= west) & (decoded.longitude <= east)
    if not lat_mask.any() or not lon_mask.any():
        raise ValueError("GEFS crop has no grid points")
    return DecodedMessage(
        accumulation=GriddedAccumulationMessage(
            start_hour=decoded.accumulation.start_hour,
            end_hour=decoded.accumulation.end_hour,
            values_mm=decoded.accumulation.values_mm[np.ix_(lat_mask, lon_mask)],
            source_id=decoded.accumulation.source_id,
        ),
        latitude=decoded.latitude[lat_mask],
        longitude=decoded.longitude[lon_mask],
        metadata=decoded.metadata,
    )


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()
