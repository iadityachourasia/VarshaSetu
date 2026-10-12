"""Append-only uncertainty and regional gate report for sealed 2024 development results."""

from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.app.ml.nationwide_research import REGIONS, comparable_mask, partition  # noqa: E402
from scripts.nationwide_research import (  # noqa: E402
    BASE, OUT, PROTOCOL, SCORE, SEAL, _feature_manifest, _load_x, _reference,
    receipt, sha, write_json,
)

REPORT = BASE / "nationwide_research_uncertainty_v1.json"
MODELS = ("M0", "M1", "M2", "M3", "M4")


def _case_stats(truth: np.ndarray, forecast: np.ndarray) -> np.ndarray:
    error = forecast.astype(np.float64) - truth.astype(np.float64)
    observed = truth >= 64.5
    warned = forecast >= 64.5
    return np.asarray([len(error), np.sum(error), np.sum(error * error),
                       np.count_nonzero(observed & warned), np.count_nonzero(observed & ~warned),
                       np.count_nonzero(~observed & warned)], dtype=np.float64)


def _metrics(stat: np.ndarray) -> tuple[float, float]:
    if stat[0] <= 0:
        return float("nan"), float("nan")
    rmse = float(np.sqrt(stat[2] / stat[0]))
    denominator = stat[3:6].sum()
    return rmse, float(stat[3] / denominator) if denominator else float("nan")


def build() -> dict:
    if REPORT.exists():
        raise FileExistsError("uncertainty report is write-once")
    protocol, features, mask = _feature_manifest()
    if receipt(SCORE) != sha(SCORE) or receipt(SEAL) != sha(SEAL):
        raise ValueError("national score/seal receipt mismatch")
    score = json.loads(SCORE.read_text(encoding="utf-8"))
    seal = json.loads(SEAL.read_text(encoding="utf-8"))
    if score["fit_seal_sha256"] != sha(SEAL) or seal["protocol_sha256"] != sha(PROTOCOL):
        raise ValueError("national evidence chain mismatch")
    regions = partition(mask)
    by_id = {row["case_id"]: row for row in features["cases"] if row["year"] == 2024}
    dates = sorted({row["case_id"][:8] for row in seal["predictions"]})
    date_index = {day: i for i, day in enumerate(dates)}
    names = ("ALL_INDIA", *REGIONS)
    stats = np.zeros((len(dates), len(names), 4, len(MODELS), 6), dtype=np.float64)
    case_support = defaultdict(lambda: {"cases": 0, "paired_cells": 0, "heavy_observed": 0, "very_heavy_observed": 0})
    for row in seal["predictions"]:
        x, _ = _load_x(by_id[row["case_id"]])
        truth = _reference(2024, row["case_id"], row["hour"])
        raw = np.full(mask.shape, np.nan)
        raw[mask] = x[:, 0]
        paired = comparable_mask(mask, raw, truth.rainfall_mm, truth.valid_mask)
        with np.load(ROOT / row["file"], allow_pickle=False) as bundle:
            forecasts = {name: bundle[name] for name in MODELS}
        for ri, name in enumerate(names):
            selected = paired & (mask if name == "ALL_INDIA" else regions[name])
            if not selected.any():
                continue
            reference = truth.rainfall_mm[selected]
            support = case_support[(name, row["hour"])]
            support["cases"] += 1
            support["paired_cells"] += int(selected.sum())
            support["heavy_observed"] += int(np.count_nonzero(reference >= 64.5))
            support["very_heavy_observed"] += int(np.count_nonzero(reference >= 115.6))
            for mi, model in enumerate(MODELS):
                field = np.full(mask.shape, np.nan)
                field[mask] = forecasts[model]
                stat = _case_stats(reference, field[selected])
                stats[date_index[row["case_id"][:8]], ri, 0, mi] += stat
                stats[date_index[row["case_id"][:8]], ri, row["hour"] // 24, mi] += stat
    repeats = protocol["uncertainty"]["repeats"]
    rng = np.random.default_rng(protocol["uncertainty"]["seed"])
    sampling = rng.integers(0, len(dates), size=(repeats, len(dates)))
    result = {}
    for ri, region in enumerate(names):
        result[region] = {}
        for lead_index, lead in enumerate((0, 24, 48, 72)):
            raw_stat = stats[:, ri, lead_index, 0].sum(axis=0)
            raw_rmse, raw_csi = _metrics(raw_stat)
            if not np.isfinite(raw_rmse):
                continue
            result[region][str(lead)] = {}
            for mi, model in enumerate(MODELS):
                observed = stats[:, ri, lead_index, mi].sum(axis=0)
                rmse, csi = _metrics(observed)
                rmse_delta, csi_delta = [], []
                for sample in sampling:
                    a = stats[sample, ri, lead_index, mi].sum(axis=0)
                    b = stats[sample, ri, lead_index, 0].sum(axis=0)
                    ar, ac = _metrics(a); br, bc = _metrics(b)
                    if np.isfinite(ar) and np.isfinite(br):
                        rmse_delta.append(ar - br)
                    if np.isfinite(ac) and np.isfinite(bc):
                        csi_delta.append(ac - bc)
                support = (case_support[(region, lead)] if lead else {
                    key: sum(v[key] for (name, _hour), v in case_support.items() if name == region)
                    for key in ("cases", "paired_cells", "heavy_observed", "very_heavy_observed")})
                supported = support["cases"] >= 30 and support["heavy_observed"] >= 30 and support["very_heavy_observed"] >= 30
                result[region][str(lead)][model] = {
                    "rmse_mm": rmse, "heavy_csi": csi if np.isfinite(csi) else None, "support": dict(support),
                    "event_support_gate": bool(supported),
                    "rmse_minus_raw": rmse - raw_rmse,
                    "heavy_csi_minus_raw": csi - raw_csi if np.isfinite(csi) and np.isfinite(raw_csi) else None,
                    "rmse_delta_ci95": np.percentile(rmse_delta, [2.5, 97.5]).tolist() if rmse_delta else None,
                    "heavy_csi_delta_ci95": np.percentile(csi_delta, [2.5, 97.5]).tolist() if csi_delta else None,
                    "defined_bootstrap_repeats": {"rmse": len(rmse_delta), "heavy_csi": len(csi_delta)},
                }
    # The national M2 selection failed on 2023 OOF. An improved 2024 metric
    # cannot retroactively change that frozen decision.
    report = {"schema": "nationwide-research-uncertainty-v1",
              "status": "CONSUMED_2024_DEVELOPMENT_DIAGNOSTIC_NO_PROMOTION",
              "protocol_sha256": sha(PROTOCOL), "fit_seal_sha256": sha(SEAL),
              "score_sha256": sha(SCORE), "builder_sha256": sha(Path(__file__)),
              "initialization_dates": len(dates), "bootstrap_repeats": repeats,
              "spatial_serial_dependence_removed": False, "results": result,
              "selection_gate_passed": seal["m2_selected"] is not None,
              "independent_year_available": False,
              "nationwide_promotion_eligible": False,
              "model_default_unchanged": "regional_M2"}
    digest = write_json(REPORT, report)
    return {"status": report["status"], "dates": len(dates), "report_sha256": digest,
            "national_m2_heavy_csi_delta_ci95": result["ALL_INDIA"]["0"]["M2"]["heavy_csi_delta_ci95"]}


def check() -> dict:
    receipt(REPORT)
    data = json.loads(REPORT.read_text(encoding="utf-8"))
    if data["score_sha256"] != receipt(SCORE) or data["fit_seal_sha256"] != receipt(SEAL) or data["protocol_sha256"] != receipt(PROTOCOL):
        raise ValueError("national uncertainty lineage mismatch")
    if data["nationwide_promotion_eligible"] or data["independent_year_available"]:
        raise ValueError("unsupported national promotion claim")
    return {"status": data["status"], "initialization_dates": data["initialization_dates"], "sha256": sha(REPORT)}


if __name__ == "__main__":
    command = sys.argv[1] if len(sys.argv) == 2 else ""
    if command not in ("build", "check"):
        raise SystemExit("usage: summarize_nationwide_research.py build|check")
    print(json.dumps(build() if command == "build" else check(), sort_keys=True, allow_nan=False))
