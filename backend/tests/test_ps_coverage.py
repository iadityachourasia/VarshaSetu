"""SIH26080 requirement-coverage manifest (P0-6): honesty guards, evidence-resolved facts and reachability data."""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend.app.api import evidence

ROOT = Path(__file__).resolve().parents[2]
RAW = json.loads(evidence.COVERAGE_FILE.read_text(encoding="utf-8"))
ROWS = {row["id"]: row for row in RAW["rows"]}
ROUTES = {"/", "/forecast", "/casebook", "/extremes", "/ensemble", "/regimes", "/districts", "/verification", "/observations", "/quality",
          "/methodology", "/audit", "/compliance", "/zones", "/geoaware", "/live"}
MUST_BE_PLANNED = ()
FORMATS = {"mm2", "score3", "int"}


@pytest.fixture(scope="module")
def client() -> TestClient:
    from backend.main import app
    return TestClient(app)


@pytest.fixture(autouse=True)
def _fresh():
    for cache in (evidence._coverage, evidence._manifest, evidence._evidence, evidence._district_manifest, evidence._district_evidence):
        cache.cache_clear()
    yield
    for cache in (evidence._coverage, evidence._manifest, evidence._evidence, evidence._district_manifest, evidence._district_evidence):
        cache.cache_clear()


def test_manifest_structure_vocabulary_and_unique_ids():
    assert RAW["status_vocabulary"] == ["IMPLEMENTED", "PARTIAL", "PLANNED"]
    assert len(ROWS) == len(RAW["rows"]) >= 25
    for row in RAW["rows"]:
        assert row["status"] in RAW["status_vocabulary"]
        assert row["requirement"].strip() and row["summary"].strip() and row["group"].strip()
        assert isinstance(row["ps_mandatory"], bool)


def test_every_official_ps_requirement_id_is_covered():
    covered = {pid for row in RAW["rows"] for pid in row["ps_ids"]}
    assert covered >= {f"PS-R{n:02d}" for n in range(1, 15)}


def test_missing_requirements_are_planned_never_implemented():
    for row_id in MUST_BE_PLANNED:
        row = ROWS[row_id]
        assert row["status"] == "PLANNED" and row["facts"] == [] and row["limitation"].strip(), row_id
    assert ROWS["REGIME-COASTAL-OROGRAPHIC"]["ps_mandatory"] and ROWS["REGIME-WESTERN-DISTURBANCE"]["ps_mandatory"]
    # the three regime rows became IMPLEMENTED only through the pre-registered sealed-year verdict (docs/142); each states what the verdict does not mean, and coastal/orographic never claims a specialist rainfall model
    for row_id in ("REGIME-CLASSIFIER", "REGIME-WESTERN-DISTURBANCE", "REGIME-COASTAL-OROGRAPHIC"):
        assert ROWS[row_id]["status"] == "IMPLEMENTED" and ROWS[row_id]["ps_mandatory"] and "docs/142_REFORECAST_STUDY_RESULTS.md" in ROWS[row_id]["docs"], row_id
        assert "not an expert analysis" in ROWS[row_id]["limitation"] and all(f["source"].startswith(("reforecast:", "zone:", "coastalregime:", "regime", "wdindicator:")) for f in ROWS[row_id]["facts"])
    assert "no specialist rainfall model" in ROWS["REGIME-COASTAL-OROGRAPHIC"]["limitation"] and any(p["href"] == "/zones" for p in ROWS["REGIME-COASTAL-OROGRAPHIC"]["pages"])
    assert "largely verifies the forecast height field" in ROWS["REGIME-WESTERN-DISTURBANCE"]["limitation"]
    assert ROWS["IMPROVEMENT-VS-RAW"]["status"] == "IMPLEMENTED" and ROWS["IMPROVEMENT-VS-RAW"]["ps_mandatory"] and "not untouched" in ROWS["IMPROVEMENT-VS-RAW"]["limitation"]
    # synoptic overlays now exist (docs/121); the row stays an extra, never mandatory, and states its scope limits
    assert ROWS["SYNOPTIC-OVERLAYS"]["status"] == "IMPLEMENTED" and not ROWS["SYNOPTIC-OVERLAYS"]["ps_mandatory"] and "Operational-era track only" in ROWS["SYNOPTIC-OVERLAYS"]["limitation"]


def test_independent_validation_is_partial_with_resolved_figures_and_states_what_it_could_not_validate():
    row = ROWS["REGIME-INDEPENDENT-VALIDATION"]
    assert row["status"] == "PARTIAL" and not row["ps_mandatory"] and len(row["facts"]) >= 4
    assert "depression is not validated" in row["limitation"] and "not the published classification" in row["limitation"]
    assert all(f["source"].startswith("regimeval:") for f in row["facts"])


def test_western_disturbance_is_implemented_through_the_sealed_verdict_and_keeps_the_earlier_negative_check_and_its_caveats(client):
    row = ROWS["REGIME-WESTERN-DISTURBANCE"]
    assert row["status"] == "IMPLEMENTED" and row["ps_mandatory"] and len([f for f in row["facts"] if f["source"].startswith("wdindicator:")]) >= 6 and len([f for f in row["facts"] if f["source"] == "reforecast:r03"]) == 3
    assert "no consistent link" in row["limitation"] and "largely verifies the forecast height field" in row["limitation"] and "not an expert analysis" in row["limitation"]
    assert row["pages"][0]["href"] == "/regimes" and "docs/138_WESTERN_DISTURBANCE_INDICATOR.md" in row["docs"]
    body = {r["id"]: r for r in client.get("/api/science/evidence/ps-coverage").json()["rows"]}["REGIME-WESTERN-DISTURBANCE"]
    low = next(f for f in body["facts"] if f["source"] == "wdindicator:2024" and "lower end" in f["label"])
    direct = json.loads((ROOT / "backend/app/evidence_data/phase13/wd_indicator_2024.json").read_text(encoding="utf-8"))
    assert low["value"] == direct["association"]["flagged_minus_not_flagged_mean_rain"]["interval95"][0]
    assert next(f for f in body["facts"] if f["source"] == "wdindicator:2025")["evidence_label"] == "POST-HOC EXPLORATORY ANALYSIS OF THE COMPLETED 2025 FINAL TEST"
    sealed = next(f for f in body["facts"] if f["source"] == "reforecast:r03" and "AUC on the sealed years" in f["label"])
    assert sealed["evidence_label"] == "POST-UNSEAL SEALED TEST 2014-2016: first use of these years"
    assert sealed["value"] == json.loads((ROOT / "backend/app/evidence_data/phase15/reforecast_r03_test.json").read_text(encoding="utf-8"))["tasks"]["WESTERN_DISTURBANCE"]["auc"]["point"]


def test_improvement_row_serves_the_2022_sealed_and_confirmatory_evidence_with_their_labels_and_states_the_failed_guardrail(client):
    row = ROWS["IMPROVEMENT-VS-RAW"]
    assert row["status"] == "IMPLEMENTED" and any(p["href"] == "/geoaware" for p in row["pages"]) and "guardrail failed" in row["limitation"] and "confirmatory" in row["limitation"]
    body = {r["id"]: r for r in client.get("/api/science/evidence/ps-coverage").json()["rows"]}["IMPROVEMENT-VS-RAW"]
    shown = [f for f in body["facts"] if f["source"] == "geofollow:2022"]
    assert len(shown) == 8 and all(f["evidence_label"] == "INDEPENDENT TEST: first use of this year" for f in shown)
    direct = json.loads((ROOT / "backend/app/evidence_data/phase11/geoaware_followup_test_2022.json").read_text(encoding="utf-8"))
    assert next(f for f in shown if "M0 Raw" in f["label"] and "heavy-rain CSI" in f["label"])["value"] == direct["pooled"]["M0"]["ALL"]["categorical"]["heavy"]["CSI"]
    primary = next(f for f in shown if "primary" in f["label"] and "lower end" in f["label"])
    assert primary["value"] < 0 < direct["pooled"]["B1#15"]["ALL"]["categorical"]["very_heavy"]["CSI"]          # the primary candidate's very-heavy interval includes zero
    reforecast = [f for f in body["facts"] if f["source"] == "reforecast:r05"]
    assert len(reforecast) == 9 and all(f["evidence_label"] == "POST-UNSEAL SEALED TEST 2014-2016: first use of these years" for f in reforecast)
    r05 = json.loads((ROOT / "backend/app/evidence_data/phase15/reforecast_r05_test.json").read_text(encoding="utf-8"))
    assert next(f for f in reforecast if "mean error of the event-weighted" in f["label"])["value"] == r05["pooled"]["B1"]["bias_mm"] > 1.5          # the failed guardrail is visible in the facts
    assert next(f for f in reforecast if "lower end of the 97.5" in f["label"])["value"] > 0                                                            # the very-heavy gain excludes zero
    confirm = [f for f in body["facts"] if f["source"] == "reforecast:r05c"]
    assert len(confirm) == 10 and all(f["evidence_label"] == "CONFIRMATORY TEST 2017-2019: no model of this study used these years (earlier Track A experiments did)" for f in confirm)
    c = json.loads((ROOT / "backend/app/evidence_data/phase15/reforecast_r05_confirmation.json").read_text(encoding="utf-8"))
    assert next(f for f in confirm if "before the mean-error correction" in f["label"])["value"] == c["pooled"]["B1_uncorrected"]["bias_mm"] > 1.5          # the drift is visible in the facts
    assert next(f for f in confirm if "after the mean-error correction" in f["label"])["value"] == c["pooled"]["B1_shifted"]["bias_mm"]


def test_live_inference_is_partial_labelled_unverified_and_makes_no_assumption_about_a_published_cycle():
    row = ROWS["LIVE-INFERENCE"]
    assert row["status"] == "PARTIAL" and not row["ps_mandatory"] and row["pages"][0]["href"] == "/live" and "docs/139_LIVE_CYCLE_WORKER.md" in row["docs"]
    assert "unverified" in row["limitation"] and "not an official warning" in row["limitation"] and "no live bundle" in row["limitation"] and "no scheduler" in row["limitation"].lower()
    assert row["facts"] == []                                                              # worker output is local and untracked: nothing is resolved from it


def test_all_india_domain_is_partial_raw_only_and_resolves_its_figures_from_the_frozen_evidence(client):
    row = ROWS["ALL-INDIA-DOMAIN"]
    assert row["status"] == "PARTIAL" and not row["ps_mandatory"] and row["pages"][0]["href"] == "/verification" and "docs/140_ALL_INDIA_RAW_VERIFICATION.md" in row["docs"]
    assert "Raw only" in row["limitation"] and "no model was applied or trained outside" in row["limitation"] and len(row["facts"]) == 12 and all(f["source"].startswith("allindia:") for f in row["facts"])
    body = {r["id"]: r for r in client.get("/api/science/evidence/ps-coverage").json()["rows"]}["ALL-INDIA-DOMAIN"]
    direct = json.loads((ROOT / "backend/app/evidence_data/phase14/all_india_raw_2025.json").read_text(encoding="utf-8"))
    east = next(f for f in body["facts"] if f["source"] == "allindia:2025" and "bias in east" in f["label"])
    assert east["value"] == direct["metrics"]["EAST_AND_NORTH_EAST"]["bias_mm"] and east["evidence_label"] == "POST-HOC EXPLORATORY ANALYSIS OF THE COMPLETED 2025 FINAL TEST"
    assert all(f["evidence_label"] == "2024 validation/selection year: development evidence" for f in body["facts"] if f["source"] == "allindia:2024")


def test_partial_and_planned_rows_state_their_gap_and_implemented_rows_are_reachable():
    for row in RAW["rows"]:
        if row["status"] in ("PARTIAL", "PLANNED"):
            assert len(row["limitation"].strip()) > 40, row["id"]
        if row["status"] == "IMPLEMENTED":
            assert row["pages"], f"{row['id']} is IMPLEMENTED but links to no page"
            assert row["docs"], f"{row['id']} is IMPLEMENTED but links to no evidence document"


def test_links_point_at_real_routes_and_real_documents():
    for row in RAW["rows"]:
        for page in row["pages"]:
            assert page["href"].split("?")[0] in ROUTES and page["label"].strip(), (row["id"], page)
        for doc in row["docs"]:
            assert (ROOT / doc).is_file(), (row["id"], doc)


def test_no_number_is_typed_into_status_text():
    pattern = re.compile(r"\d+(\.\d+)?\s*(%|mm\b|per cent)|\b\d+\.\d+\b")
    for row in RAW["rows"]:
        for field in ("requirement", "summary", "limitation"):
            assert not pattern.search(row[field]), (row["id"], field, row[field])


def test_facts_resolve_to_defined_numbers_from_hash_verified_evidence(client):
    body = client.get("/api/science/evidence/ps-coverage").json()
    assert body["counts"] == {s: sum(1 for r in RAW["rows"] if r["status"] == s) for s in RAW["status_vocabulary"]}
    assert body["mandatory_counts"]["IMPLEMENTED"] + body["mandatory_counts"]["PARTIAL"] + body["mandatory_counts"]["PLANNED"] == sum(1 for r in RAW["rows"] if r["ps_mandatory"])
    n_facts = 0
    for row in body["rows"]:
        for fact in row["facts"]:
            n_facts += 1
            assert isinstance(fact["value"], (int, float)) and fact["format"] in FORMATS and len(fact["source_sha256"]) == 64
            assert fact["evidence_label"] in evidence.EVIDENCE_LABELS.values()
    assert n_facts >= 25
    rows = {r["id"]: r for r in body["rows"]}
    direct = evidence._evidence("regime_verification_B_2025.json")[0]
    fact = next(f for f in rows["METRIC-FAR"]["facts"] if "M3" in f["label"])
    assert fact["value"] == direct["overall"]["categorical"]["heavy"]["M3"]["FAR"]
    assert next(f for f in rows["DISTRICT-VERIFICATION"]["facts"] if "districts with" in f["label"])["value"] == \
        evidence._district_evidence(2025)[0]["supported_district_counts"]["E1"]["heavy"]
    assert next(f for f in rows["REGIME-AWARE-CORRECTION"]["facts"] if "2019" in f["label"] and "M3" in f["label"])["evidence_label"] == \
        "POST-HOC EXPLORATORY ANALYSIS OF THE COMPLETED 2019 FINAL TEST"


def test_facts_use_only_allowed_sources_and_post_hoc_years_stay_labelled():
    for row in RAW["rows"]:
        for fact in row["facts"]:
            assert re.fullmatch(r"(regime:(A:(2018|2019)|B:(2024|2025))|district:(A:(2018|2019)|B:(2024|2025))|zone:(A:(2018|2019)|B:(2024|2025))|zoneforcing:(A:(2018|2019)|B:(2024|2025))|regimeval:(A:(2018|2019)|B:(2024|2025))|coastalregime:(A:(2018|2019)|B:(2024|2025))|wdindicator:(2021|2022|2024|2025)|geofollow:2022|allindia:(2023|2024|2025)|reforecast:(r05|r03|r05c))", fact["source"]), fact
            assert fact["pointer"].startswith("/") and fact["label"].strip()


def test_unresolvable_pointer_or_inconsistent_row_is_refused(client, monkeypatch):
    class FakePath:
        def __init__(self, text):
            self.text, self.name = text, "ps_coverage.json"

        def is_file(self):
            return True

        def read_text(self, encoding="utf-8"):
            return self.text

    bad = json.loads(json.dumps(RAW))
    bad["rows"][1]["facts"][0]["pointer"] = "/overall/continuous/M9/rmse_mm"
    planned_with_fact = json.loads(json.dumps(RAW))
    # no row is PLANNED any more, so a PLANNED row that carries a fact is built by demoting a row that has one
    planned_index = next((i for i, r in enumerate(planned_with_fact["rows"]) if r["status"] == "PLANNED"), 1)
    planned_with_fact["rows"][planned_index]["status"] = "PLANNED"
    planned_with_fact["rows"][planned_index]["facts"] = [dict(RAW["rows"][1]["facts"][0])]
    real = evidence.sha256_file
    for payload in (bad, planned_with_fact):
        monkeypatch.setattr(evidence, "COVERAGE_FILE", FakePath(json.dumps(payload)))
        monkeypatch.setattr(evidence, "sha256_file", lambda path: "0" * 64 if isinstance(path, FakePath) else real(path))
        evidence._coverage.cache_clear()
        response = client.get("/api/science/evidence/ps-coverage")
        assert response.status_code == 503 and response.json()["code"] == "SCIENCE_INTEGRITY_FAILURE"


def test_coverage_refuses_when_underlying_evidence_is_tampered(client, monkeypatch):
    real = evidence.sha256_file
    monkeypatch.setattr(evidence, "sha256_file", lambda path: "0" * 64 if path.name == "regime_verification_B_2025.json" else real(path))
    assert client.get("/api/science/evidence/ps-coverage").status_code == 503


def _load_doc_script():
    import importlib.util

    spec = importlib.util.spec_from_file_location("build_ps_traceability_doc", ROOT / "scripts/build_ps_traceability_doc.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_traceability_doc_is_generated_from_the_manifest_and_in_sync():
    module = _load_doc_script()
    text = (ROOT / "docs/22_REQUIREMENTS_TRACEABILITY.md").read_text(encoding="utf-8").replace("\r\n", "\n")
    block = text[text.index(module.START): text.index(module.END) + len(module.END)]
    assert block.strip() == module.render(RAW["rows"]).strip(), "docs/22 is out of sync: run python scripts/build_ps_traceability_doc.py"


def test_official_requirement_statuses_follow_the_mandatory_rows_only():
    module = _load_doc_script()
    table = {pid: status for pid, _, status, _ in module.ps_table(RAW["rows"])}
    assert set(table) == {f"PS-R{n:02d}" for n in range(1, 15)}
    assert all(table[p] == "IMPLEMENTED" for p in table)                                 # PS-R03 through the sealed-year regime verdicts, PS-R05 through the confirmatory test (docs/142)
    assert module.aggregate(["IMPLEMENTED", "PLANNED"]) == "PARTIAL" and module.aggregate(["PLANNED", "PLANNED"]) == "PLANNED"
