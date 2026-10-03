"""Read-only, hash-verified reforecast study: the heavy-rain model comparison (R05) and the regime-detection tasks (R03) on the sealed years 2014-2016 (protocol v1, docs/142).

Serves the tracked files under backend/app/evidence_data/phase15/. It never recomputes a statistic: it verifies the chain (every sidecar, the protocol hash in the manifest, the unseal record and every
result, both selection freezes, every result file's hash, and that the unseal record was written before any sealed observation was read) and serves what was frozen.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel

try:
    from backend.app.api.evidence import EVIDENCE_LABELS
    from backend.app.api.operational import ScienceErrorCode, _science_error
    from backend.app.ml.phase2b import sha256_file
except ModuleNotFoundError:
    from app.api.evidence import EVIDENCE_LABELS
    from app.api.operational import ScienceErrorCode, _science_error
    from app.ml.phase2b import sha256_file

router = APIRouter(prefix="/science/evidence/reforecast", tags=["Reforecast study (frozen, hash-verified)"])

PHASE15 = Path(__file__).resolve().parents[1] / "evidence_data" / "phase15"
NAMES = {"protocol": "reforecast_study_protocol_v1.json", "selection": "reforecast_selection_freeze.json", "tasks": "regime_tasks_selection_freeze.json", "unseal": "reforecast_unseal_record.json",
         "manifest": "reforecast_manifest.json"}
CAVEATS = [
    "GEFSv12 reforecast control member (not the operational model), June to September, 2000-2016, a different lineage from the operational years: never pooled with them.",
    "Sealed years 2014-2016: no earlier model, selection or experiment used them; they were opened once, after the selections were frozen, under a signed record. Bootstrap intervals resample whole initialization dates and are optimistic.",
    "Regime labels are objective, rule-based and relative by construction (IMD and ERA5 derived); they are not the published classifications and not an expert analysis. ERA5 is a reanalysis, used only to label past days.",
    "The western-disturbance task compares a forecast trough with a reanalysis trough, so it largely verifies the forecast height field; a regime verdict never implies skill for a new forecast cycle.",
    "FSS and district verification are not part of this study.",
]


class ReforecastOverview(BaseModel):
    protocol_sha256: str
    manifest_sha256: str
    purpose: str
    populations: dict[str, Any]
    data: dict[str, Any]
    r05: dict[str, Any]
    r03: dict[str, Any]
    selection: dict[str, Any]
    regime_tasks_selection: dict[str, Any]
    unseal_record: dict[str, Any]
    evidence_label: str
    caveats: list[str]


class ReforecastResult(BaseModel):
    evidence_role: str
    evidence_label: str
    evidence_sha256: str
    protocol_sha256: str
    payload: dict[str, Any]
    caveats: list[str]


@lru_cache(maxsize=1)
def _chain() -> dict[str, Any]:
    docs, shas = {}, {}
    for key, name in NAMES.items():
        path = PHASE15 / name
        if not path.is_file():
            raise _science_error(404, ScienceErrorCode.PRODUCT_UNAVAILABLE, "The reforecast study evidence has not been published")
        side = path.with_suffix(".sha256")
        shas[key] = sha256_file(path)
        if not side.is_file() or side.read_text(encoding="ascii").split()[0] != shas[key]:
            raise _science_error(503, ScienceErrorCode.INTEGRITY_FAILURE, f"Reforecast sidecar hash mismatch: {name}")
        docs[key] = json.loads(path.read_text(encoding="utf-8"))
    m, u = docs["manifest"], docs["unseal"]
    consistent = (m["protocol_sha256"] == shas["protocol"] and u["protocol_sha256"] == shas["protocol"] and m["unseal_record_sha256"] == shas["unseal"] and m["selection_freeze_sha256"] == shas["selection"]
                  and m["regime_tasks_freeze_sha256"] == shas["tasks"] and u["selection_freeze_sha256"] == shas["selection"] and u["regime_tasks_freeze_sha256"] == shas["tasks"]
                  and docs["selection"]["protocol_sha256"] == shas["protocol"] and docs["tasks"]["protocol_sha256"] == shas["protocol"]
                  and docs["selection"]["sealed_test"]["opened"] is False and docs["tasks"]["sealed_test"]["opened"] is False and u["written_before_any_sealed_observation_was_read"] is True
                  and docs["protocol"]["no_observation_read"] is True)
    if not consistent:
        raise _science_error(503, ScienceErrorCode.INTEGRITY_FAILURE, "Reforecast hash chain is inconsistent")
    for name, entry in m["files"].items():
        if not (PHASE15 / name).is_file() or sha256_file(PHASE15 / name) != entry["sha256"]:
            raise _science_error(503, ScienceErrorCode.INTEGRITY_FAILURE, f"Reforecast integrity failure: {name}")
    return {"docs": docs, "shas": shas}


def _result(name: str) -> tuple[dict, str]:
    chain = _chain()
    entry = chain["docs"]["manifest"]["files"].get(name)
    data = json.loads((PHASE15 / name).read_text(encoding="utf-8"))
    role = data.get("evidence_role")
    if entry is None or role != entry["evidence_role"] or role not in EVIDENCE_LABELS or data.get("protocol_sha256") != chain["shas"]["protocol"] or data.get("unseal_record_sha256") != chain["shas"]["unseal"]:
        raise _science_error(503, ScienceErrorCode.INTEGRITY_FAILURE, f"Reforecast role or protocol mismatch: {name}")
    return data, entry["sha256"]


@router.get("/overview", response_model=ReforecastOverview)
def overview() -> ReforecastOverview:
    chain = _chain()
    d = chain["docs"]
    p = d["protocol"]
    role = d["manifest"]["files"]["reforecast_r05_test.json"]["evidence_role"]
    tasks = {t: {k: v for k, v in b.items() if k not in ("model", "baseline_model")} for t, b in d["tasks"]["tasks"].items()}
    sel = {"selection": d["selection"]["selection"], "regime_arms_validation": d["selection"]["regime_arms_validation"], "development": d["selection"]["development"], "models": {k: {kk: vv for kk, vv in v.items() if kk != "file"} for k, v in d["selection"]["models"].items()}}
    r05 = {k: v for k, v in p["r05"].items() if k != "grid"}
    r05["grid_size"] = p["r05"]["grid"]["size"]
    return ReforecastOverview(protocol_sha256=chain["shas"]["protocol"], manifest_sha256=chain["shas"]["manifest"], purpose=p["purpose"], populations=p["populations"],
                              data={k: v for k, v in p["data"].items() if k != "forecast_side_files"}, r05=r05, r03=p["r03"], selection=sel, regime_tasks_selection={"tasks": tasks},
                              unseal_record={k: d["unseal"][k] for k in ("written_at_utc", "years", "owner_message", "what_is_authorised", "what_is_not_authorised", "disclosed_before_opening")},
                              evidence_label=EVIDENCE_LABELS[role], caveats=CAVEATS)


def _serve(name: str) -> ReforecastResult:
    data, digest = _result(name)
    return ReforecastResult(evidence_role=data["evidence_role"], evidence_label=EVIDENCE_LABELS[data["evidence_role"]], evidence_sha256=digest, protocol_sha256=data["protocol_sha256"], payload=data, caveats=CAVEATS)


@router.get("/r05", response_model=ReforecastResult)
def r05() -> ReforecastResult:
    return _serve("reforecast_r05_test.json")


@lru_cache(maxsize=1)
def _confirmation() -> dict[str, Any]:
    """Round 2 (amendment 3): the confirmation record, its manifest and the evidence file, chained to the protocol, the amendment and the round-1 evidence."""
    chain = _chain()
    names = {"record": "reforecast_confirmation_unseal_record.json", "manifest": "reforecast_confirmation_manifest.json", "amendment": "reforecast_protocol_v1_amendment_3.json"}
    docs, shas = {}, {}
    for key, name in names.items():
        path = PHASE15 / name
        if not path.is_file():
            raise _science_error(404, ScienceErrorCode.PRODUCT_UNAVAILABLE, "The confirmatory round has not been published")
        shas[key] = sha256_file(path)
        side = path.with_suffix(".sha256")
        if not side.is_file() or side.read_text(encoding="ascii").split()[0] != shas[key]:
            raise _science_error(503, ScienceErrorCode.INTEGRITY_FAILURE, f"Confirmation sidecar hash mismatch: {name}")
        docs[key] = json.loads(path.read_text(encoding="utf-8"))
    rec, man = docs["record"], docs["manifest"]
    r1 = chain["docs"]["manifest"]["files"]["reforecast_r05_test.json"]["sha256"]
    ok = (man["protocol_sha256"] == chain["shas"]["protocol"] and man["confirmation_record_sha256"] == shas["record"] and rec["hashes"]["reforecast_protocol_v1_amendment_3.json"] == shas["amendment"]
          and rec["hashes"]["reforecast_r05_test.json"] == r1 and rec["hashes"]["reforecast_selection_freeze.json"] == chain["shas"]["selection"]
          and rec["written_before_any_2017_2019_observation_was_read_for_this_study"] is True and docs["amendment"]["amends_protocol_sha256"] == chain["shas"]["protocol"])
    if not ok:
        raise _science_error(503, ScienceErrorCode.INTEGRITY_FAILURE, "Confirmation hash chain is inconsistent")
    for name, entry in man["files"].items():
        if not (PHASE15 / name).is_file() or sha256_file(PHASE15 / name) != entry["sha256"]:
            raise _science_error(503, ScienceErrorCode.INTEGRITY_FAILURE, f"Confirmation integrity failure: {name}")
    return {"docs": docs, "shas": shas}


def _confirmation_result() -> tuple[dict, str]:
    chain = _confirmation()
    entry = chain["docs"]["manifest"]["files"]["reforecast_r05_confirmation.json"]
    data = json.loads((PHASE15 / "reforecast_r05_confirmation.json").read_text(encoding="utf-8"))
    role = data.get("evidence_role")
    if role != entry["evidence_role"] or role not in EVIDENCE_LABELS or data.get("confirmation_record_sha256") != chain["shas"]["record"]:
        raise _science_error(503, ScienceErrorCode.INTEGRITY_FAILURE, "Confirmation role or record mismatch")
    return data, entry["sha256"]


@router.get("/r05-confirmation", response_model=ReforecastResult)
def r05_confirmation() -> ReforecastResult:
    data, digest = _confirmation_result()
    return ReforecastResult(evidence_role=data["evidence_role"], evidence_label=EVIDENCE_LABELS[data["evidence_role"]], evidence_sha256=digest, protocol_sha256=data["protocol_sha256"], payload=data,
                            caveats=CAVEATS + ["Round 2 is a confirmatory test: delta, the mean-error shift, was read from round 1 and not tuned on 2017-2019; the years were used by earlier Track A experiments of this project."])


@router.get("/r03", response_model=ReforecastResult)
def r03() -> ReforecastResult:
    return _serve("reforecast_r03_test.json")
