"""Read-only historical Phase 2C science API; never trains or decodes source data."""

from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Any

import numpy as np
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

try:
    from backend.app.ml.phase2b import ROOT, sha256_file
except ModuleNotFoundError:
    from app.ml.phase2b import ROOT, sha256_file

router = APIRouter(prefix="/science", tags=["Phase 2C historical science"])
ARTIFACTS = ROOT / "data/manifests/phase2c"
PHASE2B_ARTIFACTS = ROOT / "data/manifests/phase2b"
CASE_PATTERN = re.compile(r"^2019\d{4}T000000Z_day[123]_24h$")


class Provenance(BaseModel):
    corpus_version: str
    deterministic_model: str
    deterministic_model_sha256: str
    probability_freeze_sha256: str
    artifact_manifest_sha256: str
    prototype_only: bool = True


class ScienceStatus(BaseModel):
    readiness_state: str
    operational_ready: bool = False
    case_count: int
    district_count: int
    provenance: Provenance


class CasesResponse(BaseModel):
    cases: list[dict[str, Any]]
    provenance: Provenance


class SciencePayload(BaseModel):
    case_id: str
    initialization_utc: str
    lead_hours: int
    product: str
    valid_period_start_utc: str
    valid_period_end_utc: str
    data: dict[str, Any]
    provenance: Provenance


class VerificationResponse(BaseModel):
    metrics: dict[str, Any]
    provenance: Provenance


class DistrictGeometryResponse(BaseModel):
    geometry: dict[str, Any]
    geometry_sha256: str
    source: str
    license: str
    provenance: Provenance


class DemoCasesResponse(BaseModel):
    selection: str
    cases: list[dict[str, Any]]
    catalogue_sha256: str
    provenance: Provenance


class ModelComparisonResponse(BaseModel):
    results: dict[str, Any]
    test_year: int = 2019
    results_sha256: str
    provenance: Provenance


def _read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _grid_metadata() -> dict[str, Any]:
    """Frozen Phase 1F target-grid coordinates; no meteorological interpolation."""
    latitude = np.arange(10.0, 22.0 + 0.25, 0.25)
    longitude = np.arange(68.0, 80.0 + 0.25, 0.25)
    return {
        "crs": "EPSG:4326",
        "shape": [int(latitude.size), int(longitude.size)],
        "latitude_centers": latitude.tolist(),
        "longitude_centers": longitude.tolist(),
        "cell_size_degrees": 0.25,
        "bounds_west_south_east_north": [67.875, 9.875, 80.125, 22.125],
        "row_order": "south_to_north",
        "column_order": "west_to_east",
        "mask_policy": "paired valid forecast and IMD observation cells",
    }


@lru_cache(maxsize=1)
def _phase2b_results() -> tuple[dict, str]:
    manifest_path = PHASE2B_ARTIFACTS / "artifact_manifest.json"
    results_path = PHASE2B_ARTIFACTS / "2019_final_results.json"
    if not manifest_path.is_file() or not results_path.is_file():
        raise HTTPException(503, "Phase 2B frozen comparison is unavailable")
    manifest = _read(manifest_path)
    expected = manifest.get("test_results_sha256")
    if not isinstance(expected, str) or sha256_file(results_path) != expected:
        raise HTTPException(503, "Phase 2B frozen comparison integrity failure")
    return _read(results_path), expected


def _correct_metric_semantics(value: Any) -> Any:
    """Apply the append-only reporting supersession without changing scores."""
    if isinstance(value, dict):
        result = {k: _correct_metric_semantics(v) for k, v in value.items()}
        categorical = result.get("categorical")
        if isinstance(categorical, dict) and "threshold_mm_24h" in categorical:
            categorical["decision_threshold_probability"] = categorical.pop("threshold_mm_24h")
        return result
    if isinstance(value, list):
        return [_correct_metric_semantics(v) for v in value]
    return value


@lru_cache(maxsize=1)
def _store() -> tuple[dict, dict, dict, Provenance]:
    manifest_path = ARTIFACTS / "artifact_manifest.json"
    sidecar = ARTIFACTS / "artifact_manifest.sha256"
    if not manifest_path.is_file() or not sidecar.is_file():
        raise HTTPException(503, "Phase 2C frozen science artifacts are unavailable")
    manifest_hash = sidecar.read_text(encoding="ascii").strip()
    if sha256_file(manifest_path) != manifest_hash:
        raise HTTPException(503, "Phase 2C artifact manifest integrity failure")
    manifest = _read(manifest_path)
    for relative, digest in manifest["files"].items():
        path = ARTIFACTS / relative
        if not path.resolve().is_relative_to(ARTIFACTS.resolve()) or not path.is_file() or sha256_file(path) != digest:
            raise HTTPException(503, "Phase 2C frozen artifact integrity failure")
    result = _read(ARTIFACTS / "2019_final_results.json")
    freeze = _read(ARTIFACTS / "probability_selection_freeze.json")
    by_id = {entry["case_id"]: entry for entry in result["case_metadata"]}
    provenance = Provenance(corpus_version="varshasetu-gefs12r-imd025-2019-jjas-v2",
                            deterministic_model="Phase 2B M2 Global XGBoost",
                            deterministic_model_sha256=freeze["phase2b_global_model_sha256"],
                            probability_freeze_sha256=manifest["phase2c_freeze_sha256"],
                            artifact_manifest_sha256=manifest_hash)
    return result, by_id, manifest, provenance


def _case(case_id: str) -> tuple[dict, Provenance]:
    if not CASE_PATTERN.fullmatch(case_id):
        raise HTTPException(404, "Unknown historical case")
    _, by_id, _, provenance = _store()
    if case_id not in by_id:
        raise HTTPException(404, "Unknown historical case")
    path = ARTIFACTS / "cases" / f"{case_id}.json"
    return _read(path), provenance


def _payload(case: dict, provenance: Provenance, data: dict) -> SciencePayload:
    return SciencePayload(case_id=case["case_id"], initialization_utc=case["initialization_utc"],
                          lead_hours=case["lead_hours"], product=case["product"],
                          valid_period_start_utc=case["valid_period_start_utc"],
                          valid_period_end_utc=case["valid_period_end_utc"], data=data,
                          provenance=provenance)


@router.get("/status", response_model=ScienceStatus)
def status():
    result, _, manifest, provenance = _store()
    return ScienceStatus(readiness_state=manifest["readiness_state"], operational_ready=False,
                         case_count=result["case_count"], district_count=result["district_count"], provenance=provenance)


@router.get("/cases", response_model=CasesResponse)
def cases():
    result, _, _, provenance = _store()
    return CasesResponse(cases=[{k: v for k, v in item.items() if k not in ("array_file", "array_sha256")}
                                for item in result["case_metadata"]], provenance=provenance)


@router.get("/cases/{case_id}", response_model=SciencePayload)
def case_detail(case_id: str):
    case, provenance = _case(case_id)
    return _payload(case, provenance, {k: v for k, v in case.items() if k not in ("array_file", "array_sha256")})


@router.get("/cases/{case_id}/rainfall", response_model=SciencePayload)
def rainfall(case_id: str):
    case, provenance = _case(case_id)
    path = ARTIFACTS / "cases" / case["array_file"]
    if sha256_file(path) != case["array_sha256"]:
        raise HTTPException(503, "Case array integrity failure")
    with np.load(path, allow_pickle=False) as arrays:
        payload = {key: np.where(np.isfinite(arrays[key]), arrays[key], None).tolist()
                   for key in ("raw", "corrected", "observed")}
        payload["valid_mask"] = arrays["mask"].tolist()
    payload["unit"] = "mm/24h"
    payload["grid"] = _grid_metadata()
    return _payload(case, provenance, payload)


@router.get("/cases/{case_id}/regime", response_model=SciencePayload)
def regime(case_id: str):
    case, provenance = _case(case_id)
    return _payload(case, provenance, {"probabilities": case["regime_probabilities"],
                                       "dominant_regime": case["dominant_regime"],
                                       "label_status": "forecast-only prototype pseudo-label classifier"})


@router.get("/cases/{case_id}/probabilities", response_model=SciencePayload)
def probabilities(case_id: str):
    case, provenance = _case(case_id)
    path = ARTIFACTS / "cases" / case["array_file"]
    if sha256_file(path) != case["array_sha256"]:
        raise HTTPException(503, "Case array integrity failure")
    with np.load(path, allow_pickle=False) as arrays:
        data = {name: np.where(np.isfinite(arrays[name]), arrays[name], None).tolist()
                for name in ("heavy_probability", "very_heavy_probability")}
    data["thresholds_mm_24h"] = {"heavy": 64.5, "very_heavy": 115.6}
    data["grid"] = _grid_metadata()
    return _payload(case, provenance, data)


@router.get("/cases/{case_id}/fss", response_model=SciencePayload)
def case_fss(case_id: str):
    case, provenance = _case(case_id)
    return _payload(case, provenance, case["fss"])


@router.get("/cases/{case_id}/districts", response_model=SciencePayload)
def case_districts(case_id: str):
    case, provenance = _case(case_id)
    return _payload(case, provenance, {"districts": case["districts"],
                                       "aggregation": "grid-cell polygon overlap, cosine-latitude area approximation",
                                       "geometry_source": "geoBoundaries IND ADM2 2021, ODbL 1.0"})


@router.get("/verification", response_model=VerificationResponse)
def verification():
    result, _, _, provenance = _store()
    metrics = {k: v for k, v in result.items() if k != "case_metadata"}
    return VerificationResponse(metrics=_correct_metric_semantics(metrics), provenance=provenance)


@router.get("/geometry/districts", response_model=DistrictGeometryResponse)
def district_geometry():
    _, _, manifest, provenance = _store()
    path = ARTIFACTS / "districts.geojson"
    return DistrictGeometryResponse(
        geometry=_read(path), geometry_sha256=manifest["files"]["districts.geojson"],
        source="geoBoundaries IND ADM2 2021", license="ODbL 1.0", provenance=provenance,
    )


@router.get("/demo-cases", response_model=DemoCasesResponse)
def demo_cases():
    _, _, manifest, provenance = _store()
    catalogue = _read(ARTIFACTS / "video_case_catalogue.json")
    cases = [{k: v for k, v in item.items() if k not in ("array_file", "array_sha256")}
             for item in catalogue["cases"]]
    return DemoCasesResponse(selection=catalogue["selection"], cases=cases,
                             catalogue_sha256=manifest["files"]["video_case_catalogue.json"],
                             provenance=provenance)


@router.get("/model-comparison", response_model=ModelComparisonResponse)
def model_comparison():
    _, _, _, provenance = _store()
    results, digest = _phase2b_results()
    return ModelComparisonResponse(results=results["test_results"],
                                   results_sha256=digest, provenance=provenance)
