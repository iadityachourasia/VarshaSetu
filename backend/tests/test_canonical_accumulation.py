import numpy as np
import pytest
import csv
from pathlib import Path

from app.data.accumulation import (
    GriddedAccumulationMessage,
    reconstruct_accumulation_window,
    reconstruct_minimal_accumulation_window,
)


def message(start, end, value, *, quantum=0.25):
    return GriddedAccumulationMessage(
        start, end, np.full((2, 2), value, dtype=float), f"m-{start}-{end}", quantum
    )


def alternating_messages(*, anomalous_unused_difference=False):
    # Exact increments are 1 mm per three hours. Native six-hour fields are 2 mm.
    rows = []
    cumulative_base = 0
    for end in range(3, 28, 3):
        start = end - 3 if end % 6 == 3 else end - 6
        value = 1.0 if end % 6 == 3 else 2.0
        if anomalous_unused_difference and (start, end) == (18, 24):
            value = 0.8  # makes the old synthetic 21--24 increment negative
        rows.append(message(start, end, value))
        if end % 6 == 0:
            cumulative_base = end
    return rows


def test_canonical_cover_is_exact_and_uses_one_subtraction():
    result = reconstruct_minimal_accumulation_window(
        alternating_messages(), window_start_hour=3, window_end_hour=27
    )
    assert [(item.start_hour, item.end_hour) for item in result.segments] == [
        (3, 6), (6, 12), (12, 18), (18, 24), (24, 27)
    ]
    assert result.subtraction_count == 1
    assert sum(item.duration_hours for item in result.segments) == 24
    assert np.array_equal(result.rainfall_mm, np.full((2, 2), 8.0))


def test_canonical_algebra_matches_eight_increment_sum():
    messages = alternating_messages()
    old = reconstruct_accumulation_window(
        messages, window_start_hour=3, window_end_hour=27, negative_tolerance_mm=0.25
    )
    new = reconstruct_minimal_accumulation_window(
        messages, window_start_hour=3, window_end_hour=27
    )
    assert np.array_equal(new.rainfall_mm, old.rainfall_mm)


def test_unused_packing_anomaly_does_not_invalidate_canonical_product():
    messages = alternating_messages(anomalous_unused_difference=True)
    with pytest.raises(ValueError, match="materially negative"):
        reconstruct_accumulation_window(
            messages, window_start_hour=3, window_end_hour=27, negative_tolerance_mm=0.1
        )
    result = reconstruct_minimal_accumulation_window(
        messages, window_start_hour=3, window_end_hour=27
    )
    assert result.subtraction_count == 1
    assert np.array_equal(result.rainfall_mm, np.full((2, 2), 6.8))


def test_unavoidable_difference_must_respect_declared_packing_bound():
    messages = alternating_messages()
    messages[1] = message(0, 6, 0.7, quantum=0.1)
    messages[0] = message(0, 3, 1.0, quantum=0.1)
    with pytest.raises(ValueError, match="exceeds packing bound"):
        reconstruct_minimal_accumulation_window(
            messages, window_start_hour=3, window_end_hour=27
        )


def test_difference_without_packing_metadata_fails_closed():
    messages = alternating_messages()
    messages[0] = GriddedAccumulationMessage(0, 3, np.ones((2, 2)), "missing", None)
    with pytest.raises(ValueError, match="no exact accumulation decomposition"):
        reconstruct_minimal_accumulation_window(
            messages, window_start_hour=3, window_end_hour=27
        )


def test_phase1f_replay_eligibility_and_july22_regression():
    root = Path(__file__).resolve().parents[2]
    replay_path = root / "data/manifests/phase1f/2019-JJAS/reconstruction_replay.csv"
    eligibility_path = root / "data/manifests/phase1f/2019-JJAS/eligibility_index.csv"
    if not replay_path.exists() or not eligibility_path.exists():
        pytest.skip("Phase 1F replay artifacts have not been generated")
    with replay_path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == 1830
    july = {
        (row["member"], row["product"]): row
        for row in rows if row["initialization"] == "2019072200"
    }
    assert july[("p01", "day2_24h")]["method_a_status"] == "FAIL"
    assert july[("p01", "day2_24h")]["method_b_status"] == "PASS"
    assert july[("c00", "day2_24h")]["method_b_status"] == "FAIL"
    assert july[("p04", "day2_24h")]["method_b_status"] == "PASS"
    with eligibility_path.open(newline="", encoding="utf-8") as handle:
        eligibility = list(csv.DictReader(handle))
    assert sum(row["CONTROL_MODEL_ELIGIBLE"].lower() == "true" for row in eligibility) == 255
    assert sum(row["FULL_ENSEMBLE_ELIGIBLE"].lower() == "true" for row in eligibility) == 173
