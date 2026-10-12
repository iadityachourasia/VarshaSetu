"""Read-only, hash-verified Raw GEFS verification over the whole IMD grid (protocol v1, docs/140).

Serves the tracked files under backend/app/evidence_data/phase14/. It never recomputes a statistic: it verifies the chain (protocol sidecar, manifest sidecar, the protocol hash in the manifest and in
every result, the ledger hash recorded in the protocol, every file's hash) and serves what was frozen. Only the unmodified Raw control rainfall is compared; no model is applied anywhere.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

import numpy as np
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
ROOT = Path(__file__).resolve().parents[3]
PROTOCOL, MANIFEST, LEDGER = PHASE14 / "all_india_raw_protocol_v1.json", PHASE14 / "all_india_raw_manifest.json", PHASE14 / "all_india_raw_ledger_v1.json"
YEARS = (2023, 2024, 2025)
GEOMETRY = ROOT / "data/static/phase2c/geoBoundaries-IND-ADM2_simplified.geojson"
GEOMETRY_SHA256 = "d68db39cd3e2d0892af268e2b0454166368ce3b5b8a78fcda63069ec92a641db"
BUNDLE = PHASE14 / "india_map_demo_v1"
WINDOWS = {"day1_24h": (3, 27), "day2_24h": (27, 51), "day3_24h": (51, 75)}
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


class RawCase(BaseModel):
    case_id: str
    initialization: str
    product: str
    accumulation_window_hours: tuple[int, int]
    available_locally: bool


class RawCaseList(BaseModel):
    year: int
    evidence_role: str
    ledger_sha256: str
    cases: list[RawCase]
    caveat: str


class RawGrid(BaseModel):
    case_id: str
    year: int
    evidence_role: str
    source_track: str
    field: str
    units: str
    initialization: str
    accumulation_window_hours: tuple[int, int]
    grid: dict[str, Any]
    values: list[list[float]]
    display_mask: list[list[bool]]
    raw_array_sha256: str
    ledger_sha256: str
    geometry_sha256: str
    caveat: str


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


def _included(year: int) -> list[dict[str, Any]]:
    if year not in YEARS:
        raise _science_error(404, ScienceErrorCode.PRODUCT_UNAVAILABLE, "No Raw all-India case catalogue for this year")
    chain = _chain()
    ledger = json.loads(LEDGER.read_text(encoding="utf-8"))
    if sha256_file(LEDGER) != chain["shas"]["ledger"]:
        raise _science_error(503, ScienceErrorCode.INTEGRITY_FAILURE, "All-India Raw ledger changed")
    return [entry for entry in ledger["populations"][str(year)] if entry["status"] == "INCLUDED"]


def _cache_path(entry: dict[str, Any], year: int) -> Path:
    relative = Path(entry["path"])
    expected = Path("data/operational_derived/all_india_raw_v1") / str(year) / f"{entry['case_id']}.npy"
    if relative != expected:
        raise _science_error(503, ScienceErrorCode.INTEGRITY_FAILURE, "Raw grid path does not match the sealed ledger")
    primary = ROOT / relative
    if primary.is_file():
        return primary
    fallback = BUNDLE / f"{entry['case_id']}.npy"
    if year == 2025 and fallback.is_file():
        manifest_path = BUNDLE / "manifest.json"
        receipt = manifest_path.with_suffix(".sha256")
        if not manifest_path.is_file() or not receipt.is_file() or receipt.read_text(encoding="ascii").split() != [sha256_file(manifest_path), manifest_path.name]:
            raise _science_error(503, ScienceErrorCode.INTEGRITY_FAILURE, "India Raw demo bundle manifest receipt mismatch")
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        item = manifest.get("cases", {}).get(entry["case_id"])
        if (manifest.get("schema") != "india-map-raw-demo-v1" or manifest.get("ledger_sha256") != _chain()["shas"]["ledger"]
                or item is None or item.get("sha256") != entry["sha256"] or item.get("filename") != fallback.name):
            raise _science_error(503, ScienceErrorCode.INTEGRITY_FAILURE, "India Raw demo bundle does not match the frozen ledger")
        return fallback
    return primary


@lru_cache(maxsize=1)
def _display_mask() -> np.ndarray:
    """Research-boundary display clipping only; never a verification or model mask."""
    if not GEOMETRY.is_file() or sha256_file(GEOMETRY) != GEOMETRY_SHA256:
        raise _science_error(503, ScienceErrorCode.INTEGRITY_FAILURE, "Research boundary source is missing or changed")
    from shapely import contains_xy, union_all
    from shapely.geometry import shape

    features = json.loads(GEOMETRY.read_text(encoding="utf-8"))["features"]
    country = union_all([shape(feature["geometry"]) for feature in features])
    ledger = json.loads(LEDGER.read_text(encoding="utf-8"))
    longitude, latitude = np.meshgrid(ledger["grid"]["longitude"], ledger["grid"]["latitude"])
    return np.asarray(contains_xy(country, longitude, latitude), dtype=bool)


@router.get("/cases", response_model=RawCaseList)
def cases(year: int = Query(...)) -> RawCaseList:
    entries = _included(year)
    role = _result(year)[0]["evidence_role"]
    return RawCaseList(
        year=year, evidence_role=role, ledger_sha256=_chain()["shas"]["ledger"],
        cases=[RawCase(case_id=e["case_id"], initialization=e["initialization"], product=e["product"],
                       accumulation_window_hours=WINDOWS[e["product"]], available_locally=_cache_path(e, year).is_file()) for e in entries],
        caveat="Included historical Raw GEFS control cases only. Local cache availability does not imply corrected India-wide skill.",
    )


@router.get("/grid", response_model=RawGrid)
def grid(year: int = Query(...), case_id: str = Query(...)) -> RawGrid:
    entry = next((e for e in _included(year) if e["case_id"] == case_id), None)
    if entry is None:
        raise _science_error(404, ScienceErrorCode.PRODUCT_UNAVAILABLE, "Case is not an included all-India Raw forecast")
    path = _cache_path(entry, year)
    if not path.is_file():
        raise _science_error(404, ScienceErrorCode.PRODUCT_UNAVAILABLE, "Verified local all-India Raw array is unavailable")
    if sha256_file(path) != entry["sha256"]:
        raise _science_error(503, ScienceErrorCode.INTEGRITY_FAILURE, "All-India Raw array hash mismatch")
    try:
        values = np.load(path, allow_pickle=False)
    except (OSError, ValueError) as error:
        raise _science_error(503, ScienceErrorCode.INTEGRITY_FAILURE, f"All-India Raw array cannot be decoded: {error}")
    if values.shape != (129, 135) or not np.issubdtype(values.dtype, np.number) or not np.isfinite(values).all() or np.any(values < 0):
        raise _science_error(503, ScienceErrorCode.INTEGRITY_FAILURE, "All-India Raw array shape or rainfall values are invalid")
    ledger = json.loads(LEDGER.read_text(encoding="utf-8"))
    mask = _display_mask()
    if mask.shape != values.shape:
        raise _science_error(503, ScienceErrorCode.INTEGRITY_FAILURE, "Research display mask and forecast grid differ")
    latitude, longitude = ledger["grid"]["latitude"], ledger["grid"]["longitude"]
    return RawGrid(
        case_id=case_id, year=year, evidence_role=_result(year)[0]["evidence_role"], source_track="B_OPERATIONAL_GEFS",
        field="M0_RAW_GEFS", units="mm per 24 h", initialization=entry["initialization"],
        accumulation_window_hours=WINDOWS[entry["product"]],
        grid={"crs": "EPSG:4326", "shape": [129, 135], "latitude_centers": latitude, "longitude_centers": longitude,
              "cell_size_degrees": 0.25, "bounds_west_south_east_north": [66.375, 6.375, 100.125, 38.625],
              "row_order": "south_to_north", "column_order": "west_to_east", "mask_policy": "visual clipping by pinned 2021 research geometry; not the IMD verification mask"},
        values=values.astype(float).tolist(), display_mask=mask.tolist(), raw_array_sha256=entry["sha256"],
        ledger_sha256=_chain()["shas"]["ledger"], geometry_sha256=GEOMETRY_SHA256,
        caveat="Historical Raw GEFS across the full IMD grid. The display clips to simplified 2021 research geometry, which is not official or complete; verification uses a separate IMD valid-cell mask. No correction or probability is supplied outside the regional model domain.",
    )
