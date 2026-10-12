from __future__ import annotations

import json

import pytest

from scripts import build_east_coast_static as static
from scripts import probe_east_coast_features as features


def test_stage_protocol_is_frozen_before_any_pairing_and_keeps_seal() -> None:
    data, digest = static.protocol()
    assert static.PROTOCOL.with_suffix(".sha256").read_text().split() == [digest, static.PROTOCOL.name]
    assert data["population_roles"]["2026"].startswith("sealed_independent_test")
    assert data["population_roles"]["2024"].startswith("consumed_development")
    assert data["forecast_features"]["valid_time_observations_as_predictors"] is False
    assert data["forecast_features"]["reanalysis_as_predictors"] is False
    assert data["geometry"]["published_district_product_allowed"] is False


@pytest.mark.skipif(not static.MANIFEST.is_file() or not (static.OUTPUT / "land_mask.npy").is_file(),
                    reason="ignored local static arrays are unavailable")
def test_local_stage_static_receipts_and_mask() -> None:
    result = static.check()
    assert result["status"] == "VERIFIED_LOCAL_RESEARCH_STATIC"
    manifest = json.loads(static.MANIFEST.read_text(encoding="utf-8"))
    assert result["static_land_cells"] == manifest["static_land_cells"]
    assert manifest["observation_values_read"] is False and manifest["model_fitted"] is False


@pytest.mark.skipif(not features.REPORT.is_file() or not (static.OUTPUT / "land_mask.npy").is_file(),
                    reason="ignored local forecast arrays are unavailable")
def test_two_stage_features_reproduce_from_forecast_sources_only() -> None:
    result = features.check()
    assert result["cases"] == 2 and all(count > 0 for count in result["valid_cells"])
    report = json.loads(features.REPORT.read_text(encoding="utf-8"))
    assert report["observation_values_read"] is False and report["reference_paired"] is False
    assert report["independent_skill_claim"] is False
