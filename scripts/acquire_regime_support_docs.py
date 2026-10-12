"""Bounded local intake of official RSMC annual reports for human review.

The annual PDFs are bibliographic aids only. This tool does not infer case
labels, assign case validity windows, or add them to the annotation ledger.
RSMC reproduction rights are unresolved; keep raw files local.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "data/raw/evidence/regime_review_rsmc_annual_v1"
MANIFEST = ROOT / "data/manifests/research_pilot/regime_support_docs_v1.json"
MAX_BYTES = 65_000_000
REPORTS = {
    2014: "https://rsmcnewdelhi.imd.gov.in/uploads/report/27/27_4e1280_rsmc-2014.pdf",
    2015: "https://rsmcnewdelhi.imd.gov.in/uploads/report/27/27_9bbd0d_RSMC-2015.pdf",
    2016: "https://rsmcnewdelhi.imd.gov.in/uploads/report/27/27_ad292c_rsmc-2016.pdf",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def acquire() -> dict:
    if MANIFEST.exists() or MANIFEST.with_suffix(".sha256").exists():
        raise FileExistsError("support-document manifest is write-once")
    OUTPUT.mkdir(parents=True, exist_ok=True)
    rows = []
    for year, url in REPORTS.items():
        path = OUTPUT / f"RSMC_annual_{year}.pdf"
        if not path.exists():
            temporary = path.with_suffix(".pdf.partial")
            request = Request(url, headers={"User-Agent": "VarshaSetu-research-source-intake/1.0"})
            try:
                with urlopen(request, timeout=30) as response, temporary.open("xb") as stream:
                    if response.status != 200 or "application/pdf" not in response.headers.get("Content-Type", "").lower():
                        raise ValueError(f"RSMC response is not a PDF: {year}")
                    declared = int(response.headers.get("Content-Length", "0"))
                    if declared > MAX_BYTES:
                        raise ValueError(f"RSMC report exceeds byte cap: {year}")
                    size = 0
                    while chunk := response.read(1024 * 1024):
                        size += len(chunk)
                        if size > MAX_BYTES:
                            raise ValueError(f"RSMC report exceeds byte cap: {year}")
                        stream.write(chunk)
                with temporary.open("rb") as stream:
                    signature = stream.read(5)
                if size == 0 or (declared and declared != size) or signature != b"%PDF-":
                    raise ValueError(f"RSMC report incomplete or not PDF: {year}")
                temporary.replace(path)
            finally:
                if temporary.exists():
                    temporary.unlink()
        with path.open("rb") as stream:
            signature = stream.read(5)
        if path.stat().st_size == 0 or path.stat().st_size > MAX_BYTES or signature != b"%PDF-":
            raise ValueError(f"existing support document is invalid: {year}")
        rows.append({
            "report_year": year, "source_url": url,
            "local_path": path.relative_to(ROOT).as_posix(),
            "bytes": path.stat().st_size, "sha256": sha256(path),
            "use_rights": "local_review_only_reproduction_permission_not_established",
            "case_level_evidence_admitted": False,
            "issued_utc": None,
        })
    manifest = {
        "schema": "varshasetu-regime-support-documents-v1",
        "retrieval_utc_date": "2026-10-07",
        "status": "BIBLIOGRAPHIC_INTAKE_ONLY_NO_CASE_LABELS",
        "copyright_policy": "https://rsmcnewdelhi.imd.gov.in/copyright-policy.php",
        "reports": rows,
        "expert_labels": 0,
        "annotation_source_ledger_entries": 0,
    }
    MANIFEST.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    MANIFEST.with_suffix(".sha256").write_text(f"{sha256(MANIFEST)}  {MANIFEST.name}\n", encoding="ascii")
    return manifest


def check() -> dict:
    if MANIFEST.with_suffix(".sha256").read_text(encoding="ascii").split() != [sha256(MANIFEST), MANIFEST.name]:
        raise ValueError("support-document manifest hash mismatch")
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    if manifest["expert_labels"] != 0 or manifest["annotation_source_ledger_entries"] != 0:
        raise ValueError("annual reports were incorrectly promoted to case labels")
    for row in manifest["reports"]:
        path = ROOT / row["local_path"]
        if path.stat().st_size != row["bytes"] or sha256(path) != row["sha256"]:
            raise ValueError(f"support-document hash mismatch: {row['report_year']}")
    return {"status": "VERIFIED_BIBLIOGRAPHIC_INTAKE", "reports": len(manifest["reports"]), "expert_labels": 0}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--acquire", action="store_true")
    group.add_argument("--check", action="store_true")
    args = parser.parse_args()
    print(json.dumps(acquire() if args.acquire else check(), sort_keys=True))


if __name__ == "__main__":
    main()
