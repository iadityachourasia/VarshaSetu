# Phase 10B: geography-aware follow-up, development selection result

Date: 2026-10-03. **Outcome under the frozen rule: no candidate in any arm. The sealed 2022 was not opened, so no independent test exists.** Protocol: `backend/app/evidence_data/phase11/geoaware_followup_protocol_v1.json` (sha256 `2244e0c75abbafb216adaeca4c16be342ca3210ed58ca2b4a695b67863700e10`), design in `docs/129`. Selection freeze sha256 `40dfb3ed169315560189a7ae1f7a7e89a11565f6279d1f2730bf5c62fd46ab63`.

## What ran, and under whose approval

The project owner replied "continue do thing" to a message that listed decisions 1 to 6 of `docs/129` and said the work would stop before unsealing 2022. That was treated as approval of decisions 1 to 4 exactly as written (year roles, the four arms and the event-weight cap of 4, guardrails G1 to G4, decision rule P1 to P4). It is not an item-by-item approval and the owner may revise any of it before 2022 is unsealed. Decision 5 (scoring the frozen M1 to M4 on 2022) was not answered and defaults to **no**; IMD rights (D2) stay unresolved, so everything stayed local.

The protocol was frozen before any training. `scripts/train_geoaware_followup.py` then fit 4 arms by 16 configurations by 3 leave-one-year-out folds (192 fits, a few minutes in total, far faster than the estimate of up to two hours in `docs/129`), over the three development years 2021, 2023 and 2024 (562 cases). No 2022 feature, target or observation was read by the selection (the sealed-year check is tested in `backend/tests/test_geoaware_followup_evidence.py`).

## Result

For every arm, no configuration passed G1 to G4 in every held-out year, so no arm has a candidate, no final model was fitted, and under the frozen rule the test on the sealed 2022 **cannot be run**: there is no declared B1 to score.

Across all 64 configurations, the guardrail failures by held-out year were:

| Guardrail | 2021 | 2023 | 2024 |
|---|---|---|---|
| G1 heavy CSI at least Raw | 1 | 0 | 0 |
| G2 absolute bias at most 1.5 mm | 11 | 18 | 42 |
| G3 very-heavy frequency bias at least 0.05 | 37 | 54 | 11 |
| G4 zone heavy frequency bias at most 1.5 | 0 | 0 | 0 |

The failures are structural, not near-misses. Configurations that give heavy cases more weight forecast very-heavy rain and pass G3, but over-forecast when 2024 is held out (a bias of about +4.4 mm for the closest, B1 configuration 6) and fail G2. Configurations that do not over-forecast almost never reach 115.6 mm and fail G3 in 2021 and 2023. No configuration of any arm satisfies both. G1 and G4 are almost never the problem; G4 never failed (and, as corrected in `docs/129`, is a loose floor that would not have flagged the first experiment's 2024 zone value either).

## What the development data say about geography itself

This is descriptive, on held-out development years, and is **not a test result** (the design was informed by the 2024 and 2025 results of `docs/126`; only 2021 is new to modelling, and the feature question was already chosen). Across all 16 configurations, the geography arm B1 beats the identical control B0 on heavy-rain CSI in the Ghats-coast zone in **all three held-out years in 16 of 16 configurations**, and has lower pooled RMSE in **16 of 16**. In the zone, B1's heavy-rain frequency bias is higher than the control's in the configurations that do not over-forecast (for example about 0.37 against 0.13 for 2021 with the unweighted Tweedie configuration 8), though still well below 1. The per-configuration, per-year numbers are in `geoaware_followup_development_summary.json` with the checkpoint's hash.

So the evidence is consistent: geography features help in every development comparison, and the pre-registered guardrail set (G2 and G3 together) is what leaves no configuration eligible. That is an observation about the guardrails as designed, found after seeing the results. It does not turn the outcome into a pass.

## What is and is not claimed

- **Claimed:** under the frozen protocol the selection produced no candidate for any arm; 2022 was not opened; the development comparison above is real but descriptive.
- **Not claimed:** that geography-aware features improve on the control on an independent year, that any model is selected, or that the coastal and orographic requirement changes status (it stays PARTIAL).
- **Not changed:** the guardrails, the grid and the recipe stay exactly as frozen. Choosing different ones after seeing this table would be a new protocol, not a rescue of this one.

## Options for the project owner

1. **Accept the negative outcome and stop.** Report it with the same prominence as a success. 2022 stays sealed and available for any future, properly pre-registered question.
2. **Draft protocol v2 with revised guardrails, then test once on 2022.** The most defensible change is to keep G1, G2 and G4 as eligibility conditions and report G3 as a diagnostic instead of gating on it, because a gate that every unweighted model fails by construction selects for over-forecasting, which G2 then punishes. This would be a decision made **after** seeing the development outcome, so it must be stated as such, frozen before 2022 is opened, and it would still leave 2022 as an unbiased judge because nothing in this run touched it. It needs the owner's approval; I will not propose a threshold tuned to make a candidate appear.
3. **Wait for another independent season** (2026) and pre-register there.

Whichever is chosen, the unseal of 2022 still needs a separate signed owner record, and decision 5 (scoring frozen M1 to M4 on 2022) and D2 (IMD rights) remain open.

## Reproduction

`scripts/build_geoaware_followup_protocol.py` (write-once), `scripts/train_geoaware_followup.py` (write-once freeze, resumable), `scripts/summarize_geoaware_followup.py` (derived summary). Pure rules: `backend/app/ml/geoaware_followup.py`, tested in `backend/tests/test_geoaware_followup.py`; evidence chain and the outcome re-derived from the stored per-year metrics in `backend/tests/test_geoaware_followup_evidence.py`. The cross-validation checkpoint and the unselected (nonexistent) models are local and gitignored.

## Addendum (2026-10-03): follow-up and a precision

Protocol v2 (`docs/131`) later made one post-hoc change (G3 reported, not gating), after which every arm has a candidate; the v1 outcome above is unchanged and stays on record. One precision: the statement that geography wins in "16 of 16 configurations" is a **matched-configuration** comparison. The selection rule picks each arm's own configuration by pooled RMSE, and as selected the control has the higher Ghats-coast heavy CSI in 2021 and 2023 (`docs/131`).

Protocol v3 and the single test on 2022 followed (`docs/132`, `docs/133`); the options listed above were all carried out in the only coherent order. The statements above that 2022 "stays sealed" describe the state when this document was written.
