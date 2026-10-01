"""Phase 6 evidence (docs/108): tracked pure diagnostics code, packaged evidence files and the read-only API.

These tests need no untracked data: the evidence is tied back to the tracked frozen Phase 2B results, so
they run on a fresh clone and in the deployed image.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest
from fastapi.testclient import TestClient

from backend.app.api import evidence
from backend.app.ml.phase2b import event_metrics
from backend.app.ml.phase2c import fss_many
from backend.app.ml.verification_extra import (MODELS, REGIMES, Population, analyse, assert_counts_match_event_metrics,
                                               case_counts, categorical_from_counts, fss_components, fss_from_components,
                                               paired_case_bootstrap, to_field)

ROOT = Path(__file__).resolve().parents[2]
PHASE2B = ROOT / "data/manifests/phase2b"
COMBOS = [("A", 2018), ("A", 2019), ("B", 2024), ("B", 2025)]
MODEL_KEYS = {"M0": "M0_RAW_GEFS", "M1": "M1_LINEAR_RIDGE_MOS", "M2": "M2_GLOBAL_XGBOOST",
              "M3": "M3_HARD_REGIME_XGBOOST", "M4": "M4_SOFT_REGIME_MOE"}


@pytest.fixture(scope="module")
def client() -> TestClient:
    from backend.main import app
    return TestClient(app)


@pytest.fixture(autouse=True)
def _fresh_caches():
    for cache in (evidence._manifest, evidence._evidence, evidence._district_manifest, evidence._district_evidence):
        cache.cache_clear()
    yield
    for cache in (evidence._manifest, evidence._evidence, evidence._district_manifest, evidence._district_evidence):
        cache.cache_clear()


# ---- pure diagnostics (no data needed) ---------------------------------------------------------


def _cases(seed=0, n=6):
    rng = np.random.default_rng(seed)
    out = []
    for _ in range(n):
        mask = rng.random((49, 49)) > 0.3
        obs = np.where(rng.random((49, 49)) > 0.85, rng.uniform(60, 130, (49, 49)), rng.uniform(0, 30, (49, 49)))
        fc = np.where(rng.random((49, 49)) > 0.85, rng.uniform(60, 130, (49, 49)), rng.uniform(0, 30, (49, 49)))
        out.append({"forecast": fc, "observed": obs, "mask": mask})
    return out


@pytest.mark.parametrize("threshold,size", [(64.5, 1), (64.5, 3), (115.6, 5), (64.5, 9)])
def test_component_fss_reproduces_frozen_fss_many(threshold, size):
    cases = _cases()
    comps = [fss_components(c["forecast"], c["observed"], c["mask"], threshold, size) for c in cases]
    mine, frozen = fss_from_components(comps), fss_many(cases, threshold, size)
    assert mine["fss"] == pytest.approx(frozen["fss"], abs=1e-12) and mine["case_count"] == frozen["case_count"]


def test_counts_route_equals_frozen_event_metrics_and_bootstrap_is_seeded_and_paired():
    rng = np.random.default_rng(3)
    obs, fc = rng.uniform(0, 140, 4000), rng.uniform(0, 140, 4000)
    for threshold in (64.5, 115.6):
        assert_counts_match_event_metrics(obs, fc, threshold)
    assert_counts_match_event_metrics(obs, np.zeros_like(fc), 64.5)
    assert categorical_from_counts(case_counts(np.zeros(5), np.zeros(5), 64.5))["CSI"] is None
    per_case = rng.integers(0, 20, size=(40, 2, 4)).astype(float)
    per_case[:, 1] = per_case[:, 0]

    def diff(total):
        return float(total[0, 0] - total[1, 0])
    a, b = paired_case_bootstrap(per_case, diff, repeats=100), paired_case_bootstrap(per_case, diff, repeats=100)
    assert a == b and a["interval95"] == [0.0, 0.0]


def test_to_field_rejects_bad_pixel_maps():
    with pytest.raises(ValueError):
        to_field(np.ones(2), np.array([4, 4]))
    with pytest.raises(ValueError):
        to_field(np.ones(1), np.array([2401]))


def test_analyse_partitions_a_synthetic_population_consistently():
    rng = np.random.default_rng(11)
    n_cases, cells = 9, 300
    cases, pix, y, prob = [], [], [], []
    for i in range(n_cases):
        cases.append({"case_id": f"2019-06-0{i % 9 + 1}T00:00:00Z|day{i % 3 + 1}_24h", "row_start": i * cells, "row_count": cells})
        pix.append(rng.choice(2401, cells, replace=False))
        y.append(np.where(rng.random(cells) > 0.9, rng.uniform(65, 130, cells), rng.uniform(0, 30, cells)))
        prob.append(np.eye(3)[i % 3])
    y, pix = np.concatenate(y).astype(np.float32), np.concatenate(pix)
    preds = {m: np.maximum(0, y + rng.normal(0, 10, y.size)).astype(np.float32) for m in MODELS}
    result = analyse(Population(2019, cases, y, pix, preds, np.stack(prob), {}))
    assert sum(b["case_count"] for b in result["by_predicted_regime"].values()) == n_cases
    assert sum(b["case_count"] for b in result["by_lead_day"].values()) == n_cases
    for threshold in ("heavy", "very_heavy"):
        parts = sum(b["categorical"][threshold]["M0"]["observed_event_count"] for b in result["by_predicted_regime"].values())
        assert parts == result["overall"]["categorical"][threshold]["M0"]["observed_event_count"]
    thr = 64.5
    assert result["overall"]["categorical"]["heavy"]["M2"]["hits"] == event_metrics(y, preds["M2"], thr)["hits"]


# ---- packaged evidence ---------------------------------------------------------------------------


def test_manifest_and_every_file_hash_verify():
    manifest, digest = evidence._manifest()
    assert digest == (evidence.PHASE6 / "evidence_manifest.sha256").read_text(encoding="ascii").strip()
    assert sorted((e["track"], e["year"]) for e in manifest["files"].values()) == COMBOS
    for name in manifest["files"]:
        data, file_digest = evidence._evidence(name)
        assert data["reproduction"]["status"] == "REPRODUCED" and len(file_digest) == 64


@pytest.mark.parametrize("track,year", COMBOS)
def test_each_evidence_file_is_internally_consistent(track, year):
    data, _ = evidence._evidence(f"regime_verification_{track}_{year}.json")
    n = data["case_count"]
    assert sum(b["case_count"] for b in data["by_predicted_regime"].values()) == n
    assert sum(b["case_count"] for b in data["by_lead_day"].values()) == n
    assert list(data["by_predicted_regime"]) == list(REGIMES)
    for t in ("heavy", "very_heavy"):
        whole = data["overall"]["categorical"][t]
        for m in MODELS:
            assert whole[m]["hits"] + whole[m]["misses"] == whole["M0"]["observed_event_count"]
            assert sum(b["categorical"][t][m]["hits"] for b in data["by_predicted_regime"].values()) == whole[m]["hits"]
            assert sum(b["categorical"][t][m]["false_alarms"] for b in data["by_lead_day"].values()) == whole[m]["false_alarms"]
            for s in ("1", "3", "5", "9"):
                value = data["overall"]["fss"][t][s]["all_cases"][m]["fss"]
                assert value is None or 0.0 <= value <= 1.0
    assert data["evidence_role"] in evidence.EVIDENCE_LABELS


def test_track_a_evidence_equals_the_frozen_phase2b_results():
    """Ties the tracked evidence to the tracked frozen numbers (no untracked cache required)."""
    final = json.loads((PHASE2B / "2019_final_results.json").read_text(encoding="utf-8"))["test_results"]
    validation = json.loads((PHASE2B / "model_selection_freeze.json").read_text(encoding="utf-8"))["validation_results"]
    for year, frozen in ((2019, final), (2018, validation)):
        data, _ = evidence._evidence(f"regime_verification_A_{year}.json")
        assert data["reproduction"]["counts_exact"] is True and data["reproduction"]["max_abs_diff"] < 1e-6
        for model, key in MODEL_KEYS.items():
            ref, mine = frozen[key]["overall"], data["overall"]
            assert mine["continuous"][model]["rmse_mm"] == pytest.approx(ref["continuous"]["rmse_mm"], abs=1e-6)
            for name, label in (("heavy_64_5", "heavy"), ("very_heavy_115_6", "very_heavy")):
                for k in ("hits", "misses", "false_alarms"):
                    assert mine["categorical"][label][model][k] == ref["thresholds"][name][k]
            for hours, block in frozen[key]["by_lead_hours"].items():
                mine_lead = data["by_lead_day"][f"day{int(hours) // 24}"]
                assert mine_lead["categorical"]["heavy"][model]["hits"] == block["thresholds"]["heavy_64_5"]["hits"]
            for rid, block in frozen[key]["by_forecast_only_regime"].items():
                mine_reg = data["by_predicted_regime"][REGIMES[int(rid)]]
                assert mine_reg["continuous"][model]["rmse_mm"] == pytest.approx(block["continuous"]["rmse_mm"], abs=1e-6)


def test_track_b_2025_evidence_equals_the_frozen_phase4j_regime_metrics():
    data, _ = evidence._evidence("regime_verification_B_2025.json")
    # docs/89 section 20 frozen by-predicted-regime RMSE (M2/M3/M4), independent of this phase
    assert data["by_predicted_regime"]["LOW_DEPRESSION_INFLUENCED"]["continuous"]["M3"]["rmse_mm"] == pytest.approx(16.59550041612725, abs=1e-9)
    assert data["overall"]["continuous"]["M1"]["rmse_mm"] == pytest.approx(15.5736, abs=5e-4)
    assert data["overall"]["continuous"]["M0"]["rmse_mm"] == pytest.approx(16.1657, abs=5e-4)


# ---- API -----------------------------------------------------------------------------------------


@pytest.mark.parametrize("track,year", COMBOS)
def test_endpoint_serves_file_content_with_mandatory_label(client, track, year):
    response = client.get("/api/science/evidence/regime-verification", params={"track": track, "year": year})
    assert response.status_code == 200, response.text
    body = response.json()
    data, digest = evidence._evidence(f"regime_verification_{track}_{year}.json")
    assert body["overall"] == data["overall"] and body["evidence_sha256"] == digest
    assert body["evidence_label"] == evidence.EVIDENCE_LABELS[data["evidence_role"]]
    assert "reproduction" in body and "checks" not in body["reproduction"]
    if year in (2019, 2025):
        assert body["evidence_label"] == f"POST-HOC EXPLORATORY ANALYSIS OF THE COMPLETED {year} FINAL TEST"
    summary = body["summary"]
    assert summary["undefined_fss_cases"]["heavy"]["3"]["M0"] == summary["case_count"] - summary["defined_fss_cases"]["heavy"]["3"]["M0"]
    assert any("pseudo-label" in c for c in body["caveats"])


def test_manifest_endpoint_and_unavailable_and_invalid_requests(client):
    manifest = client.get("/api/science/evidence/manifest")
    assert manifest.status_code == 200 and len(manifest.json()["manifest_sha256"]) == 64
    missing = client.get("/api/science/evidence/regime-verification", params={"track": "A", "year": 2017})
    assert missing.status_code == 404 and missing.json()["code"] == "SCIENCE_PRODUCT_UNAVAILABLE"
    assert client.get("/api/science/evidence/regime-verification", params={"track": "C", "year": 2019}).status_code == 422


def test_tampered_file_is_refused_with_an_integrity_failure(client, monkeypatch):
    real = evidence.sha256_file
    monkeypatch.setattr(evidence, "sha256_file", lambda path: "0" * 64 if path.name == "regime_verification_B_2025.json" else real(path))
    response = client.get("/api/science/evidence/regime-verification", params={"track": "B", "year": 2025})
    assert response.status_code == 503 and response.json()["code"] == "SCIENCE_INTEGRITY_FAILURE"
    assert client.get("/api/science/evidence/regime-verification", params={"track": "B", "year": 2024}).status_code == 200


def test_tampered_manifest_is_refused(client, monkeypatch):
    real = evidence.sha256_file
    monkeypatch.setattr(evidence, "sha256_file", lambda path: "f" * 64 if path.name == "evidence_manifest.json" else real(path))
    assert client.get("/api/science/evidence/manifest").status_code == 503


def test_an_unregistered_evidence_role_is_never_served(client, monkeypatch):
    role = "PHASE4J_HOLDOUT_CONSUMED_POST_HOC_DESCRIPTIVE_ONLY"
    monkeypatch.setattr(evidence, "EVIDENCE_LABELS", {k: v for k, v in evidence.EVIDENCE_LABELS.items() if k != role})
    response = client.get("/api/science/evidence/regime-verification", params={"track": "B", "year": 2025})
    assert response.status_code == 503


# ---- verification report export ------------------------------------------------------------------


def _report(client, track, year, fmt):
    response = client.get("/api/science/evidence/report", params={"track": track, "year": year, "format": fmt})
    assert response.status_code == 200, response.text
    return response


@pytest.mark.parametrize("track,year", COMBOS)
def test_every_report_format_carries_the_mandatory_label_hash_and_attachment_headers(client, track, year):
    data, digest = evidence._evidence(f"regime_verification_{track}_{year}.json")
    label = evidence.EVIDENCE_LABELS[data["evidence_role"]]
    for fmt, media in (("md", "text/markdown"), ("csv", "text/csv"), ("json", "application/json")):
        response = _report(client, track, year, fmt)
        assert response.headers["content-type"].startswith(media)
        assert f'filename="varshasetu_verification_{track}_{year}.{fmt}"' in response.headers["content-disposition"]
        assert response.headers["x-evidence-sha256"] == digest
    assert label in _report(client, track, year, "md").text and digest in _report(client, track, year, "md").text
    body = _report(client, track, year, "json").json()
    assert body["evidence_label"] == label and body["evidence_sha256"] == digest and body["caveats"]
    assert {r["evidence_role"] for r in [{"evidence_role": body["evidence_role"]}]} == {data["evidence_role"]}


@pytest.mark.parametrize("track,year", COMBOS)
def test_csv_and_json_rows_equal_the_evidence_values_exactly(client, track, year):
    import csv
    import io

    data, _ = evidence._evidence(f"regime_verification_{track}_{year}.json")
    rows = list(csv.DictReader(io.StringIO(_report(client, track, year, "csv").text)))
    json_rows = _report(client, track, year, "json").json()["rows"]
    assert len(rows) == len(json_rows) > 1000
    lookup = {(r["group_type"], r["group"], r["model"], r["threshold"], r["metric"], r["scale"]): r for r in rows}
    # spot-check every model/metric family against the evidence file
    for model in MODELS:
        for threshold in ("heavy", "very_heavy"):
            event = data["overall"]["categorical"][threshold][model]
            for metric in ("POD", "FAR", "CSI", "ETS"):
                cell = lookup[("overall", "all cases", model, threshold, metric, "")]
                assert (cell["value"] == "") == (event[metric] is None)
                if event[metric] is not None:
                    assert float(cell["value"]) == pytest.approx(event[metric], abs=1e-12)
            for scale in ("1", "3", "5", "9"):
                score = data["overall"]["fss"][threshold][scale]["all_cases"][model]
                cell = lookup[("overall", "all cases", model, threshold, "FSS", f"{scale}x{scale}")]
                assert (cell["value"] == "") == (score["fss"] is None) and int(cell["defined_cases"]) == score["case_count"]
        assert float(lookup[("overall", "all cases", model, "", "RMSE (mm)", "")]["value"]) == pytest.approx(data["overall"]["continuous"][model]["rmse_mm"], abs=1e-12)
    for name, block in data["by_predicted_regime"].items():
        assert float(lookup[("regime", name, "M3", "heavy", "CSI", "")]["value"] or 0) == pytest.approx(block["categorical"]["heavy"]["M3"]["CSI"] or 0, abs=1e-12)
    for name, block in data["by_lead_day"].items():
        assert int(lookup[("lead", name, "M0", "", "RMSE (mm)", "")]["case_count"]) == block["case_count"]
    undefined = [r for r in rows if r["value"] == ""]
    assert all(r["note"].startswith("undefined") for r in undefined)


def test_undefined_values_are_never_written_as_zero(client):
    # Track A 2019: M2/M3/M4 forecast no very-heavy event, so FAR is undefined (null), not 0.
    data, _ = evidence._evidence("regime_verification_A_2019.json")
    assert data["overall"]["categorical"]["very_heavy"]["M3"]["FAR"] is None
    md = _report(client, "A", 2019, "md").text
    assert "Very heavy >= 115.6 mm/24h - FAR | 0.8412 | 0.8800 | undefined | undefined | undefined" in md
    rows = _report(client, "A", 2019, "json").json()["rows"]
    far = [r for r in rows if r["group_type"] == "overall" and r["model"] == "M3" and r["threshold"] == "very_heavy" and r["metric"] == "FAR"]
    assert far and far[0]["value"] is None


def test_markdown_covers_every_ps_metric_and_every_group(client):
    md = _report(client, "B", 2025, "md").text
    for needle in ("RMSE (mm)", "POD", "FAR", "CSI", "ETS", "FSS 1x1", "FSS 3x3", "FSS 5x5", "FSS 9x9", "ACTIVE_MONSOON",
                   "BREAK_WEAK_MONSOON", "LOW_DEPRESSION_INFLUENCED", "Lead: Day 1", "Lead: Day 2", "Lead: Day 3",
                   "Paired differences", "Limitations", "pseudo-label", "POST-HOC EXPLORATORY ANALYSIS OF THE COMPLETED 2025 FINAL TEST"):
        assert needle in md, needle
    data, _ = evidence._evidence("regime_verification_B_2025.json")
    m3 = data["overall"]["categorical"]["heavy"]["M3"]["CSI"]
    assert f"| Heavy >= 64.5 mm/24h - CSI | " in md and f"{m3:.4f}" in md


def test_report_invalid_unavailable_and_tampered_requests(client, monkeypatch):
    assert client.get("/api/science/evidence/report", params={"track": "A", "year": 2019, "format": "pdf"}).status_code == 422
    missing = client.get("/api/science/evidence/report", params={"track": "B", "year": 2023})
    assert missing.status_code == 404 and missing.json()["code"] == "SCIENCE_PRODUCT_UNAVAILABLE"
    real = evidence.sha256_file
    monkeypatch.setattr(evidence, "sha256_file", lambda path: "0" * 64 if path.name == "regime_verification_A_2019.json" else real(path))
    tampered = client.get("/api/science/evidence/report", params={"track": "A", "year": 2019, "format": "md"})
    assert tampered.status_code == 503 and tampered.json()["code"] == "SCIENCE_INTEGRITY_FAILURE"


# ---- district-level verification (protocol v1, docs/112) -------------------------------------------

DV_YEARS = (2024, 2025)
PROTOCOL_SHA = "9b348063a6ac654e88a822694fd199d2f432d5d6b0bebafc19567f6be6e53365"


def _dv(year):
    return evidence._district_evidence(year)[0]


def test_protocol_is_the_approved_frozen_version_and_every_district_file_verifies():
    manifest, digest = evidence._district_manifest()
    assert manifest["protocol_sha256"] == PROTOCOL_SHA == evidence.sha256_file(evidence.PHASE6 / "district_verification_protocol_v1.json")
    protocol = evidence._protocol()
    assert protocol["status"] == "APPROVED_FOR_EXECUTION" and protocol["no_results_computed"] is True
    decisions = protocol["approval"]["decisions"]
    assert decisions["primary_event_definition"] == "E1_any_cell" and decisions["min_observed_events_per_district"] == 30
    assert protocol["coverage_rule"]["min_valid_cells_per_district_case"] == 5
    assert sorted(e["year"] for e in manifest["files"].values()) == list(DV_YEARS) and len(digest) == 64
    for year in DV_YEARS:
        data, file_digest = evidence._district_evidence(year)
        assert data["reproduction"]["status"] == "REPRODUCED" and data["protocol_sha256"] == PROTOCOL_SHA and len(file_digest) == 64
        assert data["evidence_role"] in evidence.EVIDENCE_LABELS


@pytest.mark.parametrize("year", DV_YEARS)
def test_district_evidence_reproduces_the_pre_registered_observation_only_counts(year):
    data, protocol = _dv(year), evidence._protocol()
    want = protocol["observation_only_support_counts"][str(year)]
    assert data["inclusion"]["district_case_pairs"] == want["district_case_pairs"] and data["inclusion"]["cases"] == want["cases"]
    assert data["inclusion"]["districts_included"] == protocol["observation_only_support_counts"]["districts_kept"] == 169
    assert len(data["inclusion"]["districts_excluded"]) == protocol["observation_only_support_counts"]["districts_excluded"] == 19
    for threshold in ("heavy", "very_heavy"):
        for definition in ("E1", "E2", "E3"):
            assert data["observed_events_pooled"][definition][threshold] == want[threshold][definition]["event_pairs"]
        assert data["supported_district_counts"]["E1"][threshold] == want[threshold]["E1"]["districts_ge_30"]
        assert data["supported_district_counts"]["E2"][threshold] == want[threshold]["E2"]["districts_ge_30"]


@pytest.mark.parametrize("year", DV_YEARS)
def test_district_evidence_is_internally_consistent(year):
    data = _dv(year)
    for definition in ("E1", "E2", "E3"):
        for threshold in ("heavy", "very_heavy"):
            block = data["categorical"][definition][threshold]
            for model in ("M0", "M1", "M2", "M3", "M4"):
                whole = block["pooled"]["all"][model]
                assert whole["hits"] + whole["misses"] == whole["observed_event_count"] == data["observed_events_pooled"][definition][threshold]
                for kind in ("by_lead", "by_regime", "by_region"):
                    for field in ("hits", "misses", "false_alarms", "sample_count"):
                        assert sum(g[model][field] for g in block[kind].values()) == whole[field], (definition, threshold, kind, model, field)
    for kind, members in data["continuous"].items():
        assert sum(v["M0"]["pairs"] for v in members.values()) == data["inclusion"]["district_case_pairs"], kind
    for definition in ("E1", "E2"):
        for threshold in ("heavy", "very_heavy"):
            assert sum(e["categorical"][definition][threshold]["observed_events"] for e in data["districts"]) == data["observed_events_pooled"][definition][threshold]
            for e in data["districts"]:
                cell = e["categorical"][definition][threshold]
                assert (cell["status"] == "supported") == (cell["observed_events"] >= 30) and (cell["models"] is None) == (cell["status"] != "supported")
    for model, counts in data["improved_worsened"].items():
        assert counts["improved"] + counts["worsened"] + counts["indeterminate"] + counts["undefined"] == counts["tested_districts"]
        assert counts["expected_by_chance_total"] == round(0.05 * counts["tested_districts"], 1)
    assert {e["region"] for e in data["districts"]} <= {"10-14N", "14-18N", "18-22N"}


def test_district_evidence_documents_the_frozen_protocol_in_its_payload_and_labels(client):
    for year in DV_YEARS:
        body = client.get("/api/science/evidence/district-verification", params={"year": year}).json()
        data, digest = evidence._district_evidence(year)
        assert body["evidence_sha256"] == digest and body["protocol_sha256"] == PROTOCOL_SHA and body["protocol_status"] == "APPROVED_FOR_EXECUTION"
        assert body["evidence_label"] == evidence.EVIDENCE_LABELS[data["evidence_role"]]
        assert body["districts"] == data["districts"] and body["categorical"] == data["categorical"]
        assert "reproduction" in body and "checks" not in body["reproduction"] and any("chance" in c for c in body["caveats"])
        assert body["protocol_decisions"]["regional_grouping"].startswith("three latitude bands")
    assert client.get("/api/science/evidence/district-verification", params={"year": 2025}).json()["evidence_label"] == "POST-HOC EXPLORATORY ANALYSIS OF THE COMPLETED 2025 FINAL TEST"


def test_district_reports_carry_label_hashes_and_never_write_undefined_as_zero(client):
    import csv
    import io

    for year in DV_YEARS:
        data, digest = evidence._district_evidence(year)
        label = evidence.EVIDENCE_LABELS[data["evidence_role"]]
        md = client.get("/api/science/evidence/district-verification/report", params={"year": year, "format": "md"})
        assert md.status_code == 200 and label in md.text and digest in md.text and PROTOCOL_SHA in md.text and "Expected by chance" in md.text
        assert f'filename="varshasetu_district_verification_B_{year}.md"' in md.headers["content-disposition"]
        body = client.get("/api/science/evidence/district-verification/report", params={"year": year, "format": "json"}).json()
        assert body["evidence_label"] == label and body["protocol_sha256"] == PROTOCOL_SHA and len(body["rows"]) > 5000
        text = client.get("/api/science/evidence/district-verification/report", params={"year": year, "format": "csv"}).text
        rows = list(csv.DictReader(io.StringIO(text)))
        assert len(rows) == len(body["rows"])
        assert not any(r["value"] == "0" and r["note"] == "undefined" for r in rows)
        assert all(r["note"] in ("undefined", "insufficient_support") for r in rows if r["value"] == "" and r["kind"] == "categorical")
    assert evidence._district_evidence(2025)[0]["categorical"]["E2"]["very_heavy"]["pooled"]["all"]["M2"]["FAR"] is None   # M2 forecasts no event


def test_district_endpoints_unavailable_year_and_tamper_are_refused(client, monkeypatch):
    assert client.get("/api/science/evidence/district-verification", params={"year": 2023}).status_code == 404
    assert client.get("/api/science/evidence/district-verification/report", params={"year": 2025, "format": "pdf"}).status_code == 422
    real = evidence.sha256_file
    for victim in ("district_verification_B_2025.json", "district_verification_manifest.json", "district_verification_protocol_v1.json"):
        evidence._district_manifest.cache_clear()
        evidence._district_evidence.cache_clear()
        monkeypatch.setattr(evidence, "sha256_file", lambda path, victim=victim: "0" * 64 if path.name == victim else real(path))
        response = client.get("/api/science/evidence/district-verification", params={"year": 2025})
        assert response.status_code == 503 and response.json()["code"] == "SCIENCE_INTEGRITY_FAILURE", victim
        monkeypatch.setattr(evidence, "sha256_file", real)
    evidence._district_manifest.cache_clear()
    evidence._district_evidence.cache_clear()
    assert client.get("/api/science/evidence/district-verification", params={"year": 2024}).status_code == 200
