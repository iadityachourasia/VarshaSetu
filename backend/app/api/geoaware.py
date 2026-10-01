"""Read-only, hash-verified geography-aware (M5a) experiment evidence (Phase 9, docs/124 and docs/126).

Serves the tracked files under backend/app/evidence_data/phase9/. It never trains, predicts or recomputes: it verifies the frozen chain (protocol,
selection freeze, manifest, every file and the hash references between them) and serves what was frozen. This is a development-only experiment whose
pre-registered rule was not met; the payload says so and carries the evidence label of each year.
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

router = APIRouter(prefix="/science/evidence/geoaware", tags=["Geography-aware experiment (frozen, hash-verified)"])

PHASE9 = Path(__file__).resolve().parents[1] / "evidence_data" / "phase9"
PROTOCOL, FREEZE, MANIFEST, DECISION = (PHASE9 / n for n in ("geoaware_protocol_v1.json", "geoaware_selection_freeze.json", "geoaware_manifest.json", "geoaware_decision.json"))
YEARS = (2024, 2025)
CAVEATS = [
    "Development-only experiment (option D1(b) of docs/124): one training year, no independent test, 2024 is a reused development year and 2025 is a post-hoc analysis of a completed final test.",
    "The pre-registered decision rule was not met. The model is not presented as an improvement, validated or implemented.",
    "The 2024 and 2025 results have been seen, so any redesign informed by them cannot be judged on those years.",
    "Operational-era track only; historical replay, not warning skill; paired whole-case bootstrap intervals are optimistic.",
    "Zones are a rule-based convention on a 0.25 degree grid, not a learned or validated regime.",
]


class GeoawareOverview(BaseModel):
    protocol_sha256: str
    selection_freeze_sha256: str
    manifest_sha256: str
    status: str
    approval: dict[str, Any]
    decision: dict[str, Any]
    selection: dict[str, Any]
    training: dict[str, Any]
    configurations: list[dict[str, Any]]
    arms: dict[str, list[str]]
    available: list[dict[str, Any]]
    caveats: list[str]


class GeoawareEvaluation(BaseModel):
    year: int
    evidence_role: str
    evidence_label: str
    evidence_sha256: str
    payload: dict[str, Any]
    caveats: list[str]


@lru_cache(maxsize=1)
def _chain() -> dict[str, Any]:
    """Verify the whole frozen chain once. Any mismatch is a hard integrity failure (503), never a fallback."""
    for path in (PROTOCOL, FREEZE, MANIFEST, DECISION):
        if not path.is_file():
            raise _science_error(503, ScienceErrorCode.INTEGRITY_FAILURE, f"Geography-aware evidence file is unavailable: {path.name}")
    for path, sidecar in ((PROTOCOL, "geoaware_protocol_v1.sha256"), (FREEZE, "geoaware_selection_freeze.sha256"), (MANIFEST, "geoaware_manifest.sha256")):
        side = PHASE9 / sidecar
        if not side.is_file() or side.read_text(encoding="ascii").split()[0] != sha256_file(path):
            raise _science_error(503, ScienceErrorCode.INTEGRITY_FAILURE, f"Geography-aware evidence sidecar hash mismatch: {path.name}")
    protocol, freeze, manifest = (json.loads(p.read_text(encoding="utf-8")) for p in (PROTOCOL, FREEZE, MANIFEST))
    shas = {"protocol": sha256_file(PROTOCOL), "freeze": sha256_file(FREEZE), "manifest": sha256_file(MANIFEST)}
    if freeze["protocol_sha256"] != shas["protocol"] or manifest["protocol_sha256"] != shas["protocol"] or manifest["selection_freeze_sha256"] != shas["freeze"]:
        raise _science_error(503, ScienceErrorCode.INTEGRITY_FAILURE, "Geography-aware evidence hash chain is inconsistent")
    for name, entry in manifest["files"].items():
        if not (PHASE9 / name).is_file() or sha256_file(PHASE9 / name) != entry["sha256"]:
            raise _science_error(503, ScienceErrorCode.INTEGRITY_FAILURE, f"Geography-aware evidence integrity failure: {name}")
    return {"shas": shas, "protocol": protocol, "freeze": freeze, "manifest": manifest}


@lru_cache(maxsize=4)
def _evaluation(year: int) -> tuple[dict, str]:
    chain = _chain()
    name = f"geoaware_evaluation_B_{year}.json"
    entry = chain["manifest"]["files"].get(name)
    if entry is None:
        raise _science_error(404, ScienceErrorCode.PRODUCT_UNAVAILABLE, f"No geography-aware evaluation for {year}. Available: {', '.join(str(y) for y in YEARS)}")
    data = json.loads((PHASE9 / name).read_text(encoding="utf-8"))
    role = data.get("evidence_role")
    if role != entry["evidence_role"] or role not in EVIDENCE_LABELS:
        raise _science_error(503, ScienceErrorCode.INTEGRITY_FAILURE, f"Geography-aware evidence role is missing or unregistered: {name}")
    if data["protocol_sha256"] != chain["shas"]["protocol"] or data["selection_freeze_sha256"] != chain["shas"]["freeze"]:
        raise _science_error(503, ScienceErrorCode.INTEGRITY_FAILURE, f"Geography-aware evaluation does not match the frozen chain: {name}")
    return data, entry["sha256"]


@router.get("/overview", response_model=GeoawareOverview)
def overview() -> GeoawareOverview:
    chain = _chain()
    decision = json.loads(DECISION.read_text(encoding="utf-8"))
    freeze, protocol = chain["freeze"], chain["protocol"]
    available = []
    for year in YEARS:
        if f"geoaware_evaluation_B_{year}.json" in chain["manifest"]["files"]:
            data, _ = _evaluation(year)
            available.append({"year": year, "evidence_role": data["evidence_role"], "evidence_label": EVIDENCE_LABELS[data["evidence_role"]], "cases": data["case_count"]})
    return GeoawareOverview(
        protocol_sha256=chain["shas"]["protocol"], selection_freeze_sha256=chain["shas"]["freeze"], manifest_sha256=chain["shas"]["manifest"],
        status=protocol["status"], approval=protocol["approval"], decision=decision, selection=freeze["selection"], training=freeze["training"],
        configurations=freeze["all_configurations"], arms=protocol["feature_registry_v2"]["arms"], available=available, caveats=CAVEATS)


@router.get("/evaluation", response_model=GeoawareEvaluation)
def evaluation(year: int = Query(...)) -> GeoawareEvaluation:
    data, digest = _evaluation(year)
    return GeoawareEvaluation(year=year, evidence_role=data["evidence_role"], evidence_label=EVIDENCE_LABELS[data["evidence_role"]], evidence_sha256=digest, payload=data, caveats=CAVEATS)
