"""Freeze geography-aware follow-up protocol v2 (docs/131): v1 with ONE change, G3 reported but no longer gating. Write-once.

Built from the frozen v1 record so everything not named in ``changes`` is carried over unchanged. The change was decided AFTER the v1 development
selection (which found no candidate, docs/130), and the record says so. The sealed 2022 is not opened here.
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
    target = PHASE11 / "geoaware_followup_protocol_v2.json"
    if target.exists():
        raise SystemExit("protocol v2 already frozen; a change needs a new version")
    v1_path = PHASE11 / "geoaware_followup_protocol_v1.json"
    v1 = json.loads(v1_path.read_text(encoding="utf-8"))
    summary = json.loads((PHASE11 / "geoaware_followup_development_summary.json").read_text(encoding="utf-8"))
    p = copy.deepcopy(v1)
    p["schema_id"] = "geoaware_followup_protocol_v2"
    p["title"] = "Geography-aware correction, follow-up with an independent test, protocol v2 (G3 reported, not gating)"
    p["status"] = "APPROVED_FOR_DEVELOPMENT_SELECTION_ONLY_TEST_SEALED"
    p["supersedes"] = {"protocol_v1_sha256": sha(v1_path), "v1_selection_freeze_sha256": sha(PHASE11 / "geoaware_followup_selection_freeze.json"),
                       "v1_development_summary_sha256": sha(PHASE11 / "geoaware_followup_development_summary.json"),
                       "reason": "v1 found no candidate in any arm because G2 and G3 cannot both be satisfied by any of the 64 configurations (docs/130)"}
    p["changes"] = [{
        "id": "C1", "what": "G3 (very-heavy forecast frequency bias at least 0.05) is computed and reported for every held-out year and for 2022, but is no longer an eligibility gate",
        "why": ("As a gate, G3 is failed by construction by every configuration that does not give heavy cases extra weight (they almost never reach 115.6 mm), while the "
                "configurations that do pass G3 over-forecast in held-out 2024 and fail G2. A gate that selects for over-forecasting and is then punished by G2 does not "
                "discriminate between good and bad models. Eligibility keeps G1 (heavy CSI at least Raw), G2 (absolute bias) and G4 (zone over-forecast floor)."),
        "what_does_not_change": ["the arms", "the grid and the event-weight cap of 4", "G1, G2 and G4 and their values", "leave-one-year-out cross-validation", "the decision rule P1 to P4",
                                 "the support gate", "the sealing of 2022", "the seeds and libraries"],
        "g3_still_reported": "G3 per held-out year for every configuration and for the selected model, and on 2022 at unseal; a selected model that forecasts almost no very-heavy rain is labelled as such"}]
    p["post_hoc_disclosure"] = {
        "decided_after": "the v1 development selection and its table (docs/130) had been seen, including which configurations would become eligible once G3 stops gating",
        "consequence": ("The v2 selection is therefore a deterministic re-application of an already known table, not an unbiased selection, and the development comparison is "
                        "development evidence only. Only the sealed 2022, which no choice has touched, can be called independent."),
        "no_threshold_was_tuned": "no numeric threshold was changed; one guardrail was demoted from a gate to a reported diagnostic, for the structural reason in C1",
        "v1_remains_the_pre_registered_outcome": "the v1 outcome (no candidate) stays on record and is not rewritten"}
    p["approval"] = {
        "approved_before_any_v2_selection": True,
        "record": "project owner message 'try to correct and make it as accurate as possible' (2026-10-03), sent after docs/130 listed options 1 to 3, with option 2 (protocol v2 with revised guardrails, G3 as a reported diagnostic) as the stated way to proceed",
        "interpretation": ("treated as approval of option 2 in the form described in docs/130, which is change C1 only. It does not name the change item by item, and the owner may revise or withdraw it "
                           "before 2022 is unsealed. Decisions 1 to 4 of docs/129 carry over from v1 as already recorded."),
        "not_approved": v1["approval"]["not_approved"],
        "unseal": "opening the 2022 IMD values requires a separate signed unseal record from the owner after the v2 selection freeze exists; this protocol authorises development selection only"}
    p["parents"]["protocol_v1_sha256"] = sha(v1_path)
    p["selection"]["guardrails"]["G3"] = "very-heavy (115.6 mm per 24 h) forecast frequency bias at least 0.05: REPORTED for every held-out year and on 2022, NOT an eligibility gate (change C1)"
    p["selection"]["gating_guardrails"] = list(gf.GUARDRAILS_V2)
    p["selection"]["rule"] = ("per arm, among the configurations that pass G1, G2 and G4 in EVERY held-out year, the lowest pooled out-of-fold RMSE (all three held-out years together); "
                              "ties in grid order; none passing means the arm has no candidate and that is reported; G3 is reported alongside")
    p["selection"]["cross_validation_reuse"] = {"reused_from": "geoaware_followup_development_summary.json", "checkpoint_sha256": summary["checkpoint_sha256"],
                                                "why_valid": "the out-of-fold predictions do not depend on which guardrails gate; only the selection and the final fit are new"}
    p["decision_rule"]["adds_value_requires_all"] = [
        "P1: B1 beats the comparator on heavy-rain CSI in the coastal-and-orographic zone on 2022, paired whole-case 95 percent interval of (B1 minus comparator) excluding zero in the positive direction",
        "P2: overall RMSE of B1 not worse than the comparator's by more than 0.2 mm",
        "P3: B1 passes the gating guardrails G1, G2 and G4 on 2022; G3 is reported and, if B1 forecasts almost no very-heavy rain, that is stated in the result",
        "P4: the comparator rule above is applied and stated"]
    p["immutability"] = "selection outputs are write-once; any change to this protocol needs a new version and a new record"
    target.write_text(json.dumps(p, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    (PHASE11 / "geoaware_followup_protocol_v2.sha256").write_text(sha(target) + "  geoaware_followup_protocol_v2.json\n", encoding="ascii")
    print("protocol v2 sha256", sha(target))


if __name__ == "__main__":
    main()
