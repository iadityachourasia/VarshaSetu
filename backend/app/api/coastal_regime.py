"""Read-only, hash-verified forecast-time coastal and orographic forcing regime (protocol v1, docs/137).

Serves the tracked files under backend/app/evidence_data/phase12/. It never recomputes an index or a class: it verifies the chain (protocol sidecar, manifest sidecar, the protocol hash in the
manifest and in every result, the case-file hash recorded in the protocol, every file's hash) and serves what was frozen. The regime is a rule-based heuristic of the physical forcing; it is
not a learned or validated regime and its percentile is a rank, not a probability.
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

router = APIRouter(prefix="/science/evidence/coastal-regime", tags=["Coastal/orographic forcing regime (frozen, hash-verified)"])

PHASE12 = Path(__file__).resolve().parents[1] / "evidence_data" / "phase12"
PROTOCOL, MANIFEST, CASES = PHASE12 / "coastal_regime_protocol_v1.json", PHASE12 / "coastal_regime_manifest.json", PHASE12 / "coastal_regime_cases_v1.json"
TRACK_OF_YEAR = {2018: "A", 2019: "A", 2024: "B", 2025: "B"}
CAVEATS = [
    "A rule-based heuristic of the physical forcing (forecast cross-barrier wind component times precipitable water over the Ghats-coast zone), not a learned or validated regime.",
    "The percentile is a rank within the training-year distribution of the same track, not a probability of rain.",
    "Terciles were fitted on the training year only (Track A 2017, Track B 2023). Later years have more STRONG cases than a third, so the class share shifts between years.",
    "The discrimination shown restates, per case, what the cell-level forcing strata of docs/118 already showed: observed heavy rain on the Ghats coast concentrates under strong forcing. It is descriptive evidence, not a validation, and part of the concentration reflects that the STRONG class holds most cases.",
    "Consumed holdouts (2019 and 2025) are post-hoc descriptive analyses. Bootstrap intervals resample whole cases and are optimistic. Track A and Track B are never pooled.",
    "No model uses this regime: the frozen correction models and the geography-aware correction do not take it as an input.",
]


class CoastalRegimeOverview(BaseModel):
    protocol_sha256: str
    manifest_sha256: str
    cases_file_sha256: str
    status: str
    purpose: str
    definition: dict[str, Any]
    evaluation: dict[str, Any]
    decision_rule: dict[str, Any]
    decision: dict[str, Any]
    populations: dict[str, Any]
    available: list[dict[str, Any]]
    caveats: list[str]


class CoastalRegimeResult(BaseModel):
    track: str
    year: int
    evidence_role: str
    evidence_label: str
    evidence_sha256: str
    protocol_sha256: str
    payload: dict[str, Any]
    caveats: list[str]


class CoastalRegimeCases(BaseModel):
    track: str
    year: int
    evidence_label: str
    cases_file_sha256: str
    cut_points: dict[str, Any]
    cases: list[dict[str, Any]]
    caveats: list[str]


@lru_cache(maxsize=1)
def _chain() -> dict[str, Any]:
    for path in (PROTOCOL, MANIFEST, CASES):
        if not path.is_file():
            raise _science_error(503, ScienceErrorCode.INTEGRITY_FAILURE, f"Coastal regime evidence file is unavailable: {path.name}")
    for path, sidecar in ((PROTOCOL, "coastal_regime_protocol_v1.sha256"), (MANIFEST, "coastal_regime_manifest.sha256")):
        side = PHASE12 / sidecar
        if not side.is_file() or side.read_text(encoding="ascii").split()[0] != sha256_file(path):
            raise _science_error(503, ScienceErrorCode.INTEGRITY_FAILURE, f"Coastal regime sidecar hash mismatch: {path.name}")
    protocol, manifest, cases = (json.loads(p.read_text(encoding="utf-8")) for p in (PROTOCOL, MANIFEST, CASES))
    shas = {"protocol": sha256_file(PROTOCOL), "manifest": sha256_file(MANIFEST), "cases": sha256_file(CASES)}
    if manifest["protocol_sha256"] != shas["protocol"] or protocol["definition"]["cases_file_sha256"] != shas["cases"] or manifest["cases_file_sha256"] != shas["cases"]:
        raise _science_error(503, ScienceErrorCode.INTEGRITY_FAILURE, "Coastal regime hash chain is inconsistent")
    if cases["cut_points"] != protocol["definition"]["cut_points"]:
        raise _science_error(503, ScienceErrorCode.INTEGRITY_FAILURE, "Coastal regime cut-points differ between the protocol and the case file")
    for name, entry in manifest["files"].items():
        if not (PHASE12 / name).is_file() or sha256_file(PHASE12 / name) != entry["sha256"]:
            raise _science_error(503, ScienceErrorCode.INTEGRITY_FAILURE, f"Coastal regime integrity failure: {name}")
    return {"protocol": protocol, "manifest": manifest, "cases": cases, "shas": shas}


@lru_cache(maxsize=4)
def _result(year: int) -> tuple[dict, str]:
    chain = _chain()
    track = TRACK_OF_YEAR.get(year)
    name = f"coastal_regime_{track}_{year}.json"
    entry = chain["manifest"]["files"].get(name)
    if track is None or entry is None:
        raise _science_error(404, ScienceErrorCode.PRODUCT_UNAVAILABLE, f"No coastal regime evidence for {year}. Available: {', '.join(str(y) for y in sorted(TRACK_OF_YEAR))}")
    data = json.loads((PHASE12 / name).read_text(encoding="utf-8"))
    role = data.get("evidence_role")
    if role != entry["evidence_role"] or role not in EVIDENCE_LABELS or data.get("protocol_sha256") != chain["shas"]["protocol"] or data.get("track") != track:
        raise _science_error(503, ScienceErrorCode.INTEGRITY_FAILURE, f"Coastal regime role, track or protocol mismatch: {name}")
    return data, entry["sha256"]


@router.get("/overview", response_model=CoastalRegimeOverview)
def overview() -> CoastalRegimeOverview:
    chain = _chain()
    protocol = chain["protocol"]
    available = []
    for year in sorted(TRACK_OF_YEAR):
        data, _ = _result(year)
        available.append({"track": data["track"], "year": year, "evidence_role": data["evidence_role"], "evidence_label": EVIDENCE_LABELS[data["evidence_role"]], "cases": data["cases"], "development": data["development"]})
    return CoastalRegimeOverview(
        protocol_sha256=chain["shas"]["protocol"], manifest_sha256=chain["shas"]["manifest"], cases_file_sha256=chain["shas"]["cases"], status=protocol["status"], purpose=protocol["purpose"],
        definition=protocol["definition"], evaluation=protocol["evaluation"], decision_rule=protocol["decision_rule"], decision=chain["manifest"]["decision"], populations=protocol["populations"],
        available=available, caveats=CAVEATS)


@router.get("/result", response_model=CoastalRegimeResult)
def result(year: int = Query(...)) -> CoastalRegimeResult:
    data, digest = _result(year)
    return CoastalRegimeResult(track=data["track"], year=year, evidence_role=data["evidence_role"], evidence_label=EVIDENCE_LABELS[data["evidence_role"]], evidence_sha256=digest,
                               protocol_sha256=data["protocol_sha256"], payload=data, caveats=CAVEATS)


@router.get("/cases", response_model=CoastalRegimeCases)
def cases(year: int = Query(...)) -> CoastalRegimeCases:
    data, _ = _result(year)
    chain = _chain()
    population = f"{data['track']}{year}"
    return CoastalRegimeCases(track=data["track"], year=year, evidence_label=EVIDENCE_LABELS[data["evidence_role"]], cases_file_sha256=chain["shas"]["cases"],
                              cut_points=chain["cases"]["cut_points"][data["track"]], cases=chain["cases"]["populations"][population], caveats=CAVEATS)
