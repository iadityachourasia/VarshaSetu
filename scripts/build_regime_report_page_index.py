"""Local-only bibliographic page finder for the frozen blind regime packet.

An exact date string on a report page is only a review lead, never a regime
label, a dated operational bulletin, or evidence that a system was in-domain.
"""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STORE = ROOT / "data/manifests/research_pilot"
PACKET = STORE / "expert_regime_review_packet_v1.json"
REPORTS = STORE / "regime_support_docs_v1.json"
PROTOCOL = STORE / "rsmc_regime_page_index_protocol_v1.json"
RESULT = STORE / "rsmc_regime_page_index_result_v1.json"
MONTHS = {
    6: ("June", "Jun"),
    7: ("July", "Jul"),
    8: ("August", "Aug"),
    9: ("September", "Sept", "Sep"),
    10: ("October", "Oct"),
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _json_bytes(value: dict) -> bytes:
    return (json.dumps(value, sort_keys=True, indent=2, ensure_ascii=False) + "\n").encode("utf-8")


def _receipt(path: Path) -> Path:
    return path.with_suffix(".sha256")


def _write_once(path: Path, value: dict) -> str:
    sidecar = _receipt(path)
    if path.exists() or sidecar.exists():
        raise RuntimeError(f"write-once artifact already exists: {path}")
    payload = _json_bytes(value)
    digest = hashlib.sha256(payload).hexdigest()
    path.write_bytes(payload)
    sidecar.write_text(f"{digest}  {path.name}\n", encoding="utf-8")
    return digest


def _verified_json(path: Path) -> dict:
    sidecar = _receipt(path)
    if not path.is_file() or not sidecar.is_file():
        raise RuntimeError(f"missing JSON or checksum: {path}")
    expected = sidecar.read_text(encoding="utf-8").split()[0]
    if sha256(path) != expected:
        raise RuntimeError(f"checksum mismatch: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def _version() -> str:
    run = subprocess.run(["pdftotext", "-v"], capture_output=True, check=True)
    return (run.stderr or run.stdout).decode("utf-8", errors="replace").splitlines()[0].strip()


def _page_count(path: Path) -> int:
    run = subprocess.run(["pdfinfo", str(path)], capture_output=True, check=True, text=True)
    found = re.search(r"^Pages:\s+(\d+)$", run.stdout, re.MULTILINE)
    if not found:
        raise RuntimeError(f"PDF page count unavailable: {path}")
    return int(found.group(1))


def _inputs() -> tuple[dict, dict]:
    packet = _verified_json(PACKET)
    reports = _verified_json(REPORTS)
    if packet.get("case_count") != 72 or len(packet.get("cases", [])) != 72:
        raise RuntimeError("blind packet case count changed")
    if reports.get("expert_labels") != 0 or reports.get("annotation_source_ledger_entries") != 0:
        raise RuntimeError("report intake role changed")
    if [item["report_year"] for item in reports["reports"]] != [2014, 2015, 2016]:
        raise RuntimeError("unexpected annual report set")
    for item in reports["reports"]:
        path = ROOT / item["local_path"]
        if not path.is_file() or path.stat().st_size != item["bytes"] or sha256(path) != item["sha256"]:
            raise RuntimeError(f"report source changed: {path}")
    return packet, reports


def date_pattern(day: date) -> re.Pattern[str]:
    """Match explicit day/month wording, rejecting a different explicit year."""
    month = "(?:" + "|".join(MONTHS[day.month]) + ")"
    number = f"0?{day.day}(?:st|nd|rd|th)?"
    sep = r"[\s,./-]+"
    forward = rf"\b{number}{sep}{month}\b"
    reverse = rf"\b{month}{sep}{number}\b"
    return re.compile(rf"(?:{forward}|{reverse})(?:[\s,./-]+(?P<year>\d{{4}}))?", re.IGNORECASE)


def candidate_pages(pages: list[str], day: date) -> list[int]:
    pattern = date_pattern(day)
    return [index for index, page in enumerate(pages, 1)
            if any(match.group("year") in (None, str(day.year)) for match in pattern.finditer(page))]


def _extract_pages(path: Path, expected: int) -> list[str]:
    run = subprocess.run(["pdftotext", "-enc", "UTF-8", "-layout", str(path), "-"],
                         capture_output=True, check=True)
    pages = run.stdout.decode("utf-8", errors="replace").split("\f")
    if pages and not pages[-1].strip():
        pages.pop()
    if len(pages) != expected:
        raise RuntimeError(f"text/PDF page count mismatch: {path}: {len(pages)} vs {expected}")
    return pages


def prepare() -> dict:
    packet, reports = _inputs()
    protocol = {
        "schema": "rsmc-regime-page-index-protocol-v1",
        "date": "2026-10-09",
        "status": "FROZEN_BEFORE_REPORT_DATE_TO_CASE_MATCHING",
        "role": "local_only_unreviewed_bibliographic_page_leads",
        "case_count": len(packet["cases"]),
        "packet_sha256": sha256(PACKET),
        "report_intake_sha256": sha256(REPORTS),
        "runner_sha256": sha256(Path(__file__)),
        "extractor": _version(),
        "reports": [{"year": item["report_year"], "sha256": item["sha256"],
                     "pdf_pages": _page_count(ROOT / item["local_path"])} for item in reports["reports"]],
        "match_rule": "Only exact day/month or month/day wording, optional ordinal and explicit matching year; no ranges, numeric-only dates or semantic classification",
        "rights": "local_review_only_reproduction_permission_not_established",
        "case_level_evidence_admitted": False,
        "expert_labels_created": False,
        "warning": "A page hit may refer to another system, geography or historical comparison; no hit is not evidence of absence.",
    }
    return {"protocol_sha256": _write_once(PROTOCOL, protocol), "status": protocol["status"]}


def _compute(protocol: dict, packet: dict, reports: dict) -> dict:
    if (protocol["runner_sha256"] != sha256(Path(__file__))
            or protocol["packet_sha256"] != sha256(PACKET)
            or protocol["report_intake_sha256"] != sha256(REPORTS)
            or protocol["extractor"] != _version()):
        raise RuntimeError("protocol code/source/tool mismatch")
    by_year = {item["report_year"]: item for item in reports["reports"]}
    pages_by_year = {}
    for pinned in protocol["reports"]:
        source = by_year[pinned["year"]]
        if pinned["sha256"] != source["sha256"]:
            raise RuntimeError("report hash differs from protocol")
        pages_by_year[pinned["year"]] = _extract_pages(ROOT / source["local_path"], pinned["pdf_pages"])
    rows = []
    for case in sorted(packet["cases"], key=lambda item: item["case_id"]):
        day = date.fromisoformat(case["rain_valid_date_03_03_utc"])
        pages = candidate_pages(pages_by_year[day.year], day)
        rows.append({"case_id": case["case_id"], "valid_date": day.isoformat(),
                     "annual_report_year": day.year, "candidate_pdf_pages": pages,
                     "review_status": "UNREVIEWED_DATE_STRING_ONLY_NO_LABEL"})
    return {
        "schema": "rsmc-regime-page-index-result-v1",
        "status": "LOCAL_BIBLIOGRAPHIC_LEADS_ONLY",
        "protocol_sha256": sha256(PROTOCOL),
        "cases": rows,
        "case_count": len(rows),
        "cases_with_page_hits": sum(bool(row["candidate_pdf_pages"]) for row in rows),
        "cases_without_page_hits": sum(not row["candidate_pdf_pages"] for row in rows),
        "candidate_page_references": sum(len(row["candidate_pdf_pages"]) for row in rows),
        "case_level_evidence_admitted": False,
        "expert_labels_created": False,
        "2025_2026_observation_values_read": False,
        "rights": protocol["rights"],
        "warning": protocol["warning"],
    }


def write() -> dict:
    protocol = _verified_json(PROTOCOL)
    packet, reports = _inputs()
    result = _compute(protocol, packet, reports)
    return {"result_sha256": _write_once(RESULT, result), "case_count": result["case_count"],
            "cases_with_page_hits": result["cases_with_page_hits"], "status": result["status"]}


def check() -> dict:
    protocol = _verified_json(PROTOCOL)
    recorded = _verified_json(RESULT)
    packet, reports = _inputs()
    if _json_bytes(recorded) != _json_bytes(_compute(protocol, packet, reports)):
        raise RuntimeError("page index does not reproduce")
    return {"protocol_sha256": sha256(PROTOCOL), "result_sha256": sha256(RESULT),
            "status": "RSMC_PAGE_INDEX_REPRODUCED"}


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) == 2 else ""
    if mode not in {"prepare", "write", "check"}:
        raise SystemExit("usage: build_regime_report_page_index.py prepare|write|check")
    print(json.dumps({"prepare": prepare, "write": write, "check": check}[mode](), sort_keys=True))
