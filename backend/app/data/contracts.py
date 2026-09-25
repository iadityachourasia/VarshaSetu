"""Canonical source and grid metadata contracts for Phase 1A.

These models describe data that may eventually enter the scientific pipeline.
They do not make a source training-eligible and are intentionally not wired to
the training or API paths.
"""

from __future__ import annotations

import hashlib
import re
from datetime import date, datetime, time, timedelta, timezone
from enum import Enum
from pathlib import Path
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
KNOWN_UNITS = {
    "%",
    "1",
    "K",
    "Pa",
    "hPa",
    "kg kg-1",
    "kg m-2",
    "kg m**-2",
    "m",
    "m s-1",
    "m2 s-2",
    "mm",
}


class DataKind(str, Enum):
    FORECAST = "forecast"
    OBSERVATION = "observation"
    REANALYSIS = "reanalysis"
    STATIC = "static"


class BoundingBox(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    south: float = Field(ge=-90, le=90)
    north: float = Field(ge=-90, le=90)
    west: float = Field(ge=-180, le=180)
    east: float = Field(ge=-180, le=180)

    @model_validator(mode="after")
    def validate_order(self) -> Self:
        if self.south >= self.north:
            raise ValueError("south must be less than north")
        if self.west >= self.east:
            raise ValueError("west must be less than east; dateline grids need an explicit convention")
        return self


class GridDefinition(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    grid_id: str = Field(min_length=1)
    crs: str = Field(min_length=1)
    latitude_spacing_degrees: float = Field(gt=0, le=180)
    longitude_spacing_degrees: float = Field(gt=0, le=360)
    bounds: BoundingBox
    latitude_order: str
    longitude_convention: str

    @field_validator("latitude_order")
    @classmethod
    def validate_latitude_order(cls, value: str) -> str:
        if value not in {"ascending", "descending"}:
            raise ValueError("latitude_order must be ascending or descending")
        return value

    @field_validator("longitude_convention")
    @classmethod
    def validate_longitude_convention(cls, value: str) -> str:
        if value not in {"-180_to_180", "0_to_360"}:
            raise ValueError("unsupported longitude convention")
        return value


def _require_utc(value: datetime, field_name: str) -> datetime:
    if value.tzinfo is None or value.utcoffset() != timedelta(0):
        raise ValueError(f"{field_name} must be timezone-aware UTC")
    return value


def _require_http_url(value: str, field_name: str) -> str:
    if not value.startswith(("https://", "http://")):
        raise ValueError(f"{field_name} must be an HTTP(S) URL")
    return value


class ForecastGridRecord(BaseModel):
    """Metadata required for one forecast variable/grid/time record."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    source: str = Field(min_length=1)
    source_documentation_url: str = Field(min_length=1)
    model_name: str = Field(min_length=1)
    model_version: str = Field(min_length=1)
    ensemble_member: str = Field(min_length=1)
    initialization_time_utc: datetime
    valid_time_utc: datetime
    lead_hours: int = Field(gt=0)
    accumulation_start_utc: datetime | None = None
    accumulation_end_utc: datetime | None = None
    accumulation_hours: int | None = Field(default=None, gt=0)
    grid_definition: GridDefinition
    variable: str = Field(min_length=1)
    level: str = Field(min_length=1)
    units: str
    available_at_issue_time: bool

    @field_validator(
        "initialization_time_utc",
        "valid_time_utc",
        "accumulation_start_utc",
        "accumulation_end_utc",
    )
    @classmethod
    def validate_utc(cls, value: datetime | None, info) -> datetime | None:
        return None if value is None else _require_utc(value, info.field_name)

    @field_validator("source_documentation_url")
    @classmethod
    def validate_documentation_url(cls, value: str) -> str:
        return _require_http_url(value, "source_documentation_url")

    @field_validator("units")
    @classmethod
    def validate_units(cls, value: str) -> str:
        if value not in KNOWN_UNITS:
            raise ValueError(f"unknown units: {value!r}")
        return value

    @model_validator(mode="after")
    def validate_timing_and_availability(self) -> Self:
        if self.initialization_time_utc >= self.valid_time_utc:
            raise ValueError("initialization_time_utc must precede valid_time_utc")
        actual_lead = (self.valid_time_utc - self.initialization_time_utc).total_seconds() / 3600
        if actual_lead != self.lead_hours:
            raise ValueError("lead_hours must equal valid_time_utc - initialization_time_utc")
        if not self.available_at_issue_time:
            raise ValueError("operational forecast features must be available at issue time")

        accumulation_fields = (
            self.accumulation_start_utc,
            self.accumulation_end_utc,
            self.accumulation_hours,
        )
        if any(value is not None for value in accumulation_fields):
            if any(value is None for value in accumulation_fields):
                raise ValueError("all accumulation fields must be supplied together")
            if self.accumulation_start_utc >= self.accumulation_end_utc:
                raise ValueError("accumulation_start_utc must precede accumulation_end_utc")
            actual_hours = (
                self.accumulation_end_utc - self.accumulation_start_utc
            ).total_seconds() / 3600
            if actual_hours != self.accumulation_hours:
                raise ValueError("accumulation_hours does not match the accumulation timestamps")
            if self.accumulation_end_utc != self.valid_time_utc:
                raise ValueError("rainfall valid_time_utc must equal accumulation_end_utc")
        return self


class ObservationGridRecord(BaseModel):
    """Metadata required for one rainfall reference grid/day."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    source: str = Field(min_length=1)
    source_documentation_url: str = Field(min_length=1)
    product: str = Field(min_length=1)
    version: str = Field(min_length=1)
    valid_date: date
    accumulation_start_utc: datetime
    accumulation_end_utc: datetime
    accumulation_hours: int = Field(gt=0)
    grid_definition: GridDefinition
    rainfall_units: str
    quality_status: str = Field(min_length=1)
    missing_value_policy: str = Field(min_length=1)

    @field_validator("accumulation_start_utc", "accumulation_end_utc")
    @classmethod
    def validate_utc(cls, value: datetime, info) -> datetime:
        return _require_utc(value, info.field_name)

    @field_validator("source_documentation_url")
    @classmethod
    def validate_documentation_url(cls, value: str) -> str:
        return _require_http_url(value, "source_documentation_url")

    @field_validator("rainfall_units")
    @classmethod
    def validate_rainfall_units(cls, value: str) -> str:
        if value != "mm":
            raise ValueError("canonical rainfall_units must be mm")
        return value

    @model_validator(mode="after")
    def validate_window(self) -> Self:
        if self.accumulation_start_utc >= self.accumulation_end_utc:
            raise ValueError("accumulation_start_utc must precede accumulation_end_utc")
        actual_hours = (
            self.accumulation_end_utc - self.accumulation_start_utc
        ).total_seconds() / 3600
        if actual_hours != self.accumulation_hours:
            raise ValueError("accumulation_hours does not match the accumulation timestamps")
        if self.accumulation_end_utc.date() != self.valid_date:
            raise ValueError("valid_date must be the UTC date on which the observation window ends")
        return self


class SourceFileManifest(BaseModel):
    """Immutable provenance record for one acquired source file or byte range."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    dataset_id: str = Field(min_length=1)
    provider: str = Field(min_length=1)
    source_url: str = Field(min_length=1)
    retrieval_date: date
    filename: str = Field(min_length=1)
    sha256: str
    byte_size: int = Field(gt=0)
    data_type: DataKind
    product: str = Field(min_length=1)
    version: str = Field(min_length=1)
    model_name: str | None = None
    initialization_time_utc: datetime | None = None
    lead_hours: list[int] = Field(default_factory=list)
    variable: str = Field(min_length=1)
    level: str = Field(min_length=1)
    units: str
    spatial_resolution: str = Field(min_length=1)
    temporal_resolution: str = Field(min_length=1)
    license_or_terms: str = Field(min_length=1)
    request_or_subset: str = Field(min_length=1)
    provenance_status: str = Field(min_length=1)

    @field_validator("sha256")
    @classmethod
    def validate_sha256(cls, value: str) -> str:
        normalized = value.lower()
        if not SHA256_PATTERN.fullmatch(normalized):
            raise ValueError("sha256 must contain exactly 64 hexadecimal characters")
        return normalized

    @field_validator("source_url")
    @classmethod
    def validate_source_url(cls, value: str) -> str:
        return _require_http_url(value, "source_url")

    @field_validator("units")
    @classmethod
    def validate_units(cls, value: str) -> str:
        if value not in KNOWN_UNITS:
            raise ValueError(f"unknown units: {value!r}")
        return value

    @field_validator("initialization_time_utc")
    @classmethod
    def validate_initialization_utc(cls, value: datetime | None) -> datetime | None:
        return None if value is None else _require_utc(value, "initialization_time_utc")

    @model_validator(mode="after")
    def validate_kind_specific_fields(self) -> Self:
        if self.data_type == DataKind.FORECAST:
            if not self.model_name or self.initialization_time_utc is None or not self.lead_hours:
                raise ValueError("forecast manifests require model_name, initialization_time_utc, and lead_hours")
        elif self.model_name is not None or self.initialization_time_utc is not None or self.lead_hours:
            raise ValueError("forecast identity fields are only valid for forecast manifests")
        return self


class AccumulatedPrecipitationMessage(BaseModel):
    """A decoded precipitation message identified by its GRIB step range."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    start_hour: int = Field(ge=0)
    end_hour: int = Field(gt=0)
    value_mm: float = Field(ge=0)

    @model_validator(mode="after")
    def validate_range(self) -> Self:
        if self.start_hour >= self.end_hour:
            raise ValueError("start_hour must precede end_hour")
        return self


def imd_daily_window(valid_date: date) -> tuple[datetime, datetime]:
    """Return the IMD 08:30 IST-to-08:30 IST daily window in UTC."""

    end = datetime.combine(valid_date, time(hour=3), tzinfo=timezone.utc)
    return end - timedelta(hours=24), end


def validate_pairing_window(
    forecast: ForecastGridRecord, observation: ObservationGridRecord
) -> None:
    """Require an exact temporal and target-grid match for a rainfall pair."""

    if forecast.accumulation_start_utc is None or forecast.accumulation_end_utc is None:
        raise ValueError("forecast record has no accumulation window")
    if (
        forecast.accumulation_start_utc != observation.accumulation_start_utc
        or forecast.accumulation_end_utc != observation.accumulation_end_utc
        or forecast.accumulation_hours != observation.accumulation_hours
    ):
        raise ValueError("forecast and observation accumulation windows do not match exactly")
    if forecast.grid_definition.grid_id != observation.grid_definition.grid_id:
        raise ValueError("forecast and observation must be on the same validated target grid")


def reconstruct_three_hour_increments(
    messages: list[AccumulatedPrecipitationMessage],
    *,
    window_start_hour: int,
    window_end_hour: int,
    negative_tolerance_mm: float = 1e-6,
) -> list[float]:
    """Reconstruct 3-hour amounts from exact or nested GEFS step ranges.

    GEFSv12 reforecast precipitation alternates 3-hour and 6-hour intervals in
    the first ten days. A later nested total (for example 0--6 h) is differenced
    from the earlier total (0--3 h). Missing or materially negative increments
    fail closed.
    """

    if window_start_hour < 0 or window_end_hour <= window_start_hour:
        raise ValueError("invalid reconstruction window")
    if (window_end_hour - window_start_hour) % 3:
        raise ValueError("window must be divisible into complete 3-hour intervals")

    by_range = {(message.start_hour, message.end_hour): message.value_mm for message in messages}
    increments: list[float] = []
    for interval_start in range(window_start_hour, window_end_hour, 3):
        interval_end = interval_start + 3
        exact = by_range.get((interval_start, interval_end))
        if exact is not None:
            increment = exact
        else:
            candidates = [
                start
                for start, end in by_range
                if end == interval_end and start < interval_start and (start, interval_start) in by_range
            ]
            if not candidates:
                raise ValueError(f"missing precipitation messages for hours {interval_start}--{interval_end}")
            nested_start = max(candidates)
            increment = by_range[(nested_start, interval_end)] - by_range[(nested_start, interval_start)]

        if increment < -negative_tolerance_mm:
            raise ValueError(f"negative reconstructed precipitation for hours {interval_start}--{interval_end}")
        increments.append(max(0.0, increment))
    return increments


def validate_file_checksum(path: str | Path, expected_sha256: str) -> None:
    expected = expected_sha256.lower()
    if not SHA256_PATTERN.fullmatch(expected):
        raise ValueError("expected_sha256 must contain exactly 64 hexadecimal characters")
    digest = hashlib.sha256(Path(path).read_bytes()).hexdigest()
    if digest != expected:
        raise ValueError(f"SHA-256 mismatch for {Path(path).name}: expected {expected}, got {digest}")
