"""Read-only, hash-verified coastal/orographic zone evidence (Phase 7, docs/115-118).

Serves the tracked files under backend/app/evidence_data/phase7/ (static geography, Stage 1 zone verification, Stage 2 forcing
strata). It never trains, re-infers or recomputes a metric: it verifies the frozen hash chain (protocol v3, geography artifact,
Stage 2 spec, both manifests and every file) and reshapes what was frozen. A payload whose evidence role has no registered label
is refused, so a consumed holdout can never be shown without its post-hoc label.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Query
from pydantic import BaseModel

try:
    from backend.app.api.evidence import EVIDENCE_LABELS
    from backend.app.api.operational import ScienceErrorCode, _science_error
    from backend.app.ml.phase2b import sha256_file
except ModuleNotFoundError:
    from app.api.evidence import EVIDENCE_LABELS
    from app.api.operational import ScienceErrorCode, _science_error
    from app.ml.phase2b import sha256_file

router = APIRouter(prefix="/science/evidence/zones", tags=["Coastal/orographic zone evidence (frozen, hash-verified)"])

APP = Path(__file__).resolve().parents[1] / "evidence_data"
PHASE6, PHASE7 = APP / "phase6", APP / "phase7"
PROTOCOL = PHASE6 / "coastal_orographic_protocol_v3.json"
GEOGRAPHY = PHASE7 / "static_geography_v1.json"
SPEC = PHASE7 / "zone_stage2_spec_v1.json"
STAGE1_MANIFEST = PHASE7 / "zone_verification_manifest.json"
STAGE2_MANIFEST = PHASE7 / "zone_stage2_manifest.json"
PRE_REGISTERED_ZONES = ("COASTAL", "OROGRAPHIC", "COASTAL_AND_OROGRAPHIC", "OTHER")
ZONE_NOTES = {
    "COASTAL": "land cell within 100 km of the coast, relief below 300 m",
    "OROGRAPHIC": "local relief of at least 300 m (3x3 cells), more than 100 km from the coast",
    "COASTAL_AND_OROGRAPHIC": "both rules: in practice the Western Ghats coast",
    "OTHER": "neither rule: mostly the interior plateau",
}
CAVEATS = [
    "Zones are a transparent rule-based convention (distance to coast and local relief on a 0.25 degree grid), not a learned, validated or official regime.",
    "Descriptive re-aggregation of frozen predictions; no model was trained, tuned or selected for this view.",
    "Consumed holdouts (Track A 2019, Track B 2025) are post-hoc descriptive analyses and must not be used to select, tune or re-rank a model.",
    "Track B 2024 was used for model selection and calibration; it is development evidence, not an independent test.",
    "Paired whole-case bootstrap intervals are optimistic: cells within a case are correlated and consecutive days are serially correlated.",
    "Track A (GEFSv12 reforecast) and Track B (operational GEFS) are different populations and are never pooled.",
    "FSS is not reported: the zones are scattered cell sets, so a neighbourhood score would mix zone and non-zone cells.",
    "0.25 degree grid cells smooth the Ghats; a null or weak result is a statement about this resolution.",
    "Historical replay of frozen models only; not warning skill and not an operational service.",
]


class GeographyResponse(BaseModel):
    protocol: dict[str, Any]
    source: dict[str, Any]
    grid: dict[str, Any]
    method: dict[str, Any]
    qa: dict[str, Any]
    zone_cell_counts: dict[str, int]
    zone_notes: dict[str, str]
    sensitivity_only_counts: dict[str, Any]
    fields: dict[str, Any]
    geography_sha256: str
    caveats: list[str]


class ZoneVerificationResponse(BaseModel):
    track: str
    year: int
    evidence_role: str
    evidence_label: str
    evidence_sha256: str
    stage: str
    payload: dict[str, Any]
    caveats: list[str]


class ZoneOverviewResponse(BaseModel):
    protocol_sha256: str
    spec_sha256: str
    geography_sha256: str
    stage1_manifest_sha256: str
    stage2_manifest_sha256: str
    status: str
    stage_3_authorised: bool
    stage_3_recommended_by_pre_registered_rule: bool
    available: list[dict[str, Any]]
    decision_stage1: dict[str, Any]
    decision_stage2: dict[str, Any]
    caveats: list[str]


@lru_cache(maxsize=1)
def _chain() -> dict[str, Any]:
    """Verify the whole frozen chain once. Any mismatch is a hard integrity failure (503), never a fallback."""
    for path in (PROTOCOL, GEOGRAPHY, SPEC, STAGE1_MANIFEST, STAGE2_MANIFEST):
        if not path.is_file():
            raise _science_error(503, ScienceErrorCode.INTEGRITY_FAILURE, f"Zone evidence file is unavailable: {path.name}")
    shas = {name: sha256_file(path) for name, path in (("protocol", PROTOCOL), ("geography", GEOGRAPHY), ("spec", SPEC),
                                                       ("stage1", STAGE1_MANIFEST), ("stage2", STAGE2_MANIFEST))}
    for manifest, sidecar in ((STAGE1_MANIFEST, "zone_verification_manifest.sha256"), (STAGE2_MANIFEST, "zone_stage2_manifest.sha256"),
                              (GEOGRAPHY, "static_geography_v1.sha256"), (SPEC, "zone_stage2_spec_v1.sha256")):
        side = PHASE7 / sidecar
        if not side.is_file() or side.read_text(encoding="ascii").split()[0] != sha256_file(manifest):
            raise _science_error(503, ScienceErrorCode.INTEGRITY_FAILURE, f"Zone evidence sidecar hash mismatch: {manifest.name}")
    s1, s2 = (json.loads(p.read_text(encoding="utf-8")) for p in (STAGE1_MANIFEST, STAGE2_MANIFEST))
    spec = json.loads(SPEC.read_text(encoding="utf-8"))
    geography = json.loads(GEOGRAPHY.read_text(encoding="utf-8"))
    expected = [
        (s1["protocol_sha256"], shas["protocol"]), (s2["protocol_sha256"], shas["protocol"]), (geography["protocol"]["sha256"], shas["protocol"]),
        (s1["static_geography_sha256"], shas["geography"]), (s2["static_geography_sha256"], shas["geography"]),
        (s2["spec_sha256"], shas["spec"]), (spec["parent"]["protocol_v3_sha256"], shas["protocol"]),
        (spec["parent"]["static_geography_sha256"], shas["geography"]), (spec["parent"]["stage1_manifest_sha256"], shas["stage1"]),
    ]
    if any(a != b for a, b in expected) or not geography["qa"]["criteria_met"]:
        raise _science_error(503, ScienceErrorCode.INTEGRITY_FAILURE, "Zone evidence hash chain is inconsistent")
    return {"shas": shas, "stage1": s1, "stage2": s2, "geography": geography}


@lru_cache(maxsize=16)
def _evidence(stage: str, name: str) -> tuple[dict, str]:
    chain = _chain()
    manifest = chain["stage1" if stage == "stage1" else "stage2"]
    entry = manifest["files"].get(name)
    path = PHASE7 / name
    if entry is None or not path.resolve().is_relative_to(PHASE7.resolve()) or not path.is_file():
        raise _science_error(404, ScienceErrorCode.PRODUCT_UNAVAILABLE, "No such zone evidence file")
    if sha256_file(path) != entry["sha256"]:
        raise _science_error(503, ScienceErrorCode.INTEGRITY_FAILURE, f"Zone evidence integrity failure: {name}")
    data = json.loads(path.read_text(encoding="utf-8"))
    role = data.get("evidence_role")
    if role is not None and (role != entry["evidence_role"] or role not in EVIDENCE_LABELS):
        raise _science_error(503, ScienceErrorCode.INTEGRITY_FAILURE, f"Zone evidence role is missing or unregistered: {name}")
    return data, entry["sha256"]


def _available(stage: str) -> list[dict[str, Any]]:
    manifest = _chain()[stage]
    return sorted(({"track": e["track"], "year": e["year"], "evidence_role": e["evidence_role"], "evidence_label": EVIDENCE_LABELS[e["evidence_role"]],
                    "cases": e["cases"]} for e in manifest["files"].values() if "track" in e), key=lambda row: (row["track"], row["year"]))


@router.get("/overview", response_model=ZoneOverviewResponse)
def overview() -> ZoneOverviewResponse:
    chain = _chain()
    summary1, _ = _evidence("stage1", "zone_decision_summary.json")
    summary2, _ = _evidence("stage2", "zone_stage2_summary.json")
    protocol = json.loads(PROTOCOL.read_text(encoding="utf-8"))
    return ZoneOverviewResponse(
        protocol_sha256=chain["shas"]["protocol"], spec_sha256=chain["shas"]["spec"], geography_sha256=chain["shas"]["geography"],
        stage1_manifest_sha256=chain["shas"]["stage1"], stage2_manifest_sha256=chain["shas"]["stage2"], status=protocol["status"],
        stage_3_authorised=bool(protocol["stages"]["3"]["authorised"]),
        stage_3_recommended_by_pre_registered_rule=bool(summary1["stage_3_recommended"]),
        available=_available("stage1"), decision_stage1=summary1, decision_stage2=summary2, caveats=CAVEATS)


@router.get("/geography", response_model=GeographyResponse)
def geography() -> GeographyResponse:
    chain = _chain()
    g = chain["geography"]
    return GeographyResponse(protocol=g["protocol"], source=g["source"], grid=g["grid"], method=g["method"], qa=g["qa"],
                             zone_cell_counts=g["zone_cell_counts"], zone_notes=ZONE_NOTES, sensitivity_only_counts=g["sensitivity_only_counts"],
                             fields={k: g["fields"][k] for k in ("footprint", "zone", "mean_elevation_m", "local_relief_m", "distance_to_coast_km")},
                             geography_sha256=chain["shas"]["geography"], caveats=CAVEATS)


def _by_year(stage: str, prefix: str, track: str, year: int) -> ZoneVerificationResponse:
    name = f"{prefix}_{track}_{year}.json"
    manifest = _chain()[stage]
    if name not in manifest["files"]:
        available = sorted(f"{e['track']}/{e['year']}" for e in manifest["files"].values() if "track" in e)
        raise _science_error(404, ScienceErrorCode.PRODUCT_UNAVAILABLE,
                             f"No zone evidence for track {track} year {year}. Available: {', '.join(available)}")
    data, digest = _evidence(stage, name)
    return ZoneVerificationResponse(track=track, year=year, evidence_role=data["evidence_role"], evidence_label=EVIDENCE_LABELS[data["evidence_role"]],
                                    evidence_sha256=digest, stage=stage, payload=data, caveats=CAVEATS)


@router.get("/verification", response_model=ZoneVerificationResponse)
def verification(track: str = Query(..., pattern="^[AB]$"), year: int = Query(...)) -> ZoneVerificationResponse:
    return _by_year("stage1", "zone_verification", track, year)


@router.get("/forcing", response_model=ZoneVerificationResponse)
def forcing(track: str = Query(..., pattern="^[AB]$"), year: int = Query(...)) -> ZoneVerificationResponse:
    return _by_year("stage2", "zone_stage2", track, year)
