"""Integrity gate for the append-only four-workstream closeout."""

import json

import pytest

from scripts import audit_four_workstreams as audit


def test_sealed_json_rejects_tampering(tmp_path, monkeypatch):
    monkeypatch.setattr(audit, "BASE", tmp_path)
    path = tmp_path / "sample.json"
    path.write_text(json.dumps({"status": "OPEN_NO_CLEARANCE"}) + "\n")
    path.with_suffix(".sha256").write_text(f"{audit.digest(path)}  sample.json\n")
    value, digest = audit.sealed("sample.json")
    assert value["status"] == "OPEN_NO_CLEARANCE"
    assert digest == audit.digest(path)
    path.write_text(json.dumps({"status": "CLEARED"}) + "\n")
    with pytest.raises(ValueError, match="receipt mismatch"):
        audit.sealed("sample.json")


def test_sealed_json_requires_receipt(tmp_path, monkeypatch):
    monkeypatch.setattr(audit, "BASE", tmp_path)
    (tmp_path / "sample.json").write_text("{}\n")
    with pytest.raises(FileNotFoundError):
        audit.sealed("sample.json")
