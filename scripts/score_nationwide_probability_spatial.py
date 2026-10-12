"""Write-once 2024 development FSS for sealed nationwide warning fields.

Commands: prepare, write, check, deep. No fitting, threshold selection, 2025
pairing or 2026 observation access occurs here.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.app.ml.nationwide_research import comparable_mask  # noqa: E402
from backend.app.ml.probability_spatial import fss_from_sums, warning_fss_components  # noqa: E402
from scripts import nationwide_probability_v2 as v2  # noqa: E402
from scripts import nationwide_probability_v4 as v4  # noqa: E402
from scripts import nationwide_research as national  # noqa: E402

BASE = ROOT / "data/manifests/research_pilot"
PROTOCOL = BASE / "nationwide_probability_spatial_protocol_v1.json"
RESULT = BASE / "nationwide_probability_spatial_result_v1.json"
ARMS = ("v1", "v2", "v4")
HEADS = {"heavy": 64.5, "very_heavy": 115.6}
SIZES = (1, 3, 5)
CUTOFF = 0.05


def _source_hashes() -> dict[str, str]:
    return {
        "national_feature_manifest_sha256": national.sha(national.FEATURES),
        "national_land_mask_sha256": national.sha(national.OUT / "research_land_mask.npy"),
        "v1_fit_seal_sha256": national.sha(national.SEAL),
        "v1_score_sha256": national.sha(national.SCORE),
        "v2_fit_seal_sha256": national.sha(v2.SEAL),
        "v2_score_sha256": national.sha(v2.SCORE),
        "v4_fit_seal_sha256": national.sha(v4.SEAL),
        "v4_score_sha256": national.sha(v4.SCORE),
        "imd_2024_annual_sha256": national.sha(national.IMD / "RF25_ind2024_rfp25.nc"),
    }


def _protocol() -> dict:
    if national.receipt(PROTOCOL) != national.sha(PROTOCOL):
        raise ValueError("warning FSS protocol receipt changed")
    protocol = json.loads(PROTOCOL.read_text(encoding="utf-8"))
    if (protocol.get("status") != "FROZEN_BEFORE_THIS_DIAGNOSTIC_PAIRING"
            or protocol.get("source_hashes") != _source_hashes()
            or protocol.get("code_sha256") != {
                "runner": national.sha(Path(__file__)),
                "math": national.sha(ROOT / "backend/app/ml/probability_spatial.py"),
            }
            or protocol.get("forecast_probability_cutoff") != CUTOFF
            or protocol.get("rain_thresholds_mm_24h") != HEADS
            or protocol.get("neighborhood_cells") != list(SIZES)):
        raise ValueError("warning FSS protocol/code/source mismatch")
    return protocol


def prepare() -> dict:
    if PROTOCOL.exists() or RESULT.exists():
        raise FileExistsError("warning FSS protocol or result already exists")
    national.check()
    v2.check()
    v4.check()
    _, features, mask = national._feature_manifest()
    protocol = {
        "schema": "nationwide-probability-spatial-protocol-v1",
        "status": "FROZEN_BEFORE_THIS_DIAGNOSTIC_PAIRING",
        "date": "2026-10-09",
        "role": "consumed_2024_development_spatial_diagnostic_only",
        "source_track": "Track_B_operational_GEFS_c00",
        "cases": sum(row["year"] == 2024 for row in features["cases"]),
        "research_land_cells": int(mask.sum()),
        "arms": list(ARMS),
        "rain_thresholds_mm_24h": HEADS,
        "forecast_probability_cutoff": CUTOFF,
        "cutoff_provenance": "Previously fixed common 0.05 comparator in frozen v4 protocol/score; no new threshold choice",
        "neighborhood_cells": list(SIZES),
        "spatial_rule": "Aligned 129x135 fields; identical reference-valid forecast cells for all arms; 50% in-domain neighborhood valid fraction; constant-zero convolution outside grid; masked cells excluded from numerator and denominator; aggregate numerator/denominator across cases",
        "verification": "Compare one-cell FSS with frozen common-0.05 contingency counts; report aggregate and lead FSS, valid centers, contributors and 1000 paired initialization-date bootstrap deltas v4-v1/v2",
        "uncertainty": {"unit": "initialization_date", "repeats": 1000, "seed": 26080,
                        "caveat": "date bootstrap does not remove spatial or serial dependence"},
        "source_hashes": _source_hashes(),
        "code_sha256": {"runner": national.sha(Path(__file__)),
                        "math": national.sha(ROOT / "backend/app/ml/probability_spatial.py")},
        "reference_values_read_by_prepare": False,
        "prior_2024_reference_consumed": True,
        "2025_2026_observations_excluded": True,
        "decision": "descriptive FSS only; failed v4 Brier gate and regional M2 default unchanged",
    }
    digest = national.write_json(PROTOCOL, protocol)
    return {"status": protocol["status"], "protocol_sha256": digest}


def _sum_records(records: list[dict]) -> dict:
    numerator = float(sum(row["numerator"] for row in records))
    denominator = float(sum(row["denominator"] for row in records))
    return {
        "fss": fss_from_sums(numerator, denominator),
        "numerator": numerator,
        "denominator": denominator,
        "contributing_cases": sum(row["denominator"] > 0 for row in records),
        "eligible_centers": sum(row["eligible_centers"] for row in records),
        "paired_cells": sum(row["paired_cells"] for row in records),
        "forecast_events": sum(row["forecast_events"] for row in records),
        "observed_events": sum(row["observed_events"] for row in records),
        "hits": sum(row["hits"] for row in records),
    }


def _bootstrap(records: list[dict], *, seed: int, repeats: int) -> dict:
    dates = sorted({row["case_id"][:8] for row in records})
    per_date = {date: {arm: [0.0, 0.0] for arm in ARMS} for date in dates}
    for row in records:
        sums = per_date[row["case_id"][:8]][row["arm"]]
        sums[0] += row["numerator"]
        sums[1] += row["denominator"]
    array = np.asarray([[per_date[date][arm] for arm in ARMS] for date in dates], dtype=np.float64)
    draws = np.random.default_rng(seed).integers(0, len(dates), size=(repeats, len(dates)))
    sample = array[draws].sum(axis=1)
    if np.any(sample[:, :, 1] <= 0):
        return {"status": "undefined_bootstrap_denominator", "initialization_dates": len(dates)}
    scores = 1 - sample[:, :, 0] / sample[:, :, 1]
    return {
        "status": "defined",
        "initialization_dates": len(dates),
        "v4_minus_v1_ci95": np.quantile(scores[:, 2] - scores[:, 0], (0.025, 0.975)).tolist(),
        "v4_minus_v2_ci95": np.quantile(scores[:, 2] - scores[:, 1], (0.025, 0.975)).tolist(),
    }


def compute() -> dict:
    protocol = _protocol()
    national.check()
    v2.check()
    v4.check()
    _, features, mask = national._feature_manifest()
    by_case = {row["case_id"]: row for row in features["cases"] if row["year"] == 2024}
    v1_seal = json.loads(national.SEAL.read_text(encoding="utf-8"))
    _, v2_seal = v2._sealed()
    _, v4_seal, _ = v4._sealed()
    source_rows = {
        "v1": {row["case_id"]: row for row in v1_seal["predictions"]},
        "v2": {row["case_id"]: row for row in v2_seal["predictions"]},
        "v4": {row["case_id"]: row for row in v4_seal["predictions"]},
    }
    population = set(by_case)
    if len(population) != protocol["cases"] or any(set(rows) != population for rows in source_rows.values()):
        raise ValueError("warning FSS case population differs across arms")
    records: list[dict] = []
    for case_id in sorted(population):
        row = by_case[case_id]
        x, _ = national._load_x(row)
        truth = national._reference(2024, case_id, row["hour"])
        raw = np.full(national.GRID_SHAPE, np.nan, dtype=np.float32)
        raw[mask] = x[:, 0]
        valid = comparable_mask(mask, raw, truth.rainfall_mm, truth.valid_mask)
        if not np.array_equal(valid[mask], truth.valid_mask[mask]):
            raise ValueError(f"warning FSS eligible cells changed: {case_id}")
        archives = {}
        try:
            for arm in ARMS:
                prediction_row = source_rows[arm][case_id]
                path = ROOT / prediction_row["file"]
                if national.sha(path) != prediction_row["sha256"]:
                    raise ValueError(f"warning FSS source prediction changed: {arm}/{case_id}")
                archives[arm] = np.load(path, allow_pickle=False)
            for head, rain_threshold in HEADS.items():
                for arm in ARMS:
                    values = np.asarray(archives[arm][head + "_p"], dtype=np.float64)
                    if values.shape != (int(mask.sum()),):
                        raise ValueError(f"warning FSS probability shape changed: {arm}/{case_id}/{head}")
                    field = np.full(national.GRID_SHAPE, np.nan, dtype=np.float64)
                    field[mask] = values
                    for size in SIZES:
                        part = warning_fss_components(
                            field, truth.rainfall_mm, valid,
                            probability_cutoff=CUTOFF, rain_threshold_mm=rain_threshold,
                            size=size,
                        )
                        records.append({"case_id": case_id, "lead": row["hour"],
                                        "head": head, "arm": arm, "size": size, **part})
        finally:
            for archive in archives.values():
                archive.close()
    frozen = json.loads(v4.SCORE.read_text(encoding="utf-8"))
    metrics = {}
    for head in HEADS:
        metrics[head] = {}
        for size in SIZES:
            scoped = [record for record in records if record["head"] == head and record["size"] == size]
            arms = {arm: _sum_records([record for record in scoped if record["arm"] == arm]) for arm in ARMS}
            if len({block["paired_cells"] for block in arms.values()}) != 1 or len({block["eligible_centers"] for block in arms.values()}) != 1:
                raise ValueError(f"warning FSS population/centers differ: {head}/{size}")
            if size == 1:
                for arm, block in arms.items():
                    frozen_counts = frozen["heads"][head]["common_0p05_categorical"][arm]
                    if any(block[key] != frozen_counts[frozen_key] for key, frozen_key in (
                        ("paired_cells", "sample_count"), ("forecast_events", "forecast_event_count"),
                        ("observed_events", "observed_event_count"), ("hits", "hits"),
                    )):
                        raise ValueError(f"warning FSS one-cell contingency mismatch: {arm}/{head}")
                    expected_fss = (2 * block["hits"] / (block["forecast_events"] + block["observed_events"])
                                    if block["forecast_events"] + block["observed_events"] else None)
                    if expected_fss is not None and not np.isclose(block["fss"], expected_fss, atol=1e-12):
                        raise ValueError(f"warning FSS one-cell formula mismatch: {arm}/{head}")
            lead = {str(hour): {arm: _sum_records([record for record in scoped if record["arm"] == arm and record["lead"] == hour])
                                for arm in ARMS} for hour in (24, 48, 72)}
            metrics[head][str(size)] = {"arms": arms, "lead": lead,
                                        "date_bootstrap": _bootstrap(scoped, seed=protocol["uncertainty"]["seed"],
                                                                     repeats=protocol["uncertainty"]["repeats"])}
    return {
        "schema": "nationwide-probability-spatial-result-v1",
        "status": "CONSUMED_2024_DEVELOPMENT_SPATIAL_DIAGNOSTIC_ONLY",
        "protocol_sha256": national.sha(PROTOCOL),
        "case_count": len(population),
        "paired_cells_per_arm_head": metrics["heavy"]["1"]["arms"]["v1"]["paired_cells"],
        "metrics": metrics,
        "case_sums": records,
        "frozen_common_cutoff_contingency_reproduced": True,
        "2025_2026_reference_values_read_by_diagnostic": False,
        "v4_brier_gate_unchanged": "FAILED",
        "product_default_unchanged": "regional_M2",
        "public_warning_allowed": False,
    }


def write() -> dict:
    if RESULT.exists() or RESULT.with_suffix(".sha256").exists():
        raise FileExistsError("warning FSS result is write-once")
    report = compute()
    digest = national.write_json(RESULT, report)
    return {"status": report["status"], "result_sha256": digest,
            "cases": report["case_count"], "paired_cells": report["paired_cells_per_arm_head"]}


def check(*, deep: bool = False) -> dict:
    _protocol()
    if not RESULT.exists():
        return {"status": "WARNING_FSS_PROTOCOL_VERIFIED", "protocol_sha256": national.sha(PROTOCOL)}
    if national.receipt(RESULT) != national.sha(RESULT):
        raise ValueError("warning FSS result receipt changed")
    report = json.loads(RESULT.read_text(encoding="utf-8"))
    if report.get("protocol_sha256") != national.sha(PROTOCOL) or report.get("v4_brier_gate_unchanged") != "FAILED":
        raise ValueError("warning FSS result scope changed")
    if deep and report != compute():
        raise ValueError("warning FSS field recomputation differs")
    return {"status": "WARNING_FSS_REPRODUCED" if deep else "WARNING_FSS_HASH_VERIFIED",
            "protocol_sha256": national.sha(PROTOCOL), "result_sha256": national.sha(RESULT)}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("prepare", "write", "check", "deep"))
    args = parser.parse_args()
    print(json.dumps({"prepare": prepare, "write": write, "check": check,
                      "deep": lambda: check(deep=True)}[args.command](), sort_keys=True))
