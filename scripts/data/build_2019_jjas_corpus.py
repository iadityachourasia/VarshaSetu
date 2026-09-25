"""Build the QC/index/baseline layer for the acquired 2019 JJAS corpus."""

from __future__ import annotations

import csv
import hashlib
import json
import sys
from collections import defaultdict
from datetime import timedelta
from pathlib import Path

import numpy as np
import zarr

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.app.data.corpus_policy import EligibilityInputs, compute_eligibility, monthly_admission
from backend.app.data.monthly_qc import (
    ATMOSPHERIC_LEADS, ENSEMBLE_MEMBERS, PRODUCT_WINDOWS, TARGET_BOUNDS,
    observation_event_stats, product_valid_date,
)
from backend.app.data.regridding import grid_cell_areas
from backend.app.data.seasonal_corpus import (
    eligibility_index_row, raw_control_verification, seasonal_admission,
    seasonal_initializations, validate_seasonal_zarr_shape,
)
from backend.app.data.thresholds import (
    HEAVY_24H_MIN_MM, VERY_HEAVY_24H_MIN_MM, EXTREMELY_HEAVY_24H_MIN_MM,
)
from backend.app.data_sources.imd_rainfall import load_imd_day


PRODUCTS = tuple(PRODUCT_WINDOWS)
VARIABLES = ("u850", "v850", "q700", "z500", "mslp", "pwat")
DAILY_NETCDF_AUDIT_STAMPS = {
    "2019061100",  # complete five-member reference case
    "2019072200",  # known packing-anomaly case
    "2019093000",  # September-to-October valid-date boundary
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def tree_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    for item in sorted(candidate for candidate in path.rglob("*") if candidate.is_file()):
        digest.update(item.relative_to(path).as_posix().encode())
        digest.update(bytes.fromhex(sha256_file(item)))
    return digest.hexdigest()


def read_csv(path: Path) -> list[dict]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict], *, fieldnames: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if fieldnames is None:
        if not rows:
            raise ValueError(f"fieldnames are required for empty table {path}")
        fieldnames = list(rows[0])
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def finalize_netcdf_retention(
    *, processed_root: Path, manifest_root: Path, authoritative_zarr: Path,
) -> dict:
    """Keep bounded audit NetCDFs after the authoritative seasonal Zarr exists."""
    processed_root = processed_root.resolve()
    retention_path = manifest_root / "netcdf_retention_manifest.json"
    prior_pruned: dict[str, dict] = {}
    if retention_path.exists():
        previous = json.loads(retention_path.read_text(encoding="utf-8"))
        prior_pruned = {item["path"]: item for item in previous.get("pruned", [])}
    retained, newly_pruned = [], []
    for path in sorted(processed_root.rglob("*.nc")):
        resolved = path.resolve()
        if not resolved.is_relative_to(processed_root):
            raise ValueError(f"NetCDF retention target escaped processed root: {resolved}")
        relative = path.relative_to(ROOT).as_posix()
        keep = "storage_evaluation" in path.parts or any(
            stamp in path.name for stamp in DAILY_NETCDF_AUDIT_STAMPS
        )
        record = {
            "path": relative,
            "bytes": path.stat().st_size,
            "sha256": sha256_file(path),
        }
        if keep:
            retained.append(record)
        else:
            path.unlink()
            newly_pruned.append(record)
    for item in newly_pruned:
        prior_pruned[item["path"]] = item
    pruned = [prior_pruned[path] for path in sorted(prior_pruned)]
    disposition = {
        "policy": (
            "Seasonal Zarr is authoritative; retain four monthly storage-format "
            "benchmarks and three deterministic daily audit cases only."
        ),
        "authoritative_zarr": authoritative_zarr.relative_to(ROOT).as_posix(),
        "daily_audit_initializations": sorted(DAILY_NETCDF_AUDIT_STAMPS),
        "retained": retained,
        "pruned": pruned,
        "retained_count": len(retained),
        "pruned_count": len(pruned),
        "retained_bytes": sum(item["bytes"] for item in retained),
        "pruned_bytes": sum(item["bytes"] for item in pruned),
        "note": (
            "Pruned entries remain hash-addressed here and in their acquisition-time "
            "derived manifests; they are reproducible from the immutable source cache."
        ),
    }
    write_json(retention_path, disposition)
    return {
        "manifest": retention_path.relative_to(ROOT).as_posix(),
        "retained_count": disposition["retained_count"],
        "pruned_count": disposition["pruned_count"],
        "retained_bytes": disposition["retained_bytes"],
        "pruned_bytes": disposition["pruned_bytes"],
    }


def main() -> None:
    months = (6, 7, 8, 9)
    initializations = seasonal_initializations(2019)
    manifest_root = ROOT / "data/manifests/phase1e/2019-JJAS"
    processed_path = ROOT / "data/processed/phase1e/2019-JJAS/varshasetu-gefs12r-imd025-2019-jjas-v1.zarr"
    imd_path = ROOT / "data/raw/observations/imd/2019/RF25_ind2019_rfp25.nc"

    monthly = {}
    forecast_parts, observation_parts, mask_parts, atmosphere_parts, time_parts = [], [], [], [], []
    rainfall_all: list[dict] = []
    predictor_all: list[dict] = []
    monthly_lineage = {}
    for month in months:
        period = f"2019-{month:02d}"
        month_manifest_root = ROOT / f"data/manifests/phase1e/{period}"
        collection_path = month_manifest_root / "monthly_collection_manifest.json"
        collection = json.loads(collection_path.read_text(encoding="utf-8"))
        rainfall = read_csv(month_manifest_root / "rainfall_acquisition_completeness.csv")
        predictors = read_csv(month_manifest_root / "predictor_availability.csv")
        rainfall_all.extend(rainfall)
        predictor_all.extend(predictors)
        invalid = sum(row["status"] != "PASS" for row in rainfall + predictors)
        lineage_complete = (
            collection["observed_initializations"] == collection["expected_initializations"]
            and bool(collection["child_manifest_hashes"])
        )
        outcome = monthly_admission(
            source_contract_valid=collection["observed_initializations"] == collection["expected_initializations"],
            lineage_complete=lineage_complete,
            invalid_units=invalid,
        ).value
        monthly[period] = {
            "admission": outcome,
            "invalid_units": invalid,
            "rainfall_valid": sum(row["status"] == "PASS" for row in rainfall),
            "rainfall_expected": len(rainfall),
            "atmosphere_valid": sum(row["status"] == "PASS" for row in predictors),
            "atmosphere_expected": len(predictors),
        }
        monthly_lineage[period] = {
            "manifest": collection_path.relative_to(ROOT).as_posix(),
            "sha256": sha256_file(collection_path),
        }
        zarr_path = ROOT / f"data/processed/phase1e/{period}/storage_evaluation/2019{month:02d}_arrays.zarr"
        group = zarr.open_group(str(zarr_path), mode="r")
        forecast_parts.append(np.asarray(group["forecast_rain"][:]))
        observation_parts.append(np.asarray(group["observation_rain"][:]))
        mask_parts.append(np.asarray(group["valid_mask"][:], dtype=np.uint8))
        atmosphere_parts.append(np.asarray(group["atmosphere"][:]))
        time_parts.append(np.asarray(group["init_time_unix_seconds"][:], dtype=np.int64))

    forecast = np.concatenate(forecast_parts)
    observation = np.concatenate(observation_parts)
    mask = np.concatenate(mask_parts)
    atmosphere = np.concatenate(atmosphere_parts)
    init_time = np.concatenate(time_parts)
    validate_seasonal_zarr_shape(
        forecast_shape=forecast.shape, observation_shape=observation.shape,
        mask_shape=mask.shape, atmosphere_shape=atmosphere.shape,
    )

    root = zarr.open_group(str(processed_path), mode="w")
    root.attrs.update({
        "dataset_version": "varshasetu-gefs12r-imd025-jjas-2000-2019-v1",
        "season_subset": "2019-JJAS",
        "training_eligible": False,
        "product_names": list(PRODUCTS), "member_names": list(ENSEMBLE_MEMBERS),
        "atmospheric_variable_names": list(VARIABLES),
        "monthly_manifest_lineage": monthly_lineage,
    })
    root.create_array("init_time_unix_seconds", data=init_time)
    valid_times = np.asarray([
        [int((item + timedelta(hours=end)).timestamp()) for _, end in PRODUCT_WINDOWS.values()]
        for item in initializations
    ], dtype=np.int64)
    root.create_array("valid_time_unix_seconds", data=valid_times, chunks=(1, 3))
    root.create_array("lead_hours", data=np.asarray(ATMOSPHERIC_LEADS, dtype=np.int32))
    root.create_array("window_start_hours", data=np.asarray([value[0] for value in PRODUCT_WINDOWS.values()], dtype=np.int32))
    root.create_array("window_end_hours", data=np.asarray([value[1] for value in PRODUCT_WINDOWS.values()], dtype=np.int32))
    root.create_array("target_latitude", data=np.arange(10.0, 22.0 + 0.25, 0.25))
    root.create_array("target_longitude", data=np.arange(68.0, 80.0 + 0.25, 0.25))
    root.create_array("context_latitude", data=np.arange(5.0, 30.0 + 0.5, 0.5))
    root.create_array("context_longitude", data=np.arange(55.0, 95.0 + 0.5, 0.5))
    root.create_array("forecast_rain", data=forecast, chunks=(1, 3, 5, 49, 49)).attrs["units"] = "mm"
    root.create_array("observation_rain", data=observation, chunks=(1, 3, 49, 49)).attrs["units"] = "mm"
    root.create_array("valid_mask", data=mask, chunks=(1, 3, 49, 49))
    root.create_array("atmosphere", data=atmosphere, chunks=(1, 3, 1, 51, 81))

    rain_lookup = {(row["initialization"], row["product"], row["member"]): row for row in rainfall_all}
    predictor_lookup = defaultdict(list)
    for row in predictor_all:
        predictor_lookup[row["initialization"]].append(row)
    eligibility_rows = []
    for initialization in initializations:
        stamp = initialization.strftime("%Y%m%d%H")
        atmosphere_valid = len(predictor_lookup[stamp]) == 18 and all(row["status"] == "PASS" for row in predictor_lookup[stamp])
        source_manifest_path = ROOT / f"data/manifests/phase1e/{initialization:%Y-%m}/daily/source_{stamp}.json"
        source_manifest = json.loads(source_manifest_path.read_text(encoding="utf-8"))
        source_failures = source_manifest.get("failures", [])
        source_transport_valid = not any(item["component"] in {"rainfall_index", "rainfall_object", "atmospheric_index", "atmospheric_object"} for item in source_failures)
        for product in PRODUCTS:
            c00 = rain_lookup[(stamp, product, "c00")]
            perturb = {member: rain_lookup[(stamp, product, member)]["status"] == "PASS" for member in ENSEMBLE_MEMBERS[1:]}
            tiers = compute_eligibility(EligibilityInputs(
                source_valid=source_transport_valid,
                control_rain_valid=c00["status"] == "PASS",
                perturbation_rain_valid=perturb,
                observation_valid=True,
                atmospheric_bundle_valid=atmosphere_valid,
                timing_valid=True,
                spatial_alignment_valid=c00["status"] == "PASS",
                spatial_mask_valid=True,
            ))
            failures = [rain_lookup[(stamp, product, member)]["reason"] for member in ENSEMBLE_MEMBERS if rain_lookup[(stamp, product, member)]["status"] != "PASS"]
            failures.extend(row["reason"] for row in predictor_lookup[stamp] if row["status"] != "PASS")
            eligibility_rows.append(eligibility_index_row(
                initialization=initialization.isoformat(), product=product,
                valid_date=product_valid_date(initialization, product).isoformat(),
                eligibility=tiers, reasons=failures,
                source_manifest=source_manifest_path.relative_to(ROOT).as_posix(),
            ))
    write_csv(manifest_root / "eligibility_index.csv", eligibility_rows)
    tier_files = {
        "control_model_index.csv": "CONTROL_MODEL_ELIGIBLE",
        "full_ensemble_index.csv": "FULL_ENSEMBLE_ELIGIBLE",
        "regime_index.csv": "REGIME_ELIGIBLE",
        "extreme_event_index.csv": "EXTREME_EVENT_ELIGIBLE",
        "fss_index.csv": "FSS_ELIGIBLE",
    }
    for filename, tier in tier_files.items():
        write_csv(
            manifest_root / filename,
            [row for row in eligibility_rows if row[tier]],
            fieldnames=list(eligibility_rows[0]),
        )

    event_rows = []
    for valid_date in sorted({product_valid_date(item, product) for item in initializations for product in PRODUCTS}):
        field = load_imd_day(imd_path, valid_date, **TARGET_BOUNDS)
        row = observation_event_stats(field.rainfall_mm, field.valid_mask, field.latitude, field.longitude, valid_date=valid_date)
        areas = grid_cell_areas(field.latitude, field.longitude)
        extreme = field.valid_mask & (field.rainfall_mm >= EXTREMELY_HEAVY_24H_MIN_MM)
        row["extremely_heavy_cell_count"] = int(extreme.sum())
        row["extremely_heavy_valid_area_fraction"] = float(areas[extreme].sum() / areas[field.valid_mask].sum())
        row["extremely_heavy_threshold_mm"] = EXTREMELY_HEAVY_24H_MIN_MM
        event_rows.append(row)
    write_csv(manifest_root / "event_inventory_daily.csv", event_rows)

    baseline = {}
    catalogue = []
    for product_index, product in enumerate(PRODUCTS):
        eligible = np.asarray([row["CONTROL_MODEL_ELIGIBLE"] for row in eligibility_rows if row["product"] == product], dtype=bool)
        product_forecast = forecast[:, product_index, 0]
        product_observation = observation[:, product_index]
        product_mask = mask[:, product_index].astype(bool) & eligible[:, None, None]
        baseline[product] = raw_control_verification(product_forecast, product_observation, product_mask)
        for init_index, initialization in enumerate(initializations):
            obs_mask = mask[init_index, product_index].astype(bool)
            obs = observation[init_index, product_index]
            row_eligibility = next(row for row in eligibility_rows if row["initialization"] == initialization.isoformat() and row["product"] == product)
            comparable = obs_mask & (product_forecast[init_index] >= 0)
            if comparable.any() and row_eligibility["CONTROL_MODEL_ELIGIBLE"]:
                diff = product_forecast[init_index][comparable] - obs[comparable]
                rmse, bias = float(np.sqrt(np.mean(diff ** 2))), float(np.mean(diff))
            else:
                rmse, bias = "", ""
            valid_obs = obs[obs_mask]
            catalogue.append({
                "initialization": initialization.isoformat(), "product": product,
                "valid_date": product_valid_date(initialization, product).isoformat(),
                "observed_max_mm": float(valid_obs.max()),
                "observed_heavy_cell_fraction": float((valid_obs >= HEAVY_24H_MIN_MM).mean()),
                "observed_very_heavy_cell_fraction": float((valid_obs >= VERY_HEAVY_24H_MIN_MM).mean()),
                "raw_gefs_control_rmse_mm": rmse, "raw_gefs_control_bias_mm": bias,
                "CONTROL_MODEL_ELIGIBLE": row_eligibility["CONTROL_MODEL_ELIGIBLE"],
                "FULL_ENSEMBLE_ELIGIBLE": row_eligibility["FULL_ENSEMBLE_ELIGIBLE"],
                "quarantine_reason": row_eligibility["quarantine_reason"],
            })
    write_json(manifest_root / "raw_gefs_control_baseline.json", baseline)
    write_csv(manifest_root / "prototype_case_catalogue.csv", catalogue)

    rainfall_summary = []
    for month in months:
        for product in PRODUCTS:
            for member in ENSEMBLE_MEMBERS:
                rows = [row for row in rainfall_all if row["initialization"].startswith(f"2019{month:02d}") and row["product"] == product and row["member"] == member]
                rainfall_summary.append({"month": f"2019-{month:02d}", "product": product, "member": member, "expected": len(rows), "valid": sum(row["status"] == "PASS" for row in rows), "quarantined": sum(row["status"] != "PASS" for row in rows), "permanent_failures": sum("PERMANENT_FAILURE" in row["reason"] for row in rows)})
    write_csv(manifest_root / "rainfall_completeness.csv", rainfall_summary)
    predictor_summary = []
    for variable in VARIABLES:
        for lead in ATMOSPHERIC_LEADS:
            rows = [row for row in predictor_all if row["variable"] == variable and int(row["lead"]) == lead]
            predictor_summary.append({"variable": variable, "lead": lead, "expected": len(rows), "valid": sum(row["status"] == "PASS" for row in rows), "missing": sum(row["status"] == "BLOCKED" for row in rows), "permanent_failures": sum("PERMANENT_FAILURE" in row["reason"] for row in rows)})
    write_csv(manifest_root / "predictor_completeness.csv", predictor_summary)

    netcdf_retention = finalize_netcdf_retention(
        processed_root=ROOT / "data/processed/phase1e",
        manifest_root=manifest_root,
        authoritative_zarr=processed_path,
    )
    season_outcome = seasonal_admission(item["admission"] for item in monthly.values()).value
    season_manifest = {
        "dataset_version": "varshasetu-gefs12r-imd025-jjas-2000-2019-v1",
        "season": "2019-JJAS", "initializations_expected": 122,
        "initializations_observed": len(initializations), "monthly_admission": monthly,
        "season_admission": season_outcome,
        "rainfall_expected": len(rainfall_all), "rainfall_valid": sum(row["status"] == "PASS" for row in rainfall_all),
        "rainfall_quarantined": sum(row["status"] != "PASS" for row in rainfall_all),
        "atmosphere_expected": len(predictor_all), "atmosphere_valid": sum(row["status"] == "PASS" for row in predictor_all),
        "observation_pairings_expected": 366, "observation_pairings_valid": 366,
        "unique_observation_dates": len(event_rows),
        "eligibility_counts": {tier: sum(bool(row[tier]) for row in eligibility_rows) for tier in ("SOURCE_VALID", "PAIR_VALID", "CONTROL_MODEL_ELIGIBLE", "FULL_ENSEMBLE_ELIGIBLE", "REGIME_ELIGIBLE", "EXTREME_EVENT_ELIGIBLE", "FSS_ELIGIBLE", "REJECTED")},
        "event_inventory": {
            "days": len(event_rows),
            "heavy_days": sum(row["heavy_cell_count"] > 0 for row in event_rows),
            "heavy_grid_cell_events": sum(int(row["heavy_cell_count"]) for row in event_rows),
            "maximum_heavy_area_fraction": max(float(row["heavy_valid_area_fraction"]) for row in event_rows),
            "very_heavy_days": sum(row["very_heavy_cell_count"] > 0 for row in event_rows),
            "very_heavy_grid_cell_events": sum(int(row["very_heavy_cell_count"]) for row in event_rows),
            "maximum_very_heavy_area_fraction": max(float(row["very_heavy_valid_area_fraction"]) for row in event_rows),
            "extremely_heavy_days": sum(row["extremely_heavy_cell_count"] > 0 for row in event_rows),
            "extremely_heavy_grid_cell_events": sum(int(row["extremely_heavy_cell_count"]) for row in event_rows),
            "maximum_extremely_heavy_area_fraction": max(float(row["extremely_heavy_valid_area_fraction"]) for row in event_rows),
            "daily_domain_mean_mm": float(np.mean([row["mean_mm"] for row in event_rows])),
            "season_maximum_mm": float(max(row["max_mm"] for row in event_rows)),
            "daily_p90_mean_mm": float(np.mean([row["p90_mm"] for row in event_rows])),
            "daily_p95_mean_mm": float(np.mean([row["p95_mm"] for row in event_rows])),
        },
        "zarr": {"path": processed_path.relative_to(ROOT).as_posix(), "tree_sha256": tree_sha256(processed_path), "shapes": {"forecast_rain": list(forecast.shape), "observation_rain": list(observation.shape), "valid_mask": list(mask.shape), "atmosphere": list(atmosphere.shape)}},
        "raw_control_baseline": baseline,
        "netcdf_retention": netcdf_retention,
        "training_eligible": False, "regime_labels_created": False, "fss_computed": False,
    }
    write_json(manifest_root / "season_manifest.json", season_manifest)
    print(json.dumps(season_manifest, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
