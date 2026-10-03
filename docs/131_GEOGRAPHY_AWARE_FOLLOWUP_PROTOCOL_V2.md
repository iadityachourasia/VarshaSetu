# Phase 10C: geography-aware follow-up, protocol v2 and its development selection

Date: 2026-10-03. **Outcome: every arm now has a candidate, produced by one post-hoc protocol change. The sealed 2022 is still unopened, so there is no independent test.** Protocol v2: `backend/app/evidence_data/phase11/geoaware_followup_protocol_v2.json` (sha256 `f7af77deb3db8278a83df7480f60f53a881d73b461cb9498cec33d23697697f1`). Selection freeze v2 sha256 `18f0d04a58338ab41df5a8c6b2827efaee2d223aac916f4967ab0bfcc5946cb9`. Predecessor and its unchanged outcome: `docs/129`, `docs/130`.

## What changed, and why it is labelled post hoc

The project owner asked to "correct and make it as accurate as possible" after `docs/130` listed three options. That was treated as approval of option 2 in the form described there, which is change **C1 only**: G3 (very-heavy forecast frequency bias at least 0.05) is computed and reported for every held-out year but no longer gates eligibility. The message does not name the change item by item, and the owner may withdraw it before 2022 is unsealed.

The reason is structural. As a gate, G3 is failed by construction by every configuration that does not give heavy cases extra weight (they almost never reach 115.6 mm), while the configurations that pass G3 over-forecast when 2024 is held out and fail G2. Eligibility keeps G1 (heavy CSI at least Raw), G2 (absolute bias at most 1.5 mm) and G4 (zone over-forecast floor).

**This was decided after the v1 table, including which configurations would become eligible, had been seen.** The v2 selection is therefore a mechanical re-application of an already known table, not an unbiased selection, and the development comparison below is development evidence only. No numeric threshold was changed. The v1 outcome (no candidate) stays on record untouched, and nothing else in the protocol changed (a test compares v1 and v2 field by field). Only the sealed 2022, which no choice has touched, can be called independent.

## Selection (development years 2021, 2023, 2024; leave-one-year-out)

The out-of-fold predictions of the v1 run were reused, verified by checkpoint hash (they do not depend on which guardrails gate). Eligible configurations per arm and the rule's choice (lowest pooled out-of-fold RMSE among eligible):

| Arm | Eligible of 16 | Selected | Pooled RMSE (mm) |
|---|---|---|---|
| B0 control | 3 | configuration 14 (Tweedie, capped weights, depth 6, 200 rounds) | 14.77 |
| B1 geography (candidate) | 4 | configuration 8 (Tweedie, no weights, depth 4, 200 rounds) | 14.56 |
| B0Z control without 500 hPa height | 3 | configuration 8 | 14.90 |
| B1Z geography without 500 hPa height | 2 | configuration 8 | 14.62 |

Each selected model was refit on all 562 development cases; hashes are in the freeze and the models are local.

## What the selected models do, stated plainly

Held-out values for B1 against B0 and Raw (all from `geoaware_followup_selection_freeze_v2.json` and the Raw check of `docs/128`):

| | 2021 | 2023 | 2024 |
|---|---|---|---|
| RMSE (mm): Raw / B0 / B1 | 15.43 / 14.71 / 14.37 | 15.09 / 13.66 / 13.74 | 17.13 / 15.97 / 15.58 |
| Ghats-coast heavy CSI: Raw / B0 / B1 | 0.034 / 0.155 / 0.125 | 0.070 / 0.257 / 0.177 | 0.059 / 0.282 / 0.301 |
| Ghats-coast heavy frequency bias: Raw / B0 / B1 | 0.109 / 0.397 / 0.374 | 0.111 / 0.402 / 0.301 | 0.128 / 0.646 / 0.660 |
| Very-heavy frequency bias (G3, reported): B0 / B1 | 0.009 / 0.000 | 0.005 / 0.000 | 0.110 / 0.013 |

Three things follow, and none of them is flattering:

1. **As selected, B1 does not clearly beat B0 on the quantity the one-shot test cares about.** At *matched* configurations geography wins on Ghats-coast heavy CSI in all three years in 16 of 16 configurations (`docs/130`). But the rule picks each arm's own configuration by RMSE, so the control gets a capped-weight configuration and the candidate an unweighted one. As selected, the control has the higher zone heavy CSI in 2021 and 2023, and the candidate only in 2024. B1 has the lower pooled RMSE (14.56 against 14.77). The primary test P1 (zone heavy CSI, B1 against B0) is therefore more likely to fail than pass on 2022.
2. **The Ghats-coast deficiency is reduced, not fixed.** Both models still forecast only about a third to two thirds as many heavy events there as were observed (frequency bias 0.30 to 0.66), against about 0.11 to 0.13 for Raw.
3. **The selected geography model forecasts essentially no very-heavy rain** (G3 value 0.000 in two of three years). G3 is reported, not hidden: it fails in every year for all four selected models. Eligibility under v2 does not mean this requirement is solved.

The selection criterion (pooled RMSE) and the primary test (zone heavy CSI) are different quantities, and they pull in opposite directions here. That mismatch is a design weakness found after seeing the results. Aligning them would be a further post-hoc change (for example selecting the candidate by zone heavy CSI subject to an RMSE tolerance); it is **not** made here, because it changes what is being optimised and needs the owner's decision.

## Corrections to earlier statements

- `docs/129` said G4 addresses the 2024 over-forecast; it does not (G2 does). Corrected before freezing.
- `docs/130` and my summary of it said geography wins "in 16 of 16 configurations". That is true only at matched configurations; the as-selected comparison above is more mixed.
- The `geoaware_followup_selection_freeze.json` (v1) records a hash of `backend/app/ml/geoaware_followup.py` from before this phase added a `gating` parameter (additive; default behaviour identical, tested). The v1 hash therefore no longer matches the file, and the v2 freeze records the current hash.
- The estimate in `docs/129` of up to two hours of compute was wrong: the full grid ran in minutes.

## What is and is not claimed

- **Claimed:** under protocol v2 each arm has a candidate chosen by the stated rule; the sealed 2022 is unopened; on development years the selected geography model has lower overall error than the selected control and both improve on Raw.
- **Not claimed:** that geography improves heavy-rain detection on an independent year; that very-heavy rain is addressed; that the coastal and orographic requirement changes status (it stays PARTIAL).

## Decisions for the project owner

1. **Proceed to the one-shot test on 2022 as frozen** (a separate signed unseal record is required), accepting that P1 is more likely to fail than pass on this evidence. A fail would be reported with the same prominence as a pass.
2. **Or draft protocol v3** that aligns the selection criterion with the primary question (a further post-hoc change, disclosed and frozen before 2022 is opened).
3. **Or stop here** and report the development evidence with these limits.
4. Decision 5 (scoring frozen M1 to M4 on 2022, default no) and D2 (IMD rights) remain open.

## Reproduction

`scripts/build_geoaware_followup_protocol_v2.py` (write-once), `scripts/select_geoaware_followup_v2.py` (write-once freeze). Pure rule with the `gating` parameter: `backend/app/ml/geoaware_followup.py`, tested in `backend/tests/test_geoaware_followup.py`. `backend/tests/test_geoaware_followup_v2_evidence.py` checks the hash chain, that v2 differs from v1 only where documented, re-derives every arm's selection from the stored per-year metrics, pins the as-selected comparison above, and confirms 2022 is unopened.

## Addendum (2026-10-03): superseded status

The statements above that 2022 is unopened were true when written. The owner then asked for all three options; protocol v3 was frozen and 2022 was opened once under a signed record (`docs/132`), with the result in `docs/133` (primary candidate passes, the v2 candidate described here does not).
