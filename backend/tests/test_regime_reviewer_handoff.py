from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

import pytest

from backend.app.ml.expert_regime_review import TASKS
from scripts.prepare_regime_reviewer_handoff import prepare


def test_blank_handoff_matches_validator_columns_without_inventing_labels(tmp_path: Path) -> None:
    maps = tmp_path / "maps"
    (maps / "forecast_maps").mkdir(parents=True)
    (maps / "forecast_maps/x.png").write_bytes(b"forecast-only")
    packet = {
        "schema": "expert-regime-review-packet-v1", "case_count": 1,
        "cases": [{
            "case_id": "x", "forecast_source": "GEFS", "source_version": "v12",
            "issue_utc": "2014-06-09T00:00:00Z", "lead_window_h": [3, 27],
            "region_id": "research-box", "forecast_fields_png": "forecast_maps/x.png",
            "forecast_fields_sha256": hashlib.sha256(b"forecast-only").hexdigest(),
        }],
    }
    path = tmp_path / "packet.json"
    path.write_text(json.dumps(packet), encoding="utf-8")
    path.with_suffix(".sha256").write_text(hashlib.sha256(path.read_bytes()).hexdigest() + "  packet.json\n")
    output = tmp_path / "handoff"
    result = prepare(path, maps, output)
    assert result["status"] == "DRAFT_AWAITING_REAL_REVIEWERS_AND_DATED_SOURCES"
    assert result["expert_labels"] == result["source_documents_admitted"] == 0
    for reviewer in ("a", "b"):
        with (output / f"reviewer_{reviewer}_blank.csv").open(newline="", encoding="utf-8") as stream:
            reader = csv.DictReader(stream)
            rows = list(reader)
        assert len(rows) == 1 and rows[0]["case_id"] == "x"
        assert rows[0]["reviewer_id"] == rows[0]["blind_to_detector_outputs"] == ""
        for task in TASKS:
            assert rows[0][task] == rows[0][f"{task}_evidence_ids"] == ""
    assert json.loads((output / "roster_template.json").read_text())["reviewer_ids"] == ["", ""]
    assert json.loads((output / "source_ledger_template.json").read_text())["sources"] == []
    with pytest.raises(FileExistsError, match="write-once"):
        prepare(path, maps, output)
