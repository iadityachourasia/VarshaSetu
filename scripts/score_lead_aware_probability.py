"""Score sealed lead-aware development predictions on 2024 labels."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.app.ml.phase2c import probability_metrics  # noqa: E402
from scripts import fit_lead_aware_probability as fit  # noqa: E402

OUT = fit.MANIFEST / "lead_aware_probability_score_v1.json"


def score_target(y: np.ndarray, p: np.ndarray, cutoff: float, climate: float) -> dict:
    result = probability_metrics(y, p, cutoff, climate)
    result["mean_forecast_probability"] = float(np.mean(p))
    result["observed_event_frequency"] = float(np.mean(y))
    result["forecast_event_frequency_at_cutoff"] = float(np.mean(p >= cutoff))
    result["event_frequency_bias_at_cutoff"] = (result["forecast_event_frequency_at_cutoff"] /
                                                  result["observed_event_frequency"]
                                                  if result["observed_event_frequency"] else None)
    return result


def score_block(mask: np.ndarray, labels: dict, predictions: dict, rule: dict) -> dict:
    if not mask.any():
        raise ValueError("empty lead-aware scoring block")
    result = {"paired_cells": int(mask.sum()), "arms": {}}
    for arm in fit.ARMS:
        events = {}
        for target in fit.TARGETS:
            y = np.asarray(labels[target][mask], dtype=np.uint8)
            p = predictions[f"{arm}_{target}"][mask]
            events[target] = score_target(y, p, rule["fixed_warning_cutoffs"][target],
                                          rule["climatology_2023"][target])
        result["arms"][arm] = {"heavy": events["heavy"], "very_heavy": events["very_heavy"],
                               "joint_brier_sum": events["heavy"]["brier"] + events["very_heavy"]["brier"]}
    return result


def date_bootstrap_selection(data: dict, predictions: dict, *, repeats: int = 1000) -> dict:
    mask = data["masks"]["selection"]
    case_dates = sorted({case["initialization_utc"][:10] for case in data["cases"]
                         if case["case_id"] in set(data["split"]["selection_case_ids"])})
    if len(case_dates) < 2:
        raise ValueError("selection bootstrap has fewer than two initialization dates")
    rows = []
    for date in case_dates:
        date_mask = np.zeros(mask.shape, dtype=bool)
        for case in data["cases"]:
            if case["initialization_utc"][:10] == date and mask[case["row_start"]]:
                start = case["row_start"]
                date_mask[start:start + case["row_count"]] = True
        if not date_mask.any():
            raise ValueError("selection date has no rows")
        terms = [int(date_mask.sum())]
        for target in fit.TARGETS:
            y = np.asarray(data["labels"][target][date_mask], dtype=float)
            for arm in ("global", "lead_aware"):
                p = predictions[f"{arm}_{target}"][date_mask]
                terms.append(float(np.sum((p - y) ** 2)))
        rows.append(terms)
    terms = np.asarray(rows, dtype=float)
    rng = np.random.default_rng(26080)
    picks = rng.integers(0, len(rows), size=(repeats, len(rows)))
    sampled = terms[picks].sum(axis=1)
    heavy_delta = (sampled[:, 2] - sampled[:, 1]) / sampled[:, 0]
    very_delta = (sampled[:, 4] - sampled[:, 3]) / sampled[:, 0]
    return {"unit": "initialization_date", "date_count": len(rows), "repeats": repeats, "seed": 26080,
            "lead_aware_minus_global_heavy_brier_95pct_interval": np.quantile(heavy_delta, [.025, .975]).tolist(),
            "lead_aware_minus_global_very_heavy_brier_95pct_interval": np.quantile(very_delta, [.025, .975]).tolist(),
            "lead_aware_minus_global_joint_brier_95pct_interval": np.quantile(heavy_delta + very_delta, [.025, .975]).tolist(),
            "remaining_dependence": "Spatial and serial dependence remain; consumed 2024 development blocks, not an independent promotion test"}


def score() -> dict:
    rule, protocol_sha = fit.checked(fit.PROTOCOL)
    seal, seal_sha = fit.checked(fit.OUT)
    if (rule["status"] != "FROZEN_BEFORE_CANDIDATE_FITTING_AND_SELECTION_BLOCK_SCORING"
            or seal["protocol_sha256"] != protocol_sha or seal["selection_labels_decoded"] is not False):
        raise ValueError("lead-aware prediction seal or scoring protocol differs")
    manifest = fit.verified_cache(protocol_sha)
    if (fit.sha256(fit.CACHE / "manifest.json") != seal["fit_manifest_sha256"]
            or manifest["prediction_archive_sha256"] != seal["prediction_archive_sha256"]):
        raise ValueError("lead-aware fit cache differs from prediction seal")
    data = fit.source()  # selection labels are memory-mapped, not decoded until below
    if data["split_sha256"] != manifest["split_sha256"] or data["cases_sha256"] != manifest["cases_sha256"]:
        raise ValueError("lead-aware scoring cases or split differ from fitted artifacts")
    with np.load(fit.CACHE / "predictions.npz", allow_pickle=False) as archive:
        predictions = {key: archive[key] for key in archive.files}
    labels = data["labels"]
    if np.any(np.asarray(labels["very_heavy"]) > np.asarray(labels["heavy"])):
        raise ValueError("observed event labels violate 24-hour threshold nesting")
    blocks = {name: data["masks"][name] for name in ("calibration", "purged", "selection")}
    for lead_day in (1, 2, 3):
        blocks[f"selection_day{lead_day}"] = data["masks"]["selection"] & (data["lead"] == lead_day)
    summary = {name: score_block(mask, labels, predictions, rule) for name, mask in blocks.items()}
    selection = summary["selection"]
    delta = {target: selection["arms"]["lead_aware"][target]["brier"] -
            selection["arms"]["global"][target]["brier"] for target in fit.TARGETS}
    delta["joint_brier_sum"] = selection["arms"]["lead_aware"]["joint_brier_sum"] - selection["arms"]["global"]["joint_brier_sum"]
    return {"schema": "varshasetu-lead-aware-probability-score-v1", "protocol_sha256": protocol_sha,
            "prediction_seal_sha256": seal_sha, "fit_manifest_sha256": seal["fit_manifest_sha256"],
            "role": "consumed_2024_development_diagnostic_no_independent_reliability_claim",
            "training_labels": "early_2024_calibration_block_only", "scores": summary,
            "primary_selection_lead_aware_minus_global_brier": delta,
            "primary_selection_date_bootstrap": date_bootstrap_selection(data, predictions),
            "interpretation": "No method selection or live promotion. Existing base models and frozen isotonic control were selected with 2024 outcomes; any apparent advantage needs independent-year validation."}


def main() -> None:
    result = score()
    payload = json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n"
    if OUT.exists():
        if OUT.read_text(encoding="utf-8") != payload or OUT.with_suffix(".sha256").read_text(encoding="ascii").split()[0] != fit.sha256(OUT):
            raise ValueError("immutable lead-aware score differs")
    else:
        with OUT.open("x", encoding="utf-8", newline="\n") as stream:
            stream.write(payload)
        OUT.with_suffix(".sha256").write_text(hashlib.sha256(payload.encode()).hexdigest() + "  " + OUT.name + "\n", encoding="ascii")
    selection = result["scores"]["selection"]
    print(json.dumps({"selection_cells": selection["paired_cells"],
                      "primary_brier_delta": result["primary_selection_lead_aware_minus_global_brier"],
                      "bootstrap": result["primary_selection_date_bootstrap"],
                      "arms": {name: {"heavy_bss": block["heavy"]["bss"],
                                      "very_heavy_bss": block["very_heavy"]["bss"],
                                      "heavy_frequency_bias": block["heavy"]["event_frequency_bias_at_cutoff"],
                                      "very_heavy_frequency_bias": block["very_heavy"]["event_frequency_bias_at_cutoff"]}
                               for name, block in selection["arms"].items()}}, sort_keys=True))


if __name__ == "__main__":
    main()
