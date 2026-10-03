"""Read-only, hash-verified forecast-time western-disturbance indicator (protocol v1, docs/138).

Serves the tracked files under backend/app/evidence_data/phase13/. It never recomputes an index or a flag: it verifies the chain (protocol sidecar, manifest sidecar, the protocol hash in the manifest
and in every result, the case-file hash recorded in the protocol, every file's hash) and serves what was frozen. The indicator is a rule-based trough heuristic; it is not a validated detection of
western disturbances and it is not used as an input to any model.
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

router = APIRouter(prefix="/science/evidence/wd-indicator", tags=["Western-disturbance indicator (frozen, hash-verified)"])

PHASE13 = Path(__file__).resolve().parents[1] / "evidence_data" / "phase13"
PROTOCOL, MANIFEST, CASES = PHASE13 / "wd_indicator_protocol_v1.json", PHASE13 / "wd_indicator_manifest.json", PHASE13 / "wd_indicator_cases_v1.json"
YEARS = (2021, 2022, 2024, 2025)
CAVEATS = [
    "A rule-based forecast-time trough heuristic (mean geostrophic vorticity at 500 hPa over north-west India from the forecast height alone). It is NOT a validated detection of western disturbances: no label source exists.",
    "The flag is relative: the upper tercile of the 2023 training-year distribution. The share of flagged cases differs between years.",
    "The association is descriptive and about observed rainfall in the western Himalaya and Punjab box in the monsoon season, when much of that rainfall is monsoon rainfall and not western-disturbance rainfall.",
    "The corpus covers June to early October; western disturbances mainly act in winter. The 2017-2019 reforecast track is not used (only a 5-30 N window was kept for it).",
    "Consumed holdouts (2022 and 2025) are post-hoc descriptive analyses. Bootstrap intervals resample whole initialization dates and are optimistic.",
    "No model uses this indicator and there is no western-disturbance-aware correction. The rainfall verification domain still stops at 22 N.",
]


class WdOverview(BaseModel):
    protocol_sha256: str
    manifest_sha256: str
    cases_file_sha256: str
    status: str
    purpose: str
    definition: dict[str, Any]
    evaluation: dict[str, Any]
    decision_rule: dict[str, Any]
    decision: dict[str, Any]
    not_established: list[str]
    populations: dict[str, Any]
    available: list[dict[str, Any]]
    caveats: list[str]


class WdResult(BaseModel):
    year: int
    evidence_role: str
    evidence_label: str
    evidence_sha256: str
    protocol_sha256: str
    payload: dict[str, Any]
    caveats: list[str]


class WdCases(BaseModel):
    year: int
    evidence_label: str
    cases_file_sha256: str
    threshold: dict[str, Any]
    cases: list[dict[str, Any]]
    caveats: list[str]


@lru_cache(maxsize=1)
def _chain() -> dict[str, Any]:
    for path in (PROTOCOL, MANIFEST, CASES):
        if not path.is_file():
            raise _science_error(503, ScienceErrorCode.INTEGRITY_FAILURE, f"Western-disturbance evidence file is unavailable: {path.name}")
    for path, sidecar in ((PROTOCOL, "wd_indicator_protocol_v1.sha256"), (MANIFEST, "wd_indicator_manifest.sha256")):
        side = PHASE13 / sidecar
        if not side.is_file() or side.read_text(encoding="ascii").split()[0] != sha256_file(path):
            raise _science_error(503, ScienceErrorCode.INTEGRITY_FAILURE, f"Western-disturbance sidecar hash mismatch: {path.name}")
    protocol, manifest, cases = (json.loads(p.read_text(encoding="utf-8")) for p in (PROTOCOL, MANIFEST, CASES))
    shas = {"protocol": sha256_file(PROTOCOL), "manifest": sha256_file(MANIFEST), "cases": sha256_file(CASES)}
    if manifest["protocol_sha256"] != shas["protocol"] or protocol["definition"]["cases_file_sha256"] != shas["cases"] or manifest["cases_file_sha256"] != shas["cases"]:
        raise _science_error(503, ScienceErrorCode.INTEGRITY_FAILURE, "Western-disturbance hash chain is inconsistent")
    if cases["threshold"] != protocol["definition"]["threshold"]:
        raise _science_error(503, ScienceErrorCode.INTEGRITY_FAILURE, "Western-disturbance threshold differs between the protocol and the case file")
    for name, entry in manifest["files"].items():
        if not (PHASE13 / name).is_file() or sha256_file(PHASE13 / name) != entry["sha256"]:
            raise _science_error(503, ScienceErrorCode.INTEGRITY_FAILURE, f"Western-disturbance integrity failure: {name}")
    return {"protocol": protocol, "manifest": manifest, "cases": cases, "shas": shas}


@lru_cache(maxsize=4)
def _result(year: int) -> tuple[dict, str]:
    chain = _chain()
    name = f"wd_indicator_{year}.json"
    entry = chain["manifest"]["files"].get(name)
    if year not in YEARS or entry is None:
        raise _science_error(404, ScienceErrorCode.PRODUCT_UNAVAILABLE, f"No western-disturbance evidence for {year}. Available: {', '.join(str(y) for y in YEARS)}")
    data = json.loads((PHASE13 / name).read_text(encoding="utf-8"))
    role = data.get("evidence_role")
    if role != entry["evidence_role"] or role not in EVIDENCE_LABELS or data.get("protocol_sha256") != chain["shas"]["protocol"] or data.get("year") != year:
        raise _science_error(503, ScienceErrorCode.INTEGRITY_FAILURE, f"Western-disturbance role, year or protocol mismatch: {name}")
    return data, entry["sha256"]


@router.get("/overview", response_model=WdOverview)
def overview() -> WdOverview:
    chain = _chain()
    protocol = chain["protocol"]
    available = []
    for year in YEARS:
        data, _ = _result(year)
        available.append({"year": year, "evidence_role": data["evidence_role"], "evidence_label": EVIDENCE_LABELS[data["evidence_role"]], "cases_scored": data["cases_scored"], "development": data["development"]})
    return WdOverview(protocol_sha256=chain["shas"]["protocol"], manifest_sha256=chain["shas"]["manifest"], cases_file_sha256=chain["shas"]["cases"], status=protocol["status"], purpose=protocol["purpose"],
                      definition=protocol["definition"], evaluation=protocol["evaluation"], decision_rule=protocol["decision_rule"], decision=chain["manifest"]["decision"],
                      not_established=protocol["not_established_whatever_the_result"], populations=protocol["populations"], available=available, caveats=CAVEATS)


@router.get("/result", response_model=WdResult)
def result(year: int = Query(...)) -> WdResult:
    data, digest = _result(year)
    return WdResult(year=year, evidence_role=data["evidence_role"], evidence_label=EVIDENCE_LABELS[data["evidence_role"]], evidence_sha256=digest, protocol_sha256=data["protocol_sha256"], payload=data, caveats=CAVEATS)


@router.get("/cases", response_model=WdCases)
def cases(year: int = Query(...)) -> WdCases:
    data, _ = _result(year)
    chain = _chain()
    return WdCases(year=year, evidence_label=EVIDENCE_LABELS[data["evidence_role"]], cases_file_sha256=chain["shas"]["cases"], threshold=chain["cases"]["threshold"],
                   cases=chain["cases"]["populations"][str(year)], caveats=CAVEATS)
