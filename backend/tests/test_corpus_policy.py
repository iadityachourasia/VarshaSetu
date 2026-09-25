from __future__ import annotations

import json
from pathlib import Path

import pytest
import numpy as np
from pydantic import ValidationError

from backend.app.data.corpus_models import DatasetFreezeManifest
from backend.app.data.accumulation import GriddedAccumulationMessage, reconstruct_accumulation_window
from backend.app.data.corpus_policy import (
    AnomalyStatus,
    EligibilityInputs,
    MonthAdmission,
    classify_negative_increment,
    compute_eligibility,
    maximum_independent_difference_error,
    monthly_admission,
    negative_increment_admissible,
    packing_quantum,
    shared_case_intersection,
)


ROOT = Path(__file__).resolve().parents[2]
PLAN = ROOT / "data/manifests/corpus/varshasetu-gefs12r-imd025-jjas-2000-2019-v1.plan.json"


def valid_inputs(**overrides) -> EligibilityInputs:
    values = {
        "source_valid": True,
        "control_rain_valid": True,
        "perturbation_rain_valid": {member: True for member in ("p01", "p02", "p03", "p04")},
        "observation_valid": True,
        "atmospheric_bundle_valid": True,
        "timing_valid": True,
        "spatial_alignment_valid": True,
        "spatial_mask_valid": True,
    }
    values.update(overrides)
    return EligibilityInputs(**values)


def test_actual_packing_bound_rejects_july_anomaly() -> None:
    assert packing_quantum(0, 1) == pytest.approx(0.1)
    assert packing_quantum(1, 1) == pytest.approx(0.2)
    bound = maximum_independent_difference_error(0, 1, 1, 1)
    assert bound == pytest.approx(0.15)
    assert classify_negative_increment(-0.2, maximum_packing_error_mm=bound) == AnomalyStatus.SOURCE_INCONSISTENCY


def test_small_residue_must_satisfy_packing_bound_and_operational_cap() -> None:
    assert classify_negative_increment(-0.05, maximum_packing_error_mm=0.075) == AnomalyStatus.PACKING_QUANTIZATION_EXPLAINED
    assert classify_negative_increment(-0.11, maximum_packing_error_mm=0.2) == AnomalyStatus.PACKING_QUANTIZATION_EXPLAINED
    assert negative_increment_admissible(-0.05, maximum_packing_error_mm=0.075)
    assert not negative_increment_admissible(-0.11, maximum_packing_error_mm=0.2)


def test_reconstruction_uses_pair_packing_bound_not_only_global_cap() -> None:
    messages = [
        GriddedAccumulationMessage(0, 3, np.array([[1.08]]), "prefix", 0.05),
        GriddedAccumulationMessage(0, 6, np.array([[1.0]]), "total", 0.10),
    ]
    with pytest.raises(ValueError, match="materially negative"):
        reconstruct_accumulation_window(
            messages, window_start_hour=3, window_end_hour=6,
            negative_tolerance_mm=0.1,
        )


def test_missing_perturbation_preserves_control_only_eligibility() -> None:
    tiers = compute_eligibility(valid_inputs(perturbation_rain_valid={"p01": False, "p02": True, "p03": True, "p04": True}))
    assert tiers["CONTROL_MODEL_ELIGIBLE"] is True
    assert tiers["FULL_ENSEMBLE_ELIGIBLE"] is False
    assert tiers["REGIME_ELIGIBLE"] is True


@pytest.mark.parametrize(
    ("overrides", "false_tiers"),
    [
        ({"control_rain_valid": False}, {"PAIR_VALID", "CONTROL_MODEL_ELIGIBLE", "FULL_ENSEMBLE_ELIGIBLE", "EXTREME_EVENT_ELIGIBLE", "FSS_ELIGIBLE"}),
        ({"atmospheric_bundle_valid": False}, {"CONTROL_MODEL_ELIGIBLE", "REGIME_ELIGIBLE"}),
        ({"observation_valid": False}, {"PAIR_VALID", "CONTROL_MODEL_ELIGIBLE", "FULL_ENSEMBLE_ELIGIBLE", "EXTREME_EVENT_ELIGIBLE", "FSS_ELIGIBLE"}),
    ],
)
def test_component_failures_are_scoped(overrides: dict, false_tiers: set[str]) -> None:
    tiers = compute_eligibility(valid_inputs(**overrides))
    assert all(tiers[tier] is False for tier in false_tiers)


def test_month_can_be_accepted_with_explicit_quarantine() -> None:
    assert monthly_admission(source_contract_valid=True, lineage_complete=True, invalid_units=1) == MonthAdmission.MONTH_ACCEPTED_WITH_QUARANTINED_SAMPLES
    assert monthly_admission(source_contract_valid=True, lineage_complete=True, invalid_units=0) == MonthAdmission.MONTH_ACCEPTED
    assert monthly_admission(source_contract_valid=False, lineage_complete=True, invalid_units=0) == MonthAdmission.MONTH_REJECTED


def test_model_comparison_uses_shared_case_intersection() -> None:
    assert shared_case_intersection([{"a", "b", "c"}, {"b", "c", "d"}, {"b", "e"}]) == ("b",)
    with pytest.raises(ValueError):
        shared_case_intersection([{"a"}])


def test_dataset_plan_schema_and_immutability() -> None:
    manifest = DatasetFreezeManifest.model_validate(json.loads(PLAN.read_text(encoding="utf-8")))
    assert manifest.acquisition_status == "NOT_STARTED"
    assert manifest.training_eligible is False
    assert manifest.expected_initializations == 2440
    with pytest.raises(ValidationError):
        manifest.dataset_version = "mutated"


def test_dataset_plan_rejects_semantic_mutation() -> None:
    payload = json.loads(PLAN.read_text(encoding="utf-8"))
    payload["rainfall_products"]["day2_24h"] = [24, 48]
    with pytest.raises(ValidationError):
        DatasetFreezeManifest.model_validate(payload)


def test_acquisition_plan_validation_is_conservative() -> None:
    payload = json.loads(PLAN.read_text(encoding="utf-8"))
    payload["concurrency"]["noaa_range_requests"] = 20
    with pytest.raises(ValidationError):
        DatasetFreezeManifest.model_validate(payload)
    payload = json.loads(PLAN.read_text(encoding="utf-8"))
    payload["retry_policy"]["maximum_attempts"] = 99
    with pytest.raises(ValidationError):
        DatasetFreezeManifest.model_validate(payload)
