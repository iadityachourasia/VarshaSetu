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


# ------------------------------------------------------------------------------------------------------------------------------ follow-up (phase 11)
PHASE11 = Path(__file__).resolve().parents[1] / "evidence_data" / "phase11"
FOLLOWUP_FILES = ("geoaware_followup_protocol_v1", "geoaware_followup_protocol_v2", "geoaware_followup_protocol_v3", "geoaware_followup_selection_freeze",
                  "geoaware_followup_selection_freeze_v2", "geoaware_followup_selection_freeze_v3", "geoaware_followup_development_summary",
                  "geoaware_followup_unseal_record", "geoaware_followup_test_2022")
ZONE = "COASTAL_AND_OROGRAPHIC"
FOLLOWUP_CAVEATS = [
    "A single test year (2022) and a single training window of three development years.",
    "Both protocol changes (very-heavy frequency bias reported not gating, and selection aligned with the primary question) were made after earlier tables were seen; the sealed year was not used for any choice.",
    "Two candidate sets were scored on the same year, so the decision uses Bonferroni 97.5 percent intervals; the paired whole-case bootstrap is still optimistic.",
    "The secondary (v2) candidate set did not pass: the gain depends on how the candidate is selected, not on geography alone.",
    "The primary candidate raises the zone heavy-rain frequency bias above 1 (mild over-forecasting), which contributes to its higher CSI.",
    "Historical replay, not warning skill. The frozen M1 to M4 were not scored on 2022. IMD redistribution rights are unresolved.",
]


class GeoawareFollowup(BaseModel):
    protocol_v1_sha256: str
    protocol_v2_sha256: str
    protocol_v3_sha256: str
    freeze_v1_sha256: str
    freeze_v2_sha256: str
    freeze_v3_sha256: str
    summary_sha256: str
    unseal_record_sha256: str
    test_result_sha256: str
    sealed_test: dict[str, Any]
    unseal_record: dict[str, Any]
    approval: dict[str, Any]
    contamination_disclosure: str
    changes: list[dict[str, Any]]
    post_hoc_disclosure: dict[str, Any]
    decision_rule: dict[str, Any]
    development_years: list[int]
    v1_outcome: dict[str, Any]
    v2_selection: dict[str, Any]
    v3_selection: dict[str, Any]
    eligible_v2_by_arm: dict[str, int]
    raw_heavy_csi_by_year: dict[str, float]
    matched_configuration_comparison: dict[str, Any]
    test_2022: dict[str, Any]
    caveats: list[str]


@lru_cache(maxsize=1)
def _followup_chain() -> dict[str, Any]:
    """Verify the phase-11 hash chain once: every sidecar and every cross-reference, including the unseal record and the test result. Any mismatch is a 503."""
    docs: dict[str, dict] = {}
    shas: dict[str, str] = {}
    for stem in FOLLOWUP_FILES:
        path, side = PHASE11 / f"{stem}.json", PHASE11 / f"{stem}.sha256"
        if not path.is_file() or not side.is_file():
            raise _science_error(503, ScienceErrorCode.INTEGRITY_FAILURE, f"Follow-up evidence file is unavailable: {stem}")
        shas[stem] = sha256_file(path)
        if side.read_text(encoding="ascii").split()[0] != shas[stem]:
            raise _science_error(503, ScienceErrorCode.INTEGRITY_FAILURE, f"Follow-up evidence sidecar hash mismatch: {stem}")
        docs[stem] = json.loads(path.read_text(encoding="utf-8"))
    p1, p2, p3, f1, f2, f3, summary, record, result = (docs[s] for s in FOLLOWUP_FILES)
    listed = record["hashes"]
    tracked_listed = {"protocol_v1": "geoaware_followup_protocol_v1", "protocol_v2": "geoaware_followup_protocol_v2", "protocol_v3": "geoaware_followup_protocol_v3",
                      "selection_freeze_v1": "geoaware_followup_selection_freeze", "selection_freeze_v2": "geoaware_followup_selection_freeze_v2",
                      "selection_freeze_v3": "geoaware_followup_selection_freeze_v3", "development_summary": "geoaware_followup_development_summary"}
    consistent = (p2["supersedes"]["protocol_v1_sha256"] == shas["geoaware_followup_protocol_v1"] and p2["supersedes"]["v1_selection_freeze_sha256"] == shas["geoaware_followup_selection_freeze"]
                  and p3["supersedes"]["protocol_v2_sha256"] == shas["geoaware_followup_protocol_v2"] and p3["supersedes"]["v2_selection_freeze_sha256"] == shas["geoaware_followup_selection_freeze_v2"]
                  and f1["protocol_sha256"] == shas["geoaware_followup_protocol_v1"] and f2["protocol_sha256"] == shas["geoaware_followup_protocol_v2"]
                  and f3["protocol_sha256"] == shas["geoaware_followup_protocol_v3"] and f3["v2_selection_freeze_sha256"] == shas["geoaware_followup_selection_freeze_v2"]
                  and f2["supersedes_protocol_sha256"] == shas["geoaware_followup_protocol_v1"] and summary["protocol_sha256"] == shas["geoaware_followup_protocol_v1"]
                  and summary["selection_freeze_sha256"] == shas["geoaware_followup_selection_freeze"]
                  and p2["selection"]["cross_validation_reuse"]["checkpoint_sha256"] == summary["checkpoint_sha256"] == f2["cross_validation_checkpoint_sha256"] == f3["cross_validation_checkpoint_sha256"]
                  and all(listed[name]["sha256"] == shas[stem] for name, stem in tracked_listed.items())
                  and result["protocol_v3_sha256"] == shas["geoaware_followup_protocol_v3"] and result["unseal_record_sha256"] == shas["geoaware_followup_unseal_record"])
    if not consistent:
        raise _science_error(503, ScienceErrorCode.INTEGRITY_FAILURE, "Follow-up evidence hash chain is inconsistent")
    if f2["sealed_test"].get("opened") is not False or f3["sealed_test"].get("opened") is not False:
        raise _science_error(503, ScienceErrorCode.INTEGRITY_FAILURE, "A selection freeze does not record 2022 as sealed at freeze time")
    if record.get("written_before_any_2022_observation_value_was_read") is not True or not record["owner_message"]["verbatim"]:
        raise _science_error(503, ScienceErrorCode.INTEGRITY_FAILURE, "The unseal record does not carry the owner authorisation")
    if result["evidence_role"] != "INDEPENDENT_TEST_FIRST_USE_OF_2022" or result["label"] != "INDEPENDENT TEST: first use of this year" or result["year"] != 2022:
        raise _science_error(503, ScienceErrorCode.INTEGRITY_FAILURE, "The 2022 test result is not labelled as the first-use independent test")
    return {"docs": docs, "shas": shas}


def _select(model_metrics: dict, label: str) -> dict:
    z, a = model_metrics[label][ZONE], model_metrics[label]["ALL"]
    return {"rmse_mm": a["rmse_mm"], "bias_mm": a["bias_mm"], "heavy_csi": a["categorical"]["heavy"]["CSI"], "very_heavy_frequency_bias": a["categorical"]["very_heavy"]["frequency_bias"],
            "zone_heavy_csi": z["categorical"]["heavy"]["CSI"], "zone_heavy_frequency_bias": z["categorical"]["heavy"]["frequency_bias"], "zone_bias_mm": z["bias_mm"]}


def _selected_block(freeze: dict, years: tuple[str, ...]) -> dict:
    out = {}
    for arm, block in freeze["selection"].items():
        chosen = block["selected"]
        out[arm] = None if chosen is None else {
            "grid_index": chosen["grid_index"], "config": chosen["config"], "pooled_rmse_mm": chosen["pooled_out_of_fold"]["rmse_mm"], "features": chosen["features"],
            "g3_passes_in_every_year": chosen["g3_passes_in_every_year"],
            "by_year": {y: {"rmse_mm": chosen["by_year"][y]["rmse_mm"], "bias_mm": chosen["by_year"][y]["bias_mm"], "heavy_csi": chosen["by_year"][y]["heavy"]["csi"],
                            "zone_heavy_csi": chosen["by_year"][y]["zone"]["heavy_csi"], "zone_heavy_frequency_bias": chosen["by_year"][y]["zone"]["heavy_frequency_bias"],
                            "very_heavy_frequency_bias": chosen["by_year"][y]["very_heavy"]["frequency_bias"]} for y in years}}
    return out


@router.get("/followup", response_model=GeoawareFollowup)
def followup() -> GeoawareFollowup:
    chain = _followup_chain()
    d, s = chain["docs"], chain["shas"]
    p3, f1, f2, f3, summary, record, result = (d["geoaware_followup_protocol_v3"], d["geoaware_followup_selection_freeze"], d["geoaware_followup_selection_freeze_v2"],
                                               d["geoaware_followup_selection_freeze_v3"], d["geoaware_followup_development_summary"], d["geoaware_followup_unseal_record"],
                                               d["geoaware_followup_test_2022"])
    years = ("2021", "2023", "2024")
    counts = summary["b1_versus_b0_counts"]
    pooled = result["pooled"]
    shown = sorted({label for dec in result["decisions"].values() for label in (dec["candidate"], dec["comparator"])} | {"M0"})
    boot = result["bootstrap"]["decision_level_0975"]
    decisions = {}
    for key, dec in result["decisions"].items():
        decisions[key] = {k: dec.get(k) for k in ("candidate", "comparator", "status", "adds_value", "P1_zone_heavy_csi_beats_comparator_975", "P2_overall_rmse_within_tolerance",
                                                   "P3_gating_guardrails_G1_G2_G4", "guardrails", "g3_reported_only", "zone_heavy_csi_difference", "overall_rmse_difference", "level")}
    sensitivity = []
    for pair in result["sensitivity_pairs"]:
        entry = boot.get(f"diff|{ZONE}|{pair['a']}|{pair['b']}|heavy_csi")
        sensitivity.append({"a": pair["a"], "b": pair["b"], "zone_heavy_csi_difference": entry})
    by_lead = {lead: {"cases": block["cases"], "models": {label: {"rmse_mm": m["ALL"]["rmse_mm"], "zone_heavy_csi": m[ZONE]["categorical"]["heavy"]["CSI"]} for label, m in block["models"].items()}}
               for lead, block in result["by_lead"].items()}
    test = {"label": result["label"], "claim": result["claim"], "claim_wording": result["claim_wording"], "cases": result["cases"], "run_at_utc": result["run_at_utc"],
            "support_zone": result["support"][ZONE], "multiplicity": result["multiplicity"], "candidate_sets": result["candidate_sets"],
            "models": {label: result["models"][label] for label in result["models"] if label in shown}, "pooled_summary": {label: _select(pooled, label) for label in shown},
            "decisions": decisions, "sensitivity": sensitivity, "by_lead": by_lead, "limits": result["limits"]}
    return GeoawareFollowup(
        protocol_v1_sha256=s["geoaware_followup_protocol_v1"], protocol_v2_sha256=s["geoaware_followup_protocol_v2"], protocol_v3_sha256=s["geoaware_followup_protocol_v3"],
        freeze_v1_sha256=s["geoaware_followup_selection_freeze"], freeze_v2_sha256=s["geoaware_followup_selection_freeze_v2"], freeze_v3_sha256=s["geoaware_followup_selection_freeze_v3"],
        summary_sha256=s["geoaware_followup_development_summary"], unseal_record_sha256=s["geoaware_followup_unseal_record"], test_result_sha256=s["geoaware_followup_test_2022"],
        sealed_test={"year": 2022, "opened": True, "status": "OPENED_ONCE_UNDER_THE_UNSEAL_RECORD", "opened_at_utc": result["run_at_utc"],
                     "sealed_at_selection_freezes": f2["sealed_test"]["opened"] is False and f3["sealed_test"]["opened"] is False},
        unseal_record={"written_at_utc": record["written_at_utc"], "owner_message": record["owner_message"], "what_is_authorised": record["what_is_authorised"],
                       "what_is_not_authorised": record["what_is_not_authorised"], "disclosed_before_opening": record["disclosed_before_opening"], "hashes_listed": len(record["hashes"])},
        approval=p3["approval"], contamination_disclosure=p3["contamination_disclosure"], changes=p3["changes"], post_hoc_disclosure=p3["post_hoc_disclosure"], decision_rule=p3["decision_rule"],
        development_years=f2["development"]["years"],
        v1_outcome={"all_arms_without_candidate": all(b["selected"] is None for b in f1["selection"].values()), "arms": {a: b.get("reason") for a, b in f1["selection"].items()}},
        v2_selection=_selected_block(f2, years), v3_selection=_selected_block(f3, years),
        eligible_v2_by_arm={arm: sum(1 for r in f2["all_configurations"] if r["arm"] == arm and r["eligible_v2"]) for arm in f2["selection"]},
        raw_heavy_csi_by_year={k: float(v) for k, v in f2["development"]["raw_heavy_csi_by_year"].items()},
        matched_configuration_comparison={"configurations": counts["configurations"], "zone_heavy_csi_higher_in_every_held_out_year": counts["zone_heavy_csi_higher_in_every_held_out_year"],
                                          "pooled_rmse_lower": counts["pooled_rmse_lower"]},
        test_2022=test, caveats=FOLLOWUP_CAVEATS)
