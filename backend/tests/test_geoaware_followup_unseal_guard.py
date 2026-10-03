"""The unseal guard of the one-shot 2022 test (docs/132): it refuses everything except a complete, hash-matching, owner-signed record."""

from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture()
def score(tmp_path, monkeypatch):
    spec = importlib.util.spec_from_file_location("score_geoaware_followup_2022", ROOT / "scripts/score_geoaware_followup_2022.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    monkeypatch.setattr(module, "ROOT", tmp_path)
    monkeypatch.setattr(module, "PHASE11", tmp_path / "phase11")
    monkeypatch.setattr(module, "UNSEAL", tmp_path / "phase11/geoaware_followup_unseal_record.json")
    monkeypatch.setattr(module, "RESULT", tmp_path / "phase11/geoaware_followup_test_2022.json")
    (tmp_path / "phase11").mkdir()
    return module


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_record(module, tmp_path: Path, **overrides) -> dict:
    listed = tmp_path / "listed.bin"
    listed.write_bytes(b"frozen content")
    record = {"written_before_any_2022_observation_value_was_read": True, "owner_message": {"verbatim": "do all of three perfectly"},
              "hashes": {"model": {"path": "listed.bin", "sha256": _sha(listed)},
                         "scoring_script": {"path": "scripts/score_geoaware_followup_2022.py", "sha256": _sha(Path(module.__file__))}}}
    record.update(overrides)
    module.UNSEAL.write_text(json.dumps(record), encoding="utf-8")
    (tmp_path / "phase11/geoaware_followup_unseal_record.sha256").write_text(_sha(module.UNSEAL) + "  record\n", encoding="ascii")
    (tmp_path / "scripts").mkdir(exist_ok=True)
    (tmp_path / "scripts/score_geoaware_followup_2022.py").write_bytes(Path(module.__file__).read_bytes())
    return record


def test_without_a_record_2022_stays_sealed(score):
    with pytest.raises(SystemExit, match="no unseal record"):
        score.verify_unseal_record()


def test_a_complete_matching_record_is_accepted(score, tmp_path):
    _write_record(score, tmp_path)
    assert score.verify_unseal_record()["owner_message"]["verbatim"] == "do all of three perfectly"


def test_the_test_is_one_shot_a_result_blocks_any_rerun(score, tmp_path):
    _write_record(score, tmp_path)
    score.RESULT.write_text("{}", encoding="utf-8")
    with pytest.raises(SystemExit, match="one-shot"):
        score.verify_unseal_record()


def test_a_tampered_listed_file_is_refused(score, tmp_path):
    _write_record(score, tmp_path)
    (tmp_path / "listed.bin").write_bytes(b"changed after freezing")
    with pytest.raises(SystemExit, match="hash mismatch"):
        score.verify_unseal_record()


def test_a_record_that_differs_from_its_sidecar_is_refused(score, tmp_path):
    _write_record(score, tmp_path)
    (tmp_path / "phase11/geoaware_followup_unseal_record.sha256").write_text("0" * 64 + "  record\n", encoding="ascii")
    with pytest.raises(SystemExit, match="sidecar"):
        score.verify_unseal_record()


def test_a_scoring_script_that_differs_from_the_recorded_one_is_refused(score, tmp_path):
    record = _write_record(score, tmp_path)
    record["hashes"]["scoring_script"]["sha256"] = "0" * 64
    module_listed = tmp_path / "scripts/score_geoaware_followup_2022.py"
    module_listed.write_bytes(b"# a different script")                      # the listed file is hashed first and no longer matches the record
    score.UNSEAL.write_text(json.dumps(record), encoding="utf-8")
    (tmp_path / "phase11/geoaware_followup_unseal_record.sha256").write_text(_sha(score.UNSEAL) + "  record\n", encoding="ascii")
    with pytest.raises(SystemExit):
        score.verify_unseal_record()


def test_a_record_without_the_owner_authorisation_is_refused(score, tmp_path):
    _write_record(score, tmp_path, owner_message={"verbatim": ""})
    with pytest.raises(SystemExit, match="owner authorisation"):
        score.verify_unseal_record()
    score.UNSEAL.unlink()
    _write_record(score, tmp_path, written_before_any_2022_observation_value_was_read=False)
    with pytest.raises(SystemExit, match="owner authorisation"):
        score.verify_unseal_record()
