"""Read-only, hash-verified regime/lead-stratified verification evidence (Phase 6, docs/108).

Serves the tracked files under backend/app/evidence_data/phase6/. It never trains, recalibrates, re-infers or
recomputes a metric: it only verifies the manifest + per-file SHA-256 and reshapes what was frozen.
Every payload carries the evidence role and its display label; a file whose role has no registered label
is refused, so a consumed holdout can never be shown without its post-hoc label.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Query
from fastapi.responses import Response
from pydantic import BaseModel

try:
    from backend.app.api.operational import ScienceErrorCode, _science_error
    from backend.app.ml.phase2b import sha256_file
except ModuleNotFoundError:
    from app.api.operational import ScienceErrorCode, _science_error
    from app.ml.phase2b import sha256_file

router = APIRouter(prefix="/science/evidence", tags=["Verification evidence (frozen, hash-verified)"])

# Lives inside the backend package (tracked, ~0.7 MB) so the Docker image (COPY backend/) ships it unchanged.
PHASE6 = Path(__file__).resolve().parents[1] / "evidence_data" / "phase6"
MODELS = ("M0", "M1", "M2", "M3", "M4")
THRESHOLDS = ("heavy", "very_heavy")
SCALES = ("1", "3", "5", "9")

# evidence_role (recorded inside each frozen file) -> mandatory display label
EVIDENCE_LABELS: dict[str, str] = {
    "TRACK_A_2018_VALIDATION_YEAR_DEVELOPMENT_EVIDENCE":
        "Track A 2018 validation year: development evidence (used for early stopping and model selection; not a holdout)",
    "TRACK_A_2019_CONSUMED_FINAL_TEST__POST_HOC_EXPLORATORY_ANALYSIS_OF_THE_COMPLETED_2019_FINAL_TEST":
        "POST-HOC EXPLORATORY ANALYSIS OF THE COMPLETED 2019 FINAL TEST",
    "PHASE4I_VALIDATION_SELECTION_YEAR_DEVELOPMENT_EVIDENCE":
        "Track B 2024 validation/selection year: development evidence (M1 was selected on it; not a holdout)",
    "PHASE4J_HOLDOUT_CONSUMED_POST_HOC_DESCRIPTIVE_ONLY":
        "POST-HOC EXPLORATORY ANALYSIS OF THE COMPLETED 2025 FINAL TEST",
    # western-disturbance indicator populations (docs/138): the 2022 year was consumed by the geography-aware follow-up test (docs/133)
    "INDEPENDENT_TEST_FIRST_USE_OF_2022": "INDEPENDENT TEST: first use of this year",
    "ALLINDIA_2023_TRAINING_YEAR_OF_THE_DOWNSTREAM_MODELS_RAW_ONLY": "2023: training year of the downstream models (this analysis fits nothing; Raw only)",
    "ALLINDIA_2024_DEVELOPMENT_YEAR_REUSED_FOR_MODEL_SELECTION": "2024 validation/selection year: development evidence",
    "ALLINDIA_2025_CONSUMED_FINAL_TEST__POST_HOC_EXPLORATORY_ANALYSIS_OF_THE_COMPLETED_2025_FINAL_TEST": "POST-HOC EXPLORATORY ANALYSIS OF THE COMPLETED 2025 FINAL TEST",
    "REFORECAST_CONFIRMATORY_TEST_2017_2019": "CONFIRMATORY TEST 2017-2019: no model of this study used these years (earlier Track A experiments did)",
    "REFORECAST_SEALED_TEST_2014_2016_FIRST_USE": "POST-UNSEAL SEALED TEST 2014-2016: first use of these years",
    "WD_2021_DEVELOPMENT_YEAR_NEVER_USED_FOR_ANY_SELECTION": "2021 development year: never used for any selection",
    "WD_2022_CONSUMED_FINAL_TEST__POST_HOC_EXPLORATORY_ANALYSIS_OF_THE_COMPLETED_2022_FINAL_TEST": "POST-HOC EXPLORATORY ANALYSIS OF THE COMPLETED 2022 FINAL TEST",
    "WD_2023_TRAINING_YEAR": "2023 training year (the indicator threshold is fitted here)",
    "WD_2024_DEVELOPMENT_YEAR_REUSED_FOR_MODEL_SELECTION": "2024 validation/selection year: development evidence (a reused year, not a holdout)",
    "WD_2025_CONSUMED_FINAL_TEST__POST_HOC_EXPLORATORY_ANALYSIS_OF_THE_COMPLETED_2025_FINAL_TEST": "POST-HOC EXPLORATORY ANALYSIS OF THE COMPLETED 2025 FINAL TEST",
}
CAVEATS = [
    "Descriptive re-aggregation of frozen predictions; no model was trained, tuned or selected for this view.",
    "Regimes are forecast-only pseudo-labels (argmax of the frozen classifier), not observed meteorological truth.",
    "Consumed holdouts (2019, 2025) are post-hoc descriptive analyses and must not be used to select, tune or re-rank a model.",
    "Bootstrap intervals resample whole cases and ignore serial correlation between consecutive days, so they are optimistic.",
    "FSS is undefined for a case when neither forecast nor observation has an event in an eligible neighborhood; "
    "each model is scored on its own defined cases and the undefined counts are reported.",
    "Track A (GEFSv12 reforecast) and Track B (operational GEFS) are different populations and are never pooled.",
]


class RegimeVerificationResponse(BaseModel):
    track: str
    year: int
    evidence_role: str
    evidence_label: str
    evidence_sha256: str
    regime_assignment: str
    reproduction: dict[str, Any]
    lineage_sha256: dict[str, Any]
    summary: dict[str, Any]
    overall: dict[str, Any]
    by_predicted_regime: dict[str, Any]
    by_lead_day: dict[str, Any]
    bootstrap: dict[str, Any]
    caveats: list[str]


class EvidenceManifestResponse(BaseModel):
    schema_id: str
    manifest_sha256: str
    files: dict[str, Any]
    notes: list[str]


@lru_cache(maxsize=1)
def _manifest() -> tuple[dict, str]:
    path, sidecar = PHASE6 / "evidence_manifest.json", PHASE6 / "evidence_manifest.sha256"
    if not path.is_file() or not sidecar.is_file():
        raise _science_error(503, ScienceErrorCode.INTEGRITY_FAILURE, "Phase 6 evidence manifest is unavailable")
    expected = sidecar.read_text(encoding="ascii").strip()
    if sha256_file(path) != expected:
        raise _science_error(503, ScienceErrorCode.INTEGRITY_FAILURE, "Phase 6 evidence manifest hash mismatch")
    return json.loads(path.read_text(encoding="utf-8")), expected


@lru_cache(maxsize=8)
def _evidence(name: str) -> tuple[dict, str]:
    manifest, _ = _manifest()
    entry = manifest["files"].get(name)
    path = PHASE6 / name
    if entry is None or not path.resolve().is_relative_to(PHASE6.resolve()) or not path.is_file():
        raise _science_error(404, ScienceErrorCode.PRODUCT_UNAVAILABLE, "No such evidence file")
    if sha256_file(path) != entry["sha256"]:
        raise _science_error(503, ScienceErrorCode.INTEGRITY_FAILURE, f"Phase 6 evidence integrity failure: {name}")
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("evidence_role") != entry["evidence_role"] or data["evidence_role"] not in EVIDENCE_LABELS:
        raise _science_error(503, ScienceErrorCode.INTEGRITY_FAILURE, f"Phase 6 evidence role is missing or unregistered: {name}")
    return data, entry["sha256"]


def _summary(data: dict) -> dict[str, Any]:
    """Population bookkeeping derived only from fields already in the frozen file."""
    overall = data["overall"]
    n = data["case_count"]
    defined = {t: {s: {m: overall["fss"][t][s]["all_cases"][m]["case_count"] for m in MODELS} for s in SCALES} for t in THRESHOLDS}
    return {
        "case_count": n,
        "cell_count": overall["cell_count"],
        "observed_event_cells": {t: overall["categorical"][t]["M0"]["observed_event_count"] for t in THRESHOLDS},
        "cases_by_regime": {k: v["case_count"] for k, v in data["by_predicted_regime"].items()},
        "cases_by_lead_day": {k: v["case_count"] for k, v in data["by_lead_day"].items()},
        "defined_fss_cases": defined,
        "undefined_fss_cases": {t: {s: {m: n - defined[t][s][m] for m in MODELS} for s in SCALES} for t in THRESHOLDS},
    }


@router.get("/manifest", response_model=EvidenceManifestResponse)
def evidence_manifest() -> EvidenceManifestResponse:
    manifest, digest = _manifest()
    return EvidenceManifestResponse(schema_id=manifest["schema"], manifest_sha256=digest, files=manifest["files"], notes=manifest["notes"])


@router.get("/regime-verification", response_model=RegimeVerificationResponse)
def regime_verification(track: str = Query(..., pattern="^[AB]$"), year: int = Query(...)) -> RegimeVerificationResponse:
    name = f"regime_verification_{track}_{year}.json"
    manifest, _ = _manifest()
    if name not in manifest["files"]:
        available = sorted(f"{e['track']}/{e['year']}" for e in manifest["files"].values())
        raise _science_error(404, ScienceErrorCode.PRODUCT_UNAVAILABLE,
                             f"No regime-verification evidence for track {track} year {year}. Available: {', '.join(available)}")
    data, digest = _evidence(name)
    return RegimeVerificationResponse(
        track=track, year=year, evidence_role=data["evidence_role"], evidence_label=EVIDENCE_LABELS[data["evidence_role"]],
        evidence_sha256=digest, regime_assignment=data["regime_assignment"],
        reproduction={k: v for k, v in data["reproduction"].items() if k != "checks"},
        lineage_sha256=data["lineage_sha256"], summary=_summary(data), overall=data["overall"],
        by_predicted_regime=data["by_predicted_regime"], by_lead_day=data["by_lead_day"], bootstrap=data["bootstrap"],
        caveats=CAVEATS)


# ---------------------------------------------------------------------------------------------
# Verification report export (PS expected output: verification report) -- generated ONLY from the
# hash-verified evidence file, never recomputed, so it cannot drift from what the tables show.
# ---------------------------------------------------------------------------------------------

METRIC_NAMES = {"rmse_mm": "RMSE (mm)", "mae_mm": "MAE (mm)", "bias_mm": "Bias (mm)"}
EVENT_METRICS = ("POD", "FAR", "CSI", "ETS")
MODEL_NAMES = {"M0": "M0 Raw GEFS", "M1": "M1 Ridge MOS", "M2": "M2 Global ML", "M3": "M3 Hard regime", "M4": "M4 Soft regime"}
PAIR_NAMES = {"M3_minus_M0": "M3 - Raw", "M3_minus_M2": "M3 - M2", "M4_minus_M0": "M4 - Raw", "M4_minus_M2": "M4 - M2",
              "M2_minus_M0": "M2 - Raw", "M3_minus_M4": "M3 - M4"}
THRESHOLD_NAMES = {"heavy": "Heavy >= 64.5 mm/24h", "very_heavy": "Very heavy >= 115.6 mm/24h"}


def _groups(data: dict) -> list[tuple[str, str, dict]]:
    groups = [("overall", "all cases", data["overall"])]
    groups += [("regime", name, block) for name, block in data["by_predicted_regime"].items()]
    groups += [("lead", name, block) for name, block in data["by_lead_day"].items()]
    return groups


def report_rows(data: dict) -> list[dict[str, Any]]:
    """Long-format rows: one per (group, model, threshold, metric, scale). Undefined values stay None."""
    rows: list[dict[str, Any]] = []
    for group_type, group, block in _groups(data):
        base = {"group_type": group_type, "group": group, "case_count": block["case_count"]}
        for model in MODELS:
            for key, label in METRIC_NAMES.items():
                rows.append({**base, "model": model, "threshold": "", "metric": label, "scale": "",
                             "value": block["continuous"][model][key], "defined_cases": block["case_count"]})
            for threshold in THRESHOLDS:
                event = block["categorical"][threshold][model]
                for metric in EVENT_METRICS:
                    rows.append({**base, "model": model, "threshold": threshold, "metric": metric, "scale": "",
                                 "value": event[metric], "defined_cases": block["case_count"]})
                for count in ("hits", "misses", "false_alarms", "observed_event_count", "forecast_event_count"):
                    rows.append({**base, "model": model, "threshold": threshold, "metric": count, "scale": "",
                                 "value": event[count], "defined_cases": block["case_count"]})
                for scale in SCALES:
                    score = block["fss"][threshold][scale]["all_cases"][model]
                    rows.append({**base, "model": model, "threshold": threshold, "metric": "FSS", "scale": f"{scale}x{scale}",
                                 "value": score["fss"], "defined_cases": score["case_count"]})
    return rows


def _num(value: Any, digits: int = 4) -> str:
    if value is None:
        return "undefined"
    return str(value) if isinstance(value, int) else f"{value:.{digits}f}"


def report_csv(data: dict, meta: dict[str, Any]) -> str:
    import csv
    import io

    buffer = io.StringIO()
    columns = ["track", "year", "evidence_role", "group_type", "group", "case_count", "model", "threshold", "metric", "scale",
               "value", "defined_cases", "note"]
    writer = csv.DictWriter(buffer, fieldnames=columns, lineterminator="\n")
    writer.writeheader()
    for row in report_rows(data):
        writer.writerow({"track": meta["track"], "year": meta["year"], "evidence_role": meta["evidence_role"], **row,
                         "value": "" if row["value"] is None else row["value"],
                         "note": "undefined: no defined events or no forecast events" if row["value"] is None else ""})
    return buffer.getvalue()


def _block_table(block: dict) -> list[str]:
    head = "| Metric | " + " | ".join(MODEL_NAMES[m] for m in MODELS) + " |"
    lines = [head, "|---|" + "---|" * len(MODELS)]
    for key, label in METRIC_NAMES.items():
        lines.append(f"| {label} | " + " | ".join(_num(block["continuous"][m][key], 3) for m in MODELS) + " |")
    for threshold in THRESHOLDS:
        for metric in EVENT_METRICS:
            lines.append(f"| {THRESHOLD_NAMES[threshold]} - {metric} | " + " | ".join(_num(block["categorical"][threshold][m][metric]) for m in MODELS) + " |")
        for scale in SCALES:
            cells = []
            for m in MODELS:
                score = block["fss"][threshold][scale]["all_cases"][m]
                cells.append(f"{_num(score['fss'])} (n={score['case_count']})")
            lines.append(f"| {THRESHOLD_NAMES[threshold]} - FSS {scale}x{scale} | " + " | ".join(cells) + " |")
        lines.append(f"| {THRESHOLD_NAMES[threshold]} - observed / forecast event cells | " + " | ".join(
            f"{block['categorical'][threshold][m]['observed_event_count']} / {block['categorical'][threshold][m]['forecast_event_count']}" for m in MODELS) + " |")
    return lines


def _interval_text(stat: dict) -> str:
    if stat.get("status") != "ok":
        return f"not reported ({stat.get('status')})"
    low, high = stat["interval95"]
    return f"{stat['point']:+.4f} [{low:.4f}, {high:.4f}] {'excludes 0' if low > 0 or high < 0 else 'includes 0'}"


def report_markdown(data: dict, meta: dict[str, Any]) -> str:
    summary = meta["summary"]
    out = [
        f"# VarshaSetu verification report - Track {meta['track']} {meta['year']}",
        "",
        f"**{meta['evidence_label']}**",
        "",
        "Historical scientific prototype - not an operational forecast. Regime-aware verification of frozen models against IMD rainfall.",
        "",
        "## Provenance",
        f"- Evidence file SHA-256: `{meta['evidence_sha256']}`",
        f"- Reproduction of the frozen numbers: {meta['reproduction'].get('status')} ({meta['reproduction'].get('check_count')} checks, max abs difference {meta['reproduction'].get('max_abs_diff'):.2e})",
        f"- Population: {summary['case_count']} cases, {summary['cell_count']:,} paired cells; observed event cells heavy {summary['observed_event_cells']['heavy']}, very heavy {summary['observed_event_cells']['very_heavy']}",
        f"- Regime assignment: {data['regime_assignment']}",
        "- Metrics covered: RMSE, MAE, bias, POD, FAR, CSI, ETS, FSS (1x1, 3x3, 5x5, 9x9) at 64.5 and 115.6 mm per 24 h.",
        "- Every value below is read from the hash-verified evidence file; nothing was recomputed, tuned or selected for this report.",
        "",
        "## Overall",
        *_block_table(data["overall"]),
    ]
    for name, block in data["by_predicted_regime"].items():
        out += ["", f"## Forecast-only regime: {name} ({block['case_count']} cases)", *_block_table(block)]
    for name, block in data["by_lead_day"].items():
        out += ["", f"## Lead: {name.replace('day', 'Day ')} ({block['case_count']} cases)", *_block_table(block)]
    out += ["", "## Paired differences over all cases (case-cluster bootstrap, 95 % percentile interval)"]
    for threshold in THRESHOLDS:
        out += ["", f"### {THRESHOLD_NAMES[threshold]}", "| Contrast | Delta CSI | Delta FSS 3x3 | Delta FSS 9x9 |", "|---|---|---|---|"]
        for pair, label in PAIR_NAMES.items():
            cell = data["bootstrap"]["overall"][threshold][pair]
            out.append(f"| {label} | {_interval_text(cell['CSI'])} | {_interval_text(cell['FSS_3x3'])} | {_interval_text(cell['FSS_9x9'])} |")
    out += ["", "## Limitations", *[f"- {c}" for c in CAVEATS], ""]
    return "\n".join(out)


@router.get("/report")
def verification_report(track: str = Query(..., pattern="^[AB]$"), year: int = Query(...),
                        format: str = Query("md", pattern="^(md|csv|json)$")) -> Response:
    name = f"regime_verification_{track}_{year}.json"
    manifest, _ = _manifest()
    if name not in manifest["files"]:
        raise _science_error(404, ScienceErrorCode.PRODUCT_UNAVAILABLE, f"No verification report for track {track} year {year}")
    data, digest = _evidence(name)
    meta = {"track": track, "year": year, "evidence_role": data["evidence_role"], "evidence_label": EVIDENCE_LABELS[data["evidence_role"]],
            "evidence_sha256": digest, "reproduction": {k: v for k, v in data["reproduction"].items() if k != "checks"},
            "summary": _summary(data)}
    filename = f"varshasetu_verification_{track}_{year}.{format}"
    headers = {"Content-Disposition": f'attachment; filename="{filename}"', "X-Evidence-SHA256": digest}
    if format == "csv":
        return Response(report_csv(data, meta), media_type="text/csv; charset=utf-8", headers=headers)
    if format == "json":
        body = {"schema": "varshasetu-verification-report-v1", **meta, "regime_assignment": data["regime_assignment"],
                "rows": report_rows(data), "bootstrap": data["bootstrap"], "caveats": CAVEATS}
        return Response(json.dumps(body, ensure_ascii=False, allow_nan=False, indent=2), media_type="application/json", headers=headers)
    return Response(report_markdown(data, meta), media_type="text/markdown; charset=utf-8", headers=headers)


# ---------------------------------------------------------------------------------------------
# District-level verification evidence (protocol v1, docs/112)
# ---------------------------------------------------------------------------------------------

DISTRICT_CAVEATS = [
    "Defined by the frozen district verification protocol (Track B protocol v1, docs/112; Track A protocol A v1, docs/135, which carries every definition over unchanged): unit = district-case pair; events E1 any cell, E2 >= 25 % of valid area, E3 district mean; "
    "districts need >= 5 valid IMD land cells; per-district scores need >= 30 observed events (otherwise 'insufficient support').",
    "A district is 'improved' or 'worsened' only if its mean improvement over Raw and the 95 % paired whole-case bootstrap interval agree; with about 170 districts tested, "
    "about 5 % in total (about 2.5 % per direction) are expected to be classified improved or worsened by chance alone.",
    "Bootstrap intervals resample whole cases but ignore serial correlation between consecutive days and the spatial correlation of neighbouring districts, so they are optimistic.",
    "IMD land cells only: coastal and border districts are covered by few cells; district geometry is simplified; this is district-aggregate verification of historical replay, not warning skill.",
    "Regimes are forecast-only pseudo-labels (argmax of the frozen classifier), not observed meteorological truth.",
    "Consumed holdouts (2019 and 2025) are post-hoc descriptive analyses and must not be used to select, tune or re-rank a model. Track A and Track B are never pooled.",
]


class DistrictVerificationResponse(BaseModel):
    track: str
    year: int
    evidence_role: str
    evidence_label: str
    evidence_sha256: str
    protocol_sha256: str
    protocol_status: str
    protocol_decisions: dict[str, Any]
    regime_assignment: str
    reproduction: dict[str, Any]
    inclusion: dict[str, Any]
    continuous: dict[str, Any]
    categorical: dict[str, Any]
    contrasts: dict[str, Any]
    improved_worsened: dict[str, Any]
    supported_district_counts: dict[str, Any]
    observed_events_pooled: dict[str, Any]
    districts: list[dict[str, Any]]
    bootstrap: dict[str, Any]
    caveats: list[str]


DISTRICT_TRACK_OF_YEAR = {2018: "A", 2019: "A", 2024: "B", 2025: "B"}
DISTRICT_FILES = {"B": {"manifest": "district_verification_manifest", "protocol": "district_verification_protocol_v1.json"},
                  "A": {"manifest": "district_verification_manifest_A", "protocol": "district_verification_protocol_A_v1.json"}}


@lru_cache(maxsize=2)
def _district_manifest(track: str = "B") -> tuple[dict, str]:
    names = DISTRICT_FILES[track]
    path, sidecar = PHASE6 / f"{names['manifest']}.json", PHASE6 / f"{names['manifest']}.sha256"
    if not path.is_file() or not sidecar.is_file():
        raise _science_error(503, ScienceErrorCode.INTEGRITY_FAILURE, "District verification manifest is unavailable")
    expected = sidecar.read_text(encoding="ascii").strip()
    if sha256_file(path) != expected:
        raise _science_error(503, ScienceErrorCode.INTEGRITY_FAILURE, "District verification manifest hash mismatch")
    manifest = json.loads(path.read_text(encoding="utf-8"))
    protocol = PHASE6 / names["protocol"]
    if not protocol.is_file() or sha256_file(protocol) != manifest["protocol_sha256"]:
        raise _science_error(503, ScienceErrorCode.INTEGRITY_FAILURE, "District verification protocol hash mismatch")
    return manifest, expected


@lru_cache(maxsize=4)
def _district_evidence(year: int) -> tuple[dict, str]:
    track = DISTRICT_TRACK_OF_YEAR.get(year)
    if track is None:
        raise _science_error(404, ScienceErrorCode.PRODUCT_UNAVAILABLE,
                             f"No district verification for {year}. Available: {', '.join(str(y) for y in sorted(DISTRICT_TRACK_OF_YEAR))}")
    manifest, _ = _district_manifest(track)
    name = f"district_verification_{track}_{year}.json"
    entry = manifest["files"].get(name)
    path = PHASE6 / name
    if entry is None or not path.is_file():
        raise _science_error(404, ScienceErrorCode.PRODUCT_UNAVAILABLE, f"No district verification for Track {track} {year}")
    if sha256_file(path) != entry["sha256"]:
        raise _science_error(503, ScienceErrorCode.INTEGRITY_FAILURE, f"District verification integrity failure: {name}")
    data = json.loads(path.read_text(encoding="utf-8"))
    if (data.get("evidence_role") != entry["evidence_role"] or data["evidence_role"] not in EVIDENCE_LABELS or data.get("protocol_sha256") != manifest["protocol_sha256"]
            or data.get("track") != track):
        raise _science_error(503, ScienceErrorCode.INTEGRITY_FAILURE, f"District verification role, track or protocol mismatch: {name}")
    return data, entry["sha256"]


def _protocol(track: str = "B") -> dict:
    return json.loads((PHASE6 / DISTRICT_FILES[track]["protocol"]).read_text(encoding="utf-8"))


@router.get("/district-verification", response_model=DistrictVerificationResponse)
def district_verification(year: int = Query(...)) -> DistrictVerificationResponse:
    data, digest = _district_evidence(year)
    protocol = _protocol(data["track"])
    return DistrictVerificationResponse(
        track=data["track"], year=year, evidence_role=data["evidence_role"], evidence_label=EVIDENCE_LABELS[data["evidence_role"]], evidence_sha256=digest,
        protocol_sha256=data["protocol_sha256"], protocol_status=protocol["status"], protocol_decisions=protocol["approval"]["decisions"],
        regime_assignment=data["regime_assignment"], reproduction={k: v for k, v in data["reproduction"].items() if k != "checks"},
        inclusion=data["inclusion"], continuous=data["continuous"], categorical=data["categorical"], contrasts=data["contrasts"],
        improved_worsened=data["improved_worsened"], supported_district_counts=data["supported_district_counts"],
        observed_events_pooled=data["observed_events_pooled"], districts=data["districts"], bootstrap=data["bootstrap"], caveats=DISTRICT_CAVEATS)


_DEF_NAMES = {"E1": "E1 any valid cell >= threshold (primary)", "E2": "E2 >= 25 % of valid area >= threshold (secondary)", "E3": "E3 district mean >= threshold (sensitivity)"}


def district_report_markdown(data: dict, meta: dict[str, Any]) -> str:
    inc = data["inclusion"]
    out = [f"# VarshaSetu district-level verification report - Track {meta['track']} {meta['year']}", "", f"**{meta['evidence_label']}**", "",
           "Historical scientific prototype - not an operational forecast. District-aggregate verification of frozen models against IMD rainfall.", "",
           "## Provenance",
           f"- Evidence file SHA-256: `{meta['evidence_sha256']}`", f"- Protocol SHA-256: `{data['protocol_sha256']}` (approved and frozen before any result; docs/112 for Track B, docs/135 for Track A)",
           f"- Reproduction gate: {data['reproduction']['status']} ({data['reproduction']['check_count']} checks)",
           f"- Population: {inc['cases']} cases, {inc['districts_included']} of {inc['districts_total']} districts included, {inc['district_case_pairs']:,} district-case pairs (>= {inc['min_valid_cells']} valid cells)",
           f"- Regime assignment: {data['regime_assignment']}", "",
           "## Pooled district-mean error (mm/24h)", "| Model | RMSE | MAE | Bias (model - IMD) | Pairs |", "|---|---|---|---|---|"]
    for m in MODELS:
        c = data["continuous"]["pooled"]["all"][m]
        out.append(f"| {MODEL_NAMES[m]} | {_num(c['rmse_mm'], 3)} | {_num(c['mae_mm'], 3)} | {_num(c['bias_mm'], 3)} | {c['pairs']} |")
    for definition in ("E1", "E2", "E3"):
        for threshold in THRESHOLDS:
            out += ["", f"## Pooled district events - {_DEF_NAMES[definition]} - {THRESHOLD_NAMES[threshold]}",
                    "| Model | POD | FAR | CSI | ETS | Observed events | Forecast events |", "|---|---|---|---|---|---|---|"]
            for m in MODELS:
                e = data["categorical"][definition][threshold]["pooled"]["all"][m]
                out.append(f"| {MODEL_NAMES[m]} | {_num(e['POD'])} | {_num(e['FAR'])} | {_num(e['CSI'])} | {_num(e['ETS'])} | {e['observed_event_count']} | {e['forecast_event_count']} |")
    for kind, title in (("by_lead", "lead day"), ("by_regime", "forecast-only pseudo-regime"), ("by_region", "latitude band")):
        out += ["", f"## E1 heavy CSI by {title}", "| Group | " + " | ".join(MODEL_NAMES[m] for m in MODELS) + " |", "|---|" + "---|" * len(MODELS)]
        for name, block in data["categorical"]["E1"]["heavy"][kind].items():
            out.append(f"| {name} | " + " | ".join(_num(block[m]["CSI"]) for m in MODELS) + " |")
    out += ["", "## Paired contrasts (case-cluster bootstrap, 95 % percentile interval)", "### E1 heavy CSI", "| Contrast | Delta CSI |", "|---|---|"]
    for key, cell in data["contrasts"]["categorical"]["E1"]["heavy"].items():
        a, b = key.split("_minus_")
        out.append(f"| {MODEL_NAMES[a]} - {MODEL_NAMES[b]} | {_interval_text(cell['CSI'])} |")
    out += ["", "### District-mean absolute error: mean of (|err of second| - |err of first|) mm; positive = first is closer to IMD", "| Contrast | Mean improvement (mm) |", "|---|---|"]
    for key, cell in data["contrasts"]["continuous"].items():
        a, b = key.split("_vs_")
        out.append(f"| {MODEL_NAMES[a]} vs {MODEL_NAMES[b]} | {_interval_text(cell)} |")
    out += ["", "## Districts improved / worsened versus Raw (per-district mean improvement with 95 % interval)",
            "| Model | Tested | Improved | Worsened | Indeterminate | Expected by chance (total / per direction) |", "|---|---|---|---|---|---|"]
    for m, v in data["improved_worsened"].items():
        out.append(f"| {MODEL_NAMES[m.upper()] if m.upper() in MODEL_NAMES else m} | {v['tested_districts']} | {v['improved']} | {v['worsened']} | {v['indeterminate']} | {v['expected_by_chance_total']} / {v['expected_by_chance_per_direction']} |")
    out += ["", "## Districts with per-district event scores", "- " + "; ".join(
        f"{d} {t}: {n} supported districts" for d, v in data["supported_district_counts"].items() for t, n in v.items()),
            "", "## Limitations", *[f"- {c}" for c in DISTRICT_CAVEATS], ""]
    return "\n".join(out)


def district_report_rows(data: dict) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for e in data["districts"]:
        base = {"district_id": e["district_id"], "district_name": e["district_name"], "region": e["region"], "included_cases": e["included_cases"]}
        if e["continuous"] != "insufficient_support":
            for m in MODELS:
                for key in ("rmse_mm", "mae_mm", "bias_mm"):
                    rows.append({**base, "model": m, "kind": "continuous", "definition": "", "threshold": "", "metric": key, "value": e["continuous"][m][key], "note": ""})
        if e["improvement"] != "insufficient_support":
            for m, v in e["improvement"].items():
                rows.append({**base, "model": m.upper() if m.upper() in MODELS else m, "kind": "improvement", "definition": "", "threshold": "", "metric": "mean_improvement_mm",
                             "value": v["mean_improvement_mm"], "note": f"{v['status']}; 95% interval [{v['interval95'][0]:.4f}, {v['interval95'][1]:.4f}]"})
        for definition, thresholds in e["categorical"].items():
            for threshold, cell in thresholds.items():
                if cell["status"] != "supported":
                    rows.append({**base, "model": "", "kind": "categorical", "definition": definition, "threshold": threshold, "metric": "observed_events",
                                 "value": cell["observed_events"], "note": "insufficient_support"})
                    continue
                for m, ev in cell["models"].items():
                    for metric in ("POD", "FAR", "CSI", "ETS", "hits", "misses", "false_alarms"):
                        rows.append({**base, "model": m, "kind": "categorical", "definition": definition, "threshold": threshold, "metric": metric,
                                     "value": ev[metric], "note": "undefined" if ev[metric] is None else ""})
    return rows


@router.get("/district-verification/report")
def district_verification_report(year: int = Query(...), format: str = Query("md", pattern="^(md|csv|json)$")) -> Response:
    data, digest = _district_evidence(year)
    meta = {"track": data["track"], "year": year, "evidence_label": EVIDENCE_LABELS[data["evidence_role"]], "evidence_sha256": digest}
    headers = {"Content-Disposition": f'attachment; filename="varshasetu_district_verification_{data["track"]}_{year}.{format}"', "X-Evidence-SHA256": digest}
    if format == "csv":
        import csv
        import io

        buffer = io.StringIO()
        writer = csv.DictWriter(buffer, fieldnames=["year", "evidence_role", "district_id", "district_name", "region", "included_cases", "model", "kind", "definition",
                                                    "threshold", "metric", "value", "note"], lineterminator="\n")
        writer.writeheader()
        for row in district_report_rows(data):
            writer.writerow({"year": year, "evidence_role": data["evidence_role"], **row, "value": "" if row["value"] is None else row["value"]})
        return Response(buffer.getvalue(), media_type="text/csv; charset=utf-8", headers=headers)
    if format == "json":
        body = {"schema": "varshasetu-district-verification-report-v1", **meta, "protocol_sha256": data["protocol_sha256"], "rows": district_report_rows(data),
                "inclusion": data["inclusion"], "continuous": data["continuous"], "improved_worsened": data["improved_worsened"], "caveats": DISTRICT_CAVEATS}
        return Response(json.dumps(body, ensure_ascii=False, allow_nan=False, indent=2), media_type="application/json", headers=headers)
    return Response(district_report_markdown(data, meta), media_type="text/markdown; charset=utf-8", headers=headers)


# ---------------------------------------------------------------------------------------------
# SIH26080 requirement coverage (P0-6): a machine-readable manifest whose figures are resolved from evidence
# ---------------------------------------------------------------------------------------------

COVERAGE_STATUSES = ("IMPLEMENTED", "PARTIAL", "PLANNED")
COVERAGE_FILE = PHASE6 / "ps_coverage.json"


class PsFact(BaseModel):
    label: str
    value: float | int
    format: str
    source: str
    source_sha256: str
    evidence_label: str


class PsCoverageRow(BaseModel):
    id: str
    group: str
    requirement: str
    ps_ids: list[str]
    ps_mandatory: bool
    status: str
    summary: str
    limitation: str
    pages: list[dict[str, str]]
    docs: list[str]
    facts: list[PsFact]


class PsCoverageResponse(BaseModel):
    schema_id: str
    title: str
    rules: list[str]
    status_vocabulary: list[str]
    counts: dict[str, int]
    mandatory_counts: dict[str, int]
    coverage_sha256: str
    rows: list[PsCoverageRow]


def _resolve_fact(fact: dict) -> PsFact:
    kind, *rest = fact["source"].split(":")
    if kind == "regime" and len(rest) == 2 and rest[0] in ("A", "B"):
        data, digest = _evidence(f"regime_verification_{rest[0]}_{rest[1]}.json")
    elif kind == "district" and rest[:1] in (["A"], ["B"]) and len(rest) == 2 and DISTRICT_TRACK_OF_YEAR.get(int(rest[1])) == rest[0]:
        data, digest = _district_evidence(int(rest[1]))
    elif kind == "coastalregime" and len(rest) == 2 and rest[0] in ("A", "B"):
        try:
            from backend.app.api import coastal_regime
        except ModuleNotFoundError:
            from app.api import coastal_regime
        if coastal_regime.TRACK_OF_YEAR.get(int(rest[1])) != rest[0]:
            raise _science_error(503, ScienceErrorCode.INTEGRITY_FAILURE, f"Coverage fact has an unknown source: {fact['source']}")
        data, digest = coastal_regime._result(int(rest[1]))
    elif kind == "geofollow" and rest == ["2022"]:
        try:
            from backend.app.api import geoaware
        except ModuleNotFoundError:
            from app.api import geoaware
        chain = geoaware._followup_chain()
        data, digest = chain["docs"]["geoaware_followup_test_2022"], chain["shas"]["geoaware_followup_test_2022"]
    elif kind == "reforecast" and rest in (["r05"], ["r03"], ["r05c"]):
        try:
            from backend.app.api import reforecast
        except ModuleNotFoundError:
            from app.api import reforecast
        data, digest = reforecast._confirmation_result() if rest[0] == "r05c" else reforecast._result(f"reforecast_{rest[0]}_test.json")
    elif kind == "allindia" and len(rest) == 1 and rest[0].isdigit():
        try:
            from backend.app.api import all_india_raw
        except ModuleNotFoundError:
            from app.api import all_india_raw
        if int(rest[0]) not in all_india_raw.YEARS:
            raise _science_error(503, ScienceErrorCode.INTEGRITY_FAILURE, f"Coverage fact has an unknown source: {fact['source']}")
        data, digest = all_india_raw._result(int(rest[0]))
    elif kind == "wdindicator" and len(rest) == 1 and rest[0].isdigit():
        try:
            from backend.app.api import wd_indicator
        except ModuleNotFoundError:
            from app.api import wd_indicator
        if int(rest[0]) not in wd_indicator.YEARS:
            raise _science_error(503, ScienceErrorCode.INTEGRITY_FAILURE, f"Coverage fact has an unknown source: {fact['source']}")
        data, digest = wd_indicator._result(int(rest[0]))
    elif kind == "regimeval" and len(rest) == 2 and rest[0] in ("A", "B"):
        try:
            from backend.app.api import regime_validation
        except ModuleNotFoundError:
            from app.api import regime_validation
        if regime_validation.TRACK_OF_YEAR.get(int(rest[1])) != rest[0]:
            raise _science_error(503, ScienceErrorCode.INTEGRITY_FAILURE, f"Coverage fact has an unknown source: {fact['source']}")
        data, digest = regime_validation._result(int(rest[1]))
    elif kind in ("zone", "zoneforcing") and len(rest) == 2 and rest[0] in ("A", "B"):
        try:
            from backend.app.api import zones
        except ModuleNotFoundError:
            from app.api import zones
        stage, prefix = ("stage1", "zone_verification") if kind == "zone" else ("stage2", "zone_stage2")
        data, digest = zones._evidence(stage, f"{prefix}_{rest[0]}_{rest[1]}.json")
    else:
        raise _science_error(503, ScienceErrorCode.INTEGRITY_FAILURE, f"Coverage fact has an unknown source: {fact['source']}")
    node: Any = data
    for part in fact["pointer"].strip("/").split("/"):
        if isinstance(node, dict) and part in node:
            node = node[part]
        elif isinstance(node, list) and part.isdigit() and int(part) < len(node):
            node = node[int(part)]
        else:
            raise _science_error(503, ScienceErrorCode.INTEGRITY_FAILURE, f"Coverage fact pointer does not resolve: {fact['source']} {fact['pointer']}")
    if isinstance(node, bool) or not isinstance(node, (int, float)):
        raise _science_error(503, ScienceErrorCode.INTEGRITY_FAILURE, f"Coverage fact is not a defined number: {fact['source']} {fact['pointer']}")
    return PsFact(label=fact["label"], value=node, format=fact["format"], source=fact["source"], source_sha256=digest,
                  evidence_label=EVIDENCE_LABELS[data["evidence_role"]])


@lru_cache(maxsize=1)
def _coverage() -> PsCoverageResponse:
    if not COVERAGE_FILE.is_file():
        raise _science_error(503, ScienceErrorCode.INTEGRITY_FAILURE, "SIH26080 coverage manifest is unavailable")
    raw = json.loads(COVERAGE_FILE.read_text(encoding="utf-8"))
    ids = [row["id"] for row in raw["rows"]]
    if len(ids) != len(set(ids)) or list(raw["status_vocabulary"]) != list(COVERAGE_STATUSES):
        raise _science_error(503, ScienceErrorCode.INTEGRITY_FAILURE, "SIH26080 coverage manifest is malformed")
    rows = []
    for row in raw["rows"]:
        if row["status"] not in COVERAGE_STATUSES or (row["status"] == "PLANNED" and row["facts"]):
            raise _science_error(503, ScienceErrorCode.INTEGRITY_FAILURE, f"SIH26080 coverage row is inconsistent: {row['id']}")
        rows.append(PsCoverageRow(**{**row, "facts": [_resolve_fact(f) for f in row["facts"]]}))
    counts = {s: sum(1 for r in rows if r.status == s) for s in COVERAGE_STATUSES}
    mandatory = {s: sum(1 for r in rows if r.status == s and r.ps_mandatory) for s in COVERAGE_STATUSES}
    return PsCoverageResponse(schema_id=raw["schema"], title=raw["title"], rules=raw["rules"], status_vocabulary=list(COVERAGE_STATUSES),
                              counts=counts, mandatory_counts=mandatory, coverage_sha256=sha256_file(COVERAGE_FILE), rows=rows)


@router.get("/ps-coverage", response_model=PsCoverageResponse)
def ps_coverage() -> PsCoverageResponse:
    return _coverage()
