"""Validated manifest models for the Phase 1C monthly acquisition pilot."""

from __future__ import annotations

import re
import calendar
from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
CaseStatus = Literal["PASS", "FAIL", "BLOCKED", "PARTIAL"]


def _sha256(value: str) -> str:
    lowered = value.lower()
    if not SHA256_PATTERN.fullmatch(lowered):
        raise ValueError("expected a 64-character SHA-256")
    return lowered


class MonthlyCollectionManifest(BaseModel):
    model_config = ConfigDict(extra="allow", frozen=True)

    collection_id: str = Field(min_length=1)
    period: dict
    forecast_provider: str = Field(min_length=1)
    observation_provider: str = Field(min_length=1)
    expected_initializations: int = Field(gt=0)
    observed_initializations: int = Field(ge=0)
    rainfall_products: list[str] = Field(min_length=1)
    ensemble_members: list[str] = Field(min_length=1)
    atmospheric_fields: list[str] = Field(min_length=1)
    target_domain: dict
    context_domain: dict
    source_bytes: dict
    processed_bytes: dict
    child_manifest_hashes: dict[str, str]
    failed_cases: list[dict]
    qc_summary: dict
    training_eligible: Literal[False]

    @field_validator("child_manifest_hashes")
    @classmethod
    def validate_hashes(cls, value: dict[str, str]) -> dict[str, str]:
        if not value:
            raise ValueError("monthly collection requires child lineage hashes")
        return {key: _sha256(digest) for key, digest in value.items()}

    @model_validator(mode="after")
    def validate_counts(self) -> Self:
        if self.observed_initializations > self.expected_initializations:
            raise ValueError("observed initializations exceed expected initializations")
        month = self.period.get("month", "")
        if not re.fullmatch(r"\d{4}-\d{2}", month):
            raise ValueError("period month must use YYYY-MM")
        year_value, month_value = map(int, month.split("-"))
        if not 1 <= month_value <= 12:
            raise ValueError("period month is invalid")
        expected_days = calendar.monthrange(year_value, month_value)[1]
        if self.expected_initializations != expected_days:
            raise ValueError("expected initializations must equal calendar month days")
        return self
