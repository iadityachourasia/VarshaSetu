"""Read-only, hash-verified Raw GEFS verification over the whole IMD grid (protocol v1, docs/140).

Serves the tracked files under backend/app/evidence_data/phase14/. It never recomputes a statistic: it verifies the chain (protocol sidecar, manifest sidecar, the protocol hash in the manifest and in
every result, the ledger hash recorded in the protocol, every file's hash) and serves what was frozen. Only the unmodified Raw control rainfall is compared; no model is applied anywhere.
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

router = APIRouter(prefix="/science/evidence/all-india-raw", tags=["All-India Raw verification (frozen, hash-verified)"])

PHASE14 = Path(__file__).resolve().parents[1] / "evidence_data" / "phase14"
PROTOCOL, MANIFEST, LEDGER = PHASE14 / "all_india_raw_protocol_v1.json", PHASE14 / "all_india_raw_manifest.json", PHASE14 / "all_india_raw_ledger_v1.json"
YEARS = (2023, 2024, 2025)
CAVEATS = [
    "Raw only: the unmodified control-member GEFS rainfall is compared with IMD. No model was applied, so this says nothing about any correction outside the 10 to 22 N and 68 to 80 E modelling box.",
    "Only leads that passed the regional canonical rainfall reconstruction are used, and the wider all-India reconstruction excluded further cases; the populations are therefore smaller than the regional study and not identical to it.",
    "Regions are a fixed latitude-longitude rule, a description of where the forecast is checked, not meteorological regimes. A region with too few cases or observed events carries no number.",
    "The corpus covers June to early October. Bootstrap intervals resample whole initialization dates and are optimistic. IMD observations are the reference and carry their own gauge-density limits, which differ between regions.",
    "2023 is the training year of the downstream models (nothing is fitted here); 2024 is a reused development year; 2025 is a consumed holdout and is a post-hoc descriptive analysis.",
]


class AllIndiaOverview(BaseModel):
    protocol_sha256: str
    manifest_sha256: str
    ledger_sha256: str
    status: str
    purpose: str
    definition: dict[str, Any]
    evaluation: dict[str, Any]
    decision_rule: str
    not_established: list[str]
    populations: dict[str, Any]
    available: list[dict[str, Any]]
    caveats: list[str]


class AllIndiaResult(BaseModel):
    year: int
    evidence_role: str
    evidence_label: str
    evidence_sha256: str
    protocol_sha256: str
    payload: dict[str, Any]
    caveats: list[str]


@lru_cache(maxsize=1)
def _chain() -> dict[str, Any]:
    for path in (PROTOCOL, MANIFEST, LEDGER):
        if not path.is_file():
            raise _science_error(503, ScienceErrorCode.INTEGRITY_FAILURE, f"All-India Raw evidence file is unavailable: {path.name}")
    for path, sidecar in ((PROTOCOL, "all_india_raw_protocol_v1.sha256"), (MANIFEST, "all_india_raw_manifest.sha256")):
        side = PHASE14 / sidecar
        if not side.is_file() or side.read_text(encoding="ascii").split()[0] != sha256_file(path):
            raise _science_error(503, ScienceErrorCode.INTEGRITY_FAILURE, f"All-India Raw sidecar hash mismatch: {path.name}")
    protocol, manifest = (json.loads(p.read_text(encoding="utf-8")) for p in (PROTOCOL, MANIFEST))
    shas = {"protocol": sha256_file(PROTOCOL), "manifest": sha256_file(MANIFEST), "ledger": sha256_file(LEDGER)}
    if manifest["protocol_sha256"] != shas["protocol"] or protocol["definition"]["ledger_file_sha256"] != shas["ledger"] or manifest["ledger_file_sha256"] != shas["ledger"]:
        raise _science_error(503, ScienceErrorCode.INTEGRITY_FAILURE, "All-India Raw hash chain is inconsistent")
    for name, entry in manifest["files"].items():
        if not (PHASE14 / name).is_file() or sha256_file(PHASE14 / name) != entry["sha256"]:
            raise _science_error(503, ScienceErrorCode.INTEGRITY_FAILURE, f"All-India Raw integrity failure: {name}")
    return {"protocol": protocol, "manifest": manifest, "shas": shas}


@lru_cache(maxsize=4)
def _result(year: int) -> tuple[dict, str]:
    chain = _chain()
    name = f"all_india_raw_{year}.json"
    entry = chain["manifest"]["files"].get(name)
    if year not in YEARS or entry is None:
        raise _science_error(404, ScienceErrorCode.PRODUCT_UNAVAILABLE, f"No all-India Raw evidence for {year}. Available: {', '.join(str(y) for y in YEARS)}")
    data = json.loads((PHASE14 / name).read_text(encoding="utf-8"))
    role = data.get("evidence_role")
    if role != entry["evidence_role"] or role not in EVIDENCE_LABELS or data.get("protocol_sha256") != chain["shas"]["protocol"] or data.get("year") != year:
        raise _science_error(503, ScienceErrorCode.INTEGRITY_FAILURE, f"All-India Raw role, year or protocol mismatch: {name}")
    return data, entry["sha256"]


@router.get("/overview", response_model=AllIndiaOverview)
def overview() -> AllIndiaOverview:
    chain = _chain()
    protocol = chain["protocol"]
    available = []
    for year in YEARS:
        data, _ = _result(year)
        available.append({"year": year, "evidence_role": data["evidence_role"], "evidence_label": EVIDENCE_LABELS[data["evidence_role"]], "cases_scored": data["cases_scored"], "development": data["development"]})
    return AllIndiaOverview(protocol_sha256=chain["shas"]["protocol"], manifest_sha256=chain["shas"]["manifest"], ledger_sha256=chain["shas"]["ledger"], status=protocol["status"], purpose=protocol["purpose"],
                            definition=protocol["definition"], evaluation=protocol["evaluation"], decision_rule=protocol["decision_rule"], not_established=protocol["not_established_whatever_the_result"],
                            populations=protocol["populations"], available=available, caveats=CAVEATS)


@router.get("/result", response_model=AllIndiaResult)
def result(year: int = Query(...)) -> AllIndiaResult:
    data, digest = _result(year)
    return AllIndiaResult(year=year, evidence_role=data["evidence_role"], evidence_label=EVIDENCE_LABELS[data["evidence_role"]], evidence_sha256=digest, protocol_sha256=data["protocol_sha256"], payload=data, caveats=CAVEATS)
