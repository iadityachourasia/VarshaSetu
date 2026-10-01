"""Stage 0 of the coastal/orographic protocol v3 (docs/115, docs/116): build the static_geography_v1 artifact.

    python scripts/build_static_geography.py            # build and write
    python scripts/build_static_geography.py --check    # rebuild in memory and compare with the committed bytes

Reads only the GMTED2010 mean 30 arc-second NetCDF4 (hash pinned below) and the time-invariant IMD valid-cell footprint (cell set only; no rainfall
value is read). Needs h5py, which is a build-time dependency of this script only and is not in backend/requirements.txt.
The artifact is canonical sorted-key JSON (LF bytes) so it can be hash-pinned and tracked despite the *.npy/*.npz ignore rules.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data/static_geography_raw/GMTED2010_mean_30arcsec.nc4"
RAW_SIZE, RAW_MD5 = 249_216_253, "5b6c47502ae8d03b8718349655d5cd95"
RAW_SHA256 = "5aef5bbaa5373d530752ad648c63aa2cc2b14d5a854fe5acf0a61fb8bacca7f8"
PROTOCOL = ROOT / "backend/app/evidence_data/phase6/coastal_orographic_protocol_v3.json"
PROTOCOL_SHA256 = "a9ff78173ddb6026e6b297c2da2128dde2fdcf825ae8b0c368c5f5fa79d199fd"
FOOTPRINT_SOURCE = ROOT / "data/operational_derived/operational_features_2023_2025_v1"
OUT_DIR = ROOT / "backend/app/evidence_data/phase7"
OUT = OUT_DIR / "static_geography_v1.json"

SHAPE = (49, 49)
LAT0, LON0, STEP = 10.0, 68.0, 0.25
MARGIN = 5.0                           # degrees of context on every side, for coast distance and neighbourhood fields
SUB = 30                               # source pixels per 0.25 degree cell (30 arc-second source)
EARTH_RADIUS_KM = 6371.0
FILL = -32768                          # declared fill value of the file; not used for the land test (see aggregate())
# QA criteria of protocol v2 (static_geography.qa); fixed after the v1 diagnostics and before this artifact was built
QA_MIN_LAND_MAJORITY_SHARE = 0.90      # share of footprint cells whose terrain land fraction is >= 0.5
QA_MAX_TERRAIN_LAND_OUTSIDE_FOOTPRINT = 5
ZONE_RULES = {"coastal_km_max": 100.0, "relief_m_min": 300.0}          # protocol v3: the v2 elevation test was removed
ALTERNATIVES = {"coastal_km": [50.0, 75.0, 150.0], "relief_m": [200.0, 250.0, 400.0]}
SUPERSEDED_ELEVATION_M = 400.0
MIN_CELLS = 20


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def footprint() -> np.ndarray:
    base = FOOTPRINT_SOURCE
    cells = None
    for year, role in ((2023, "train"), (2024, "validation")):
        directory = base / str(year) / role / "deterministic"
        pixel = np.load(directory / "pixel_index.npy")
        records = json.loads((directory / "cases.json").read_text(encoding="utf-8"))
        for record in records:
            current = set(pixel[record["row_start"]: record["row_start"] + record["row_count"]].tolist())
            if cells is None:
                cells = current
            elif current != cells:
                raise RuntimeError("valid-cell footprint is not identical across cases")
    mask = np.zeros(SHAPE[0] * SHAPE[1], bool)
    mask[sorted(cells)] = True
    return mask.reshape(SHAPE)


def extended_axes() -> tuple[np.ndarray, np.ndarray]:
    n = int(round((12.0 + 2 * MARGIN) / STEP)) + 1
    lat = LAT0 - MARGIN + STEP * np.arange(n)
    lon = LON0 - MARGIN + STEP * np.arange(n)
    return lat, lon


def aggregate(lat_c: np.ndarray, lon_c: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Area-mean elevation over land source pixels, land fraction and land pixel count per 0.25 degree cell."""
    import h5py

    with h5py.File(RAW, "r") as f:
        src_lat = f["lat"][:]
        src_lon = f["lon"][:]
        half = STEP / 2
        rows = np.where((src_lat <= lat_c.max() + half) & (src_lat >= lat_c.min() - half))[0]
        cols = np.where((src_lon >= lon_c.min() - half) & (src_lon <= lon_c.max() + half))[0]
        block = f["surface_altitude"][rows.min(): rows.max() + 1, cols.min(): cols.max() + 1]
        lat_s, lon_s = src_lat[rows], src_lon[cols]
    land = block > 0                      # this file encodes ocean as 0 m (not as the fill value); a land pixel is therefore one above 0 m
    elev = np.where(land, block, 0).astype(np.float64)
    ci = np.floor((lat_s[:, None] - (lat_c.min() - half)) / STEP).astype(int)      # cell row of each source row
    cj = np.floor((lon_s[None, :] - (lon_c.min() - half)) / STEP).astype(int)
    n_lat, n_lon = len(lat_c), len(lon_c)
    total = np.zeros((n_lat, n_lon))
    land_n = np.zeros((n_lat, n_lon))
    elev_sum = np.zeros((n_lat, n_lon))
    ok_i = (ci >= 0) & (ci < n_lat)
    ok_j = (cj >= 0) & (cj < n_lon)
    for i in np.unique(ci[ok_i]):
        r = np.where((ci[:, 0] == i))[0]
        for j in np.unique(cj[0][ok_j[0]]):
            c = np.where(cj[0] == j)[0]
            sub_land = land[np.ix_(r, c)]
            total[i, j] = sub_land.size
            land_n[i, j] = sub_land.sum()
            elev_sum[i, j] = elev[np.ix_(r, c)][sub_land].sum()
    land_fraction = land_n / np.maximum(total, 1)
    mean_elev = np.where(land_n > 0, elev_sum / np.maximum(land_n, 1), np.nan)
    return mean_elev, land_fraction, total


def great_circle_km(lat1, lon1, lat2, lon2):
    p1, p2 = np.radians(lat1), np.radians(lat2)
    a = np.sin((p2 - p1) / 2) ** 2 + np.cos(p1) * np.cos(p2) * np.sin(np.radians(lon2 - lon1) / 2) ** 2
    return 2 * EARTH_RADIUS_KM * np.arcsin(np.sqrt(a))


def mean3(a: np.ndarray) -> np.ndarray:
    padded = np.pad(a, 1, mode="edge")
    return sum(padded[i: i + a.shape[0], j: j + a.shape[1]] for i in range(3) for j in range(3)) / 9.0


def gradient_vector(field: np.ndarray, lat_c: np.ndarray):
    """d(field)/dx (east) and d(field)/dy (north) per km with central differences on the 0.25 degree grid."""
    dy_km = STEP * np.pi / 180 * EARTH_RADIUS_KM
    dx_km = dy_km * np.cos(np.radians(lat_c))[:, None]
    gy = np.gradient(field, axis=0) / dy_km
    gx = np.gradient(field, axis=1) / dx_km
    return gx, gy


def build() -> dict:
    lat_c, lon_c = extended_axes()
    mean_elev, land_fraction, total = aggregate(lat_c, lon_c)
    terrain_land = land_fraction >= 0.5
    mi, mj = int(round(MARGIN / STEP)), int(round(MARGIN / STEP))
    window = (slice(mi, mi + SHAPE[0]), slice(mj, mj + SHAPE[1]))
    foot = footprint()
    foot_ext = np.zeros(land_fraction.shape, bool)
    foot_ext[window] = foot
    land_mask = terrain_land | foot_ext      # protocol v2: a footprint cell is land by IMD's own definition

    # distance to coast: nearest ocean cell centre of the frozen land-sea mask, searched over the extended grid
    ocean_i, ocean_j = np.where(~land_mask)
    lat_g, lon_g = np.meshgrid(lat_c, lon_c, indexing="ij")
    distance = np.full(land_mask.shape, np.nan)
    for i, j in zip(*np.where(land_mask)):
        distance[i, j] = great_circle_km(lat_g[i, j], lon_g[i, j], lat_g[ocean_i, ocean_j], lon_g[ocean_i, ocean_j]).min()

    # relief: max - min of the aggregated mean elevation over land cells of the 3x3 neighbourhood
    padded = np.pad(np.where(land_mask & np.isfinite(mean_elev), mean_elev, np.nan), 1, constant_values=np.nan)
    stack = np.stack([padded[i: i + mean_elev.shape[0], j: j + mean_elev.shape[1]] for i in range(3) for j in range(3)])
    with np.errstate(all="ignore"):
        relief = np.where(land_mask, np.nanmax(stack, axis=0) - np.nanmin(stack, axis=0), np.nan)

    # terrain gradient: ocean cells at 0 m, one 3x3 mean, central differences (declared builder detail within the protocol)
    elev_for_gradient = np.where(land_mask & np.isfinite(mean_elev), mean_elev, 0.0)
    smooth = mean3(elev_for_gradient)
    gx, gy = gradient_vector(smooth, lat_c)
    slope = np.hypot(gx, gy)
    # coast normal: unit gradient of the 3x3-smoothed land fraction, pointing landward
    cx, cy = gradient_vector(mean3(land_mask.astype(float)), lat_c)
    norm = np.hypot(cx, cy)
    with np.errstate(all="ignore"):
        coast_nx = np.where(norm > 0, cx / norm, 0.0)
        coast_ny = np.where(norm > 0, cy / norm, 0.0)
        terrain_nx = np.where(slope > 0, gx / slope, 0.0)
        terrain_ny = np.where(slope > 0, gy / slope, 0.0)

    sub = {k: v[window] for k, v in dict(mean_elev=mean_elev, land_fraction=land_fraction, land_mask=land_mask, distance=distance, relief=relief,
                                         slope=slope, coast_nx=coast_nx, coast_ny=coast_ny, terrain_nx=terrain_nx, terrain_ny=terrain_ny).items()}
    lf = sub["land_fraction"]

    # QA against the footprint (protocol v2 criteria)
    foot_land_majority = float((lf[foot] >= 0.5).mean())
    outside = int(((lf >= 0.5) & ~foot).sum())
    no_pixel = int(((lf <= 0.0) & foot).sum())
    dist_finite = bool(np.isfinite(np.where(foot, sub["distance"], 0.0)).all())
    qa = {
        "footprint_cells": int(foot.sum()),
        "footprint_cells_terrain_land_majority": int(((lf >= 0.5) & foot).sum()),
        "footprint_terrain_land_majority_share": round(foot_land_majority, 6),
        "footprint_cells_less_than_half_land": int(((lf < 0.5) & foot).sum()),
        "footprint_cells_without_a_land_pixel_elevation_undefined": no_pixel,
        "terrain_land_cells_outside_footprint": outside,
        "all_footprint_cells_have_finite_distance_to_coast": dist_finite,
        "criteria": {"min_footprint_terrain_land_majority_share": QA_MIN_LAND_MAJORITY_SHARE,
                     "max_terrain_land_cells_outside_footprint": QA_MAX_TERRAIN_LAND_OUTSIDE_FOOTPRINT,
                     "all_footprint_cells_receive_a_finite_distance_to_coast": True, "every_zone_has_at_least_min_cells": True},
        "source_pixels_per_cell_min_max": [int(total[window].min()), int(total[window].max())],
    }

    elev = np.where(foot, sub["mean_elev"], np.nan)
    # zones are decided on the values exactly as stored (2 decimals), so the artifact is self-consistent at the thresholds
    dist = np.round(np.where(foot, sub["distance"], np.nan), 2)
    rel = np.round(np.where(foot, sub["relief"], np.nan), 2)
    coastal = foot & (dist <= ZONE_RULES["coastal_km_max"])
    orographic = foot & (rel >= ZONE_RULES["relief_m_min"])
    zone = np.full(SHAPE, "", dtype=object)
    zone[foot] = "OTHER"
    zone[coastal & ~orographic] = "COASTAL"
    zone[orographic & ~coastal] = "OROGRAPHIC"
    zone[coastal & orographic] = "COASTAL_AND_OROGRAPHIC"
    counts = {label: int((zone == label).sum()) for label in ("COASTAL", "OROGRAPHIC", "COASTAL_AND_OROGRAPHIC", "OTHER")}
    sensitivity = {
        "coastal_cells_by_km": {str(int(k)): int((foot & (dist <= k)).sum()) for k in [ZONE_RULES["coastal_km_max"], *ALTERNATIVES["coastal_km"]]},
        "orographic_cells_by_relief_m": {str(int(k)): int((foot & (rel >= k)).sum()) for k in [ZONE_RULES["relief_m_min"], *ALTERNATIVES["relief_m"]]},
        "superseded_v2_rule_cells": int((foot & ((elev >= SUPERSEDED_ELEVATION_M) | (rel >= ZONE_RULES["relief_m_min"]))).sum()),
    }
    min_zone_cells_ok = {label: counts[label] >= MIN_CELLS for label in counts}
    qa["criteria_met"] = bool(foot_land_majority >= QA_MIN_LAND_MAJORITY_SHARE and outside <= QA_MAX_TERRAIN_LAND_OUTSIDE_FOOTPRINT
                              and dist_finite and all(min_zone_cells_ok.values()))

    def grid(a: np.ndarray, digits: int) -> list[list[float | None]]:
        return [[None if not np.isfinite(v) else round(float(v), digits) for v in row] for row in a]

    return {
        "schema_id": "phase7a-static-geography-v1",
        "protocol": {"file": "coastal_orographic_protocol_v3.json", "sha256": PROTOCOL_SHA256},
        "source": {
            "file": "GMTED2010_mean_30arcsec.nc4", "size_bytes": RAW_SIZE, "md5": RAW_MD5, "sha256": RAW_SHA256,
            "distribution": "https://zenodo.org/records/14537811 (third-party NetCDF conversion of the USGS ArcGrid, CC BY 4.0)",
            "original": "USGS/NGA Global Multi-resolution Terrain Elevation Data 2010, mean statistic, 30 arc-second (US Geological Survey)",
            "vertical_reference": "EGM96 geoid (as stated in the file); used only as relative elevation",
            "attribution": "Danielson and Gesch (2011) GMTED2010; converted to NetCDF by C. D. Holmes; distributed on Zenodo under CC BY 4.0",
        },
        "grid": {"shape": list(SHAPE), "latitude_centers": [round(LAT0 + STEP * i, 6) for i in range(SHAPE[0])],
                 "longitude_centers": [round(LON0 + STEP * i, 6) for i in range(SHAPE[1])], "row_order": "south_to_north", "column_order": "west_to_east"},
        "method": {
            "aggregation": "source pixels assigned to the 0.25 degree cell containing their centre; a land pixel is one above 0 m (the file stores ocean as 0 m, not as a fill value, so true land at exactly 0 m is counted as sea); elevation = mean over land pixels; "
                           "land_fraction = land pixels / all pixels; terrain land = land_fraction >= 0.5; land cell = terrain land OR IMD footprint cell (protocol v2 and v3)",
            "context_margin_degrees": MARGIN,
            "distance_to_coast": "great-circle km from the cell centre to the nearest ocean cell centre of the land-sea mask over the extended grid",
            "local_relief": "max minus min of the aggregated mean elevation over land cells of the 3x3 neighbourhood (ocean cells excluded)",
            "terrain_gradient": "non-land cells and land cells with undefined elevation at 0 m, one 3x3 mean, central differences; slope in m per km; unit vector pointing uphill",
            "coast_normal": "unit gradient of the 3x3-mean land mask, pointing landward (the direction of onshore flow)",
            "footprint": "time-invariant IMD valid-cell set (identical in every 2023 and 2024 case); the set of cells only, no rainfall value",
            "zone_rules": ZONE_RULES,
        },
        "qa": qa,
        "zone_cell_counts": counts,
        "zone_meets_min_cells": min_zone_cells_ok,
        "sensitivity_only_counts": sensitivity,
        "fields": {
            "footprint": [[bool(v) for v in row] for row in foot],
            "land_fraction": grid(sub["land_fraction"], 4),
            "mean_elevation_m": grid(sub["mean_elev"], 2),
            "local_relief_m": grid(sub["relief"], 2),
            "distance_to_coast_km": grid(np.where(sub["land_mask"], sub["distance"], np.nan), 2),
            "slope_m_per_km": grid(sub["slope"], 4),
            "terrain_uphill_east": grid(sub["terrain_nx"], 4),
            "terrain_uphill_north": grid(sub["terrain_ny"], 4),
            "coast_landward_east": grid(sub["coast_nx"], 4),
            "coast_landward_north": grid(sub["coast_ny"], 4),
            "zone": [[None if v == "" else v for v in row] for row in zone.tolist()],
        },
    }


def encode(artifact: dict) -> bytes:
    return (json.dumps(artifact, indent=1, sort_keys=True, ensure_ascii=False) + "\n").encode("utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    if sha256_file(PROTOCOL) != PROTOCOL_SHA256:
        print("protocol hash mismatch: refusing to build")
        return 2
    if RAW.stat().st_size != RAW_SIZE or sha256_file(RAW) != RAW_SHA256:
        print("source file size/hash mismatch: refusing to build")
        return 2
    artifact = build()
    if not artifact["qa"]["criteria_met"]:
        print("QA criteria NOT met; refusing to write an artifact (protocol stop condition). Details:")
        print(json.dumps(artifact["qa"], indent=1))
        return 3
    data = encode(artifact)
    if args.check:
        same = OUT.read_bytes() == data
        print("artifact reproduces byte-for-byte" if same else "ARTIFACT DOES NOT REPRODUCE")
        return 0 if same else 1
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    OUT.write_bytes(data)
    (OUT_DIR / "static_geography_v1.sha256").write_bytes(f"{sha256_bytes(data)}  {OUT.name}\n".encode("utf-8"))
    print(f"wrote {OUT.relative_to(ROOT)} sha256 {sha256_bytes(data)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
