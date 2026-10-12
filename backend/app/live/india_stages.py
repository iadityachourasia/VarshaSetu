"""Research-only, bounded extension of a corrected grid beyond the model box.

This module does not fit or transfer a model. A caller must supply a correction
trained for the declared stage. Forecast construction cannot read observations;
pairing and verification are separate operations.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from backend.app.ml.all_india_raw import IMD_BOUNDS, region_masks


IMD_LAT = np.arange(IMD_BOUNDS["south"], IMD_BOUNDS["north"] + 0.125, 0.25)
IMD_LON = np.arange(IMD_BOUNDS["west"], IMD_BOUNDS["east"] + 0.125, 0.25)
GRID_SHAPE = (129, 135)
THRESHOLDS_MM = {"heavy": 64.5, "very_heavy": 115.6}
FIRST_STAGE = "EAST_COAST_PENINSULA"
MIN_CASES = 30
MIN_OBSERVED_EVENTS = 30
MIN_DISTRICT_COVERAGE = 0.95
MIN_SUPPORTED_DISTRICT_FRACTION = 0.90


@dataclass(frozen=True)
class StageLineage:
    case_id: str
    source_sha256: str
    model_sha256: str
    model_training_domain: str
    land_mask_sha256: str


def _hash(value: str) -> bool:
    return len(value) == 64 and all(character in "0123456789abcdef" for character in value)


def stage_mask(stage: str, land_mask: np.ndarray) -> np.ndarray:
    """Use the frozen Raw-verification partition and a forecast-time static mask."""
    if stage != FIRST_STAGE:
        raise ValueError("only the first bounded geographic stage is defined")
    land = np.asarray(land_mask)
    if land.shape != GRID_SHAPE or land.dtype != np.bool_:
        raise ValueError("static land mask must be a boolean IMD-grid field")
    return region_masks(IMD_LAT, IMD_LON)[stage].reshape(GRID_SHAPE) & land


def forecast_field(
    stage: str,
    land_mask: np.ndarray,
    raw: np.ndarray,
    global_corrected: np.ndarray,
    valid_mask: np.ndarray,
    lineage: StageLineage,
) -> dict:
    """Retain only jointly valid forecast cells; refuse cross-domain model transfer."""
    if not lineage.case_id or any(not _hash(value) for value in (lineage.source_sha256, lineage.model_sha256, lineage.land_mask_sha256)):
        raise ValueError("forecast source, model and static-mask hashes are required")
    if lineage.model_training_domain != stage:
        raise ValueError("correction model was not trained for this geographic stage")
    footprint = stage_mask(stage, land_mask)
    valid = np.asarray(valid_mask)
    if valid.shape != GRID_SHAPE or valid.dtype != np.bool_ or np.any(valid & ~footprint):
        raise ValueError("forecast validity must stay inside the stage land footprint")
    if not valid.any():
        raise ValueError("stage contains no valid forecast cells")
    fields = {}
    for name, value in (("raw", raw), ("global_corrected", global_corrected)):
        field = np.asarray(value, dtype=np.float64)
        if field.shape != GRID_SHAPE or not np.isfinite(field[valid]).all() or np.any(field[valid] < 0) or not np.isnan(field[~valid]).all():
            raise ValueError(f"{name} must be nonnegative on exactly the same valid cells")
        fields[name] = field.copy()
    return {"stage": stage, "lineage": lineage, "footprint": footprint, "valid_mask": valid.copy(), "fields": fields,
            "eligible_cells": int(footprint.sum()), "valid_cells": int(valid.sum())}


def pair_reference(forecast: dict, observation: np.ndarray, observation_mask: np.ndarray) -> dict:
    """Retrospective same-cell pair; observations never enter forecast_field."""
    obs = np.asarray(observation, dtype=np.float64)
    obs_valid = np.asarray(observation_mask)
    if obs.shape != GRID_SHAPE or obs_valid.shape != GRID_SHAPE or obs_valid.dtype != np.bool_:
        raise ValueError("observation and mask must use the IMD grid")
    if not np.isfinite(obs[obs_valid]).all() or np.any(obs[obs_valid] < 0) or not np.isnan(obs[~obs_valid]).all():
        raise ValueError("observation values and validity disagree")
    paired = forecast["valid_mask"] & obs_valid
    if not paired.any():
        raise ValueError("no forecast/reference paired cells")
    raw = forecast["fields"]["raw"][paired]
    corrected = forecast["fields"]["global_corrected"][paired]
    truth = obs[paired]
    events = {name: int(np.count_nonzero(truth >= threshold)) for name, threshold in THRESHOLDS_MM.items()}
    return {"case_id": forecast["lineage"].case_id, "stage": forecast["stage"],
            "source_sha256": forecast["lineage"].source_sha256, "model_sha256": forecast["lineage"].model_sha256,
            "paired_mask": paired,
            "paired_cells": int(paired.sum()), "observed_events": events,
            "raw_squared_error": float(np.sum((raw - truth) ** 2)),
            "global_squared_error": float(np.sum((corrected - truth) ** 2))}


def district_rows(forecast: dict, districts: list[dict], weights: np.ndarray) -> list[dict]:
    """Withhold district values below weighted forecast coverage."""
    valid = forecast["valid_mask"].ravel()
    matrix = np.asarray(weights, dtype=np.float64)
    if (matrix.shape != (len(districts), valid.size) or not np.isfinite(matrix).all() or np.any(matrix < 0)
            or np.any(matrix[:, ~forecast["footprint"].ravel()] > 0)):
        raise ValueError("district weights or coverage gate are invalid")
    rows = []
    for district, weight in zip(districts, matrix):
        if not district.get("district_id") or not district.get("district_name") or weight.sum() <= 0:
            raise ValueError("district identity or intersecting area is missing")
        coverage = float(weight[valid].sum() / weight.sum())
        supported = coverage >= MIN_DISTRICT_COVERAGE
        row = {"district_id": district["district_id"], "district_name": district["district_name"],
               "coverage_fraction": coverage, "supported": supported, "raw_mean_mm": None, "global_mean_mm": None}
        if supported:
            local = weight[valid] / weight[valid].sum()
            row["raw_mean_mm"] = float(local @ forecast["fields"]["raw"].ravel()[valid])
            row["global_mean_mm"] = float(local @ forecast["fields"]["global_corrected"].ravel()[valid])
        rows.append(row)
    return rows


def evidence_gate(pairs: list[dict], district_tables: dict[str, list[dict]], *, independent_year: bool, consumed_test: bool,
                  geometry_version: str, geometry_sha256: str, rights_reviewed: bool) -> dict:
    """A conservative gate for even considering a staged research product."""
    if (not pairs or len({row["case_id"] for row in pairs}) != len(pairs)
            or len({row["stage"] for row in pairs}) != 1
            or len({row["model_sha256"] for row in pairs}) != 1
            or set(district_tables) != {row["case_id"] for row in pairs}):
        raise ValueError("paired cases must be unique, one stage/model and have matching district tables")
    count = sum(row["paired_cells"] for row in pairs)
    if count <= 0 or any(row["paired_cells"] <= 0 for row in pairs):
        raise ValueError("paired-cell support is invalid")
    events = {name: sum(row["observed_events"][name] for row in pairs) for name in THRESHOLDS_MM}
    reasons = []
    if len(pairs) < MIN_CASES or any(value < MIN_OBSERVED_EVENTS for value in events.values()):
        reasons.append("insufficient paired-case or observed-event support")
    district_support = {}
    for case_id, table in district_tables.items():
        if not table or len({row["district_id"] for row in table}) != len(table):
            raise ValueError(f"{case_id}: district table is empty or has duplicate IDs")
        if any(not 0 <= row["coverage_fraction"] <= 1 for row in table):
            raise ValueError(f"{case_id}: invalid district coverage")
        if any(row["supported"] != (row["coverage_fraction"] >= MIN_DISTRICT_COVERAGE) for row in table):
            raise ValueError(f"{case_id}: district support disagrees with coverage")
        district_support[case_id] = sum(bool(row["supported"]) for row in table)
    if any(count / len(district_tables[case_id]) < MIN_SUPPORTED_DISTRICT_FRACTION for case_id, count in district_support.items()):
        reasons.append("a case has fewer than 90% of its stage districts above the weighted coverage gate")
    if not independent_year or consumed_test:
        reasons.append("no untouched independent evaluation year")
    if not geometry_version or not _hash(geometry_sha256) or not rights_reviewed:
        reasons.append("district geometry version, hash or redistribution rights review missing")
    return {"stage": pairs[0]["stage"], "model_sha256": pairs[0]["model_sha256"], "cases": len(pairs),
            "paired_cells": count, "observed_events": events, "districts_supported_per_case": district_support,
            "raw_rmse_mm": float(np.sqrt(sum(row["raw_squared_error"] for row in pairs) / count)),
            "global_rmse_mm": float(np.sqrt(sum(row["global_squared_error"] for row in pairs) / count)),
            "eligible_for_review": not reasons, "reasons": reasons}
