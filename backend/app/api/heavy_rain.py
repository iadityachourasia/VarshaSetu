"""Read-only, hash-verified heavy-rain bundle (B1) layer for the 2019 map and district products (docs/143).

It serves what the local builder wrote under backend/app/evidence_data/phase17/ and never recomputes a prediction. Every request first checks the chain: the protocol and manifest sidecars, the protocol hash recorded
in the manifest, the array file hash, and that the confirmatory record and evidence the bundle depends on still carry the hashes the protocol froze. A mismatch is an integrity failure (503), never a quiet fallback.
The district rows are the frozen district aggregation applied to the stored B1 fields and the product's own raw and observed cells.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

import numpy as np
from fastapi import APIRouter
from pydantic import BaseModel

try:
    from backend.app.api import science
    from backend.app.api.evidence import EVIDENCE_LABELS
    from backend.app.api.operational import ScienceErrorCode, _district_static, _science_error
    from backend.app.ml import heavy_rain_product as hp
    from backend.app.ml.geoaware import G2_MAX_ABS_BIAS_MM
    from backend.app.ml.phase2b import sha256_file
except ModuleNotFoundError:
    from app.api import science
    from app.api.evidence import EVIDENCE_LABELS
    from app.api.operational import ScienceErrorCode, _district_static, _science_error
    from app.ml import heavy_rain_product as hp
    from app.ml.geoaware import G2_MAX_ABS_BIAS_MM
    from app.ml.phase2b import sha256_file

router = APIRouter(prefix="/science/heavy-rain", tags=["Heavy-rain bundle in the 2019 products (frozen, hash-verified)"])

EVIDENCE = Path(__file__).resolve().parents[1] / "evidence_data"
PHASE15, PHASE17 = EVIDENCE / "phase15", EVIDENCE / "phase17"
PROTOCOL = PHASE17 / "heavy_rain_integration_protocol_v1.json"
MANIFEST = PHASE17 / "heavy_rain_b1_manifest.json"
YEAR = 2019
CAVEATS = [
    "The heavy and very-heavy outputs are scores from a class-weighted classifier with a threshold fixed on validation years, not calibrated probabilities. The map of the score and the yes/no decision are two views of the same output.",
    "At the frozen thresholds the yes/no forecast over-forecasts heavy and very-heavy events: it flags more events than were observed (frequency bias above one in the frozen evidence), which raises hits and false alarms together.",
    "The bundle was built on the GEFSv12 reforecast control member (2000 to 2016). It is a different model version from the operational years and has not been tested there.",
    "The first test round failed its mean-error guardrail; the one-parameter shift was read from that round, and the second round is confirmatory, not untouched. The 2019 cases shown here were part of those confirmatory years and had been used by earlier Track A experiments.",
    "This is a descriptive display of frozen predictions. Nothing was selected, tuned or recalibrated on these cases, and regime-aware routing is not part of this bundle.",
]


def _fail(message: str) -> Exception:
    return _science_error(503, ScienceErrorCode.INTEGRITY_FAILURE, f"Heavy-rain bundle integrity failure: {message}")


def _sidecar_ok(path: Path) -> str:
    side = path.with_suffix(".sha256")
    if not path.is_file() or not side.is_file():
        raise _fail(f"{path.name} or its sidecar is missing")
    digest = sha256_file(path)
    if side.read_text(encoding="ascii").split()[0] != digest:
        raise _fail(f"{path.name} differs from its sidecar")
    return digest


@lru_cache(maxsize=1)
def _chain() -> dict[str, Any]:
    protocol_sha = _sidecar_ok(PROTOCOL)
    manifest_sha = _sidecar_ok(MANIFEST)
    protocol = json.loads(PROTOCOL.read_text(encoding="utf-8"))
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    if manifest["protocol_sha256"] != protocol_sha:
        raise _fail("the manifest was not built under this protocol")
    arrays = PHASE17 / manifest["arrays_file"]
    if not arrays.is_file() or sha256_file(arrays) != manifest["arrays_sha256"]:
        raise _fail("the array file differs from the manifest")
    record = PHASE15 / "reforecast_confirmation_unseal_record.json"
    evidence = PHASE15 / "reforecast_r05_confirmation.json"
    if sha256_file(record) != protocol["bundle"]["confirmation_record_sha256"] or sha256_file(record) != manifest["confirmation_record_sha256"]:
        raise _fail("the confirmatory record differs from the one the protocol froze")
    if sha256_file(evidence) != protocol["bundle"]["confirmation_evidence_sha256"]:
        raise _fail("the confirmatory evidence differs from the one the protocol froze")
    if json.loads(record.read_text(encoding="utf-8"))["model_files_sha256"] != manifest["model_files_sha256"]:
        raise _fail("the model hashes differ from the confirmatory record")
    with np.load(arrays, allow_pickle=False) as data:
        loaded = {name: data[name] for name in data.files}
    ids = [str(x) for x in loaded["case_ids"]]
    if len(ids) != manifest["cases"] or len(set(ids)) != len(ids) or loaded["b1_rainfall"].shape != (len(ids), 49, 49):
        raise _fail("the array file does not match its manifest")
    return {"protocol": protocol, "manifest": manifest, "protocol_sha": protocol_sha, "manifest_sha": manifest_sha, "evidence": json.loads(evidence.read_text(encoding="utf-8")), "arrays": loaded,
            "index": {case: i for i, case in enumerate(ids)}}


def _nullable(grid: np.ndarray) -> list[list[float | None]]:
    return np.where(np.isfinite(grid), grid.astype(np.float64), None).tolist()


class HeavyRainOverview(BaseModel):
    year: int
    cases: int
    evidence_label: str
    bundle_label: str
    shift_mm: float
    bias_guardrail_mm: float
    slice_bias_within_limit: bool
    thresholds_mm: dict[str, float]
    decision_thresholds: dict[str, float]
    protocol_sha256: str
    manifest_sha256: str
    arrays_sha256: str
    summary: dict[str, Any]
    confirmation: dict[str, Any]
    caveats: list[str]


class HeavyRainCase(BaseModel):
    case_id: str
    year: int
    b1_rainfall_mm: list[list[float | None]]
    heavy_score: list[list[float | None]]
    very_heavy_score: list[list[float | None]]
    heavy_decision: list[list[float | None]]
    very_heavy_decision: list[list[float | None]]
    decision_thresholds: dict[str, float]
    b1_rmse_mm: float
    evidence_label: str
    caveats: list[str]


class HeavyRainDistricts(BaseModel):
    case_id: str
    year: int
    districts: list[dict[str, Any]]
    aggregation: str
    decision_thresholds: dict[str, float]
    evidence_label: str
    caveats: list[str]


def _label() -> str:
    return EVIDENCE_LABELS[_chain()["protocol"]["labels"]["track_a_2019_role"]]


@router.get("/overview", response_model=HeavyRainOverview)
def overview() -> HeavyRainOverview:
    chain = _chain()
    manifest, evidence = chain["manifest"], chain["evidence"]
    decision = evidence["bundle_decision"]["decision"]
    confirmation = {"label": evidence["label"], "years": evidence["years"], "cases": evidence["cases"], "tier": decision["tier"], "bias_within_limit": decision["BIAS_OK"],
                    "pooled": {k: evidence["pooled"][k] for k in ("M0", "B1_shifted")}, "exceedance": {k: evidence["exceedance"][k]["test"] for k in ("B1:heavy", "B1:very_heavy")},
                    "raw_categorical": evidence["raw_categorical"], "delta_source": evidence["delta_source"]}
    return HeavyRainOverview(year=YEAR, cases=manifest["cases"], evidence_label=_label(), bundle_label=chain["protocol"]["labels"]["wording"], shift_mm=manifest["shift_mm"],
                             bias_guardrail_mm=G2_MAX_ABS_BIAS_MM, slice_bias_within_limit=abs(manifest["summary_2019"]["rainfall"]["B1"]["bias_mm"]) <= G2_MAX_ABS_BIAS_MM,
                             thresholds_mm=dict(hp.THRESHOLDS), decision_thresholds=manifest["thresholds"], protocol_sha256=chain["protocol_sha"], manifest_sha256=chain["manifest_sha"],
                             arrays_sha256=manifest["arrays_sha256"], summary=manifest["summary_2019"], confirmation=confirmation, caveats=CAVEATS)


def _index(case_id: str) -> tuple[int, dict[str, Any]]:
    chain = _chain()
    if case_id not in chain["index"]:
        raise _science_error(404, ScienceErrorCode.CASE_NOT_FOUND, "No heavy-rain bundle output exists for this case")
    return chain["index"][case_id], chain


@router.get("/cases/{case_id}", response_model=HeavyRainCase)
def case(case_id: str) -> HeavyRainCase:
    i, chain = _index(case_id)
    a, taus = chain["arrays"], chain["manifest"]["thresholds"]
    return HeavyRainCase(case_id=case_id, year=YEAR, b1_rainfall_mm=_nullable(a["b1_rainfall"][i]), heavy_score=_nullable(a["heavy_score"][i]), very_heavy_score=_nullable(a["very_heavy_score"][i]),
                         heavy_decision=_nullable(hp.decision(a["heavy_score"][i], taus["heavy"])), very_heavy_decision=_nullable(hp.decision(a["very_heavy_score"][i], taus["very_heavy"])),
                         decision_thresholds=taus, b1_rmse_mm=float(a["case_rmse_b1"][i]), evidence_label=_label(), caveats=CAVEATS)


@router.get("/cases/{case_id}/districts", response_model=HeavyRainDistricts)
def districts(case_id: str) -> HeavyRainDistricts:
    i, chain = _index(case_id)
    product, _ = science._case(case_id)                                    # the product's own verified case record
    path = science.ARTIFACTS / "cases" / product["array_file"]
    if sha256_file(path) != product["array_sha256"]:
        raise _science_error(503, ScienceErrorCode.INTEGRITY_FAILURE, "Case array integrity failure")
    with np.load(path, allow_pickle=False) as app:
        raw, observed = app["raw"].astype(np.float64), app["observed"].astype(np.float64)
    a, taus = chain["arrays"], chain["manifest"]["thresholds"]
    listing, weights, _, _ = _district_static()
    rows = hp.aggregate_b1_districts(listing, weights, raw=raw, observed=observed, b1_rainfall=a["b1_rainfall"][i], heavy_score=a["heavy_score"][i], very_heavy_score=a["very_heavy_score"][i], taus=taus)
    regime = {d["district_id"]: d.get("dominant_regime") for d in product["districts"]}
    for row in rows:
        row["dominant_regime"] = regime.get(row["district_id"])
    return HeavyRainDistricts(case_id=case_id, year=YEAR, districts=rows, aggregation="grid-cell polygon overlap, cosine-latitude area approximation (the frozen district aggregation)",
                              decision_thresholds=taus, evidence_label=_label(), caveats=CAVEATS)
