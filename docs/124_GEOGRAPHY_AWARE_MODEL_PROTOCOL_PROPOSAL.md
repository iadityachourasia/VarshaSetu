# Phase 9A: geography-aware correction (Stage 3 / M5), protocol PROPOSAL — not frozen, awaiting approval

Date: 2026-10-01. **Status: PROPOSED.** Nothing here has been trained, tuned or frozen; no model, data or evaluation year was touched to write it. Values marked *proposed* are
decisions for the project owner. On approval they would be copied into a machine-readable, hash-frozen protocol (as for `docs/112` and `docs/115`) before any training starts.
Protocol first, then stop for approval, is the standing rule for every science-changing step.

## 1. Why this is the next scientific step

The problem statement asks for improved forecasts, especially for heavy and very-heavy rain. That is the project's weakest requirement (PS-R05 is PARTIAL): RMSE improves over Raw, but
heavy-rain skill is mixed and very-heavy skill does not improve. The zone analysis (`docs/117`, `docs/118`) located the deficiency precisely:

- The 109 coastal-and-orographic cells (the Western Ghats coast, 8 % of land cells) hold 35 to 43 % of all observed heavy-rain cell-case pairs in every population.
- Raw forecasts only about 7 to 22 % as many heavy events as were observed there, in both tracks and all four years.
- No frozen model removes this. On the operational-era track M2 to M4 recover part of it (in the strong-forcing stratum, heavy frequency bias 0.57 to 0.80 in 2024 and 0.15 to 0.29 in 2025); on the 2019 reforecast track they recover almost nothing.
- Heavy rain there falls almost entirely under strong cross-barrier forcing (83 to 94 % of the zone's events), so the information a model needs is physically identifiable from the forecast.
- In the interior the corrected models forecast almost no heavy rain at all.

A model that is given geography and forecast-time forcing explicitly is the natural, evidence-grounded candidate. It is **not** certain to help: the evidence shows a deficiency, not that
this remedy cures it, and the answer may be "no gain", which would be reported as such.

## 2. The blocker: there is no untouched test period

| Year | State |
|---|---|
| 2019 | Consumed final test of the reforecast track |
| 2025 | Consumed one-time final test of the operational track |
| 2024 | Used for model selection and calibration (M1 was chosen on it) |
| 2023 | The only training year of the operational track |

Any new model therefore cannot be judged on a clean holdout without new data. Options for the owner (decision **D1**):

| Option | What it gives | Cost and uncertainty |
|---|---|---|
| (a) New operational-era corpus for 2021 and 2022, with 2022 sealed as the independent test | A genuine independent test and a larger training set (2021 and 2023, validate on 2024) | Compatibility of the 2021–2022 GEFS archive with the corpus is **unverified**; needs a source probe, the two years' forecast downloads (the earlier years took about an hour each, an estimate that does not transfer automatically) and IMD annual files for 2021 and 2022 under IMD's unresolved redistribution terms |
| (b) Development-only | A frozen protocol, training on 2023, comparison on 2024 (already reused) and a labelled post-hoc comparison on 2025, no independent claim | No new data; honest but weaker: the result could say "a promising candidate", not "validated" |
| (c) Wait for JJAS 2026 | An independent season for free | The 2026 forecast archive can be fetched soon, but the IMD 2026 annual file's release date is unknown; delays the result |

**Recommendation:** (b) now, so the work can proceed and the evidence is on the table, with (a) as a separate later approval if the result justifies an independent test. State the limit plainly on every output.

## 3. Proposed design

| Item | Proposal |
|---|---|
| Track | Operational-era (Track B) only. The reforecast track did not show the same behaviour, and the zones' forcing behaviour differs by track, so the two are not pooled |
| Training data | 2023 only: 200 paired cases, 260,200 cell rows. Training-year (observation-only) support is adequate: 4,851 heavy-rain rows overall, of which 1,554 in the Ghats-coast zone across 102 cases, and 378 very-heavy rows there |
| Existing baselines kept | M0 Raw, M1 Ridge MOS, M2 global XGBoost, M3, M4, all frozen and untouched. The strongest non-regime comparator is **M2** |
| M5a (first candidate) | One global gradient-boosted model with the 22 existing forecast-time features **plus** static geography (elevation, local relief, distance to coast, slope, terrain and coast unit vectors from `static_geography_v1`) **plus** forecast-time forcing (onshore and cross-barrier components times precipitable water, `docs/118`), no hard experts, which avoids the starvation seen in the Break/Weak experts |
| M5b (only if M5a shows zone-specific gain) | Zone-conditioned experts, shrunk toward M2 by support (zones as defined in protocol v3, not learned) |
| Not proposed | Deep learning, new regime classes, LightGBM, CatBoost, Optuna or any new dependency (only scikit-learn and XGBoost are installed; the standing rule is no escalation before data validity is settled) |
| Targets | Direct 24-hour rainfall, non-negative output; objective squared error (as M2) with one declared alternative, a heavy-tail-aware loss, chosen by grouped validation in 2023 only |
| Event emphasis | Optional case-capped event weights with a frozen cap (*proposed*: at most 10 times) judged by effective sample size; no extreme weights |
| Feature registry | A **new versioned registry** (v2); v1 is not edited. Static geography is allowed at forecast time (`AGENTS.md` section 3.4); no observation or target-derived feature enters |
| Cross-validation | The frozen 2023 five date-block folds with the three-initialization-day embargo (`docs/87`); one case, all its cells and all leads of an initialization stay together |
| Hyperparameters | A small fixed grid in the style of M2 (depth, rounds), no open-ended search; selected on 2023 grouped validation only; CPU XGBoost, seed 26080 (the GPU path failed the project's equivalence gate, `docs/87` section 29) |
| Evaluation | M5 against M0 to M4 on RMSE, MAE, bias, heavy and very-heavy POD, FAR, CSI, ETS and frequency bias, **overall and by the four geographic zones of protocol v3**, plus by lead and pseudo-regime, with the paired whole-case bootstrap and the existing support gate |
| Populations | 2024 development evidence; 2025 `POST-HOC EXPLORATORY ANALYSIS OF THE COMPLETED 2025 FINAL TEST` (never used for selection); an independent test only under option D1(a) or (c) |

## 4. Proposed decision rule and guardrails (to be frozen, decision **D3**)

M5 is reported as "adds value" only if **all** hold on the evaluation population:

1. It beats M2 on heavy-rain CSI in the Ghats-coast zone, with the paired 95 % interval excluding zero.
2. Its overall RMSE is not worse than M2's by more than a frozen tolerance (*proposed*: 0.2 mm).
3. G1: heavy CSI overall is not below Raw's. G2: absolute overall bias at most 1.5 mm. G3: very-heavy forecast frequency bias at least 0.05 (this stops a model that never forecasts very-heavy rain from passing).
4. The result is stated for the operational-era track only, with the limit of option D1 attached.

If the rule is not met, the honest result is "no evidence that geography-aware features improve on M2", and the coverage status stays PARTIAL. If it is met under option (b), the status is still not
"implemented": it would say "a candidate that improves on M2 in development evidence".

## 5. Risks stated up front

- One training year; the model could learn year-specific patterns. The grouped folds reduce but do not remove this.
- The 0.25 degree zone geometry is coarse; a null result is a statement about this resolution.
- 2024 has been used for selection already; it can support a comparison but not an unbiased estimate.
- Heavy-rain events within a case are spatially correlated; bootstrap intervals remain optimistic.
- Choosing the heavy-tail loss, the event-weight cap and the grid on 2023 folds must not leak into 2024 or 2025 choices.

## 6. Decisions requested

1. **D1** independent test period: (a), (b) or (c); recommendation (b) first.
2. **D2** IMD redistribution terms: not required for local CPU training under (b) (no data leave this machine), but required before any new IMD year is added under (a) and remains unresolved for the already-public bundle.
3. **D3** guardrail and tolerance values in section 4.
4. **D4** approval of the feature set (static geography and forecast-time forcing) and the new registry version.
5. **D5** model families and scope (M5a first; M5b only conditionally; no new dependencies).

Gate: `P3_STAGE3_PROTOCOL_PROPOSED_AWAITING_APPROVAL`. Nothing will be trained until the protocol is approved and frozen.
