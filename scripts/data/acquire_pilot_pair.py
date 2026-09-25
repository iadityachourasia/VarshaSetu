"""Acquire and validate one GEFS/IMD rainfall pair; never trains a model."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
import threading
import time
from dataclasses import asdict
from datetime import date, datetime, time as datetime_time, timedelta, timezone
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import psutil
import scipy
import eccodes
from scipy.io import netcdf_file

from backend.app.data.accumulation import reconstruct_accumulation_window
from backend.app.data.pilot_models import PilotDerivedManifest, PilotSourceManifest
from backend.app.data.regridding import (
    area_weighted_integral,
    build_first_order_conservative_weights,
    grid_cell_areas,
)
from backend.app.data_sources.imd_rainfall import inspect_imd_netcdf, load_imd_day
from backend.app.data_sources.noaa_gefs import (
    crop_message,
    decode_message,
    fetch_url,
    gefs_object_url,
    parse_index,
    sha256_bytes,
)


UTC = timezone.utc
TARGET_BOUNDS = {"south": 10.0, "north": 22.0, "west": 68.0, "east": 80.0}
PILOT_DATE = date(2019, 7, 15)
CONSERVATION_RELATIVE_TOLERANCE = 1e-10


def sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def json_hash(path: Path) -> str:
    return sha256_file(path)


class PeakRssMonitor:
    def __init__(self) -> None:
        self.process = psutil.Process()
        self.peak = self.process.memory_info().rss
        self.stop_event = threading.Event()
        self.thread = threading.Thread(target=self._sample, daemon=True)

    def _sample(self) -> None:
        while not self.stop_event.wait(0.02):
            self.peak = max(self.peak, self.process.memory_info().rss)

    def __enter__(self):
        self.thread.start()
        return self

    def __exit__(self, exc_type, exc, traceback) -> None:
        self.stop_event.set()
        self.thread.join()
        self.peak = max(self.peak, self.process.memory_info().rss)


def copy_immutable(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        if sha256_file(source) != sha256_file(destination):
            raise ValueError(f"immutable destination differs: {destination}")
        return
    shutil.copy2(source, destination)


def write_immutable_bytes(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if sha256_file(path) != hashlib.sha256(payload).hexdigest():
            raise ValueError(f"immutable raw file differs: {path}")
        return
    path.write_bytes(payload)


def write_pair_netcdf(
    path: Path,
    *,
    latitude: np.ndarray,
    longitude: np.ndarray,
    forecast: np.ndarray,
    observation: np.ndarray,
    valid_mask: np.ndarray,
    initialization: datetime,
    pilot_date: date,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fill_value = np.float32(-999.0)
    observation_stored = np.where(valid_mask, observation, fill_value).astype(np.float32)
    with netcdf_file(path, "w") as dataset:
        dataset.createDimension("y", latitude.size)
        dataset.createDimension("x", longitude.size)
        lat_var = dataset.createVariable("latitude", "d", ("y",))
        lon_var = dataset.createVariable("longitude", "d", ("x",))
        forecast_var = dataset.createVariable("raw_nwp_rain_24h", "f", ("y", "x"))
        observation_var = dataset.createVariable("observed_rain_24h", "f", ("y", "x"))
        mask_var = dataset.createVariable("valid_mask", "b", ("y", "x"))
        lat_var[:] = latitude
        lon_var[:] = longitude
        forecast_var[:] = forecast.astype(np.float32)
        observation_var[:] = observation_stored
        mask_var[:] = valid_mask.astype(np.int8)
        lat_var.units = "degrees_north"
        lon_var.units = "degrees_east"
        forecast_var.units = "mm"
        forecast_var.long_name = "GEFSv12 control-member 24-hour accumulated rainfall"
        observation_var.units = "mm"
        observation_var.long_name = "IMD 0.25 degree daily gridded rainfall"
        observation_var._FillValue = fill_value
        observation_var.missing_value = fill_value
        mask_var.flag_values = "0,1"
        mask_var.flag_meanings = "invalid valid"
        dataset.Conventions = "CF-1.8"
        dataset.title = "VarshaSetu Phase 1B one-window pairing pilot"
        dataset.training_eligible = "false"
        dataset.forecast_source = "NOAA GEFSv12 Reforecast"
        dataset.forecast_model = "GEFS v12 reforecast"
        dataset.forecast_init_time = initialization.isoformat()
        dataset.forecast_member = "c00"
        dataset.forecast_window_start = (initialization + timedelta(hours=3)).isoformat()
        dataset.forecast_window_end = (initialization + timedelta(hours=27)).isoformat()
        dataset.lead_window_identity = "day1_24h:+3_to_+27"
        dataset.observation_source = "India Meteorological Department"
        dataset.observation_product = "0.25 degree Daily Gridded Rainfall"
        dataset.observation_date = pilot_date.isoformat()
        dataset.accumulation_hours = np.int32(24)
        dataset.target_grid = "IMD native 0.25 degree target-domain grid"
        dataset.regridding_method = "first-order conservative spherical cell-overlap"
        dataset.source_manifest_ids = "noaa-gefsv12-2019071400-c00-apcp;imd-rf25-2019"
        dataset.derived_manifest_id = "phase1b-pair-2019-07-15-v1"


def create_qc_image(
    path: Path,
    latitude: np.ndarray,
    longitude: np.ndarray,
    source: np.ndarray,
    regridded: np.ndarray,
    observation: np.ndarray,
    valid_mask: np.ndarray,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    observed_masked = np.ma.masked_where(~valid_mask, observation)
    vmax = float(max(np.nanmax(source), np.nanmax(regridded), observed_masked.max()))
    figure, axes = plt.subplots(1, 3, figsize=(15, 4.8), constrained_layout=True)
    titles = [
        "GEFS accumulated rainfall\n(source grid subset)",
        "GEFS rainfall\n(on IMD grid)",
        "IMD observed rainfall\n(mask retained)",
    ]
    fields = [source, regridded, observed_masked]
    image = None
    for axis, title, field in zip(axes, titles, fields, strict=True):
        image = axis.pcolormesh(longitude, latitude, field, shading="nearest", vmin=0, vmax=vmax)
        axis.set_title(title)
        axis.set_xlabel("Longitude (°E)")
        axis.set_ylabel("Latitude (°N)")
        axis.set_xlim(longitude[0], longitude[-1])
        axis.set_ylim(latitude[0], latitude[-1])
    colorbar = figure.colorbar(image, ax=axes, shrink=0.88)
    colorbar.set_label("24-hour rainfall (mm)")
    figure.suptitle(
        "Engineering QC only — 03:00 UTC 2019-07-14 to 03:00 UTC 2019-07-15\n"
        "No forecast-skill or improvement claim"
    )
    figure.savefig(path, dpi=150)
    plt.close(figure)


def stats(values: np.ndarray, mask: np.ndarray | None = None) -> dict:
    selected = np.asarray(values, dtype=float) if mask is None else np.asarray(values, dtype=float)[mask]
    return {
        "min_mm": float(np.min(selected)),
        "max_mm": float(np.max(selected)),
        "mean_mm": float(np.mean(selected)),
        "negative_count": int((selected < 0).sum()),
        "nonfinite_count": int((~np.isfinite(selected)).sum()),
    }


def run(imd_input: Path, output_root: Path, pilot_date: date) -> dict:
    if pilot_date != PILOT_DATE:
        raise ValueError("Phase 1B uses the deterministic fixed date 2019-07-15")
    started = time.perf_counter()
    initialization = datetime.combine(pilot_date - timedelta(days=1), datetime_time(), tzinfo=UTC)
    stamp = initialization.strftime("%Y%m%d%H")
    raw_imd = output_root / "raw/observations/imd/2019" / imd_input.name
    raw_noaa = output_root / "raw/forecasts/gefsv12" / stamp / "c00/apcp_sfc"
    processed = output_root / "processed/pilot/2019-07-15"
    manifest_dir = output_root / "manifests/phase1b/2019-07-15"
    docs_artifacts = REPOSITORY_ROOT / "docs/artifacts"

    with PeakRssMonitor() as memory:
        copy_immutable(imd_input, raw_imd)
        imd_sha = sha256_file(raw_imd)
        imd_size = raw_imd.stat().st_size
        imd_metadata = inspect_imd_netcdf(raw_imd)

        object_url = gefs_object_url(initialization)
        raw_noaa.mkdir(parents=True, exist_ok=True)
        index_path = raw_noaa / f"apcp_sfc_{stamp}_c00.grib2.idx"
        if index_path.exists():
            index_payload = index_path.read_bytes()
            index_response = {"source": "immutable_local_cache"}
        else:
            index_payload, index_response = fetch_url(object_url + ".idx")
        index_entries = parse_index(index_payload.decode("utf-8"))
        needed = [entry for entry in index_entries if entry.message_number <= 9]
        if [(entry.start_step, entry.end_step) for entry in needed] != [
            (0, 3), (0, 6), (6, 9), (6, 12), (12, 15),
            (12, 18), (18, 21), (18, 24), (24, 27),
        ]:
            raise ValueError("NOAA index does not contain the required deterministic window structure")
        selected_range = (needed[0].byte_start, needed[-1].byte_end)
        expected_message_paths = [
            raw_noaa / f"message_{entry.message_number:03d}_{entry.start_step}-{entry.end_step}.grib2"
            for entry in needed
        ]
        if all(path.exists() for path in expected_message_paths):
            selected_payload = b"".join(path.read_bytes() for path in expected_message_paths)
            range_response = {"source": "immutable_local_cache"}
            successful_run_network_bytes = 0
        else:
            selected_payload, range_response = fetch_url(object_url, selected_range)
            successful_run_network_bytes = len(index_payload) + len(selected_payload)
        noaa_transferred = len(index_payload) + len(selected_payload)
        write_immutable_bytes(index_path, index_payload)

        decoded_messages = []
        message_records = []
        for entry in needed:
            relative_start = entry.byte_start - selected_range[0]
            relative_end = entry.byte_end - selected_range[0] + 1
            payload = selected_payload[relative_start:relative_end]
            message_path = raw_noaa / (
                f"message_{entry.message_number:03d}_{entry.start_step}-{entry.end_step}.grib2"
            )
            write_immutable_bytes(message_path, payload)
            source_id = f"GEFS:{stamp}:c00:{entry.start_step}-{entry.end_step}"
            decoded = crop_message(decode_message(payload, source_id), **TARGET_BOUNDS)
            if (
                decoded.accumulation.start_hour != entry.start_step
                or decoded.accumulation.end_hour != entry.end_step
            ):
                raise ValueError("GRIB step metadata disagrees with NOAA index")
            decoded_messages.append(decoded)
            message_records.append(
                {
                    "message_number": entry.message_number,
                    "object_byte_range": [entry.byte_start, entry.byte_end],
                    "local_filename": message_path.name,
                    "byte_size": len(payload),
                    "sha256": sha256_bytes(payload),
                    "index_description": entry.description,
                    "metadata": decoded.metadata,
                    "target_subset_stats": stats(decoded.accumulation.values_mm),
                }
            )

        first = decoded_messages[0]
        for decoded in decoded_messages[1:]:
            if not np.array_equal(decoded.latitude, first.latitude) or not np.array_equal(
                decoded.longitude, first.longitude
            ):
                raise ValueError("GEFS message grids differ within the accumulation window")
        packing_quantum_mm = max(
            10.0 ** (-decoded.metadata["decimal_scale_factor"])
            for decoded in decoded_messages
        )
        accumulation = reconstruct_accumulation_window(
            [decoded.accumulation for decoded in decoded_messages],
            window_start_hour=3,
            window_end_hour=27,
            negative_tolerance_mm=packing_quantum_mm + 1e-12,
        )

        imd = load_imd_day(raw_imd, pilot_date, **TARGET_BOUNDS)
        if not np.array_equal(first.latitude, imd.latitude) or not np.array_equal(
            first.longitude, imd.longitude
        ):
            raise ValueError("GEFS and IMD pilot cell centers do not align exactly")

        weights = build_first_order_conservative_weights(
            first.latitude, first.longitude, imd.latitude, imd.longitude
        )
        weight_path = processed / "gefsv12_to_imd025_conservative_weights.npy"
        weight_hash, weight_size = weights.save(weight_path)
        regridded = weights.apply(accumulation.rainfall_mm)
        source_integral = area_weighted_integral(
            accumulation.rainfall_mm, first.latitude, first.longitude, imd.valid_mask
        )
        target_integral = area_weighted_integral(
            regridded, imd.latitude, imd.longitude, imd.valid_mask
        )
        relative_difference = (
            abs(target_integral - source_integral) / abs(source_integral)
            if source_integral != 0
            else 0.0 if target_integral == 0 else float("inf")
        )
        if relative_difference > CONSERVATION_RELATIVE_TOLERANCE:
            raise ValueError("conservative regridding failed the area-integral tolerance")

        retrieved = datetime.fromtimestamp(index_path.stat().st_mtime, tz=UTC)
        noaa_manifest_data = PilotSourceManifest(
            manifest_id="noaa-gefsv12-2019071400-c00-apcp",
            provider="NOAA/NCEP",
            official_url=object_url,
            retrieval_timestamp_utc=retrieved,
            filename_or_object_key=object_url.rsplit("/", 1)[-1],
            byte_size=len(selected_payload),
            sha256=sha256_bytes(selected_payload),
            source_type="forecast",
            license_or_terms_reference="https://registry.opendata.aws/noaa-gefs-reforecast/",
            variable="apcp_sfc archive object / tp GRIB short name",
            units="kg m**-2 normalized 1:1 to mm",
            grid=first.metadata["grid"],
            time_coverage={
                "initialization_time_utc": initialization.isoformat(),
                "selected_byte_range": list(selected_range),
                "accumulation_source_steps": [[e.start_step, e.end_step] for e in needed],
                "target_window_leads": [3, 27],
            },
            index={
                "url": object_url + ".idx",
                "filename": index_path.name,
                "byte_size": len(index_payload),
                "sha256": sha256_bytes(index_payload),
                "acquisition": "official HTTPS; immutable local cache on reruns",
            },
            selected_range_acquisition={
                "method": "official HTTPS Range request; immutable local cache on reruns",
                "range": list(selected_range),
            },
            member="c00",
            messages=message_records,
        ).model_dump(mode="json")
        noaa_manifest_path = manifest_dir / "noaa_gefsv12_2019071400_c00_apcp.json"
        write_json(noaa_manifest_path, noaa_manifest_data)

        imd_retrieved = datetime.fromtimestamp(imd_input.stat().st_mtime, tz=UTC)
        imd_manifest_data = PilotSourceManifest(
            manifest_id="imd-rf25-2019",
            provider="India Meteorological Department, Climate Research and Services, Pune",
            official_url="https://imdpune.gov.in/cmpg/Griddata/Rainfall_25_NetCDF.html",
            retrieval_timestamp_utc=imd_retrieved,
            filename_or_object_key=raw_imd.name,
            byte_size=imd_size,
            sha256=imd_sha,
            source_type="observation",
            license_or_terms_reference="Official page citation and disclaimer; Pai et al. (2014)",
            variable="RAINFALL",
            units="mm",
            grid={
                "shape": [129, 135],
                "latitude_range": [6.5, 38.5],
                "longitude_range": [66.5, 100.0],
                "resolution_degrees": 0.25,
                "coordinate_order": "latitude ascending, longitude ascending",
            },
            time_coverage={
                "year": 2019,
                "records": 365,
                "time_units": imd.metadata["time_units"],
                "calendar": imd.metadata["calendar"],
                "pilot_record_index": imd.metadata["record_index"],
                "pilot_time_value": imd.metadata["time_value"],
                "netcdf_time_label": imd.metadata["netcdf_time_label"],
                "accumulation_window_basis": (
                    "official external IMD 08:30 IST previous day to 08:30 IST current day; "
                    "NetCDF does not encode start/end bounds"
                ),
            },
            access_method="official form POST RF25=2019 to RF25.php",
            netcdf_metadata=imd_metadata,
            pilot_field_metadata=imd.metadata,
            citation=(
                "Pai D.S. et al. (2014), Development of a new high spatial resolution "
                "0.25 degree daily gridded rainfall data set over India, MAUSAM 65(1), 1-18"
            ),
            disclaimer=(
                "IMD states it cannot guarantee correctness in all circumstances and accepts "
                "no liability for errors, omissions, loss, or damage arising from use."
            ),
        ).model_dump(mode="json")
        imd_manifest_path = manifest_dir / "imd_rf25_2019.json"
        write_json(imd_manifest_path, imd_manifest_data)

        pair_path = processed / "gefsv12_imd_pair_2019-07-15.nc"
        write_pair_netcdf(
            pair_path,
            latitude=imd.latitude,
            longitude=imd.longitude,
            forecast=regridded,
            observation=imd.rainfall_mm,
            valid_mask=imd.valid_mask,
            initialization=initialization,
            pilot_date=pilot_date,
        )
        pair_hash = sha256_file(pair_path)
        pair_size = pair_path.stat().st_size
        image_path = docs_artifacts / "phase1b_qc_2019-07-15.png"
        create_qc_image(
            image_path,
            imd.latitude,
            imd.longitude,
            accumulation.rainfall_mm,
            regridded,
            imd.rainfall_mm,
            imd.valid_mask,
        )
        image_manifest_path = str(image_path.relative_to(REPOSITORY_ROOT)).replace("\\", "/")

        code_paths = [
            REPOSITORY_ROOT / "backend/app/data/accumulation.py",
            REPOSITORY_ROOT / "backend/app/data/regridding.py",
            REPOSITORY_ROOT / "backend/app/data_sources/noaa_gefs.py",
            REPOSITORY_ROOT / "backend/app/data_sources/imd_rainfall.py",
            REPOSITORY_ROOT / "scripts/data/acquire_pilot_pair.py",
        ]
        source_manifest_hashes = {
            "noaa_gefs": json_hash(noaa_manifest_path),
            "imd_rainfall": json_hash(imd_manifest_path),
        }
        code_hashes = {
            str(path.relative_to(REPOSITORY_ROOT)).replace("\\", "/"): sha256_file(path)
            for path in code_paths
        }
        target_areas = grid_cell_areas(imd.latitude, imd.longitude)
        full_target_area_m2 = float(np.sum(target_areas))
        comparable_valid_area_m2 = float(np.sum(target_areas[imd.valid_mask]))
        qc_core = {
            "status": "PASS",
            "timing": {
                "forecast_initialization_utc": initialization.isoformat(),
                "forecast_window_start_utc": (initialization + timedelta(hours=3)).isoformat(),
                "forecast_window_end_utc": (initialization + timedelta(hours=27)).isoformat(),
                "observation_target_date": pilot_date.isoformat(),
                "observation_window_start_utc": (initialization + timedelta(hours=3)).isoformat(),
                "observation_window_end_utc": (initialization + timedelta(hours=27)).isoformat(),
                "interval_equality": True,
                "observation_timing_basis": "official IMD 08:30 IST daily convention",
                "netcdf_time_bounds_present": False,
            },
            "precipitation": {
                "source_messages": message_records,
                "source_message_values_combined": stats(
                    np.stack([item.accumulation.values_mm for item in decoded_messages])
                ),
                "accumulation_segments": [asdict(segment) for segment in accumulation.segments],
                "tiny_negative_clamped_count": accumulation.tiny_negative_count,
                "minimum_tolerated_negative_mm": accumulation.minimum_tolerated_negative_mm,
                "negative_tolerance_mm": accumulation.negative_tolerance_mm,
                "negative_tolerance_basis": (
                    "maximum decoded GRIB packing quantum from decimalScaleFactor; "
                    "values more negative than this fail"
                ),
                "accumulated_source_subset": stats(accumulation.rainfall_mm),
                "regridded_target": stats(regridded),
                "imd_valid_cells": stats(imd.rainfall_mm, imd.valid_mask),
                "imd_missing_count": int((~imd.valid_mask).sum()),
            },
            "spatial": {
                "source_grid_shape": list(accumulation.rainfall_mm.shape),
                "target_grid_shape": list(regridded.shape),
                "latitude_range": [float(imd.latitude[0]), float(imd.latitude[-1])],
                "longitude_range": [float(imd.longitude[0]), float(imd.longitude[-1])],
                "valid_target_cells": int(imd.valid_mask.sum()),
                "masked_target_cells": int((~imd.valid_mask).sum()),
                "full_target_domain_area_m2": full_target_area_m2,
                "comparable_valid_area_m2": comparable_valid_area_m2,
                "source_area_weighted_integral_mm_m2": source_integral,
                "target_area_weighted_integral_mm_m2": target_integral,
                "conservation_relative_difference": relative_difference,
                "conservation_tolerance": CONSERVATION_RELATIVE_TOLERANCE,
                "conservation_pass": True,
            },
            "provenance": {
                "source_manifest_hashes": source_manifest_hashes,
                "source_urls_present": True,
                "terms_recorded": True,
                "all_source_hashes_present": True,
            },
        }
        derived = PilotDerivedManifest(
            manifest_id="phase1b-pair-2019-07-15-v1",
            derived_artifact=str(pair_path).replace("\\", "/"),
            derived_artifact_sha256=pair_hash,
            source_manifest_hashes=source_manifest_hashes,
            processing_code_hashes=code_hashes,
            window_definition={
                "semantics": "half-open",
                "start_utc": (initialization + timedelta(hours=3)).isoformat(),
                "end_utc": (initialization + timedelta(hours=27)).isoformat(),
                "duration_hours": 24,
                "lead_start_hours": 3,
                "lead_end_hours": 27,
            },
            regridding_method="first-order conservative spherical rectilinear cell-overlap",
            weight_hash=weight_hash,
            target_domain=TARGET_BOUNDS,
            target_grid={
                "source": "IMD native 0.25 degree grid",
                "shape": list(regridded.shape),
                "valid_mask_variable": "valid_mask",
            },
            qc_results={
                "status": "PASS",
                "conservation_relative_difference": relative_difference,
                "conservation_tolerance": CONSERVATION_RELATIVE_TOLERANCE,
                "valid_target_cells": int(imd.valid_mask.sum()),
            },
            training_eligible=False,
            code_version="unavailable:not-a-git-checkout",
            regridding_implementation={
                "library": "repository-local NumPy spherical cell-overlap implementation",
                "numpy_version": np.__version__,
                "scipy_version": scipy.__version__,
                "eccodes_version": eccodes.__version__,
            },
            weight_artifact=str(weight_path).replace("\\", "/"),
            weight_byte_size=weight_size,
            visual_qc_artifact=image_manifest_path,
        ).model_dump(mode="json")
        derived_manifest_path = manifest_dir / "derived_pair_2019-07-15.json"
        write_json(derived_manifest_path, derived)

    runtime_seconds = time.perf_counter() - started
    raw_pilot_bytes = imd_size + noaa_transferred
    processed_bytes = pair_size + weight_size + image_path.stat().st_size
    qc_report = qc_core | {
        "pilot_date": pilot_date.isoformat(),
        "training_eligible": False,
        "artifacts": {
            "pair": str(pair_path).replace("\\", "/"),
            "pair_sha256": pair_hash,
            "pair_bytes": pair_size,
            "weights": str(weight_path).replace("\\", "/"),
            "weight_sha256": weight_hash,
            "weight_bytes": weight_size,
            "visual_qc": image_manifest_path,
            "visual_qc_sha256": sha256_file(image_path),
            "visual_qc_bytes": image_path.stat().st_size,
            "derived_manifest": str(derived_manifest_path).replace("\\", "/"),
            "derived_manifest_sha256": json_hash(derived_manifest_path),
        },
        "measurements": {
            "noaa_bytes_transferred": noaa_transferred,
            "successful_run_network_bytes": successful_run_network_bytes,
            "imd_bytes_transferred": imd_size,
            "raw_pilot_bytes": raw_pilot_bytes,
            "processed_bytes": processed_bytes,
            "peak_rss_bytes": memory.peak,
            "runtime_seconds": runtime_seconds,
        },
    }
    qc_path = manifest_dir / "qc_report_2019-07-15.json"
    write_json(qc_path, qc_report)
    print(json.dumps(qc_report, indent=2, sort_keys=True))
    return qc_report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--imd-file", type=Path, required=True)
    parser.add_argument("--pilot-date", type=date.fromisoformat, default=PILOT_DATE)
    parser.add_argument("--output-root", type=Path, default=Path("data"))
    args = parser.parse_args()
    run(args.imd_file.resolve(), args.output_root, args.pilot_date)


if __name__ == "__main__":
    main()
