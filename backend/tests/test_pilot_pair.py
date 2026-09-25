import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pytest
from pydantic import ValidationError

from app.data.accumulation import (
    GriddedAccumulationMessage,
    reconstruct_accumulation_window,
    validate_segment_coverage,
)
from app.data.loader import load_source_dataset
from app.data.pilot_models import PilotDerivedManifest, PilotSourceManifest
from app.data.readiness import assess_training_readiness
from app.data.regridding import (
    area_weighted_integral,
    build_first_order_conservative_weights,
)


def message(start, end, value, source_id=None):
    return GriddedAccumulationMessage(
        start_hour=start,
        end_hour=end,
        values_mm=np.full((2, 2), value, dtype=float),
        source_id=source_id or f"m-{start}-{end}",
    )


def valid_messages():
    return [
        message(0, 3, 1),
        message(0, 6, 3),
        message(6, 9, 3),
        message(6, 12, 7),
        message(12, 15, 5),
        message(12, 18, 11),
        message(18, 21, 7),
        message(18, 24, 15),
        message(24, 27, 9),
    ]


def test_exact_24_hour_accumulation_has_eight_non_overlapping_segments():
    result = reconstruct_accumulation_window(
        valid_messages(), window_start_hour=3, window_end_hour=27
    )
    assert np.array_equal(result.rainfall_mm, np.full((2, 2), 44.0))
    assert [(item.start_hour, item.end_hour) for item in result.segments] == [
        (3, 6), (6, 9), (9, 12), (12, 15),
        (15, 18), (18, 21), (21, 24), (24, 27),
    ]
    assert sum(item.duration_hours for item in result.segments) == 24
    assert result.tiny_negative_count == 0


def test_overlapping_missing_and_duplicate_intervals_are_rejected():
    with pytest.raises(ValueError, match="overlapping"):
        validate_segment_coverage([(3, 9), (6, 12)], window_start_hour=3, window_end_hour=12)
    with pytest.raises(ValueError, match="missing"):
        reconstruct_accumulation_window(
            valid_messages()[:-1], window_start_hour=3, window_end_hour=27
        )
    with pytest.raises(ValueError, match="duplicate"):
        reconstruct_accumulation_window(
            valid_messages() + [message(0, 3, 1)],
            window_start_hour=3,
            window_end_hour=27,
        )


def test_material_negative_difference_is_rejected_and_tiny_negative_is_explicit():
    with pytest.raises(ValueError, match="materially negative"):
        reconstruct_accumulation_window(
            [message(0, 3, 3.0), message(0, 6, 2.0)],
            window_start_hour=3,
            window_end_hour=6,
        )
    result = reconstruct_accumulation_window(
        [message(0, 3, 1.0), message(0, 6, 1.0 - 5e-7)],
        window_start_hour=3,
        window_end_hour=6,
        negative_tolerance_mm=1e-6,
    )
    assert np.array_equal(result.rainfall_mm, np.zeros((2, 2)))
    assert result.tiny_negative_count == 4
    assert result.minimum_tolerated_negative_mm == pytest.approx(-5e-7)
    assert result.negative_tolerance_mm == 1e-6


def test_aligned_conservative_regridding_preserves_values_integral_and_mask():
    latitude = np.arange(10.0, 22.0 + 0.25, 0.25)
    longitude = np.arange(68.0, 80.0 + 0.25, 0.25)
    assert latitude.size == longitude.size == 49
    source = np.arange(49 * 49, dtype=float).reshape(49, 49) / 100
    valid_mask = np.ones_like(source, dtype=bool)
    valid_mask[:10, :12] = False
    weights = build_first_order_conservative_weights(
        latitude, longitude, latitude, longitude
    )
    target = weights.apply(source)
    assert np.allclose(target, source, rtol=0, atol=1e-12)
    assert np.array_equal(valid_mask, valid_mask.copy())
    source_integral = area_weighted_integral(source, latitude, longitude, valid_mask)
    target_integral = area_weighted_integral(target, latitude, longitude, valid_mask)
    assert target_integral == pytest.approx(source_integral, rel=1e-14)


def test_source_and_derived_manifests_retain_identity_hashes_and_block_training():
    digest_a = hashlib.sha256(b"noaa").hexdigest()
    digest_b = hashlib.sha256(b"imd").hexdigest()
    source = PilotSourceManifest(
        manifest_id="noaa-source",
        provider="NOAA/NCEP",
        official_url="https://example.test/noaa",
        retrieval_timestamp_utc=datetime(2026, 9, 19, tzinfo=timezone.utc),
        filename_or_object_key="apcp.grib2",
        byte_size=5,
        sha256=digest_a,
        source_type="forecast",
        license_or_terms_reference="official open-data terms",
        variable="apcp_sfc / tp",
        units="kg m**-2",
        grid={"type": "regular_ll"},
        time_coverage={"start_step": 3, "end_step": 27},
    )
    assert source.provider == "NOAA/NCEP"
    assert source.variable == "apcp_sfc / tp"

    derived = PilotDerivedManifest(
        manifest_id="pilot-pair",
        derived_artifact="pair.nc",
        derived_artifact_sha256=hashlib.sha256(b"pair").hexdigest(),
        source_manifest_hashes={"noaa_gefs": digest_a, "imd_rainfall": digest_b},
        processing_code_hashes={"code.py": hashlib.sha256(b"code").hexdigest()},
        window_definition={"duration_hours": 24},
        regridding_method="first-order conservative",
        weight_hash=hashlib.sha256(b"weights").hexdigest(),
        target_domain={"south": 10, "north": 22, "west": 68, "east": 80},
        target_grid={"shape": [49, 49]},
        qc_results={"status": "PASS"},
        training_eligible=False,
    )
    assert derived.training_eligible is False
    with pytest.raises(ValidationError):
        PilotDerivedManifest.model_validate(derived.model_dump() | {"training_eligible": True})

    prototype, metadata = load_source_dataset()
    readiness = assess_training_readiness(prototype, metadata)
    assert readiness.ready is False
    assert len(readiness.blockers) == 5


def test_checked_in_pilot_manifests_preserve_pairing_identity_and_block_training():
    repository_root = Path(__file__).resolve().parents[2]
    manifest_dir = repository_root / "data/manifests/phase1b/2019-07-15"
    noaa_path = manifest_dir / "noaa_gefsv12_2019071400_c00_apcp.json"
    imd_path = manifest_dir / "imd_rf25_2019.json"
    derived_path = manifest_dir / "derived_pair_2019-07-15.json"
    qc_path = manifest_dir / "qc_report_2019-07-15.json"

    noaa = PilotSourceManifest.model_validate_json(noaa_path.read_text(encoding="utf-8"))
    imd = PilotSourceManifest.model_validate_json(imd_path.read_text(encoding="utf-8"))
    derived = PilotDerivedManifest.model_validate_json(
        derived_path.read_text(encoding="utf-8")
    )
    qc = json.loads(qc_path.read_text(encoding="utf-8"))

    noaa_manifest_hash = hashlib.sha256(noaa_path.read_bytes()).hexdigest()
    imd_manifest_hash = hashlib.sha256(imd_path.read_bytes()).hexdigest()

    assert noaa.source_type == "forecast"
    assert noaa.variable == "apcp_sfc archive object / tp GRIB short name"
    assert noaa.units == "kg m**-2 normalized 1:1 to mm"
    assert noaa.time_coverage["target_window_leads"] == [3, 27]
    assert imd.source_type == "observation"
    assert imd.time_coverage["pilot_time_value"] == 43295.0
    assert derived.training_eligible is False
    assert derived.source_manifest_hashes == {
        "noaa_gefs": noaa_manifest_hash,
        "imd_rainfall": imd_manifest_hash,
    }
    assert derived.target_domain == {
        "south": 10.0,
        "north": 22.0,
        "west": 68.0,
        "east": 80.0,
    }
    assert derived.target_grid["shape"] == [49, 49]
    assert qc["timing"]["interval_equality"] is True
    initialization = datetime.fromisoformat(qc["timing"]["forecast_initialization_utc"])
    window_start = datetime.fromisoformat(qc["timing"]["forecast_window_start_utc"])
    window_end = datetime.fromisoformat(qc["timing"]["forecast_window_end_utc"])
    assert initialization < window_start < window_end
    assert (window_end - window_start).total_seconds() == 24 * 60 * 60
    assert qc["spatial"]["valid_target_cells"] == 1301
    assert qc["spatial"]["masked_target_cells"] == 1100
    assert qc["status"] == "PASS"


def test_phase1b_protected_artifact_history_and_versioned_supersession():
    repository_root = Path(__file__).resolve().parents[2]
    integrity_path = (
        repository_root
        / "data/manifests/phase1b/2019-07-15/protected_artifact_integrity.json"
    )
    integrity = json.loads(integrity_path.read_text(encoding="utf-8"))
    assert integrity["status"] == "PASS"
    assert integrity["unchanged_count"] == len(integrity["protected_artifacts"]) == 18
    supersession_path = integrity_path.with_name("protected_artifact_supersession_v1.json")
    supersession = json.loads(supersession_path.read_text(encoding="utf-8"))
    assert supersession["record_type"] == "append_only_protected_artifact_supersession"
    assert supersession["historical_lock_is_unchanged"] is True
    assert hashlib.sha256(integrity_path.read_bytes()).hexdigest() == supersession["historical_lock_sha256"]
    superseded = supersession["superseded_artifacts"]
    assert set(superseded) == {"backend/app/api/routes.py", "backend/app/data/readiness.py"}
    unchanged_count = 0
    for relative_path, expected_hash in integrity["protected_artifacts"].items():
        actual_hash = hashlib.sha256((repository_root / relative_path).read_bytes()).hexdigest()
        if relative_path in superseded:
            assert superseded[relative_path]["phase1b_sha256"] == expected_hash
            assert superseded[relative_path]["current_sha256"] == actual_hash
        else:
            assert actual_hash == expected_hash, relative_path
            unchanged_count += 1
    assert unchanged_count == supersession["current_verification"]["baseline_protected_artifacts_unchanged"] == 16
    assert len(superseded) == supersession["current_verification"]["superseded_by_versioned_current_hash"] == 2
