"""Hash-sealed, forecast-only 2024 partial-grid research inference.

Run one date first or all 30 June dates. This does not write data/live or
expose an API. A separate scoring script may later pair retained fields with
IMD, using the already frozen protocol.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
from pathlib import Path
from uuid import uuid4

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.app.live.districts import verified_weights  # noqa: E402
from backend.app.live.partial_candidate import MODEL_FIELDS, run_candidate_cycle  # noqa: E402
from backend.app.live.pipeline import FrozenModels  # noqa: E402
from backend.app.live.stored import StoredSource  # noqa: E402

PROTOCOL = ROOT / "data/manifests/research_pilot/partial_grid_inference_protocol_v1.json"
OUT = ROOT / "data/manifests/research_pilot/partial_grid_inference_forecast_result_v1.json"
CACHE = ROOT / "data/processed/partial_grid_candidate_v1/2024"
MIN_FREE = 50 * 1024**3


def sha(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def protocol() -> tuple[dict, str]:
    digest = sha(PROTOCOL)
    if PROTOCOL.with_suffix(".sha256").read_text(encoding="ascii").split()[0] != digest:
        raise ValueError("partial-grid inference protocol hash mismatch")
    rule = json.loads(PROTOCOL.read_text(encoding="utf-8"))
    if rule["status"] != "FROZEN_BEFORE_2024_PARTIAL_MODEL_SCORING" or rule["excluded_years"] != [2025, 2026]:
        raise ValueError("partial-grid inference scope differs")
    return rule, digest


def verify_case(directory: Path, expected_protocol_sha: str) -> dict:
    manifest_path = directory / "manifest.json"
    if manifest_path.with_suffix(".sha256").read_text(encoding="ascii").split()[0] != sha(manifest_path):
        raise ValueError(f"candidate case manifest hash mismatch: {directory.name}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if (manifest["schema"] != "varshasetu-partial-grid-candidate-case-v1" or manifest["cycle"] != directory.name
            or manifest["protocol_sha256"] != expected_protocol_sha or manifest["observation_read"] is not False):
        raise ValueError("candidate case identity differs")
    archive = directory / "fields.npz"
    district_path = directory / "districts.json"
    if sha(archive) != manifest["fields_sha256"] or sha(district_path) != manifest["districts_sha256"]:
        raise ValueError("candidate field or district hash mismatch")
    district_rows = json.loads(district_path.read_text(encoding="utf-8"))
    with np.load(archive, allow_pickle=False) as fields:
        for product in ("day1_24h", "day2_24h", "day3_24h"):
            if manifest["products"][product]["status"] == "REFUSED_BY_FROZEN_MODEL_GATE":
                if district_rows[product] or any(f"{name}_{product}" in fields for name in MODEL_FIELDS) or f"valid_{product}" in fields:
                    raise ValueError("refused candidate lead contains forecast arrays or district values")
                continue
            if manifest["products"][product]["status"] != "READY":
                raise ValueError("unknown candidate lead status")
            mask = fields[f"valid_{product}"].astype(bool)
            if mask.shape != (49, 49) or int(mask.sum()) != manifest["products"][product]["valid_cells"]:
                raise ValueError("candidate mask differs from manifest")
            for name in MODEL_FIELDS:
                array = fields[f"{name}_{product}"]
                if array.shape != mask.shape or not np.isfinite(array[mask]).all() or np.any(array[mask] < 0) or not np.isnan(array[~mask]).all():
                    raise ValueError(f"candidate {name} values or missing cells differ")
                if name.endswith("probability") and np.any(array[mask] > 1):
                    raise ValueError("candidate probability exceeds one")
            if np.any(fields[f"very_heavy_probability_{product}"][mask] > fields[f"heavy_probability_{product}"][mask] + 1e-12):
                raise ValueError("candidate nested probabilities differ")
            rows = district_rows[product]
            if len(rows) != manifest["district_count"] or sum(row["supported"] for row in rows) != manifest["products"][product]["supported_districts"]:
                raise ValueError("candidate district count differs")
            for row in rows:
                if row["supported"] != (row["coverage_fraction"] >= manifest["district_minimum_fraction"]):
                    raise ValueError("candidate district coverage decision differs")
                if not row["supported"] and any(row[f"{name}_mean"] is not None for name in MODEL_FIELDS):
                    raise ValueError("unsupported district has a forecast value")
    return manifest


def run_one(date: str, rule: dict, protocol_sha: str, models: FrozenModels, districts: list[dict],
            weights: np.ndarray, geometry: dict) -> dict:
    directory = CACHE / date
    if directory.exists():
        return verify_case(directory, protocol_sha)
    if shutil.disk_usage(CACHE.parent if CACHE.parent.exists() else ROOT).free < MIN_FREE:
        raise ValueError("50 GiB disk guard failed")
    result = run_candidate_cycle(StoredSource(date), date, models, districts, weights,
                                 regional_minimum=rule["regional_minimum_valid_fraction"],
                                 district_minimum=rule["district_minimum_weighted_valid_fraction"])
    arrays, district_table, products = {}, {}, {}
    for product, block in result["products"].items():
        if block["status"] != "READY":
            district_table[product] = []
            products[product] = {"status": block["status"], "reason": block["reason"],
                                 "strict_passed": block["strict_passed"], "valid_cells": block["valid_cells"],
                                 "invalid_cells": block["invalid_cells"], "valid_fraction": block["valid_cells"] / 2401,
                                 "supported_districts": 0}
            continue
        inferred = block["inference"]
        arrays[f"valid_{product}"] = inferred["valid_mask"].astype(np.uint8)
        for name in MODEL_FIELDS:
            arrays[f"{name}_{product}"] = inferred["fields"][name]
        district_table[product] = block["districts"]
        products[product] = {"status": "READY", "strict_passed": block["strict_passed"], "valid_cells": inferred["valid_cells"],
                             "invalid_cells": inferred["invalid_cells"], "valid_fraction": inferred["valid_fraction"],
                             "supported_districts": sum(row["supported"] for row in block["districts"])}
    directory.parent.mkdir(parents=True, exist_ok=True)
    staging = directory.parent / f".stage-{date}-{uuid4().hex}"
    staging.mkdir(exist_ok=False)
    try:
        np.savez_compressed(staging / "fields.npz", **arrays)
        district_text = json.dumps(district_table, indent=2, sort_keys=True, allow_nan=False) + "\n"
        (staging / "districts.json").write_text(district_text, encoding="utf-8", newline="\n")
        manifest = {"schema": "varshasetu-partial-grid-candidate-case-v1", "cycle": date,
                    "protocol_sha256": protocol_sha, "observation_read": False, "model_inference": True,
                    "model_hashes": result["frozen_models"], "source_selected_message_sha256": [entry["sha256"] for entry in result["sources"]],
                    "geometry": geometry, "district_count": len(districts),
                    "district_minimum_fraction": rule["district_minimum_weighted_valid_fraction"],
                    "products": products, "strict_withheld_reasons": result["withheld_by_strict"],
                    "fields_sha256": sha(staging / "fields.npz"), "districts_sha256": sha(staging / "districts.json"),
                    "meaning": "Forecast-only research candidate; NaN outside valid cells, not an operational or public-warning product"}
        text = json.dumps(manifest, indent=2, sort_keys=True, allow_nan=False) + "\n"
        (staging / "manifest.json").write_text(text, encoding="utf-8", newline="\n")
        (staging / "manifest.sha256").write_text(hashlib.sha256(text.encode("utf-8")).hexdigest() + "  manifest.json\n", encoding="ascii")
        if directory.exists():
            raise ValueError("candidate case was concurrently published")
        staging.rename(directory)
    except Exception:
        shutil.rmtree(staging)
        raise
    return verify_case(directory, protocol_sha)


def seal_year(protocol_sha: str) -> dict:
    rows = []
    for day in range(1, 31):
        date = f"202406{day:02d}"
        path = CACHE / date / "manifest.json"
        if not path.is_file():
            raise ValueError(f"candidate year incomplete: {date}")
        case = verify_case(path.parent, protocol_sha)
        rows.append({"cycle": date, "manifest_sha256": sha(path), "products": case["products"]})
    result = {"schema": "varshasetu-partial-grid-inference-forecast-result-v1", "protocol_sha256": protocol_sha,
              "observation_read": False, "case_count": 30, "lead_count": 90,
              "strict_passing_leads": sum(p["strict_passed"] for row in rows for p in row["products"].values()),
              "regional_eligible_leads": sum(p["valid_fraction"] >= .99 for row in rows for p in row["products"].values()),
              "model_ready_leads": sum(p["status"] == "READY" for row in rows for p in row["products"].values()),
              "model_refused_leads": sum(p["status"] == "REFUSED_BY_FROZEN_MODEL_GATE" for row in rows for p in row["products"].values()),
              "district_values_suppressed_on_ready_leads": sum(188 - p["supported_districts"] for row in rows for p in row["products"].values() if p["status"] == "READY"),
              "cases": rows, "meaning": "Forecast-only, development-validation research candidate; no skill or promotion claim"}
    text = json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n"
    if OUT.exists():
        if OUT.read_text(encoding="utf-8") != text or OUT.with_suffix(".sha256").read_text(encoding="ascii").split()[0] != sha(OUT):
            raise ValueError("sealed candidate forecast result differs")
        return result
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(text)
    OUT.with_suffix(".sha256").write_text(hashlib.sha256(text.encode("utf-8")).hexdigest() + "  " + OUT.name + "\n", encoding="ascii")
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--date", help="one June 2024 date in YYYYMMDD")
    group.add_argument("--all-june-2024", action="store_true")
    args = parser.parse_args()
    rule, protocol_sha = protocol()
    dates = [f"202406{day:02d}" for day in range(1, 31)] if args.all_june_2024 else [args.date]
    if any(date not in {f"202406{day:02d}" for day in range(1, 31)} for date in dates):
        raise ValueError("date outside frozen June 2024 population")
    models = FrozenModels.load()
    districts, weights, geometry = verified_weights()
    for date in dates:
        case = run_one(date, rule, protocol_sha, models, districts, weights, geometry)
        print(json.dumps({"cycle": date, "status": {name: p["status"] for name, p in case["products"].items()},
                          "strict_passed": {name: p["strict_passed"] for name, p in case["products"].items()},
                          "supported_districts": {name: p["supported_districts"] for name, p in case["products"].items()}}), flush=True)
    if args.all_june_2024:
        year = seal_year(protocol_sha)
        print(json.dumps({key: year[key] for key in ("case_count", "lead_count", "strict_passing_leads", "regional_eligible_leads", "model_ready_leads", "model_refused_leads", "district_values_suppressed_on_ready_leads")}))


if __name__ == "__main__":
    main()
