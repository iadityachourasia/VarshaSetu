"""Guards for the append-only v3/v4 metadata correction audit."""

from scripts import audit_nationwide_probability_v4_lineage as lineage


def test_scientific_contract_comparison_allows_only_version_name_in_gate() -> None:
    v3 = {key: {"fixed": key} for key in lineage.SCIENCE_KEYS}
    v3["diagnostic_gate"] = "v3 very-heavy Brier beats v1/v2"
    v4 = {**v3, "diagnostic_gate": "v4 very-heavy Brier beats v1/v2"}
    assert lineage.scientific_contract_equal(v3, v4)
    v4["model_spec"] = {"n_estimators": 160}
    assert not lineage.scientific_contract_equal(v3, v4)


def test_scientific_contract_rejects_gate_change_other_than_version() -> None:
    v3 = {key: key for key in lineage.SCIENCE_KEYS}
    v3["diagnostic_gate"] = "v3 threshold 0.14"
    v4 = {**v3, "diagnostic_gate": "v4 threshold 0.10"}
    assert not lineage.scientific_contract_equal(v3, v4)
