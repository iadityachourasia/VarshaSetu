"""Forecast-only projected-probability replay of every June 2024 partial-grid lead."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
import time
from pathlib import Path
from uuid import uuid4

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.app.live.coherent_research import ProjectedFrozenModels  # noqa: E402
from backend.app.live.districts import verified_weights  # noqa: E402
from backend.app.live.partial_candidate import MODEL_FIELDS, run_candidate_cycle  # noqa: E402
from backend.app.live.pipeline import FrozenModels  # noqa: E402
from backend.app.live.stored import StoredSource  # noqa: E402
from scripts import run_partial_grid_candidate as previous  # noqa: E402

PROTOCOL = ROOT / "data/manifests/research_pilot/coherent_partial_grid_protocol_v1.json"
OUT = ROOT / "data/manifests/research_pilot/coherent_partial_grid_forecast_v1.json"
CACHE = ROOT / "data/processed/coherent_partial_grid_v1/2024"
DATES = [f"202406{day:02d}" for day in range(1, 31)]
PRODUCTS = ("day1_24h", "day2_24h", "day3_24h")


def checked_protocol() -> tuple[dict, str]:
    digest = previous.sha(PROTOCOL)
    if PROTOCOL.with_suffix(".sha256").read_text(encoding="ascii").split()[0] != digest:
        raise ValueError("coherent replay protocol hash differs")
    rule = json.loads(PROTOCOL.read_text(encoding="utf-8"))
    if (rule["status"] != "FROZEN_BEFORE_2024_JUNE_FORECAST_REPLAY" or not rule["forecast_only"]
            or rule["reference_read"] or rule["excluded_years"] != [2025, 2026]):
        raise ValueError("coherent replay protocol role differs")
    return rule, digest


def check_prior() -> tuple[dict, str, str]:
    old_rule, old_hash = previous.protocol()
    prior = previous.seal_year(old_hash)
    return prior, previous.sha(previous.OUT), old_hash


def compare_prior(date: str, result: dict, prior_hash: str) -> int:
    old_dir = previous.CACHE / date
    old = previous.verify_case(old_dir, prior_hash)
    compared = 0
    with np.load(old_dir / "fields.npz", allow_pickle=False) as archive:
        for product in PRODUCTS:
            if old["products"][product]["status"] != "READY":
                continue
            current = result["products"][product]
            if current["status"] != "READY":
                raise ValueError(f"previously ready lead became refused: {date} {product}")
            inferred = current["inference"]
            if not np.array_equal(inferred["valid_mask"], archive[f"valid_{product}"].astype(bool)):
                raise ValueError("prior mask changed")
            for field in MODEL_FIELDS:
                if not np.array_equal(inferred["fields"][field], archive[f"{field}_{product}"], equal_nan=True):
                    raise ValueError(f"prior ready {field} changed on {date} {product}")
            if inferred["projection_modified_cells"] != 0:
                raise ValueError("previously ready lead unexpectedly needed projection")
            compared += 1
    return compared


def verify_case(directory: Path, protocol_sha: str, prior_hash: str) -> dict:
    path = directory / "manifest.json"
    if path.with_suffix(".sha256").read_text(encoding="ascii").split()[0] != previous.sha(path):
        raise ValueError("coherent case manifest hash mismatch")
    case = json.loads(path.read_text(encoding="utf-8"))
    if (case["schema"] != "varshasetu-coherent-partial-grid-case-v1" or case["cycle"] != directory.name
            or case["protocol_sha256"] != protocol_sha or case["prior_forecast_sha256"] != prior_hash
            or case["observation_read"] is not False):
        raise ValueError("coherent case identity differs")
    archive_path = directory / "fields.npz"
    district_path = directory / "districts.json"
    if previous.sha(archive_path) != case["fields_sha256"] or previous.sha(district_path) != case["districts_sha256"]:
        raise ValueError("coherent case arrays/districts hash mismatch")
    districts = json.loads(district_path.read_text(encoding="utf-8"))
    with np.load(archive_path, allow_pickle=False) as archive:
        for product in PRODUCTS:
            info = case["products"][product]
            if info["status"] != "READY":
                if districts[product] or any(f"{field}_{product}" in archive for field in MODEL_FIELDS):
                    raise ValueError("refused lead retained arrays or districts")
                continue
            mask = archive[f"valid_{product}"].astype(bool)
            if mask.shape != (49, 49) or int(mask.sum()) != info["valid_cells"]:
                raise ValueError("coherent lead mask differs")
            for field in MODEL_FIELDS:
                values = archive[f"{field}_{product}"]
                if (values.shape != (49, 49) or not np.isfinite(values[mask]).all() or np.any(values[mask] < 0)
                        or not np.isnan(values[~mask]).all() or (field.endswith("probability") and np.any(values[mask] > 1))):
                    raise ValueError(f"coherent {field} field invalid")
            if np.any(archive[f"very_heavy_probability_{product}"][mask] > archive[f"heavy_probability_{product}"][mask]):
                raise ValueError("coherent probability nesting failed")
            if len(districts[product]) != case["district_count"]:
                raise ValueError("coherent district population differs")
            for row in districts[product]:
                if row["supported"] != (row["coverage_fraction"] >= case["district_minimum_fraction"]):
                    raise ValueError("coherent district coverage gate differs")
                if not row["supported"] and any(row[f"{field}_mean"] is not None for field in MODEL_FIELDS):
                    raise ValueError("unsupported district has a value")
    return case


def publish_stage(stage: Path, directory: Path) -> None:
    """Retry only transient Windows access-denied renames; never replace a case."""
    if stage.resolve().parent != CACHE.resolve() or directory.resolve().parent != CACHE.resolve():
        raise ValueError("coherent case publication escaped its cache directory")
    for attempt in range(5):
        if directory.exists():
            raise ValueError("coherent case published concurrently")
        try:
            stage.rename(directory)
            return
        except PermissionError as error:
            if getattr(error, "winerror", None) != 5 or attempt == 4:
                raise
            time.sleep(0.2 * (attempt + 1))


def run_one(date: str, rule: dict, protocol_sha: str, prior_hash: str, old_protocol_sha: str,
            models, districts: list[dict], weights: np.ndarray, geometry: dict) -> dict:
    directory = CACHE / date
    if directory.exists():
        return verify_case(directory, protocol_sha, prior_hash)
    if shutil.disk_usage(ROOT).free < 50 * 1024**3:
        raise ValueError("50 GiB disk guard failed")
    result = run_candidate_cycle(StoredSource(date), date, models, districts, weights,
                                 regional_minimum=rule["regional_minimum_valid_fraction"],
                                 district_minimum=rule["district_minimum_weighted_valid_fraction"])
    compared = compare_prior(date, result, old_protocol_sha)
    arrays, district_table, products = {}, {}, {}
    for product in PRODUCTS:
        block = result["products"][product]
        if block["status"] != "READY":
            district_table[product] = []
            products[product] = {"status": block["status"], "reason": block["reason"],
                                 "strict_passed": block["strict_passed"], "valid_cells": block["valid_cells"],
                                 "invalid_cells": block["invalid_cells"], "projection_modified_cells": 0,
                                 "supported_districts": 0}
            continue
        inferred = block["inference"]
        arrays[f"valid_{product}"] = inferred["valid_mask"].astype(np.uint8)
        for field in MODEL_FIELDS:
            arrays[f"{field}_{product}"] = inferred["fields"][field]
        district_table[product] = block["districts"]
        products[product] = {"status": "READY", "strict_passed": block["strict_passed"],
                             "valid_cells": inferred["valid_cells"], "invalid_cells": inferred["invalid_cells"],
                             "projection_modified_cells": inferred["projection_modified_cells"],
                             "projection_max_gap": inferred["projection_max_gap"],
                             "supported_districts": sum(row["supported"] for row in block["districts"])}
    directory.parent.mkdir(parents=True, exist_ok=True)
    stage = directory.parent / f".stage-{date}-{uuid4().hex}"
    stage.mkdir(exist_ok=False)
    try:
        np.savez_compressed(stage / "fields.npz", **arrays)
        (stage / "districts.json").write_text(json.dumps(district_table, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8", newline="\n")
        case = {"schema": "varshasetu-coherent-partial-grid-case-v1", "cycle": date,
                "protocol_sha256": protocol_sha, "prior_forecast_sha256": prior_hash,
                "observation_read": False, "projection": "symmetric_euclidean_no_refit",
                "model_hashes": result["frozen_models"], "source_selected_message_sha256": [row["sha256"] for row in result["sources"]],
                "geometry": geometry, "district_count": len(districts),
                "district_minimum_fraction": rule["district_minimum_weighted_valid_fraction"],
                "prior_ready_leads_compared": compared, "products": products,
                "fields_sha256": previous.sha(stage / "fields.npz"), "districts_sha256": previous.sha(stage / "districts.json")}
        payload = json.dumps(case, indent=2, sort_keys=True, allow_nan=False) + "\n"
        (stage / "manifest.json").write_text(payload, encoding="utf-8", newline="\n")
        (stage / "manifest.sha256").write_text(hashlib.sha256(payload.encode()).hexdigest() + "  manifest.json\n", encoding="ascii")
        publish_stage(stage, directory)
    except Exception:
        if stage.exists() and stage.resolve().parent == CACHE.resolve():
            shutil.rmtree(stage)
        raise
    return verify_case(directory, protocol_sha, prior_hash)


def seal_year(protocol_sha: str, prior_hash: str) -> dict:
    cases = []
    for date in DATES:
        directory = CACHE / date
        case = verify_case(directory, protocol_sha, prior_hash)
        cases.append({"cycle": date, "manifest_sha256": previous.sha(directory / "manifest.json"),
                      "products": case["products"], "prior_ready_leads_compared": case["prior_ready_leads_compared"]})
    products = [p for case in cases for p in case["products"].values()]
    ready = [p for p in products if p["status"] == "READY"]
    result = {"schema": "varshasetu-coherent-partial-grid-forecast-v1", "protocol_sha256": protocol_sha,
              "prior_forecast_sha256": prior_hash, "observation_read": False, "case_count": len(cases),
              "lead_count": len(products), "ready_leads": len(ready), "refused_leads": len(products) - len(ready),
              "previously_ready_fields_matched": sum(case["prior_ready_leads_compared"] for case in cases),
              "newly_ready_leads": len(ready) - sum(case["prior_ready_leads_compared"] for case in cases),
              "projection_modified_cells": sum(p["projection_modified_cells"] for p in ready),
              "leads_with_projection": sum(p["projection_modified_cells"] > 0 for p in ready),
              "suppressed_district_values": sum(188 - p["supported_districts"] for p in ready),
              "cases": cases, "meaning": "Forecast-only consumed-development replay; no reliability or operational claim"}
    payload = json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n"
    if OUT.exists():
        if OUT.read_text(encoding="utf-8") != payload or OUT.with_suffix(".sha256").read_text(encoding="ascii").split()[0] != previous.sha(OUT):
            raise ValueError("immutable coherent year forecast differs")
    else:
        with OUT.open("x", encoding="utf-8", newline="\n") as stream:
            stream.write(payload)
        OUT.with_suffix(".sha256").write_text(hashlib.sha256(payload.encode()).hexdigest() + "  " + OUT.name + "\n", encoding="ascii")
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--date")
    group.add_argument("--all-june-2024", action="store_true")
    args = parser.parse_args()
    dates = DATES if args.all_june_2024 else [args.date]
    if any(date not in DATES for date in dates):
        raise ValueError("cycle outside frozen June 2024 population")
    rule, protocol_sha = checked_protocol()
    _, prior_hash, old_protocol_sha = check_prior()
    models = ProjectedFrozenModels(FrozenModels.load())
    districts, weights, geometry = verified_weights()
    for date in dates:
        case = run_one(date, rule, protocol_sha, prior_hash, old_protocol_sha, models, districts, weights, geometry)
        print(json.dumps({"cycle": date, "ready": sum(p["status"] == "READY" for p in case["products"].values()),
                          "projection_modified_cells": sum(p["projection_modified_cells"] for p in case["products"].values())}), flush=True)
    if args.all_june_2024:
        result = seal_year(protocol_sha, prior_hash)
        print(json.dumps({k: result[k] for k in ("lead_count", "ready_leads", "refused_leads", "previously_ready_fields_matched", "newly_ready_leads", "projection_modified_cells", "leads_with_projection", "suppressed_district_values")}))


if __name__ == "__main__":
    main()
