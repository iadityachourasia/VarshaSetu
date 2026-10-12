"""Paired June 2024 IMD diagnostic after the no-refit transport forecast seal."""

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
from scripts import fit_lead_aware_probability as fit  # noqa: E402
from scripts import run_coherent_partial_grid as old  # noqa: E402
from scripts import run_june_probability_transport as forecast  # noqa: E402
from scripts import run_partial_cell_development as prior_imd  # noqa: E402
from scripts import score_coherent_partial_grid as old_score  # noqa: E402
from scripts.score_lead_aware_probability import score_target  # noqa: E402

OUT = ROOT / "data/manifests/research_pilot/june_probability_transport_score_v1.json"
IMD = ROOT / "experiments/recent_historical/imd/RF25_ind2024_rfp25.nc"
ARMS = ("frozen", "global", "lead_aware")
TARGETS = ("heavy", "very_heavy")


def score_group(group: list[dict], rule: dict) -> dict:
    if not group:
        raise ValueError("empty June transport scoring group")
    output = {"case_count": len(group), "initialization_count": len({case["cycle"] for case in group}),
              "paired_cells": sum(case["paired_cells"] for case in group), "arms": {}}
    for arm in ARMS:
        events = {}
        for target in TARGETS:
            y = np.concatenate([case[f"{target}_label"] for case in group])
            p = np.concatenate([case[f"{arm}_{target}"] for case in group])
            events[target] = score_target(y, p, rule["fixed_warning_cutoffs"][target],
                                          rule["climatology_2023"][target])
        output["arms"][arm] = {"heavy": events["heavy"], "very_heavy": events["very_heavy"],
                               "joint_brier_sum": events["heavy"]["brier"] + events["very_heavy"]["brier"]}
    output["date_bootstrap"] = bootstrap(group)
    return output


def bootstrap(group: list[dict], repeats: int = 1000) -> dict:
    dates = sorted({case["cycle"] for case in group})
    if len(dates) < 2:
        return {"reason": "fewer than two initialization dates"}
    rows = []
    for date in dates:
        cases = [case for case in group if case["cycle"] == date]
        row = [sum(case["paired_cells"] for case in cases)]
        for target in TARGETS:
            for arm in ARMS:
                row.append(sum(float(np.sum((case[f"{arm}_{target}"] - case[f"{target}_label"]) ** 2))
                               for case in cases))
        rows.append(row)
    matrix = np.asarray(rows, dtype=np.float64)
    rng = np.random.default_rng(26080)
    samples = matrix[rng.integers(0, len(dates), size=(repeats, len(dates)))].sum(axis=1)
    intervals = {}
    for label, left, right in (("lead_aware_minus_global", 2, 1),
                               ("lead_aware_minus_frozen", 2, 0),
                               ("global_minus_frozen", 1, 0)):
        heavy = (samples[:, 1 + left] - samples[:, 1 + right]) / samples[:, 0]
        very = (samples[:, 4 + left] - samples[:, 4 + right]) / samples[:, 0]
        intervals[label] = {"heavy": np.quantile(heavy, [.025, .975]).tolist(),
                            "very_heavy": np.quantile(very, [.025, .975]).tolist(),
                            "joint": np.quantile(heavy + very, [.025, .975]).tolist()}
    return {"unit": "initialization_date", "date_count": len(dates), "repeats": repeats,
            "seed": 26080, "brier_difference_95pct_intervals": intervals,
            "interpretation": "Descriptive consumed-development bootstrap; spatial and serial dependence remain"}


def score() -> dict:
    context = forecast.inputs()
    transport, transport_sha = forecast.checked(forecast.OUT)
    if (transport["protocol_sha256"] != context["protocol_sha256"]
            or transport["lead_count"] != 90 or transport["observation_read"] is not False
            or forecast.seal_year(context) != transport):
        raise ValueError("transport forecast seal does not reproduce")
    fit_rule, fit_rule_sha = fit.checked(fit.PROTOCOL)
    if context["fit_manifest"]["protocol_sha256"] != fit_rule_sha:
        raise ValueError("transport score calibrator protocol differs")
    prior_result, prior_result_sha = forecast.checked(prior_imd.ROOT / "data/manifests/research_pilot/partial_cell_development_result_v1.json")
    imd_sha = fit.sha256(IMD)
    if imd_sha != prior_result["year_results"][1]["imd_reference_sha256"]:
        raise ValueError("June 2024 IMD source differs from prior development reference")
    coherent_result, coherent_score_sha = forecast.checked(old_score.OUT)
    if coherent_result["forecast_seal_sha256"] != context["old_year_sha256"]:
        raise ValueError("coherent prior score used a different forecast seal")
    cases, lineage = [], []
    for entry in transport["cases"]:
        date = entry["cycle"]
        directory = forecast.CACHE / date
        prior_dir = old.CACHE / date
        case = forecast.verify_case(directory, context["protocol_sha256"],
                                    context["old_year_sha256"], context["fit_seal_sha256"])
        if fit.sha256(directory / "manifest.json") != entry["manifest_sha256"]:
            raise ValueError("transport case differs from year seal")
        prior = old.verify_case(prior_dir, context["old_protocol_sha256"],
                                context["old_year"]["prior_forecast_sha256"])
        if fit.sha256(prior_dir / "manifest.json") != case["coherent_case_sha256"]:
            raise ValueError("transport case linked to another coherent case")
        init = datetime.strptime(date, "%Y%m%d").replace(tzinfo=timezone.utc)
        with np.load(directory / "fields.npz", allow_pickle=False) as candidate, np.load(prior_dir / "fields.npz", allow_pickle=False) as baseline:
            for product in old.PRODUCTS:
                valid_date = product_valid_date(init, product)
                obs = load_imd_day(IMD, valid_date, south=10, north=22, west=68, east=80)
                if (obs.rainfall_mm.shape != (49, 49)
                        or not np.array_equal(obs.latitude, np.linspace(10, 22, 49))
                        or not np.array_equal(obs.longitude, np.linspace(68, 80, 49))):
                    raise ValueError("transport forecast and IMD coordinates differ")
                valid = candidate[f"valid_{product}"].astype(bool)
                if not np.array_equal(valid, baseline[f"valid_{product}"].astype(bool)):
                    raise ValueError("transport and coherent masks differ")
                paired = valid & obs.valid_mask
                if not paired.any():
                    raise ValueError("transport lead has no IMD-paired cells")
                item = {"cycle": date, "product": product, "prior_ready": case["products"][product]["prior_ready"],
                        "paired_cells": int(paired.sum())}
                for target, threshold in fit_rule["event_thresholds_mm_24h"].items():
                    item[f"{target}_label"] = (obs.rainfall_mm[paired] >= threshold).astype(np.uint8)
                    item[f"frozen_{target}"] = baseline[f"{target}_probability_{product}"][paired]
                    for arm in forecast.ARMS:
                        item[f"{arm}_{target}"] = candidate[f"{arm}_{target}_{product}"][paired]
                cases.append(item)
                lineage.append({"cycle": date, "product": product, "valid_date": valid_date.isoformat(),
                                "paired_cells": item["paired_cells"], "prior_ready": item["prior_ready"],
                                "transport_case_sha256": entry["manifest_sha256"],
                                "coherent_case_sha256": case["coherent_case_sha256"]})
    if len(cases) != 90 or sum(case["prior_ready"] for case in cases) != 55:
        raise ValueError("transport score population differs")
    groups = {"all_ready": cases, "prior_ready": [case for case in cases if case["prior_ready"]],
              "newly_ready": [case for case in cases if not case["prior_ready"]]}
    for product in old.PRODUCTS:
        groups[product] = [case for case in cases if case["product"] == product]
    summary = {name: score_group(group, fit_rule) for name, group in groups.items()}
    for name in ("all_ready", "prior_ready", "newly_ready"):
        earlier = coherent_result["summary"][name]
        block = summary[name]
        if block["paired_cells"] != earlier["paired_cells"]:
            raise ValueError("transport same-cell comparison differs from coherent score")
        for target in TARGETS:
            if not np.isclose(block["arms"]["frozen"][target]["brier"], earlier["probability"][target]["brier"], rtol=0, atol=1e-15):
                raise ValueError("transport frozen probability score differs from coherent score")
    return {"schema": "varshasetu-june-probability-transport-score-v1",
            "protocol_sha256": context["protocol_sha256"], "transport_forecast_sha256": transport_sha,
            "lead_aware_fit_seal_sha256": context["fit_seal_sha256"],
            "coherent_score_sha256": coherent_score_sha,
            "prior_imd_development_result_sha256": prior_result_sha, "imd_reference_sha256": imd_sha,
            "role": "consumed_2024_no_refit_transport_diagnostic_not_independent_reliability",
            "same_paired_cells_for_all_arms": True, "observation_read_only_after_forecast_seal": True,
            "summary": summary, "cases": lineage,
            "decision": "No candidate promotion or calibrated-status change from consumed June 2024 data"}


def main() -> None:
    result = score()
    payload = json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n"
    if OUT.exists():
        if OUT.read_text(encoding="utf-8") != payload or OUT.with_suffix(".sha256").read_text(encoding="ascii").split()[0] != fit.sha256(OUT):
            raise ValueError("immutable June transport score differs")
    else:
        with OUT.open("x", encoding="utf-8", newline="\n") as stream:
            stream.write(payload)
        OUT.with_suffix(".sha256").write_text(hashlib.sha256(payload.encode()).hexdigest() + "  " + OUT.name + "\n", encoding="ascii")
    for name in ("all_ready", "prior_ready", "newly_ready"):
        block = result["summary"][name]
        print(json.dumps({"group": name, "paired_cells": block["paired_cells"],
                          "arms": {arm: {"joint_brier": block["arms"][arm]["joint_brier_sum"],
                                         "heavy_bss": block["arms"][arm]["heavy"]["bss"],
                                         "very_heavy_bss": block["arms"][arm]["very_heavy"]["bss"],
                                         "very_heavy_frequency_bias": block["arms"][arm]["very_heavy"]["event_frequency_bias_at_cutoff"]}
                                   for arm in ARMS},
                          "joint_intervals": {key: value["joint"] for key, value in block["date_bootstrap"]["brier_difference_95pct_intervals"].items()}}))


if __name__ == "__main__":
    main()
