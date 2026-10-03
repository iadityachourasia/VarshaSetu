# Phase 10A: geography-aware correction, follow-up with an independent test (protocol PROPOSAL, not frozen)

Date: 2026-10-03. **Status: PROPOSED.** No model was fit, tuned or scored to write this. The only 2021 numbers used are the descriptive raw-forecast checks of `docs/128`, and 2022 observations have not been opened. Values marked *proposed* are decisions for the project owner. On approval they would be copied into a machine-readable, hash-frozen protocol (as for `docs/112`, `docs/115` and `docs/124`) before any training starts. Protocol first, then stop for approval, is the standing rule for every science-changing step.

## 1. What this is for

The first geography-aware experiment (`docs/124`, `docs/126`) found a large, replicated gain in heavy-rain detection on the Ghats coast, but 2024 over-forecast, so its pre-registered rule was **not met**, and the gain could not be attributed to geography because the control arm had no eligible configuration. Because 2024 and 2025 were then seen, no redesign could be judged on them. The independent-years corpus (`docs/128`) supplies a year that no choice has touched: **2022, sealed.**

This follow-up asks one question: *does a geography-aware gradient-boosted correction, trained on the three development years, beat the same pipeline without geography on heavy-rain detection in the Ghats-coast zone in the sealed 2022, without making overall error or bias worse?* The answer may be no, and that would be reported as such.

## 2. Contamination disclosure (stated before any run)

This design uses what `docs/126` showed: that the first recipe over-forecast in 2024, that static geography carried the gain and forecast-time forcing added nothing, and that the control arm failed its guardrails. Those results came from 2024 and 2025, so the design choices below (dropping the forcing arms, adding a zone over-forecast guardrail, lowering the event-weight cap) are informed by them. That is acceptable only because **2022 was never used for any choice**, and it is the only evidence that may be called independent. Results on 2021, 2023 and 2024 in this protocol are development evidence.

## 3. Proposed design

| Item | Proposal |
|---|---|
| Track | Operational-era (Track B) only; the tracks are never pooled |
| Development data | 2021 (179 cases, 232,879 rows), 2023 (200 cases, 260,200 rows) and 2024 (183 cases, 238,083 rows): 562 paired cases. The Ghats-coast zone holds 1,331, 1,554 and 2,627 observed heavy cell-days in the three years, so support is adequate |
| Sealed test | 2022: 173 forecast-eligible cases, no observation opened. Support is unknown until unseal, so the support gate of section 6 applies |
| Feature arms | **B0** control: the 22 existing forecast-time features. **B1**: B0 plus the 8 static geography features of `docs/116` (declared candidate). **B0Z** and **B1Z**: B0 and B1 without the two 500 hPa height features (`forecast_z500`, `z500_area_mean`), because `docs/128` shows a multi-year offset in that field (2022 is about 1.5 standard deviations below 2023 to 2024) and any model using it faces a distribution shift. Forecast-time forcing is **not** carried over (it added nothing in `docs/126`). Static geography is allowed at forecast time (`AGENTS.md` section 3.4) |
| Model | XGBoost, CPU, histogram method, seed 26080, 16 configurations per arm: depth {4, 6}, rounds {200, 350}, objective {squared error, Tweedie 1.5}, weights {none, capped event weight with cap **4**}. Everything else as `docs/126`. The cap changes from 10 to **4** because the capped weights are the likeliest cause of the 2024 over-forecast; it is the only recipe change, it is declared here, and it is one value |
| Training and selection | **Leave-one-year-out across 2021, 2023 and 2024**: for each held-out year the arm is fit on the other two and predicts the held-out year. This tests exactly the year-to-year transfer the sealed test needs. Selection uses the three held-out years together, with guardrails applied to **each** held-out year |
| Selection rule | Per arm, among the configurations passing G1 to G4 in every held-out year, the lowest pooled out-of-fold RMSE; ties in grid order; an arm with no passing configuration has **no candidate** and that is reported |
| Final model | The selected configuration refit on all 562 development cases, hash-recorded in a selection freeze before any 2022 value is opened |
| Baselines kept | Frozen M0 to M4 (trained on 2023 only, never refit) are reported as context. The primary comparator is **B0** under the same pipeline |
| Not proposed | Regime experts, deep learning, new dependencies, GPU, any open-ended search |

## 4. Guardrails (to be frozen, *proposed* values)

For every held-out year during selection and again on 2022:

- **G1** pooled heavy-rain CSI (64.5 mm per 24 h) at least the Raw value on the same cases.
- **G2** absolute pooled bias at most 1.5 mm.
- **G3** very-heavy (115.6 mm per 24 h) forecast frequency bias at least 0.05.
- **G4 (new)** heavy-rain forecast frequency bias in the Ghats-coast zone at most 1.5, a floor against gross zone over-forecasting. It is deliberately loose and would **not** have flagged the first candidate's 2024 zone value (about 1.28); what caught 2024 was G2 (overall bias about +5.2 mm against the 1.5 mm limit), which applies unchanged and now to every held-out year. No lower bound is imposed on G4 because the raw model sits at about 0.1.

*Correction recorded 2026-10-03, before freezing:* the first draft of this paragraph said G4 addresses the 2024 over-forecast. It does not; G2 does. The value 1.5 was not changed.

## 5. One-shot test on the sealed 2022 and the decision rule (*proposed*)

Procedure: freeze the selection, model hashes, code and this protocol's hash; the owner signs an unseal record; only then are the 2022 IMD values opened and paired (finite forecast cells intersected with IMD non-fill cells); everything is scored once, write-once, labelled "INDEPENDENT TEST: first use of this year", with no retuning afterwards.

The declared candidate **adds value** only if all hold on 2022:

1. **P1** B1 beats B0 on heavy-rain CSI in the coastal-and-orographic zone, paired whole-case 95 percent interval of (B1 minus B0) excluding zero in the positive direction. This is the geography-attribution test.
2. **P2** Overall RMSE of B1 is not worse than B0's by more than 0.2 mm.
3. **P3** B1 passes G1 to G4 on 2022.
4. **P4** If B0 has no candidate at selection, the comparator for P1 and P2 is the frozen M2 and the result is reported as *attribution undetermined* (this closes the gap that `docs/126` disclosed).

Reported but not part of the rule: B1Z against B1 (sensitivity to the 500 hPa height offset: if B1 passes and B1Z does not, the result is stated as sensitive to that shift), comparisons with frozen M0 to M4, by lead and by zone, very-heavy skill, and the ensemble context. One primary question, so no multiplicity adjustment is needed. The paired whole-case bootstrap (2,000 resamples, seed 26080) is optimistic because cells within a case and consecutive days are correlated, and is labelled so.

## 6. Support gate and stop rules

The frozen gate of `docs/124` applies unchanged: at least 30 cases, 20 cells and 30 observed event pairs per stratum, otherwise the stratum carries *insufficient support* and no number. If the Ghats-coast zone fails it on 2022, the primary test is not run and the result is reported as unevaluable, not as a pass or fail. Stop and report if the corpus shows a material discontinuity, if the reproduction gate fails (recomputed frozen M0 to M4 must reproduce their published values on the paired 2022 cells exactly where those apply), or if the seal cannot be shown intact.

## 7. What each outcome would mean

- **Rule met:** "a geography-aware correction improved Ghats-coast heavy-rain detection over the identical pipeline without geography on an independent year, within error and bias limits, for the operational-era track". The coverage row stays PARTIAL unless the owner decides otherwise, and no claim of validated regime awareness follows.
- **Rule not met:** "no independent evidence that geography-aware features improve on the pipeline without them", recorded with the same prominence as a success.
- **Unevaluable:** stated as such.

## 8. Risks stated up front

- The year-to-year offset in forecast 500 hPa height may degrade any model that uses it; B0Z and B1Z measure this but do not remove it.
- About half the scheduled cases are eligible, so the sample is smaller than the schedule.
- Three development years with two held out per fit is a small sample for year-transfer; the intervals will be wide.
- 2024 has been used before; its role here is development evidence only.
- The 0.25 degree zone is coarse; a null result is a statement about this resolution.
- Heavy-rain cell-days within a case are spatially correlated; bootstrap intervals stay optimistic.
- IMD redistribution rights (D2) are unresolved: all of this runs locally and nothing derived from IMD values may be uploaded.

## 9. Compute and reproducibility

Four arms by 16 configurations by 3 held-out years is 192 fits of about 500,000 rows and at most 32 features on CPU. At the rate of the first experiment this is an estimate of minutes to roughly two hours, not a measurement. Seeds, library versions, input hashes and the 2021 to 2023 to 2024 feature hashes are recorded in the selection freeze; outputs are write-once; a reproduction gate precedes every number.

## 10. Decisions requested

1. **Year roles:** confirm 2021 and 2023 and 2024 as development and 2022 as the sealed test.
2. **Arms and recipe:** approve B0, B1, B0Z, B1Z and the single recipe change (event-weight cap 4); forecast-time forcing dropped.
3. **Guardrails:** approve G1 to G4, in particular the new G4 value.
4. **Decision rule:** approve P1 to P4, including the fallback comparator when B0 has no candidate.
5. **Scoring of the frozen M1 to M4 on 2022** as descriptive context only (no decision rule): yes or no. This would be their first independent test.
6. **D2** IMD terms for the new years, before any output derived from IMD values leaves this machine.

Gate: `P10_FOLLOWUP_PROTOCOL_PROPOSED_AWAITING_APPROVAL`. Nothing will be trained, selected or unsealed until the protocol is approved and frozen.

## Addendum (2026-10-03): what became of this proposal

Frozen as protocol v1 (`docs/130`), amended by v2 (`docs/131`) and v3 (`docs/132`), and tested once on 2022 (`docs/133`). The decision rule P1 to P4 was kept; the interval level became 97.5 percent because two candidate sets were scored on the same year.
