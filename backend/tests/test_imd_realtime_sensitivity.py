"""The provisional reference reader must preserve date, mask and receipt identity."""

from __future__ import annotations

import hashlib
import json
from datetime import date

import numpy as np
import pytest

from scripts import score_2026_realtime_sensitivity as sensitivity


def test_daily_reader_crops_same_grid_and_rejects_changed_bytes(tmp_path):
    day = date(2026, 6, 1)
    path = tmp_path / "data/raw/observations/imd_realtime_2026_v1/rainfall_20260601.grd"
    path.parent.mkdir(parents=True)
    (path.parent / "receipts").mkdir()
    grid = np.full((129, 135), -999.0, dtype="<f4")
    grid[14, 6] = 72.5
    grid[62, 54] = 0.0
    payload = grid.tobytes()
    path.write_bytes(payload)
    record = {"date": day.isoformat(), "byte_size": len(payload), "sha256": hashlib.sha256(payload).hexdigest(),
              "local_path": "data/raw/observations/imd_realtime_2026_v1/rainfall_20260601.grd"}
    (path.parent / "receipts/20260601.json").write_text(json.dumps(record), encoding="utf-8")
    field, mask = sensitivity.load_day(day, record, tmp_path)
    assert field.shape == mask.shape == (49, 49)
    assert field[0, 0] == 72.5 and field[-1, -1] == 0.0
    assert mask.sum() == 2
    assert not mask[1, 1]

    path.write_bytes(bytes([1]) + payload[1:])
    with pytest.raises(ValueError, match="changed"):
        sensitivity.load_day(day, record, tmp_path)


def test_daily_reader_rejects_misdated_receipt(tmp_path):
    with pytest.raises(ValueError, match="identity"):
        sensitivity.load_day(date(2026, 6, 1), {"date": "2026-06-02", "byte_size": 69660}, tmp_path)


def test_secondary_score_cannot_decode_before_primary_score(monkeypatch):
    monkeypatch.setattr(sensitivity, "preflight", lambda: {"status": "BLOCKED_BEFORE_VALUE_DECODING", "reasons": ["PRIMARY_ANNUAL_SCORE_REQUIRED_FIRST"]})
    monkeypatch.setattr(sensitivity, "load_day", lambda *_args, **_kwargs: pytest.fail("daily values decoded"))
    with pytest.raises(RuntimeError, match="PRIMARY_ANNUAL_SCORE_REQUIRED_FIRST"):
        sensitivity.score_once()
