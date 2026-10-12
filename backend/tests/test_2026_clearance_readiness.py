"""A supplemental annual/source review must fail closed before 2026 pairing."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import numpy as np

from scripts import audit_2026_clearance_readiness as audit


def _reference() -> dict:
    return {"status": "APPROVED_FOR_LOCAL_RESEARCH_VERIFICATION",
            "annual_calendar_year": 2026, "daily_record_count": 365,
            "first_date": "2026-01-01", "last_date": "2026-12-31",
            "accumulation_window_utc": "03:00-03:00", "file_sha256": "a" * 64,
            "source_url_or_receipt": "https://imdpune.gov.in/example",
            "terms": {"local_research_use_authorized": True,
                      "authorization_evidence_uri_or_hash": "b" * 64,
                      "redistribution_decision": "NOT_AUTHORIZED"}}


def _version() -> dict:
    return {"status": "MODEL_VERSION_REVIEW_COMPLETE",
            "authoritative_evidence_uri_or_hash": "https://www.nco.ncep.noaa.gov/example",
            "actual_transition_utc": "2026-06-15T12:00:00Z",
            "training_version_evidence_uri_or_hash": "c" * 64,
            "training_cycle_versions": {"20230601": "gefs.v12.3.0"},
            "forecast_cycle_versions": {"20260601": "gefs.v12.3.18"},
            "selected_predictor_review": {
                field: {"decision": "ACCEPT_FOR_STRATIFIED_EVALUATION",
                        "evidence_uri_or_hash": "d" * 64,
                        "rationale": "Reviewed source processing and recorded the version difference."}
                for field in audit.FIELDS}}


def test_current_preflight_stays_blocked_without_observation_access() -> None:
    result = audit.preflight()
    assert result["status"] == "BLOCKED_BEFORE_OBSERVATION_READ"
    assert "IMD_2026_REFERENCE_CLEARANCE_MISSING" in result["reasons"]
    assert "GEFS_2026_VERSION_REVIEW_MISSING" in result["reasons"]
    assert result["observation_values_read"] is False
    assert result["score_run"] is False


def test_annual_claim_requires_dates_hash_and_terms() -> None:
    good = _reference()
    assert audit.validate_reference_claim(good) == []
    weak = {**good, "daily_record_count": 125, "terms": {"local_research_use_authorized": False}}
    assert "ANNUAL_REFERENCE_COVERAGE_OR_WINDOW_NOT_REVIEWED" in audit.validate_reference_claim(weak)
    assert "IMD_LOCAL_USE_AND_REDISTRIBUTION_TERMS_UNREVIEWED" in audit.validate_reference_claim(weak)


def test_cycle_map_and_all_predictor_reviews_required() -> None:
    good = _version()
    assert audit.validate_version_claim(good, {"20230601"}, {"20260601"}) == []
    weak = {**good, "training_cycle_versions": {},
            "selected_predictor_review": {"rain": good["selected_predictor_review"]["rain"]}}
    reasons = audit.validate_version_claim(weak, {"20230601"}, {"20260601"})
    assert "TRAINING_CYCLE_VERSIONS_INCOMPLETE" in reasons
    assert "SELECTED_PREDICTOR_COMPARABILITY_NOT_APPROVED" in reasons


def test_annual_metadata_reads_axis_but_not_rainfall_values(tmp_path: Path, monkeypatch) -> None:
    path = tmp_path / "annual.nc"
    path.touch()

    class Rain:
        shape = (365, 129, 135)

        @property
        def data(self):
            raise AssertionError("rainfall values must stay unopened")

    class Dataset:
        def __init__(self):
            self.variables = {"TIME": SimpleNamespace(units=b"days since 2026-01-01", data=np.arange(365)),
                              "LATITUDE": SimpleNamespace(data=np.empty(129)),
                              "LONGITUDE": SimpleNamespace(data=np.empty(135)),
                              "RAINFALL": Rain()}

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return None

    monkeypatch.setattr(audit, "netcdf_file", lambda *_args, **_kwargs: Dataset())
    assert audit.validate_annual_metadata(path) == []

    class MissingDay(Dataset):
        def __init__(self):
            super().__init__()
            self.variables["TIME"].data[120] = 119

    monkeypatch.setattr(audit, "netcdf_file", lambda *_args, **_kwargs: MissingDay())
    assert audit.validate_annual_metadata(path) == ["ANNUAL_REFERENCE_DAILY_AXIS_INCOMPLETE"]
