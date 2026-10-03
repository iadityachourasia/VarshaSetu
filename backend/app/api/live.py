"""Read-only, hash-verified experimental cycle bundles (docs/139). Serves what the worker published under data/live/; it never fetches, decodes or infers.

Every request verifies the bundle (manifest sidecar, schema, label, flags, every array hash and shape) and refuses with an integrity failure otherwise. A ``replay`` bundle is a stored historical cycle
pushed through the live code path and is labelled as such everywhere; a ``live`` bundle carries no skill claim because no observation exists yet.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
from fastapi import APIRouter, Query
from pydantic import BaseModel

try:
    from backend.app.api.operational import ScienceErrorCode, _science_error
    from backend.app.live import bundle
except ModuleNotFoundError:
    from app.api.operational import ScienceErrorCode, _science_error
    from app.live import bundle

router = APIRouter(prefix="/science/live", tags=["Experimental live cycle (worker bundles, read-only)"])

ROOT = bundle.ROOT
STALE_AFTER_DAYS = 2
REGIME_NAMES = ("ACTIVE_MONSOON", "BREAK_WEAK_MONSOON", "LOW_DEPRESSION_INFLUENCED")
FIELDS = {"M0": "Raw GEFS control", "M1": "M1 linear MOS (frozen)", "M2": "M2 global XGBoost (frozen)", "M3": "M3 hard regime-aware (frozen)", "M4": "M4 soft regime-aware (frozen)",
          "heavy_probability": "Calibrated heavy-rain probability (64.5 mm per 24 h)", "very_heavy_probability": "Calibrated very-heavy-rain probability (115.6 mm per 24 h)"}
CAVEATS = [
    "EXPERIMENTAL: the frozen Track B models applied to a new forecast cycle. No observation exists for it yet, so there is no verification and no skill statement.",
    "Not an official warning and not a forecast product of any national centre. The input is NOAA GEFS, not an NCMRWF model.",
    "The heavy and very-heavy probabilities are the frozen, calibrated estimates of the 2023 to 2025 study; their reliability for a new cycle is unknown, and very-heavy skill was never shown to improve on Raw.",
    "A lead is withheld, with its reason, when the canonical rainfall reconstruction fails for the cycle, as in the study corpus. A cycle failing any other gate is not published at all.",
    "The applicability check is a range heuristic against the 2023 training matrix, not a validity test. A cycle outside the range is still shown, with the warning.",
]


class CycleSummary(BaseModel):
    kind: str
    cycle: str
    initialization: str
    label: str
    created_at_utc: str
    age_days: int
    stale: bool
    products: list[str]
    withheld_products: dict[str, str]


class LiveStatus(BaseModel):
    has_live_cycle: bool
    latest_live: CycleSummary | None
    cycles: list[CycleSummary]
    message: str
    caveats: list[str]


class LiveCycle(BaseModel):
    summary: CycleSummary
    manifest_sha256: str
    messages: int
    transferred_bytes: int
    frozen_models: dict[str, str]
    applicability: dict[str, Any] | None
    replay_comparison: dict[str, Any] | None
    regime_probabilities: dict[str, dict[str, float]]
    domain_statistics: dict[str, dict[str, dict[str, float]]]
    fields: dict[str, str]
    observation_read: bool
    caveats: list[str]


class LiveField(BaseModel):
    kind: str
    cycle: str
    product: str
    field: str
    label: str
    evidence_label: str
    units: str
    latitude: list[float]
    longitude: list[float]
    values: list[list[float]]
    array_sha256: str


def _summary(directory: Path, manifest: dict) -> CycleSummary:
    start = datetime.fromisoformat(manifest["initialization"].replace("Z", "+00:00"))
    age = max(0, (datetime.now(timezone.utc) - start).days)
    return CycleSummary(kind=manifest["kind"], cycle=manifest["cycle"], initialization=manifest["initialization"], label=manifest["label"], created_at_utc=manifest["created_at_utc"], age_days=age,
                        stale=manifest["kind"] == "live" and age > STALE_AFTER_DAYS, products=manifest["products"], withheld_products=manifest["provenance"].get("withheld_products", {}))


def _verified(kind: str, date: str) -> tuple[Path, dict]:
    if kind not in bundle.KINDS or not (date.isdigit() and len(date) == 8):
        raise _science_error(404, ScienceErrorCode.PRODUCT_UNAVAILABLE, "Unknown bundle kind or cycle")
    directory = ROOT / kind / date
    if not directory.is_dir():
        raise _science_error(404, ScienceErrorCode.PRODUCT_UNAVAILABLE, f"No {kind} bundle for cycle {date}")
    try:
        return directory, bundle.verify_bundle(directory)
    except (bundle.BundleError, KeyError, ValueError) as error:
        raise _science_error(503, ScienceErrorCode.INTEGRITY_FAILURE, f"Live bundle integrity failure: {error}")


@router.get("/status", response_model=LiveStatus)
def status() -> LiveStatus:
    cycles = [_summary(*_verified(kind, date)) for kind, date in bundle.list_bundles(ROOT)]
    live = next((c for c in cycles if c.kind == "live"), None)
    if live is None:
        message = "No experimental live cycle has been published yet. Only historical replays of stored cycles (a pipeline proof) are available." if cycles else "No experimental cycle has been published."
    else:
        message = f"Latest experimental live cycle: {live.cycle}" + (" (stale: it is older than the freshness limit and a newer cycle has not been published)" if live.stale else "")
    return LiveStatus(has_live_cycle=live is not None, latest_live=live, cycles=cycles, message=message, caveats=CAVEATS)


@router.get("/cycle", response_model=LiveCycle)
def cycle(kind: str = Query(...), date: str = Query(...)) -> LiveCycle:
    directory, manifest = _verified(kind, date)
    provenance = manifest["provenance"]
    stats: dict[str, dict[str, dict[str, float]]] = {}
    regimes: dict[str, dict[str, float]] = {}
    for product in manifest["products"]:
        regimes[product] = dict(zip(REGIME_NAMES, (float(x) for x in bundle.load_array(directory, f"regime_probability_{product}"))))
        stats[product] = {name: {k: manifest["arrays"][f"{name}_{product}"][k] for k in ("min", "max", "mean")} for name in FIELDS}
    return LiveCycle(summary=_summary(directory, manifest), manifest_sha256=bundle.sha256_file(directory / "manifest.json"), messages=len(provenance["sources"]),
                     transferred_bytes=sum(s["bytes"] for s in provenance["sources"]), frozen_models=provenance["frozen_models"], applicability=provenance.get("applicability"),
                     replay_comparison=manifest.get("replay_comparison"), regime_probabilities=regimes, domain_statistics=stats, fields=FIELDS, observation_read=manifest["observation_read"], caveats=CAVEATS)


@router.get("/field", response_model=LiveField)
def field(kind: str = Query(...), date: str = Query(...), product: str = Query(...), name: str = Query(..., alias="field")) -> LiveField:
    directory, manifest = _verified(kind, date)
    if product not in manifest["products"] or name not in FIELDS:
        raise _science_error(404, ScienceErrorCode.PRODUCT_UNAVAILABLE, f"Product {product} or field {name} is not in this bundle (a withheld lead is not served)")
    array = bundle.load_array(directory, f"{name}_{product}")
    probability = name.endswith("probability")
    values = np.round(array.astype(np.float64), 4 if probability else 2)
    return LiveField(kind=kind, cycle=date, product=product, field=name, label=FIELDS[name], evidence_label=manifest["label"], units="probability" if probability else "mm per 24 h",
                     latitude=[float(x) for x in np.linspace(10, 22, 49)], longitude=[float(x) for x in np.linspace(68, 80, 49)], values=values.tolist(), array_sha256=manifest["arrays"][f"{name}_{product}"]["sha256"])
