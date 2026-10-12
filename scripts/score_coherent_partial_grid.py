"""Descriptive 2024 IMD pairing after the coherent forecast-only replay seal."""

from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.app.data.monthly_qc import product_valid_date  # noqa: E402
from backend.app.data_sources.imd_rainfall import load_imd_day  # noqa: E402
from backend.app.ml.phase2c import fss_many, probability_metrics  # noqa: E402
from scripts import run_coherent_partial_grid as forecast  # noqa: E402
from scripts import run_partial_grid_candidate as prior_forecast  # noqa: E402
from scripts import run_partial_cell_development as prior_imd  # noqa: E402
from scripts.score_partial_grid_candidate import aggregate, metrics  # noqa: E402

PROTOCOL = ROOT / "data/manifests/research_pilot/coherent_partial_grid_score_protocol_v1.json"
OUT = ROOT / "data/manifests/research_pilot/coherent_partial_grid_score_v1.json"
IMD = ROOT / "experiments/recent_historical/imd/RF25_ind2024_rfp25.nc"
SELECTION = ROOT / "experiments/recent_historical/phase4i_operational_model_development_v1/final_freeze/model_selection_freeze.json"


def checked(path: Path) -> tuple[dict, str]:
    digest = prior_forecast.sha(path)
    if path.with_suffix(".sha256").read_text(encoding="ascii").split()[0] != digest:
        raise ValueError(f"evidence hash mismatch: {path}")
    return json.loads(path.read_text(encoding="utf-8")), digest


def verified_protocol() -> tuple[dict, str]:
    rule, digest = checked(PROTOCOL)
    if (rule["status"] != "FROZEN_AFTER_FORECAST_SEAL_BEFORE_IMD_PAIRING"
            or rule["excluded_years"] != [2025, 2026]):
        raise ValueError("coherent score protocol role differs")
    from experiments.recent_historical.phase4j_operational_final_test_v1.governance import READY_SHA
    readiness_path = SELECTION.parent / "FINAL_TEST_READY.json"
    if prior_forecast.sha(readiness_path) != READY_SHA:
        raise ValueError("frozen readiness record hash mismatch")
    readiness = json.loads(readiness_path.read_text(encoding="utf-8"))
    if prior_forecast.sha(SELECTION) != readiness["model_selection_freeze_sha256"]:
        raise ValueError("frozen model-selection hash mismatch")
    selection = json.loads(SELECTION.read_text(encoding="utf-8"))
    for name in ("heavy", "very_heavy"):
        if (selection[name]["threshold"] != rule["probability_decision_thresholds"][name]
                or selection[name]["bss_reference_2023"] != rule["climatology_2023"][name]):
            raise ValueError("frozen threshold or training climatology differs")
    return rule, digest


def score_group(group: list[dict], rule: dict) -> dict:
    if not group:
        return {"case_count": 0, "reason": "no paired cases"}
    result = {"case_count": len(group), "initialization_count": len({case["cycle"] for case in group}),
              "paired_cells": sum(case["cell_count"] for case in group), "deterministic": aggregate(group),
              "probability": {}, "heavy_fss_3x3": {}}
    for name in ("heavy", "very_heavy"):
        y = np.concatenate([case[f"{name}_label"] for case in group])
        p = np.concatenate([case[f"{name}_probability"] for case in group])
        cutoff = rule["probability_decision_thresholds"][name]
        climatology = rule["climatology_2023"][name]
        score = probability_metrics(y, p, cutoff, climatology)
        predicted_rate = float(np.mean(p >= cutoff))
        observed_rate = float(np.mean(y))
        score["predicted_event_frequency"] = predicted_rate
        score["observed_event_frequency"] = observed_rate
        score["event_frequency_bias"] = predicted_rate / observed_rate if observed_rate else None
        score["mean_forecast_probability"] = float(np.mean(p))
        result["probability"][name] = score
    for model in ("M0", "M2", "M4"):
        spatial = [{"forecast": case[f"{model}_field"], "observed": case["observed_field"],
                    "mask": case["valid_mask"]} for case in group]
        result["heavy_fss_3x3"][model] = fss_many(spatial, rule["thresholds_mm_24h"]["heavy"], 3)
    result["bss_date_bootstrap"] = bootstrap_bss(group, rule)
    return result


def bootstrap_bss(group: list[dict], rule: dict, repeats: int = 1000) -> dict:
    dates = sorted({case["cycle"] for case in group})
    if len(dates) < 2:
        return {"reason": "fewer than two initialization dates"}
    rng = np.random.default_rng(26080)
    output = {"unit": "initialization_date", "repeats": repeats, "seed": 26080,
              "spatial_serial_dependence_remains": True, "bss_95pct_interval": {}}
    for name in ("heavy", "very_heavy"):
        climate = rule["climatology_2023"][name]
        sums = []
        for date in dates:
            cases = [case for case in group if case["cycle"] == date]
            numer = sum(float(np.sum((case[f"{name}_probability"] - case[f"{name}_label"]) ** 2)) for case in cases)
            denom = sum(float(np.sum((climate - case[f"{name}_label"]) ** 2)) for case in cases)
            sums.append((numer, denom))
        pairs = np.asarray(sums, dtype=float)
        picks = rng.integers(0, len(dates), size=(repeats, len(dates)))
        selected = pairs[picks].sum(axis=1)
        bss = 1 - selected[:, 0] / selected[:, 1]
        output["bss_95pct_interval"][name] = np.quantile(bss, [.025, .975]).tolist()
    return output


def score() -> dict:
    rule, score_protocol_sha = verified_protocol()  # before IMD access
    _, forecast_protocol_sha = forecast.checked_protocol()
    forecast_year, forecast_sha = checked(forecast.OUT)
    if (forecast_year["protocol_sha256"] != forecast_protocol_sha or forecast_year["ready_leads"] != 90
            or forecast_year["previously_ready_fields_matched"] != 55 or forecast_year["newly_ready_leads"] != 35
            or forecast.seal_year(forecast_protocol_sha, forecast_year["prior_forecast_sha256"]) != forecast_year):
        raise ValueError("coherent forecast seal or expected population differs")
    old_year, old_year_sha, _ = forecast.check_prior()
    if old_year_sha != forecast_year["prior_forecast_sha256"]:
        raise ValueError("prior forecast seal differs from coherent replay")
    prior_status = {case["cycle"]: {product: case["products"][product]["status"] == "READY"
                                     for product in forecast.PRODUCTS} for case in old_year["cases"]}
    prior, prior_sha = checked(prior_imd.ROOT / "data/manifests/research_pilot/partial_cell_development_result_v1.json")
    imd_sha = prior_forecast.sha(IMD)
    if imd_sha != prior["year_results"][1]["imd_reference_sha256"]:
        raise ValueError("2024 IMD reference differs from frozen prior development study")
    cases = []
    lineage = []
    for entry in forecast_year["cases"]:
        cycle = entry["cycle"]
        directory = forecast.CACHE / cycle
        manifest = forecast.verify_case(directory, forecast_protocol_sha, forecast_year["prior_forecast_sha256"])
        if prior_forecast.sha(directory / "manifest.json") != entry["manifest_sha256"]:
            raise ValueError("coherent case differs from year seal")
        init = datetime.strptime(cycle, "%Y%m%d").replace(tzinfo=timezone.utc)
        with np.load(directory / "fields.npz", allow_pickle=False) as archive:
            for product in forecast.PRODUCTS:
                info = manifest["products"][product]
                if info["status"] != "READY":
                    raise ValueError("score protocol requires all 90 forecast-ready leads")
                date = product_valid_date(init, product)
                observation = load_imd_day(IMD, date, south=10, north=22, west=68, east=80)
                if (observation.rainfall_mm.shape != (49, 49)
                        or not np.array_equal(observation.latitude, np.linspace(10, 22, 49))
                        or not np.array_equal(observation.longitude, np.linspace(68, 80, 49))):
                    raise ValueError("forecast and IMD coordinates differ")
                mask = archive[f"valid_{product}"].astype(bool) & observation.valid_mask
                if not mask.any():
                    raise ValueError("coherent lead has no paired cells")
                payload = {"cycle": cycle, "product": product, "strict_passed": info["strict_passed"],
                           "prior_ready": prior_status[cycle][product],
                           "cell_count": int(mask.sum()), "valid_mask": mask,
                           "observed_field": observation.rainfall_mm,
                           "models": {name: metrics(archive[f"{name}_{product}"], observation.rainfall_mm, mask)
                                      for name in ("M0", "M2", "M4")}}
                for name, threshold in rule["thresholds_mm_24h"].items():
                    payload[f"{name}_label"] = (observation.rainfall_mm[mask] >= threshold).astype(np.uint8)
                    payload[f"{name}_probability"] = archive[f"{name}_probability_{product}"][mask].astype(np.float64)
                for name in ("M0", "M2", "M4"):
                    payload[f"{name}_field"] = archive[f"{name}_{product}"]
                cases.append(payload)
                lineage.append({"cycle": cycle, "product": product, "valid_date": date.isoformat(),
                                "paired_cells": int(mask.sum()), "strict_passed": info["strict_passed"],
                                "prior_ready": payload["prior_ready"], "projection_modified_cells": info["projection_modified_cells"],
                                "forecast_manifest_sha256": entry["manifest_sha256"]})
    if len(cases) != 90 or sum(case["prior_ready"] for case in cases) != 55:
        raise ValueError("coherent score strata differ from prior forecast")
    groups = {"all_ready": cases, "prior_ready": [case for case in cases if case["prior_ready"]],
              "newly_ready": [case for case in cases if not case["prior_ready"]]}
    for product in forecast.PRODUCTS:
        groups[product] = [case for case in cases if case["product"] == product]
    return {"schema": "varshasetu-coherent-partial-grid-score-v1", "score_protocol_sha256": score_protocol_sha,
            "forecast_protocol_sha256": forecast_protocol_sha, "forecast_seal_sha256": forecast_sha,
            "prior_imd_development_result_sha256": prior_sha, "imd_reference_sha256": imd_sha,
            "model_selection_freeze_sha256": prior_forecast.sha(SELECTION),
            "role": "consumed_2024_development_diagnostic_not_independent_reliability",
            "same_paired_cells_for_all_comparators": True, "observation_read_only_after_forecast_seal": True,
            "summary": {name: score_group(group, rule) for name, group in groups.items()},
            "cases": lineage, "decision": "No live promotion or calibrated-reliability claim; independent-year test required"}


def main() -> None:
    result = score()
    payload = json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n"
    if OUT.exists():
        if OUT.read_text(encoding="utf-8") != payload or OUT.with_suffix(".sha256").read_text(encoding="ascii").split()[0] != prior_forecast.sha(OUT):
            raise ValueError("immutable coherent score differs")
    else:
        with OUT.open("x", encoding="utf-8", newline="\n") as stream:
            stream.write(payload)
        OUT.with_suffix(".sha256").write_text(hashlib.sha256(payload.encode()).hexdigest() + "  " + OUT.name + "\n", encoding="ascii")
    for name in ("all_ready", "prior_ready", "newly_ready"):
        block = result["summary"][name]
        print(json.dumps({"group": name, "case_count": block["case_count"], "paired_cells": block["paired_cells"],
                          "heavy_brier": block["probability"]["heavy"]["brier"],
                          "heavy_bss": block["probability"]["heavy"]["bss"],
                          "very_heavy_brier": block["probability"]["very_heavy"]["brier"],
                          "very_heavy_bss": block["probability"]["very_heavy"]["bss"]}))


if __name__ == "__main__":
    main()
