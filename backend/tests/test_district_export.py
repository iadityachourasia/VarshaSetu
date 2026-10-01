"""District export (CSV/JSON): equals the served comparison exactly, carries provenance, and refuses what the comparison refuses."""

from __future__ import annotations

import csv
import io
import json

import pytest
from fastapi.testclient import TestClient

BASE = "/api/science/operational"
CASES = [(2024, "20240718_day2_24h"), (2025, "20250714_day2_24h")]


@pytest.fixture(scope="module")
def client() -> TestClient:
    from backend.main import app
    return TestClient(app)


def _rows(response):
    return list(csv.DictReader(io.StringIO(response.text)))


@pytest.mark.parametrize("year,case_id", CASES)
def test_csv_equals_the_served_comparison_and_carries_provenance(client, year, case_id):
    compare = client.get(f"{BASE}/{year}/cases/{case_id}/districts/compare")
    export = client.get(f"{BASE}/{year}/cases/{case_id}/districts/export?format=csv")
    assert compare.status_code == 200 and export.status_code == 200
    assert export.headers["content-type"].startswith("text/csv") and "attachment" in export.headers["content-disposition"] and case_id in export.headers["content-disposition"]
    body, rows = compare.json(), _rows(export)
    assert len(rows) == len(body["districts"]) > 0
    assert export.headers["x-weights-sha256"] == body["weights_sha256"] and export.headers["x-geometry-sha256"] == body["geometry_sha256"]
    for row, district in zip(rows, body["districts"]):
        assert row["district_id"] == district["district_id"] and row["district_name"] == district["district_name"]
        assert row["year_role"] == body["year_role"] and row["weights_sha256"] == body["weights_sha256"] and row["units"] == "mm/24h"
        assert "not an operational warning" in row["label"] and row["case_id"] == case_id
        assert float(row["observed_mean_mm"]) == district["observed_mean_mm"] and float(row["raw_error_mm"]) == district["raw_error_mm"]
        for model, cell in district["models"].items():
            assert float(row[f"{model}_mean_mm"]) == cell["mean_mm"] and float(row[f"{model}_improvement_vs_raw_mm"]) == cell["improvement_vs_raw_mm"]
            assert float(row[f"{model}_error_mm"]) == pytest.approx(cell["mean_mm"] - district["observed_mean_mm"], abs=1e-9)
            assert float(row[f"{model}_improvement_vs_raw_mm"]) == pytest.approx(abs(district["raw_error_mm"]) - abs(cell["error_mm"]), abs=1e-9)


def test_2025_export_keeps_the_final_test_role_and_json_matches(client):
    year, case_id = CASES[1]
    export = client.get(f"{BASE}/{year}/cases/{case_id}/districts/export?format=json")
    body = json.loads(export.text)
    assert body["schema"] == "varshasetu-district-export-v1" and body["year_role"] == "FINAL_TEST_COMPLETED" and body["caveats"]
    assert body["districts"] == client.get(f"{BASE}/{year}/cases/{case_id}/districts/compare").json()["districts"]


def test_unknown_case_unknown_format_and_unknown_year_are_refused(client):
    assert client.get(f"{BASE}/2025/cases/19000101_day1_24h/districts/export").status_code in (404, 409, 422)
    assert client.get(f"{BASE}/2025/cases/{CASES[1][1]}/districts/export?format=xlsx").status_code == 422
    assert client.get(f"{BASE}/2031/cases/{CASES[1][1]}/districts/export").status_code in (404, 422)
