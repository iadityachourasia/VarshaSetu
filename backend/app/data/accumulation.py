"""Fail-closed reconstruction of gridded accumulated precipitation windows."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class GriddedAccumulationMessage:
    start_hour: int
    end_hour: int
    values_mm: np.ndarray
    source_id: str
    packing_quantum_mm: float | None = None

    def __post_init__(self) -> None:
        if self.start_hour < 0 or self.start_hour >= self.end_hour:
            raise ValueError("message step range is invalid")
        values = np.asarray(self.values_mm, dtype=float)
        if values.ndim != 2:
            raise ValueError("precipitation message must contain a 2-D grid")
        if not np.isfinite(values).all():
            raise ValueError("precipitation message contains non-finite values")
        if (values < 0).any():
            raise ValueError("source precipitation message contains negative values")
        if self.packing_quantum_mm is not None and self.packing_quantum_mm <= 0:
            raise ValueError("packing quantum must be positive")
        object.__setattr__(self, "values_mm", values)


@dataclass(frozen=True)
class CoverageSegment:
    start_hour: int
    end_hour: int
    duration_hours: int
    source_ids: tuple[str, ...]
    operation: str
    negative_tolerance_mm: float


@dataclass(frozen=True)
class AccumulationResult:
    rainfall_mm: np.ndarray
    segments: tuple[CoverageSegment, ...]
    tiny_negative_count: int
    minimum_tolerated_negative_mm: float | None
    negative_tolerance_mm: float


@dataclass(frozen=True)
class CanonicalCoverageSegment:
    start_hour: int
    end_hour: int
    duration_hours: int
    source_ids: tuple[str, ...]
    operation: str
    packing_error_bound_mm: float
    normalized_negative_count: int
    minimum_normalized_negative_mm: float | None


@dataclass(frozen=True)
class CanonicalAccumulationResult:
    rainfall_mm: np.ndarray
    segments: tuple[CanonicalCoverageSegment, ...]
    subtraction_count: int
    normalized_negative_count: int
    minimum_normalized_negative_mm: float | None


def validate_segment_coverage(
    segments: list[tuple[int, int]], *, window_start_hour: int, window_end_hour: int
) -> None:
    """Require one exact, gap-free, non-overlapping union of a target window."""

    if window_start_hour >= window_end_hour:
        raise ValueError("invalid target window")
    ordered = sorted(segments)
    cursor = window_start_hour
    for start, end in ordered:
        if start < cursor:
            raise ValueError("overlapping accumulation segments")
        if start > cursor:
            raise ValueError("missing accumulation segment")
        if end <= start:
            raise ValueError("segment duration must be positive")
        cursor = end
    if cursor != window_end_hour:
        raise ValueError("missing accumulation segment")


def reconstruct_accumulation_window(
    messages: list[GriddedAccumulationMessage],
    *,
    window_start_hour: int,
    window_end_hour: int,
    segment_hours: int = 3,
    negative_tolerance_mm: float = 1e-6,
) -> AccumulationResult:
    """Reconstruct exact increments from direct or nested interval totals.

    GEFSv12 days 1--10 alternate direct three-hour totals with nested six-hour
    totals. For example, +3--+6 is `(0--6) - (0--3)`. Inputs are never summed
    directly when their intervals overlap.
    """

    if segment_hours <= 0 or (window_end_hour - window_start_hour) % segment_hours:
        raise ValueError("target window must contain complete equal segments")
    if not messages:
        raise ValueError("no precipitation messages supplied")

    shape = messages[0].values_mm.shape
    by_range: dict[tuple[int, int], GriddedAccumulationMessage] = {}
    for message in messages:
        if message.values_mm.shape != shape:
            raise ValueError("all precipitation message grids must have the same shape")
        key = (message.start_hour, message.end_hour)
        if key in by_range:
            raise ValueError(f"duplicate precipitation interval {key}")
        by_range[key] = message

    reconstructed: list[np.ndarray] = []
    coverage: list[CoverageSegment] = []
    tiny_negative_count = 0
    minimum_tolerated_negative_mm: float | None = None
    for start in range(window_start_hour, window_end_hour, segment_hours):
        end = start + segment_hours
        direct = by_range.get((start, end))
        if direct is not None:
            increment = direct.values_mm.copy()
            source_ids = (direct.source_id,)
            operation = "direct_interval"
            segment_tolerance = negative_tolerance_mm
        else:
            candidates: list[tuple[GriddedAccumulationMessage, GriddedAccumulationMessage]] = []
            for base in range(0, start):
                total = by_range.get((base, end))
                prefix = by_range.get((base, start))
                if total is not None and prefix is not None:
                    candidates.append((total, prefix))
            if len(candidates) != 1:
                if not candidates:
                    raise ValueError(f"missing precipitation interval {start}--{end}")
                raise ValueError(f"ambiguous overlapping reconstruction for {start}--{end}")
            total, prefix = candidates[0]
            increment = total.values_mm - prefix.values_mm
            source_ids = (total.source_id, prefix.source_id)
            operation = "nested_interval_difference"

            if total.packing_quantum_mm is not None and prefix.packing_quantum_mm is not None:
                packing_bound = (total.packing_quantum_mm + prefix.packing_quantum_mm) / 2.0
                segment_tolerance = min(negative_tolerance_mm, packing_bound)
            else:
                segment_tolerance = negative_tolerance_mm

        material_negative = increment < -(segment_tolerance + 1e-12)
        if material_negative.any():
            raise ValueError(
                f"materially negative reconstructed precipitation for {start}--{end}"
            )
        tiny_negative = (increment < 0) & ~material_negative
        tiny_negative_count += int(tiny_negative.sum())
        if tiny_negative.any():
            candidate = float(np.min(increment[tiny_negative]))
            minimum_tolerated_negative_mm = (
                candidate
                if minimum_tolerated_negative_mm is None
                else min(minimum_tolerated_negative_mm, candidate)
            )
        increment[tiny_negative] = 0.0
        reconstructed.append(increment)
        coverage.append(
            CoverageSegment(
                start_hour=start,
                end_hour=end,
                duration_hours=segment_hours,
                source_ids=source_ids,
                operation=operation,
                negative_tolerance_mm=segment_tolerance,
            )
        )

    validate_segment_coverage(
        [(segment.start_hour, segment.end_hour) for segment in coverage],
        window_start_hour=window_start_hour,
        window_end_hour=window_end_hour,
    )
    return AccumulationResult(
        rainfall_mm=np.sum(np.stack(reconstructed), axis=0),
        segments=tuple(coverage),
        tiny_negative_count=tiny_negative_count,
        minimum_tolerated_negative_mm=minimum_tolerated_negative_mm,
        negative_tolerance_mm=negative_tolerance_mm,
    )


def reconstruct_minimal_accumulation_window(
    messages: list[GriddedAccumulationMessage],
    *,
    window_start_hour: int,
    window_end_hour: int,
) -> CanonicalAccumulationResult:
    """Reconstruct an exact window using the fewest packed-field subtractions.

    Every native interval wholly inside the target is a zero-subtraction candidate.
    A difference candidate ``(base, end) - (base, start)`` is admitted only when
    both fields declare their packing quantum. Dynamic programming chooses the
    exact cover with the lexicographically smallest ``(subtractions, segments)``.
    Thus source metadata, rather than a hard-coded interval formula, determines
    the decomposition.
    """

    if window_start_hour >= window_end_hour:
        raise ValueError("invalid target window")
    if not messages:
        raise ValueError("no precipitation messages supplied")

    shape = messages[0].values_mm.shape
    by_range: dict[tuple[int, int], GriddedAccumulationMessage] = {}
    for message in messages:
        if message.values_mm.shape != shape:
            raise ValueError("all precipitation message grids must have the same shape")
        key = (message.start_hour, message.end_hour)
        if key in by_range:
            raise ValueError(f"duplicate precipitation interval {key}")
        by_range[key] = message

    # Candidate tuple: end, subtraction cost, values, source ids, operation, bound.
    candidates: dict[int, list[tuple[int, int, np.ndarray, tuple[str, ...], str, float]]] = {}
    for (start, end), message in by_range.items():
        if window_start_hour <= start < end <= window_end_hour:
            candidates.setdefault(start, []).append(
                (end, 0, message.values_mm.copy(), (message.source_id,), "direct_interval", 0.0)
            )
    for start in range(window_start_hour, window_end_hour):
        for end in range(start + 1, window_end_hour + 1):
            for base in sorted({item.start_hour for item in messages if item.start_hour < start}):
                total = by_range.get((base, end))
                prefix = by_range.get((base, start))
                if total is None or prefix is None:
                    continue
                if total.packing_quantum_mm is None or prefix.packing_quantum_mm is None:
                    continue
                bound = (total.packing_quantum_mm + prefix.packing_quantum_mm) / 2.0
                candidates.setdefault(start, []).append(
                    (
                        end,
                        1,
                        total.values_mm - prefix.values_mm,
                        (total.source_id, prefix.source_id),
                        "nested_interval_difference",
                        bound,
                    )
                )

    # endpoint -> (score, chosen candidates). Source ids break otherwise exact ties.
    paths: dict[int, tuple[tuple, list[tuple]]] = {window_start_hour: ((0, 0, ()), [])}
    for start in range(window_start_hour, window_end_hour):
        if start not in paths:
            continue
        prior_score, prior_path = paths[start]
        for candidate in sorted(candidates.get(start, []), key=lambda item: (item[0], item[4], item[3])):
            end, subtraction_cost, _, source_ids, operation, _ = candidate
            score = (
                prior_score[0] + subtraction_cost,
                prior_score[1] + 1,
                prior_score[2] + ((start, end, operation, source_ids),),
            )
            if end not in paths or score < paths[end][0]:
                paths[end] = (score, prior_path + [(start, candidate)])
    if window_end_hour not in paths:
        raise ValueError(
            f"no exact accumulation decomposition for {window_start_hour}--{window_end_hour}"
        )

    arrays: list[np.ndarray] = []
    coverage: list[CanonicalCoverageSegment] = []
    normalized_count = 0
    minimum_negative: float | None = None
    for start, candidate in paths[window_end_hour][1]:
        end, _, raw_values, source_ids, operation, bound = candidate
        values = raw_values.copy()
        material_negative = values < -(bound + 1e-12)
        if material_negative.any():
            raise ValueError(
                f"negative difference exceeds packing bound for {start}--{end}"
            )
        negative = values < 0
        count = int(negative.sum())
        segment_minimum = float(np.min(values[negative])) if count else None
        if count:
            normalized_count += count
            minimum_negative = (
                segment_minimum
                if minimum_negative is None
                else min(minimum_negative, segment_minimum)
            )
            values[negative] = 0.0
        arrays.append(values)
        coverage.append(
            CanonicalCoverageSegment(
                start_hour=start,
                end_hour=end,
                duration_hours=end - start,
                source_ids=source_ids,
                operation=operation,
                packing_error_bound_mm=bound,
                normalized_negative_count=count,
                minimum_normalized_negative_mm=segment_minimum,
            )
        )

    validate_segment_coverage(
        [(item.start_hour, item.end_hour) for item in coverage],
        window_start_hour=window_start_hour,
        window_end_hour=window_end_hour,
    )
    rainfall = np.sum(np.stack(arrays), axis=0)
    if not np.isfinite(rainfall).all() or (rainfall < 0).any():
        raise ValueError("canonical rainfall output is invalid")
    return CanonicalAccumulationResult(
        rainfall_mm=rainfall,
        segments=tuple(coverage),
        subtraction_count=sum(item.operation == "nested_interval_difference" for item in coverage),
        normalized_negative_count=normalized_count,
        minimum_normalized_negative_mm=minimum_negative,
    )
