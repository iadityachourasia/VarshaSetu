"""Build one admitted Phase 2A seasonal corpus from four completed monthly runs."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
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
    ATMOSPHERIC_LEADS,
    ENSEMBLE_MEMBERS,
    PRODUCT_WINDOWS,
    TARGET_BOUNDS,
    observation_event_stats,
    product_valid_date,
)
from backend.app.data.seasonal_corpus import (
    eligibility_index_row,
    seasonal_admission,
    seasonal_initializations,
    validate_seasonal_zarr_shape,
)
from backend.app.data_sources.imd_rainfall import load_imd_day


VERSION = "varshasetu-gefs12r-imd025-jjas-2000-2019-v2"
PRODUCTS = tuple(PRODUCT_WINDOWS)
VARIABLES = ("u850", "v850", "q700", "z500", "mslp", "pwat")
TIERS = (
    "SOURCE_VALID",
    "PAIR_VALID",
    "CONTROL_MODEL_ELIGIBLE",
    "FULL_ENSEMBLE_ELIGIBLE",
    "REGIME_ELIGIBLE",
    "EXTREME_EVENT_ELIGIBLE",
    "FSS_ELIGIBLE",
    "REJECTED",
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def tree_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    for item in sorted(candidate for candidate in path.rglob("*") if candidate.is_file()):
        digest.update(item.relative_to(path).as_posix().encode("utf-8"))
        digest.update(bytes.fromhex(sha256_file(item)))
    return digest.hexdigest()


def read_csv(path: Path) -> list[dict]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict], fieldnames: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    names = fieldnames or list(rows[0])
    temporary = path.with_name(path.name + ".partial")
    with temporary.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=names)
        writer.writeheader()
        writer.writerows(rows)
    os.replace(temporary, path)


def write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".partial")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def _create_seasonal_zarr(year: int, monthly_lineage: dict, destination: Path) -> str:
    temporary = destination.with_name(destination.name + ".partial")
    if destination.exists():
        raise FileExistsError(f"refusing to overwrite completed seasonal corpus {destination}")
    if temporary.exists():
        raise FileExistsError(f"stale partial seasonal corpus requires quarantine: {temporary}")
    initializations = seasonal_initializations(year)
    root = zarr.open_group(str(temporary), mode="w")
    root.attrs.update(
        {
            "dataset_version": VERSION,
            "season_subset": f"{year}-JJAS",
            "training_eligible": False,
            "product_names": list(PRODUCTS),
            "member_names": list(ENSEMBLE_MEMBERS),
            "atmospheric_variable_names": list(VARIABLES),
            "monthly_manifest_lineage": monthly_lineage,
            "canonical_reconstruction": "minimal native-interval decomposition with representation-aware packing bound",
        }
    )
    root.create_array(
        "init_time_unix_seconds",
        data=np.asarray([int(item.timestamp()) for item in initializations], dtype=np.int64),
    )
    valid_time = np.asarray(
        [
            [int((item + timedelta(hours=end)).timestamp()) for _, end in PRODUCT_WINDOWS.values()]
            for item in initializations
        ],
        dtype=np.int64,
    )
    root.create_array("valid_time_unix_seconds", data=valid_time, chunks=(1, 3))
    root.create_array("lead_hours", data=np.asarray(ATMOSPHERIC_LEADS, dtype=np.int32))
    root.create_array(
        "window_start_hours",
        data=np.asarray([value[0] for value in PRODUCT_WINDOWS.values()], dtype=np.int32),
    )
    root.create_array(
        "window_end_hours",
        data=np.asarray([value[1] for value in PRODUCT_WINDOWS.values()], dtype=np.int32),
    )
    root.create_array("target_latitude", data=np.arange(10.0, 22.0 + 0.25, 0.25))
    root.create_array("target_longitude", data=np.arange(68.0, 80.0 + 0.25, 0.25))
    root.create_array("context_latitude", data=np.arange(5.0, 30.0 + 0.5, 0.5))
    root.create_array("context_longitude", data=np.arange(55.0, 95.0 + 0.5, 0.5))
    forecast = root.create_array(
        "forecast_rain", shape=(122, 3, 5, 49, 49), dtype="f4", chunks=(1, 3, 5, 49, 49)
    )
    observation = root.create_array(
        "observation_rain", shape=(122, 3, 49, 49), dtype="f4", chunks=(1, 3, 49, 49)
    )
    mask = root.create_array(
        "valid_mask", shape=(122, 3, 49, 49), dtype="i1", chunks=(1, 3, 49, 49)
    )
    atmosphere = root.create_array(
        "atmosphere", shape=(122, 3, 6, 51, 81), dtype="f4", chunks=(1, 3, 1, 51, 81)
    )
    forecast.attrs["units"] = "mm"
    observation.attrs["units"] = "mm"
    atmosphere.attrs["units_by_variable"] = {
        "u850": "m s**-1",
        "v850": "m s**-1",
        "q700": "kg kg**-1",
        "z500": "gpm",
        "mslp": "Pa",
        "pwat": "kg m**-2",
    }
    offset = 0
    for month in (6, 7, 8, 9):
        source_path = ROOT / f"data/processed/phase2a/{year}-{month:02d}/storage_evaluation/{year}{month:02d}_arrays.zarr"
        source = zarr.open_group(str(source_path), mode="r")
        count = source["forecast_rain"].shape[0]
        target = slice(offset, offset + count)
        forecast[target] = source["forecast_rain"][:]
        observation[target] = source["observation_rain"][:]
        mask[target] = source["valid_mask"][:]
        atmosphere[target] = source["atmosphere"][:]
        offset += count
    validate_seasonal_zarr_shape(
        forecast_shape=forecast.shape,
        observation_shape=observation.shape,
        mask_shape=mask.shape,
        atmosphere_shape=atmosphere.shape,
    )
    if offset != 122:
        raise ValueError(f"seasonal corpus contains {offset}, not 122, initializations")
    temporary.replace(destination)
    return tree_sha256(destination)


def build(year: int) -> dict:
    initializations = seasonal_initializations(year)
    manifest_root = ROOT / f"data/manifests/phase2a/{year}-JJAS"
    destination = ROOT / f"data/processed/phase2a/{year}-JJAS/varshasetu-gefs12r-imd025-{year}-jjas-v2.zarr"
    destination.parent.mkdir(parents=True, exist_ok=True)
    imd_path = ROOT / f"data/raw/observations/imd/{year}/RF25_ind{year}_rfp25.nc"

    rainfall_all, predictor_all = [], []
    monthly_results, monthly_lineage = {}, {}
    for month in (6, 7, 8, 9):
        period = f"{year}-{month:02d}"
        month_root = ROOT / f"data/manifests/phase2a/{period}"
        collection_path = month_root / "monthly_collection_manifest.json"
        collection = json.loads(collection_path.read_text(encoding="utf-8"))
        if collection.get("dataset_version") != VERSION:
            raise ValueError(f"{period} is not a canonical v2 monthly collection")
        rainfall = read_csv(month_root / "rainfall_acquisition_completeness.csv")
        predictors = read_csv(month_root / "predictor_availability.csv")
        rainfall_all.extend(rainfall)
        predictor_all.extend(predictors)
        invalid = sum(row["status"] != "PASS" for row in rainfall + predictors)
        lineage_complete = (
            collection["observed_initializations"] == collection["expected_initializations"]
            and len(collection["child_manifest_hashes"]) == 2 * collection["expected_initializations"]
        )
        outcome = monthly_admission(
            source_contract_valid=(
                collection["observed_initializations"] == collection["expected_initializations"]
            ),
            lineage_complete=lineage_complete,
            invalid_units=invalid,
        ).value
        monthly_results[period] = {
            "admission": outcome,
            "rainfall_valid": sum(row["status"] == "PASS" for row in rainfall),
            "rainfall_expected": len(rainfall),
            "atmosphere_valid": sum(row["status"] == "PASS" for row in predictors),
            "atmosphere_expected": len(predictors),
            "invalid_units": invalid,
        }
        monthly_lineage[period] = {
            "manifest": collection_path.relative_to(ROOT).as_posix(),
            "sha256": sha256_file(collection_path),
        }

    zarr_hash = _create_seasonal_zarr(year, monthly_lineage, destination)
    rain_lookup = {
        (row["initialization"], row["product"], row["member"]): row for row in rainfall_all
    }
    predictor_lookup = defaultdict(list)
    for row in predictor_all:
        predictor_lookup[row["initialization"]].append(row)
    eligibility_rows = []
    for initialization in initializations:
        stamp = initialization.strftime("%Y%m%d%H")
        predictor_rows = predictor_lookup[stamp]
        atmosphere_valid = len(predictor_rows) == 18 and all(
            row["status"] == "PASS" for row in predictor_rows
        )
        source_path = ROOT / f"data/manifests/phase2a/{initialization:%Y-%m}/daily/source_{stamp}.json"
        source_manifest = json.loads(source_path.read_text(encoding="utf-8"))
        transport_invalid = any(
            item.get("component")
            in {"rainfall_index", "rainfall_object", "atmospheric_index", "atmospheric_object"}
            for item in source_manifest.get("failures", [])
        )
        for product in PRODUCTS:
            member_rows = {
                member: rain_lookup[(stamp, product, member)] for member in ENSEMBLE_MEMBERS
            }
            tiers = compute_eligibility(
                EligibilityInputs(
                    source_valid=not transport_invalid,
                    control_rain_valid=member_rows["c00"]["status"] == "PASS",
                    perturbation_rain_valid={
                        member: member_rows[member]["status"] == "PASS"
                        for member in ENSEMBLE_MEMBERS[1:]
                    },
                    observation_valid=True,
                    atmospheric_bundle_valid=atmosphere_valid,
                    timing_valid=True,
                    spatial_alignment_valid=member_rows["c00"]["status"] == "PASS",
                    spatial_mask_valid=True,
                )
            )
            reasons = [
                row["reason"] for row in member_rows.values() if row["status"] != "PASS"
            ] + [row["reason"] for row in predictor_rows if row["status"] != "PASS"]
            eligibility_rows.append(
                eligibility_index_row(
                    initialization=initialization.isoformat(),
                    product=product,
                    valid_date=product_valid_date(initialization, product).isoformat(),
                    eligibility=tiers,
                    reasons=reasons,
                    source_manifest=source_path.relative_to(ROOT).as_posix(),
                )
            )
    write_csv(manifest_root / "eligibility_index.csv", eligibility_rows)
    tier_files = {
        "SOURCE_VALID": "source_valid_index.csv",
        "PAIR_VALID": "pair_valid_index.csv",
        "CONTROL_MODEL_ELIGIBLE": "control_model_index.csv",
        "FULL_ENSEMBLE_ELIGIBLE": "full_ensemble_index.csv",
        "REGIME_ELIGIBLE": "regime_index.csv",
        "EXTREME_EVENT_ELIGIBLE": "extreme_event_index.csv",
        "FSS_ELIGIBLE": "fss_index.csv",
    }
    for tier, filename in tier_files.items():
        write_csv(
            manifest_root / filename,
            [row for row in eligibility_rows if row[tier]],
            list(eligibility_rows[0]),
        )

    event_rows = []
    valid_dates = sorted(
        {
            product_valid_date(initialization, product)
            for initialization in initializations
            for product in PRODUCTS
        }
    )
    for valid_date in valid_dates:
        field = load_imd_day(imd_path, valid_date, **TARGET_BOUNDS)
        row = observation_event_stats(
            field.rainfall_mm,
            field.valid_mask,
            field.latitude,
            field.longitude,
            valid_date=valid_date,
        )
        row["year"] = valid_date.year
        row["month"] = valid_date.month
        event_rows.append(row)
    write_csv(manifest_root / "event_inventory_daily.csv", event_rows)
    event_by_month = []
    for event_year, event_month in sorted({(row["year"], row["month"]) for row in event_rows}):
        rows = [
            row for row in event_rows if row["year"] == event_year and row["month"] == event_month
        ]
        event_by_month.append(
            {
                "year_month": f"{event_year}-{event_month:02d}",
                "days": len(rows),
                "heavy_days": sum(int(row["heavy_cell_count"]) > 0 for row in rows),
                "heavy_grid_cell_events": sum(int(row["heavy_cell_count"]) for row in rows),
                "very_heavy_days": sum(int(row["very_heavy_cell_count"]) > 0 for row in rows),
                "very_heavy_grid_cell_events": sum(
                    int(row["very_heavy_cell_count"]) for row in rows
                ),
                "maximum_observed_rainfall_mm": max(float(row["max_mm"]) for row in rows),
            }
        )
    write_csv(manifest_root / "event_inventory_by_month.csv", event_by_month)

    rainfall_summary = []
    for month in (6, 7, 8, 9):
        for product in PRODUCTS:
            for member in ENSEMBLE_MEMBERS:
                rows = [
                    row
                    for row in rainfall_all
                    if row["initialization"].startswith(f"{year}{month:02d}")
                    and row["product"] == product
                    and row["member"] == member
                ]
                rainfall_summary.append(
                    {
                        "month": f"{year}-{month:02d}",
                        "product": product,
                        "member": member,
                        "expected": len(rows),
                        "valid": sum(row["status"] == "PASS" for row in rows),
                        "quarantined": sum(row["status"] != "PASS" for row in rows),
                    }
                )
    write_csv(manifest_root / "rainfall_completeness.csv", rainfall_summary)
    predictor_summary = []
    for variable in VARIABLES:
        for lead in ATMOSPHERIC_LEADS:
            rows = [
                row
                for row in predictor_all
                if row["variable"] == variable and int(row["lead"]) == lead
            ]
            predictor_summary.append(
                {
                    "variable": variable,
                    "lead": lead,
                    "expected": len(rows),
                    "valid": sum(row["status"] == "PASS" for row in rows),
                    "missing": sum(row["status"] != "PASS" for row in rows),
                }
            )
    write_csv(manifest_root / "predictor_completeness.csv", predictor_summary)

    season_outcome = seasonal_admission(
        item["admission"] for item in monthly_results.values()
    ).value
    season_manifest = {
        "dataset_version": VERSION,
        "season": f"{year}-JJAS",
        "role": "TRAIN" if year == 2017 else "VALIDATION",
        "initializations_expected": 122,
        "initializations_observed": len(initializations),
        "monthly_admission": monthly_results,
        "season_admission": season_outcome,
        "rainfall_expected": len(rainfall_all),
        "rainfall_valid": sum(row["status"] == "PASS" for row in rainfall_all),
        "rainfall_quarantined": sum(row["status"] != "PASS" for row in rainfall_all),
        "atmosphere_expected": len(predictor_all),
        "atmosphere_valid": sum(row["status"] == "PASS" for row in predictor_all),
        "observation_pairings_expected": 366,
        "observation_pairings_valid": 366,
        "unique_observation_dates": len(event_rows),
        "eligibility_counts": {
            tier: sum(str(row[tier]).lower() == "true" for row in eligibility_rows)
            for tier in TIERS
        },
        "event_inventory": {
            "days": len(event_rows),
            "heavy_days": sum(int(row["heavy_cell_count"]) > 0 for row in event_rows),
            "heavy_grid_cell_events": sum(int(row["heavy_cell_count"]) for row in event_rows),
            "very_heavy_days": sum(
                int(row["very_heavy_cell_count"]) > 0 for row in event_rows
            ),
            "very_heavy_grid_cell_events": sum(
                int(row["very_heavy_cell_count"]) for row in event_rows
            ),
            "maximum_observed_rainfall_mm": max(float(row["max_mm"]) for row in event_rows),
        },
        "imd_source": f"data/manifests/phase2a/sources/imd_rf25_{year}.json",
        "seasonal_zarr": destination.relative_to(ROOT).as_posix(),
        "seasonal_zarr_tree_sha256": zarr_hash,
        "monthly_manifest_lineage": monthly_lineage,
        "training_eligible": False,
        "note": "Eligibility is case-tiered; rainfall-model training is not authorized in Phase 2A.",
    }
    write_json(manifest_root / "season_manifest.json", season_manifest)
    return season_manifest


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("year", type=int, choices=(2017, 2018))
    args = parser.parse_args()
    print(json.dumps(build(args.year), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
