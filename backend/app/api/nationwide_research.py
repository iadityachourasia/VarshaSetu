"""Opt-in, local-only historical research view of sealed nationwide development output."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

import numpy as np
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from backend.app.ml.nationwide_research import GRID_SHAPE, LATITUDE, LONGITUDE, LEADS

router = APIRouter(prefix="/science/research/nationwide", tags=["Local nationwide development research"])
ROOT = Path(__file__).resolve().parents[3]
BASE = ROOT / "data/manifests/research_pilot"
OUT = ROOT / "data/processed/nationwide_research_v1"
PROTOCOL = BASE / "nationwide_research_protocol_v1.json"
FEATURES = BASE / "nationwide_research_features_v1.json"
SEAL = BASE / "nationwide_research_fit_seal_v1.json"
SCORE = BASE / "nationwide_research_score_v1.json"
UNCERTAINTY = BASE / "nationwide_research_uncertainty_v1.json"
DISTRICT = BASE / "nationwide_district_tables_v1.json"
FIELDS = ("M0", "M1", "M2", "M3", "M4", "heavy_p", "very_heavy_p")
PROBABILITY_STATUS = "RESEARCH_METHOD_AUDIT_FAILED_RELIABILITY_UNVALIDATED"


class EventScores(BaseModel):
    CSI: float | None
    ETS: float | None
    FAR: float | None
    POD: float | None


class EventVerification(BaseModel):
    hits: int
    false_alarms: int
    misses: int
    observed_event_count: int
    forecast_event_count: int
    sample_count: int
    threshold_mm_24h: float
    metrics: EventScores
    undefined_metric_reasons: dict[str, str]
    undefined_reason: str | None


class ContinuousVerification(BaseModel):
    bias_mm: float
    mae_mm: float
    rmse_mm: float
    sample_count: int


class FssVerification(BaseModel):
    case_count: int
    fss: float | None
    reason: str | None


class ModelVerification(BaseModel):
    cases: int
    cells: int
    metrics: dict[str, ContinuousVerification | EventVerification]
    fss: dict[str, dict[str, FssVerification]]


class DateBlockUncertainty(BaseModel):
    defined_bootstrap_repeats: dict[str, int]
    event_support_gate: bool
    heavy_csi: float | None
    heavy_csi_delta_ci95: list[float] | None
    heavy_csi_minus_raw: float | None
    rmse_delta_ci95: list[float] | None
    rmse_minus_raw: float | None
    rmse_mm: float
    support: dict[str, int]


class NationwideVerification(BaseModel):
    status: str
    source_track: str
    reference: str
    region: str
    lead_hours: int
    paired_cases: int
    paired_cells: int
    models: dict[str, ModelVerification]
    uncertainty: dict[str, DateBlockUncertainty]
    protocol_sha256: str
    score_sha256: str
    uncertainty_sha256: str
    independent_skill_claim: bool
    caveat: str


def _sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _error(code: int, detail: str) -> HTTPException:
    return HTTPException(code, detail={"code": "NATIONWIDE_RESEARCH_UNAVAILABLE" if code == 404 else "INTEGRITY_FAILURE", "detail": detail})


def _enabled() -> None:
    if os.environ.get("VARSHASETU_LOCAL_NATIONWIDE_RESEARCH") != "1":
        raise _error(404, "Local nationwide research view is disabled")


def _json(path: Path) -> tuple[dict, str]:
    if not path.is_file() or not path.with_suffix(".sha256").is_file():
        raise _error(404, f"Local nationwide research evidence is missing: {path.name}")
    digest = _sha(path)
    if path.with_suffix(".sha256").read_text(encoding="ascii").split() != [digest, path.name]:
        raise _error(503, f"Nationwide research evidence hash mismatch: {path.name}")
    return json.loads(path.read_text(encoding="utf-8")), digest


def _chain() -> dict:
    _enabled()
    protocol, psha = _json(PROTOCOL)
    features, fsha = _json(FEATURES)
    seal, ssha = _json(SEAL)
    score, score_sha = _json(SCORE)
    uncertainty, usha = _json(UNCERTAINTY)
    district, dsha = _json(DISTRICT)
    if (features["protocol_sha256"] != psha or seal["protocol_sha256"] != psha
            or seal["feature_manifest_sha256"] != fsha or score["fit_seal_sha256"] != ssha
            or uncertainty["score_sha256"] != score_sha or district["fit_seal_sha256"] != ssha
            or protocol["roles"]["2026"] != "sealed_test_excluded"
            or score["independent_skill_claim"] or uncertainty["nationwide_promotion_eligible"]
            or district["public_product_allowed"]):
        raise _error(503, "Nationwide research evidence chain or promotion boundary is invalid")
    mask_path = OUT / "research_land_mask.npy"
    static, _ = _json(BASE / "nationwide_research_static_v1.json")
    if not mask_path.is_file() or _sha(mask_path) != static["mask_sha256"]:
        raise _error(503, "Nationwide research mask hash mismatch")
    return {"protocol": protocol, "protocol_sha256": psha, "features": features,
            "seal": seal, "seal_sha256": ssha, "score": score, "score_sha256": score_sha,
            "uncertainty": uncertainty, "uncertainty_sha256": usha,
            "district": district, "district_sha256": dsha, "mask_path": mask_path}


def _case(chain: dict, case_id: str) -> dict:
    match = next((row for row in chain["seal"]["predictions"] if row["case_id"] == case_id), None)
    if match is None or match["year"] != 2024:
        raise _error(404, "Only sealed 2024 development cases are available")
    path = ROOT / match["file"]
    if not path.is_file() or _sha(path) != match["sha256"]:
        raise _error(503, "Nationwide research case prediction hash mismatch")
    return match


@router.get("/overview")
def overview() -> dict:
    chain = _chain()
    metrics = chain["score"]["same_case_cell_metrics"]["ALL_INDIA"]["0"]
    return {"status": "CONSUMED_2024_DEVELOPMENT_RESEARCH_ONLY", "source_track": "B_OPERATIONAL_GEFS",
            "year": 2024, "cases": len(chain["seal"]["predictions"]),
            "paired_cells": metrics["M0"]["cells"], "model_default": "regional_M2",
            "m2_selection_passed": chain["seal"]["m2_selected"] is not None,
            "nationwide_promotion_eligible": False, "geometry_status": "2021 research geometry, not official",
            "probability_status": PROBABILITY_STATUS,
            "protocol_sha256": chain["protocol_sha256"], "score_sha256": chain["score_sha256"],
            "uncertainty_sha256": chain["uncertainty_sha256"],
            "models": {name: {"rmse_mm": block["metrics"]["continuous"]["rmse_mm"],
                              "heavy_csi": block["metrics"]["heavy"]["metrics"]["CSI"],
                              "very_heavy_csi": block["metrics"]["very_heavy"]["metrics"]["CSI"]}
                       for name, block in metrics.items()},
            "regional_gate": {name: {"M0_heavy_csi": values["0"]["M0"]["heavy_csi"],
                                     "M2_heavy_csi": values["0"]["M2"]["heavy_csi"],
                                     "M2_minus_raw_ci95": values["0"]["M2"]["heavy_csi_delta_ci95"],
                                     "event_support": values["0"]["M2"]["support"]}
                              for name, values in chain["uncertainty"]["results"].items() if "0" in values},
            "caveat": "Sealed consumed-2024 development comparison, not independent skill or an operational warning."}


@router.get("/cases")
def cases() -> dict:
    chain = _chain()
    return {"year": 2024, "status": "CONSUMED_DEVELOPMENT_ONLY", "seal_sha256": chain["seal_sha256"],
            "cases": [{"case_id": row["case_id"], "lead_hours": row["hour"], "available_locally": (ROOT / row["file"]).is_file()}
                      for row in chain["seal"]["predictions"]]}


@router.get("/verification", response_model=NationwideVerification)
def verification(region: str = Query("ALL_INDIA"), lead_hours: int = Query(0)) -> NationwideVerification:
    """Serve sealed same-case 2024 development metrics, never a new verification run."""
    chain = _chain()
    score_regions = chain["score"]["same_case_cell_metrics"]
    lead = str(lead_hours)
    if region not in score_regions or lead not in score_regions[region]:
        raise _error(404, "Requested development region or lead is unavailable")
    models = score_regions[region][lead]
    uncertainty = chain["uncertainty"]["results"][region][lead]
    if set(models) != {"M0", "M1", "M2", "M3", "M4"} or set(uncertainty) != set(models):
        raise _error(503, "Same-case model ladder or uncertainty is incomplete")
    paired = {(block["cases"], block["cells"]) for block in models.values()}
    if len(paired) != 1:
        raise _error(503, "Model ladder does not share identical cases and cells")
    cases_count, cells_count = paired.pop()
    return NationwideVerification(
        status="CONSUMED_2024_DEVELOPMENT_RESEARCH_ONLY",
        source_track="B_OPERATIONAL_GEFS", reference="IMD_RF25_03_TO_03_UTC",
        region=region, lead_hours=lead_hours, paired_cases=cases_count, paired_cells=cells_count,
        models=models, uncertainty=uncertainty,
        protocol_sha256=chain["protocol_sha256"], score_sha256=chain["score_sha256"],
        uncertainty_sha256=chain["uncertainty_sha256"], independent_skill_claim=False,
        caveat="Sealed consumed-2024 development verification. Date-block intervals do not remove spatial or serial dependence. No independent nationwide skill or operational warning claim.",
    )


@router.get("/grid")
def grid(case_id: str = Query(...), field: str = Query(...)) -> dict:
    chain = _chain()
    if field not in FIELDS:
        raise _error(404, "Requested nationwide research field is unavailable")
    row = _case(chain, case_id)
    mask = np.load(chain["mask_path"], allow_pickle=False)
    with np.load(ROOT / row["file"], allow_pickle=False) as bundle:
        value = bundle[field]
    if mask.shape != GRID_SHAPE or value.shape != (int(mask.sum()),) or not np.isfinite(value).all() or np.any(value < 0):
        raise _error(503, "Nationwide research field shape/values invalid")
    if field.endswith("_p") and np.any(value > 1):
        raise _error(503, "Nationwide research probability exceeds one")
    full = np.full(GRID_SHAPE, np.nan)
    full[mask] = value
    values = [[float(cell) if valid else None for cell, valid in zip(vrow, mrow)] for vrow, mrow in zip(full, mask)]
    product = next(name for name, hour in LEADS.items() if hour == row["hour"])
    return {"case_id": case_id, "year": 2024, "source_track": "B_OPERATIONAL_GEFS",
            "status": "CONSUMED_2024_DEVELOPMENT_RESEARCH_ONLY", "field": field,
            "units": "probability" if field.endswith("_p") else "mm per 24 h",
            "probability_status": PROBABILITY_STATUS if field.endswith("_p") else None,
            "accumulation_window_hours": chain["protocol"]["sources"]["windows_hours"][product],
            "grid": {"crs": "EPSG:4326", "shape": list(GRID_SHAPE),
                     "latitude_centers": LATITUDE.tolist(), "longitude_centers": LONGITUDE.tolist(),
                     "cell_size_degrees": 0.25, "bounds_west_south_east_north": [66.375, 6.375, 100.125, 38.625],
                     "row_order": "south_to_north", "column_order": "west_to_east",
                     "mask_policy": "2021 research district polygons, positive cell-area overlap"},
            "values": values, "valid_mask": mask.tolist(), "valid_cells": int(mask.sum()),
            "prediction_sha256": row["sha256"], "fit_seal_sha256": chain["seal_sha256"],
            "caveat": "Historical development forecast. The original probability method failed a validation audit; its warning cutoffs and reliability are unvalidated. No independent nationwide correction or calibrated-warning claim."}


@router.get("/districts")
def districts(case_id: str = Query(...)) -> dict:
    chain = _chain()
    _case(chain, case_id)
    match = next((row for row in chain["district"]["case_tables"] if row["case_id"] == case_id), None)
    if match is None or not (ROOT / match["file"]).is_file() or _sha(ROOT / match["file"]) != match["sha256"]:
        raise _error(503, "Nationwide research district table hash mismatch")
    table = json.loads((ROOT / match["file"]).read_text(encoding="utf-8"))
    return {"case_id": case_id, "status": "LOCAL_RESEARCH_GEOMETRY_ONLY_NOT_OFFICIAL",
            "districts": table["rows"], "table_sha256": match["sha256"],
            "coverage_rule": chain["district"]["coverage_rule"],
            "caveat": "2021 simplified research boundaries; redistribution rights and official geometry are unresolved."}
