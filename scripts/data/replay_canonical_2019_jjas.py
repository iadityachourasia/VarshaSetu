"""Cache-only Phase 1F replay of both rainfall reconstruction methods."""

from __future__ import annotations

import csv
import hashlib
import json
import sys
from collections import Counter, defaultdict
from dataclasses import asdict
from datetime import timedelta
from pathlib import Path

import numpy as np
import zarr

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.app.data.accumulation import (
    GriddedAccumulationMessage,
    reconstruct_accumulation_window,
    reconstruct_minimal_accumulation_window,
)
from backend.app.data.corpus_policy import EligibilityInputs, compute_eligibility
from backend.app.data.monthly_qc import ENSEMBLE_MEMBERS, PRODUCT_WINDOWS, product_valid_date
from backend.app.data.seasonal_corpus import (
    eligibility_index_row,
    raw_control_verification,
    seasonal_initializations,
    validate_seasonal_zarr_shape,
)
from backend.app.data_sources.noaa_gefs_monthly import crop_grid, decode_precipitation_message


VERSION = "varshasetu-gefs12r-imd025-jjas-2000-2019-v2"
PRODUCTS = tuple(PRODUCT_WINDOWS)
MANIFEST_ROOT = ROOT / "data/manifests/phase1f/2019-JJAS"
V1_ROOT = ROOT / "data/manifests/phase1e/2019-JJAS"
V1_ZARR = ROOT / "data/processed/phase1e/2019-JJAS/varshasetu-gefs12r-imd025-2019-jjas-v1.zarr"
V2_ZARR = ROOT / "data/processed/phase1f/2019-JJAS/varshasetu-gefs12r-imd025-2019-jjas-v2.zarr"
TARGET_BOUNDS = {"south": 10.0, "north": 22.0, "west": 68.0, "east": 80.0}


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


def write_csv(path: Path, rows: list[dict], fieldnames: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    names = fieldnames or list(rows[0])
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=names)
        writer.writeheader()
        writer.writerows(rows)


def write_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def truth(value: str | bool) -> bool:
    return value is True or str(value).lower() == "true"


def decode_member(source_manifest: dict, member: str) -> tuple[list[GriddedAccumulationMessage], list[dict]]:
    rainfall_object = next(item for item in source_manifest["rainfall_objects"] if item["member"] == member)
    chunk_record = rainfall_object["selected_chunk"]
    chunk_path = ROOT / chunk_record["path"]
    if not chunk_path.is_file():
        raise FileNotFoundError(f"cache-only replay missing {chunk_path}")
    if chunk_path.stat().st_size != chunk_record["byte_size"] or sha256_file(chunk_path) != chunk_record["sha256"]:
        raise ValueError(f"cached source identity mismatch: {chunk_path}")
    chunk = chunk_path.read_bytes()
    first_byte = rainfall_object["messages"][0]["byte_range"][0]
    decoded_messages, inventory = [], []
    for record in rainfall_object["messages"]:
        start, end = record["byte_range"]
        payload = chunk[start - first_byte : end - first_byte + 1]
        source_id = f"GEFS:{source_manifest['initialization_time_utc']}:{member}:{record['message_number']}"
        accumulation, decoded = decode_precipitation_message(
            payload, member=member, description=record["description"], source_id=source_id
        )
        cropped = crop_grid(decoded, **TARGET_BOUNDS)
        decoded_messages.append(
            GriddedAccumulationMessage(
                accumulation.start_hour, accumulation.end_hour, cropped.values,
                accumulation.source_id, accumulation.packing_quantum_mm,
            )
        )
        metadata = decoded.metadata
        inventory.append({
            "initialization": source_manifest["initialization_time_utc"],
            "member": member,
            "message_number": record["message_number"],
            "source_id": source_id,
            "startStep": accumulation.start_hour,
            "endStep": accumulation.end_hour,
            "stepRange": metadata["step_range"],
            "stepType": metadata["step_type"],
            "typeOfStatisticalProcessing": metadata["type_of_statistical_processing"],
            "numberOfTimeRanges": metadata["number_of_time_ranges"],
            "lengthOfTimeRange": metadata["length_of_time_range"],
            "indicatorOfUnitForTimeRange": metadata["indicator_of_unit_for_time_range"],
            "typeOfTimeIncrement": metadata["type_of_time_increment"],
            "packingType": metadata["packing_type"],
            "bitsPerValue": metadata["bits_per_value"],
            "referenceValue": metadata["reference_value"],
            "binaryScaleFactor": metadata["binary_scale_factor"],
            "decimalScaleFactor": metadata["decimal_scale_factor"],
            "packingQuantumMm": accumulation.packing_quantum_mm,
            "packingErrorKey": metadata["packing_error"],
            "sourceChunk": chunk_record["path"],
            "sourceChunkSha256": chunk_record["sha256"],
        })
    return decoded_messages, inventory


def old_result(messages, start, end):
    try:
        result = reconstruct_accumulation_window(
            messages, window_start_hour=start, window_end_hour=end,
            negative_tolerance_mm=0.1,
        )
        return result, "PASS", ""
    except Exception as exc:
        return None, "FAIL", f"{type(exc).__name__}: {exc}"


def method_diagnostics(messages, start, end, *, minimal: bool) -> dict:
    """Audit every intermediate without changing either method's admission path."""
    by_range = {(item.start_hour, item.end_hour): item for item in messages}
    segments = []
    if minimal:
        base = start - 3
        segments.append((by_range[(base, start + 3)], by_range[(base, start)]))
        cursor = start + 3
        while cursor < end - 3:
            segments.append((by_range[(cursor, cursor + 6)], None))
            cursor += 6
        segments.append((by_range[(end - 3, end)], None))
    else:
        for left in range(start, end, 3):
            direct = by_range.get((left, left + 3))
            if direct is not None:
                segments.append((direct, None))
            else:
                pair = next(
                    (by_range[(base, left + 3)], by_range[(base, left)])
                    for base in range(left)
                    if (base, left + 3) in by_range and (base, left) in by_range
                )
                segments.append(pair)
    raw_parts, normalized_parts = [], []
    negative_count = packing_violations = policy_violation_count = normalized_count = 0
    for total, prefix in segments:
        if prefix is None:
            raw = total.values_mm.copy()
            bound = 0.0
        else:
            raw = total.values_mm - prefix.values_mm
            bound = (total.packing_quantum_mm + prefix.packing_quantum_mm) / 2.0
        negative = raw < 0
        violations = raw < -(bound + 1e-12)
        admission_bound = bound if minimal else min(0.1, bound)
        policy_violations = raw < -(admission_bound + 1e-12)
        negative_count += int(negative.sum())
        packing_violations += int(violations.sum())
        normalized = raw.copy()
        admissible = negative & ~policy_violations
        normalized_count += int(admissible.sum())
        normalized[admissible] = 0
        raw_parts.append(raw)
        normalized_parts.append(normalized)
        policy_violation_count += int(policy_violations.sum())
    raw_final = np.sum(np.stack(raw_parts), axis=0)
    normalized_final = np.sum(np.stack(normalized_parts), axis=0)
    return {
        "subtraction_count": sum(prefix is not None for _, prefix in segments),
        "segment_count": len(segments),
        "negative_intermediate_cells": negative_count,
        "packing_bound_violations": packing_violations,
        "admission_policy_violations": policy_violation_count,
        "justified_normalized_cells": normalized_count,
        "raw_final_negative_cells": int((raw_final < 0).sum()),
        "normalized_final_negative_cells": int((normalized_final < 0).sum()),
        "raw_final_sha256": hashlib.sha256(raw_final.tobytes()).hexdigest(),
        "normalized_final_sha256": hashlib.sha256(normalized_final.tobytes()).hexdigest(),
    }


def explicit_minimal_formula(messages, start, end) -> tuple[np.ndarray | None, str, str]:
    by_range = {(item.start_hour, item.end_hour): item for item in messages}
    base = start - 3
    total, prefix = by_range[(base, start + 3)], by_range[(base, start)]
    bound = (total.packing_quantum_mm + prefix.packing_quantum_mm) / 2.0
    first = total.values_mm - prefix.values_mm
    if (first < -(bound + 1e-12)).any():
        return None, "FAIL", f"independent unavoidable difference exceeds {bound} mm bound"
    first = first.copy()
    first[first < 0] = 0
    parts = [first]
    cursor = start + 3
    while cursor < end - 3:
        parts.append(by_range[(cursor, cursor + 6)].values_mm)
        cursor += 6
    parts.append(by_range[(end - 3, end)].values_mm)
    return np.sum(np.stack(parts), axis=0), "PASS", ""


def choose_verification_stamps(observation, mask, initializations) -> dict[str, str]:
    means = []
    for index, initialization in enumerate(initializations):
        values = []
        for product_index in range(3):
            valid = mask[index, product_index].astype(bool)
            values.append(float(np.mean(observation[index, product_index][valid])))
        means.append((float(np.mean(values)), initialization.strftime("%Y%m%d%H")))
    selected = {
        min(means)[1]: "dry_observation_extreme",
        max(means)[1]: "wet_observation_extreme",
        "2019060100": "june_boundary",
        "2019072200": "july22",
        "2019093000": "september_boundary",
    }
    for _, stamp in sorted(means):
        if len(selected) >= 5:
            break
        selected[stamp] = "deterministic_fill"
    return dict(sorted(selected.items()))


def main() -> None:
    initializations = seasonal_initializations(2019)
    v1 = zarr.open_group(str(V1_ZARR), mode="r")
    observation = np.asarray(v1["observation_rain"][:])
    mask = np.asarray(v1["valid_mask"][:], dtype=np.uint8)
    atmosphere = np.asarray(v1["atmosphere"][:])
    init_time = np.asarray(v1["init_time_unix_seconds"][:], dtype=np.int64)
    old_eligibility_rows = read_csv(V1_ROOT / "eligibility_index.csv")
    old_eligibility = {(row["initialization"], row["product"]): row for row in old_eligibility_rows}
    verification_roles = choose_verification_stamps(observation, mask, initializations)
    verification_stamps = set(verification_roles)

    forecast = np.full((122, 3, 5, 49, 49), np.nan, dtype=np.float64)
    replay_rows, inventory_rows, comparison_values, independent_rows = [], [], [], []
    validity: dict[tuple[str, str, str], bool] = {}
    formulas: dict[str, set[str]] = defaultdict(set)
    for init_index, initialization in enumerate(initializations):
        stamp = initialization.strftime("%Y%m%d%H")
        source_path = ROOT / f"data/manifests/phase1e/{initialization:%Y-%m}/daily/source_{stamp}.json"
        source_manifest = json.loads(source_path.read_text(encoding="utf-8"))
        for member_index, member in enumerate(ENSEMBLE_MEMBERS):
            messages, inventory = decode_member(source_manifest, member)
            inventory_rows.extend(inventory)
            for product_index, (product, (start, end)) in enumerate(PRODUCT_WINDOWS.items()):
                old, old_status, old_reason = old_result(messages, start, end)
                try:
                    new = reconstruct_minimal_accumulation_window(
                        messages, window_start_hour=start, window_end_hour=end
                    )
                    forecast[init_index, product_index, member_index] = new.rainfall_mm
                    new_status, new_reason = "PASS", ""
                    validity[(stamp, product, member)] = True
                    formula = " + ".join(
                        (
                            f"({item.source_ids[0]} - {item.source_ids[1]})"
                            if item.operation == "nested_interval_difference"
                            else item.source_ids[0]
                        )
                        for item in new.segments
                    )
                    formulas[product].add(
                        " + ".join(
                            f"({item.start_hour}-{item.end_hour})[{item.operation}]"
                            for item in new.segments
                        )
                    )
                except Exception as exc:
                    new = None
                    new_status, new_reason = "FAIL", f"{type(exc).__name__}: {exc}"
                    validity[(stamp, product, member)] = False
                    formula = ""
                if old is not None and new is not None:
                    difference = new.rainfall_mm - old.rainfall_mm
                    comparison_values.append(np.abs(difference).ravel())
                    comparison_max = float(np.max(np.abs(difference)))
                    comparison_mean = float(np.mean(np.abs(difference)))
                else:
                    comparison_max = comparison_mean = ""
                replay_rows.append({
                    "initialization": stamp, "month": f"2019-{initialization.month:02d}",
                    "product": product, "member": member,
                    "method_a_status": old_status, "method_a_reason": old_reason,
                    "method_b_status": new_status, "method_b_reason": new_reason,
                    "method_b_subtractions": new.subtraction_count if new else "",
                    "method_b_segments": len(new.segments) if new else "",
                    "method_b_normalized_negative_count": new.normalized_negative_count if new else "",
                    "method_b_minimum_normalized_negative_mm": new.minimum_normalized_negative_mm if new else "",
                    "method_b_formula": formula,
                    "both_pass_max_abs_difference_mm": comparison_max,
                    "both_pass_mean_abs_difference_mm": comparison_mean,
                    "source_manifest": source_path.relative_to(ROOT).as_posix(),
                    "source_manifest_sha256": sha256_file(source_path),
                })
                if stamp in verification_stamps and member == "c00":
                    explicit, independent_status, independent_reason = explicit_minimal_formula(
                        messages, start, end
                    )
                    status_agrees = independent_status == new_status
                    max_difference = (
                        float(np.max(np.abs(explicit - new.rainfall_mm)))
                        if explicit is not None and new is not None else ""
                    )
                    independent_rows.append({
                        "initialization": stamp, "product": product, "member": member,
                        "selection_role": verification_roles[stamp],
                        "algorithm_status": new_status,
                        "independent_status": independent_status,
                        "independent_reason": independent_reason,
                        "status_agrees": status_agrees,
                        "independent_formula_max_abs_difference_mm": max_difference,
                        "nonnegative": bool((new.rainfall_mm >= 0).all()) if new else "",
                        "subtractions": new.subtraction_count if new else "",
                        "segments": len(new.segments) if new else "",
                    })
        print(f"replayed {stamp}", flush=True)

    validate_seasonal_zarr_shape(
        forecast_shape=forecast.shape, observation_shape=observation.shape,
        mask_shape=mask.shape, atmosphere_shape=atmosphere.shape,
    )
    if np.isnan(forecast).any():
        print(f"warning: {np.isnan(forecast).sum()} forecast cells remain quarantined", flush=True)

    eligibility_rows = []
    for initialization in initializations:
        stamp = initialization.strftime("%Y%m%d%H")
        iso = initialization.isoformat()
        for product in PRODUCTS:
            previous = old_eligibility[(iso, product)]
            control_valid = validity[(stamp, product, "c00")]
            perturb = {member: validity[(stamp, product, member)] for member in ENSEMBLE_MEMBERS[1:]}
            tiers = compute_eligibility(EligibilityInputs(
                source_valid=truth(previous["SOURCE_VALID"]),
                control_rain_valid=control_valid,
                perturbation_rain_valid=perturb,
                observation_valid=True,
                atmospheric_bundle_valid=truth(previous["REGIME_ELIGIBLE"]),
                timing_valid=True,
                spatial_alignment_valid=control_valid,
                spatial_mask_valid=True,
            ))
            reasons = [
                row["method_b_reason"] for row in replay_rows
                if row["initialization"] == stamp and row["product"] == product
                and row["method_b_status"] != "PASS"
            ]
            eligibility_rows.append(eligibility_index_row(
                initialization=iso, product=product,
                valid_date=product_valid_date(initialization, product).isoformat(),
                eligibility=tiers, reasons=reasons,
                source_manifest=f"data/manifests/phase1e/{initialization:%Y-%m}/daily/source_{stamp}.json",
            ))

    MANIFEST_ROOT.mkdir(parents=True, exist_ok=True)
    write_csv(MANIFEST_ROOT / "interval_inventory.csv", inventory_rows)
    write_csv(MANIFEST_ROOT / "reconstruction_replay.csv", replay_rows)
    write_csv(MANIFEST_ROOT / "independent_verification.csv", independent_rows)
    write_csv(MANIFEST_ROOT / "eligibility_index.csv", eligibility_rows)
    for filename, tier in {
        "control_model_index.csv": "CONTROL_MODEL_ELIGIBLE",
        "full_ensemble_index.csv": "FULL_ENSEMBLE_ELIGIBLE",
        "regime_index.csv": "REGIME_ELIGIBLE",
        "extreme_event_index.csv": "EXTREME_EVENT_ELIGIBLE",
        "fss_index.csv": "FSS_ELIGIBLE",
    }.items():
        write_csv(MANIFEST_ROOT / filename, [row for row in eligibility_rows if row[tier]], list(eligibility_rows[0]))

    baseline = {}
    for product_index, product in enumerate(PRODUCTS):
        eligible = np.asarray([
            truth(row["CONTROL_MODEL_ELIGIBLE"])
            for row in eligibility_rows if row["product"] == product
        ])
        baseline[product] = raw_control_verification(
            forecast[:, product_index, 0], observation[:, product_index],
            mask[:, product_index].astype(bool) & eligible[:, None, None],
        )
    write_json(MANIFEST_ROOT / "raw_gefs_control_baseline.json", baseline)

    differences = np.concatenate(comparison_values) if comparison_values else np.asarray([])
    comparison = {
        "both_pass_cases": sum(row["method_a_status"] == row["method_b_status"] == "PASS" for row in replay_rows),
        "cell_count": int(differences.size),
        "mean_absolute_difference_mm": float(np.mean(differences)),
        "maximum_absolute_difference_mm": float(np.max(differences)),
        "percentiles_mm": {str(q): float(np.percentile(differences, q)) for q in (50, 90, 95, 99)},
    }
    write_json(MANIFEST_ROOT / "method_comparison.json", comparison)

    V2_ZARR.parent.mkdir(parents=True, exist_ok=True)
    root = zarr.open_group(str(V2_ZARR), mode="w")
    root.attrs.update(dict(v1.attrs))
    root.attrs.update({
        "dataset_version": VERSION,
        "reconstruction_method": "metadata-derived exact cover minimizing (subtractions, segments)",
        "packing_negative_policy": "normalize only within half-sum source packing quantum bound",
        "supersedes_for_future_training": v1.attrs["dataset_version"],
        "training_eligible": False,
    })
    for name in (
        "init_time_unix_seconds", "valid_time_unix_seconds", "lead_hours",
        "window_start_hours", "window_end_hours", "target_latitude",
        "target_longitude", "context_latitude", "context_longitude",
    ):
        root.create_array(name, data=np.asarray(v1[name][:]))
    root.create_array("forecast_rain", data=forecast, chunks=(1, 3, 5, 49, 49)).attrs["units"] = "mm"
    root.create_array("observation_rain", data=observation, chunks=(1, 3, 49, 49)).attrs["units"] = "mm"
    root.create_array("valid_mask", data=mask, chunks=(1, 3, 49, 49))
    root.create_array("atmosphere", data=atmosphere, chunks=(1, 3, 1, 51, 81))

    by_month = []
    for month in (6, 7, 8, 9):
        for product in PRODUCTS:
            rows = [row for row in replay_rows if row["month"] == f"2019-{month:02d}" and row["product"] == product]
            by_month.append({
                "month": f"2019-{month:02d}", "product": product,
                "expected": len(rows),
                "method_a_pass": sum(row["method_a_status"] == "PASS" for row in rows),
                "method_b_pass": sum(row["method_b_status"] == "PASS" for row in rows),
                "method_b_quarantined": sum(row["method_b_status"] != "PASS" for row in rows),
            })
    write_csv(MANIFEST_ROOT / "coverage_by_month_product.csv", by_month)
    old_counts = {tier: sum(truth(row[tier]) for row in old_eligibility_rows) for tier in old_eligibility_rows[0] if tier.isupper()}
    new_counts = {tier: sum(truth(row[tier]) for row in eligibility_rows) for tier in eligibility_rows[0] if tier.isupper()}
    season_manifest = {
        "dataset_version": VERSION,
        "season": "2019-JJAS",
        "cache_only": True,
        "network_calls": 0,
        "source_cases": len(replay_rows),
        "interval_inventory_rows": len(inventory_rows),
        "method_a": {
            "accepted": sum(row["method_a_status"] == "PASS" for row in replay_rows),
            "quarantined": sum(row["method_a_status"] != "PASS" for row in replay_rows),
        },
        "method_b": {
            "accepted": sum(row["method_b_status"] == "PASS" for row in replay_rows),
            "quarantined": sum(row["method_b_status"] != "PASS" for row in replay_rows),
            "subtraction_counts": dict(Counter(str(row["method_b_subtractions"]) for row in replay_rows)),
            "formulas_by_product": {key: sorted(value) for key, value in formulas.items()},
        },
        "old_eligibility_counts": old_counts,
        "new_eligibility_counts": new_counts,
        "method_comparison": comparison,
        "independent_verification": {
            "selected_initializations": sorted(verification_stamps),
            "cases": len(independent_rows),
            "all_statuses_agree": all(row["status_agrees"] for row in independent_rows),
            "all_accepted_exact": all(
                row["independent_formula_max_abs_difference_mm"] in {"", 0}
                for row in independent_rows
            ),
            "all_accepted_nonnegative": all(
                row["nonnegative"] in {"", True} for row in independent_rows
            ),
        },
        "july22": [row for row in replay_rows if row["initialization"] == "2019072200" and row["member"] in {"c00", "p01", "p04"}],
        "raw_control_baseline": baseline,
        "zarr": {
            "path": V2_ZARR.relative_to(ROOT).as_posix(),
            "tree_sha256": tree_sha256(V2_ZARR),
            "shapes": {
                "forecast_rain": list(forecast.shape), "observation_rain": list(observation.shape),
                "valid_mask": list(mask.shape), "atmosphere": list(atmosphere.shape),
            },
        },
        "v1_preserved": {
            "manifest": V1_ROOT.joinpath("season_manifest.json").relative_to(ROOT).as_posix(),
            "manifest_sha256": sha256_file(V1_ROOT / "season_manifest.json"),
            "zarr_tree_sha256": tree_sha256(V1_ZARR),
        },
        "training_eligible": False,
        "regime_labels_created": False,
        "fss_computed": False,
    }
    write_json(MANIFEST_ROOT / "season_manifest.json", season_manifest)
    print(json.dumps(season_manifest, indent=2, sort_keys=True), flush=True)


if __name__ == "__main__":
    main()
