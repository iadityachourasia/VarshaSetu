"""Small first-order conservative rectilinear regridder for the Phase 1B pilot."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path

import numpy as np


EARTH_RADIUS_M = 6_371_000.0


def cell_bounds_from_centers(centers: np.ndarray) -> np.ndarray:
    centers = np.asarray(centers, dtype=float)
    if centers.ndim != 1 or centers.size < 2 or not np.all(np.diff(centers) > 0):
        raise ValueError("cell centers must be a strictly ascending 1-D coordinate")
    midpoints = (centers[:-1] + centers[1:]) / 2
    bounds = np.empty(centers.size + 1, dtype=float)
    bounds[1:-1] = midpoints
    bounds[0] = centers[0] - (midpoints[0] - centers[0])
    bounds[-1] = centers[-1] + (centers[-1] - midpoints[-1])
    return bounds


def grid_cell_areas(latitude: np.ndarray, longitude: np.ndarray) -> np.ndarray:
    lat_bounds = np.deg2rad(cell_bounds_from_centers(latitude))
    lon_bounds = np.deg2rad(cell_bounds_from_centers(longitude))
    lat_factor = np.sin(lat_bounds[1:]) - np.sin(lat_bounds[:-1])
    lon_width = lon_bounds[1:] - lon_bounds[:-1]
    return (EARTH_RADIUS_M**2) * lat_factor[:, None] * lon_width[None, :]


@dataclass(frozen=True)
class ConservativeWeights:
    source_flat_index: np.ndarray
    target_flat_index: np.ndarray
    weight: np.ndarray
    source_shape: tuple[int, int]
    target_shape: tuple[int, int]

    def apply(self, source: np.ndarray) -> np.ndarray:
        source = np.asarray(source, dtype=float)
        if source.shape != self.source_shape:
            raise ValueError("source grid shape does not match conservative weights")
        target = np.zeros(self.target_shape[0] * self.target_shape[1], dtype=float)
        np.add.at(
            target,
            self.target_flat_index,
            source.reshape(-1)[self.source_flat_index] * self.weight,
        )
        return target.reshape(self.target_shape)

    def save(self, path: str | Path) -> tuple[str, int]:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        rows = np.empty(
            self.weight.size,
            dtype=[("source", "<i8"), ("target", "<i8"), ("weight", "<f8")],
        )
        rows["source"] = self.source_flat_index
        rows["target"] = self.target_flat_index
        rows["weight"] = self.weight
        with path.open("wb") as handle:
            np.save(handle, rows, allow_pickle=False)
        payload = path.read_bytes()
        return hashlib.sha256(payload).hexdigest(), len(payload)


def build_first_order_conservative_weights(
    source_latitude: np.ndarray,
    source_longitude: np.ndarray,
    target_latitude: np.ndarray,
    target_longitude: np.ndarray,
) -> ConservativeWeights:
    """Build target-area-normalized spherical overlap weights."""

    source_latitude = np.asarray(source_latitude, dtype=float)
    source_longitude = np.asarray(source_longitude, dtype=float)
    target_latitude = np.asarray(target_latitude, dtype=float)
    target_longitude = np.asarray(target_longitude, dtype=float)
    slat = cell_bounds_from_centers(source_latitude)
    slon = cell_bounds_from_centers(source_longitude)
    tlat = cell_bounds_from_centers(target_latitude)
    tlon = cell_bounds_from_centers(target_longitude)

    source_index: list[int] = []
    target_index: list[int] = []
    weights: list[float] = []
    source_nlon = source_longitude.size
    target_nlon = target_longitude.size

    for ty in range(target_latitude.size):
        lat_south, lat_north = tlat[ty], tlat[ty + 1]
        target_lat_factor = np.sin(np.deg2rad(lat_north)) - np.sin(np.deg2rad(lat_south))
        for tx in range(target_longitude.size):
            lon_west, lon_east = tlon[tx], tlon[tx + 1]
            target_area_factor = target_lat_factor * np.deg2rad(lon_east - lon_west)
            row_weight = 0.0
            for sy in range(source_latitude.size):
                overlap_south = max(lat_south, slat[sy])
                overlap_north = min(lat_north, slat[sy + 1])
                if overlap_south >= overlap_north:
                    continue
                lat_factor = np.sin(np.deg2rad(overlap_north)) - np.sin(
                    np.deg2rad(overlap_south)
                )
                for sx in range(source_longitude.size):
                    overlap_west = max(lon_west, slon[sx])
                    overlap_east = min(lon_east, slon[sx + 1])
                    if overlap_west >= overlap_east:
                        continue
                    overlap_factor = lat_factor * np.deg2rad(overlap_east - overlap_west)
                    value = overlap_factor / target_area_factor
                    source_index.append(sy * source_nlon + sx)
                    target_index.append(ty * target_nlon + tx)
                    weights.append(value)
                    row_weight += value
            if not np.isclose(row_weight, 1.0, rtol=0, atol=1e-10):
                raise ValueError(
                    f"source grid does not fully cover target cell {(ty, tx)}; weight sum={row_weight}"
                )

    return ConservativeWeights(
        source_flat_index=np.asarray(source_index, dtype=np.int64),
        target_flat_index=np.asarray(target_index, dtype=np.int64),
        weight=np.asarray(weights, dtype=np.float64),
        source_shape=(source_latitude.size, source_longitude.size),
        target_shape=(target_latitude.size, target_longitude.size),
    )


def area_weighted_integral(
    rainfall_mm: np.ndarray,
    latitude: np.ndarray,
    longitude: np.ndarray,
    valid_mask: np.ndarray,
) -> float:
    rainfall_mm = np.asarray(rainfall_mm, dtype=float)
    valid_mask = np.asarray(valid_mask, dtype=bool)
    if rainfall_mm.shape != valid_mask.shape:
        raise ValueError("rainfall and valid mask shapes differ")
    area = grid_cell_areas(latitude, longitude)
    return float(np.sum(rainfall_mm[valid_mask] * area[valid_mask]))
