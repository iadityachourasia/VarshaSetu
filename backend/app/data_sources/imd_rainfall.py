"""Reader for the official IMD 0.25-degree yearly rainfall NetCDF."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path

import numpy as np
from scipy.io import netcdf_file


@dataclass(frozen=True)
class ImdDailyField:
    rainfall_mm: np.ndarray
    valid_mask: np.ndarray
    latitude: np.ndarray
    longitude: np.ndarray
    metadata: dict


def _json_value(value):
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    if isinstance(value, np.generic):
        return value.item()
    return value


def inspect_imd_netcdf(path: str | Path) -> dict:
    path = Path(path)
    with netcdf_file(path, "r", mmap=False) as dataset:
        variables = {}
        for name, variable in dataset.variables.items():
            variables[name] = {
                "dimensions": list(variable.dimensions),
                "shape": list(variable.shape),
                "dtype": variable.typecode(),
                "attributes": {
                    key: _json_value(getattr(variable, key)) for key in variable._attributes
                },
            }
        return {
            "format_magic": path.read_bytes()[:4].hex(),
            "dimensions": {
                name: (None if size is None else int(size)) for name, size in dataset.dimensions.items()
            },
            "global_attributes": {
                key: _json_value(getattr(dataset, key)) for key in dataset._attributes
            },
            "variables": variables,
        }


def _parse_time_origin(units: str) -> datetime:
    prefix = "days since "
    if not units.startswith(prefix):
        raise ValueError(f"unsupported IMD time units: {units}")
    return datetime.fromisoformat(units[len(prefix) :])


def load_imd_day(
    path: str | Path,
    valid_date: date,
    *,
    south: float,
    north: float,
    west: float,
    east: float,
) -> ImdDailyField:
    with netcdf_file(Path(path), "r", mmap=False) as dataset:
        required = {"TIME", "LATITUDE", "LONGITUDE", "RAINFALL"}
        if not required.issubset(dataset.variables):
            raise ValueError("IMD NetCDF is missing required variables")
        time_var = dataset.variables["TIME"]
        units = _json_value(getattr(time_var, "units"))
        origin = _parse_time_origin(units)
        target_offset = (datetime.combine(valid_date, datetime.min.time()) - origin).days
        time_values = np.asarray(time_var.data, dtype=float)
        matches = np.flatnonzero(np.isclose(time_values, target_offset, rtol=0, atol=1e-9))
        if matches.size != 1:
            raise ValueError(f"IMD date {valid_date.isoformat()} does not map to exactly one record")

        rain_var = dataset.variables["RAINFALL"]
        fill_value = float(getattr(rain_var, "_FillValue"))
        missing_value = float(getattr(rain_var, "missing_value"))
        if fill_value != missing_value:
            raise ValueError("IMD _FillValue and missing_value differ")
        latitude = np.asarray(dataset.variables["LATITUDE"].data, dtype=float)
        longitude = np.asarray(dataset.variables["LONGITUDE"].data, dtype=float)
        if not np.all(np.diff(latitude) > 0) or not np.all(np.diff(longitude) > 0):
            raise ValueError("IMD coordinates must be strictly ascending")
        lat_mask = (latitude >= south) & (latitude <= north)
        lon_mask = (longitude >= west) & (longitude <= east)
        rainfall = np.asarray(rain_var.data[int(matches[0])], dtype=float)[np.ix_(lat_mask, lon_mask)]
        valid_mask = np.isfinite(rainfall) & (rainfall != fill_value)
        if (rainfall[valid_mask] < 0).any():
            raise ValueError("IMD valid rainfall contains negative values")
        calendar = _json_value(getattr(time_var, "calendar", "CF default standard calendar"))
        return ImdDailyField(
            rainfall_mm=rainfall,
            valid_mask=valid_mask,
            latitude=latitude[lat_mask],
            longitude=longitude[lon_mask],
            metadata={
                "record_index": int(matches[0]),
                "time_value": float(time_values[matches[0]]),
                "time_units": units,
                "calendar": calendar,
                "netcdf_time_label": (origin + timedelta(days=target_offset)).isoformat(),
                "fill_value": fill_value,
                "missing_value": missing_value,
                "rainfall_units": _json_value(getattr(rain_var, "units")),
                "dimensions": list(rain_var.dimensions),
                "latitude_orientation": "ascending",
                "longitude_orientation": "ascending",
                "longitude_convention": "0_to_360",
            },
        )
