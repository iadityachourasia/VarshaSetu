"""Machine-readable provenance models for the one-window Phase 1B pilot."""

from __future__ import annotations

import re
from datetime import datetime, timedelta
from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")


def _hash(value: str) -> str:
    value = value.lower()
    if not SHA256_PATTERN.fullmatch(value):
        raise ValueError("expected a 64-character SHA-256")
    return value


class PilotSourceManifest(BaseModel):
    model_config = ConfigDict(extra="allow", frozen=True)

    manifest_id: str = Field(min_length=1)
    provider: str = Field(min_length=1)
    official_url: str = Field(pattern=r"^https?://")
    retrieval_timestamp_utc: datetime
    filename_or_object_key: str = Field(min_length=1)
    byte_size: int = Field(gt=0)
    sha256: str
    source_type: Literal["forecast", "observation"]
    license_or_terms_reference: str = Field(min_length=1)
    variable: str = Field(min_length=1)
    units: str = Field(min_length=1)
    grid: dict
    time_coverage: dict

    @field_validator("sha256")
    @classmethod
    def validate_hash(cls, value: str) -> str:
        return _hash(value)

    @field_validator("retrieval_timestamp_utc")
    @classmethod
    def validate_utc(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() != timedelta(0):
            raise ValueError("retrieval_timestamp_utc must be timezone-aware UTC")
        return value


class PilotDerivedManifest(BaseModel):
    model_config = ConfigDict(extra="allow", frozen=True)

    manifest_id: str = Field(min_length=1)
    derived_artifact: str = Field(min_length=1)
    derived_artifact_sha256: str
    source_manifest_hashes: dict[str, str]
    processing_code_hashes: dict[str, str]
    window_definition: dict
    regridding_method: str = Field(min_length=1)
    weight_hash: str
    target_domain: dict
    target_grid: dict
    qc_results: dict
    training_eligible: Literal[False]

    @field_validator("derived_artifact_sha256", "weight_hash")
    @classmethod
    def validate_hash(cls, value: str) -> str:
        return _hash(value)

    @field_validator("source_manifest_hashes", "processing_code_hashes")
    @classmethod
    def validate_hash_map(cls, value: dict[str, str]) -> dict[str, str]:
        if not value:
            raise ValueError("lineage hash map cannot be empty")
        return {name: _hash(hash_value) for name, hash_value in value.items()}

    @model_validator(mode="after")
    def require_source_lineage(self) -> Self:
        required = {"noaa_gefs", "imd_rainfall"}
        if not required.issubset(self.source_manifest_hashes):
            raise ValueError("derived pilot manifest requires NOAA and IMD lineage")
        return self
