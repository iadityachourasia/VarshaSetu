"""Receipt and integrity check for one local, official GEFS version source.

This only admits a June 2023 EMC review PDF as contextual evidence. It never
creates a GEFS version clearance or reads forecast/observation values.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PDF = ROOT / "data/raw/evidence/gefs_version_review_2023_v1/EMC_Review_Package_Implementations_2023.pdf"
RECEIPT = ROOT / "data/manifests/research_pilot/gefs_2023_emc_review_intake_v1.json"
SOURCE_URL = (
    "https://vlab.noaa.gov/documents/17693964/29773494/"
    "EMC%2BReview%2BPackage%2B-%2BImplementations.pdf/"
    "16039299-9768-1739-c0d9-9cdf02da4841?t=1685111831730"
)
EXPECTED_PDF_SHA256 = "97cefdcf67559e8872cbc059fab5c70c382e72fb2e6223d7820acda567b921e7"
EXPECTED_BYTES = 532296
EXPECTED_PAGES = 10


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate_file(path: Path, *, expected_bytes: int, expected_sha256: str) -> None:
    if (not path.is_file() or path.stat().st_size != expected_bytes
            or path.open("rb").read(5) != b"%PDF-" or sha256(path) != expected_sha256):
        raise ValueError("NOAA EMC source bytes or SHA-256 changed")


def pdf_pages(path: Path) -> int:
    result = subprocess.run(["pdfinfo", str(path)], check=True, capture_output=True,
                            text=True, timeout=15)
    match = re.search(r"^Pages:\s+(\d+)\s*$", result.stdout, re.MULTILINE)
    if not match:
        raise ValueError("PDF page count unavailable")
    return int(match.group(1))


def write() -> dict:
    """Write a source receipt only for the already downloaded, pinned bytes."""
    if RECEIPT.exists() or RECEIPT.with_suffix(".sha256").exists():
        raise FileExistsError("write-once EMC source receipt already exists")
    validate_file(PDF, expected_bytes=EXPECTED_BYTES, expected_sha256=EXPECTED_PDF_SHA256)
    if pdf_pages(PDF) != EXPECTED_PAGES:
        raise ValueError("unexpected NOAA EMC PDF page count")
    record = {
        "schema": "gefs-2023-emc-review-source-intake-v1",
        "status": "CONTEXT_ONLY_NOT_CYCLE_VERSION_CLEARANCE",
        "source_url": SOURCE_URL,
        "source_organization": "NOAA/NWS/NCEP/EMC",
        "source_title": "EMC Review Package - Implementations",
        "printed_review_date": "2023-06-06/2023-06-08",
        "http_last_modified": "Fri, 26 May 2023 14:37:11 GMT",
        "http_content_type": "application/pdf",
        "intake_checked_utc": datetime.now(timezone.utc).isoformat(),
        "local_path": PDF.relative_to(ROOT).as_posix(),
        "bytes": EXPECTED_BYTES,
        "pages": EXPECTED_PAGES,
        "sha256": EXPECTED_PDF_SHA256,
        "inspected_pages": [8, 9, 10],
        "use_rights": "Local source review only; redistribution of PDF not assessed",
        "claim_limit": "The printed Current (Ops) GEFS 12.3.5 column is June-2023 context, not a per-cycle JJAS-2023 executable record",
        "2026_observation_values_read": False,
        "clearance_created": False,
    }
    payload = (json.dumps(record, indent=2, sort_keys=True, allow_nan=False) + "\n").encode("utf-8")
    RECEIPT.parent.mkdir(parents=True, exist_ok=True)
    RECEIPT.write_bytes(payload)
    digest = hashlib.sha256(payload).hexdigest()
    RECEIPT.with_suffix(".sha256").write_text(f"{digest}  {RECEIPT.name}\n", encoding="utf-8")
    return {"status": record["status"], "pdf_sha256": EXPECTED_PDF_SHA256,
            "receipt_sha256": digest}


def check() -> dict:
    if not RECEIPT.is_file() or not RECEIPT.with_suffix(".sha256").is_file():
        raise FileNotFoundError("NOAA EMC source receipt missing")
    record = json.loads(RECEIPT.read_text(encoding="utf-8"))
    digest = sha256(RECEIPT)
    if (RECEIPT.with_suffix(".sha256").read_text(encoding="utf-8")
            != f"{digest}  {RECEIPT.name}\n"):
        raise ValueError("NOAA EMC receipt hash changed")
    expected = {"schema": "gefs-2023-emc-review-source-intake-v1",
                "status": "CONTEXT_ONLY_NOT_CYCLE_VERSION_CLEARANCE",
                "source_url": SOURCE_URL, "local_path": PDF.relative_to(ROOT).as_posix(),
                "bytes": EXPECTED_BYTES, "pages": EXPECTED_PAGES,
                "sha256": EXPECTED_PDF_SHA256, "clearance_created": False,
                "2026_observation_values_read": False}
    if any(record.get(key) != value for key, value in expected.items()):
        raise ValueError("NOAA EMC receipt scope or source changed")
    validate_file(PDF, expected_bytes=EXPECTED_BYTES, expected_sha256=EXPECTED_PDF_SHA256)
    if pdf_pages(PDF) != EXPECTED_PAGES:
        raise ValueError("NOAA EMC PDF page count changed")
    return {"status": record["status"], "pdf_sha256": EXPECTED_PDF_SHA256,
            "receipt_sha256": digest}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("write", "check"))
    arguments = parser.parse_args()
    print(json.dumps({"write": write, "check": check}[arguments.command](), sort_keys=True))
