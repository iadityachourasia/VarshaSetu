"""Experimental cell-mask accumulation diagnostic, separate from canonical QC.

The canonical operational/research corpus continues to refuse an entire lead
when any packed nested difference exceeds its bound. This module explores how
much coverage a future version might retain if only affected cells were marked
missing. It is not a replacement or authorized model input.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from backend.app.data.accumulation import GriddedAccumulationMessage, validate_segment_coverage


@dataclass(frozen=True)
class MaskedAccumulationDiagnostic:
    rainfall_mm: np.ndarray
    valid_mask: np.ndarray
    invalid_cells: int
    segments: tuple[dict, ...]
    subtraction_count: int


def reconstruct_masked_diagnostic(messages: list[GriddedAccumulationMessage], *, window_start_hour: int,
                                  window_end_hour: int) -> MaskedAccumulationDiagnostic:
    """Use the canonical minimum-subtraction path and mask material negatives.

    Invalid cells remain NaN, never zero. The exact path rule is duplicated
    here deliberately so the frozen canonical function is untouched.
    """
    if window_start_hour >= window_end_hour or not messages:
        raise ValueError("invalid target window or no messages")
    shape = messages[0].values_mm.shape
    by_range = {}
    for message in messages:
        if message.values_mm.shape != shape:
            raise ValueError("message grids differ")
        key = (message.start_hour, message.end_hour)
        if key in by_range:
            raise ValueError("duplicate precipitation interval")
        by_range[key] = message
    candidates: dict[int, list[tuple[int, int, np.ndarray, tuple[str, ...], str, float]]] = {}
    for (start, end), message in by_range.items():
        if window_start_hour <= start < end <= window_end_hour:
            candidates.setdefault(start, []).append((end, 0, message.values_mm.copy(), (message.source_id,), "direct_interval", 0.0))
    for start in range(window_start_hour, window_end_hour):
        for end in range(start + 1, window_end_hour + 1):
            for base in sorted({item.start_hour for item in messages if item.start_hour < start}):
                total, prefix = by_range.get((base, end)), by_range.get((base, start))
                if total is None or prefix is None or total.packing_quantum_mm is None or prefix.packing_quantum_mm is None:
                    continue
                bound = (total.packing_quantum_mm + prefix.packing_quantum_mm) / 2.0
                candidates.setdefault(start, []).append((end, 1, total.values_mm - prefix.values_mm,
                                                           (total.source_id, prefix.source_id), "nested_interval_difference", bound))
    paths: dict[int, tuple[tuple, list[tuple]]] = {window_start_hour: ((0, 0, ()), [])}
    for start in range(window_start_hour, window_end_hour):
        if start not in paths:
            continue
        prior_score, prior_path = paths[start]
        for candidate in sorted(candidates.get(start, []), key=lambda item: (item[0], item[4], item[3])):
            end, subtraction_cost, _, source_ids, operation, _ = candidate
            score = (prior_score[0] + subtraction_cost, prior_score[1] + 1,
                     prior_score[2] + ((start, end, operation, source_ids),))
            if end not in paths or score < paths[end][0]:
                paths[end] = (score, prior_path + [(start, candidate)])
    if window_end_hour not in paths:
        raise ValueError("no exact accumulation decomposition")
    valid = np.ones(shape, dtype=bool)
    fields = []
    segments = []
    for start, candidate in paths[window_end_hour][1]:
        end, _, raw, source_ids, operation, bound = candidate
        values = raw.copy()
        invalid = values < -(bound + 1e-12)
        valid &= ~invalid
        within_bound_negative = (values < 0) & ~invalid
        values[within_bound_negative] = 0.0
        values[invalid] = np.nan
        fields.append(values)
        segments.append({"start_hour": start, "end_hour": end, "operation": operation,
                         "source_ids": source_ids, "packing_error_bound_mm": bound,
                         "invalid_cells": int(invalid.sum()),
                         "normalized_within_bound_cells": int(within_bound_negative.sum())})
    validate_segment_coverage([(segment["start_hour"], segment["end_hour"]) for segment in segments],
                              window_start_hour=window_start_hour, window_end_hour=window_end_hour)
    rainfall = np.sum(np.stack(fields), axis=0)
    rainfall[~valid] = np.nan
    if not np.isfinite(rainfall[valid]).all() or np.any(rainfall[valid] < 0):
        raise ValueError("masked rainfall contains invalid eligible values")
    return MaskedAccumulationDiagnostic(rainfall, valid, int((~valid).sum()), tuple(segments),
                                        sum(s["operation"] == "nested_interval_difference" for s in segments))
