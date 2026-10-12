"""Forecast-only applicability summary must not clear the 2026 source gate."""

from __future__ import annotations

import hashlib
import json

import pytest

from scripts import audit_2026_feature_applicability as app


def _copy(source, target):
    target.write_bytes(source.read_bytes())
    target.with_suffix(".sha256").write_bytes(source.with_suffix(".sha256").read_bytes())


def _rewrite(path, value):
    raw = (json.dumps(value, indent=2, sort_keys=True) + "\n").encode()
    path.write_bytes(raw)
    path.with_suffix(".sha256").write_text(f"{hashlib.sha256(raw).hexdigest()}  {path.name}\n", encoding="ascii")


def test_sealed_forecast_only_summary_preserves_month_denominators():
    report = app.audit()
    assert report["status"] == "DESCRIPTIVE_FORECAST_ONLY_NO_VERSION_CLEARANCE"
    assert report["observation_read"] is False
    assert (report["cases"], report["flagged_case_leads"], report["feature_case_warnings"]) == (213, 45, 123)
    assert [(row["month"], row["eligible_case_leads"], row["flagged_case_leads"])
            for row in report["months"]] == [("202606", 40, 3), ("202607", 62, 14),
                                              ("202608", 62, 0), ("202609", 49, 28)]


def test_rejects_tampered_receipt_and_observation_provenance(tmp_path):
    feature = tmp_path / app.FEATURES.name
    year = tmp_path / app.YEAR.name
    _copy(app.FEATURES, feature)
    _copy(app.YEAR, year)
    feature.write_bytes(feature.read_bytes() + b" ")
    with pytest.raises(ValueError, match="receipt mismatch"):
        app.audit(feature, year)
    changed = json.loads(app.FEATURES.read_text(encoding="utf-8"))
    changed["observation_read"] = True
    _rewrite(feature, changed)
    with pytest.raises(ValueError, match="Forecast-only provenance"):
        app.audit(feature, year)


def test_rejects_out_of_population_warning_even_with_new_receipt(tmp_path):
    feature = tmp_path / app.FEATURES.name
    year = tmp_path / app.YEAR.name
    _copy(app.FEATURES, feature)
    _copy(app.YEAR, year)
    changed = json.loads(feature.read_text(encoding="utf-8"))
    changed["dynamic_case_feature_warnings_over_5pct"][0]["cycle"] = "20260501"
    _rewrite(feature, changed)
    with pytest.raises(ValueError, match="Warning month is absent"):
        app.audit(feature, year)
