"""Read-only Phase 5A.1 presentation API over the frozen operational-era (2023-2025)
historical GEFS + IMD corpus under experiments/recent_historical/.

This module never trains, recalibrates, reselects, or re-infers. It only indexes,
reshapes (scatter of already-frozen flat arrays into the frozen Phase 2C 49x49
grid via frozen pixel-index arrays), and hash- or fingerprint-verifies artifacts
that were produced by phase4b-phase4l. See docs/92_OPERATIONAL_SCIENCE_PRESENTATION_API.md
for the full contract, known limitations, and the scientific-freeze rationale for
every "unavailable" response below.
"""

from __future__ import annotations

import json
import re
from enum import Enum
from functools import lru_cache
from pathlib import Path
from typing import Any, Literal

import numpy as np
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

try:
    from backend.app.ml.phase2b import ROOT, sha256_file
    from backend.app.api.science import ARTIFACTS as TRACK_A_ARTIFACTS, _grid_metadata, _store as _track_a_store
    from backend.app.ml.district_product import aggregate_operational_districts, district_case_means, flat_field
    from backend.app.data.monthly_qc import context_coordinates
except ModuleNotFoundError:
    from app.ml.phase2b import ROOT, sha256_file
    from app.api.science import ARTIFACTS as TRACK_A_ARTIFACTS, _grid_metadata, _store as _track_a_store
    from app.ml.district_product import aggregate_operational_districts, district_case_means, flat_field
    from app.data.monthly_qc import context_coordinates


class ScienceErrorCode(str, Enum):
    """Structured error codes for /api/science/operational/*. The plain
    HTTPException(status, "message") convention used by the existing
    /api/science/* (Track A) router is untouched -- these codes exist only on
    this router's own exception bodies, via the app-level exception handler in
    main.py that flattens a dict `detail` into a top-level {code, detail} body
    when present, and leaves a plain string `detail` exactly as before."""

    PRODUCT_UNAVAILABLE = "SCIENCE_PRODUCT_UNAVAILABLE"
    CASE_NOT_FOUND = "SCIENCE_CASE_NOT_FOUND"
    CASE_NOT_ELIGIBLE = "SCIENCE_CASE_NOT_ELIGIBLE"
    INTEGRITY_FAILURE = "SCIENCE_INTEGRITY_FAILURE"
    INVALID_FIELD = "SCIENCE_INVALID_FIELD"


def _science_error(status_code: int, code: ScienceErrorCode, message: str) -> HTTPException:
    return HTTPException(status_code=status_code, detail={"code": code.value, "detail": message})

router = APIRouter(prefix="/science/operational", tags=["Operational-era (2023-2025) presentation API"])

EXPERIMENTS_ROOT = ROOT / "experiments" / "recent_historical"
PHASE4F = EXPERIMENTS_ROOT / "phase4f_payload_acquisition_v1"
PHASE4I = EXPERIMENTS_ROOT / "phase4i_operational_model_development_v1"
PHASE4J = EXPERIMENTS_ROOT / "phase4j_operational_final_test_v1"
# Phase 4G's per-year/per-split feature-build output: proven (Phase 5A.1B) to hold
# the exact row_start/row_count/pixel_index ordering that phase4i's flat model
# arrays are written in. Internal split directory names ("train"/"validation"/
# "test_sealed") are pipeline-stage labels from *before* the 2025 holdout was
# unsealed; they are used only as internal lookup keys and are never surfaced in
# any API response (2025's year_role is always reported as FINAL_TEST_COMPLETED).
PHASE4G_ROOT = ROOT / "data" / "operational_derived" / "operational_features_2023_2025_v1"
_PHASE4G_SPLIT: dict[int, str] = {2023: "train", 2024: "validation", 2025: "test_sealed"}

YEARS: tuple[int, ...] = (2023, 2024, 2025)
YEAR_ROLE: dict[int, str] = {2023: "TRAIN_CROSSFIT", 2024: "VALIDATION_SELECTION", 2025: "FINAL_TEST_COMPLETED"}
YEAR_ROLE_LABEL: dict[int, str] = {
    2023: "Training / cross-fit year",
    2024: "Validation / calibration / model-selection year",
    2025: "One-time final historical test (holdout consumed; not sealed or untouched)",
}
CASE_ID_PATTERN = re.compile(r"^(202[345]\d{4})_day([123])_24h$")
LEAD_HOURS_BY_DAY: dict[str, int] = {"1": 24, "2": 48, "3": 72}
FORECAST_HOUR_BY_LEAD: dict[int, str] = {24: "024", 48: "048", 72: "072"}
ATMOSPHERE_FIELDS: tuple[str, ...] = ("u850", "v850", "q700", "z500", "mslp", "pwat")
ENSEMBLE_MEMBERS: tuple[str, ...] = ("c00", "p01", "p02", "p03", "p04")
REGIME_CLASSES: tuple[str, ...] = ("ACTIVE_MONSOON", "BREAK_WEAK_MONSOON", "LOW_DEPRESSION_INFLUENCED")
GRID_CELLS = 49 * 49
# Frozen IMD 24-hour event thresholds (docs/11_SCIENTIFIC_CONSTRAINTS.md); the
# same constants already used throughout phase4i/phase4j's own heavy/very_heavy
# metric definitions.
HEAVY_THRESHOLD_MM = 64.5
VERY_HEAVY_THRESHOLD_MM = 115.6

# ---------------------------------------------------------------------------
# Pydantic response contracts
# ---------------------------------------------------------------------------


class OperationalYearCapabilities(BaseModel):
    year: int
    role: str
    role_label: str
    raw_rainfall: bool
    imd_observation: bool
    m1: Literal["unavailable", "case_grid", "aggregate_metric_only"]
    m2: Literal["unavailable", "out_of_fold_case_grid", "case_grid", "aggregate_metric_only"]
    m3: Literal["unavailable", "case_grid", "aggregate_metric_only"]
    m4: Literal["unavailable", "case_grid", "aggregate_metric_only"]
    heavy_probability: Literal["unavailable", "case_grid", "aggregate_metric_only"]
    very_heavy_probability: Literal["unavailable", "case_grid", "aggregate_metric_only"]
    regime_probability: Literal["unavailable", "per_case", "aggregate_distribution_only"]
    atmosphere_fields: bool
    ensemble_members: Literal["unavailable", "eligible_subset_only"]
    case_level_metrics: bool
    per_cell_metrics: bool
    fss: bool
    reliability_bins: bool
    pr_roc_curve_arrays: Literal["unavailable"] = "unavailable"
    district_aggregates: bool = False
    notes: list[str] = []


class OperationalStatus(BaseModel):
    experiment: str = "operational_gefs_2023_2025"
    label: str = "Historical Operational GEFS (Track B)"
    forecast_source: str = "NOAA operational GEFS (historical archive)"
    observation_source: str = "IMD 0.25 degree gridded rainfall"
    years: dict[str, str]
    api_version: str = "phase5a.1"
    integrity_model: str = "hash-verified where a frozen manifest+digest exists; existence+fingerprint-pinned otherwise"


class OperationalCaseSummary(BaseModel):
    case_id: str
    year: int
    initialization_utc: str
    lead_hours: int
    product: str
    year_role: str
    source_complete: bool
    deterministic_source_eligible: bool
    probability_source_eligible: bool
    regime_source_eligible: bool
    ensemble_source_eligible: bool
    c00_rainfall_qc_pass: bool
    full_5_member_rainfall_qc_pass: bool
    m1_rmse_mm: float | None = None
    raw_rmse_mm: float | None = None
    m1_minus_raw_rmse_mm: float | None = None
    # Phase 5A.2C: presentation-safe selector/casebook metadata, each field
    # left null rather than fabricated when no frozen artifact backs it for
    # that year/case (see docs/96 section 3-4).
    initialization_date: str
    month: int
    lead_label: str
    valid_date: str | None = None
    event_heavy: bool | None = None
    event_very_heavy: bool | None = None
    pseudo_regime_class: str | None = None
    selected_model_improved_vs_raw: bool | None = None


class OperationalCasesResponse(BaseModel):
    year: int
    total: int
    page: int
    page_size: int
    cases: list[OperationalCaseSummary]


class OperationalCaseDetail(OperationalCaseSummary):
    member_qc: dict[str, bool]
    available_products: list[str]


class OperationalDistrictRow(BaseModel):
    district_id: str
    district_name: str
    valid_grid_cells: int
    raw_mean_mm: float
    raw_max_mm: float
    corrected_mean_mm: float
    corrected_max_mm: float
    heavy_probability: float | None = None
    very_heavy_probability: float | None = None
    heavy_area_fraction: float
    very_heavy_area_fraction: float
    observed_mean_mm: float
    observed_max_mm: float
    observed_heavy_area_fraction: float
    observed_very_heavy_area_fraction: float


class OperationalDistrictsResponse(BaseModel):
    case_id: str
    year: int
    year_role: str
    model: str
    model_role: str
    units: str = "mm/24h"
    heavy_threshold_mm: float = HEAVY_THRESHOLD_MM
    very_heavy_threshold_mm: float = VERY_HEAVY_THRESHOLD_MM
    predicted_regime: str | None = None
    districts: list[OperationalDistrictRow]
    source_district_count: int
    method: str
    weights_sha256: str
    geometry_sha256: str
    geometry_source: str = "geoBoundaries IND ADM2 2021"
    geometry_license: str = "ODbL 1.0"
    caveats: list[str]


class OperationalDistrictModelCell(BaseModel):
    mean_mm: float
    max_mm: float
    heavy_area_fraction: float
    very_heavy_area_fraction: float
    error_mm: float                      # model district mean minus IMD district mean
    improvement_vs_raw_mm: float         # |raw mean - IMD mean| - |model mean - IMD mean|; > 0 means closer to IMD than Raw


class OperationalDistrictCompareRow(BaseModel):
    district_id: str
    district_name: str
    valid_grid_cells: int
    raw_mean_mm: float
    raw_max_mm: float
    raw_error_mm: float                  # Raw district mean minus IMD district mean
    observed_mean_mm: float
    observed_max_mm: float
    observed_heavy_area_fraction: float
    observed_very_heavy_area_fraction: float
    heavy_probability: float | None = None
    very_heavy_probability: float | None = None
    models: dict[str, OperationalDistrictModelCell]


class OperationalDistrictCompareResponse(BaseModel):
    case_id: str
    year: int
    year_role: str
    models: list[str]
    model_roles: dict[str, str]
    units: str = "mm/24h"
    heavy_threshold_mm: float = HEAVY_THRESHOLD_MM
    very_heavy_threshold_mm: float = VERY_HEAVY_THRESHOLD_MM
    predicted_regime: str | None = None
    improvement_definition: str
    districts: list[OperationalDistrictCompareRow]
    source_district_count: int
    method: str
    weights_sha256: str
    geometry_sha256: str
    caveats: list[str]


class OperationalDistrictHistoryPoint(BaseModel):
    case_id: str
    initialization_utc: str
    lead_hours: int
    valid_grid_cells: int
    raw_mean_mm: float
    model_mean_mm: float
    observed_mean_mm: float


class OperationalDistrictHistoryResponse(BaseModel):
    year: int
    year_role: str
    district_id: str
    district_name: str
    model: str
    model_role: str
    case_count: int
    points: list[OperationalDistrictHistoryPoint]
    descriptive_only_note: str
    method: str
    weights_sha256: str
    caveats: list[str]


class GridFieldResponse(BaseModel):
    case_id: str
    year: int
    field: str
    units: str
    shape: list[int]
    latitude_centers: list[float] | None = None
    longitude_centers: list[float] | None = None
    values: list[Any]
    valid_mask: list[Any] | None = None
    source: str
    scientific_role: str
    prediction_role: str = "FROZEN_ARCHIVAL_PREDICTION"


class AtmosphericFieldResponse(BaseModel):
    case_id: str
    year: int
    field: str
    pressure_level_hpa: float | None
    forecast_hour: int
    units: str
    shape: list[int]
    values: list[Any]
    latitude_centers: list[float]
    longitude_centers: list[float]
    grid_spacing_degrees: float
    coordinate_note: str = (
        "The frozen artifact stores index-space values only (no per-cell coordinate sidecar). The coordinates returned here are the "
        "frozen context-grid definition (backend/app/data/monthly_qc.context_coordinates: 5-30N, 55-95E, 0.5 degree, row 0 = 5N, column 0 = 55E), "
        "whose alignment with the stored 2024 grids was confirmed against the independently stored Track A coordinates by seasonal-mean "
        "pattern correlation (docs/121). The source grid is approximately 0.5 degree and 51x81; do not assume 0.25 degree resolution."
    )
    source: str = "phase4f_payload_acquisition_v1/atmospheric_qc"


class ProbabilityFieldResponse(BaseModel):
    case_id: str
    year: int
    target: str
    threshold_probability: float
    calibration_type: str
    values: list[Any]
    prediction_role: str = "FROZEN_ARCHIVAL_PREDICTION"


class EnsembleMemberStatus(BaseModel):
    member: str
    qc_eligible: bool
    values: list[Any] | None = None


class EnsembleResponse(BaseModel):
    case_id: str
    year: int
    label: str = "AVAILABLE FIVE-MEMBER SUBSET"
    members: list[EnsembleMemberStatus]


class DeterministicMetricsResponse(BaseModel):
    year: int
    metrics: dict[str, Any]
    primary_model: str | None = None
    notes: list[str] = []


class ProbabilityMetricsResponse(BaseModel):
    year: int
    metrics: dict[str, Any]
    curve_arrays: Literal["unavailable"] = "unavailable"


class FSSResponse(BaseModel):
    year: int
    fss: dict[str, Any]
    neighborhoods: list[int] = [1, 3, 5, 9]


class EnsembleMetricsResponse(BaseModel):
    year: int
    metrics: dict[str, Any]
    label: str = "MATCHED 75-CASE SUBSET"
    note: str = (
        "This matched-population comparison covers only the cases with a complete "
        "eligible five-member ensemble; it must not be interpreted as a head-to-head "
        "result on the full final-test population."
    )


class RegimeSummaryResponse(BaseModel):
    year: int
    prediction_role: str = "FORECAST_ONLY_PSEUDO_REGIME"
    semantic_note: str = "forecast-only pseudo-regime; not independently observed meteorological truth"
    distribution: dict[str, Any]


class RegimeResponse(BaseModel):
    case_id: str
    year: int
    year_role: str
    prediction_role: Literal["OUT_OF_FOLD", "PROSPECTIVE_VALIDATION", "FINAL_TEST_PREDICTION"]
    classes: list[str] = list(REGIME_CLASSES)
    probabilities: dict[str, float]
    predicted_class: str
    semantic_note: str = "forecast-only pseudo-regime; not independently observed meteorological truth"


class QualitySummary(BaseModel):
    scheduled_date_lead_cases: int
    atmosphere_complete: int
    c00_eligible_total: int
    five_member_eligible_total: int
    c00_eligible_by_year: dict[str, int]
    five_member_eligible_by_year: dict[str, int]
    atmosphere_complete_by_year: dict[str, int]
    deterministic_eligible_by_year: dict[str, int]
    scheduled_by_year: dict[str, int]
    note: str = (
        "All selected source messages were acquired; the eligible counts below reflect "
        "canonical QC attrition, not download failure."
    )


class ProvenanceSummary(BaseModel):
    experiment_version: str
    forecast_source: str = "NOAA operational GEFS (historical archive)"
    observation_source: str = "IMD 0.25 degree gridded rainfall"
    model_versions: dict[str, Any]
    scientific_freeze_status: str = "FINAL_TEST_COMPLETED (2025 holdout consumed)"
    artifact_verification_status: str


# ---------------------------------------------------------------------------
# Integrity helpers
# ---------------------------------------------------------------------------

_FINGERPRINT_CACHE: dict[str, tuple[int, float]] = {}


def _guard_path(path: Path, base: Path) -> Path:
    resolved = path.resolve()
    if not resolved.is_relative_to(base.resolve()) or not resolved.is_file():
        raise _science_error(404, ScienceErrorCode.CASE_NOT_FOUND, "Unknown or inaccessible frozen artifact")
    return resolved


def _guard_and_fingerprint(path: Path, base: Path) -> Path:
    """Tier-2 integrity: no dedicated hash manifest covers this file, so pin its
    (size, mtime) on first access and fail closed if either changes afterward."""
    resolved = _guard_path(path, base)
    stat = resolved.stat()
    fingerprint = (stat.st_size, stat.st_mtime)
    key = str(resolved)
    seen = _FINGERPRINT_CACHE.get(key)
    if seen is None:
        _FINGERPRINT_CACHE[key] = fingerprint
    elif seen != fingerprint:
        raise _science_error(503, ScienceErrorCode.INTEGRITY_FAILURE, "Frozen artifact changed after first verification; integrity failure")
    return resolved


@lru_cache(maxsize=1)
def _phase4j_integrity() -> dict[str, str]:
    """Tier-1 integrity for the 2025 final-test corpus: whole-manifest hash check,
    then per-file hash check, cached for process lifetime (~25 files, cheap)."""
    manifest_path = PHASE4J / "ARTIFACT_INTEGRITY.json"
    sidecar = PHASE4J / "ARTIFACT_INTEGRITY.sha256"
    if not manifest_path.is_file() or not sidecar.is_file():
        raise _science_error(503, ScienceErrorCode.INTEGRITY_FAILURE, "Phase 4J frozen artifact integrity manifest is unavailable")
    expected_manifest_hash = sidecar.read_text(encoding="ascii").strip()
    if sha256_file(manifest_path) != expected_manifest_hash:
        raise _science_error(503, ScienceErrorCode.INTEGRITY_FAILURE, "Phase 4J artifact integrity manifest hash mismatch")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    files = manifest["files"]
    digests: dict[str, str] = {}
    for relative, meta in files.items():
        path = PHASE4J / relative
        if not path.resolve().is_relative_to(PHASE4J.resolve()) or not path.is_file():
            raise _science_error(503, ScienceErrorCode.INTEGRITY_FAILURE, f"Phase 4J frozen artifact missing: {relative}")
        digest = meta["sha256"]
        if sha256_file(path) != digest:
            raise _science_error(503, ScienceErrorCode.INTEGRITY_FAILURE, f"Phase 4J frozen artifact integrity failure: {relative}")
        digests[relative] = digest
    return digests


def _phase4j_json(relative: str) -> dict:
    digests = _phase4j_integrity()
    if relative not in digests:
        raise _science_error(404, ScienceErrorCode.CASE_NOT_FOUND, "Unknown frozen artifact")
    return json.loads((PHASE4J / relative).read_text(encoding="utf-8"))


@lru_cache(maxsize=16)
def _phase4j_array(relative: str) -> np.ndarray:
    digests = _phase4j_integrity()
    if relative not in digests:
        raise _science_error(404, ScienceErrorCode.CASE_NOT_FOUND, "Unknown frozen artifact")
    return np.load(PHASE4J / relative, allow_pickle=False)


@lru_cache(maxsize=1)
def _phase4j_population_by_case() -> dict[str, dict]:
    manifest = _phase4j_json("population/2025_population_manifest.json")
    return {c["case_id"]: c for c in manifest["paired_cases"]}


@lru_cache(maxsize=1)
def _phase4j_case_level_by_case() -> dict[str, dict]:
    payload = _phase4j_json("metrics/case_level.json")
    return {c["case_id"]: c for c in payload["cases"]}


def _scatter_49x49(values: np.ndarray, pixel_index: np.ndarray, row_start: int, row_count: int) -> list:
    grid = np.full(GRID_CELLS, np.nan, dtype=np.float64)
    sl = slice(row_start, row_start + row_count)
    grid[pixel_index[sl]] = values[sl].astype(np.float64)
    grid = grid.reshape(49, 49)
    return np.where(np.isfinite(grid), grid, None).tolist()


_PHASE4J_RAINFALL_FIELDS: dict[str, str] = {
    "raw": "predictions/M0.npy",
    "m1": "predictions/M1.npy",
    "m2": "predictions/M2.npy",
    "m3": "predictions/M3.npy",
    "m4": "predictions/M4.npy",
    "imd": "pairing/observation_mm.npy",
}
_PHASE4J_PROBABILITY_FIELDS: dict[str, str] = {
    "heavy": "predictions/heavy_probability.npy",
    "very_heavy": "predictions/very_heavy_probability.npy",
}


# ---------------------------------------------------------------------------
# Phase 4G row/pixel attribution (proven in Phase 5A.1B; see docs/93 section 2-3)
# ---------------------------------------------------------------------------


@lru_cache(maxsize=1)
def _phase4g_catalog() -> dict:
    catalog_path = _guard_and_fingerprint(PHASE4G_ROOT / "dataset_catalog_manifest.json", PHASE4G_ROOT)
    experiment_path = _guard_and_fingerprint(PHASE4G_ROOT / "phase4g_experiment_manifest.json", PHASE4G_ROOT)
    catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
    experiment = json.loads(experiment_path.read_text(encoding="utf-8"))
    for year_str, meta in catalog["years"].items():
        if experiment["year_manifest_sha256"].get(year_str) != meta["year_manifest_sha256"]:
            raise _science_error(503, ScienceErrorCode.INTEGRITY_FAILURE, f"Phase 4G catalog/experiment manifest cross-check failed for {year_str}")
    return catalog


@lru_cache(maxsize=3)
def _phase4g_year_manifest(year: int) -> dict:
    catalog = _phase4g_catalog()
    expected_hash = catalog["years"][str(year)]["year_manifest_sha256"]
    path = PHASE4G_ROOT / str(year) / _PHASE4G_SPLIT[year] / "year_manifest.json"
    if not path.is_file() or sha256_file(path) != expected_hash:
        raise _science_error(503, ScienceErrorCode.INTEGRITY_FAILURE, f"Phase 4G year manifest integrity failure for {year}")
    return json.loads(path.read_text(encoding="utf-8"))


@lru_cache(maxsize=3)
def _phase4g_deterministic(year: int) -> dict[str, Any]:
    """Hash-verified case_id -> (row_start, row_count) index, pixel_index, and
    paired IMD grid for the year's Phase 4G deterministic feature build. Proven
    (Phase 5A.1B) to be the exact ordering phase4i's flat M1-M4/probability
    arrays were written in: reconstructing all four 2024 models through this
    index reproduces the frozen validation_manifest.json aggregate RMSE to
    float32 precision, and 2023's case_id list matches oof_m2's manifest
    case_ids array element-for-element."""
    manifest = _phase4g_year_manifest(year)
    outputs = manifest["outputs_sha256"]["deterministic"]
    base = PHASE4G_ROOT / str(year) / _PHASE4G_SPLIT[year] / "deterministic"

    def _verified(key: str, filename: str) -> Path:
        path = base / filename
        if not path.resolve().is_relative_to(base.resolve()) or not path.is_file() or sha256_file(path) != outputs[key]:
            raise _science_error(503, ScienceErrorCode.INTEGRITY_FAILURE, f"Phase 4G deterministic artifact integrity failure: {year}/{filename}")
        return path

    cases = json.loads(_verified("cases", "cases.json").read_text(encoding="utf-8"))
    pixel_index = np.load(_verified("pixel_index", "pixel_index.npy"), allow_pickle=False)
    imd = np.load(_verified("target_mm", "y_mm.npy"), allow_pickle=False)
    return {"cases_by_id": {c["case_id"]: c for c in cases}, "pixel_index": pixel_index, "imd": imd}


_PHASE4I_2024_FIELDS: dict[str, str] = {
    "m1": "deterministic_models/M1_2024.npy",
    "m2": "deterministic_models/M2_2024.npy",
    "m3": "deterministic_models/M3_2024.npy",
    "m4": "deterministic_models/M4_2024.npy",
}
_PHASE4I_2024_PROBABILITY_FIELDS: dict[str, str] = {
    "heavy": "probability_models/heavy/selected_2024_probability.npy",
    "very_heavy": "probability_models/very_heavy/selected_2024_probability.npy",
}


def _phase4i_array(relative: str) -> np.ndarray:
    path = _guard_and_fingerprint(PHASE4I / relative, PHASE4I)
    return np.load(path, allow_pickle=False)


@lru_cache(maxsize=1)
def _oof_m2_2023() -> dict[str, Any]:
    """2023 leakage-safe out-of-fold M2. case_ids order in this manifest is
    verified (Phase 5A.1B) to match Phase 4G's 2023 deterministic cases.json
    element-for-element, and prediction.npy's hash matches the manifest's own
    declared prediction_sha256."""
    manifest_path = _guard_and_fingerprint(PHASE4I / "oof_m2" / "manifest.json", PHASE4I)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    prediction_path = PHASE4I / "oof_m2" / "prediction.npy"
    if not prediction_path.is_file() or sha256_file(prediction_path) != manifest["prediction_sha256"]:
        raise _science_error(503, ScienceErrorCode.INTEGRITY_FAILURE, "2023 OOF M2 prediction integrity failure")
    phase4g = _phase4g_deterministic(2023)
    if manifest["case_ids"] != list(phase4g["cases_by_id"].keys()):
        raise _science_error(503, ScienceErrorCode.INTEGRITY_FAILURE, "2023 OOF M2 case-order cross-check failed")
    prediction = np.load(prediction_path, allow_pickle=False)
    return {"prediction": prediction, "cases_by_id": phase4g["cases_by_id"], "pixel_index": phase4g["pixel_index"]}


@lru_cache(maxsize=1)
def _regime_2023() -> dict[str, np.ndarray]:
    """Explicit case_ids array (oof_regime/manifest.json) -> probability.npy
    row, hash-verified against the manifest's own declared probability_sha256."""
    manifest_path = _guard_and_fingerprint(PHASE4I / "oof_regime" / "manifest.json", PHASE4I)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    prob_path = PHASE4I / "oof_regime" / "probability.npy"
    if not prob_path.is_file() or sha256_file(prob_path) != manifest["probability_sha256"]:
        raise _science_error(503, ScienceErrorCode.INTEGRITY_FAILURE, "2023 OOF regime probability integrity failure")
    probability = np.load(prob_path, allow_pickle=False)
    return {row_case: probability[i] for i, row_case in enumerate(manifest["case_ids"])}


@lru_cache(maxsize=1)
def _regime_2024() -> dict[str, np.ndarray]:
    """Explicit validation_case_ids array (regime_models/manifest.json) ->
    2024_prospective_probability.npy row, hash-verified against the manifest's
    own declared 2024_probability_sha256."""
    manifest_path = _guard_and_fingerprint(PHASE4I / "regime_models" / "manifest.json", PHASE4I)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    prob_path = PHASE4I / "regime_models" / "2024_prospective_probability.npy"
    if not prob_path.is_file() or sha256_file(prob_path) != manifest["2024_probability_sha256"]:
        raise _science_error(503, ScienceErrorCode.INTEGRITY_FAILURE, "2024 prospective regime probability integrity failure")
    probability = np.load(prob_path, allow_pickle=False)
    return {row_case: probability[i] for i, row_case in enumerate(manifest["validation_case_ids"])}


@lru_cache(maxsize=1)
def _regime_2025() -> dict[str, np.ndarray]:
    """regime_375x3.npy has no dedicated case_ids array; row order is proven
    (Phase 5A.1B) by independent reconstruction: indexing it by the frozen
    2025 eligibility file's own row order reproduces BOTH the frozen full-375
    classifier counts (150/130/95) and the frozen 232-case paired counts
    (100/71/61) from metrics/regime.json exactly -- a coincidence this precise
    across two independent aggregates is not plausible under a wrong ordering."""
    probability = _phase4j_array("predictions/regime_375x3.npy")
    records = _eligibility(2025)
    case_ids = [_eligibility_case_id(record) for record in records]
    if len(case_ids) != probability.shape[0]:
        raise _science_error(503, ScienceErrorCode.INTEGRITY_FAILURE, "2025 regime case-order cross-check failed: length mismatch")
    return {case_id: probability[i] for i, case_id in enumerate(case_ids)}


_REGIME_LOADER: dict[int, Any] = {2023: _regime_2023, 2024: _regime_2024, 2025: _regime_2025}
_REGIME_PREDICTION_ROLE: dict[int, str] = {
    2023: "OUT_OF_FOLD", 2024: "PROSPECTIVE_VALIDATION", 2025: "FINAL_TEST_PREDICTION",
}


# ---------------------------------------------------------------------------
# Case-id / eligibility helpers (shared across all three years)
# ---------------------------------------------------------------------------


def _parse_case_id(case_id: str) -> tuple[str, str, int, int]:
    match = CASE_ID_PATTERN.fullmatch(case_id)
    if not match:
        raise _science_error(404, ScienceErrorCode.CASE_NOT_FOUND, "Unknown or malformed case identifier")
    date8, day = match.group(1), match.group(2)
    return date8, f"day{day}_24h", LEAD_HOURS_BY_DAY[day], int(date8[:4])


def _require_year(year: int) -> int:
    if year not in YEARS:
        raise _science_error(404, ScienceErrorCode.INVALID_FIELD, f"Unknown operational year: {year}. Valid years: {YEARS}")
    return year


@lru_cache(maxsize=3)
def _eligibility(year: int) -> tuple[dict, ...]:
    _require_year(year)
    path = _guard_and_fingerprint(PHASE4F / "eligibility" / f"{year}_source_eligibility.json", PHASE4F)
    return tuple(json.loads(path.read_text(encoding="utf-8")))


def _eligibility_case_id(record: dict) -> str:
    date8 = record["initialization"][:10].replace("-", "")
    return f"{date8}_{record['product']}"


@lru_cache(maxsize=3)
def _eligibility_by_case_id(year: int) -> dict[str, dict]:
    return {_eligibility_case_id(record): record for record in _eligibility(year)}


def _case_record(case_id: str) -> tuple[dict, int]:
    date8, product, lead_hours, year = _parse_case_id(case_id)
    record = _eligibility_by_case_id(year).get(case_id)
    if record is None:
        raise _science_error(404, ScienceErrorCode.CASE_NOT_FOUND, "Unknown historical operational case")
    return record, year


@lru_cache(maxsize=3)
def _paired_cases_by_id(year: int) -> dict[str, dict]:
    """Case_id -> {row_start, row_count, valid_observation_date, ...} for
    whichever population manifest that year's deterministic/IMD pairing
    actually uses. Only covers deterministic-source-eligible cases -- a case
    outside this population has no frozen IMD pairing and therefore no event
    flag, which _event_flags_by_case/_valid_date_for_case correctly return as
    None for rather than fabricating one."""
    if year == 2025:
        return _phase4j_population_by_case()
    return _phase4g_deterministic(year)["cases_by_id"]


def _imd_array_for_year(year: int) -> np.ndarray:
    if year == 2025:
        return _phase4j_array("pairing/observation_mm.npy")
    return _phase4g_deterministic(year)["imd"]


@lru_cache(maxsize=3)
def _event_flags_by_case(year: int) -> dict[str, tuple[bool, bool]]:
    """Per-case (event_heavy, event_very_heavy) from the frozen, already-
    loaded IMD pairing array -- a deterministic threshold comparison over
    data already in memory, not a new computation on stored science."""
    paired = _paired_cases_by_id(year)
    imd = _imd_array_for_year(year)
    flags: dict[str, tuple[bool, bool]] = {}
    for case_id, meta in paired.items():
        segment = imd[meta["row_start"]: meta["row_start"] + meta["row_count"]]
        finite = segment[np.isfinite(segment)]
        if finite.size == 0:
            continue
        peak = float(finite.max())
        flags[case_id] = (peak >= HEAVY_THRESHOLD_MM, peak >= VERY_HEAVY_THRESHOLD_MM)
    return flags


@lru_cache(maxsize=3)
def _pseudo_regime_class_by_case(year: int) -> dict[str, str]:
    lookup = _REGIME_LOADER[year]()
    return {case_id: REGIME_CLASSES[int(np.argmax(vector))] for case_id, vector in lookup.items()}


def _case_summary(case_id: str, record: dict, year: int) -> OperationalCaseSummary:
    case_level = _phase4j_case_level_by_case().get(case_id) if year == 2025 else None
    paired_meta = _paired_cases_by_id(year).get(case_id)
    event_flags = _event_flags_by_case(year).get(case_id)
    date8 = record["initialization"][:10]
    lead_hours = LEAD_HOURS_BY_DAY[record["product"][3]]
    m1_minus_raw = case_level["M1_minus_raw_rmse_mm"] if case_level else None
    return OperationalCaseSummary(
        case_id=case_id,
        year=year,
        initialization_utc=record["initialization"],
        lead_hours=LEAD_HOURS_BY_DAY[record["product"][3]],
        product=record["product"],
        year_role=YEAR_ROLE[year],
        source_complete=record["SOURCE_COMPLETE"],
        deterministic_source_eligible=record["DETERMINISTIC_SOURCE_ELIGIBLE"],
        probability_source_eligible=record["PROBABILITY_SOURCE_ELIGIBLE"],
        regime_source_eligible=record["REGIME_SOURCE_ELIGIBLE"],
        ensemble_source_eligible=record["ENSEMBLE_SOURCE_ELIGIBLE"],
        c00_rainfall_qc_pass=record["C00_RAINFALL_QC_PASS"],
        full_5_member_rainfall_qc_pass=record["FULL_5_MEMBER_RAINFALL_QC_PASS"],
        m1_rmse_mm=case_level["M1_rmse_mm"] if case_level else None,
        raw_rmse_mm=case_level["raw_rmse_mm"] if case_level else None,
        m1_minus_raw_rmse_mm=m1_minus_raw,
        initialization_date=date8,
        month=int(date8[5:7]),
        lead_label=f"Day {lead_hours // 24}",
        valid_date=paired_meta.get("valid_observation_date") if paired_meta else None,
        event_heavy=event_flags[0] if event_flags else None,
        event_very_heavy=event_flags[1] if event_flags else None,
        pseudo_regime_class=_pseudo_regime_class_by_case(year).get(case_id) if record["REGIME_SOURCE_ELIGIBLE"] else None,
        selected_model_improved_vs_raw=(m1_minus_raw < 0) if m1_minus_raw is not None else None,
    )


def _rainfall_qc_grid(year: int, date8: str, product: str, member: str) -> np.ndarray:
    path = _guard_and_fingerprint(PHASE4F / "rainfall_qc" / str(year) / date8 / f"{product}_{member}.npy", PHASE4F)
    return np.load(path, allow_pickle=False)


def _atmospheric_qc_grid(year: int, date8: str, field: str, hour: str) -> np.ndarray:
    path = _guard_and_fingerprint(PHASE4F / "atmospheric_qc" / str(year) / date8 / f"{field}_f{hour}.npy", PHASE4F)
    return np.load(path, allow_pickle=False)


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get("/status", response_model=OperationalStatus)
def status() -> OperationalStatus:
    return OperationalStatus(years={str(y): YEAR_ROLE[y] for y in YEARS})


@router.get("/years", response_model=list[OperationalYearCapabilities])
def years() -> list[OperationalYearCapabilities]:
    return [availability(year) for year in YEARS]


@router.get("/{year}/availability", response_model=OperationalYearCapabilities)
def availability(year: int) -> OperationalYearCapabilities:
    _require_year(year)
    if year == 2023:
        return OperationalYearCapabilities(
            year=year, role=YEAR_ROLE[year], role_label=YEAR_ROLE_LABEL[year],
            raw_rainfall=True, imd_observation=True,
            m1="unavailable", m2="out_of_fold_case_grid", m3="unavailable", m4="unavailable",
            heavy_probability="unavailable", very_heavy_probability="unavailable",
            regime_probability="per_case",
            atmosphere_fields=True, ensemble_members="eligible_subset_only",
            case_level_metrics=False, per_cell_metrics=False, fss=False, reliability_bins=False,
            notes=[
                "2023 is train/cross-fit only: M1/M3/M4 and probability models are fit on this "
                "year, not scored against it, so no frozen 2023 output grid exists for them.",
                "M2 is exposed only as leakage-safe out-of-fold (K-fold) prediction (verified: "
                "oof_m2 manifest case_ids match Phase 4G's 2023 case index element-for-element); "
                "never as an independent final-test result.",
                "Regime probability is out-of-fold, verified via the oof_regime manifest's own "
                "explicit case_ids array plus a declared-hash cross-check.",
                "No district product for 2023: there are no probability or M1/M3/M4 output grids to aggregate.",
            ],
        )
    if year == 2024:
        return OperationalYearCapabilities(
            year=year, role=YEAR_ROLE[year], role_label=YEAR_ROLE_LABEL[year],
            raw_rainfall=True, imd_observation=True,
            m1="case_grid", m2="case_grid", m3="case_grid", m4="case_grid",
            heavy_probability="case_grid", very_heavy_probability="case_grid",
            regime_probability="per_case",
            atmosphere_fields=True, ensemble_members="eligible_subset_only",
            case_level_metrics=False, per_cell_metrics=False, fss=True, reliability_bins=True,
            district_aggregates=True,
            notes=[
                "District aggregates are area-weighted (Phase 2C overlap weights shared with Track A) over "
                "the frozen M0-M4/probability/IMD grids; a read-only aggregation, not a new model output.",
                "2024 model-output case grids are reconstructed via the verified Phase 4G "
                "case_id -> row_start/pixel_index index; reconstructing all four models this way "
                "reproduces validation_manifest.json's frozen aggregate RMSE to float32 precision.",
                "No per-case metrics file exists for 2024 (unlike 2025's case_level.json), so "
                "case_level_metrics stays false even though grids are now available.",
                "Regime probability is prospective validation, verified via regime_models "
                "manifest's own explicit validation_case_ids array plus a declared-hash cross-check.",
            ],
        )
    return OperationalYearCapabilities(
        year=year, role=YEAR_ROLE[year], role_label=YEAR_ROLE_LABEL[year],
        raw_rainfall=True, imd_observation=True,
        m1="case_grid", m2="case_grid", m3="case_grid", m4="case_grid",
        heavy_probability="case_grid", very_heavy_probability="case_grid",
        regime_probability="per_case",
        atmosphere_fields=True, ensemble_members="eligible_subset_only",
        case_level_metrics=True, per_cell_metrics=True, fss=True, reliability_bins=True,
        district_aggregates=True,
        notes=[
            "District aggregates are area-weighted (Phase 2C overlap weights shared with Track A) over "
            "the frozen M0-M4/probability/IMD grids of a consumed holdout; historical replay only.",
            "2025 M1 is the pre-registered primary final-test model; M2 achieved a lower "
            "secondary RMSE but was not selected before the holdout was opened.",
            "Per-case regime probability is indexed by the frozen eligibility file's row order; "
            "this ordering is verified by independently reproducing both the full-375 classifier "
            "counts and the 232-case paired counts from metrics/regime.json exactly.",
        ],
    )


@router.get("/{year}/cases", response_model=OperationalCasesResponse)
def cases(
    year: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=400),  # 375 = one full scheduled year; still bounded, not unlimited
    lead_hours: int | None = Query(None),
) -> OperationalCasesResponse:
    _require_year(year)
    records = list(_eligibility(year))
    summaries = []
    for record in records:
        case_id = _eligibility_case_id(record)
        summary = _case_summary(case_id, record, year)
        if lead_hours is not None and summary.lead_hours != lead_hours:
            continue
        summaries.append(summary)
    total = len(summaries)
    start = (page - 1) * page_size
    page_items = summaries[start:start + page_size]
    return OperationalCasesResponse(year=year, total=total, page=page, page_size=page_size, cases=page_items)


@router.get("/{year}/cases/{case_id}", response_model=OperationalCaseDetail)
def case_detail(year: int, case_id: str) -> OperationalCaseDetail:
    _require_year(year)
    record, record_year = _case_record(case_id)
    if record_year != year:
        raise _science_error(404, ScienceErrorCode.CASE_NOT_FOUND, "Case does not belong to the requested year")
    summary = _case_summary(case_id, record, year)
    member_qc = {
        "c00": record["C00_RAINFALL_QC_PASS"],
        "p01": record["P01_RAINFALL_QC_PASS"],
        "p02": record["P02_RAINFALL_QC_PASS"],
        "p03": record["P03_RAINFALL_QC_PASS"],
        "p04": record["P04_RAINFALL_QC_PASS"],
    }
    available_products = ["raw"]
    if year == 2025:
        available_products += ["m1", "m2", "m3", "m4", "imd", "heavy_probability", "very_heavy_probability"]
    elif year == 2024:
        available_products += ["m1", "m2", "m3", "m4", "imd"]
        if record["PROBABILITY_SOURCE_ELIGIBLE"]:
            available_products += ["heavy_probability", "very_heavy_probability"]
    elif year == 2023:
        available_products += ["m2_out_of_fold", "imd"]
    if record["REGIME_SOURCE_ELIGIBLE"]:
        available_products.append("regime")
    return OperationalCaseDetail(**summary.model_dump(), member_qc=member_qc, available_products=available_products)


@router.get("/{year}/cases/{case_id}/rainfall", response_model=GridFieldResponse)
def rainfall(year: int, case_id: str, field: str = Query(..., pattern="^(raw|p01|p02|p03|p04|m1|m2|m3|m4|imd)$")) -> GridFieldResponse:
    _require_year(year)
    record, record_year = _case_record(case_id)
    if record_year != year:
        raise _science_error(404, ScienceErrorCode.CASE_NOT_FOUND, "Case does not belong to the requested year")
    date8, product, lead_hours, _ = _parse_case_id(case_id)

    if field in ("raw", "p01", "p02", "p03", "p04"):
        member = "c00" if field == "raw" else field
        qc_key = f"{member.upper()}_RAINFALL_QC_PASS"
        if not record.get(qc_key, False):
            raise _science_error(404, ScienceErrorCode.CASE_NOT_ELIGIBLE, f"Member {member} failed canonical QC for this case; not exposed as valid")
        grid = _rainfall_qc_grid(year, date8, product, member)
        values = np.where(np.isfinite(grid), grid, None).tolist()
        return GridFieldResponse(
            case_id=case_id, year=year, field=field, units="mm/24h", shape=[49, 49],
            **_grid_lat_lon(), values=values, source="phase4f_payload_acquisition_v1/rainfall_qc",
            scientific_role="raw GEFS ensemble member (source, not a post-processed model)",
        )

    scientific_role_by_field = {
        "m1": "Ridge MOS",
        "m2": "non-regime global ML",
        "m3": "hard regime-routed ML",
        "m4": "soft regime-mixture ML",
        "imd": "IMD observed rainfall (paired to this case's valid cells)",
    }

    if year == 2025:
        if field not in _PHASE4J_RAINFALL_FIELDS:
            raise _science_error(404, ScienceErrorCode.INVALID_FIELD, f"Unknown or unavailable rainfall field: {field}")
        population = _phase4j_population_by_case().get(case_id)
        if population is None:
            raise _science_error(404, ScienceErrorCode.CASE_NOT_ELIGIBLE, "Case is not in the frozen 2025 final-test population")
        values_array = _phase4j_array(_PHASE4J_RAINFALL_FIELDS[field])
        pixel_index = _phase4j_array("pairing/pixel_index.npy")
        values = _scatter_49x49(values_array, pixel_index, population["row_start"], population["row_count"])
        role = scientific_role_by_field[field]
        if field == "m1":
            role += " (pre-registered primary 2025 final-test model)"
        elif field == "m2":
            role += " (secondary 2025 final-test result; not pre-registered primary)"
        return GridFieldResponse(
            case_id=case_id, year=year, field=field, units="mm/24h", shape=[49, 49],
            **_grid_lat_lon(), values=values, source="phase4j_operational_final_test_v1", scientific_role=role,
        )

    if year == 2024:
        if field not in (*_PHASE4I_2024_FIELDS, "imd"):
            raise _science_error(
                404, ScienceErrorCode.PRODUCT_UNAVAILABLE,
                f"Field '{field}' is not available as a per-case grid for {year} "
                "(2024 provides raw/p01-p04 source members plus m1-m4/imd via the verified Phase 4G index).",
            )
        phase4g = _phase4g_deterministic(2024)
        case_meta = phase4g["cases_by_id"].get(case_id)
        if case_meta is None:
            raise _science_error(404, ScienceErrorCode.CASE_NOT_ELIGIBLE, "Case is not in the frozen 2024 validation population")
        pixel_index = phase4g["pixel_index"]
        row_start, row_count = case_meta["row_start"], case_meta["row_count"]
        if field == "imd":
            values = _scatter_49x49(phase4g["imd"], pixel_index, row_start, row_count)
        else:
            values_array = _phase4i_array(_PHASE4I_2024_FIELDS[field])
            values = _scatter_49x49(values_array, pixel_index, row_start, row_count)
        return GridFieldResponse(
            case_id=case_id, year=year, field=field, units="mm/24h", shape=[49, 49],
            **_grid_lat_lon(), values=values, source="phase4i_operational_model_development_v1 + phase4g_features_v1",
            scientific_role=scientific_role_by_field[field],
        )

    # year == 2023
    if field == "m2":
        if not record.get("PROBABILITY_SOURCE_ELIGIBLE", False) and not record.get("DETERMINISTIC_SOURCE_ELIGIBLE", False):
            raise _science_error(404, ScienceErrorCode.CASE_NOT_ELIGIBLE, "Case is not deterministic-source-eligible for 2023")
        oof = _oof_m2_2023()
        case_meta = oof["cases_by_id"].get(case_id)
        if case_meta is None:
            raise _science_error(404, ScienceErrorCode.CASE_NOT_ELIGIBLE, "Case is not in the frozen 2023 out-of-fold population")
        values = _scatter_49x49(oof["prediction"], oof["pixel_index"], case_meta["row_start"], case_meta["row_count"])
        return GridFieldResponse(
            case_id=case_id, year=year, field=field, units="mm/24h", shape=[49, 49],
            **_grid_lat_lon(), values=values, source="phase4i_operational_model_development_v1/oof_m2",
            scientific_role="non-regime global ML, leakage-safe out-of-fold prediction",
            prediction_role="OUT_OF_FOLD",
        )
    if field == "imd":
        phase4g = _phase4g_deterministic(2023)
        case_meta = phase4g["cases_by_id"].get(case_id)
        if case_meta is None:
            raise _science_error(404, ScienceErrorCode.CASE_NOT_ELIGIBLE, "Case is not in the frozen 2023 deterministic population")
        values = _scatter_49x49(phase4g["imd"], phase4g["pixel_index"], case_meta["row_start"], case_meta["row_count"])
        return GridFieldResponse(
            case_id=case_id, year=year, field=field, units="mm/24h", shape=[49, 49],
            **_grid_lat_lon(), values=values, source="phase4g_features_v1", scientific_role=scientific_role_by_field[field],
        )
    raise _science_error(
        404, ScienceErrorCode.PRODUCT_UNAVAILABLE,
        f"Field '{field}' is not available for 2023: models other than M2 are fit on 2023, not scored "
        "against it, so no frozen 2023 output grid exists for them.",
    )


def _grid_lat_lon() -> dict[str, Any]:
    meta = _grid_metadata()
    return {"latitude_centers": meta["latitude_centers"], "longitude_centers": meta["longitude_centers"]}


@router.get("/{year}/cases/{case_id}/atmosphere/{field}", response_model=AtmosphericFieldResponse)
def atmosphere(year: int, case_id: str, field: str) -> AtmosphericFieldResponse:
    _require_year(year)
    if field not in ATMOSPHERE_FIELDS:
        raise _science_error(404, ScienceErrorCode.INVALID_FIELD, f"Unknown atmospheric field: {field}. Valid fields: {ATMOSPHERE_FIELDS}")
    record, record_year = _case_record(case_id)
    if record_year != year:
        raise _science_error(404, ScienceErrorCode.CASE_NOT_FOUND, "Case does not belong to the requested year")
    if not record.get("ATMOSPHERIC_QC_PASS", False):
        raise _science_error(404, ScienceErrorCode.CASE_NOT_ELIGIBLE, "Atmospheric fields failed canonical QC for this case; not exposed as valid")
    date8, _, lead_hours, _ = _parse_case_id(case_id)
    hour = FORECAST_HOUR_BY_LEAD[lead_hours]
    grid = _atmospheric_qc_grid(year, date8, field, hour)
    values = np.where(np.isfinite(grid), grid, None).tolist()
    pressure_level = {"u850": 850.0, "v850": 850.0, "q700": 700.0, "z500": 500.0, "mslp": None, "pwat": None}[field]
    units = {"u850": "m/s", "v850": "m/s", "q700": "kg/kg", "z500": "gpm", "mslp": "Pa", "pwat": "kg/m^2"}[field]
    latitude, longitude = context_coordinates()
    return AtmosphericFieldResponse(
        case_id=case_id, year=year, field=field, pressure_level_hpa=pressure_level, forecast_hour=lead_hours,
        units=units, shape=[51, 81], values=values,
        latitude_centers=[float(v) for v in latitude], longitude_centers=[float(v) for v in longitude], grid_spacing_degrees=0.5,
    )


@router.get("/{year}/cases/{case_id}/probability/{target}", response_model=ProbabilityFieldResponse)
def probability(year: int, case_id: str, target: str) -> ProbabilityFieldResponse:
    _require_year(year)
    if target not in ("heavy", "very_heavy"):
        raise _science_error(404, ScienceErrorCode.INVALID_FIELD, "Unknown probability target; valid targets: heavy, very_heavy")
    record, record_year = _case_record(case_id)
    if record_year != year:
        raise _science_error(404, ScienceErrorCode.CASE_NOT_FOUND, "Case does not belong to the requested year")
    if year == 2023:
        raise _science_error(
            404, ScienceErrorCode.PRODUCT_UNAVAILABLE,
            "2023 is train/cross-fit only: probability models are fit on this year, not scored "
            "against it, so no frozen 2023 probability grid exists.",
        )
    if not record.get("PROBABILITY_SOURCE_ELIGIBLE", False):
        raise _science_error(404, ScienceErrorCode.CASE_NOT_ELIGIBLE, "Case is not probability-source-eligible")
    threshold = {"heavy": 0.1, "very_heavy": 0.05}[target]

    if year == 2024:
        phase4g = _phase4g_deterministic(2024)
        case_meta = phase4g["cases_by_id"].get(case_id)
        if case_meta is None:
            raise _science_error(404, ScienceErrorCode.CASE_NOT_ELIGIBLE, "Case is not in the frozen 2024 validation population")
        values_array = _phase4i_array(_PHASE4I_2024_PROBABILITY_FIELDS[target])
        values = _scatter_49x49(values_array, phase4g["pixel_index"], case_meta["row_start"], case_meta["row_count"])
        return ProbabilityFieldResponse(
            case_id=case_id, year=year, target=target, threshold_probability=threshold,
            calibration_type="frozen isotonic/logistic calibrator selected in Phase 4I", values=values,
        )

    population = _phase4j_population_by_case().get(case_id)
    if population is None:
        raise _science_error(404, ScienceErrorCode.CASE_NOT_ELIGIBLE, "Case is not in the frozen 2025 final-test population")
    values_array = _phase4j_array(_PHASE4J_PROBABILITY_FIELDS[target])
    pixel_index = _phase4j_array("pairing/pixel_index.npy")
    values = _scatter_49x49(values_array, pixel_index, population["row_start"], population["row_count"])
    return ProbabilityFieldResponse(
        case_id=case_id, year=year, target=target, threshold_probability=threshold,
        calibration_type="frozen isotonic/logistic calibrator selected in Phase 4I", values=values,
    )


_MODEL_ROLE: dict[str, str] = {
    "m1": "Ridge MOS", "m2": "non-regime global ML", "m3": "hard regime-routed ML", "m4": "soft regime-mixture ML",
}
_DISTRICT_METHOD = (
    "Area-overlap weighting of the frozen 0.25 degree target cells (Phase 2C weight matrix shared with Track A; "
    "cosine-latitude-corrected planar overlap), normalised over the case's valid paired cells. Historical replay of "
    "frozen predictions; not a live district forecast."
)
_DISTRICT_CAVEATS = [
    "Historical replay: observed IMD district statistics are shown only because this is a retrospective case.",
    "District values are area-weighted means over valid paired cells only (IMD land cells with a finite forecast); "
    "districts without any valid cell in this case are omitted.",
    "Probabilities are frozen calibrated cell probabilities area-averaged per district; area fractions are the share "
    "of cells at or above the 24 h threshold. They are different measures.",
    "Maximum is a single-cell maximum, not an area-weighted extreme. Geometry is simplified and is not an official "
    "current administrative boundary; coverage is limited to the 10-22N, 68-80E validated domain.",
    "Regime is a forecast-only classifier pseudo-label, not observed meteorological truth.",
]


@lru_cache(maxsize=1)
def _district_static() -> tuple[list[dict], np.ndarray, str, str]:
    """Hash-verified district list + Phase 2C overlap weights (Track A's verified store)."""
    _, _, manifest, _ = _track_a_store()
    geometry = json.loads((TRACK_A_ARTIFACTS / "districts.geojson").read_text(encoding="utf-8"))
    districts = [feature["properties"] for feature in geometry["features"]]
    weights = np.load(TRACK_A_ARTIFACTS / "district_weights.npy", allow_pickle=False)
    if weights.shape != (len(districts), GRID_CELLS):
        raise _science_error(503, ScienceErrorCode.INTEGRITY_FAILURE, "District weight matrix does not match district geometry")
    return districts, weights, manifest["files"]["district_weights.npy"], manifest["files"]["districts.geojson"]


def _district_case_fields(year: int, case_id: str, model: str, with_probability: bool) -> dict[str, np.ndarray | None]:
    """Flat 2401-cell frozen fields for one paired case (NaN off the valid paired cells)."""
    if year == 2025:
        population = _phase4j_population_by_case().get(case_id)
        if population is None:
            raise _science_error(404, ScienceErrorCode.CASE_NOT_ELIGIBLE, "Case is not in the frozen 2025 final-test population")
        sl = slice(population["row_start"], population["row_start"] + population["row_count"])
        pixel = _phase4j_array("pairing/pixel_index.npy")[sl]

        def grid(relative: str) -> np.ndarray:
            return flat_field(_phase4j_array(relative)[sl], pixel)
        return {
            "raw": grid(_PHASE4J_RAINFALL_FIELDS["raw"]), "corrected": grid(_PHASE4J_RAINFALL_FIELDS[model]),
            "observed": grid(_PHASE4J_RAINFALL_FIELDS["imd"]),
            "heavy": grid(_PHASE4J_PROBABILITY_FIELDS["heavy"]) if with_probability else None,
            "very_heavy": grid(_PHASE4J_PROBABILITY_FIELDS["very_heavy"]) if with_probability else None,
        }
    phase4g = _phase4g_deterministic(2024)
    meta = phase4g["cases_by_id"].get(case_id)
    if meta is None:
        raise _science_error(404, ScienceErrorCode.CASE_NOT_ELIGIBLE, "Case is not in the frozen 2024 validation population")
    sl = slice(meta["row_start"], meta["row_start"] + meta["row_count"])
    pixel = phase4g["pixel_index"][sl]

    def grid24(array: np.ndarray) -> np.ndarray:
        return flat_field(array[sl], pixel)
    return {
        "raw": grid24(_phase4i_array("deterministic_models/M0_2024.npy")),
        "corrected": grid24(_phase4i_array(_PHASE4I_2024_FIELDS[model])),
        "observed": grid24(phase4g["imd"]),
        "heavy": grid24(_phase4i_array(_PHASE4I_2024_PROBABILITY_FIELDS["heavy"])) if with_probability else None,
        "very_heavy": grid24(_phase4i_array(_PHASE4I_2024_PROBABILITY_FIELDS["very_heavy"])) if with_probability else None,
    }


@router.get("/{year}/cases/{case_id}/districts", response_model=OperationalDistrictsResponse)
def case_districts(year: int, case_id: str, model: str = Query("m1", pattern="^(m1|m2|m3|m4)$")) -> OperationalDistrictsResponse:
    _require_year(year)
    record, record_year = _case_record(case_id)
    if record_year != year:
        raise _science_error(404, ScienceErrorCode.CASE_NOT_FOUND, "Case does not belong to the requested year")
    if year == 2023:
        raise _science_error(
            404, ScienceErrorCode.PRODUCT_UNAVAILABLE,
            "No district product for 2023: it is the train/cross-fit year, so only out-of-fold M2 exists "
            "and there are no probability or M1/M3/M4 output grids to aggregate.",
        )
    districts, weights, weights_sha, geometry_sha = _district_static()
    with_probability = bool(record.get("PROBABILITY_SOURCE_ELIGIBLE", False))
    fields = _district_case_fields(year, case_id, model, with_probability)
    rows = aggregate_operational_districts(
        districts, weights, raw=fields["raw"], corrected=fields["corrected"], observed=fields["observed"],
        heavy_p=fields["heavy"], very_heavy_p=fields["very_heavy"])
    predicted = None
    if record.get("REGIME_SOURCE_ELIGIBLE", False):
        vector = _REGIME_LOADER[year]().get(case_id)
        if vector is not None:
            predicted = REGIME_CLASSES[int(np.argmax(vector))]
    role = _MODEL_ROLE[model] + (" (pre-registered primary 2025 final-test model)" if year == 2025 and model == "m1"
                                 else " (RMSE-selected 2024 model)" if year == 2024 and model == "m1" else "")
    return OperationalDistrictsResponse(
        case_id=case_id, year=year, year_role=YEAR_ROLE[year], model=model, model_role=role,
        predicted_regime=predicted, districts=[OperationalDistrictRow(**row) for row in rows],
        source_district_count=len(districts), method=_DISTRICT_METHOD, weights_sha256=weights_sha,
        geometry_sha256=geometry_sha, caveats=_DISTRICT_CAVEATS)


_IMPROVEMENT_DEFINITION = (
    "improvement_vs_raw_mm = |Raw district mean - IMD district mean| - |model district mean - IMD district mean| for this case. "
    "Positive: the corrected district mean is closer to IMD than Raw; negative: farther. A single-case, district-mean quantity, "
    "not a skill score."
)
_HISTORY_NOTE = (
    "Descriptive history only: the district-mean series of Raw, the selected model and IMD across this year's paired cases. "
    "No district-level skill score is computed or implied; district-level verification is a separate, protocol-gated phase."
)
_COMPARE_MODELS = ("m1", "m2", "m3", "m4")


def _district_context(year: int, case_id: str) -> dict:
    _require_year(year)
    record, record_year = _case_record(case_id)
    if record_year != year:
        raise _science_error(404, ScienceErrorCode.CASE_NOT_FOUND, "Case does not belong to the requested year")
    if year == 2023:
        raise _science_error(
            404, ScienceErrorCode.PRODUCT_UNAVAILABLE,
            "No district product for 2023: it is the train/cross-fit year, so only out-of-fold M2 exists "
            "and there are no probability or M1/M3/M4 output grids to aggregate.",
        )
    return record


def _model_role(year: int, model: str) -> str:
    return _MODEL_ROLE[model] + (" (pre-registered primary 2025 final-test model)" if year == 2025 and model == "m1"
                                 else " (RMSE-selected 2024 model)" if year == 2024 and model == "m1" else "")


@router.get("/{year}/cases/{case_id}/districts/compare", response_model=OperationalDistrictCompareResponse)
def case_districts_compare(year: int, case_id: str) -> OperationalDistrictCompareResponse:
    """All four corrected models next to Raw and IMD for every district of one case (same Phase 2C weights)."""
    record = _district_context(year, case_id)
    districts, weights, weights_sha, geometry_sha = _district_static()
    with_probability = bool(record.get("PROBABILITY_SOURCE_ELIGIBLE", False))
    per_model: dict[str, dict[str, dict]] = {}
    base_rows: dict[str, dict] = {}
    order: list[str] = []
    for model in _COMPARE_MODELS:
        fields = _district_case_fields(year, case_id, model, with_probability)
        rows = aggregate_operational_districts(
            districts, weights, raw=fields["raw"], corrected=fields["corrected"], observed=fields["observed"],
            heavy_p=fields["heavy"], very_heavy_p=fields["very_heavy"])
        for row in rows:
            did = row["district_id"]
            if model == _COMPARE_MODELS[0]:
                base_rows[did] = row
                order.append(did)
            per_model.setdefault(did, {})[model] = row
    out = []
    for did in order:
        base = base_rows[did]
        raw_error = base["raw_mean_mm"] - base["observed_mean_mm"]
        cells = {}
        for model in _COMPARE_MODELS:
            row = per_model[did][model]
            error = row["corrected_mean_mm"] - row["observed_mean_mm"]
            cells[model] = OperationalDistrictModelCell(
                mean_mm=row["corrected_mean_mm"], max_mm=row["corrected_max_mm"],
                heavy_area_fraction=row["heavy_area_fraction"], very_heavy_area_fraction=row["very_heavy_area_fraction"],
                error_mm=error, improvement_vs_raw_mm=abs(raw_error) - abs(error))
        out.append(OperationalDistrictCompareRow(
            district_id=did, district_name=base["district_name"], valid_grid_cells=base["valid_grid_cells"],
            raw_mean_mm=base["raw_mean_mm"], raw_max_mm=base["raw_max_mm"], raw_error_mm=raw_error,
            observed_mean_mm=base["observed_mean_mm"], observed_max_mm=base["observed_max_mm"],
            observed_heavy_area_fraction=base["observed_heavy_area_fraction"],
            observed_very_heavy_area_fraction=base["observed_very_heavy_area_fraction"],
            heavy_probability=base["heavy_probability"], very_heavy_probability=base["very_heavy_probability"], models=cells))
    predicted = None
    if record.get("REGIME_SOURCE_ELIGIBLE", False):
        vector = _REGIME_LOADER[year]().get(case_id)
        if vector is not None:
            predicted = REGIME_CLASSES[int(np.argmax(vector))]
    return OperationalDistrictCompareResponse(
        case_id=case_id, year=year, year_role=YEAR_ROLE[year], models=list(_COMPARE_MODELS),
        model_roles={m: _model_role(year, m) for m in _COMPARE_MODELS}, predicted_regime=predicted,
        improvement_definition=_IMPROVEMENT_DEFINITION, districts=out, source_district_count=len(districts),
        method=_DISTRICT_METHOD, weights_sha256=weights_sha, geometry_sha256=geometry_sha, caveats=_DISTRICT_CAVEATS)


@lru_cache(maxsize=64)
def _district_history_points(year: int, district_index: int, model: str) -> tuple[OperationalDistrictHistoryPoint, ...]:
    _, weights, _, _ = _district_static()
    points = []
    for case_id in sorted(_paired_cases_by_id(year)):
        fields = _district_case_fields(year, case_id, model, False)
        means = district_case_means(weights[district_index], raw=fields["raw"], corrected=fields["corrected"], observed=fields["observed"])
        if means is None:
            continue
        date8, _, lead_hours, _ = _parse_case_id(case_id)
        points.append(OperationalDistrictHistoryPoint(
            case_id=case_id, initialization_utc=f"{date8[:4]}-{date8[4:6]}-{date8[6:]}T00:00:00Z", lead_hours=lead_hours,
            valid_grid_cells=means["valid_grid_cells"], raw_mean_mm=means["raw_mean_mm"],
            model_mean_mm=means["corrected_mean_mm"], observed_mean_mm=means["observed_mean_mm"]))
    return tuple(points)


@router.get("/{year}/districts/{district_id}/history", response_model=OperationalDistrictHistoryResponse)
def district_history(year: int, district_id: str, model: str = Query("m1", pattern="^(m1|m2|m3|m4)$")) -> OperationalDistrictHistoryResponse:
    """Descriptive series for one district across the year's paired cases (no skill statistic)."""
    _require_year(year)
    if year == 2023:
        raise _science_error(404, ScienceErrorCode.PRODUCT_UNAVAILABLE, "No district product for 2023 (train/cross-fit year).")
    districts, _, weights_sha, _ = _district_static()
    index = next((i for i, d in enumerate(districts) if d["district_id"] == district_id), None)
    if index is None:
        raise _science_error(404, ScienceErrorCode.CASE_NOT_FOUND, "Unknown district")
    points = _district_history_points(year, index, model)
    return OperationalDistrictHistoryResponse(
        year=year, year_role=YEAR_ROLE[year], district_id=district_id, district_name=districts[index]["district_name"],
        model=model, model_role=_model_role(year, model), case_count=len(points), points=list(points),
        descriptive_only_note=_HISTORY_NOTE, method=_DISTRICT_METHOD, weights_sha256=weights_sha, caveats=_DISTRICT_CAVEATS)


@router.get("/{year}/cases/{case_id}/ensemble", response_model=EnsembleResponse)
def ensemble(year: int, case_id: str) -> EnsembleResponse:
    _require_year(year)
    record, record_year = _case_record(case_id)
    if record_year != year:
        raise _science_error(404, ScienceErrorCode.CASE_NOT_FOUND, "Case does not belong to the requested year")
    date8, product, _, _ = _parse_case_id(case_id)
    members = []
    for member in ENSEMBLE_MEMBERS:
        qc_key = f"{member.upper()}_RAINFALL_QC_PASS"
        eligible = record.get(qc_key, False)
        values = None
        if eligible:
            grid = _rainfall_qc_grid(year, date8, product, member)
            values = np.where(np.isfinite(grid), grid, None).tolist()
        members.append(EnsembleMemberStatus(member=member, qc_eligible=eligible, values=values))
    return EnsembleResponse(case_id=case_id, year=year, members=members)


@router.get("/{year}/cases/{case_id}/regime", response_model=RegimeResponse)
def case_regime(year: int, case_id: str) -> RegimeResponse:
    _require_year(year)
    record, record_year = _case_record(case_id)
    if record_year != year:
        raise _science_error(404, ScienceErrorCode.CASE_NOT_FOUND, "Case does not belong to the requested year")
    if not record.get("REGIME_SOURCE_ELIGIBLE", False):
        raise _science_error(404, ScienceErrorCode.CASE_NOT_ELIGIBLE, "Case is not regime-source-eligible")
    loader = _REGIME_LOADER[year]
    lookup = loader()
    vector = lookup.get(case_id)
    if vector is None:
        raise _science_error(404, ScienceErrorCode.CASE_NOT_ELIGIBLE, "Case has no frozen regime probability assignment")
    probabilities = {cls: float(p) for cls, p in zip(REGIME_CLASSES, vector)}
    predicted = max(probabilities, key=probabilities.get)
    return RegimeResponse(
        case_id=case_id, year=year, year_role=YEAR_ROLE[year],
        prediction_role=_REGIME_PREDICTION_ROLE[year], probabilities=probabilities, predicted_class=predicted,
    )


@router.get("/{year}/metrics/deterministic", response_model=DeterministicMetricsResponse)
def metrics_deterministic(year: int) -> DeterministicMetricsResponse:
    _require_year(year)
    if year == 2023:
        raise _science_error(404, ScienceErrorCode.PRODUCT_UNAVAILABLE, "2023 is train/cross-fit only; no frozen final-test deterministic metrics exist")
    if year == 2024:
        path = _guard_and_fingerprint(PHASE4I / "deterministic_models" / "validation_manifest.json", PHASE4I)
        payload = json.loads(path.read_text(encoding="utf-8"))
        return DeterministicMetricsResponse(year=year, metrics=payload["metrics"], primary_model=None,
                                             notes=["2024 is the validation/model-selection year; no model is designated primary yet."])
    metrics = _phase4j_json("metrics/deterministic.json")
    return DeterministicMetricsResponse(
        year=year, metrics=metrics, primary_model="M1",
        notes=[
            "M1 carries primary_selection_status=PRESELECTED_PRIMARY_MODEL: it was chosen before "
            "the 2025 holdout was opened.",
            "M2 achieved a lower secondary RMSE (15.0022mm vs M1's 15.5736mm) but is reported as "
            "SECONDARY_FINAL_TEST_RESULT only; it was not retroactively reselected as primary.",
        ],
    )


@router.get("/{year}/metrics/probability", response_model=ProbabilityMetricsResponse)
def metrics_probability(year: int) -> ProbabilityMetricsResponse:
    _require_year(year)
    if year == 2023:
        raise _science_error(404, ScienceErrorCode.PRODUCT_UNAVAILABLE, "2023 is train/cross-fit only; no frozen probability metrics exist")
    if year == 2024:
        heavy_path = _guard_and_fingerprint(PHASE4I / "validation" / "probability_heavy_2024.json", PHASE4I)
        vh_path = _guard_and_fingerprint(PHASE4I / "validation" / "probability_very_heavy_2024.json", PHASE4I)
        metrics = {
            "heavy": json.loads(heavy_path.read_text(encoding="utf-8")),
            "very_heavy": json.loads(vh_path.read_text(encoding="utf-8")),
        }
        return ProbabilityMetricsResponse(year=year, metrics=metrics)
    metrics = _phase4j_json("metrics/probability.json")
    return ProbabilityMetricsResponse(year=year, metrics=metrics)


@router.get("/{year}/metrics/fss", response_model=FSSResponse)
def metrics_fss(year: int) -> FSSResponse:
    _require_year(year)
    if year == 2023:
        raise _science_error(404, ScienceErrorCode.PRODUCT_UNAVAILABLE, "2023 is train/cross-fit only; no frozen FSS results exist")
    if year == 2024:
        path = _guard_and_fingerprint(PHASE4I / "fss" / "2024.json", PHASE4I)
        return FSSResponse(year=year, fss=json.loads(path.read_text(encoding="utf-8")))
    return FSSResponse(year=year, fss=_phase4j_json("metrics/fss.json"))


@router.get("/{year}/metrics/ensemble", response_model=EnsembleMetricsResponse)
def metrics_ensemble(year: int) -> EnsembleMetricsResponse:
    _require_year(year)
    if year != 2025:
        raise _science_error(
            404, ScienceErrorCode.PRODUCT_UNAVAILABLE,
            f"No frozen matched-population five-member-vs-ML comparison exists for {year}; this comparison is a 2025-only frozen artifact.",
        )
    return EnsembleMetricsResponse(year=year, metrics=_phase4j_json("metrics/ensemble.json"))


@router.get("/{year}/regimes", response_model=RegimeSummaryResponse)
def regimes(year: int) -> RegimeSummaryResponse:
    _require_year(year)
    if year == 2025:
        payload = _phase4j_json("metrics/regime.json")
        return RegimeSummaryResponse(year=year, distribution=payload)
    lookup = _REGIME_LOADER[year]()
    counts = {cls: 0 for cls in REGIME_CLASSES}
    for vector in lookup.values():
        counts[REGIME_CLASSES[int(np.argmax(vector))]] += 1
    return RegimeSummaryResponse(
        year=year,
        distribution={"predicted_class_counts": counts, "case_count": len(lookup), "prediction_role": _REGIME_PREDICTION_ROLE[year]},
    )


@router.get("/quality", response_model=QualitySummary)
def quality() -> QualitySummary:
    c00_by_year: dict[str, int] = {}
    five_member_by_year: dict[str, int] = {}
    atmosphere_by_year: dict[str, int] = {}
    deterministic_by_year: dict[str, int] = {}
    scheduled_by_year: dict[str, int] = {}
    for year in YEARS:
        records = _eligibility(year)
        scheduled_by_year[str(year)] = len(records)
        c00_by_year[str(year)] = sum(1 for r in records if r["C00_RAINFALL_QC_PASS"])
        five_member_by_year[str(year)] = sum(1 for r in records if r["FULL_5_MEMBER_RAINFALL_QC_PASS"])
        atmosphere_by_year[str(year)] = sum(1 for r in records if r["ATMOSPHERIC_QC_PASS"])
        deterministic_by_year[str(year)] = sum(1 for r in records if r["DETERMINISTIC_SOURCE_ELIGIBLE"])
    return QualitySummary(
        scheduled_date_lead_cases=sum(len(_eligibility(y)) for y in YEARS),
        atmosphere_complete=sum(1 for y in YEARS for r in _eligibility(y) if r["ATMOSPHERIC_QC_PASS"]),
        c00_eligible_total=sum(c00_by_year.values()),
        five_member_eligible_total=sum(five_member_by_year.values()),
        atmosphere_complete_by_year=atmosphere_by_year,
        deterministic_eligible_by_year=deterministic_by_year,
        scheduled_by_year=scheduled_by_year,
        c00_eligible_by_year=c00_by_year,
        five_member_eligible_by_year=five_member_by_year,
    )


@router.get("/provenance", response_model=ProvenanceSummary)
def provenance() -> ProvenanceSummary:
    integrity_status = "unavailable"
    try:
        _phase4j_integrity()
        integrity_status = "phase4j (2025 final test) hash-verified"
    except HTTPException:
        integrity_status = "phase4j integrity verification failed"
    return ProvenanceSummary(
        experiment_version="operational-era-2023-2025-v1",
        model_versions={
            "M1": "Ridge MOS", "M2": "global XGBoost (non-regime)",
            "M3": "hard regime-routed expert ML", "M4": "soft regime-mixture ML",
        },
        artifact_verification_status=integrity_status,
    )
