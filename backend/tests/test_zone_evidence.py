"""Stage 1 zone-verification evidence (docs/117): hashes, reproduction, partition and support-gate honesty, decision-rule consistency."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

PHASE7 = Path(__file__).resolve().parents[2] / "backend/app/evidence_data/phase7"
MANIFEST = json.loads((PHASE7 / "zone_verification_manifest.json").read_text(encoding="utf-8"))
YEARS = {("A", 2018): "DEVELOPMENT", ("A", 2019): "POST_HOC", ("B", 2024): "DEVELOPMENT", ("B", 2025): "POST_HOC"}
PROTOCOL_V3 = "a9ff78173ddb6026e6b297c2da2128dde2fdcf825ae8b0c368c5f5fa79d199fd"
ZONES = ("COASTAL", "OROGRAPHIC", "COASTAL_AND_OROGRAPHIC", "OTHER")


def load(track, year):
    return json.loads((PHASE7 / f"zone_verification_{track}_{year}.json").read_text(encoding="utf-8"))


def test_manifest_hash_sidecar_and_every_file_hash():
    raw = (PHASE7 / "zone_verification_manifest.json").read_bytes()
    assert hashlib.sha256(raw).hexdigest() == (PHASE7 / "zone_verification_manifest.sha256").read_text().strip()
    assert b"\r\n" not in raw
    for name, entry in MANIFEST["files"].items():
        assert hashlib.sha256((PHASE7 / name).read_bytes()).hexdigest() == entry["sha256"], name
    assert MANIFEST["protocol_sha256"] == PROTOCOL_V3
    assert MANIFEST["static_geography_sha256"] == hashlib.sha256((PHASE7 / "static_geography_v1.json").read_bytes()).hexdigest()


@pytest.mark.parametrize("track,year", list(YEARS))
def test_each_year_reproduces_published_evidence_and_zones_partition(track, year):
    data = load(track, year)
    assert data["reproduction"]["status"] == "REPRODUCED" and data["reproduction"]["counts_exact"]
    assert data["reproduction"]["max_abs_diff"] <= 1e-6 and data["reproduction"]["zones_partition_all_cells"]
    assert data["protocol_sha256"] == PROTOCOL_V3
    cells = {z: data["zones"][z]["cells"] for z in data["zones"]}
    assert sum(cells[z] for z in ZONES) == cells["ALL"] == 1301
    assert data["models"] == (["M0", "M2", "M3", "M4"] if track == "A" else ["M0", "M1", "M2", "M3", "M4"])
    for model in data["models"]:
        assert sum(data["pooled"][z][model]["cell_count"] for z in ZONES) == data["pooled"]["ALL"][model]["cell_count"]
        for key in ("hits", "misses", "false_alarms"):
            assert sum(data["pooled"][z][model]["categorical"]["heavy"][key] for z in ZONES) == data["pooled"]["ALL"][model]["categorical"]["heavy"][key]
    assert data["fss"]["status"] == "not_reported"


def test_evidence_roles_label_the_consumed_years_as_post_hoc():
    for (track, year), kind in YEARS.items():
        role = load(track, year)["evidence_role"]
        assert ("POST_HOC" in role) == (kind == "POST_HOC"), role


def test_unsupported_strata_carry_no_number():
    for (track, year) in YEARS:
        data = load(track, year)
        for zone, gate in data["support"].items():
            for threshold in ("heavy", "very_heavy"):
                if gate[threshold]["supported"]:
                    continue
                for model in data["models"]:
                    block = data["pooled"][zone][model]["categorical"][threshold]
                    assert block.get("status") == "insufficient_support" and "CSI" not in block
                for by_model in data["differences"]["q1"].get(zone, {}).values():
                    metric = by_model.get("heavy_csi" if threshold == "heavy" else "very_heavy_csi")
                    assert metric is None or metric.get("status") == "insufficient_support"
        for regime in data["by_pseudo_regime"].values():
            for zone in regime["zones"].values():
                for block in zone["models"].values():
                    heavy = block.get("categorical", {}).get("heavy")
                    assert "very_heavy" not in block.get("categorical", {})
                    if heavy and heavy.get("status") == "insufficient_support":
                        assert "CSI" not in heavy


def test_bootstrap_is_the_declared_paired_whole_case_procedure():
    data = load("B", 2025)
    assert data["bootstrap"]["repeats"] == 2000 and data["bootstrap"]["seed"] == 26080
    entry = data["differences"]["q1"]["COASTAL"]["M0"]["rmse"]
    assert entry["status"] == "ok" and entry["interval95"][0] <= entry["point"] <= entry["interval95"][1] + 1e-9
    assert entry["excludes_zero"] == (entry["interval95"][0] > 0 or entry["interval95"][1] < 0)
    assert "M0" not in data["differences"]["q2"]["COASTAL"]      # improvement over Raw is not defined for Raw


def test_decision_summary_is_internally_consistent_and_keeps_the_rule_wording():
    summary = json.loads((PHASE7 / "zone_decision_summary.json").read_text(encoding="utf-8"))
    assert "excludes zero in the development year" in summary["rule"]
    assert summary["stage_3_recommended"] == any(t["geographic_gaps"] > 0 for t in summary["tracks"].values())
    for track, block in summary["tracks"].items():
        assert block["development_significant"] == len(block["rows"]) and block["geographic_gaps"] == sum(r["geographic_gap"] for r in block["rows"])
        assert block["geographic_gaps"] <= block["development_significant"] <= block["tests"]
        for row in block["rows"]:
            lo, hi = row["development_interval95"]
            assert (lo > 0 or hi < 0)
            assert row["same_sign"] == (row["development_point"] * row["final_point"] > 0)
            assert row["geographic_gap"] == row["same_sign"]
            assert row["zone"] in ZONES and row["metric"] in ("rmse", "bias", "heavy_csi")
        dev, final = load(track, block["development_year"]), load(track, block["final_test_year"])
        assert "POST_HOC" not in dev["evidence_role"] and "POST_HOC" in final["evidence_role"]
