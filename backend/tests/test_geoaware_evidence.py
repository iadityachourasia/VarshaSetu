"""Geography-aware (M5a) evidence: hash chain, independent re-derivation of the frozen selection and of the pre-registered decision."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from backend.app.ml import geoaware as ga

PHASE7 = Path(__file__).resolve().parents[1] / "app/evidence_data/phase7"
PHASE9 = Path(__file__).resolve().parents[1] / "app/evidence_data/phase9"
MODELS = Path(__file__).resolve().parents[2] / "experiments/geoaware_m5_v1/models"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(name: str, folder: Path = PHASE9) -> dict:
    return json.loads((folder / name).read_text(encoding="utf-8"))


PROTOCOL, FREEZE, MANIFEST, DECISION = load("geoaware_protocol_v1.json"), load("geoaware_selection_freeze.json"), load("geoaware_manifest.json"), load("geoaware_decision.json")
EVAL = {2024: load("geoaware_evaluation_B_2024.json"), 2025: load("geoaware_evaluation_B_2025.json")}


def test_hash_chain_protocol_freeze_manifest_and_every_file():
    assert FREEZE["protocol_sha256"] == sha(PHASE9 / "geoaware_protocol_v1.json")
    assert (PHASE9 / "geoaware_selection_freeze.sha256").read_text().split()[0] == sha(PHASE9 / "geoaware_selection_freeze.json")
    assert MANIFEST["protocol_sha256"] == FREEZE["protocol_sha256"] and MANIFEST["selection_freeze_sha256"] == sha(PHASE9 / "geoaware_selection_freeze.json")
    assert (PHASE9 / "geoaware_manifest.sha256").read_text().strip() == sha(PHASE9 / "geoaware_manifest.json")
    for name, entry in MANIFEST["files"].items():
        assert sha(PHASE9 / name) == entry["sha256"], name
    for year, result in EVAL.items():
        assert result["protocol_sha256"] == FREEZE["protocol_sha256"] and result["selection_freeze_sha256"] == sha(PHASE9 / "geoaware_selection_freeze.json")
    for raw in (PHASE9 / n for n in ("geoaware_protocol_v1.json", "geoaware_selection_freeze.json", "geoaware_decision.json")):
        assert b"\r\n" not in raw.read_bytes()


def test_selection_is_reproducible_from_the_stored_configuration_table():
    """Re-apply the frozen rule to the 64 stored out-of-fold results; it must pick exactly what the freeze says."""
    table = FREEZE["all_configurations"]
    assert len(table) == 64 and {r["arm"] for r in table} == {"A0", "A1", "A2", "A3"}
    ref = FREEZE["training"]["raw_out_of_fold_reference"]
    for arm in ga.ARMS:
        rows = [r for r in table if r["arm"] == arm]
        assert [r["grid_index"] for r in rows] == list(range(16))
        for r in rows:                                     # the stored pass flag equals the guardrails recomputed from the stored values
            g1 = r["heavy_csi"] is not None and r["heavy_csi"] >= ref["heavy_csi"]
            g2 = abs(r["bias_mm"]) <= ga.G2_MAX_ABS_BIAS_MM
            g3 = r["very_heavy_frequency_bias"] is not None and r["very_heavy_frequency_bias"] >= ga.G3_MIN_VERY_HEAVY_FREQUENCY_BIAS
            assert r["passes_guardrails"] == (g1 and g2 and g3), (arm, r["grid_index"])
        passing = [r for r in rows if r["passes_guardrails"]]
        chosen = FREEZE["selection"][arm]["selected"]
        if not passing:
            assert chosen is None
        else:
            best = min(passing, key=lambda r: (r["rmse_mm"], r["grid_index"]))
            assert chosen["grid_index"] == best["grid_index"] and chosen["config"] == ga.configurations()[best["grid_index"]]
    assert {a for a, b in FREEZE["selection"].items() if b["selected"]} == {"A1", "A3"}
    assert FREEZE["selection"]["A0"]["selected"] is None and FREEZE["selection"]["A2"]["selected"] is None


def test_model_files_match_the_freeze_when_present():
    present = [arm for arm, b in FREEZE["selection"].items() if b["selected"] and (MODELS / f"{arm}.json").exists()]
    if not present:
        pytest.skip("the trained model files are local (gitignored); the freeze records their hashes")
    for arm in present:
        assert sha(MODELS / f"{arm}.json") == FREEZE["selection"][arm]["selected"]["model_sha256"]


def test_published_baselines_reproduce_exactly_and_equal_the_stage1_evidence():
    for year, result in EVAL.items():
        stage1 = load(f"zone_verification_B_{year}.json", PHASE7)
        assert result["reproduction"]["status"] == "REPRODUCED" and result["reproduction"]["m0_to_m4_equal_published_zone_evidence_max_abs_diff"] <= 1e-9
        for zone in stage1["pooled"]:
            for model in ("M0", "M1", "M2", "M3", "M4"):
                a, b = result["pooled"][zone][model], stage1["pooled"][zone][model]
                assert a["cell_count"] == b["cell_count"]
                if "rmse_mm" in b:
                    assert a["rmse_mm"] == pytest.approx(b["rmse_mm"], abs=1e-9) and a["bias_mm"] == pytest.approx(b["bias_mm"], abs=1e-9)


def test_labels_and_scope_are_stated():
    assert "POST_HOC" not in EVAL[2024]["evidence_role"] and "POST_HOC" in EVAL[2025]["evidence_role"]
    assert EVAL[2024]["models"] == ["M0", "M1", "M2", "M3", "M4", "A1", "A3"] and EVAL[2024]["fss"]["status"] == "not_reported"
    assert any("single training year" in limit for limit in EVAL[2025]["limits"]) and any("no independent test" in limit for limit in EVAL[2025]["limits"])
    assert PROTOCOL["approval"]["option_D1"].startswith("(b) development-only")


def test_decision_is_rederived_from_the_evaluation_files_and_is_not_met():
    zone = "COASTAL_AND_OROGRAPHIC"
    for year, result in EVAL.items():
        pair = DECISION["per_year"][str(year)]
        csi, rmse = result["comparisons"][zone]["A3-M2"]["heavy_csi"], result["comparisons"]["ALL"]["A3-M2"]["rmse"]
        assert pair["csi_beats_M2"] == (csi["point"] > 0 and csi["excludes_zero"]) and pair["rmse_within_tolerance"] == (rmse["point"] <= 0.2)
        assert pair["guardrails_pass"] == all(result["guardrails_on_evaluation_population"]["A3"].values())
    y24, y25 = (DECISION["per_year"][y] for y in ("2024", "2025"))
    sign = EVAL[2024]["comparisons"][zone]["A3-M2"]["heavy_csi"]["point"] * EVAL[2025]["comparisons"][zone]["A3-M2"]["heavy_csi"]["point"] > 0
    expected = bool(y24["csi_beats_M2"] and y24["rmse_within_tolerance"] and y24["guardrails_pass"] and sign)
    assert DECISION["adds_value"] is expected is False
    assert y24["csi_beats_M2"] and y25["csi_beats_M2"] and sign              # the heavy-rain gain in the target zone is real and replicated
    assert not y24["rmse_within_tolerance"] and not y24["guardrails_pass"]   # but 2024 fails the overall-error tolerance and the bias guardrail
    assert y25["rmse_within_tolerance"] and y25["guardrails_pass"]
    assert DECISION["geography_attribution"] is None and "no evidence" in DECISION["wording"]
    assert "did not anticipate" in (DECISION["protocol_gap"] or "")


def test_unsupported_strata_carry_no_number_and_bootstrap_is_declared():
    for result in EVAL.values():
        assert result["bootstrap"]["repeats"] == 2000 and result["bootstrap"]["seed"] == 26080
        for zone, by_model in result["pooled"].items():
            for model, block in by_model.items():
                if not result["support"][zone]["continuous_supported"]:
                    assert block.get("status") == "insufficient_support" and "rmse_mm" not in block
        for zone, by_pair in result["comparisons"].items():
            for pair, by_metric in by_pair.items():
                for metric, stat in by_metric.items():
                    assert stat["status"] in ("ok", "insufficient_support", "undefined", "unstable") and (stat["status"] != "ok" or stat["interval95"][0] <= stat["point"] <= stat["interval95"][1] + 1e-9)
