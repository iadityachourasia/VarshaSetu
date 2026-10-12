"""The research score must reproduce the sealed forecast-side candidate."""

from scripts import fit_lead_aware_probability as fit
from scripts import score_lead_aware_probability as score


def test_fit_and_score_protocol_identity():
    rule, protocol_sha = fit.checked(fit.PROTOCOL)
    seal, _ = fit.checked(fit.OUT)
    manifest = fit.verified_cache(protocol_sha)
    assert rule["excluded_years"] == [2025, 2026]
    assert seal["selection_labels_decoded"] is False
    assert seal["fit_manifest_sha256"] == fit.sha256(fit.CACHE / "manifest.json")
    assert manifest["calibration_case_count"] == 108
    assert manifest["selection_case_count"] == 68
    assert manifest["calibration_support"]["very_heavy"]["positive_cells"] >= 100


def test_score_recomputes_sealed_selection_comparison():
    stored, _ = fit.checked(score.OUT)
    rebuilt = score.score()
    assert rebuilt == stored
    assert rebuilt["scores"]["selection"]["paired_cells"] == 88468
    assert rebuilt["role"] == "consumed_2024_development_diagnostic_no_independent_reliability_claim"
