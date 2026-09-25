"""Phase 4H protocol-only integrity and leakage tests; no model execution."""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path

from experiments.recent_historical.operational_model_protocol_v1.build_protocol import (
    DATA,
    HERE,
    build_folds,
    build_protocol,
    check_inputs,
    encode,
    load,
    outer_membership,
    sha256,
)


def _frozen() -> tuple[dict, dict]:
    return load(HERE / "protocol.json"), load(HERE / "crossfit_folds_2023.json")


def test_input_hashes_year_roles_and_seal() -> None:
    check_inputs()
    protocol, _ = _frozen()
    assert protocol["roles"] == {
        "2023": "train_and_grouped_crossfit",
        "2024": "validation_calibration_and_selection",
        "2025": "sealed_final_test",
    }
    assert protocol["unseal_2025"]["status"] == "SEALED"
    assert len(protocol["unseal_2025"]["requirements"]) == 13


def test_fold_manifest_reproducibility_and_hash() -> None:
    protocol, folds = _frozen()
    assert encode(build_folds()) == (HERE / "crossfit_folds_2023.json").read_bytes()
    assert hashlib.sha256(encode(folds)).hexdigest() == protocol["crossfit_folds_2023_sha256"]
    assert encode(build_protocol(protocol["crossfit_folds_2023_sha256"])) == (HERE / "protocol.json").read_bytes()
    assert sha256(HERE / "protocol.json") == (HERE / "protocol.sha256").read_text().strip()
    assert sha256(HERE / "crossfit_folds_2023.json") == (HERE / "crossfit_folds_2023.sha256").read_text().strip()


def test_every_case_once_and_no_case_or_init_split() -> None:
    _, folds = _frozen()
    cases = folds["deterministic_cases"]
    regime = folds["regime_cases"]
    source = load(DATA / "2023/train/deterministic/cases.json")
    assert len(cases) == 200
    assert len(regime) == 375
    assert [r["case_id"] for r in cases] == [r["case_id"] for r in source]
    assert len({r["case_id"] for r in cases}) == 200
    init_folds = {}
    for row in cases + regime:
        assert row["fold_id"] in {"F1", "F2", "F3", "F4", "F5"}
        assert init_folds.setdefault(row["initialization_utc"], row["fold_id"]) == row["fold_id"]
    for fold in folds["folds"]:
        assert fold["deterministic_case_count"] == sum(r["fold_id"] == fold["fold_id"] for r in cases)
        assert fold["deterministic_row_count"] == fold["deterministic_case_count"] * 1301
        assert fold["regime_case_count"] == 75
    assert sum(f["deterministic_row_count"] for f in folds["folds"]) == 260200
    assert sum(Counter(r["fold_id"] for r in cases).values()) == 200


def test_outer_training_holdout_and_embargo_are_disjoint() -> None:
    _, folds = _frozen()
    for population, count in (("deterministic_cases", 200), ("regime_cases", 375)):
        all_heldout = []
        for i in range(1, 6):
            train, heldout, embargo = outer_membership(folds, f"F{i}", population)
            assert set(train).isdisjoint(heldout)
            assert set(train).isdisjoint(embargo)
            assert len(train) + len(heldout) + len(embargo) == count
            all_heldout.extend(heldout)
        assert len(all_heldout) == len(set(all_heldout)) == count


def test_frozen_bounded_candidates_and_selection() -> None:
    protocol, _ = _frozen()
    assert len(protocol["models"]["M1"]["alpha_candidates"]) == 4
    grid = protocol["models"]["M2"]["candidate_grid"]
    count = 1
    for values in grid.values():
        assert values and all(isinstance(x, (int, float)) for x in values)
        count *= len(values)
    assert count == 4
    assert protocol["models"]["M2"]["device"] == "cpu"
    assert "2023 inner" in protocol["models"]["M2"]["selection"]
    assert protocol["deterministic_selection"]["primary"] == "RMSE"
    assert len(protocol["probability"]["candidates"]) == 3
    assert protocol["probability"]["calibration"]["candidates"] == ["identity", "sigmoid", "isotonic"]
    assert protocol["probability"]["thresholds"]["grid"] == [round(i / 100, 2) for i in range(5, 100, 5)]
    assert "maximum CSI" in protocol["probability"]["thresholds"]["selection"]
    assert protocol["final_fit"]["option"] == "A_2023_ONLY"


def test_common_populations_and_safe_artifacts() -> None:
    protocol, _ = _frozen()
    assert protocol["deterministic_selection"]["cases"] == 183
    assert protocol["deterministic_selection"]["cells"] == 238083
    assert protocol["ensemble_baseline"]["cases"] == 67
    assert protocol["ensemble_baseline"]["cells"] == 87167
    assert protocol["features"]["m2_regime_exclusion"] is True
    assert protocol["serialization"]["forbidden"] == ["pickle", "joblib"]
    assert sha256(HERE / "crossfit_folds_2023.json") == protocol["crossfit_folds_2023_sha256"]
