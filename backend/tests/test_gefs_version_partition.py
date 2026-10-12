from __future__ import annotations

import pytest

from scripts.summarize_gefs_version_partition import partition, sealed


def test_announced_noon_boundary_on_00z_archive() -> None:
    effective = "2026-06-15T12:00:00Z"
    assert partition("20260615", effective) == "before_announced_change"
    assert partition("20260616", effective) == "after_announced_change"


def test_partition_requires_unambiguous_utc_time_and_cycle() -> None:
    with pytest.raises(ValueError):
        partition("2026061", "2026-06-15T12:00:00Z")
    with pytest.raises(ValueError):
        partition("20260615", "2026-06-15T12:00:00")


def test_sealed_source_refuses_tampered_bytes(tmp_path) -> None:
    path = tmp_path / "source.json"
    path.write_text('{"status":"forecast-only"}', encoding="utf-8")
    path.with_suffix(".sha256").write_text("0" * 64 + "  source.json\n", encoding="ascii")
    with pytest.raises(ValueError, match="hash mismatch"):
        sealed(path)
