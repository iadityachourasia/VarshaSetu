"""Read-only, hash-verified independent check of the regime classifier (protocol v1, docs/136).

Serves the tracked files under backend/app/evidence_data/phase6/ (regime_validation_*). It never recomputes labels or scores: it verifies the chain (protocol sidecar, manifest sidecar,
protocol hash recorded in the manifest and in every result, every file's hash) and serves what was frozen. Active and break only: depression is explicitly not validated, and the labels are
an implementation of rainfall criteria with documented deviations, not the published classification.
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

router = APIRouter(prefix="/science/evidence/regime-validation", tags=["Independent regime validation (frozen, hash-verified)"])

PHASE6 = Path(__file__).resolve().parents[1] / "evidence_data" / "phase6"
PROTOCOL, MANIFEST = PHASE6 / "regime_validation_protocol_v1.json", PHASE6 / "regime_validation_manifest.json"
TRACK_OF_YEAR = {2018: "A", 2019: "A", 2024: "B", 2025: "B"}
CAVEATS = [
    "Independent of the pseudo-labelling rule, but only for active and break: a pseudo-regime called LOW_DEPRESSION_INFLUENCED has no observation-based label here and is NOT validated.",
    "The labels are an implementation of rainfall criteria in the style of Rajeevan et al. (2010) with documented deviations (a box for the core zone, a moving-average climatology, one pooled standard deviation, a 36-year climatology); they are not the published classification and the criteria were not verified against the paper's text.",
    "Only July and August days carry a label; cases whose paired day falls in June or September are not scored.",
    "The break class of the classifier merges break with weak monsoon, and the published criteria define no weak or neutral state, so the break task is break versus not break only.",
    "Consumed holdouts (2019 and 2025) are post-hoc descriptive analyses. Bootstrap intervals resample whole initialization dates and are optimistic.",
    "Separate from, and never merged with, the agreement with the pseudo-labels. The IMD files and daily series stay local; only aggregate counts and scores are served.",
]


class RegimeValidationOverview(BaseModel):
    protocol_sha256: str
    manifest_sha256: str
    status: str
    purpose: str
    criteria: dict[str, Any]
    tasks: dict[str, str]
    support_gate: dict[str, Any]
    observation_only_counts: dict[str, Any]
    approval: dict[str, Any]
    available: list[dict[str, Any]]
    caveats: list[str]


class RegimeValidationResult(BaseModel):
    track: str
    year: int
    evidence_role: str
    evidence_label: str
    evidence_sha256: str
    protocol_sha256: str
    payload: dict[str, Any]
    caveats: list[str]


@lru_cache(maxsize=1)
def _chain() -> dict[str, Any]:
    for path in (PROTOCOL, MANIFEST):
        if not path.is_file():
            raise _science_error(503, ScienceErrorCode.INTEGRITY_FAILURE, f"Regime validation evidence file is unavailable: {path.name}")
    for path, sidecar in ((PROTOCOL, "regime_validation_protocol_v1.sha256"), (MANIFEST, "regime_validation_manifest.sha256")):
        side = PHASE6 / sidecar
        if not side.is_file() or side.read_text(encoding="ascii").split()[0] != sha256_file(path):
            raise _science_error(503, ScienceErrorCode.INTEGRITY_FAILURE, f"Regime validation sidecar hash mismatch: {path.name}")
    protocol, manifest = (json.loads(p.read_text(encoding="utf-8")) for p in (PROTOCOL, MANIFEST))
    shas = {"protocol": sha256_file(PROTOCOL), "manifest": sha256_file(MANIFEST)}
    if manifest["protocol_sha256"] != shas["protocol"]:
        raise _science_error(503, ScienceErrorCode.INTEGRITY_FAILURE, "Regime validation protocol hash differs from the manifest")
    for name, entry in manifest["files"].items():
        if not (PHASE6 / name).is_file() or sha256_file(PHASE6 / name) != entry["sha256"]:
            raise _science_error(503, ScienceErrorCode.INTEGRITY_FAILURE, f"Regime validation integrity failure: {name}")
    return {"protocol": protocol, "manifest": manifest, "shas": shas}


@lru_cache(maxsize=4)
def _result(year: int) -> tuple[dict, str]:
    chain = _chain()
    track = TRACK_OF_YEAR.get(year)
    name = f"regime_validation_{track}_{year}.json"
    entry = chain["manifest"]["files"].get(name)
    if track is None or entry is None:
        raise _science_error(404, ScienceErrorCode.PRODUCT_UNAVAILABLE, f"No regime validation for {year}. Available: {', '.join(str(y) for y in sorted(TRACK_OF_YEAR))}")
    data = json.loads((PHASE6 / name).read_text(encoding="utf-8"))
    role = data.get("evidence_role")
    if role != entry["evidence_role"] or role not in EVIDENCE_LABELS or data.get("protocol_sha256") != chain["shas"]["protocol"] or data.get("track") != track:
        raise _science_error(503, ScienceErrorCode.INTEGRITY_FAILURE, f"Regime validation role, track or protocol mismatch: {name}")
    return data, entry["sha256"]


@router.get("/overview", response_model=RegimeValidationOverview)
def overview() -> RegimeValidationOverview:
    chain = _chain()
    protocol = chain["protocol"]
    available = []
    for year in sorted(TRACK_OF_YEAR):
        data, _ = _result(year)
        available.append({"track": data["track"], "year": year, "evidence_role": data["evidence_role"], "evidence_label": EVIDENCE_LABELS[data["evidence_role"]], "cases_labelled": data["cases_labelled"]})
    criteria = {k: v for k, v in protocol["criteria"].items() if k != "climatology"}
    clim = protocol["criteria"]["climatology"]
    criteria["climatology"] = {"years": clim["years"], "smoothing": clim["smoothing"], "sigma": clim["sigma"], "sigma_mm_per_day": clim["sigma_mm_per_day"], "files": len(clim["file_sha256"])}
    return RegimeValidationOverview(
        protocol_sha256=chain["shas"]["protocol"], manifest_sha256=chain["shas"]["manifest"], status=protocol["status"], purpose=protocol["purpose"], criteria=criteria, tasks=protocol["tasks"],
        support_gate=protocol["support_gate"], observation_only_counts=protocol["observation_only_counts"], approval=protocol["approval"], available=available, caveats=CAVEATS)


@router.get("/result", response_model=RegimeValidationResult)
def result(year: int = Query(...)) -> RegimeValidationResult:
    data, digest = _result(year)
    return RegimeValidationResult(track=data["track"], year=year, evidence_role=data["evidence_role"], evidence_label=EVIDENCE_LABELS[data["evidence_role"]], evidence_sha256=digest,
                                  protocol_sha256=data["protocol_sha256"], payload=data, caveats=CAVEATS)
