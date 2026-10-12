"""Frozen, development-only paired evaluation of experimental cell masking."""

from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.app.data.accumulation import GriddedAccumulationMessage, reconstruct_minimal_accumulation_window  # noqa: E402
from backend.app.data.accumulation_masked import reconstruct_masked_diagnostic  # noqa: E402
from backend.app.data.monthly_qc import product_valid_date  # noqa: E402
from backend.app.data_sources.imd_rainfall import load_imd_day  # noqa: E402
from backend.app.data_sources.noaa_gefs_monthly import crop_grid, decode_precipitation_message  # noqa: E402
from backend.app.live.districts import verified_weights  # noqa: E402
from backend.app.live.pipeline import LEADS  # noqa: E402

PROTOCOL = ROOT / "data/manifests/research_pilot/partial_cell_development_protocol_v1.json"
OUT = ROOT / "data/manifests/research_pilot/partial_cell_development_result_v1.json"
SOURCE = ROOT / "experiments/recent_historical/phase4f_payload_acquisition_v1/manifests"
IMD = ROOT / "experiments/recent_historical/imd"
RAIN_HOURS = sorted({hour for rule in LEADS.values() for hour in rule["rain_hours"]})


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def checked(path: Path) -> tuple[dict, str]:
    digest = sha(path)
    if path.with_suffix(".sha256").read_text(encoding="ascii").split()[0] != digest:
        raise ValueError(f"hash mismatch: {path}")
    return json.loads(path.read_text(encoding="utf-8")), digest


def load_rain(year: int, cycle: str, files: dict) -> tuple[dict[int, GriddedAccumulationMessage], dict[str, str]]:
    messages, hashes = {}, {}
    for hour in RAIN_HOURS:
        relative = f"data/operational_gefs/v1/{year}/{cycle}/pgrb2sp25/c00_f{hour:03d}_rain.grib2"
        path = ROOT / relative
        payload = path.read_bytes()
        digest = hashlib.sha256(payload).hexdigest()
        receipt = files[relative]
        if digest != receipt["sha256"] or len(payload) != receipt["bytes"]:
            raise ValueError(f"forecast source differs: {relative}")
        accumulation, grid = decode_precipitation_message(payload, member="c00", description="ENS=low-res ctl", source_id=digest)
        if accumulation.end_hour != hour:
            raise ValueError(f"unexpected forecast step: {relative}")
        region = crop_grid(grid, south=10, north=22, west=68, east=80)
        if region.values.shape != (49, 49):
            raise ValueError("regional forecast grid differs")
        messages[hour] = GriddedAccumulationMessage(accumulation.start_hour, accumulation.end_hour,
                                                      region.values, accumulation.source_id, accumulation.packing_quantum_mm)
        hashes[str(hour)] = digest
    return messages, hashes


def paired_counts(forecast: np.ndarray, observed: np.ndarray, eligible: np.ndarray, threshold: float) -> dict:
    f, o = forecast[eligible] >= threshold, observed[eligible] >= threshold
    return {"hits": int(np.sum(f & o)), "misses": int(np.sum(~f & o)),
            "false_alarms": int(np.sum(f & ~o)), "correct_negatives": int(np.sum(~f & ~o))}


def case_measure(forecast: np.ndarray, observed: np.ndarray, valid: np.ndarray, observed_valid: np.ndarray) -> dict:
    paired = valid & observed_valid
    error = forecast[paired] - observed[paired]
    return {"paired_cells": int(paired.sum()), "squared_error_sum": float(error @ error),
            "error_sum": float(error.sum()),
            "events": {str(threshold): paired_counts(forecast, observed, paired, threshold) for threshold in (64.5, 115.6)}}


def year_report(year: int, weights: np.ndarray, protocol: dict) -> dict:
    source, source_hash = checked(SOURCE / f"{year}_source_manifest.json")
    imd_path = IMD / f"RF25_ind{year}_rfp25.nc"
    imd_manifest = json.loads((IMD / f"imd_{year}_manifest.json").read_text(encoding="utf-8"))
    imd_hash = sha(imd_path)
    if imd_hash != imd_manifest["sha256"]:
        raise ValueError(f"IMD {year} reference hash mismatch")
    total_weight = weights.sum(axis=1)
    if not np.all(total_weight > 0):
        raise ValueError("district has no area on the regional grid")
    rows = []
    for day in range(1, 31):
        cycle = f"{year}06{day:02d}"
        initialization = datetime(year, 6, day, tzinfo=timezone.utc)
        rain, hashes = load_rain(year, cycle, source["files"])
        for product, rule in LEADS.items():
            messages = [rain[hour] for hour in rule["rain_hours"]]
            masked = reconstruct_masked_diagnostic(messages, window_start_hour=rule["window"][0], window_end_hour=rule["window"][1])
            try:
                canonical = reconstruct_minimal_accumulation_window(messages, window_start_hour=rule["window"][0], window_end_hour=rule["window"][1])
            except ValueError as error:
                if "negative difference exceeds packing bound" not in str(error):
                    raise
                strict_passed = False
            else:
                strict_passed = True
                if not masked.valid_mask.all() or not np.array_equal(masked.rainfall_mm, canonical.rainfall_mm):
                    raise ValueError(f"masked method differs on strict-pass case: {cycle}/{product}")
            reference = load_imd_day(imd_path, product_valid_date(initialization, product), south=10, north=22, west=68, east=80)
            if (reference.rainfall_mm.shape != (49, 49) or not np.array_equal(reference.latitude, np.linspace(10, 22, 49))
                    or not np.array_equal(reference.longitude, np.linspace(68, 80, 49))):
                raise ValueError("forecast and IMD grids do not align")
            observed, observed_valid = reference.rainfall_mm, reference.valid_mask
            invalid_observed = ~masked.valid_mask & observed_valid
            valid_observed = masked.valid_mask & observed_valid
            district_coverage = (weights @ masked.valid_mask.reshape(-1).astype(float)) / total_weight
            district_supported = district_coverage >= protocol["district_minimum_area_coverage_fraction"]
            rows.append({"cycle": cycle, "product": product, "valid_date": product_valid_date(initialization, product).isoformat(),
                         "strict_passed": strict_passed, "forecast_rain_sha256": {str(h): hashes[str(h)] for h in rule["rain_hours"]},
                         "valid_cells": int(masked.valid_mask.sum()), "invalid_cells": masked.invalid_cells,
                         "reference_valid_cells": int(observed_valid.sum()), "paired_valid_cells": int(valid_observed.sum()),
                         "invalid_with_valid_reference": int(invalid_observed.sum()),
                         "invalid_reference_rain_sum_mm": float(observed[invalid_observed].sum()),
                         "valid_reference_rain_sum_mm": float(observed[valid_observed].sum()),
                         "invalid_reference_events": {str(t): int(np.sum(observed[invalid_observed] >= t)) for t in (64.5, 115.6)},
                         "valid_reference_events": {str(t): int(np.sum(observed[valid_observed] >= t)) for t in (64.5, 115.6)},
                         "district_coverage_min": float(district_coverage.min()),
                         "district_supported_count": int(district_supported.sum()),
                         "district_unsupported_ids": np.flatnonzero(~district_supported).astype(int).tolist(),
                         "raw_on_paired_cells": case_measure(masked.rainfall_mm, observed, masked.valid_mask, observed_valid)})
        print(json.dumps({"cycle": cycle, "completed": day}), flush=True)
    return {"year": year, "role": protocol["years"][str(year)], "forecast_source_manifest_sha256": source_hash,
            "imd_reference_sha256": imd_hash, "case_count": len(rows), "rows": rows}


def main() -> None:
    protocol, protocol_hash = checked(PROTOCOL)
    if OUT.exists() or protocol["status"] != "FROZEN_BEFORE_THIS_PARTIAL_CELL_OBSERVATION_PAIRING":
        raise ValueError("protocol differs or immutable result already exists")
    districts, weights, geometry = verified_weights()
    if len(districts) != weights.shape[0]:
        raise ValueError("district geometry mismatch")
    if protocol["years"] != {"2023": "design_development", "2024": "validation_development"} or protocol["district_minimum_area_coverage_fraction"] != 0.95:
        raise ValueError("partial-cell population or district gate differs from frozen protocol")
    results = [year_report(year, weights, protocol) for year in (2023, 2024)]
    rows = [row for year in results for row in year["rows"]]
    report = {"schema": "varshasetu-partial-cell-development-result-v1", "protocol_sha256": protocol_hash,
              "geometry": geometry, "district_count": len(districts), "source_track": protocol["track"],
              "observation_used_for_scoring": True, "model_inference": False, "changes_canonical_qc": False,
              "year_results": results, "strict_passing_leads": sum(r["strict_passed"] for r in rows),
              "strict_withheld_leads": sum(not r["strict_passed"] for r in rows),
              "masked_leads_with_at_least_99pct_regional_coverage": sum(r["valid_cells"] / 2401 >= 0.99 for r in rows),
              "interpretation": protocol["interpretation"]}
    value = json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + "\n"
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(value)
    OUT.with_suffix(".sha256").write_text(hashlib.sha256(value.encode("utf-8")).hexdigest() + "  " + OUT.name + "\n", encoding="ascii")
    print(json.dumps({key: report[key] for key in ("strict_passing_leads", "strict_withheld_leads", "masked_leads_with_at_least_99pct_regional_coverage")}))


if __name__ == "__main__":
    main()
