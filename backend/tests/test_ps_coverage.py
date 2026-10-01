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
          "/methodology", "/audit", "/compliance", "/zones"}
MUST_BE_PLANNED = ("REGIME-WESTERN-DISTURBANCE", "REGIME-INDEPENDENT-VALIDATION", "LIVE-INFERENCE",
                   "ALL-INDIA-DOMAIN")
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
    # coastal/orographic is PARTIAL (rule-based zones + stratified verification) and can never be IMPLEMENTED without a validated model (docs/115, docs/118)
    assert ROWS["REGIME-COASTAL-OROGRAPHIC"]["status"] == "PARTIAL" and ROWS["REGIME-COASTAL-OROGRAPHIC"]["ps_mandatory"]
    assert "specialist model" in ROWS["REGIME-COASTAL-OROGRAPHIC"]["limitation"] and ROWS["REGIME-COASTAL-OROGRAPHIC"]["pages"][0]["href"] == "/zones"
    # the classifier row cannot claim full coverage while mandatory regimes are missing
    assert ROWS["REGIME-CLASSIFIER"]["status"] == "PARTIAL"
    assert ROWS["IMPROVEMENT-VS-RAW"]["status"] == "PARTIAL"
    # synoptic overlays now exist (docs/121); the row stays an extra, never mandatory, and states its scope limits
    assert ROWS["SYNOPTIC-OVERLAYS"]["status"] == "IMPLEMENTED" and not ROWS["SYNOPTIC-OVERLAYS"]["ps_mandatory"] and "Operational-era track only" in ROWS["SYNOPTIC-OVERLAYS"]["limitation"]


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
            assert re.fullmatch(r"(regime:(A:(2018|2019)|B:(2024|2025))|district:B:(2024|2025)|zone:(A:(2018|2019)|B:(2024|2025))|zoneforcing:(A:(2018|2019)|B:(2024|2025)))", fact["source"]), fact
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
    planned_index = next(i for i, r in enumerate(planned_with_fact["rows"]) if r["status"] == "PLANNED")
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
    assert table["PS-R03"] == "PARTIAL" and table["PS-R05"] == "PARTIAL"                  # missing regimes / mixed extreme skill
    assert all(table[p] == "IMPLEMENTED" for p in table if p not in ("PS-R03", "PS-R05"))
    assert module.aggregate(["IMPLEMENTED", "PLANNED"]) == "PARTIAL" and module.aggregate(["PLANNED", "PLANNED"]) == "PLANNED"
