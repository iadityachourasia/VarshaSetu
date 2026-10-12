"""Byte integrity and non-clearance scope of the NOAA EMC review intake."""

import hashlib
import json

import pytest

from scripts import check_gefs_2023_emc_review as review


def test_receipt_is_write_once_and_rejects_tampering(tmp_path, monkeypatch) -> None:
    pdf = tmp_path / "source.pdf"
    payload = b"%PDF-1.4\nsource fixture\n%%EOF\n"
    pdf.write_bytes(payload)
    receipt = tmp_path / "evidence.json"
    monkeypatch.setattr(review, "ROOT", tmp_path)
    monkeypatch.setattr(review, "PDF", pdf)
    monkeypatch.setattr(review, "RECEIPT", receipt)
    monkeypatch.setattr(review, "EXPECTED_BYTES", len(payload))
    monkeypatch.setattr(review, "EXPECTED_PDF_SHA256", hashlib.sha256(payload).hexdigest())
    monkeypatch.setattr(review, "pdf_pages", lambda _: review.EXPECTED_PAGES)
    written = review.write()
    assert review.check() == written
    record = json.loads(receipt.read_text(encoding="utf-8"))
    assert record["clearance_created"] is False
    assert record["2026_observation_values_read"] is False
    with pytest.raises(FileExistsError):
        review.write()
    pdf.write_bytes(payload.replace(b"fixture", b"changed"))
    with pytest.raises(ValueError, match="source bytes"):
        review.check()


def test_receipt_hash_is_checked_independently(tmp_path, monkeypatch) -> None:
    pdf = tmp_path / "source.pdf"
    payload = b"%PDF-1.4\nfixture\n%%EOF\n"
    pdf.write_bytes(payload)
    receipt = tmp_path / "evidence.json"
    monkeypatch.setattr(review, "ROOT", tmp_path)
    monkeypatch.setattr(review, "PDF", pdf)
    monkeypatch.setattr(review, "RECEIPT", receipt)
    monkeypatch.setattr(review, "EXPECTED_BYTES", len(payload))
    monkeypatch.setattr(review, "EXPECTED_PDF_SHA256", hashlib.sha256(payload).hexdigest())
    monkeypatch.setattr(review, "pdf_pages", lambda _: review.EXPECTED_PAGES)
    review.write()
    receipt.write_text(receipt.read_text(encoding="utf-8") + " ", encoding="utf-8")
    with pytest.raises(ValueError, match="receipt hash"):
        review.check()
