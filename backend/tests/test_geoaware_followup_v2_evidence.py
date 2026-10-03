"""Geography-aware follow-up protocol v2 (docs/131): hash chain, one documented change, mechanical re-derivation of the selection, honest G3 reporting, sealed 2022."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from backend.app.ml import geoaware_followup as gf

PHASE11 = Path(__file__).resolve().parents[1] / "app/evidence_data/phase11"
MODELS = Path(__file__).resolve().parents[2] / "experiments/geoaware_followup_v2/models"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(name: str) -> dict:
    return json.loads((PHASE11 / name).read_text(encoding="utf-8"))


V1, V2 = load("geoaware_followup_protocol_v1.json"), load("geoaware_followup_protocol_v2.json")
FREEZE1, FREEZE2, SUMMARY = load("geoaware_followup_selection_freeze.json"), load("geoaware_followup_selection_freeze_v2.json"), load("geoaware_followup_development_summary.json")


def test_hash_chain_v2():
    for stem in ("geoaware_followup_protocol_v2", "geoaware_followup_selection_freeze_v2"):
        assert (PHASE11 / f"{stem}.sha256").read_text(encoding="ascii").split()[0] == sha(PHASE11 / f"{stem}.json"), stem
        assert b"\r\n" not in (PHASE11 / f"{stem}.json").read_bytes()
    assert V2["supersedes"]["protocol_v1_sha256"] == V2["parents"]["protocol_v1_sha256"] == sha(PHASE11 / "geoaware_followup_protocol_v1.json")
    assert V2["supersedes"]["v1_selection_freeze_sha256"] == sha(PHASE11 / "geoaware_followup_selection_freeze.json")
    assert FREEZE2["protocol_sha256"] == sha(PHASE11 / "geoaware_followup_protocol_v2.json") and FREEZE2["supersedes_protocol_sha256"] == sha(PHASE11 / "geoaware_followup_protocol_v1.json")
    assert V2["selection"]["cross_validation_reuse"]["checkpoint_sha256"] == SUMMARY["checkpoint_sha256"] == FREEZE2["cross_validation_checkpoint_sha256"]
    assert FREEZE2["development"]["input_sha256"] == V1["development_data_sha256"]


def test_v2_differs_from_v1_only_where_documented_and_the_v1_outcome_is_untouched():
    changed = {k for k in set(V1) | set(V2) if V1.get(k) != V2.get(k)}
    assert changed <= {"schema_id", "title", "supersedes", "changes", "post_hoc_disclosure", "approval", "parents", "selection", "decision_rule", "immutability"}
    for untouched in ("model", "feature_registry", "evaluation", "years", "development_data_sha256", "track", "contamination_disclosure"):
        assert V1[untouched] == V2[untouched], untouched
    assert {k for k in set(V1["selection"]) | set(V2["selection"]) if V1["selection"].get(k) != V2["selection"].get(k)} == {"guardrails", "gating_guardrails", "rule", "cross_validation_reuse"}
    assert {g: v for g, v in V1["selection"]["guardrails"].items() if g != "G3"} == {g: v for g, v in V2["selection"]["guardrails"].items() if g != "G3"}
    assert [c["id"] for c in V2["changes"]] == ["C1"] and V2["selection"]["gating_guardrails"] == ["G1", "G2", "G4"] == list(gf.GUARDRAILS_V2)
    assert all(block["selected"] is None for block in FREEZE1["selection"].values())          # the v1 pre-registered outcome stays on record
    assert "had been seen" in V2["post_hoc_disclosure"]["decided_after"] and "not an unbiased selection" in V2["post_hoc_disclosure"]["consequence"]


def test_the_post_hoc_nature_of_the_change_is_disclosed_and_no_numeric_threshold_moved():
    d = V2["post_hoc_disclosure"]
    assert "v1 development selection and its table" in d["decided_after"] and "had been seen" in d["decided_after"] and "not an unbiased selection" in d["consequence"] and "no numeric threshold was changed" in d["no_threshold_was_tuned"]
    assert "does not name the change item by item" in V2["approval"]["interpretation"] and "separate signed unseal record" in V2["approval"]["unseal"]
    assert V2["approval"]["not_approved"] == V1["approval"]["not_approved"]
    assert V2["decision_rule"]["adds_value_requires_all"][0] == V1["decision_rule"]["adds_value_requires_all"][0] and V2["decision_rule"]["adds_value_requires_all"][1] == V1["decision_rule"]["adds_value_requires_all"][1]


def _results(arm: str) -> list[dict]:
    out: dict[int, dict] = {}
    for row in SUMMARY["rows"]:
        if row["arm"] != arm:
            continue
        entry = out.setdefault(row["grid_index"], {"grid_index": row["grid_index"], "pooled": {"rmse_mm": next(r["pooled_rmse_mm"] for r in FREEZE1["all_configurations"] if r["arm"] == arm and r["grid_index"] == row["grid_index"])}, "by_year": {}})
        entry["by_year"][row["held_out_year"]] = {"heavy": {"csi": row["heavy_csi"]}, "very_heavy": {"frequency_bias": row["very_heavy_frequency_bias"]}, "bias_mm": row["bias_mm"],
                                                  "zone": {"heavy_frequency_bias": row["zone_heavy_frequency_bias"]}}
    return list(out.values())


def test_the_v2_selection_is_rederived_mechanically_from_the_stored_per_year_metrics():
    raw = {int(y): v for y, v in FREEZE2["development"]["raw_heavy_csi_by_year"].items()}
    expected_eligible = {"B0": 3, "B1": 4, "B0Z": 3, "B1Z": 2}
    for arm in gf.ARMS:
        chosen = gf.select_configuration(_results(arm), raw, gating=gf.GUARDRAILS_V2)
        assert chosen is not None and FREEZE2["selection"][arm]["selected"]["grid_index"] == chosen["grid_index"], arm
        assert sum(r["eligible_v2"] for r in FREEZE2["all_configurations"] if r["arm"] == arm) == expected_eligible[arm]
        assert gf.select_configuration(_results(arm), raw) is None                      # under v1 gating the same data still give no candidate
    for r in FREEZE2["all_configurations"]:
        assert r["eligible_v2"] == all(r["guardrails_by_year"][y][g] for y in r["guardrails_by_year"] for g in gf.GUARDRAILS_V2)


def test_g3_is_reported_honestly_for_every_selected_model():
    for arm, block in FREEZE2["selection"].items():
        selected = block["selected"]
        assert set(selected["g3_reported_very_heavy_frequency_bias_by_year"]) == {"2021", "2023", "2024"}
        for year, value in selected["g3_reported_very_heavy_frequency_bias_by_year"].items():
            row = next(r for r in SUMMARY["rows"] if r["arm"] == arm and r["grid_index"] == selected["grid_index"] and r["held_out_year"] == int(year))
            assert value == row["very_heavy_frequency_bias"]
        assert selected["g3_passes_in_every_year"] == all(v >= gf.G3_MIN_VERY_HEAVY_FREQUENCY_BIAS for v in selected["g3_reported_very_heavy_frequency_bias_by_year"].values())
        assert selected["g3_passes_in_every_year"] is False            # every selected model forecasts almost no very-heavy rain: stated, not hidden
        assert all(selected["guardrails_by_year"][y][g] for y in selected["guardrails_by_year"] for g in gf.GUARDRAILS_V2)


def test_the_sealed_year_is_still_unopened():
    assert FREEZE2["sealed_test"]["opened"] is False and FREEZE2["sealed_test"]["year"] == 2022 and FREEZE2["development"]["years"] == [2021, 2023, 2024]


@pytest.mark.skipif(not MODELS.exists(), reason="the fitted models are local (gitignored); the freeze records their hashes")
def test_model_files_match_the_freeze_when_present():
    for arm, block in FREEZE2["selection"].items():
        assert sha(MODELS / f"{arm}.json") == block["selected"]["model_sha256"]


def test_as_selected_the_candidate_does_not_clearly_beat_the_control_on_zone_heavy_csi_and_this_is_pinned():
    """Matched-configuration comparisons favour geography in 16 of 16 (SUMMARY), but the rule selects each arm's own configuration by pooled RMSE.
    As selected, the control B0 (capped weights) has the higher zone heavy CSI in 2021 and 2023 and B1 only in 2024, while B1 has the lower pooled RMSE."""
    b0, b1 = FREEZE2["selection"]["B0"]["selected"], FREEZE2["selection"]["B1"]["selected"]
    assert (b0["grid_index"], b0["config"]["weights"]) == (14, "capped_event") and (b1["grid_index"], b1["config"]["weights"]) == (8, "none")
    zone = {y: (b1["by_year"][y]["zone"]["heavy_csi"] - b0["by_year"][y]["zone"]["heavy_csi"]) for y in ("2021", "2023", "2024")}
    assert zone["2021"] < 0 and zone["2023"] < 0 and zone["2024"] > 0
    assert b1["pooled_out_of_fold"]["rmse_mm"] < b0["pooled_out_of_fold"]["rmse_mm"]
    assert all(b0["by_year"][y]["heavy"]["csi"] > b1["by_year"][y]["heavy"]["csi"] for y in ("2021", "2023", "2024"))
    assert SUMMARY["b1_versus_b0_counts"]["zone_heavy_csi_higher_in_every_held_out_year"] == 16          # at matched configurations geography wins everywhere
