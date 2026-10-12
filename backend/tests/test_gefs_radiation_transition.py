"""Bounded NOAA radiation evidence must reject changed ranges and cache bytes."""

from __future__ import annotations

import hashlib
import io

import pytest

from scripts import probe_gefs_radiation_transition as probe


class Response:
    def __init__(self, payload: bytes, *, status: int, content_range: str | None = None):
        self.stream = io.BytesIO(payload)
        self.status = status
        self.headers = {"Content-Range": content_range} if content_range else {}

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.stream.close()

    def read(self, count: int):
        return self.stream.read(count)


def test_byte_range_requires_exact_content_range(monkeypatch):
    monkeypatch.setattr(probe, "urlopen", lambda *_args, **_kwargs: Response(b"GRIB", status=206, content_range="bytes 10-13/100"))
    payload, transport = probe._fetch("https://example.test/message", 10, 10, 13)
    assert payload == b"GRIB"
    assert transport["http_status"] == 206
    with pytest.raises(ValueError, match="byte-range response mismatch"):
        probe._fetch("https://example.test/message", 10, 11, 14)


def test_byte_range_rejects_full_body(monkeypatch):
    monkeypatch.setattr(probe, "urlopen", lambda *_args, **_kwargs: Response(b"GRIB", status=200))
    with pytest.raises(ValueError, match="unexpected HTTP"):
        probe._fetch("https://example.test/message", 10, 10, 13)


def test_cached_evidence_tamper_refused(tmp_path, monkeypatch):
    monkeypatch.setattr(probe, "ROOT", tmp_path)
    path = tmp_path / "evidence.grib2"
    path.write_bytes(b"GRIB")
    item = {"local_path": path.name, "byte_size": 4, "sha256": hashlib.sha256(b"GRIB").hexdigest()}
    probe._check_cached({"index": item, "message": item})
    path.write_bytes(b"BAD!")
    with pytest.raises(ValueError, match="changed"):
        probe._check_cached({"index": item, "message": item})
