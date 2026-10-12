"""Append-only lead breakdown of the sealed, consumed-2024 development score."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.app.ml.phase2b import continuous_metrics, event_metrics  # noqa: E402
from scripts.build_east_coast_static import BASE, OUTPUT as STATIC, sha256  # noqa: E402
from scripts.run_east_coast_development import (FIT, GRID_SHAPE, OUTPUT, RESULT,  # noqa: E402
                                                 ROOT, RAW_LEDGER, preflight, receipt, reference, write_once)

REPORT = BASE / "east_coast_lead_breakdown_v1.json"


def build() -> dict:
    if REPORT.exists() or REPORT.with_suffix(".sha256").exists():
        raise FileExistsError("lead breakdown is write-once")
    _, ledger, mask, _ = preflight()
    fit_hash, result_hash = receipt(FIT), receipt(RESULT)
    sealed = json.loads(FIT.read_text(encoding="utf-8"))
    result = json.loads(RESULT.read_text(encoding="utf-8"))
    if result["fit_seal_sha256"] != fit_hash or sealed["model_sha256"] != result["model_sha256"]:
        raise ValueError("fit/result lineage mismatch")
    raw_rows = {row["case_id"]: row for row in ledger["populations"]["2024"] if row["status"] == "INCLUDED"}
    groups = {24: {"raw": [], "global": [], "observed": []},
              48: {"raw": [], "global": [], "observed": []},
              72: {"raw": [], "global": [], "observed": []}}
    for row in sealed["forecasts"]:
        case_id, hour = row["case_id"], row["lead_hours"]
        raw_row = raw_rows[case_id]
        raw_path = ROOT / raw_row["path"]
        global_path = ROOT / row["file"]
        if sha256(raw_path) != row["raw_sha256"] or sha256(global_path) != row["sha256"]:
            raise ValueError(f"case source/prediction changed: {case_id}")
        raw = np.load(raw_path, allow_pickle=False)
        global_field = np.load(global_path, allow_pickle=False)
        observed = reference(2024, case_id, hour)
        valid = mask & observed.valid_mask & np.isfinite(raw) & (raw >= 0) & np.isfinite(global_field) & (global_field >= 0)
        if not valid.any() or raw.shape != GRID_SHAPE or global_field.shape != GRID_SHAPE:
            raise ValueError(f"invalid lead population: {case_id}")
        groups[hour]["raw"].append(raw[valid])
        groups[hour]["global"].append(global_field[valid])
        groups[hour]["observed"].append(observed.rainfall_mm[valid])
    leads = {}
    aggregate = {name: [] for name in ("raw", "global", "observed")}
    for hour, group in groups.items():
        truth = np.concatenate(group["observed"])
        for name in aggregate:
            aggregate[name].extend(group[name])
        arms = {}
        for name in ("raw", "global"):
            forecast = np.concatenate(group[name])
            events = {}
            for category, threshold in (("heavy", 64.5), ("very_heavy", 115.6)):
                item = event_metrics(truth, forecast, threshold)
                item["frequency_bias"] = item["forecast_event_count"] / item["observed_event_count"] if item["observed_event_count"] else None
                events[category] = item
            arms[name] = {"continuous": continuous_metrics(truth, forecast), "events": events}
        leads[str(hour)] = {"cases": len(group["observed"]), "paired_cells": len(truth), "arms": arms}
    if sum(row["paired_cells"] for row in leads.values()) != result["same_cell_population"]:
        raise ValueError("lead cells do not sum to sealed aggregate")
    for name in ("raw", "global"):
        check = continuous_metrics(np.concatenate(aggregate["observed"]), np.concatenate(aggregate[name]))
        if abs(check["rmse_mm"] - result["metrics"][name]["continuous"]["rmse_mm"]) > 1e-12:
            raise ValueError("lead/aggregate RMSE does not reproduce")
    report = {"schema": "varshasetu-east-coast-lead-breakdown-v1",
              "status": "CONSUMED_2024_DEVELOPMENT_DIAGNOSTIC_ONLY", "fit_seal_sha256": fit_hash,
              "result_sha256": result_hash, "leads": leads,
              "claim": "No independent year; no stage-product promotion or operational skill claim"}
    write_once(REPORT, report)
    return {"status": report["status"], "leads": {key: {"cases": value["cases"], "cells": value["paired_cells"]}
                                                     for key, value in leads.items()}}


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    if args.check:
        value = json.loads(REPORT.read_text(encoding="utf-8"))
        if value["fit_seal_sha256"] != receipt(FIT) or value["result_sha256"] != receipt(RESULT):
            raise ValueError("lead lineage mismatch")
        output = {"status": "VERIFIED_RECEIPTS", "lead_breakdown_sha256": receipt(REPORT)}
    else:
        output = build()
    print(json.dumps(output, sort_keys=True))
