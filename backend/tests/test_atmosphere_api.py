"""Synoptic data contract: the wide-domain atmosphere endpoint returns explicit, frozen coordinates alongside the 51x81 values."""

from __future__ import annotations

import numpy as np
import pytest
from fastapi.testclient import TestClient

from backend.app.data.monthly_qc import context_coordinates

BASE = "/api/science/operational"
CASE = "20250730_day1_24h"
FIELDS = ("u850", "v850", "q700", "z500", "mslp", "pwat")


@pytest.fixture(scope="module")
def client() -> TestClient:
    from backend.main import app
    return TestClient(app)


@pytest.mark.parametrize("field", FIELDS)
def test_every_field_carries_the_frozen_coordinates(client, field):
    body = client.get(f"{BASE}/2025/cases/{CASE}/atmosphere/{field}").json()
    latitude, longitude = context_coordinates()
    assert body["shape"] == [51, 81] and len(body["values"]) == 51 and all(len(row) == 81 for row in body["values"])
    assert body["latitude_centers"] == [float(v) for v in latitude] and body["longitude_centers"] == [float(v) for v in longitude]
    assert body["latitude_centers"][0] == 5.0 and body["latitude_centers"][-1] == 30.0
    assert body["longitude_centers"][0] == 55.0 and body["longitude_centers"][-1] == 95.0 and body["grid_spacing_degrees"] == 0.5
    assert "docs/121" in body["coordinate_note"] and "0.25 degree resolution" in body["coordinate_note"]


def test_values_are_physically_plausible_in_the_stated_orientation(client):
    """Row 0 is 5N, column 0 is 55E: in the monsoon season precipitable water is far larger over the Arabian Sea (5-15N, 55-70E) than
    over the dry Iran/Pakistan desert in the north-west of the domain (25-30N, 55-70E). A flipped grid would reverse this."""
    for case in ("20250730_day1_24h", "20250615_day2_24h", "20250901_day3_24h"):
        pwat = np.array(client.get(f"{BASE}/2025/cases/{case}/atmosphere/pwat").json()["values"], dtype=float)
        assert np.nanmean(pwat[0:20, 0:30]) > np.nanmean(pwat[40:51, 0:30]) + 15, case
    mslp = np.array(client.get(f"{BASE}/2025/cases/{CASE}/atmosphere/mslp").json()["values"], dtype=float)
    assert 90000 < np.nanmin(mslp) and np.nanmax(mslp) < 105000      # Pa


def test_unsupported_field_and_foreign_case_are_still_refused(client):
    assert client.get(f"{BASE}/2025/cases/{CASE}/atmosphere/rain").status_code == 404
    assert client.get(f"{BASE}/2024/cases/{CASE}/atmosphere/pwat").status_code == 404
