"""Raw all-India verification (protocol v1, docs/140): hash chain, internal consistency of the stored statistics, honest labels, API, tamper refusal, and (locally) an independent recomputation."""

from __future__ import annotations

import hashlib
import json
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pytest
from fastapi.testclient import TestClient

from backend.app.api import all_india_raw as api
from backend.app.ml import all_india_raw as air

ROOT = Path(__file__).resolve().parents[2]
PHASE14 = ROOT / "backend/app/evidence_data/phase14"
BASE = "/api/science/evidence/all-india-raw"
YEARS = (2023, 2024, 2025)


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(name: str) -> dict:
    return json.loads((PHASE14 / name).read_text(encoding="utf-8"))


PROTOCOL, MANIFEST, LEDGER = load("all_india_raw_protocol_v1.json"), load("all_india_raw_manifest.json"), load("all_india_raw_ledger_v1.json")
RESULTS = {y: load(f"all_india_raw_{y}.json") for y in YEARS}


@pytest.fixture(scope="module")
def client() -> TestClient:
    from backend.main import app
    return TestClient(app)


@pytest.fixture(autouse=True)
def _fresh():
    api._chain.cache_clear()
    api._result.cache_clear()
    yield
    api._chain.cache_clear()
    api._result.cache_clear()


def test_hash_chain():
    assert (PHASE14 / "all_india_raw_protocol_v1.sha256").read_text(encoding="ascii").split()[0] == sha(PHASE14 / "all_india_raw_protocol_v1.json")
    assert (PHASE14 / "all_india_raw_manifest.sha256").read_text(encoding="ascii").split()[0] == sha(PHASE14 / "all_india_raw_manifest.json")
    ledger_sha = sha(PHASE14 / "all_india_raw_ledger_v1.json")
    assert PROTOCOL["definition"]["ledger_file_sha256"] == MANIFEST["ledger_file_sha256"] == ledger_sha and MANIFEST["protocol_sha256"] == sha(PHASE14 / "all_india_raw_protocol_v1.json")
    assert set(MANIFEST["files"]) == {f"all_india_raw_{y}.json" for y in YEARS}
    for name, entry in MANIFEST["files"].items():
        assert sha(PHASE14 / name) == entry["sha256"] and load(name)["protocol_sha256"] == MANIFEST["protocol_sha256"]


def test_the_protocol_is_raw_only_descriptive_and_freezes_the_regions_before_scoring():
    assert PROTOCOL["no_observation_read"] is True and "Nothing is fitted or corrected" in PROTOCOL["purpose"]
    assert PROTOCOL["decision_rule"].startswith("none: the analysis is descriptive")
    regions = PROTOCOL["definition"]["regions"]
    lat = np.array(LEDGER["grid"]["latitude"])
    lon = np.array(LEDGER["grid"]["longitude"])
    masks = air.region_masks(lat, lon)
    assert regions["cell_counts"] == {name: int(masks[name].sum()) for name in air.REGIONS} and regions["all_scored_cells"] == int(masks["ALL"].sum())
    assert (len(lat), len(lon)) == (129, 135) and lat[0] == 6.5 and lat[-1] == 38.5 and lon[0] == 66.5 and lon[-1] == 100.0
    assert any("no model was applied there" in item for item in PROTOCOL["not_established_whatever_the_result"])
    assert "applying or training any model on the all-India fields" in PROTOCOL["forbidden"]
    labels = {y: PROTOCOL["populations"][str(y)]["label"] for y in YEARS}
    assert labels[2025] == "POST-HOC EXPLORATORY ANALYSIS OF THE COMPLETED 2025 FINAL TEST" and "training year of the downstream models" in labels[2023] and "development" in labels[2024]


def test_ledger_counts_match_the_protocol_and_every_included_case_has_a_hash_and_no_excluded_case_has_one():
    for year in YEARS:
        rows = LEDGER["populations"][str(year)]
        counts = {}
        for r in rows:
            counts[r["status"]] = counts.get(r["status"], 0) + 1
            assert (r["status"] == "INCLUDED") == (r["sha256"] is not None and r["path"] is not None), r["case_id"]
            if r["status"] == "INCLUDED":
                assert r["regional_qc_pass"] is True
        assert counts == PROTOCOL["populations"][str(year)]["forecast_only_status_counts"]
        assert RESULTS[year]["cases_scored"] == counts["INCLUDED"] and RESULTS[year]["excluded_cases"] == {s: n for s, n in counts.items() if s != "INCLUDED"}
        assert len(rows) == 375


def test_stored_statistics_are_internally_consistent():
    for year, result in RESULTS.items():
        metrics, gate = result["metrics"], result["support"]
        assert result["reproduction"]["status"] == "REPRODUCED" and result["paired_cells_outside_every_region"] == 0
        assert metrics["ALL_INDIA"]["cell_count"] == sum(metrics[r]["cell_count"] for r in air.REGIONS)
        assert result["region_cells_with_observation"]["INSIDE_MODEL_DOMAIN"] == 1301                         # the regional footprint
        assert result["region_cells_with_observation"]["ALL_INDIA"] == sum(result["region_cells_with_observation"][r] for r in air.REGIONS)
        for name in air.NAMES:
            m = metrics[name]
            assert m["continuous_supported"] == gate[name]["continuous_supported"] and ("rmse_mm" in m) == m["continuous_supported"]
            for threshold in ("heavy", "very_heavy"):
                cat = m["categorical"][threshold]
                if gate[name][threshold]["supported"]:
                    h, mi, fa = cat["hits"], cat["misses"], cat["false_alarms"]
                    assert cat["observed_event_count"] == h + mi == gate[name][threshold]["observed_event_pairs"] and cat["forecast_event_count"] == h + fa
                    assert cat["CSI"] == pytest.approx(h / (h + mi + fa)) and cat["POD"] == pytest.approx(h / (h + mi)) and cat["frequency_bias"] == pytest.approx((h + fa) / (h + mi))
                else:
                    assert cat["status"] == "insufficient_support" and "CSI" not in cat
            for metric, entry in result["bootstrap"]["intervals"][name].items():
                if entry["status"] == "ok":
                    low, high = entry["interval95"]
                    assert low <= entry["point"] <= high and entry["excludes_zero"] == (low > 0 or high < 0)
            if m["continuous_supported"]:
                assert result["bootstrap"]["intervals"][name]["rmse"]["point"] == pytest.approx(m["rmse_mm"])


def test_recorded_findings_raw_heavy_rain_skill_is_low_everywhere_and_the_east_has_a_wet_bias():
    for year, result in RESULTS.items():
        for name in air.NAMES:
            heavy = result["metrics"][name]["categorical"]["heavy"]
            if "CSI" in heavy:
                assert heavy["CSI"] < 0.1 and heavy["frequency_bias"] < 1.0, (year, name)       # Raw under-forecasts heavy rain in every supported region: stated, not hidden
        east = result["bootstrap"]["intervals"]["EAST_AND_NORTH_EAST"]["bias"]
        assert east["status"] == "ok" and east["interval95"][0] > 0 and result["metrics"]["INSIDE_MODEL_DOMAIN"]["bias_mm"] < 0


def test_why_the_stage_one_comparison_was_not_applied_is_recorded():
    for result in RESULTS.values():
        assert result["reproduction"]["stage1_comparison"]["compared"] is False and "populations differ" in result["reproduction"]["stage1_comparison"]["reason"]
        assert result["excluded_cases"].get("EXCLUDED_WIDE_RECONSTRUCTION", 0) > 0


@pytest.mark.parametrize("year", YEARS)
def test_the_api_serves_the_frozen_files(client, year):
    result = client.get(f"{BASE}/result?year={year}").json()
    assert result["payload"] == load(f"all_india_raw_{year}.json") and result["year"] == year
    assert result["evidence_label"].startswith("POST-HOC") == (year == 2025)
    assert any("Raw only" in c for c in result["caveats"]) and any("not meteorological regimes" in c for c in result["caveats"])


def test_overview_and_unknown_year(client):
    body = client.get(f"{BASE}/overview").json()
    assert [a["year"] for a in body["available"]] == list(YEARS) and body["protocol_sha256"] == sha(PHASE14 / "all_india_raw_protocol_v1.json")
    assert body["decision_rule"].startswith("none") and "Nothing is fitted" in body["purpose"]
    for year in (2022, 2021):
        response = client.get(f"{BASE}/result?year={year}")
        assert response.status_code == 404 and response.json()["code"] == "SCIENCE_PRODUCT_UNAVAILABLE"


@pytest.mark.parametrize("victim", ["all_india_raw_2025.json", "all_india_raw_protocol_v1.json", "all_india_raw_manifest.json", "all_india_raw_ledger_v1.json"])
def test_tampered_evidence_is_refused(client, monkeypatch, victim):
    real = api.sha256_file
    monkeypatch.setattr(api, "sha256_file", lambda path: "0" * 64 if path.name == victim else real(path))
    response = client.get(f"{BASE}/overview")
    assert response.status_code == 503 and response.json()["code"] == "SCIENCE_INTEGRITY_FAILURE"


LOCAL = pytest.mark.skipif(not (ROOT / "experiments/recent_historical/imd/RF25_ind2025_rfp25.nc").exists() or not (ROOT / "data/operational_derived/all_india_raw_v1/2025").exists(),
                           reason="local IMD file or the frozen cache is not present")


@LOCAL
def test_an_independent_plain_loop_reproduces_the_stored_2025_region_statistics():
    """Recompute the pooled RMSE, bias and heavy-rain hits per region with a separate code path (backend IMD reader and an explicit per-cell loop) and compare with the stored evidence."""
    from backend.app.data_sources.imd_rainfall import load_imd_day
    lat, lon = np.array(LEDGER["grid"]["latitude"]), np.array(LEDGER["grid"]["longitude"])
    names = air.REGIONS
    n = {r: 0 for r in names}
    err = {r: 0.0 for r in names}
    sq = {r: 0.0 for r in names}
    hits = {r: 0 for r in names}
    imd = ROOT / "experiments/recent_historical/imd/RF25_ind2025_rfp25.nc"
    for row in LEDGER["populations"]["2025"]:
        if row["status"] != "INCLUDED":
            continue
        offset = {"day1_24h": 1, "day2_24h": 2, "day3_24h": 3}[row["product"]]
        day = date.fromisoformat(row["initialization"]) + timedelta(days=offset)
        obs = load_imd_day(imd, day, south=6.5, north=38.5, west=66.5, east=100.0)
        field = np.load(ROOT / row["path"], allow_pickle=False)
        for i, a in enumerate(lat):
            for j, b in enumerate(lon):
                if not obs.valid_mask[i, j]:
                    continue
                region = air.region_of(float(a), float(b))
                if region is None:
                    continue
                e = float(field[i, j]) - float(obs.rainfall_mm[i, j])
                n[region] += 1
                err[region] += e
                sq[region] += e * e
                hits[region] += int(np.float32(obs.rainfall_mm[i, j]) >= np.float32(64.5) and np.float32(field[i, j]) >= np.float32(64.5))
    stored = RESULTS[2025]["metrics"]
    for r in names:
        assert stored[r]["cell_count"] == n[r]
        assert stored[r]["bias_mm"] == pytest.approx(err[r] / n[r], rel=1e-9, abs=1e-12) and stored[r]["rmse_mm"] == pytest.approx(np.sqrt(sq[r] / n[r]), rel=1e-9)
        heavy = stored[r]["categorical"]["heavy"]
        if "hits" in heavy:
            assert heavy["hits"] == hits[r]
