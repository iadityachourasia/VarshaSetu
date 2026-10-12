"""One-shot 2026 Track B verification, gated on an authorized IMD file and version review.

--preflight reads only manifests/metadata and reports open gates. --score reads
the IMD reference only after all gates pass. A blocked run writes no score.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

import numpy as np
from scipy.io import netcdf_file

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.app.live.pipeline import TARGET_LAT, TARGET_LON  # noqa: E402
from backend.app.ml.track_b_2026_scoring import LEADS, MODELS, score_cases  # noqa: E402
from scripts.run_2026_frozen_inference import OUT as FORECASTS, sha, sealed, verify_output  # noqa: E402
from scripts.summarize_gefs_version_partition import partition  # noqa: E402

BASE = ROOT / "data/manifests/research_pilot"
PROTOCOL = BASE / "2026_track_b_score_protocol_v1.json"
RESULT = BASE / "2026_track_b_score_v1.json"
REFERENCE_CLEARANCE = BASE / "2026_imd_reference_clearance_v1.json"
VERSION_CLEARANCE = BASE / "2026_gefs_version_clearance_v1.json"
IMD = ROOT / "experiments/recent_historical/imd/RF25_ind2026_rfp25.nc"
SELECTION = ROOT / "experiments/recent_historical/phase4i_operational_model_development_v1/final_freeze/model_selection_freeze.json"
FORECAST_YEAR = BASE / "2026_frozen_inference_year_v1.json"
EVALUATION = BASE / "2026_track_b_evaluation_protocol_v1.json"
LEAD_DAYS = {"day1_24h": 1, "day2_24h": 2, "day3_24h": 3}


def _json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def preflight() -> dict:
    reasons = []
    try:
        protocol = sealed(PROTOCOL)
        expected = {"forecast_year_sha256": sha(FORECAST_YEAR), "evaluation_protocol_sha256": sha(EVALUATION),
                    "selection_sha256": sha(SELECTION), "scorer_sha256": sha(Path(__file__)),
                    "pure_scoring_sha256": sha(ROOT / "backend/app/ml/track_b_2026_scoring.py")}
        if any(protocol[k] != digest for k, digest in expected.items()):
            reasons.append("SCORING_PROTOCOL_OR_INPUT_HASH_CHANGED")
        if protocol["status"] != "FROZEN_BEFORE_2026_OBSERVATION_PAIRING":
            reasons.append("SCORING_PROTOCOL_NOT_FROZEN")
    except (OSError, KeyError, ValueError):
        reasons.append("SCORING_PROTOCOL_OR_INPUT_SEAL_MISSING")
    try:
        forecast = sealed(FORECAST_YEAR)
        if forecast["cycle_count"] != 122 or sum(forecast["strict_qc_inferred_leads"].values()) != 213 or forecast["observation_read"] is not False:
            reasons.append("FORECAST_YEAR_SEAL_INCOMPLETE")
    except (OSError, KeyError, ValueError):
        reasons.append("FORECAST_YEAR_SEAL_MISSING_OR_CHANGED")
    try:
        audit = sealed(BASE / "2026_prior_observation_use_audit_v2.json")
        if audit.get("prior_use_gate") != "PROVISIONALLY_CLEARED_BY_TEAM_ATTESTATION_AND_LOCAL_AUDIT":
            reasons.append("PRIOR_2026_OBSERVATION_USE_REVIEW_REQUIRED")
    except (OSError, ValueError):
        reasons.append("PRIOR_2026_OBSERVATION_USE_AUDIT_MISSING")
    if not REFERENCE_CLEARANCE.exists():
        reasons.append("IMD_2026_REFERENCE_CLEARANCE_MISSING")
    else:
        try:
            ref = sealed(REFERENCE_CLEARANCE)
            if ref["status"] != "APPROVED_FOR_LOCAL_RESEARCH_VERIFICATION" or ref["accumulation_window_utc"] != "03:00-03:00" or not ref.get("source_url_or_receipt"):
                reasons.append("IMD_2026_REFERENCE_CLEARANCE_INCOMPLETE")
            elif not IMD.is_file() or sha(IMD) != ref["file_sha256"]:
                reasons.append("IMD_2026_REFERENCE_FILE_MISSING_OR_CHANGED")
        except (OSError, KeyError, ValueError):
            reasons.append("IMD_2026_REFERENCE_CLEARANCE_INVALID")
    if not VERSION_CLEARANCE.exists():
        reasons.append("GEFS_2026_VERSION_REVIEW_MISSING")
    else:
        try:
            version = sealed(VERSION_CLEARANCE)
            if version["status"] != "MODEL_VERSION_REVIEW_COMPLETE" or not version.get("authoritative_evidence_uri_or_hash") or not version.get("actual_transition_utc"):
                reasons.append("GEFS_2026_VERSION_REVIEW_INCOMPLETE")
        except (OSError, KeyError, ValueError):
            reasons.append("GEFS_2026_VERSION_REVIEW_INVALID")
    return {"status": "READY_TO_PAIR" if not reasons else "BLOCKED_BEFORE_OBSERVATION_READ",
            "reasons": reasons, "forecast_cases": 213, "observation_read": False}


class ImdYear:
    """Bounded one-open IMD reader; grid values are copied before close."""

    def __init__(self, path: Path):
        self.dataset = netcdf_file(path, "r", mmap=True)
        variables = self.dataset.variables
        if not {"TIME", "LATITUDE", "LONGITUDE", "RAINFALL"}.issubset(variables):
            self.close()
            raise ValueError("IMD NetCDF missing required variables")
        time = variables["TIME"]
        units = getattr(time, "units")
        units = units.decode("utf-8") if isinstance(units, bytes) else str(units)
        if not units.startswith("days since "):
            self.close()
            raise ValueError("unsupported IMD time units")
        self.origin = datetime.fromisoformat(units[len("days since "):])
        self.times = np.asarray(time.data, dtype=np.float64).copy()
        lat = np.asarray(variables["LATITUDE"].data, dtype=np.float64)
        lon = np.asarray(variables["LONGITUDE"].data, dtype=np.float64)
        li = np.flatnonzero((lat >= 10) & (lat <= 22))
        lj = np.flatnonzero((lon >= 68) & (lon <= 80))
        if len(li) != 49 or len(lj) != 49 or not np.array_equal(lat[li], TARGET_LAT) or not np.array_equal(lon[lj], TARGET_LON):
            self.close()
            raise ValueError("IMD grid differs from the frozen regional target")
        self.li, self.lj = li, lj
        rain = variables["RAINFALL"]
        self.fill = float(getattr(rain, "_FillValue"))
        if self.fill != float(getattr(rain, "missing_value")):
            self.close()
            raise ValueError("IMD fill/missing metadata differ")
        self.rain = rain
        self.cache: dict[date, tuple[np.ndarray, np.ndarray]] = {}

    def day(self, valid: date) -> tuple[np.ndarray, np.ndarray]:
        if valid not in self.cache:
            offset = (datetime.combine(valid, datetime.min.time()) - self.origin).days
            indices = np.flatnonzero(np.isclose(self.times, offset, atol=1e-9, rtol=0))
            if len(indices) != 1:
                raise ValueError(f"IMD date missing or duplicated: {valid}")
            field = np.asarray(self.rain.data[int(indices[0]), self.li[0]:self.li[-1] + 1, self.lj[0]:self.lj[-1] + 1], dtype=np.float64).copy()
            mask = np.isfinite(field) & (field != self.fill)
            if np.any(field[mask] < 0):
                raise ValueError(f"negative IMD rainfall on {valid}")
            self.cache[valid] = field, mask
        return self.cache[valid]

    def close(self) -> None:
        self.rain = None
        self.dataset.close()

    def __enter__(self) -> ImdYear:
        return self

    def __exit__(self, *_exc) -> None:
        self.close()


def score_once() -> dict:
    gate = preflight()
    if gate["status"] != "READY_TO_PAIR":
        raise RuntimeError("2026 scoring blocked before observation read: " + ", ".join(gate["reasons"]))
    if RESULT.exists():
        raise RuntimeError("2026 score already exists: one-shot")
    forecast_year = sealed(FORECAST_YEAR)
    protocol = sealed(PROTOCOL)
    selection = _json(SELECTION)
    cases = []
    with ImdYear(IMD) as reference:
        for cycle in sorted(forecast_year["case_manifest_sha256"]):
            folder = FORECASTS / cycle
            manifest = verify_output(folder, sha(ROOT / "data/processed/gefs_2026_forecast_only_v1" / cycle / "manifest.json"),
                                     forecast_year["protocol_sha256"], forecast_year["model_artifact_sha256"])
            if sha(folder / "manifest.json") != forecast_year["case_manifest_sha256"][cycle]:
                raise ValueError(f"forecast manifest changed: {cycle}")
            for lead, meta in sorted(manifest["products"].items()):
                valid = date.fromisoformat(f"{cycle[:4]}-{cycle[4:6]}-{cycle[6:8]}") + timedelta(days=LEAD_DAYS[lead])
                observed, mask = reference.day(valid)
                if not mask.any():
                    raise ValueError(f"no valid IMD cells: {cycle}/{lead}")
                with np.load(folder / f"{lead}.npz", allow_pickle=False) as saved:
                    array = {name: saved[name].reshape(49, 49) if name != "regime_probability" else saved[name].copy() for name in saved.files}
                cases.append({"cycle": cycle, "lead": lead, "version_stratum": partition(cycle, "2026-06-15T12:00:00Z"),
                              "observed": observed, "valid_mask": mask, "rainfall": {name: array[name] for name in MODELS},
                              "heavy_probability": array["heavy_probability"], "very_heavy_probability": array["very_heavy_probability"],
                              "regime_probability": array["regime_probability"],
                              "nested_probability_violating_cells": meta["nested_probability_violating_cells"]})
    if len(cases) != 213:
        raise ValueError("paired population differs from the 213 sealed forecast leads")
    metrics = score_cases(cases,
                          climatology={name: selection[name]["bss_reference_2023"] for name in ("heavy", "very_heavy")},
                          probability_cutoffs={name: selection[name]["threshold"] for name in ("heavy", "very_heavy")},
                          repeats=protocol["bootstrap_replicates"], seed=protocol["bootstrap_seed"])
    result = {"schema": "varshasetu-2026-track-b-score-v1", "status": "SCORED_ONCE_NO_AUTOMATIC_PROMOTION",
              "scoring_protocol_sha256": sha(PROTOCOL), "forecast_year_sha256": sha(FORECAST_YEAR),
              "imd_reference_sha256": sha(IMD), "imd_clearance_sha256": sha(REFERENCE_CLEARANCE),
              "gefs_version_review_sha256": sha(VERSION_CLEARANCE), "case_count": len(cases),
              "paired_cell_count": metrics["overall"]["paired_cells"], "metrics": metrics,
              "model_default_after_score": "M2_UNCHANGED_PENDING_FORECASTER_GOVERNANCE"}
    stage = RESULT.with_name(RESULT.name + ".stage")
    with stage.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(result, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write("\n")
    if RESULT.exists():
        raise RuntimeError("2026 score appeared during staging")
    stage.rename(RESULT)
    RESULT.with_suffix(".sha256").write_text(f"{sha(RESULT)}  {RESULT.name}\n", encoding="ascii")
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--preflight", action="store_true")
    group.add_argument("--score", action="store_true")
    args = parser.parse_args()
    if args.preflight:
        print(json.dumps(preflight(), sort_keys=True))
    else:
        result = score_once()
        print(json.dumps({"status": result["status"], "sha256": sha(RESULT), "case_count": result["case_count"],
                          "paired_cell_count": result["paired_cell_count"], "regime_promotion_eligible": result["metrics"]["regime_promotion_eligible"]}, sort_keys=True))


if __name__ == "__main__":
    main()
