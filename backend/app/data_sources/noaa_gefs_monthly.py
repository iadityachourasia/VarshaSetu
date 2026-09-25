"""GEFSv12 adapters used only by the bounded Phase 1C monthly pilot."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timezone

import numpy as np
from eccodes import (
    codes_get,
    codes_get_array,
    codes_get_values,
    codes_new_from_message,
    codes_release,
)

from backend.app.data.accumulation import GriddedAccumulationMessage


BASE_URL = "https://noaa-gefs-retrospective.s3.amazonaws.com/GEFSv12/reforecast"
PRECIPITATION_PATTERN = re.compile(r":(\d+)-(\d+) hour acc fcst:")


@dataclass(frozen=True)
class GenericIndexEntry:
    message_number: int
    byte_start: int
    byte_end: int
    description: str

    @property
    def byte_size(self) -> int:
        return self.byte_end - self.byte_start + 1


@dataclass(frozen=True)
class DecodedGrid:
    values: np.ndarray
    latitude: np.ndarray
    longitude: np.ndarray
    metadata: dict


@dataclass(frozen=True)
class AtmosphericSpec:
    canonical_name: str
    object_family: str
    index_parameter: str
    index_level: str
    short_name: str
    parameter_name: str
    type_of_level: str
    level: int | str
    units: tuple[str, ...]


ATMOSPHERIC_SPECS = {
    "u850": AtmosphericSpec(
        "nwp_u850", "ugrd_pres", "UGRD", "850 mb", "u",
        "U component of wind", "isobaricInhPa", 850, ("m s**-1", "m/s"),
    ),
    "v850": AtmosphericSpec(
        "nwp_v850", "vgrd_pres", "VGRD", "850 mb", "v",
        "V component of wind", "isobaricInhPa", 850, ("m s**-1", "m/s"),
    ),
    "q700": AtmosphericSpec(
        "nwp_q700", "spfh_pres_abv700mb", "SPFH", "700 mb", "q",
        "Specific humidity", "isobaricInhPa", 700, ("kg kg**-1", "kg/kg"),
    ),
    "z500": AtmosphericSpec(
        "nwp_z500_height", "hgt_pres_abv700mb", "HGT", "500 mb", "gh",
        "Geopotential height", "isobaricInhPa", 500, ("gpm", "m"),
    ),
    "mslp": AtmosphericSpec(
        "nwp_mslp", "pres_msl", "PRES", "mean sea level", "msl",
        "Mean sea level pressure", "meanSea", 0, ("Pa",),
    ),
    "pwat": AtmosphericSpec(
        "nwp_tcwv", "pwat_eatm", "PWAT",
        "entire atmosphere (considered as a single layer)", "pwat",
        "Precipitable water", "atmosphereSingleLayer", 0, ("kg m**-2", "kg m-2"),
    ),
}


def object_url(initialization: datetime, member: str, object_family: str) -> str:
    if initialization.tzinfo is None or initialization.utcoffset() != timezone.utc.utcoffset(initialization):
        raise ValueError("initialization must be timezone-aware UTC")
    if member not in {"c00", "p01", "p02", "p03", "p04"}:
        raise ValueError(f"unsupported daily member {member}")
    stamp = initialization.strftime("%Y%m%d%H")
    return (
        f"{BASE_URL}/{initialization:%Y}/{stamp}/{member}/Days%3A1-10/"
        f"{object_family}_{stamp}_{member}.grib2"
    )


def parse_generic_index(index_text: str) -> list[GenericIndexEntry]:
    rows = [row for row in index_text.splitlines() if row.strip()]
    parsed: list[tuple[int, int, str]] = []
    for row in rows:
        parts = row.split(":", 2)
        if len(parts) != 3 or not parts[0].isdigit() or not parts[1].isdigit():
            raise ValueError(f"unrecognized GEFS index row: {row}")
        parsed.append((int(parts[0]), int(parts[1]), row))
    entries: list[GenericIndexEntry] = []
    for offset, (number, start, row) in enumerate(parsed):
        end = parsed[offset + 1][1] - 1 if offset + 1 < len(parsed) else -1
        entries.append(GenericIndexEntry(number, start, end, row))
    return entries


def select_precipitation_entries(entries: list[GenericIndexEntry]) -> list[GenericIndexEntry]:
    selected: list[GenericIndexEntry] = []
    observed_ranges: list[tuple[int, int]] = []
    for entry in entries:
        match = PRECIPITATION_PATTERN.search(entry.description)
        if match and int(match.group(2)) <= 75:
            selected.append(entry)
            observed_ranges.append((int(match.group(1)), int(match.group(2))))
    expected = [
        ((end - 3) if end % 6 == 3 else (end - 6), end)
        for end in range(3, 76, 3)
    ]
    if observed_ranges != expected or len(selected) != 25:
        raise ValueError(
            f"unexpected precipitation interval sequence: {observed_ranges}"
        )
    if any(entry.byte_end < entry.byte_start for entry in selected):
        raise ValueError("selected precipitation message lacks a byte boundary")
    return selected


def select_atmospheric_entry(
    entries: list[GenericIndexEntry], spec: AtmosphericSpec, lead_hour: int
) -> GenericIndexEntry:
    marker = (
        f":{spec.index_parameter}:{spec.index_level}:{lead_hour} hour fcst:"
    )
    matches = [entry for entry in entries if marker in entry.description]
    if len(matches) != 1:
        raise ValueError(
            f"expected one {spec.object_family} {spec.index_level} lead {lead_hour}; "
            f"found {len(matches)}"
        )
    if matches[0].byte_end < matches[0].byte_start:
        raise ValueError("selected atmospheric message lacks a byte boundary")
    return matches[0]


def _optional(handle, key: str):
    try:
        return codes_get(handle, key)
    except Exception:
        return None


def _decode_grid(handle) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    ni = int(codes_get(handle, "Ni"))
    nj = int(codes_get(handle, "Nj"))
    values = np.asarray(codes_get_values(handle), dtype=float).reshape(nj, ni)
    lat2d = np.asarray(codes_get_array(handle, "latitudes"), dtype=float).reshape(nj, ni)
    lon2d = np.asarray(codes_get_array(handle, "longitudes"), dtype=float).reshape(nj, ni)
    latitude = lat2d[:, 0]
    longitude = lon2d[0, :]
    if not np.allclose(lat2d, latitude[:, None]) or not np.allclose(
        lon2d, longitude[None, :]
    ):
        raise ValueError("GEFS monthly pilot requires a rectilinear grid")
    if np.all(np.diff(latitude) < 0):
        latitude = latitude[::-1]
        values = values[::-1, :]
    elif not np.all(np.diff(latitude) > 0):
        raise ValueError("latitude is not monotonic")
    if not np.all(np.diff(longitude) > 0):
        raise ValueError("longitude is not ascending")
    return values, latitude, longitude


def _member_metadata(handle, member: str, description: str) -> dict:
    perturbation_number = _optional(handle, "perturbationNumber")
    ensemble_type = _optional(handle, "typeOfEnsembleForecast")
    expected_number = 0 if member == "c00" else int(member[1:])
    if perturbation_number is not None and int(perturbation_number) != expected_number:
        raise ValueError(
            f"decoded perturbation {perturbation_number} does not match requested {member}"
        )
    if member == "c00" and "ENS=low-res ctl" not in description:
        raise ValueError("control-member identity is absent from index metadata")
    if member != "c00" and f"ENS=+{expected_number}" not in description:
        raise ValueError(f"perturbed-member identity is absent for {member}")
    return {
        "requested_member": member,
        "perturbation_number": perturbation_number,
        "type_of_ensemble_forecast": ensemble_type,
        "index_member_description": description.rsplit(":", 1)[-1],
    }


def _common_metadata(handle, latitude: np.ndarray, longitude: np.ndarray) -> dict:
    return {
        "forecast_init": (
            f"{int(codes_get(handle, 'dataDate')):08d}T"
            f"{int(codes_get(handle, 'dataTime')):04d}Z"
        ),
        "forecast_step": int(codes_get(handle, "forecastTime")),
        "step_range": str(codes_get(handle, "stepRange")),
        "step_type": str(codes_get(handle, "stepType")),
        "valid_date": int(codes_get(handle, "validityDate")),
        "valid_time": int(codes_get(handle, "validityTime")),
        "short_name": str(codes_get(handle, "shortName")),
        "parameter_name": str(codes_get(handle, "name")),
        "type_of_level": str(codes_get(handle, "typeOfLevel")),
        "level": codes_get(handle, "level"),
        "units": str(codes_get(handle, "units")),
        "packing_type": str(codes_get(handle, "packingType")),
        "bits_per_value": int(codes_get(handle, "bitsPerValue")),
        "reference_value": float(codes_get(handle, "referenceValue")),
        "binary_scale_factor": int(codes_get(handle, "binaryScaleFactor")),
        "decimal_scale_factor": int(codes_get(handle, "decimalScaleFactor")),
        "packing_error": _optional(handle, "packingError"),
        "type_of_statistical_processing": _optional(
            handle, "typeOfStatisticalProcessing"
        ),
        "number_of_time_ranges": _optional(handle, "numberOfTimeRanges"),
        "length_of_time_range": _optional(handle, "lengthOfTimeRange"),
        "indicator_of_unit_for_time_range": _optional(
            handle, "indicatorOfUnitForTimeRange"
        ),
        "type_of_time_increment": _optional(handle, "typeOfTimeIncrement"),
        "grid": {
            "grid_type": str(codes_get(handle, "gridType")),
            "ni": int(codes_get(handle, "Ni")),
            "nj": int(codes_get(handle, "Nj")),
            "latitude_first": float(latitude[0]),
            "latitude_last": float(latitude[-1]),
            "longitude_first": float(longitude[0]),
            "longitude_last": float(longitude[-1]),
            "latitude_orientation": "ascending_after_canonicalization",
            "longitude_convention": "0_to_360",
        },
    }


def decode_precipitation_message(
    payload: bytes,
    *,
    member: str,
    description: str,
    source_id: str,
) -> tuple[GriddedAccumulationMessage, DecodedGrid]:
    handle = codes_new_from_message(payload)
    try:
        values, latitude, longitude = _decode_grid(handle)
        metadata = _common_metadata(handle, latitude, longitude)
        metadata.update(_member_metadata(handle, member, description))
        if metadata["short_name"] != "tp" or metadata["parameter_name"] != "Total Precipitation":
            raise ValueError("unexpected precipitation identity")
        if metadata["step_type"] != "accum" or metadata["units"] not in {
            "kg m**-2", "kg m-2"
        }:
            raise ValueError("unexpected precipitation accumulation semantics or units")
        start_step = int(codes_get(handle, "startStep"))
        end_step = int(codes_get(handle, "endStep"))
        metadata.update({"start_step": start_step, "end_step": end_step})
        accumulation = GriddedAccumulationMessage(
            start_hour=start_step,
            end_hour=end_step,
            values_mm=values,
            source_id=source_id,
            packing_quantum_mm=(
                (2.0 ** metadata["binary_scale_factor"])
                * (10.0 ** (-metadata["decimal_scale_factor"]))
            ),
        )
        return accumulation, DecodedGrid(values, latitude, longitude, metadata)
    finally:
        codes_release(handle)


def decode_atmospheric_message(
    payload: bytes,
    *,
    member: str,
    description: str,
    spec: AtmosphericSpec,
    lead_hour: int,
) -> DecodedGrid:
    handle = codes_new_from_message(payload)
    try:
        values, latitude, longitude = _decode_grid(handle)
        metadata = _common_metadata(handle, latitude, longitude)
        metadata.update(_member_metadata(handle, member, description))
        metadata["archive_object_family"] = spec.object_family
        if metadata["short_name"] != spec.short_name:
            raise ValueError(f"unexpected shortName for {spec.canonical_name}")
        if metadata["parameter_name"] != spec.parameter_name:
            raise ValueError(f"unexpected parameter name for {spec.canonical_name}")
        if metadata["type_of_level"] != spec.type_of_level:
            raise ValueError(f"unexpected level type for {spec.canonical_name}")
        if metadata["level"] != spec.level:
            raise ValueError(f"unexpected level for {spec.canonical_name}")
        if metadata["units"] not in spec.units:
            raise ValueError(f"unexpected units for {spec.canonical_name}: {metadata['units']}")
        if metadata["forecast_step"] != lead_hour or metadata["step_type"] != "instant":
            raise ValueError(f"unexpected forecast timing for {spec.canonical_name}")
        if not np.isfinite(values).all():
            raise ValueError(f"non-finite values in {spec.canonical_name}")
        return DecodedGrid(values, latitude, longitude, metadata)
    finally:
        codes_release(handle)


def crop_grid(
    decoded: DecodedGrid, *, south: float, north: float, west: float, east: float
) -> DecodedGrid:
    lat_mask = (decoded.latitude >= south) & (decoded.latitude <= north)
    lon_mask = (decoded.longitude >= west) & (decoded.longitude <= east)
    if not lat_mask.any() or not lon_mask.any():
        raise ValueError("requested crop has no source grid points")
    return DecodedGrid(
        values=decoded.values[np.ix_(lat_mask, lon_mask)],
        latitude=decoded.latitude[lat_mask],
        longitude=decoded.longitude[lon_mask],
        metadata=decoded.metadata,
    )
