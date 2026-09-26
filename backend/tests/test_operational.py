"""Contract and numerical-regression tests for the Phase 5A.1 read-only
operational (2023-2025) presentation API. These tests prove the API only
indexes/reshapes frozen artifacts -- it must never fabricate, recompute, or
misattribute a scientific value. No model is trained or re-run here."""

from __future__ import annotations

import math

import numpy as np
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

try:
    from backend.app.api.operational import router
except ModuleNotFoundError:
    from app.api.operational import router


@pytest.fixture(scope="module")
def client() -> TestClient:
    app = FastAPI()
    app.include_router(router, prefix="/api")
    return TestClient(app)


@pytest.fixture(scope="module")
def full_app_client() -> TestClient:
    """Uses the real app (backend/main.py), including its structured-error
    exception handler -- the bare-router `client` fixture above does not
    register that handler, so a dict `detail` there would come back nested
    under FastAPI's default {"detail": {...}} instead of the flattened
    {code, detail} body the real server actually returns."""
    try:
        from backend.main import app as real_app
    except ModuleNotFoundError:
        from main import app as real_app
    return TestClient(real_app)


def _close(actual: float, expected: float, tol: float = 1e-4) -> bool:
    return math.isclose(actual, expected, rel_tol=tol, abs_tol=tol)


# ---------------------------------------------------------------------------
# Year-role and capability contract
# ---------------------------------------------------------------------------


def test_status_reports_year_roles(client: TestClient) -> None:
    payload = client.get("/api/science/operational/status").json()
    assert payload["years"] == {"2023": "TRAIN_CROSSFIT", "2024": "VALIDATION_SELECTION", "2025": "FINAL_TEST_COMPLETED"}


def test_2023_m2_is_out_of_fold(client: TestClient) -> None:
    capabilities = client.get("/api/science/operational/2023/availability").json()
    assert capabilities["m2"] == "out_of_fold_case_grid"


def test_2023_m1_m3_m4_unavailable(client: TestClient) -> None:
    capabilities = client.get("/api/science/operational/2023/availability").json()
    assert capabilities["m1"] == "unavailable"
    assert capabilities["m3"] == "unavailable"
    assert capabilities["m4"] == "unavailable"
    assert capabilities["heavy_probability"] == "unavailable"
    assert capabilities["very_heavy_probability"] == "unavailable"


def test_2024_supports_verified_case_grid_set(client: TestClient) -> None:
    """Phase 5A.1B proved the Phase 4G row/pixel index for 2024; case grids are
    now exposed (upgraded from Phase 5A.1's aggregate-only exposure)."""
    capabilities = client.get("/api/science/operational/2024/availability").json()
    for field in ("m1", "m2", "m3", "m4", "heavy_probability", "very_heavy_probability"):
        assert capabilities[field] == "case_grid"
    assert capabilities["regime_probability"] == "per_case"
    assert capabilities["fss"] is True
    assert capabilities["case_level_metrics"] is False  # no per-case metrics file exists for 2024


def test_2025_supports_full_case_grid_set(client: TestClient) -> None:
    capabilities = client.get("/api/science/operational/2025/availability").json()
    for field in ("m1", "m2", "m3", "m4", "heavy_probability", "very_heavy_probability"):
        assert capabilities[field] == "case_grid"
    assert capabilities["case_level_metrics"] is True
    assert capabilities["per_cell_metrics"] is True
    assert capabilities["fss"] is True
    assert capabilities["reliability_bins"] is True


def test_pr_roc_curve_arrays_always_unavailable(client: TestClient) -> None:
    for year in (2023, 2024, 2025):
        capabilities = client.get(f"/api/science/operational/{year}/availability").json()
        assert capabilities["pr_roc_curve_arrays"] == "unavailable"


def test_district_aggregation_always_unavailable(client: TestClient) -> None:
    for year in (2023, 2024, 2025):
        capabilities = client.get(f"/api/science/operational/{year}/availability").json()
        assert capabilities["district_aggregates"] is False


def test_2025_m1_is_primary_m2_is_secondary(client: TestClient) -> None:
    payload = client.get("/api/science/operational/2025/metrics/deterministic").json()
    assert payload["primary_model"] == "M1"
    notes = " ".join(payload["notes"])
    assert "PRESELECTED_PRIMARY_MODEL" in notes
    assert "SECONDARY_FINAL_TEST_RESULT" in notes


def test_2024_has_no_primary_model_designation(client: TestClient) -> None:
    payload = client.get("/api/science/operational/2024/metrics/deterministic").json()
    assert payload["primary_model"] is None


def test_2023_deterministic_metrics_unavailable(client: TestClient) -> None:
    response = client.get("/api/science/operational/2023/metrics/deterministic")
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# QC / eligibility contract
# ---------------------------------------------------------------------------


def test_qc_failed_member_is_never_exposed_as_valid(client: TestClient) -> None:
    cases = client.get("/api/science/operational/2025/cases", params={"page_size": 5}).json()["cases"]
    target = None
    case_id = None
    for case in cases:
        detail = client.get(f"/api/science/operational/2025/cases/{case['case_id']}").json()
        for member, eligible in detail["member_qc"].items():
            if not eligible:
                target, case_id = member, case["case_id"]
                break
        if target:
            break
    assert target is not None, "expected at least one QC-ineligible member in the sample"
    response = client.get(f"/api/science/operational/2025/cases/{case_id}/rainfall", params={"field": target if target != "c00" else "raw"})
    assert response.status_code == 404


def test_five_member_eligibility_is_respected_in_ensemble_endpoint(client: TestClient) -> None:
    cases = client.get("/api/science/operational/2025/cases", params={"page_size": 5}).json()["cases"]
    case_id = cases[0]["case_id"]
    response = client.get(f"/api/science/operational/2025/cases/{case_id}/ensemble").json()
    for member in response["members"]:
        if not member["qc_eligible"]:
            assert member["values"] is None


# ---------------------------------------------------------------------------
# Path safety
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("bad_case_id", [
    "../../etc/passwd",
    "2025-06-01_day1_24h",
    "20259999_day1_24h",
    "20250601_day9_24h",
    "20250601_day1_48h",
    "%2e%2e%2fdata",
])
def test_malformed_case_ids_are_rejected(client: TestClient, bad_case_id: str) -> None:
    response = client.get(f"/api/science/operational/2025/cases/{bad_case_id}")
    assert response.status_code == 404


def test_unknown_year_is_rejected(client: TestClient) -> None:
    assert client.get("/api/science/operational/2026/availability").status_code == 404
    assert client.get("/api/science/operational/2020/cases").status_code == 404


def test_unknown_rainfall_field_is_rejected(client: TestClient) -> None:
    cases = client.get("/api/science/operational/2025/cases", params={"page_size": 1}).json()["cases"]
    case_id = cases[0]["case_id"]
    response = client.get(f"/api/science/operational/2025/cases/{case_id}/rainfall", params={"field": "not_a_field"})
    assert response.status_code == 422  # FastAPI query pattern validation


def test_unknown_atmospheric_field_is_rejected(client: TestClient) -> None:
    cases = client.get("/api/science/operational/2025/cases", params={"page_size": 1}).json()["cases"]
    case_id = cases[0]["case_id"]
    response = client.get(f"/api/science/operational/2025/cases/{case_id}/atmosphere/bogus_field")
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# Numerical regression -- exact known headline values
# ---------------------------------------------------------------------------


def test_2025_deterministic_headline_numbers(client: TestClient) -> None:
    metrics = client.get("/api/science/operational/2025/metrics/deterministic").json()["metrics"]
    assert metrics["M0"]["case_count"] == 232
    assert metrics["M0"]["cell_count"] == 301832
    assert _close(metrics["M0"]["continuous"]["rmse_mm"], 16.1657)
    assert _close(metrics["M1"]["continuous"]["rmse_mm"], 15.5736)
    assert _close(metrics["M2"]["continuous"]["rmse_mm"], 15.0022)
    assert _close(metrics["M3"]["continuous"]["rmse_mm"], 15.4608)
    assert _close(metrics["M4"]["continuous"]["rmse_mm"], 15.2153)


def test_2025_ensemble_metrics_headline_numbers(client: TestClient) -> None:
    payload = client.get("/api/science/operational/2025/metrics/ensemble").json()
    assert payload["label"] == "MATCHED 75-CASE SUBSET"
    metrics = payload["metrics"]
    assert metrics["case_count"] == 75
    assert metrics["cell_count"] == 97575
    assert _close(metrics["heavy"]["five_member_fraction"]["brier"], 0.0228866)
    assert _close(metrics["heavy"]["frozen_ML_same_cells"]["brier"], 0.0208497)
    assert _close(metrics["very_heavy"]["five_member_fraction"]["brier"], 0.00502342)
    assert _close(metrics["very_heavy"]["frozen_ML_same_cells"]["brier"], 0.00493453)


def test_ensemble_metrics_unavailable_outside_2025(client: TestClient) -> None:
    for year in (2023, 2024):
        response = client.get(f"/api/science/operational/{year}/metrics/ensemble")
        assert response.status_code == 404


def test_2024_deterministic_headline_numbers(client: TestClient) -> None:
    metrics = client.get("/api/science/operational/2024/metrics/deterministic").json()["metrics"]
    assert metrics["M0"]["case_count"] == 183
    assert _close(metrics["M0"]["continuous"]["rmse_mm"], 17.1297, tol=1e-3)
    assert _close(metrics["M1"]["continuous"]["rmse_mm"], 16.7975, tol=1e-3)


def test_quality_headline_numbers(client: TestClient) -> None:
    payload = client.get("/api/science/operational/quality").json()
    assert payload["scheduled_date_lead_cases"] == 1125
    assert payload["atmosphere_complete"] == 1125
    assert payload["c00_eligible_total"] == 615
    assert payload["five_member_eligible_total"] == 218
    assert payload["c00_eligible_by_year"] == {"2023": 200, "2024": 183, "2025": 232}
    assert payload["five_member_eligible_by_year"] == {"2023": 76, "2024": 67, "2025": 75}
    assert payload["scheduled_by_year"] == {"2023": 375, "2024": 375, "2025": 375}
    assert payload["atmosphere_complete_by_year"] == {"2023": 375, "2024": 375, "2025": 375}
    assert payload["deterministic_eligible_by_year"] == {"2023": 200, "2024": 183, "2025": 232}


def test_2025_regime_case_counts(client: TestClient) -> None:
    distribution = client.get("/api/science/operational/2025/regimes").json()["distribution"]
    assert distribution["paired_case_counts"] == {
        "ACTIVE_MONSOON": 100, "BREAK_WEAK_MONSOON": 71, "LOW_DEPRESSION_INFLUENCED": 61,
    }


# ---------------------------------------------------------------------------
# Array regression -- reconstructed grid must reproduce the frozen scalar metric
# exactly, proving the pixel-index scatter is a lossless reshape, not a
# recomputation.
# ---------------------------------------------------------------------------


def test_2025_rainfall_grid_reconstructs_frozen_case_rmse(client: TestClient) -> None:
    case_id = "20250601_day1_24h"
    m1 = client.get(f"/api/science/operational/2025/cases/{case_id}/rainfall", params={"field": "m1"}).json()["values"]
    imd = client.get(f"/api/science/operational/2025/cases/{case_id}/rainfall", params={"field": "imd"}).json()["values"]
    m1_arr = np.array([[np.nan if v is None else v for v in row] for row in m1])
    imd_arr = np.array([[np.nan if v is None else v for v in row] for row in imd])
    mask = np.isfinite(m1_arr) & np.isfinite(imd_arr)
    assert mask.sum() > 0
    rmse = float(np.sqrt(np.mean((m1_arr[mask] - imd_arr[mask]) ** 2)))
    case_level = client.get("/api/science/operational/2025/cases", params={"page_size": 1}).json()["cases"][0]
    assert case_level["case_id"] == case_id
    assert _close(rmse, case_level["m1_rmse_mm"], tol=1e-9)


def test_2025_raw_rainfall_grid_shape(client: TestClient) -> None:
    case_id = "20250601_day1_24h"
    payload = client.get(f"/api/science/operational/2025/cases/{case_id}/rainfall", params={"field": "raw"}).json()
    assert payload["shape"] == [49, 49]
    assert len(payload["values"]) == 49
    assert len(payload["values"][0]) == 49


def test_2023_unproven_fields_remain_unavailable(client: TestClient) -> None:
    """2023's M1/M3/M4/probability mapping was never claimed proven -- these
    fields must stay unavailable regardless of how much other 2023 attribution
    (M2 OOF, regime OOF) was resolved in Phase 5A.1B."""
    cases = client.get("/api/science/operational/2023/cases", params={"page_size": 1}).json()["cases"]
    case_id = cases[0]["case_id"]
    for field in ("m1", "m3", "m4"):
        response = client.get(f"/api/science/operational/2023/cases/{case_id}/rainfall", params={"field": field})
        assert response.status_code == 404
    response = client.get(f"/api/science/operational/2023/cases/{case_id}/probability/heavy")
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# Phase 5A.1B -- 2024 row/pixel attribution proof
# ---------------------------------------------------------------------------


def test_2024_m1_m2_m3_m4_grid_reconstruction_reproduces_frozen_aggregate_rmse(client: TestClient) -> None:
    """The core Phase 5A.1B mapping proof: reshaping each 2024 model's flat
    corpus-order array through the Phase 4G case_id -> row_start/pixel_index
    index and recomputing RMSE against the reshaped IMD grid, summed over every
    case in the 183-case population, must reproduce validation_manifest.json's
    frozen aggregate RMSE to float32 precision -- proving the row order, not
    merely assuming it from matching array lengths."""
    expected = {"M0": 17.1297, "M1": 16.7975, "M2": 16.8459, "M3": 17.4134, "M4": 17.2628}
    cases = client.get("/api/science/operational/2024/cases", params={"page_size": 400}).json()["cases"]
    case_ids = [c["case_id"] for c in cases if c["deterministic_source_eligible"]]
    assert len(case_ids) == 183

    imd_by_case: dict[str, np.ndarray] = {}
    for cid in case_ids:
        payload = client.get(f"/api/science/operational/2024/cases/{cid}/rainfall", params={"field": "imd"}).json()
        imd_by_case[cid] = np.array([[np.nan if v is None else v for v in row] for row in payload["values"]])

    for model_key, expected_rmse in [("M1", expected["M1"]), ("M2", expected["M2"]), ("M3", expected["M3"]), ("M4", expected["M4"])]:
        squared_errors = []
        for cid in case_ids:
            payload = client.get(f"/api/science/operational/2024/cases/{cid}/rainfall", params={"field": model_key.lower()}).json()
            model_grid = np.array([[np.nan if v is None else v for v in row] for row in payload["values"]])
            mask = np.isfinite(model_grid) & np.isfinite(imd_by_case[cid])
            squared_errors.append((model_grid[mask] - imd_by_case[cid][mask]) ** 2)
        rmse = float(np.sqrt(np.concatenate(squared_errors).mean()))
        assert _close(rmse, expected_rmse, tol=2e-4), f"{model_key}: reconstructed {rmse} vs expected {expected_rmse}"


def test_2024_raw_reconstruction_via_rainfall_qc_matches_frozen_aggregate(client: TestClient) -> None:
    """Cross-check using the (already-gridded, no-reshape-needed) raw c00 path
    against the same 183-case population reproduces M0's frozen RMSE too."""
    cases = client.get("/api/science/operational/2024/cases", params={"page_size": 400}).json()["cases"]
    case_ids = [c["case_id"] for c in cases if c["deterministic_source_eligible"]]
    squared_errors = []
    for cid in case_ids:
        raw = client.get(f"/api/science/operational/2024/cases/{cid}/rainfall", params={"field": "raw"}).json()
        imd = client.get(f"/api/science/operational/2024/cases/{cid}/rainfall", params={"field": "imd"}).json()
        raw_grid = np.array([[np.nan if v is None else v for v in row] for row in raw["values"]])
        imd_grid = np.array([[np.nan if v is None else v for v in row] for row in imd["values"]])
        mask = np.isfinite(raw_grid) & np.isfinite(imd_grid)
        squared_errors.append((raw_grid[mask] - imd_grid[mask]) ** 2)
    rmse = float(np.sqrt(np.concatenate(squared_errors).mean()))
    assert _close(rmse, 17.1297, tol=2e-4)


def test_2023_oof_m2_case_order_matches_phase4g_index(client: TestClient) -> None:
    """The 2023 OOF M2 case grid must only ever be reachable for cases the
    oof_m2 manifest actually declares -- proving the mapping is case_id-keyed,
    not position-guessed."""
    cases = client.get("/api/science/operational/2023/cases", params={"page_size": 200}).json()["cases"]
    eligible = [c["case_id"] for c in cases if c["deterministic_source_eligible"]][:5]
    for cid in eligible:
        response = client.get(f"/api/science/operational/2023/cases/{cid}/rainfall", params={"field": "m2"})
        assert response.status_code == 200
        payload = response.json()
        assert payload["prediction_role"] == "OUT_OF_FOLD"
        assert payload["shape"] == [49, 49]


# ---------------------------------------------------------------------------
# Phase 5A.1B -- regime attribution proof
# ---------------------------------------------------------------------------


def test_2023_regime_is_out_of_fold(client: TestClient) -> None:
    cases = client.get("/api/science/operational/2023/cases", params={"page_size": 5}).json()["cases"]
    case_id = next(c["case_id"] for c in cases if c["regime_source_eligible"])
    payload = client.get(f"/api/science/operational/2023/cases/{case_id}/regime").json()
    assert payload["prediction_role"] == "OUT_OF_FOLD"
    assert payload["year_role"] == "TRAIN_CROSSFIT"
    assert "not independently observed meteorological truth" in payload["semantic_note"]


def test_2024_regime_is_prospective_validation(client: TestClient) -> None:
    cases = client.get("/api/science/operational/2024/cases", params={"page_size": 5}).json()["cases"]
    case_id = next(c["case_id"] for c in cases if c["regime_source_eligible"])
    payload = client.get(f"/api/science/operational/2024/cases/{case_id}/regime").json()
    assert payload["prediction_role"] == "PROSPECTIVE_VALIDATION"
    assert payload["year_role"] == "VALIDATION_SELECTION"


def test_2025_regime_is_final_test_prediction(client: TestClient) -> None:
    cases = client.get("/api/science/operational/2025/cases", params={"page_size": 5}).json()["cases"]
    case_id = next(c["case_id"] for c in cases if c["regime_source_eligible"])
    payload = client.get(f"/api/science/operational/2025/cases/{case_id}/regime").json()
    assert payload["prediction_role"] == "FINAL_TEST_PREDICTION"
    assert payload["year_role"] == "FINAL_TEST_COMPLETED"


def test_regime_probabilities_are_finite_and_sum_to_one(client: TestClient) -> None:
    for year in (2023, 2024, 2025):
        cases = client.get(f"/api/science/operational/{year}/cases", params={"page_size": 10}).json()["cases"]
        checked = 0
        for case in cases:
            if not case["regime_source_eligible"]:
                continue
            payload = client.get(f"/api/science/operational/{year}/cases/{case['case_id']}/regime").json()
            values = list(payload["probabilities"].values())
            assert all(math.isfinite(v) for v in values)
            assert _close(sum(values), 1.0, tol=1e-6)
            assert payload["predicted_class"] in payload["probabilities"]
            checked += 1
        assert checked > 0


def test_2025_regime_full_and_paired_counts_reproduce_frozen_aggregates(client: TestClient) -> None:
    """Reproduces BOTH the 375-case classifier counts and the 232-case paired
    counts by walking every case through the per-case regime endpoint -- the
    same independent double cross-check used to prove the eligibility-order
    hypothesis in the first place."""
    all_cases = client.get("/api/science/operational/2025/cases", params={"page_size": 400}).json()["cases"]
    assert len(all_cases) == 375
    full_counts = {"ACTIVE_MONSOON": 0, "BREAK_WEAK_MONSOON": 0, "LOW_DEPRESSION_INFLUENCED": 0}
    paired_counts = {"ACTIVE_MONSOON": 0, "BREAK_WEAK_MONSOON": 0, "LOW_DEPRESSION_INFLUENCED": 0}
    for case in all_cases:
        if not case["regime_source_eligible"]:
            continue
        payload = client.get(f"/api/science/operational/2025/cases/{case['case_id']}/regime").json()
        full_counts[payload["predicted_class"]] += 1
        if case["deterministic_source_eligible"]:
            paired_counts[payload["predicted_class"]] += 1
    assert full_counts == {"ACTIVE_MONSOON": 150, "BREAK_WEAK_MONSOON": 130, "LOW_DEPRESSION_INFLUENCED": 95}
    assert paired_counts == {"ACTIVE_MONSOON": 100, "BREAK_WEAK_MONSOON": 71, "LOW_DEPRESSION_INFLUENCED": 61}


def test_regime_endpoint_unknown_case_is_rejected(client: TestClient) -> None:
    response = client.get("/api/science/operational/2025/cases/20250101_day1_24h/regime")
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# Phase 5A.2 -- structured {code, detail} error contract (main.py's exception
# handler), additive and backward-compatible with the plain-string convention
# every other existing route still uses unchanged.
# ---------------------------------------------------------------------------


def test_qc_failed_member_returns_case_not_eligible_code(full_app_client: TestClient) -> None:
    response = full_app_client.get(
        "/api/science/operational/2025/cases/20250601_day1_24h/rainfall", params={"field": "p02"},
    )
    assert response.status_code == 404
    body = response.json()
    assert body["code"] == "SCIENCE_CASE_NOT_ELIGIBLE"
    assert "QC" in body["detail"]


def test_2023_unsupported_model_returns_product_unavailable_code(full_app_client: TestClient) -> None:
    response = full_app_client.get(
        "/api/science/operational/2023/cases/20230601_day1_24h/rainfall", params={"field": "m1"},
    )
    assert response.status_code == 404
    body = response.json()
    assert body["code"] == "SCIENCE_PRODUCT_UNAVAILABLE"


def test_unknown_field_returns_invalid_field_code(full_app_client: TestClient) -> None:
    response = full_app_client.get(
        "/api/science/operational/2025/cases/20250601_day1_24h/atmosphere/bogus",
    )
    assert response.status_code == 404
    assert response.json()["code"] == "SCIENCE_INVALID_FIELD"


def test_malformed_case_id_returns_case_not_found_code(full_app_client: TestClient) -> None:
    response = full_app_client.get("/api/science/operational/2025/cases/not-a-real-case")
    assert response.status_code == 404
    assert response.json()["code"] == "SCIENCE_CASE_NOT_FOUND"


def test_legacy_science_routes_keep_plain_string_detail(full_app_client: TestClient) -> None:
    """The structured-error handler must be purely additive: Track A's
    existing /api/science/* router (and the legacy /api/* router) still
    return a plain string `detail`, unchanged, because their HTTPExceptions
    never set a dict detail."""
    response = full_app_client.get("/api/science/cases/not-a-real-case")
    assert response.status_code == 404
    assert isinstance(response.json()["detail"], str)
    assert "code" not in response.json()


# ---------------------------------------------------------------------------
# Phase 5A.2C -- extended case-index selector/casebook metadata
# ---------------------------------------------------------------------------


def test_case_index_never_fabricates_metadata_for_ineligible_cases(client: TestClient) -> None:
    """A case outside the deterministic-eligible population has no frozen
    IMD pairing, so its event/valid-date fields must be null, never guessed."""
    cases = client.get("/api/science/operational/2024/cases", params={"page_size": 400}).json()["cases"]
    ineligible = next(c for c in cases if not c["deterministic_source_eligible"])
    assert ineligible["valid_date"] is None
    assert ineligible["event_heavy"] is None
    assert ineligible["event_very_heavy"] is None
    assert ineligible["selected_model_improved_vs_raw"] is None


def test_case_index_populates_event_flags_for_eligible_cases(client: TestClient) -> None:
    cases = client.get("/api/science/operational/2025/cases", params={"page_size": 400}).json()["cases"]
    eligible = [c for c in cases if c["deterministic_source_eligible"]]
    assert eligible, "expected at least one deterministic-eligible 2025 case"
    for case in eligible:
        assert case["valid_date"] is not None
        assert isinstance(case["event_heavy"], bool)
        assert isinstance(case["event_very_heavy"], bool)
        # A very-heavy event is definitionally also a heavy event.
        if case["event_very_heavy"]:
            assert case["event_heavy"] is True


def test_case_index_2025_improved_flag_matches_rmse_sign(client: TestClient) -> None:
    cases = client.get("/api/science/operational/2025/cases", params={"page_size": 400}).json()["cases"]
    scored = [c for c in cases if c["m1_minus_raw_rmse_mm"] is not None]
    assert scored, "expected at least one 2025 case with frozen case-level metrics"
    for case in scored:
        assert case["selected_model_improved_vs_raw"] == (case["m1_minus_raw_rmse_mm"] < 0)


def test_case_index_lead_label_and_calendar_fields_are_consistent(client: TestClient) -> None:
    cases = client.get("/api/science/operational/2025/cases", params={"page_size": 5}).json()["cases"]
    for case in cases:
        assert case["lead_label"] == f"Day {case['lead_hours'] // 24}"
        assert case["initialization_utc"].startswith(case["initialization_date"])
        assert case["month"] == int(case["initialization_date"][5:7])


def test_case_index_pseudo_regime_class_only_when_regime_eligible(client: TestClient) -> None:
    for year in (2023, 2024, 2025):
        cases = client.get(f"/api/science/operational/{year}/cases", params={"page_size": 20}).json()["cases"]
        for case in cases:
            if case["regime_source_eligible"]:
                assert case["pseudo_regime_class"] in (
                    "ACTIVE_MONSOON", "BREAK_WEAK_MONSOON", "LOW_DEPRESSION_INFLUENCED",
                )
            else:
                assert case["pseudo_regime_class"] is None


def test_no_model_execution_in_operational_module() -> None:
    """The operational router's own source must not train or re-run inference."""
    import inspect
    try:
        from backend.app.api import operational as op_module
    except ModuleNotFoundError:
        from app.api import operational as op_module
    source = inspect.getsource(op_module)
    for forbidden in ("XGBRegressor", ".fit(", "joblib.load", "train_test_split"):
        assert forbidden not in source
