"""Score a sealed ordinal candidate on consumed 2024 development blocks only."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.app.ml.phase2c import probability_metrics  # noqa: E402
from scripts import experiment_extreme_ordinal_fit as fit  # noqa: E402

OUT = fit.OUT / "extreme_ordinal_probability_score_v1.json"
ARMS = ("frozen", "global", "ordinal")
TARGETS = ("heavy", "very_heavy")


def score_target(y: np.ndarray, p: np.ndarray, cutoff: float, climate: float) -> dict:
    result = probability_metrics(y, p, cutoff, climate)
    observed = int(y.sum())
    warnings = int(np.sum(p >= cutoff))
    result.update({"observed_event_cells": observed, "forecast_warning_cells": warnings,
                   "observed_event_frequency": float(y.mean()),
                   "mean_forecast_probability": float(p.mean()),
                   "forecast_warning_frequency": float(warnings / len(y)),
                   "warning_frequency_ratio": float(warnings / observed) if observed else None})
    return result


def block(mask: np.ndarray, cases: list, labels: dict, arrays: dict, rule: dict) -> dict:
    if not mask.any():
        raise ValueError("empty scoring block")
    event_cases = {}
    for target in TARGETS:
        event_cases[target] = sum(
            int(np.asarray(labels[target][int(case["row_start"]):int(case["row_start"]) + 1301]).sum() > 0)
            for case in cases if mask[int(case["row_start"])]
        )
    arms = {}
    for arm in ARMS:
        per_target = {}
        for target in TARGETS:
            y = np.asarray(labels[target][mask], dtype=np.uint8)
            p = arrays[f"{arm}_{target}"][mask]
            per_target[target] = score_target(y, p, rule["fixed_warning_cutoffs"][target],
                                              rule["climatology_2023"][target])
        arms[arm] = {**per_target,
                     "joint_brier_sum": per_target["heavy"]["brier"] + per_target["very_heavy"]["brier"]}
    return {"paired_cells": int(mask.sum()), "event_bearing_cases": event_cases,
            "arms": arms}


def date_bootstrap(mask: np.ndarray, cases: list, labels: dict, arrays: dict,
                   *, repeats: int = 1000) -> dict:
    by_date = {}
    for case in cases:
        start = int(case["row_start"])
        if not mask[start]:
            continue
        date = case["initialization_utc"][:10]
        by_date.setdefault(date, []).append(slice(start, start + 1301))
    if len(by_date) < 2:
        raise ValueError("too few initialization dates for bootstrap")
    terms = []
    for slices in by_date.values():
        term = {"cells": 0, "observed_very_heavy": 0}
        for target in TARGETS:
            term[f"observed_{target}"] = 0
            for arm in ARMS:
                term[f"sse_{arm}_{target}"] = 0.0
                term[f"warnings_{arm}_{target}"] = 0
        for sl in slices:
            term["cells"] += sl.stop - sl.start
            for target in TARGETS:
                y = np.asarray(labels[target][sl], dtype=np.float64)
                term[f"observed_{target}"] += int(y.sum())
                for arm in ARMS:
                    p = arrays[f"{arm}_{target}"][sl]
                    term[f"sse_{arm}_{target}"] += float(np.sum((p - y) ** 2))
                    term[f"warnings_{arm}_{target}"] += int(np.sum(p >= (0.10 if target == "heavy" else 0.05)))
        terms.append(term)
    rng = np.random.default_rng(26080)
    picks = rng.integers(0, len(terms), size=(repeats, len(terms)))
    def sampled(key: str) -> np.ndarray:
        values = np.asarray([term[key] for term in terms], dtype=np.float64)
        return values[picks].sum(axis=1)
    cells = sampled("cells")
    intervals = {}
    for control in ("frozen", "global"):
        h = (sampled("sse_ordinal_heavy") - sampled(f"sse_{control}_heavy")) / cells
        v = (sampled("sse_ordinal_very_heavy") - sampled(f"sse_{control}_very_heavy")) / cells
        intervals[f"ordinal_minus_{control}"] = {
            "heavy_brier_95pct": np.quantile(h, [.025, .975]).tolist(),
            "very_heavy_brier_95pct": np.quantile(v, [.025, .975]).tolist(),
            "joint_brier_95pct": np.quantile(h + v, [.025, .975]).tolist(),
        }
    observed = sampled("observed_very_heavy")
    warning_intervals = {}
    for arm in ARMS:
        ratio = np.divide(sampled(f"warnings_{arm}_very_heavy"), observed,
                          out=np.full(repeats, np.nan), where=observed > 0)
        valid = ratio[np.isfinite(ratio)]
        warning_intervals[arm] = np.quantile(valid, [.025, .975]).tolist() if len(valid) else None
    return {"unit": "initialization_date", "dates": len(terms), "repeats": repeats,
            "seed": 26080, "brier_difference_intervals": intervals,
            "very_heavy_warning_frequency_ratio_intervals": warning_intervals,
            "zero_event_replicates": int(np.sum(observed == 0)),
            "caveat": "Descriptive intervals on consumed 2024; spatial and serial dependence remain"}


def score(source_root: Path) -> dict:
    rule, protocol_sha = fit.checked(fit.PROTOCOL)
    seal, seal_sha = fit.checked(fit.SEAL)
    if (seal["protocol_sha256"] != protocol_sha or seal["selection_labels_decoded"] is not False
            or fit.sha256(fit.PREDICTIONS) != seal["prediction_archive_sha256"]):
        raise ValueError("prediction seal or protocol differs")
    data = fit.inputs(source_root)
    if data["source_hashes"] != seal["source_hashes"]:
        raise ValueError("source inputs differ from forecast seal")
    with np.load(fit.PREDICTIONS, allow_pickle=False) as archive:
        arrays = {key: archive[key] for key in archive.files}
    with np.load(data["prior_path"] / "predictions.npz", allow_pickle=False) as prior:
        for arm in ("frozen", "global"):
            for target in TARGETS:
                key = f"{arm}_{target}"
                if not np.array_equal(arrays[key], prior[key]):
                    raise ValueError("sealed control differs from prior prediction")
    if np.any(np.asarray(data["labels"]["very_heavy"]) > np.asarray(data["labels"]["heavy"])):
        raise ValueError("observed labels violate nesting")
    masks = dict(data["masks"])
    for day in (1, 2, 3):
        lead_mask = np.zeros(fit.COUNT, dtype=bool)
        for case in data["cases"]:
            if case["lead_hours"] == 24 * day:
                start = int(case["row_start"])
                lead_mask[start:start + 1301] = True
        masks[f"selection_day{day}"] = masks["selection"] & lead_mask
    scores = {name: block(mask, data["cases"], data["labels"], arrays, rule)
              for name, mask in masks.items()}
    selected = scores["selection"]["arms"]
    delta = {target: selected["ordinal"][target]["brier"] - selected["frozen"][target]["brier"]
             for target in TARGETS}
    delta["joint"] = selected["ordinal"]["joint_brier_sum"] - selected["frozen"]["joint_brier_sum"]
    bootstrap = date_bootstrap(masks["selection"], data["cases"], data["labels"], arrays)
    ordinal_v = selected["ordinal"]["very_heavy"]
    frozen_v = selected["frozen"]["very_heavy"]
    interval = bootstrap["brier_difference_intervals"]["ordinal_minus_frozen"]["very_heavy_brier_95pct"]
    diagnostic_pass = (interval[1] < 0 and ordinal_v["bss"] is not None and ordinal_v["bss"] > 0
                       and delta["heavy"] <= 0.0001
                       and ordinal_v["warning_frequency_ratio"] is not None
                       and frozen_v["warning_frequency_ratio"] is not None
                       and abs(np.log(ordinal_v["warning_frequency_ratio"]))
                       < abs(np.log(frozen_v["warning_frequency_ratio"])))
    return {"schema": "varshasetu-extreme-ordinal-score-v1",
            "protocol_sha256": protocol_sha, "prediction_seal_sha256": seal_sha,
            "population_role": "consumed_2024_development_only",
            "scores": scores, "selection_ordinal_minus_frozen_brier": delta,
            "selection_date_bootstrap": bootstrap,
            "prespecified_diagnostic_gate_passed": bool(diagnostic_pass),
            "promotion_eligible": False,
            "interpretation": "The 2024 base/control model selection consumed this year. This is not independent reliability evidence."}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, required=True)
    args = parser.parse_args()
    result = score(args.source_root.resolve())
    fit.write_once_json(OUT, result)
    print(json.dumps({"selection_cells": result["scores"]["selection"]["paired_cells"],
                      "brier_delta": result["selection_ordinal_minus_frozen_brier"],
                      "diagnostic_gate": result["prespecified_diagnostic_gate_passed"]}, sort_keys=True))
