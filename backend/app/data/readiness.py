from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Iterable

import pandas as pd

try:
    from backend.app.core.config import TARGET_ACCUMULATION_HOURS
except ModuleNotFoundError:
    from app.core.config import TARGET_ACCUMULATION_HOURS


class ScientificReadinessError(RuntimeError):
    """Raised when a scientific workflow would rely on unresolved evidence."""

    def __init__(self, blockers: Iterable[str]):
        self.blockers = list(blockers)
        super().__init__("Scientific workflow blocked: " + "; ".join(self.blockers))


@dataclass(frozen=True)
class ReadinessStatus:
    ready: bool
    mode: str
    blockers: list[str]
    resolved_controls: list[str]

    def to_dict(self) -> dict:
        return asdict(self)


def assess_training_readiness(df: pd.DataFrame, metadata: dict) -> ReadinessStatus:
    blockers: list[str] = []

    if metadata.get("provenance_status") != "verified":
        blockers.append(
            "Dataset providers, licenses, and forecast/observation lineage are unverified."
        )
    if not metadata.get("training_eligible", False):
        blockers.append("The configured dataset manifest marks this dataset ineligible for training.")
    if "regime_id" not in df.columns:
        blockers.append(
            "regime_id is absent and no reproducible generator is connected to this legacy dataset."
        )

    required_forecast_metadata = {
        "forecast_source",
        "model_version",
        "init_time_utc",
        "valid_time_utc",
        "lead_hours",
        "accumulation_hours",
    }
    missing_forecast_metadata = sorted(required_forecast_metadata.difference(df.columns))
    if missing_forecast_metadata:
        blockers.append(
            "Forecast identity/timing metadata is missing: "
            + ", ".join(missing_forecast_metadata)
            + "."
        )

    if TARGET_ACCUMULATION_HOURS != 24:
        blockers.append(
            "The target is 6-hour rainfall; 24-hour heavy/very-heavy categories cannot be trained or evaluated."
        )

    return ReadinessStatus(
        ready=not blockers,
        mode="scientific" if not blockers else "stabilization_blocked",
        blockers=blockers,
        resolved_controls=[
            "Dataset path resolves from the repository or explicit environment variables.",
            "Dataset checksum, row count, and schema are verified against a checked-in manifest.",
            "Unverified contemporaneous atmospheric fields are excluded from the feature builder.",
            "Legacy model/report artifacts are not loaded against a mismatched dataset.",
        ],
    )


def require_training_ready(df: pd.DataFrame, metadata: dict) -> None:
    status = assess_training_readiness(df, metadata)
    if not status.ready:
        raise ScientificReadinessError(status.blockers)
