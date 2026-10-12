"""Forecast-only 2026 corpus publication is immutable and hash checked."""

import numpy as np
import pytest
import hashlib
import json
from pathlib import Path

from scripts import build_gefs_2026_forecast_corpus as corpus
from scripts import summarize_gefs_2026_forecast_corpus as monthly
from scripts import summarize_gefs_2026_forecast_year as yearly
from scripts import summarize_2026_feature_shift_year as year_features


def test_protocol_keeps_forecast_only_scope_and_canonical_windows():
    settings, digest = corpus.protocol()
    assert len(digest) == 64
    assert corpus.dates_for_month("202606", settings)[0] == "20260601"
    assert corpus.dates_for_month("202609", settings)[-1] == "20260930"
    with pytest.raises(ValueError):
        corpus.dates_for_month("202610", settings)
    assert settings["rainfall_windows_hours"] == {"day1_24h": [3, 27], "day2_24h": [27, 51], "day3_24h": [51, 75]}


def test_case_publication_verifies_hashes_and_refuses_overwrite(tmp_path):
    _, digest = corpus.protocol()
    manifest = {"schema": "test", "cycle": "20260601", "protocol_sha256": digest,
                "observation_read": False, "model_inference": False,
                "products_passing_qc": ["day1_24h"], "withheld_products": {}}
    array = np.ones((2401, 22), dtype=np.float32)
    directory = corpus.publish_case(tmp_path, "20260601", manifest, {"X_day1_24h.npy": array})
    assert corpus.verify_case(directory, digest)["products_passing_qc"] == ["day1_24h"]
    with pytest.raises(FileExistsError):
        corpus.publish_case(tmp_path, "20260601", manifest, {"X_day1_24h.npy": array})
    np.save(directory / "X_day1_24h.npy", np.zeros_like(array), allow_pickle=False)
    with pytest.raises(ValueError, match="integrity"):
        corpus.verify_case(directory, digest)


def test_publication_rejects_nonfinite_forecast_array(tmp_path):
    bad = np.array([np.nan], dtype=np.float32)
    with pytest.raises(ValueError, match="invalid forecast"):
        corpus.publish_case(tmp_path, "20260601", {"cycle": "20260601"}, {"X_day1_24h.npy": bad})
    assert not (tmp_path / "20260601").exists()


def test_atomic_case_publication_retries_transient_windows_access_denial(tmp_path, monkeypatch):
    original = Path.rename
    attempts = []

    def transient(self, target):
        attempts.append(self)
        if len(attempts) == 1:
            error = PermissionError("transient Windows staging-directory access denial")
            error.winerror = 5
            raise error
        return original(self, target)

    monkeypatch.setattr(Path, "rename", transient)
    monkeypatch.setattr(corpus.time, "sleep", lambda _seconds: None)
    target = corpus.publish_case(tmp_path, "20260601", {"cycle": "20260601"}, {})
    assert target.is_dir() and len(attempts) == 2
    assert not list(tmp_path.glob(".stage-*"))


def test_month_summary_refuses_missing_dates_and_counts_qc_leads(tmp_path):
    settings, digest = corpus.protocol()
    dates = corpus.dates_for_month("202606", settings)
    with pytest.raises(ValueError, match="incomplete"):
        monthly.summary("202606", root=tmp_path)
    for cycle in dates:
        passing = ["day1_24h"] if cycle == dates[0] else []
        record = {"schema": "test", "cycle": cycle, "protocol_sha256": digest,
                  "observation_read": False, "model_inference": False,
                  "status": "FEATURES_READY" if passing else "NO_ELIGIBLE_LEAD",
                  "products_passing_qc": passing, "withheld_products": {}, "planned_selected_bytes": 100}
        corpus.publish_case(tmp_path, cycle, record, {})
    result = monthly.summary("202606", root=tmp_path)
    assert result["cycle_count"] == 30 and result["products_passing_qc"]["day1_24h"] == 1
    assert result["products_withheld_qc"]["day1_24h"] == 29
    assert result["no_eligible_lead_cycles"] == 29 and result["observation_read"] is False
    destination = tmp_path / "month.json"
    monthly.write_once("202606", result, output=destination)
    monthly.write_once("202606", result, output=destination)


def test_case_verifier_rehashes_source_cache_against_manifest(tmp_path):
    _, digest = corpus.protocol()
    payload = b"example selected GRIB bytes"
    source_hash = hashlib.sha256(payload).hexdigest()
    source_root = tmp_path / "cache"
    source = source_root / "20260601/pgrb2sp25/f003_rain.grib2"
    source.parent.mkdir(parents=True)
    source.write_bytes(payload)
    source.with_name(source.name + ".receipt.json").write_text(json.dumps({"sha256": source_hash, "byte_size": len(payload)}))
    record = {"schema": "test", "cycle": "20260601", "protocol_sha256": digest,
              "observation_read": False, "model_inference": False,
              "source_sha256": {"pgrb2sp25:3:rain": source_hash}}
    directory = corpus.publish_case(tmp_path / "cases", "20260601", record, {})
    corpus.verify_case(directory, digest, source_root=source_root)
    source.write_bytes(b"tampered")
    with pytest.raises(ValueError, match="source integrity"):
        corpus.verify_case(directory, digest, source_root=source_root)


def test_transient_503_retries_without_changing_case_identity(monkeypatch, tmp_path):
    calls, sleeps = [], []

    def case(cycle, settings, digest, *, root):
        calls.append(cycle)
        if len(calls) == 1:
            raise corpus.pipeline.CycleRefused("index not available (HTTP 503)")
        return {"cycle": cycle, "status": "FEATURES_READY"}

    monkeypatch.setattr(corpus, "build_case", case)
    monkeypatch.setattr(corpus.time, "sleep", sleeps.append)
    assert corpus.build_case_with_retries("20260712", {}, "digest", root=tmp_path)["cycle"] == "20260712"
    assert calls == ["20260712", "20260712"]
    assert sleeps == [10]


def test_nontransient_scientific_gate_is_not_retried(monkeypatch, tmp_path):
    calls = []

    def case(cycle, settings, digest, *, root):
        calls.append(cycle)
        raise ValueError("source integrity failure")

    monkeypatch.setattr(corpus, "build_case", case)
    with pytest.raises(ValueError, match="source integrity failure"):
        corpus.build_case_with_retries("20260712", {}, "digest", root=tmp_path)
    assert calls == ["20260712"]


def test_year_seal_refuses_missing_month_summaries(tmp_path):
    with pytest.raises(ValueError, match="incomplete"):
        yearly.summary(base=tmp_path)


def test_year_seal_aggregates_only_verified_months(monkeypatch, tmp_path):
    reports = {}
    for month, cycles in zip(yearly.MONTHS, (30, 31, 31, 30)):
        report = {"month": month, "cycle_count": cycles, "observation_read": False, "model_inference": False,
                  "products_passing_qc": {"day1_24h": 1, "day2_24h": 2, "day3_24h": 3},
                  "products_withheld_qc": {"day1_24h": cycles - 1, "day2_24h": cycles - 2, "day3_24h": cycles - 3},
                  "no_eligible_lead_cycles": 0}
        reports[month] = report
        path = tmp_path / f"2026_forecast_month_{month}_v1.json"
        path.write_text(json.dumps(report), encoding="utf-8")
        path.with_suffix(".sha256").write_text(hashlib.sha256(path.read_bytes()).hexdigest(), encoding="ascii")
    monkeypatch.setattr(yearly.monthly, "summary", lambda month: reports[month])
    result = yearly.summary(base=tmp_path)
    assert result["cycle_count"] == 122
    assert result["possible_date_lead_products"] == 366
    assert result["products_passing_qc"] == {"day1_24h": 4, "day2_24h": 8, "day3_24h": 12}
    assert result["products_withheld_qc"]["day1_24h"] == 118


def test_year_feature_range_uses_exact_sealed_case_population(monkeypatch, tmp_path):
    year = {"products_passing_qc": {"day1_24h": 4, "day2_24h": 0, "day3_24h": 0}}
    path = tmp_path / "year.json"
    path.write_text(json.dumps(year), encoding="utf-8")
    path.with_suffix(".sha256").write_text(hashlib.sha256(path.read_bytes()).hexdigest(), encoding="ascii")
    monkeypatch.setattr(year_features.yearly, "OUT", path)
    monkeypatch.setattr(year_features.yearly, "summary", lambda: year)

    def month_result(month):
        fractions = {name: 0.0 for name in year_features.feature.FEATURE_NAMES}
        if month == "202606":
            fractions["forecast_z500"] = .1
        return {"training_X_sha256": "a" * 64,
                "rows": [{"cycle": month + "01", "lead": "day1_24h", "outside_fraction_by_feature": fractions}]}

    monkeypatch.setattr(year_features.feature, "summarize", month_result)
    report = year_features.summary()
    assert report["cases"] == 4 and report["by_lead"]["day1_24h"]["cases"] == 4
    assert report["by_lead"]["day2_24h"]["cases"] == 0
    assert report["dynamic_case_feature_warnings_over_5pct"] == [
        {"cycle": "20260601", "lead": "day1_24h", "feature": "forecast_z500", "outside_fraction": .1}
    ]
