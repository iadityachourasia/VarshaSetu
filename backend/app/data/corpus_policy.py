"""Fail-closed scientific admission rules for the frozen historical corpus."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Iterable, Mapping


class AnomalyStatus(StrEnum):
    PACKING_QUANTIZATION_EXPLAINED = "PACKING_QUANTIZATION_EXPLAINED"
    SOURCE_INCONSISTENCY = "SOURCE_INCONSISTENCY"
    RECONSTRUCTION_BUG = "RECONSTRUCTION_BUG"
    DECODER_BUG = "DECODER_BUG"
    UNRESOLVED = "UNRESOLVED"


class MonthAdmission(StrEnum):
    MONTH_ACCEPTED = "MONTH_ACCEPTED"
    MONTH_ACCEPTED_WITH_QUARANTINED_SAMPLES = "MONTH_ACCEPTED_WITH_QUARANTINED_SAMPLES"
    MONTH_REJECTED = "MONTH_REJECTED"


def packing_quantum(binary_scale_factor: int, decimal_scale_factor: int) -> float:
    """Return the GRIB decoded-value spacing 2**E * 10**-D."""
    return (2.0 ** binary_scale_factor) * (10.0 ** (-decimal_scale_factor))


def maximum_independent_difference_error(
    first_binary_scale: int,
    first_decimal_scale: int,
    second_binary_scale: int,
    second_decimal_scale: int,
) -> float:
    """Worst-case error for a difference of two independently rounded fields."""
    return (
        packing_quantum(first_binary_scale, first_decimal_scale)
        + packing_quantum(second_binary_scale, second_decimal_scale)
    ) / 2.0


def classify_negative_increment(
    increment_mm: float,
    *,
    maximum_packing_error_mm: float,
) -> AnomalyStatus:
    """Classify cause using the representation bound, not admission policy."""
    if increment_mm >= 0:
        raise ValueError("classification requires a negative increment")
    if maximum_packing_error_mm < 0:
        raise ValueError("error bound must be nonnegative")
    magnitude = abs(increment_mm)
    if magnitude <= maximum_packing_error_mm:
        return AnomalyStatus.PACKING_QUANTIZATION_EXPLAINED
    return AnomalyStatus.SOURCE_INCONSISTENCY


def negative_increment_admissible(
    increment_mm: float,
    *,
    maximum_packing_error_mm: float,
    operational_tolerance_mm: float = 0.1,
) -> bool:
    """Apply both causal explanation and the independent operational cap."""
    if increment_mm >= 0:
        return True
    if maximum_packing_error_mm < 0 or operational_tolerance_mm < 0:
        raise ValueError("error bounds and tolerance must be nonnegative")
    magnitude = abs(increment_mm)
    return magnitude <= maximum_packing_error_mm and magnitude <= operational_tolerance_mm


@dataclass(frozen=True)
class EligibilityInputs:
    source_valid: bool
    control_rain_valid: bool
    perturbation_rain_valid: Mapping[str, bool]
    observation_valid: bool
    atmospheric_bundle_valid: bool
    timing_valid: bool
    spatial_alignment_valid: bool
    spatial_mask_valid: bool
    extreme_forecast_inputs_valid: bool = True


def compute_eligibility(inputs: EligibilityInputs) -> dict[str, bool]:
    expected = {"p01", "p02", "p03", "p04"}
    if set(inputs.perturbation_rain_valid) != expected:
        raise ValueError("perturbation validity must contain exactly p01-p04")

    pair_valid = (
        inputs.source_valid
        and inputs.control_rain_valid
        and inputs.observation_valid
        and inputs.timing_valid
        and inputs.spatial_alignment_valid
    )
    control = pair_valid and inputs.atmospheric_bundle_valid
    full_ensemble = pair_valid and all(inputs.perturbation_rain_valid.values())
    regime = inputs.source_valid and inputs.atmospheric_bundle_valid and inputs.timing_valid
    extreme = pair_valid and inputs.extreme_forecast_inputs_valid
    fss = pair_valid and inputs.spatial_mask_valid
    any_use = control or full_ensemble or regime or extreme or fss
    return {
        "SOURCE_VALID": inputs.source_valid,
        "PAIR_VALID": pair_valid,
        "CONTROL_MODEL_ELIGIBLE": control,
        "FULL_ENSEMBLE_ELIGIBLE": full_ensemble,
        "REGIME_ELIGIBLE": regime,
        "EXTREME_EVENT_ELIGIBLE": extreme,
        "FSS_ELIGIBLE": fss,
        "REJECTED": not any_use,
    }


def monthly_admission(*, source_contract_valid: bool, lineage_complete: bool, invalid_units: int) -> MonthAdmission:
    if invalid_units < 0:
        raise ValueError("invalid_units cannot be negative")
    if not source_contract_valid or not lineage_complete:
        return MonthAdmission.MONTH_REJECTED
    if invalid_units:
        return MonthAdmission.MONTH_ACCEPTED_WITH_QUARANTINED_SAMPLES
    return MonthAdmission.MONTH_ACCEPTED


def shared_case_intersection(case_sets: Iterable[Iterable[str]]) -> tuple[str, ...]:
    normalized = [set(items) for items in case_sets]
    if len(normalized) < 2:
        raise ValueError("a scientific comparison requires at least two model case sets")
    return tuple(sorted(set.intersection(*normalized)))
