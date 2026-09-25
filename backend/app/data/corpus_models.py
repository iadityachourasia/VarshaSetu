"""Schema for the immutable VarshaSetu historical-corpus plan manifest."""

from __future__ import annotations

from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator


DATASET_VERSION = "varshasetu-gefs12r-imd025-jjas-2000-2019-v1"


class DatasetFreezeManifest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["1.0.0"]
    dataset_version: Literal[DATASET_VERSION]
    acquisition_status: Literal["NOT_STARTED"]
    training_eligible: Literal[False]
    forecast_source: dict
    forecast_version: str
    observation_source: dict
    observation_product: str
    years: list[int] = Field(min_length=20, max_length=20)
    season: dict
    initialization_cycle: Literal["00Z"]
    expected_initializations: Literal[2440]
    rainfall_products: dict
    ensemble_members: list[str]
    atmospheric_fields: dict
    target_domain: dict
    context_domain: dict
    target_grid: dict
    context_grid: dict
    accumulation_contract: dict
    regridding_policy: dict
    negative_residue_policy: dict
    eligibility_policy: dict
    monthly_qc_policy: dict
    storage_format: dict
    chunking: dict
    acquisition_unit: dict
    concurrency: dict
    retry_policy: dict
    split_candidates: dict
    fairness_policy: dict

    @model_validator(mode="after")
    def validate_frozen_contract(self) -> Self:
        if self.years != list(range(2000, 2020)):
            raise ValueError("v1 years must be exactly 2000-2019")
        if self.season.get("initialization_dates") != "June 1 through September 30 inclusive":
            raise ValueError("v1 initialization season must be exact JJAS")
        if self.ensemble_members != ["c00", "p01", "p02", "p03", "p04"]:
            raise ValueError("v1 members must be c00 and p01-p04 in canonical order")
        if self.rainfall_products != {
            "day1_24h": [3, 27],
            "day2_24h": [27, 51],
            "day3_24h": [51, 75],
        }:
            raise ValueError("v1 rainfall windows are immutable")
        if self.atmospheric_fields.get("leads_hours") != [24, 48, 72]:
            raise ValueError("v1 atmospheric leads are immutable")
        if self.concurrency.get("noaa_range_requests") not in (2, 3, 4):
            raise ValueError("NOAA concurrency must remain conservative (2-4)")
        if self.retry_policy.get("maximum_attempts") != 5:
            raise ValueError("v1 retry maximum must be five attempts")
        return self
