"""Execute one authoritative calendar-month acquisition/QC run; never train."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict
from datetime import date, datetime, timezone
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

import eccodes
import numpy as np
import psutil
import scipy
import zarr
from scipy.io import netcdf_file

from backend.app.data.accumulation import (
    reconstruct_accumulation_window,
    reconstruct_minimal_accumulation_window,
)
from backend.app.data.cache import (
    CacheIntegrityError,
    CacheResult,
    fetch_cached,
    receipt_path,
    sha256_bytes,
    sha256_file,
    store_verified_bytes,
)
from backend.app.data.monthly_models import MonthlyCollectionManifest
from backend.app.data.monthly_qc import (
    ATMOSPHERIC_LEADS,
    CONTEXT_BOUNDS,
    ENSEMBLE_MEMBERS,
    PRODUCT_WINDOWS,
    TARGET_BOUNDS,
    bilinear_to_context,
    context_coordinates,
    monthly_initializations,
    numeric_stats,
    observation_event_stats,
    product_valid_date,
    product_window,
    projected_storage,
    summarize_initialization_status,
)
from backend.app.data.regridding import (
    area_weighted_integral,
    build_first_order_conservative_weights,
)
from backend.app.data_sources.imd_rainfall import load_imd_day
from backend.app.data_sources.noaa_gefs_monthly import (
    ATMOSPHERIC_SPECS,
    crop_grid,
    decode_atmospheric_message,
    decode_precipitation_message,
    object_url,
    parse_generic_index,
    select_atmospheric_entry,
    select_precipitation_entries,
)


UTC = timezone.utc
CONSERVATION_TOLERANCE = 1e-10
FILL_VALUE = np.float32(-999.0)


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


def write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(value, indent=2, sort_keys=True) + "\n"
    path.write_text(payload, encoding="utf-8")


def write_csv(path: Path, rows: list[dict], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def relative(path: Path) -> str:
    return str(path.resolve().relative_to(REPOSITORY_ROOT)).replace("\\", "/")


def code_hashes() -> dict[str, str]:
    paths = [
        "backend/app/data/accumulation.py",
        "backend/app/data/cache.py",
        "backend/app/data/monthly_models.py",
        "backend/app/data/monthly_qc.py",
        "backend/app/data/regridding.py",
        "backend/app/data_sources/imd_rainfall.py",
        "backend/app/data_sources/noaa_gefs_monthly.py",
        "scripts/data/acquire_monthly_pilot.py",
    ]
    return {name: sha256_file(REPOSITORY_ROOT / name) for name in paths}


def field_stats(values: np.ndarray) -> dict:
    values = np.asarray(values, dtype=float)
    return {
        "min": float(np.min(values)),
        "max": float(np.max(values)),
        "mean": float(np.mean(values)),
        "nonfinite_count": int((~np.isfinite(values)).sum()),
        "negative_count": int((values < 0).sum()),
    }


def ensure_cache_available(path: Path, cache_only: bool) -> None:
    if cache_only and not (path.exists() and receipt_path(path).exists()):
        raise FileNotFoundError(f"cache-only run is missing {path}")


def acquire(
    url: str,
    path: Path,
    *,
    byte_range: tuple[int, int] | None = None,
    cache_only: bool,
) -> CacheResult:
    ensure_cache_available(path, cache_only)
    return fetch_cached(
        url,
        path,
        byte_range=byte_range,
        retries=5,
        timeout_seconds=300.0,
        backoff_seconds=2.0,
    )


def parallel_fetch(
    tasks: list[tuple[str, Path, tuple[int, int] | None]],
    cache_only: bool,
    *,
    max_workers: int = 3,
):
    results: dict[str, CacheResult] = {}
    failures: dict[str, str] = {}
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_map = {
            executor.submit(
                acquire, url, path, byte_range=byte_range, cache_only=cache_only
            ): key
            for key, url, path, byte_range in tasks
        }
        for future in as_completed(future_map):
            key = future_map[future]
            try:
                results[key] = future.result()
            except Exception as exc:
                failures[key] = f"{type(exc).__name__}: {exc}"
    return results, failures


def reuse_phase1b_index_if_available(
    initialization: datetime,
    member: str,
    destination: Path,
    url: str,
) -> CacheResult | None:
    if initialization.strftime("%Y%m%d%H") != "2019071400" or member != "c00":
        return None
    manifest_path = (
        REPOSITORY_ROOT
        / "data/manifests/phase1b/2019-07-15/noaa_gefsv12_2019071400_c00_apcp.json"
    )
    source_path = (
        REPOSITORY_ROOT
        / "data/raw/forecasts/gefsv12/2019071400/c00/apcp_sfc/"
        "apcp_sfc_2019071400_c00.grib2.idx"
    )
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if sha256_file(source_path) != manifest["index"]["sha256"]:
        raise CacheIntegrityError("Phase 1B index no longer matches its manifest")
    stored = store_verified_bytes(
        destination, url=url + ".idx", byte_range=None, payload=source_path.read_bytes()
    )
    return CacheResult(
        stored.path, stored.sha256, stored.byte_size, True, 0, 0, 0.0
    )


def acquire_precipitation_chunk(
    initialization: datetime,
    member: str,
    entries,
    destination: Path,
    url: str,
    *,
    cache_only: bool,
) -> tuple[CacheResult, list[str]]:
    overall_range = (entries[0].byte_start, entries[-1].byte_end)
    notes: list[str] = []
    phase1b_prefix = (
        initialization.strftime("%Y%m%d%H") == "2019071400" and member == "c00"
    )
    if phase1b_prefix:
        notes.append("reused checksummed Phase 1B messages 0-3 through 24-27")
    if destination.exists() or receipt_path(destination).exists():
        return fetch_cached(url, destination, byte_range=overall_range), notes

    if phase1b_prefix:
        manifest_path = (
            REPOSITORY_ROOT
            / "data/manifests/phase1b/2019-07-15/noaa_gefsv12_2019071400_c00_apcp.json"
        )
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        old_root = (
            REPOSITORY_ROOT
            / "data/raw/forecasts/gefsv12/2019071400/c00/apcp_sfc"
        )
        prefix_parts: list[bytes] = []
        for record in manifest["messages"]:
            source_path = old_root / record["local_filename"]
            if sha256_file(source_path) != record["sha256"]:
                raise CacheIntegrityError("Phase 1B precipitation cache changed")
            prefix_parts.append(source_path.read_bytes())
        suffix_range = (entries[9].byte_start, entries[-1].byte_end)
        suffix_path = destination.with_name("selected_027_075.grib2")
        suffix = acquire(
            url, suffix_path, byte_range=suffix_range, cache_only=cache_only
        )
        payload = b"".join(prefix_parts) + suffix.path.read_bytes()
        if len(payload) != overall_range[1] - overall_range[0] + 1:
            raise CacheIntegrityError("Phase 1B prefix and Phase 1C suffix do not join")
        stored = store_verified_bytes(
            destination, url=url, byte_range=overall_range, payload=payload
        )
        return CacheResult(
            stored.path,
            stored.sha256,
            stored.byte_size,
            False,
            suffix.network_bytes,
            suffix.attempts,
            suffix.elapsed_seconds,
        ), notes

    ensure_cache_available(destination, cache_only)
    return acquire(
        url, destination, byte_range=overall_range, cache_only=cache_only
    ), notes


def message_payload(chunk: bytes, chunk_start: int, entry) -> bytes:
    start = entry.byte_start - chunk_start
    end = entry.byte_end - chunk_start + 1
    payload = chunk[start:end]
    if len(payload) != entry.byte_size:
        raise ValueError("message slice byte count mismatch")
    return payload


def write_daily_pair(
    path: Path,
    *,
    initialization: datetime,
    latitude: np.ndarray,
    longitude: np.ndarray,
    forecasts: np.ndarray,
    observations: np.ndarray,
    masks: np.ndarray,
    availability: np.ndarray,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with netcdf_file(path, "w") as dataset:
        dataset.createDimension("product", len(PRODUCT_WINDOWS))
        dataset.createDimension("member", len(ENSEMBLE_MEMBERS))
        dataset.createDimension("y", latitude.size)
        dataset.createDimension("x", longitude.size)
        product_var = dataset.createVariable("product", "i", ("product",))
        member_var = dataset.createVariable("member", "i", ("member",))
        lat_var = dataset.createVariable("latitude", "d", ("y",))
        lon_var = dataset.createVariable("longitude", "d", ("x",))
        forecast_var = dataset.createVariable(
            "raw_nwp_rain_24h", "f", ("product", "member", "y", "x")
        )
        observation_var = dataset.createVariable(
            "observed_rain_24h", "f", ("product", "y", "x")
        )
        mask_var = dataset.createVariable("valid_mask", "b", ("product", "y", "x"))
        available_var = dataset.createVariable(
            "forecast_available", "b", ("product", "member")
        )
        product_var[:] = np.arange(len(PRODUCT_WINDOWS), dtype=np.int32)
        member_var[:] = np.arange(len(ENSEMBLE_MEMBERS), dtype=np.int32)
        lat_var[:] = latitude
        lon_var[:] = longitude
        forecast_var[:] = forecasts.astype(np.float32)
        observation_var[:] = observations.astype(np.float32)
        mask_var[:] = masks.astype(np.int8)
        available_var[:] = availability.astype(np.int8)
        lat_var.units = "degrees_north"
        lon_var.units = "degrees_east"
        forecast_var.units = "mm"
        forecast_var.missing_value = FILL_VALUE
        observation_var.units = "mm"
        observation_var.missing_value = FILL_VALUE
        dataset.Conventions = "CF-1.8"
        dataset.title = "VarshaSetu Phase 1C daily rainfall pairing artifact"
        dataset.training_eligible = "false"
        dataset.initialization_time_utc = initialization.isoformat()
        dataset.product_names = ",".join(PRODUCT_WINDOWS)
        dataset.member_names = ",".join(ENSEMBLE_MEMBERS)
        dataset.product_windows = "day1:+3..+27,day2:+27..+51,day3:+51..+75"
        dataset.observation_timing = "03 UTC previous day to 03 UTC valid day"
        dataset.regridding_method = "first-order conservative spherical cell-overlap"


def write_daily_atmosphere(
    path: Path,
    *,
    initialization: datetime,
    arrays: dict[str, np.ndarray],
    units: dict[str, str],
    availability: np.ndarray,
) -> None:
    latitude, longitude = context_coordinates()
    path.parent.mkdir(parents=True, exist_ok=True)
    with netcdf_file(path, "w") as dataset:
        dataset.createDimension("lead", len(ATMOSPHERIC_LEADS))
        dataset.createDimension("y", latitude.size)
        dataset.createDimension("x", longitude.size)
        lead_var = dataset.createVariable("lead_hours", "i", ("lead",))
        lat_var = dataset.createVariable("latitude", "d", ("y",))
        lon_var = dataset.createVariable("longitude", "d", ("x",))
        lead_var[:] = np.asarray(ATMOSPHERIC_LEADS, dtype=np.int32)
        lat_var[:] = latitude
        lon_var[:] = longitude
        lat_var.units = "degrees_north"
        lon_var.units = "degrees_east"
        for field_index, key in enumerate(ATMOSPHERIC_SPECS):
            variable = dataset.createVariable(key, "f", ("lead", "y", "x"))
            variable[:] = arrays[key].astype(np.float32)
            variable.units = units.get(key, "unknown")
            variable.missing_value = FILL_VALUE
            variable.availability_by_lead = ",".join(
                str(int(value)) for value in availability[field_index]
            )
            variable.archive_object_family = ATMOSPHERIC_SPECS[key].object_family
        dataset.Conventions = "CF-1.8"
        dataset.title = "VarshaSetu Phase 1C control-member atmospheric context"
        dataset.training_eligible = "false"
        dataset.initialization_time_utc = initialization.isoformat()
        dataset.member = "c00"
        dataset.regridding_method = "bilinear to 0.5 degree context grid"


def acquire_initialization(
    initialization: datetime,
    *,
    imd_path: Path,
    raw_root: Path,
    processed_root: Path,
    manifest_root: Path,
    weights,
    cache_only: bool,
    phase_id: str,
    network_workers: int = 3,
    reconstruction_method: str = "legacy_v1",
    imd_source_manifest: str = "data/manifests/phase1b/2019-07-15/imd_rf25_2019.json",
    access_date: str = "2026-09-19",
) -> dict:
    initialization_started = time.perf_counter()
    timings = {
        "precipitation_decode_and_crop": 0.0,
        "rainfall_reconstruct_regrid_qc": 0.0,
        "atmosphere_decode_interpolate_qc": 0.0,
        "artifact_write": 0.0,
    }
    stamp = initialization.strftime("%Y%m%d%H")
    product_names = list(PRODUCT_WINDOWS)
    member_names = list(ENSEMBLE_MEMBERS)
    imd_fields = {
        product: load_imd_day(
            imd_path, product_valid_date(initialization, product), **TARGET_BOUNDS
        )
        for product in product_names
    }
    first_observation = imd_fields[product_names[0]]
    forecasts = np.full(
        (len(product_names), len(member_names), 49, 49), FILL_VALUE, dtype=np.float32
    )
    observations = np.full((len(product_names), 49, 49), FILL_VALUE, dtype=np.float32)
    masks = np.zeros((len(product_names), 49, 49), dtype=bool)
    rainfall_available = np.zeros((len(product_names), len(member_names)), dtype=bool)
    observation_records = []
    for product_index, product in enumerate(product_names):
        field = imd_fields[product]
        observations[product_index] = np.where(
            field.valid_mask, field.rainfall_mm, FILL_VALUE
        )
        masks[product_index] = field.valid_mask
        observation_records.append(
            {
                "product": product,
                "record_index": field.metadata["record_index"],
                "date_label": field.metadata["netcdf_time_label"],
                "valid_date": product_valid_date(initialization, product).isoformat(),
                "valid_cells": int(field.valid_mask.sum()),
                "masked_cells": int((~field.valid_mask).sum()),
                "stats": field_stats(field.rainfall_mm[field.valid_mask]),
            }
        )

    source_manifest: dict = {
        "manifest_id": f"{phase_id}-source-{stamp}",
        "initialization_time_utc": initialization.isoformat(),
        "forecast_provider": "NOAA/NCEP GEFSv12 Reforecast",
        "model_name": "GEFS",
        "model_version": "v12 reforecast",
        "access_date": access_date,
        "license_or_terms_reference": "https://registry.opendata.aws/noaa-gefs-reforecast/",
        "observation_provider": "India Meteorological Department",
        "imd_source_manifest": imd_source_manifest,
        "imd_source_sha256": sha256_file(imd_path),
        "training_eligible": False,
        "rainfall_objects": [],
        "atmospheric_objects": [],
        "failures": [],
    }
    rainfall_rows: list[dict] = []
    predictor_rows: list[dict] = []
    conservation_errors: list[float] = []
    network = {"precipitation": 0, "atmospheric": 0, "index": 0}
    network_seconds = 0.0

    index_results: dict[str, tuple[CacheResult, str, Path]] = {}
    index_tasks = []
    for member in member_names:
        url = object_url(initialization, member, "apcp_sfc")
        directory = raw_root / stamp / member / "apcp_sfc"
        index_path = directory / f"apcp_sfc_{stamp}_{member}.grib2.idx"
        reused = reuse_phase1b_index_if_available(
            initialization, member, index_path, url
        )
        if reused is not None:
            index_results[member] = (reused, url, index_path)
        else:
            index_tasks.append((member, url + ".idx", index_path, None))
    fetched_indexes, index_failures = parallel_fetch(
        index_tasks, cache_only, max_workers=network_workers
    )
    for member, result in fetched_indexes.items():
        url = object_url(initialization, member, "apcp_sfc")
        index_results[member] = (result, url, result.path)
        network["index"] += result.network_bytes
        network_seconds += result.elapsed_seconds
    for member, reason in index_failures.items():
        source_manifest["failures"].append(
            {"component": "rainfall_index", "member": member, "reason": reason}
        )

    # Fetch the five large member chunks concurrently. Index parsing remains a
    # fail-closed preparation step, and the bounded thread count is shared with
    # all other network stages rather than nested under another executor.
    prepared_rainfall: dict[str, tuple[list, str, Path, CacheResult, list[str]]] = {}
    chunk_tasks = []
    chunk_context = {}
    for member, (index_result, url, index_path) in index_results.items():
        try:
            entries = select_precipitation_entries(
                parse_generic_index(index_path.read_text(encoding="utf-8"))
            )
            chunk_path = index_path.parent / f"selected_003_075_{stamp}_{member}.grib2"
            if stamp == "2019071400" and member == "c00":
                chunk_result, reuse_notes = acquire_precipitation_chunk(
                    initialization,
                    member,
                    entries,
                    chunk_path,
                    url,
                    cache_only=cache_only,
                )
                prepared_rainfall[member] = (
                    entries, url, chunk_path, chunk_result, reuse_notes
                )
            else:
                overall_range = (entries[0].byte_start, entries[-1].byte_end)
                chunk_tasks.append((member, url, chunk_path, overall_range))
                chunk_context[member] = (entries, url, chunk_path)
        except Exception as exc:
            reason = f"{type(exc).__name__}: {exc}"
            source_manifest["failures"].append(
                {"component": "rainfall_object", "member": member, "reason": reason}
            )
    fetched_chunks, chunk_failures = parallel_fetch(
        chunk_tasks, cache_only, max_workers=network_workers
    )
    for member, chunk_result in fetched_chunks.items():
        entries, url, chunk_path = chunk_context[member]
        prepared_rainfall[member] = (entries, url, chunk_path, chunk_result, [])
        network["precipitation"] += chunk_result.network_bytes
        network_seconds += chunk_result.elapsed_seconds
    for member, reason in chunk_failures.items():
        source_manifest["failures"].append(
            {"component": "rainfall_object", "member": member, "reason": reason}
        )

    for member_index, member in enumerate(member_names):
        member_status = {product: "BLOCKED" for product in product_names}
        member_reasons = {product: "" for product in product_names}
        if member not in index_results or member not in prepared_rainfall:
            missing_reason = index_failures.get(
                member, chunk_failures.get(member, "source rainfall chunk unavailable")
            )
            for product in product_names:
                rainfall_rows.append(
                    {
                        "initialization": stamp,
                        "product": product,
                        "member": member,
                        "status": "BLOCKED",
                        "reason": missing_reason,
                        "source_chunk_bytes_shared": 0,
                    }
                )
            continue
        index_result, _, index_path = index_results[member]
        try:
            entries, url, chunk_path, chunk_result, reuse_notes = prepared_rainfall[member]
            # The Phase 1B bridge is the only non-executor path and may have
            # acquired a suffix; account for it here.
            if stamp == "2019071400" and member == "c00":
                network["precipitation"] += chunk_result.network_bytes
                network_seconds += chunk_result.elapsed_seconds
            chunk = chunk_path.read_bytes()
            decoded_messages = []
            message_metadata = []
            decode_started = time.perf_counter()
            for entry in entries:
                payload = message_payload(chunk, entries[0].byte_start, entry)
                source_id = f"GEFS:{stamp}:{member}:{entry.message_number}"
                accumulation, decoded = decode_precipitation_message(
                    payload,
                    member=member,
                    description=entry.description,
                    source_id=source_id,
                )
                cropped = crop_grid(decoded, **TARGET_BOUNDS)
                accumulation = type(accumulation)(
                    accumulation.start_hour,
                    accumulation.end_hour,
                    cropped.values,
                    accumulation.source_id,
                    accumulation.packing_quantum_mm,
                )
                decoded_messages.append(accumulation)
                message_metadata.append(
                    {
                        "message_number": entry.message_number,
                        "byte_range": [entry.byte_start, entry.byte_end],
                        "byte_size": entry.byte_size,
                        "description": entry.description,
                        "metadata": decoded.metadata,
                    }
                )
            timings["precipitation_decode_and_crop"] += (
                time.perf_counter() - decode_started
            )
            if not np.array_equal(cropped.latitude, first_observation.latitude) or not np.array_equal(
                cropped.longitude, first_observation.longitude
            ):
                raise ValueError("GEFS rainfall grid does not match IMD target centres")
            product_records = []
            for product_index, product in enumerate(product_names):
                start, end = PRODUCT_WINDOWS[product]
                processing_started = time.perf_counter()
                try:
                    if reconstruction_method == "canonical_v2":
                        result = reconstruct_minimal_accumulation_window(
                            decoded_messages,
                            window_start_hour=start,
                            window_end_hour=end,
                        )
                    elif reconstruction_method == "legacy_v1":
                        result = reconstruct_accumulation_window(
                            decoded_messages,
                            window_start_hour=start,
                            window_end_hour=end,
                            negative_tolerance_mm=0.1,
                        )
                    else:
                        raise ValueError(
                            f"unsupported reconstruction method {reconstruction_method}"
                        )
                    regridded = weights.apply(result.rainfall_mm)
                    observation = imd_fields[product]
                    source_integral = area_weighted_integral(
                        result.rainfall_mm,
                        cropped.latitude,
                        cropped.longitude,
                        observation.valid_mask,
                    )
                    target_integral = area_weighted_integral(
                        regridded,
                        observation.latitude,
                        observation.longitude,
                        observation.valid_mask,
                    )
                    difference = (
                        abs(target_integral - source_integral) / abs(source_integral)
                        if source_integral
                        else 0.0 if target_integral == 0 else float("inf")
                    )
                    if difference > CONSERVATION_TOLERANCE:
                        raise ValueError(f"conservation error {difference}")
                    forecasts[product_index, member_index] = regridded
                    rainfall_available[product_index, member_index] = True
                    conservation_errors.append(difference)
                    member_status[product] = "PASS"
                    diagnostics = (
                        {
                            "canonical_subtraction_count": result.subtraction_count,
                            "packing_bound_normalized_negative_count": result.normalized_negative_count,
                            "minimum_normalized_negative_mm": result.minimum_normalized_negative_mm,
                        }
                        if reconstruction_method == "canonical_v2"
                        else {
                            "tiny_negative_count": result.tiny_negative_count,
                            "minimum_tolerated_negative_mm": result.minimum_tolerated_negative_mm,
                            "negative_tolerance_mm": result.negative_tolerance_mm,
                        }
                    )
                    product_records.append(
                        {
                            "product": product,
                            "status": "PASS",
                            "reconstruction_method": reconstruction_method,
                            "segments": [asdict(segment) for segment in result.segments],
                            **diagnostics,
                            "forecast_stats": field_stats(regridded),
                            "conservation_relative_difference": difference,
                        }
                    )
                except Exception as exc:
                    member_status[product] = "FAIL"
                    member_reasons[product] = f"{type(exc).__name__}: {exc}"
                    product_records.append(
                        {"product": product, "status": "FAIL", "reason": str(exc)}
                    )
                    source_manifest["failures"].append(
                        {
                            "component": "rainfall_product",
                            "member": member,
                            "product": product,
                            "reason": f"{type(exc).__name__}: {exc}",
                        }
                    )
                finally:
                    timings["rainfall_reconstruct_regrid_qc"] += (
                        time.perf_counter() - processing_started
                    )
            source_manifest["rainfall_objects"].append(
                {
                    "member": member,
                    "official_url": url,
                    "index": {
                        "path": relative(index_path),
                        "sha256": index_result.sha256,
                        "byte_size": index_result.byte_size,
                    },
                    "selected_chunk": {
                        "path": relative(chunk_path),
                        "sha256": chunk_result.sha256,
                        "byte_size": chunk_result.byte_size,
                        "byte_range": [entries[0].byte_start, entries[-1].byte_end],
                    },
                    "reuse_notes": reuse_notes,
                    "messages": message_metadata,
                    "products": product_records,
                }
            )
        except Exception as exc:
            source_manifest["failures"].append(
                {
                    "component": "rainfall_object",
                    "member": member,
                    "reason": f"{type(exc).__name__}: {exc}",
                }
            )
            member_status = {product: "FAIL" for product in product_names}
            member_reasons = {
                product: f"{type(exc).__name__}: {exc}" for product in product_names
            }
        for product in product_names:
            rainfall_rows.append(
                {
                    "initialization": stamp,
                    "product": product,
                    "member": member,
                    "status": member_status[product],
                    "reason": member_reasons[product],
                    "source_chunk_bytes_shared": (
                        source_manifest["rainfall_objects"][-1]["selected_chunk"]["byte_size"]
                        if source_manifest["rainfall_objects"]
                        and source_manifest["rainfall_objects"][-1]["member"] == member
                        else 0
                    ),
                }
            )

    context_latitude, context_longitude = context_coordinates()
    atmosphere_arrays = {
        key: np.full(
            (len(ATMOSPHERIC_LEADS), context_latitude.size, context_longitude.size),
            FILL_VALUE,
            dtype=np.float32,
        )
        for key in ATMOSPHERIC_SPECS
    }
    atmosphere_units: dict[str, str] = {}
    atmosphere_available = np.zeros(
        (len(ATMOSPHERIC_SPECS), len(ATMOSPHERIC_LEADS)), dtype=bool
    )
    atmospheric_index_tasks = []
    atmospheric_indexes = {}
    for key, spec in ATMOSPHERIC_SPECS.items():
        url = object_url(initialization, "c00", spec.object_family)
        directory = raw_root / stamp / "c00" / spec.object_family
        index_path = directory / f"{spec.object_family}_{stamp}_c00.grib2.idx"
        atmospheric_index_tasks.append((key, url + ".idx", index_path, None))
    atmosphere_index_results, atmosphere_index_failures = parallel_fetch(
        atmospheric_index_tasks, cache_only, max_workers=network_workers
    )
    message_tasks = []
    selected_entries = {}
    for key, result in atmosphere_index_results.items():
        network["index"] += result.network_bytes
        network_seconds += result.elapsed_seconds
        spec = ATMOSPHERIC_SPECS[key]
        url = object_url(initialization, "c00", spec.object_family)
        entries = parse_generic_index(result.path.read_text(encoding="utf-8"))
        atmospheric_indexes[key] = (result, url)
        for lead in ATMOSPHERIC_LEADS:
            try:
                entry = select_atmospheric_entry(entries, spec, lead)
                selected_entries[(key, lead)] = entry
                message_path = result.path.parent / f"lead_{lead:03d}.grib2"
                message_tasks.append(
                    (f"{key}:{lead}", url, message_path, (entry.byte_start, entry.byte_end))
                )
            except Exception as exc:
                atmosphere_index_failures[f"{key}:{lead}"] = str(exc)
    atmosphere_message_results, atmosphere_message_failures = parallel_fetch(
        message_tasks, cache_only, max_workers=network_workers
    )
    for key, reason in atmosphere_index_failures.items():
        for lead in ATMOSPHERIC_LEADS:
            atmosphere_message_failures[f"{key}:{lead}"] = reason
    for key_index, (key, spec) in enumerate(ATMOSPHERIC_SPECS.items()):
        object_record = {
            "field": key,
            "canonical_name": spec.canonical_name,
            "object_family": spec.object_family,
            "messages": [],
        }
        if key in atmospheric_indexes:
            index_result, url = atmospheric_indexes[key]
            object_record.update(
                {
                    "official_url": url,
                    "index_sha256": index_result.sha256,
                    "index_byte_size": index_result.byte_size,
                }
            )
        for lead_index, lead in enumerate(ATMOSPHERIC_LEADS):
            task_key = f"{key}:{lead}"
            if task_key not in atmosphere_message_results:
                reason = atmosphere_message_failures.get(task_key, "source unavailable")
                predictor_rows.append(
                    {
                        "initialization": stamp,
                        "lead": lead,
                        "variable": key,
                        "status": "BLOCKED",
                        "reason": reason,
                        "downloaded_bytes": 0,
                    }
                )
                source_manifest["failures"].append(
                    {"component": "atmospheric", "field": key, "lead": lead, "reason": reason}
                )
                continue
            result = atmosphere_message_results[task_key]
            network["atmospheric"] += result.network_bytes
            network_seconds += result.elapsed_seconds
            entry = selected_entries[(key, lead)]
            atmosphere_started = time.perf_counter()
            try:
                decoded = decode_atmospheric_message(
                    result.path.read_bytes(),
                    member="c00",
                    description=entry.description,
                    spec=spec,
                    lead_hour=lead,
                )
                cropped = crop_grid(decoded, **CONTEXT_BOUNDS)
                context, target_lat, target_lon = bilinear_to_context(
                    cropped.values, cropped.latitude, cropped.longitude
                )
                if not np.array_equal(target_lat, context_latitude) or not np.array_equal(
                    target_lon, context_longitude
                ):
                    raise ValueError("unexpected context-grid coordinates")
                atmosphere_arrays[key][lead_index] = context
                atmosphere_units[key] = decoded.metadata["units"]
                atmosphere_available[key_index, lead_index] = True
                status = "PASS"
                reason = ""
                object_record["messages"].append(
                    {
                        "lead": lead,
                        "status": status,
                        "path": relative(result.path),
                        "sha256": result.sha256,
                        "byte_size": result.byte_size,
                        "byte_range": [entry.byte_start, entry.byte_end],
                        "description": entry.description,
                        "metadata": decoded.metadata,
                        "context_stats": numeric_stats(context),
                    }
                )
            except Exception as exc:
                status = "FAIL"
                reason = f"{type(exc).__name__}: {exc}"
                object_record["messages"].append(
                    {"lead": lead, "status": status, "reason": reason}
                )
                source_manifest["failures"].append(
                    {"component": "atmospheric", "field": key, "lead": lead, "reason": reason}
                )
            finally:
                timings["atmosphere_decode_interpolate_qc"] += (
                    time.perf_counter() - atmosphere_started
                )
            predictor_rows.append(
                {
                    "initialization": stamp,
                    "lead": lead,
                    "variable": key,
                    "status": status,
                    "reason": reason,
                    "downloaded_bytes": result.byte_size,
                }
            )
        source_manifest["atmospheric_objects"].append(object_record)

    source_manifest_path = manifest_root / "daily" / f"source_{stamp}.json"
    write_started = time.perf_counter()
    write_json(source_manifest_path, source_manifest)
    pair_path = processed_root / "daily" / f"rainfall_pair_{stamp}.nc"
    atmosphere_path = processed_root / "daily" / f"atmosphere_context_{stamp}.nc"
    write_daily_pair(
        pair_path,
        initialization=initialization,
        latitude=first_observation.latitude,
        longitude=first_observation.longitude,
        forecasts=forecasts,
        observations=observations,
        masks=masks,
        availability=rainfall_available,
    )
    write_daily_atmosphere(
        atmosphere_path,
        initialization=initialization,
        arrays=atmosphere_arrays,
        units=atmosphere_units,
        availability=atmosphere_available,
    )
    case_statuses = [row["status"] for row in rainfall_rows + predictor_rows]
    daily_status = summarize_initialization_status(case_statuses)
    derived_manifest = {
        "manifest_id": f"{phase_id}-derived-{stamp}",
        "initialization_time_utc": initialization.isoformat(),
        "status": daily_status,
        "source_manifest": relative(source_manifest_path),
        "source_manifest_sha256": sha256_file(source_manifest_path),
        "rainfall_pair": {
            "path": relative(pair_path),
            "sha256": sha256_file(pair_path),
            "byte_size": pair_path.stat().st_size,
        },
        "atmospheric_context": {
            "path": relative(atmosphere_path),
            "sha256": sha256_file(atmosphere_path),
            "byte_size": atmosphere_path.stat().st_size,
        },
        "observation_records": observation_records,
        "rainfall_complete": int(rainfall_available.sum()),
        "rainfall_expected": int(rainfall_available.size),
        "predictor_valid": int(atmosphere_available.sum()),
        "predictor_expected": int(atmosphere_available.size),
        "conservation_errors": conservation_errors,
        "processing_code_hashes": code_hashes(),
        "training_eligible": False,
    }
    derived_manifest_path = manifest_root / "daily" / f"derived_{stamp}.json"
    write_json(derived_manifest_path, derived_manifest)
    timings["artifact_write"] += time.perf_counter() - write_started
    timings["total_initialization"] = time.perf_counter() - initialization_started
    return {
        "status": daily_status,
        "initialization": stamp,
        "rainfall_rows": rainfall_rows,
        "predictor_rows": predictor_rows,
        "conservation_errors": conservation_errors,
        "network": network,
        "network_seconds": network_seconds,
        "source_manifest_path": source_manifest_path,
        "derived_manifest_path": derived_manifest_path,
        "pair_path": pair_path,
        "atmosphere_path": atmosphere_path,
        "forecasts": forecasts,
        "observations": observations,
        "masks": masks,
        "atmosphere_arrays": atmosphere_arrays,
        "timings": timings,
    }


def directory_size(path: Path, *, include_receipts: bool = True) -> int:
    return sum(
        item.stat().st_size
        for item in path.rglob("*")
        if item.is_file() and (include_receipts or not item.name.endswith(".receipt.json"))
    )


def write_monthly_netcdf(path: Path, monthly: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with netcdf_file(path, "w") as dataset:
        forecast = monthly["forecast"]
        observation = monthly["observation"]
        mask = monthly["mask"]
        atmosphere = monthly["atmosphere"]
        dataset.createDimension("init", forecast.shape[0])
        dataset.createDimension("product", forecast.shape[1])
        dataset.createDimension("member", forecast.shape[2])
        dataset.createDimension("y", forecast.shape[3])
        dataset.createDimension("x", forecast.shape[4])
        dataset.createDimension("lead", len(ATMOSPHERIC_LEADS))
        dataset.createDimension("context_y", atmosphere["u850"].shape[2])
        dataset.createDimension("context_x", atmosphere["u850"].shape[3])
        target_latitude = np.arange(10.0, 22.0 + 0.25, 0.25)
        target_longitude = np.arange(68.0, 80.0 + 0.25, 0.25)
        context_latitude, context_longitude = context_coordinates()
        dataset.createVariable("target_latitude", "d", ("y",))[:] = target_latitude
        dataset.createVariable("target_longitude", "d", ("x",))[:] = target_longitude
        dataset.createVariable("context_latitude", "d", ("context_y",))[:] = context_latitude
        dataset.createVariable("context_longitude", "d", ("context_x",))[:] = context_longitude
        forecast_var = dataset.createVariable(
            "forecast_rain", "f", ("init", "product", "member", "y", "x")
        )
        forecast_var[:] = forecast
        forecast_var.units = "mm"
        observation_var = dataset.createVariable(
            "observation_rain", "f", ("init", "product", "y", "x")
        )
        observation_var[:] = observation
        observation_var.units = "mm"
        dataset.createVariable("valid_mask", "b", ("init", "product", "y", "x"))[:] = mask
        for key, values in atmosphere.items():
            variable = dataset.createVariable(
                key, "f", ("init", "lead", "context_y", "context_x")
            )
            variable[:] = values
            variable.units = {
                "u850": "m s**-1",
                "v850": "m s**-1",
                "q700": "kg kg**-1",
                "z500": "gpm",
                "mslp": "Pa",
                "pwat": "kg m**-2",
            }[key]
        dataset.training_eligible = "false"
        dataset.scope = "storage-format evaluation only"
        dataset.Conventions = "CF-1.8"


def write_monthly_zarr(path: Path, monthly: dict, *, dataset_version: str) -> None:
    root = zarr.open_group(str(path), mode="w")
    root.attrs.update({
        "training_eligible": False,
        "dataset_version": dataset_version,
        "product_names": list(PRODUCT_WINDOWS),
        "member_names": list(ENSEMBLE_MEMBERS),
        "atmospheric_variable_names": list(ATMOSPHERIC_SPECS),
        "rainfall_dimensions": ["init_time", "product", "member", "lat", "lon"],
        "observation_dimensions": ["init_time", "product", "lat", "lon"],
        "atmosphere_dimensions": ["init_time", "lead", "variable", "lat", "lon"],
    })
    root.create_array("init_time_unix_seconds", data=np.asarray(monthly["init_time"], dtype=np.int64))
    root.create_array("lead_hours", data=np.asarray(ATMOSPHERIC_LEADS, dtype=np.int32))
    root.create_array("target_latitude", data=np.arange(10.0, 22.0 + 0.25, 0.25))
    root.create_array("target_longitude", data=np.arange(68.0, 80.0 + 0.25, 0.25))
    context_latitude, context_longitude = context_coordinates()
    root.create_array("context_latitude", data=context_latitude)
    root.create_array("context_longitude", data=context_longitude)
    forecast_array = root.create_array(
        "forecast_rain",
        data=monthly["forecast"],
        chunks=(1, 3, 5, 49, 49),
    )
    forecast_array.attrs["units"] = "mm"
    observation_array = root.create_array(
        "observation_rain", data=monthly["observation"], chunks=(1, 3, 49, 49)
    )
    observation_array.attrs["units"] = "mm"
    root.create_array("valid_mask", data=monthly["mask"], chunks=(1, 3, 49, 49))
    atmosphere = np.stack(
        [monthly["atmosphere"][key] for key in ATMOSPHERIC_SPECS], axis=2
    )
    atmosphere_array = root.create_array(
        "atmosphere", data=atmosphere, chunks=(1, 3, 1, 51, 81)
    )
    atmosphere_array.attrs["units_by_variable"] = {
            "u850": "m s**-1",
            "v850": "m s**-1",
            "q700": "kg kg**-1",
            "z500": "gpm",
            "mslp": "Pa",
            "pwat": "kg m**-2",
        }


def benchmark_storage(netcdf_path: Path, zarr_path: Path) -> dict:
    repetitions = 30
    started = time.perf_counter()
    for _ in range(repetitions):
        with netcdf_file(netcdf_path, "r", mmap=False) as dataset:
            _ = np.asarray(dataset.variables["forecast_rain"].data[15, 1, 2]).copy()
    netcdf_random = (time.perf_counter() - started) / repetitions
    started = time.perf_counter()
    for _ in range(repetitions):
        root = zarr.open_group(str(zarr_path), mode="r")
        _ = np.asarray(root["forecast_rain"][15, 1, 2])
    zarr_random = (time.perf_counter() - started) / repetitions
    started = time.perf_counter()
    with netcdf_file(netcdf_path, "r", mmap=False) as dataset:
        _ = np.asarray(dataset.variables["forecast_rain"].data).copy()
    netcdf_full = time.perf_counter() - started
    started = time.perf_counter()
    root = zarr.open_group(str(zarr_path), mode="r")
    _ = np.asarray(root["forecast_rain"][:])
    zarr_full = time.perf_counter() - started
    return {
        "netcdf": {
            "byte_size": netcdf_path.stat().st_size,
            "random_slice_mean_seconds": netcdf_random,
            "full_forecast_read_seconds": netcdf_full,
            "append_chunk_practicality": "fixed classic NetCDF output; rewrite needed for this implementation",
            "metadata_preservation": "CF-style variables and attributes",
            "portability": "single file; broadly portable",
        },
        "zarr": {
            "byte_size": directory_size(zarr_path),
            "random_slice_mean_seconds": zarr_random,
            "full_forecast_read_seconds": zarr_full,
            "append_chunk_practicality": "chunked hierarchy supports initialization-wise extension",
            "metadata_preservation": "group and array attributes; CF conventions require project schema",
            "portability": "many files; efficient object-store/chunk access, less convenient to copy",
        },
        "library_versions": {"scipy": scipy.__version__, "zarr": zarr.__version__},
    }


def run(
    imd_path: Path,
    output_root: Path,
    *,
    cache_only: bool,
    year: int = 2019,
    month: int = 7,
    phase_id: str = "phase1c",
    network_workers: int = 3,
    reconstruction_method: str = "legacy_v1",
    dataset_version: str = "varshasetu-gefs12r-imd025-jjas-2000-2019-v1",
    raw_phase: str = "phase1c",
    imd_source_manifest: str = "data/manifests/phase1b/2019-07-15/imd_rf25_2019.json",
    expected_imd_sha256: str = "c551c563b3514d492a2de94c706c1c254d5826656738b4a8e7dbd83841344a5b",
    access_date: str = "2026-09-19",
) -> dict:
    started = time.perf_counter()
    initializations = monthly_initializations(year, month)
    period_id = f"{year:04d}-{month:02d}"
    expected_initializations = len(initializations)
    raw_root = output_root / f"raw/{raw_phase}/gefsv12"
    processed_root = output_root / f"processed/{phase_id}/{period_id}"
    manifest_root = output_root / f"manifests/{phase_id}/{period_id}"
    previous_daily_hashes = {
        relative(path): sha256_file(path)
        for path in (manifest_root / "daily").glob("*.json")
    } if (manifest_root / "daily").exists() else {}
    imd_path = imd_path.resolve()
    if sha256_file(imd_path) != expected_imd_sha256:
        raise ValueError("IMD file does not match its validated source-manifest hash")
    reference = load_imd_day(imd_path, product_valid_date(initializations[0], "day1_24h"), **TARGET_BOUNDS)
    weights = build_first_order_conservative_weights(
        reference.latitude, reference.longitude, reference.latitude, reference.longitude
    )
    weight_path = processed_root / "weights/gefsv12_to_imd025_conservative_weights.npy"
    weight_hash, weight_bytes = weights.save(weight_path)

    results = []
    with PeakRssMonitor() as memory:
        for index, initialization in enumerate(initializations, start=1):
            print(f"[{index:02d}/{expected_initializations}] {initialization:%Y-%m-%d} starting", flush=True)
            result = acquire_initialization(
                initialization,
                imd_path=imd_path,
                raw_root=raw_root,
                processed_root=processed_root,
                manifest_root=manifest_root,
                weights=weights,
                cache_only=cache_only,
                phase_id=phase_id,
                network_workers=network_workers,
                reconstruction_method=reconstruction_method,
                imd_source_manifest=imd_source_manifest,
                access_date=access_date,
            )
            results.append(result)
            print(
                f"[{index:02d}/{expected_initializations}] {initialization:%Y-%m-%d} {result['status']}",
                flush=True,
            )

        rainfall_rows = [row for result in results for row in result["rainfall_rows"]]
        predictor_rows = [row for result in results for row in result["predictor_rows"]]
        all_observation_dates = sorted(
            {
                product_valid_date(initialization, product)
                for initialization in initializations
                for product in PRODUCT_WINDOWS
            }
        )
        event_rows = [
            observation_event_stats(
                field.rainfall_mm,
                field.valid_mask,
                field.latitude,
                field.longitude,
                valid_date=valid_date,
            )
            for valid_date in all_observation_dates
            for field in [load_imd_day(imd_path, valid_date, **TARGET_BOUNDS)]
        ]
        monthly_arrays = {
            "init_time": [int(item.timestamp()) for item in initializations],
            "forecast": np.stack([result["forecasts"] for result in results]),
            "observation": np.stack([result["observations"] for result in results]),
            "mask": np.stack([result["masks"] for result in results]).astype(np.int8),
            "atmosphere": {
                key: np.stack([result["atmosphere_arrays"][key] for result in results])
                for key in ATMOSPHERIC_SPECS
            },
        }
        monthly_processing_started = time.perf_counter()
        storage_root = processed_root / "storage_evaluation"
        monthly_netcdf = storage_root / f"{year:04d}{month:02d}_arrays.nc"
        monthly_zarr = storage_root / f"{year:04d}{month:02d}_arrays.zarr"
        write_monthly_netcdf(monthly_netcdf, monthly_arrays)
        write_monthly_zarr(monthly_zarr, monthly_arrays, dataset_version=dataset_version)
        storage_benchmark = benchmark_storage(monthly_netcdf, monthly_zarr)
        monthly_processing_seconds = time.perf_counter() - monthly_processing_started

    write_csv(
        manifest_root / "rainfall_acquisition_completeness.csv",
        rainfall_rows,
        [
            "initialization",
            "product",
            "member",
            "status",
            "reason",
            "source_chunk_bytes_shared",
        ],
    )
    write_csv(
        manifest_root / "predictor_availability.csv",
        predictor_rows,
        ["initialization", "lead", "variable", "status", "reason", "downloaded_bytes"],
    )
    write_csv(
        manifest_root / "event_coverage.csv",
        event_rows,
        list(event_rows[0]),
    )
    initialization_rows = [
        {
            "initialization": result["initialization"],
            "status": result["status"],
            "reason": "; ".join(
                f"{row.get('product', row.get('variable'))}/{row.get('member', row.get('lead'))}: {row['reason']}"
                for row in result["rainfall_rows"] + result["predictor_rows"]
                if row["status"] != "PASS"
            ),
        }
        for result in results
    ]
    write_csv(
        manifest_root / "initialization_status.csv",
        initialization_rows,
        ["initialization", "status", "reason"],
    )

    child_hashes = {}
    for result in results:
        child_hashes[f"source:{result['initialization']}"] = sha256_file(
            result["source_manifest_path"]
        )
        child_hashes[f"derived:{result['initialization']}"] = sha256_file(
            result["derived_manifest_path"]
        )
    conservation = [error for result in results for error in result["conservation_errors"]]
    # Account only for this calendar month. The immutable raw cache is shared
    # across Phase 2A months, so scanning the whole root would make later
    # monthly reports cumulative and would overstate storage projections.
    raw_files = [
        item
        for initialization in initializations
        for item in (raw_root / initialization.strftime("%Y%m%d%H")).rglob("*")
        if item.is_file()
    ]
    source_bytes = {
        "precipitation_messages": sum(
            item.stat().st_size
            for item in raw_files
            if item.name.startswith("selected_") and item.suffix == ".grib2"
        ),
        "atmospheric_messages": sum(
            item.stat().st_size
            for item in raw_files
            if item.name.startswith("lead_") and item.suffix == ".grib2"
        ),
        "indexes": sum(
            item.stat().st_size for item in raw_files if item.name.endswith(".grib2.idx")
        ),
        "cache_receipts": sum(
            item.stat().st_size for item in raw_files if item.name.endswith(".receipt.json")
        ),
        "imd_existing_source": imd_path.stat().st_size,
        "imd_incremental_network": 0,
    }
    source_bytes["cache_excluding_receipts"] = (
        source_bytes["precipitation_messages"]
        + source_bytes["atmospheric_messages"]
        + source_bytes["indexes"]
    )
    daily_pair_bytes = sum(result["pair_path"].stat().st_size for result in results)
    daily_atmosphere_bytes = sum(
        result["atmosphere_path"].stat().st_size for result in results
    )
    processed_bytes = {
        "daily_rainfall_pairs": daily_pair_bytes,
        "daily_atmospheric_context": daily_atmosphere_bytes,
        "regridding_weights": weight_bytes,
        "storage_evaluation_netcdf": monthly_netcdf.stat().st_size,
        "storage_evaluation_zarr": directory_size(monthly_zarr),
        "daily_manifests": directory_size(manifest_root / "daily"),
        "qc_csv_tables": sum(
            path.stat().st_size for path in manifest_root.glob("*.csv")
        ),
    }
    processed_bytes["total"] = sum(processed_bytes.values())
    failed_cases = [
        row for row in rainfall_rows + predictor_rows if row["status"] != "PASS"
    ]
    plausible_ranges = {
        "u850": (-150.0, 150.0),
        "v850": (-150.0, 150.0),
        "q700": (0.0, 0.1),
        "z500": (4000.0, 7000.0),
        "mslp": (80000.0, 110000.0),
        "pwat": (0.0, 100.0),
    }
    predictor_statistics = {}
    for key in ATMOSPHERIC_SPECS:
        values = monthly_arrays["atmosphere"][key].astype(float)
        valid = values != float(FILL_VALUE)
        valid_values = values[valid]
        lower, upper = plausible_ranges[key]
        predictor_statistics[key] = {
            "min": float(valid_values.min()) if valid_values.size else None,
            "max": float(valid_values.max()) if valid_values.size else None,
            "mean": float(valid_values.mean()) if valid_values.size else None,
            "missing_fraction": float((~valid).mean()),
            "plausibility_warning": (
                "outside_initial_warning_bounds"
                if valid_values.size
                and (float(valid_values.min()) < lower or float(valid_values.max()) > upper)
                else None
            ),
            "initial_warning_bounds": [lower, upper],
        }
    qc_summary = {
        "initialization_status_counts": {
            status: sum(row["status"] == status for row in initialization_rows)
            for status in ("PASS", "PARTIAL", "BLOCKED", "FAIL")
        },
        "rainfall_expected": len(rainfall_rows),
        "rainfall_complete": sum(row["status"] == "PASS" for row in rainfall_rows),
        "predictor_expected": len(predictor_rows),
        "predictor_valid": sum(row["status"] == "PASS" for row in predictor_rows),
        "conservation": {
            "count": len(conservation),
            "minimum": min(conservation) if conservation else None,
            "median": float(np.median(conservation)) if conservation else None,
            "maximum": max(conservation) if conservation else None,
            "failures": sum(error > CONSERVATION_TOLERANCE for error in conservation),
            "tolerance": CONSERVATION_TOLERANCE,
        },
        "event_coverage": {
            "unique_observation_days": len(event_rows),
            "days_with_heavy_cell": sum(row["heavy_cell_count"] > 0 for row in event_rows),
            "days_with_very_heavy_cell": sum(
                row["very_heavy_cell_count"] > 0 for row in event_rows
            ),
            "total_heavy_grid_cell_events": sum(
                row["heavy_cell_count"] for row in event_rows
            ),
            "total_very_heavy_grid_cell_events": sum(
                row["very_heavy_cell_count"] for row in event_rows
            ),
            "maximum_observed_rainfall_mm": max(row["max_mm"] for row in event_rows),
            "district_counts": "not_computed:no_authoritative_district_geometry",
        },
        "weight_sha256": weight_hash,
        "predictor_statistics": predictor_statistics,
    }
    collection = MonthlyCollectionManifest(
        collection_id=f"{phase_id}-{period_id}-{dataset_version.rsplit('-', 1)[-1]}",
        period={"month": period_id, "start": initializations[0].date().isoformat(), "end": initializations[-1].date().isoformat()},
        forecast_provider="NOAA/NCEP GEFSv12 Reforecast",
        observation_provider="India Meteorological Department 0.25 degree Daily Gridded Rainfall",
        expected_initializations=expected_initializations,
        observed_initializations=len(results),
        rainfall_products=list(PRODUCT_WINDOWS),
        ensemble_members=list(ENSEMBLE_MEMBERS),
        atmospheric_fields=list(ATMOSPHERIC_SPECS),
        target_domain=TARGET_BOUNDS,
        context_domain=CONTEXT_BOUNDS | {"resolution_degrees": 0.5},
        source_bytes=source_bytes,
        processed_bytes=processed_bytes,
        child_manifest_hashes=child_hashes,
        failed_cases=failed_cases,
        qc_summary=qc_summary,
        training_eligible=False,
        processing_code_hashes=code_hashes(),
        dataset_version=dataset_version,
        reconstruction_method=reconstruction_method,
        network_workers=network_workers,
        storage_format={
            "authoritative_candidate": "zarr",
            "zarr_version": zarr.__version__,
            "netcdf_library": f"scipy-{scipy.__version__}",
            "note": "Volatile read timings are retained only in the execution report.",
        },
    ).model_dump(mode="json")
    collection_path = manifest_root / "monthly_collection_manifest.json"
    write_json(collection_path, collection)

    network = {
        category: sum(result["network"][category] for result in results)
        for category in ("precipitation", "atmospheric", "index")
    }
    measured_total = source_bytes["cache_excluding_receipts"] + processed_bytes["total"]
    total_runtime_seconds = time.perf_counter() - started
    current_daily_hashes = {
        relative(path): sha256_file(path)
        for path in (manifest_root / "daily").glob("*.json")
    }
    rerun_comparison = {
        "previous_artifact_count": len(previous_daily_hashes),
        "current_artifact_count": len(current_daily_hashes),
        "unchanged_count": sum(
            previous_daily_hashes.get(path) == digest
            for path, digest in current_daily_hashes.items()
            if path in previous_daily_hashes
        ),
        "changed_or_new": sorted(
            path
            for path, digest in current_daily_hashes.items()
            if previous_daily_hashes.get(path) != digest
        ),
        "removed": sorted(set(previous_daily_hashes) - set(current_daily_hashes)),
    }
    child_timings = {
        key: sum(result["timings"][key] for result in results)
        for key in results[0]["timings"]
    }
    execution = {
        "status": (
            "PASS"
            if not failed_cases and all(row["status"] == "PASS" for row in initialization_rows)
            else "PARTIAL"
        ),
        "cache_only": cache_only,
        "network_bytes": network | {"total": sum(network.values()), "imd": 0},
        "network_seconds_sum_concurrent_requests": sum(
            result["network_seconds"] for result in results
        ),
        "total_runtime_seconds": total_runtime_seconds,
        "average_seconds_per_initialization": total_runtime_seconds / expected_initializations,
        "measured_stage_seconds": child_timings
        | {"monthly_consolidation_and_benchmark": monthly_processing_seconds},
        "peak_rss_bytes": memory.peak,
        "raw_source_bytes": source_bytes,
        "processed_bytes": processed_bytes,
        "storage_projections": projected_storage(measured_total),
        "storage_format_evaluation": storage_benchmark,
        "collection_manifest": relative(collection_path),
        "collection_manifest_sha256": sha256_file(collection_path),
        "qc_summary": qc_summary,
        "training_eligible": False,
        "dataset_version": dataset_version,
        "reconstruction_method": reconstruction_method,
        "network_workers": network_workers,
        "rerun_daily_manifest_comparison": rerun_comparison,
    }
    if cache_only:
        execution_name = "execution_cache_validation.json"
    elif (manifest_root / "execution_initial.json").exists():
        execution_name = "execution_resume.json"
    else:
        execution_name = "execution_initial.json"
    execution_path = manifest_root / execution_name
    write_json(execution_path, execution)
    print(json.dumps(execution, indent=2, sort_keys=True), flush=True)
    return execution


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--imd-file",
        type=Path,
        default=Path("data/raw/observations/imd/2019/RF25_ind2019_rfp25.nc"),
    )
    parser.add_argument("--output-root", type=Path, default=Path("data"))
    parser.add_argument("--cache-only", action="store_true")
    parser.add_argument("--year", type=int, default=2019)
    parser.add_argument("--month", type=int, default=7)
    parser.add_argument("--phase-id", default="phase1c")
    parser.add_argument("--network-workers", type=int, default=3)
    parser.add_argument(
        "--reconstruction-method",
        choices=("legacy_v1", "canonical_v2"),
        default="legacy_v1",
    )
    parser.add_argument(
        "--dataset-version",
        default="varshasetu-gefs12r-imd025-jjas-2000-2019-v1",
    )
    parser.add_argument("--raw-phase", default="phase1c")
    parser.add_argument(
        "--imd-source-manifest",
        default="data/manifests/phase1b/2019-07-15/imd_rf25_2019.json",
    )
    parser.add_argument(
        "--expected-imd-sha256",
        default="c551c563b3514d492a2de94c706c1c254d5826656738b4a8e7dbd83841344a5b",
    )
    parser.add_argument("--access-date", default="2026-09-19")
    args = parser.parse_args()
    run(
        args.imd_file,
        args.output_root,
        cache_only=args.cache_only,
        year=args.year,
        month=args.month,
        phase_id=args.phase_id,
        network_workers=args.network_workers,
        reconstruction_method=args.reconstruction_method,
        dataset_version=args.dataset_version,
        raw_phase=args.raw_phase,
        imd_source_manifest=args.imd_source_manifest,
        expected_imd_sha256=args.expected_imd_sha256,
        access_date=args.access_date,
    )


if __name__ == "__main__":
    main()
