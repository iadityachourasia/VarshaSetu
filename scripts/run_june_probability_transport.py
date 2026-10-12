"""No-refit forecast-only June 2024 transport replay for sealed recalibrators."""

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

from backend.app.data.accumulation_masked import reconstruct_masked_diagnostic  # noqa: E402
from backend.app.live import pipeline  # noqa: E402
from backend.app.live.stored import StoredSource  # noqa: E402
from backend.app.ml.coherent_probability import project_nested_probabilities  # noqa: E402
from backend.app.ml.lead_aware_calibration import apply_recalibrator  # noqa: E402
from backend.app.ml.phase2c import probability_features  # noqa: E402
from experiments.recent_historical.phase4i_operational_model_development_v1.probability import predict_logistic  # noqa: E402
from scripts import fit_lead_aware_probability as fit  # noqa: E402
from scripts import run_coherent_partial_grid as old  # noqa: E402

PROTOCOL = ROOT / "data/manifests/research_pilot/june_probability_transport_protocol_v1.json"
OUT = ROOT / "data/manifests/research_pilot/june_probability_transport_forecast_v1.json"
CACHE = ROOT / "data/processed/june_probability_transport_v1/2024"
ARMS = ("global", "lead_aware")
TARGETS = ("heavy", "very_heavy")


def checked(path: Path) -> tuple[dict, str]:
    digest = fit.sha256(path)
    if path.with_suffix(".sha256").read_text(encoding="ascii").split()[0] != digest:
        raise ValueError(f"transport hash sidecar mismatch: {path}")
    return json.loads(path.read_text(encoding="utf-8")), digest


def inputs() -> dict:
    rule, protocol_sha = checked(PROTOCOL)
    if (rule["status"] != "FROZEN_BEFORE_JUNE_2024_NO_REFIT_FORECAST_REPLAY"
            or not rule["forecast_only"] or rule["observation_read"] or rule["excluded_years"] != [2025, 2026]):
        raise ValueError("transport protocol scope differs")
    fit_seal, fit_seal_sha = checked(fit.OUT)
    fit_manifest = fit.verified_cache(fit_seal["protocol_sha256"])
    if fit.sha256(fit.CACHE / "manifest.json") != fit_seal["fit_manifest_sha256"]:
        raise ValueError("lead-aware fit artifact differs from its seal")
    old_rule, old_protocol_sha = old.checked_protocol()
    old_year, old_year_sha = checked(old.OUT)
    if (old_year["protocol_sha256"] != old_protocol_sha or old_year["ready_leads"] != 90
            or old.seal_year(old_protocol_sha, old_year["prior_forecast_sha256"]) != old_year):
        raise ValueError("coherent prior forecast year does not reproduce")
    return {"rule": rule, "protocol_sha256": protocol_sha, "fit_seal_sha256": fit_seal_sha,
            "fit_manifest": fit_manifest, "old_protocol_sha256": old_protocol_sha,
            "old_year": old_year, "old_year_sha256": old_year_sha}


def candidate_fields(masked, atmosphere: dict, product: str, models, fit_manifest: dict,
                     prior_archive) -> tuple[dict, dict]:
    mask = np.asarray(masked.valid_mask, dtype=bool)
    rain = np.asarray(masked.rainfall_mm, dtype=np.float64)
    if (mask.shape != (49, 49) or mask.mean() < 0.99 or not np.isfinite(rain[mask]).all()
            or np.any(rain[mask] < 0) or not np.isnan(rain[~mask]).all()):
        raise ValueError("transport rainfall mask or regional coverage differs")
    if not np.array_equal(mask, prior_archive[f"valid_{product}"].astype(bool)):
        raise ValueError("transport valid-cell mask differs from coherent replay")
    features = pipeline.build_features({product: np.where(mask, rain, 0.0)}, atmosphere)[product]
    X = features["X"][mask.ravel()]
    expected_hour = pipeline.LEADS[product]["atmosphere_hour"]
    if (X.shape != (int(mask.sum()), 22) or not np.isfinite(X).all()
            or not np.array_equal(X[:, 0], rain.ravel()[mask.ravel()].astype(np.float32))
            or not np.all(X[:, -1] == expected_hour)):
        raise ValueError("transport forecast-time feature rows differ")
    output = models._apply_unchecked(X, features["regime"])
    frozen_h, frozen_v = project_nested_probabilities(output["heavy_probability"], output["very_heavy_probability"])
    for name, values in (("M0", output["M0"]), ("M2", output["M2"]), ("M4", output["M4"]),
                         ("heavy_probability", frozen_h), ("very_heavy_probability", frozen_v)):
        if not np.array_equal(np.asarray(values, dtype=np.float64), prior_archive[f"{name}_{product}"][mask]):
            raise ValueError(f"transport changed prior coherent {name} on {product}")
    regime = np.asarray(output["regime_probability"], dtype=np.float64)
    X26 = probability_features(X, output["M2"], np.repeat(regime.reshape(1, 3), len(X), axis=0))
    raw = {}
    for target in TARGETS:
        if (fit_manifest["models"]["lead_aware"][target]["base_score_sha256"] !=
                fit_manifest["selected_base_inputs"][target]["base_probability_sha256"]):
            raise ValueError("transport recalibrator base score provenance differs")
        raw[target] = predict_logistic(X26, models.probability[target]["base"])
    day = np.full(len(X), expected_hour // 24, dtype=np.int8)
    arrays, projection = {}, {}
    for arm in ARMS:
        h = apply_recalibrator(raw["heavy"], day, fit_manifest["models"][arm]["heavy"])
        v = apply_recalibrator(raw["very_heavy"], day, fit_manifest["models"][arm]["very_heavy"])
        bad = v > h
        ph, pv = project_nested_probabilities(h, v)
        projection[arm] = {"modified_cells": int(bad.sum()),
                           "maximum_gap": float(np.max(v[bad] - h[bad])) if bad.any() else 0.0}
        for target, values in (("heavy", ph), ("very_heavy", pv)):
            field = np.full(mask.size, np.nan, dtype=np.float64)
            field[mask.ravel()] = values
            arrays[f"{arm}_{target}_{product}"] = field.reshape(mask.shape)
    arrays[f"valid_{product}"] = mask.astype(np.uint8)
    return arrays, {"valid_cells": int(mask.sum()), "invalid_cells": int((~mask).sum()),
                    "projection": projection}


def verify_case(directory: Path, protocol_sha: str, old_year_sha: str, fit_seal_sha: str) -> dict:
    path = directory / "manifest.json"
    case = json.loads(path.read_text(encoding="utf-8"))
    if (case["schema"] != "varshasetu-june-probability-transport-case-v1"
            or case["cycle"] != directory.name or case["protocol_sha256"] != protocol_sha
            or case["coherent_forecast_sha256"] != old_year_sha
            or case["lead_aware_fit_seal_sha256"] != fit_seal_sha or case["observation_read"] is not False
            or fit.sha256(path) != path.with_suffix(".sha256").read_text(encoding="ascii").split()[0]
            or fit.sha256(directory / "fields.npz") != case["fields_sha256"]):
        raise ValueError("transport case identity or hash differs")
    with np.load(directory / "fields.npz", allow_pickle=False) as archive:
        if len(archive.files) != 15:
            raise ValueError("transport forecast archive field count differs")
        for product in old.PRODUCTS:
            mask = archive[f"valid_{product}"].astype(bool)
            if mask.shape != (49, 49) or int(mask.sum()) != case["products"][product]["valid_cells"]:
                raise ValueError("transport mask differs")
            for arm in ARMS:
                h = archive[f"{arm}_heavy_{product}"]
                v = archive[f"{arm}_very_heavy_{product}"]
                if (h.shape != mask.shape or v.shape != mask.shape or not np.isfinite(h[mask]).all()
                        or not np.isfinite(v[mask]).all() or np.any((h[mask] < 0) | (h[mask] > 1))
                        or np.any((v[mask] < 0) | (v[mask] > 1)) or np.any(v[mask] > h[mask])
                        or not np.isnan(h[~mask]).all() or not np.isnan(v[~mask]).all()):
                    raise ValueError("transport candidate probability field differs")
    return case


def run_one(date: str, context: dict, models) -> dict:
    directory = CACHE / date
    if directory.exists():
        return verify_case(directory, context["protocol_sha256"], context["old_year_sha256"], context["fit_seal_sha256"])
    if shutil.disk_usage(ROOT).free < 50 * 1024**3:
        raise ValueError("50 GiB disk guard failed")
    prior_dir = old.CACHE / date
    prior = old.verify_case(prior_dir, context["old_protocol_sha256"], context["old_year"]["prior_forecast_sha256"])
    decoded = pipeline.decode_cycle(StoredSource(date), date, allow_no_eligible=True)
    arrays, products = {}, {}
    with np.load(prior_dir / "fields.npz", allow_pickle=False) as prior_fields:
        for product, lead in pipeline.LEADS.items():
            if prior["products"][product]["status"] != "READY":
                raise ValueError("coherent prior lead is not ready")
            messages = [decoded["rain_messages"][hour] for hour in lead["rain_hours"]]
            masked = reconstruct_masked_diagnostic(messages, window_start_hour=lead["window"][0],
                                                    window_end_hour=lead["window"][1])
            fields, status = candidate_fields(masked, decoded["atmosphere"], product, models,
                                              context["fit_manifest"], prior_fields)
            arrays.update(fields)
            status["strict_passed"] = prior["products"][product]["strict_passed"]
            status["prior_ready"] = prior["products"][product]["projection_modified_cells"] == 0
            products[product] = status
    CACHE.mkdir(parents=True, exist_ok=True)
    stage = CACHE / f".stage-{date}-{uuid4().hex}"
    stage.mkdir(exist_ok=False)
    try:
        np.savez_compressed(stage / "fields.npz", **arrays)
        manifest = {"schema": "varshasetu-june-probability-transport-case-v1", "cycle": date,
                    "protocol_sha256": context["protocol_sha256"],
                    "coherent_forecast_sha256": context["old_year_sha256"],
                    "coherent_case_sha256": fit.sha256(prior_dir / "manifest.json"),
                    "lead_aware_fit_seal_sha256": context["fit_seal_sha256"],
                    "frozen_model_hashes": models.hashes,
                    "source_selected_message_sha256": [row["sha256"] for row in decoded["sources"]],
                    "observation_read": False, "products": products,
                    "fields_sha256": fit.sha256(stage / "fields.npz")}
        payload = json.dumps(manifest, indent=2, sort_keys=True, allow_nan=False) + "\n"
        (stage / "manifest.json").write_text(payload, encoding="utf-8", newline="\n")
        (stage / "manifest.sha256").write_text(hashlib.sha256(payload.encode()).hexdigest() + "  manifest.json\n", encoding="ascii")
        if stage.resolve().parent != CACHE.resolve() or directory.resolve().parent != CACHE.resolve():
            raise ValueError("transport publication escaped cache")
        for attempt in range(5):
            if directory.exists():
                raise ValueError("transport case published concurrently")
            try:
                stage.rename(directory)
                break
            except PermissionError as error:
                if getattr(error, "winerror", None) != 5 or attempt == 4:
                    raise
                time.sleep(0.2 * (attempt + 1))
    except Exception:
        if stage.exists() and stage.resolve().parent == CACHE.resolve():
            shutil.rmtree(stage)
        raise
    return verify_case(directory, context["protocol_sha256"], context["old_year_sha256"], context["fit_seal_sha256"])


def seal_year(context: dict) -> dict:
    cases = []
    for date in old.DATES:
        directory = CACHE / date
        case = verify_case(directory, context["protocol_sha256"], context["old_year_sha256"], context["fit_seal_sha256"])
        cases.append({"cycle": date, "manifest_sha256": fit.sha256(directory / "manifest.json"),
                      "products": case["products"]})
    products = [p for case in cases for p in case["products"].values()]
    if len(products) != 90:
        raise ValueError("transport year is not complete")
    result = {"schema": "varshasetu-june-probability-transport-forecast-v1",
              "protocol_sha256": context["protocol_sha256"],
              "coherent_forecast_sha256": context["old_year_sha256"],
              "lead_aware_fit_seal_sha256": context["fit_seal_sha256"],
              "observation_read": False, "cycle_count": 30, "lead_count": 90,
              "prior_ready_leads": sum(p["prior_ready"] for p in products),
              "newly_ready_leads": sum(not p["prior_ready"] for p in products),
              "projection_modified_cells": {arm: sum(p["projection"][arm]["modified_cells"] for p in products)
                                            for arm in ARMS},
              "cases": cases,
              "meaning": "No-refit forecast-only transport; consumed 2024 development population, not independent reliability"}
    payload = json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n"
    if OUT.exists():
        if OUT.read_text(encoding="utf-8") != payload or OUT.with_suffix(".sha256").read_text(encoding="ascii").split()[0] != fit.sha256(OUT):
            raise ValueError("immutable transport forecast seal differs")
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
    dates = old.DATES if args.all_june_2024 else [args.date]
    if any(date not in old.DATES for date in dates):
        raise ValueError("transport date outside June 2024")
    context = inputs()
    models = pipeline.FrozenModels.load()
    for date in dates:
        case = run_one(date, context, models)
        print(json.dumps({"cycle": date, "ready_leads": len(case["products"]),
                          "lead_aware_projected_cells": sum(p["projection"]["lead_aware"]["modified_cells"]
                                                            for p in case["products"].values())}), flush=True)
    if args.all_june_2024:
        result = seal_year(context)
        print(json.dumps({key: result[key] for key in ("lead_count", "prior_ready_leads", "newly_ready_leads", "projection_modified_cells")}))


if __name__ == "__main__":
    main()
