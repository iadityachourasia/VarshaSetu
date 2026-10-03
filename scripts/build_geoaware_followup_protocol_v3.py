"""Freeze geography-aware follow-up protocol v3 (docs/132): v2 plus ONE change (C2, candidate selection aligned with the primary question) and the
design of the single, pre-registered 2022 test of BOTH frozen candidate sets. Write-once.

Built from the frozen v2 record, so everything not named in ``changes`` is carried over. C2 was decided AFTER the v2 table was seen, and the record says so.
The sealed 2022 is not opened here.
"""

from __future__ import annotations

import copy
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.app.ml import geoaware_followup as gf  # noqa: E402

PHASE11 = ROOT / "backend/app/evidence_data/phase11"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    target = PHASE11 / "geoaware_followup_protocol_v3.json"
    if target.exists():
        raise SystemExit("protocol v3 already frozen; a change needs a new version")
    v2_path = PHASE11 / "geoaware_followup_protocol_v2.json"
    v2 = json.loads(v2_path.read_text(encoding="utf-8"))
    p = copy.deepcopy(v2)
    p["schema_id"] = "geoaware_followup_protocol_v3"
    p["title"] = "Geography-aware correction, follow-up with an independent test, protocol v3 (aligned selection, two pre-registered candidate sets, one test)"
    p["supersedes"] = {"protocol_v2_sha256": sha(v2_path), "v2_selection_freeze_sha256": sha(PHASE11 / "geoaware_followup_selection_freeze_v2.json"),
                       "protocol_v1_sha256": v2["supersedes"]["protocol_v1_sha256"],
                       "reason": ("v2's selection (lowest pooled RMSE) and the primary test (Ghats-coast heavy CSI) are different quantities; as selected, the v2 candidate "
                                  "does not clearly beat the v2 control on the primary quantity (docs/131)")}
    p["changes"] = list(v2["changes"]) + [{
        "id": "C2", "what": ("Candidate selection is aligned with the primary question: among configurations eligible under G1, G2 and G4 in every held-out year and within "
                             f"{gf.RMSE_TOLERANCE_MM} mm of the lowest eligible pooled out-of-fold RMSE, the one with the highest mean (over the three held-out years) Ghats-coast zone "
                             "heavy-rain CSI is selected; ties go to the lower pooled RMSE, then the earlier grid position. The same rule is applied to every arm, including the control"),
        "why": ("Selecting by RMSE and testing by heavy CSI lets the two pull apart; the rule keeps overall error bounded (the tolerance equals decision rule P2) while selecting "
                "on the quantity the test asks about, and gives the control the same advantage so the comparator is not weakened"),
        "what_does_not_change": ["the arms", "the grid and the event-weight cap of 4", "G1, G2, G4 and their values", "G3 reported, not gating (C1)", "leave-one-year-out cross-validation",
                                 "the development data", "the sealing rule for 2022 until the unseal record"]}]
    p["post_hoc_disclosure"] = {
        "decided_after": "the v2 selection table (docs/131), including which configurations the aligned rule would select, had been seen",
        "consequence": ("C2 is the second post-hoc change. The v3 selection is a deterministic re-application of an already known table, not an unbiased selection, and the "
                        "development comparison is development evidence only. Only the sealed 2022, which no choice has touched, can be called independent."),
        "no_threshold_was_tuned": f"the only new number is the RMSE tolerance of {gf.RMSE_TOLERANCE_MM} mm, taken unchanged from decision rule P2; no guardrail value moved",
        "earlier_outcomes_remain_on_record": "the v1 outcome (no candidate in any arm) and the v2 selection stay on record and are not rewritten"}
    p["approval"] = {
        "approved_before_any_v3_selection": True,
        "record": "project owner message 'do all of three perfectly' (2026-10-03), sent after docs/131 listed the options: run the one-shot 2022 test as frozen, draft a protocol v3 aligning the selection criterion, or stop and report",
        "interpretation": ("treated as authorising all three, in the only coherent order given that 2022 can be opened once: (a) freeze v3 including its selection, (b) open 2022 ONCE and score the "
                           "frozen v2 candidate set and the frozen v3 candidate set together under the multiplicity rule below, (c) report every result. It does not name each step, and the unseal "
                           "record (written before scoring, listing every hash) is the signed form of step (b)."),
        "not_approved": v2["approval"]["not_approved"],
        "unseal": "the unseal record geoaware_followup_unseal_record.json must exist, quote the owner message and list the hashes of this protocol, both selection freezes, the models and the scoring code before any 2022 value is read"}
    p["parents"]["protocol_v2_sha256"] = sha(v2_path)
    p["selection"]["rule_v3"] = p["changes"][-1]["what"]
    p["selection"]["rmse_tolerance_mm"] = gf.RMSE_TOLERANCE_MM
    p["selection"]["rule_v2_candidate_set"] = v2["selection"]["rule"] + " (frozen in selection_freeze_v2 and still scored as the secondary candidate set)"
    p["test"] = {
        "single_event": "2022 is opened once. Both frozen candidate sets are scored in that one event; nothing is selected, tuned or re-scored afterwards",
        "candidate_sets": {"primary": "protocol v3 selection (selection_freeze_v3): B1 versus B0", "secondary": "protocol v2 selection (selection_freeze_v2): B1 versus B0",
                           "identical_models": "a model selected by both protocols is one model; arms are identified by (arm, grid index, model hash)"},
        "multiplicity": {"family": "the two B1-versus-B0 comparisons on the same year", "method": "Bonferroni: each paired whole-case interval is two-sided at 97.5 percent (alpha 0.025), "
                                                                                                    "stated as such, never as 95 percent",
                         "claim": "'adds value' is claimed only for a candidate set that satisfies P1 to P4 with its 97.5 percent interval; the primary set is the v3 set"},
        "models_scored": ["Raw (M0, the c00 rainfall feature)", "every unique selected model of selection_freeze_v2 and selection_freeze_v3"],
        "not_scored": "the frozen M1 to M4 of the 2023 to 2025 corpus (decision 5 stays NO)"}
    p["decision_rule"]["adds_value_requires_all"] = [
        "P1: B1 beats the comparator on heavy-rain CSI in the coastal-and-orographic zone on 2022, paired whole-case 97.5 percent interval of (B1 minus comparator) excluding zero in the positive direction (Bonferroni for two candidate sets)",
        "P2: overall RMSE of B1 not worse than the comparator's by more than 0.2 mm",
        "P3: B1 passes the gating guardrails G1, G2 and G4 on 2022; G3 is reported and, if B1 forecasts almost no very-heavy rain, that is stated in the result",
        "P4: the comparator is the control B0 selected under the same protocol's rule; if that arm had no candidate the frozen M2 is the comparator and attribution is undetermined"]
    p["decision_rule"]["if_not_met"] = "no independent evidence that geography-aware features improve on the pipeline without them, reported with the same prominence as a success"
    p["evaluation"] = copy.deepcopy(v2["evaluation"])
    p["evaluation"]["uncertainty"] = {"method": "paired whole-case bootstrap", "repeats": 2000, "seed": 26080, "level_for_decision": 0.975,
                                      "note": "optimistic: cells within a case and consecutive days are correlated"}
    p["evaluation"]["label_for_2022"] = "INDEPENDENT TEST: first use of this year"
    p["immutability"] = "selection and test outputs are write-once; any change to this protocol needs a new version and a new record"
    target.write_text(json.dumps(p, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    (PHASE11 / "geoaware_followup_protocol_v3.sha256").write_text(sha(target) + "  geoaware_followup_protocol_v3.json\n", encoding="ascii")
    print("protocol v3 sha256", sha(target))


if __name__ == "__main__":
    main()
