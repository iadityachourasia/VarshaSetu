# Phase 4J — one-time operational-era 2025 final test

## 1. Executive Summary

The operational-era experiment's frozen **M1 Ridge MOS** reduced common-cell 2025 RMSE from **16.1657** to **15.5736 mm** (−0.5922 mm; −3.6631%). This is the primary preselected final-test result, not a post-test model choice. On the same 232 cases and 301,832 cells, M2 XGBoost had a lower **secondary** RMSE of 15.0022 mm; it does **not** replace selected M1. Raw GEFS beat M1 on both extreme-event FSS thresholds at every neighborhood scale. The one-time holdout is consumed.

## 2. Final-Test Governance

2023 was train/cross-fit, 2024 validation/calibration/selection, and 2025 the untouched final test. The Phase 4I selection, models, calibration, thresholds, metrics, source QC and applicability policy were not changed after unseal. The result is an historical selected-range experiment, not a live operational claim.

## 3. Readiness Verification

`FINAL_TEST_READY.json` matched SHA-256 `67170a350abb0663aedb2ea129d4eac3ce10ce9d77863af43b4f5c22700b2b48`. The Phase 4H protocol and folds matched `cfe273d765ae943ea0dc394439436af09391a4c25e3684629732394801582770` and `151f574906666648e673d0e3d6e918405156b5bd5a2a2122589a755a2a4a0f95`. The Phase 4G feature freeze and split matched `f1520a32aadef460249ba26a39c106f9593fcd3407c23d2967ddc90d889ed67b` and `c400c36d793b68f394774c999bbf6729a439cc9d3bdd415ca9a33f27ce4520b5`. Phase 4I verification covered every listed artifact and source-code pin. The forecast-only Phase 4G 2025 verifier returned 232 deterministic, 75 five-member and 375 regime cases.

## 4. Unseal Authorization

The user explicitly authorized a *one-time* observation opening after the integrity gate. The append-only `UNSEAL_AUTHORIZATION.json` SHA-256 is `e03668e8524e22bafce59a47abfb2cbdd1a0aea6716aacfa07293e1406a8ca12`. Separate immutable records preserve `SEALED → AUTHORIZED_TO_UNSEAL → UNSEALED_FOR_FINAL_EVALUATION → FINAL_TEST_COMPLETED` without rewriting the historical Phase 4I sealed record.

## 5. 2025 Observation Source

The pre-acquired official IMD RF25 annual `RF25_ind2025_rfp25.nc` matched source SHA-256 `7d03cd397ebb1d7209ffae947d3965113643e1f30023cca657f0aa2c800af035`. No redownload was made. The 49×49 target grid was joined at initialization plus one, two or three calendar days for Day 1/2/3. IMD daily date labels do **not** supply explicit accumulation-bound metadata; the timing limitation remains.

## 6. Final Population

Of 375 scheduled source cases, 232 passed frozen deterministic source eligibility (75/75/82 at 24/48/72 h). All 232 had available aligned IMD outcomes; there were zero observation/mask rejections. The *pre-scoring* population manifest fixed 301,832 valid paired cells (1,301 per case), exact case IDs, source-row indices and target-grid pixels. All M0–M4 and probability comparisons use this same population and mask. All 75 five-member source cases paired with observations, yielding 97,575 common ensemble cells. No poor-performing case was excluded.

## 7. M0 Raw GEFS

M0 is the source-qualified operational GEFS c00 24-hour rainfall: RMSE **16.1657**, MAE **7.6536**, bias **−1.2650 mm**.

## 8. Selected M1 Ridge

The 2024-selected Ridge MOS, alpha 0.1, was loaded from its frozen safe JSON artifact (SHA-256 `dab6547f1ebee9408b90430f8074258d0520bf3bbdc9f6731a2f9ff9cd9e0395`). RMSE **15.5736**, MAE **7.5802**, bias **−1.2023 mm**. It was not refit.

## 9. M2 Global XGBoost

The 2023-trained, pre-frozen global XGBoost yielded RMSE **15.0022**, MAE **7.3987**, bias **−0.9266 mm**. This is a secondary comparator. Its stronger 2025 RMSE is descriptive; post-holdout substitution for selected M1 is prohibited under this version.

## 10. M3 Hard Routing

The shared frozen specialists and forecast-only regime classifier yielded RMSE **15.4608**, MAE **8.0405**, bias **+0.1657 mm**. No specialist was refit or newly selected.

## 11. M4 Soft Mixture

The same specialists blended by frozen forecast-only regime probabilities yielded RMSE **15.2153**, MAE **7.9682**, bias **+0.2513 mm**. M4 improved on M3 but did not beat M2 on overall 2025 RMSE.

## 12. Primary RMSE Result

The frozen primary comparison M1 minus M0 is **−0.592163 mm**, or **−3.663079%** of M0 RMSE. Classification: `SELECTED_MODEL_IMPROVED_RMSE`. This applies only to the evaluated paired population.

## 13. MAE and Bias

| Model | RMSE mm | MAE mm | Bias mm |
|---|---:|---:|---:|
| M0 Raw | 16.1657 | 7.6536 | −1.2650 |
| M1 selected Ridge | 15.5736 | 7.5802 | −1.2023 |
| M2 Global XGBoost | 15.0022 | 7.3987 | −0.9266 |
| M3 Hard Routing | 15.4608 | 8.0405 | +0.1657 |
| M4 Soft Mixture | 15.2153 | 7.9682 | +0.2513 |

## 14. Lead-Specific Results

| Lead | Cases | M0 RMSE | M1 RMSE | M2 RMSE | M3 RMSE | M4 RMSE |
|---|---:|---:|---:|---:|---:|---:|
| Day 1 / 24 h | 75 | 15.5951 | 15.3501 | 15.0010 | 15.6084 | 15.2850 |
| Day 2 / 48 h | 75 | 16.0150 | 15.2790 | 14.6955 | 15.0170 | 14.8711 |
| Day 3 / 72 h | 82 | 16.8030 | 16.0365 | 15.2785 | 15.7231 | 15.4607 |

## 15. Case-Level Error Changes

M1 improved RMSE against Raw in **166** cases, worsened it in **66**, and tied in **0**. Median M1-minus-Raw case RMSE change was **−0.3875 mm**. The largest improvement was `20250911_day3_24h` (−5.2590 mm); largest deterioration was `20250616_day1_24h` (+1.7578 mm). Neither was removed. Exact per-case values are frozen in `metrics/case_level.json`.

A read-only post-freeze tally of the *same frozen predictions and paired observations* gives M0 **0/0/232**, M1 **166/66/0**, M2 **176/56/0**, M3 **153/79/0**, and M4 **161/71/0** improved/worsened/tied cases versus Raw. This supplementary tally does not change `FINAL_TEST_RESULT.json`, select a different model, or reopen the test.

## 16. Heavy Deterministic Verification

Threshold: inclusive **≥64.5 mm/24 h**. There were **6,760** observed event cells across **213** cases. On 301,832 common cells:

| Model | POD | FAR | CSI | ETS |
|---|---:|---:|---:|---:|
| M0 | .0558 | .7498 | .0478 | .0437 |
| M1 | .0209 | .6706 | .0200 | .0187 |
| M2 | .0783 | .4918 | .0727 | .0698 |
| M3 | .1065 | .5623 | .0937 | .0893 |
| M4 | .0975 | .5204 | .0882 | .0844 |

M1's FAR is lower, but its POD/CSI/ETS are materially worse than Raw. Continuous RMSE improvement does not establish improved heavy-event detection.

## 17. Very-Heavy Deterministic Verification

Threshold: inclusive **≥115.6 mm/24 h**. There were **1,430** event cells across **121** cases.

| Model | POD | FAR | CSI | ETS |
|---|---:|---:|---:|---:|
| M0 | .0217 | .8187 | .0197 | .0192 |
| M1 | .0098 | .3913 | .0097 | .0097 |
| M2 | .0007 | .6667 | .0007 | .0007 |
| M3 | .0231 | .5769 | .0224 | .0221 |
| M4 | .0091 | .6176 | .0090 | .0088 |

Undefined metric rules preserve `null` and reasons; no undefined FAR was changed to zero. M1 again improves FAR but worsens POD/CSI/ETS relative to Raw.

## 18. Heavy FSS

The frozen true-2D, 49×49 implementation used clipped edges, ≥50% valid neighborhoods and identical paired masks. Scores below are matched-case values (214 cases at each size):

| Neighborhood | Raw M0 | selected M1 |
|---|---:|---:|
| 1×1 | .0912 | .0392 |
| 3×3 | .1561 | .0667 |
| 5×5 | .1949 | .0836 |
| 9×9 | .2523 | .1063 |

## 19. Very-Heavy FSS

Scores below use the **121 matched defined cases** at each size. Raw alone had 124 defined cases; the unmatched Raw value is not used as a head-to-head claim.

| Neighborhood | Raw M0 | selected M1 |
|---|---:|---:|
| 1×1 | .0390 | .0193 |
| 3×3 | .0860 | .0379 |
| 5×5 | .1237 | .0537 |
| 9×9 | .1713 | .0711 |

Extreme spatial classification: **`RAW_BETTER`** at both thresholds and all declared scales.

## 20. Regime Analysis

The frozen 2023-trained classifier produced forecast-only pseudo-regime probabilities. Among paired cases, predicted classes were Active Monsoon **100**, Break/Weak **71**, and Low/Depression Influenced **61**. Overall RMSE was M2 **15.0022**, M3 **15.4608**, M4 **15.2153**. M2 also had lower RMSE than M3 and M4 in every predicted-class subgroup (see `metrics/regime.json`). These labels/probabilities are **not verified meteorological truth**.

## 21. Heavy Probability Final Test

The frozen 26-feature heavy logistic-C1 model and 2024 isotonic calibrator produced bounded probabilities without 2025 targets as predictors. On 232 cases / 301,832 cells: Brier **.0198313**, BSS **+.09483**, PR-AUC **.21736**, ROC-AUC **.89455**. The fixed BSS reference is the 2023 training prevalence **.01864335**, not a 2025-tuned climatology. At the 2024-frozen probability cutoff **.10**: POD **.27796**, FAR **.69576**, CSI **.16994**, ETS **.15942**. The final artifact includes ten reliability bins with counts. Calibration did **not** transfer perfectly: in the largest 0–10% bin (295,656 cells), mean forecast was **.00731** versus observed frequency **.01651**; the 10–20% bin forecast **.13481** versus observed **.25198**. Upper bins are sparse and do not support broad calibration claims.

## 22. Very-Heavy Probability Final Test

The separate frozen logistic-C0.1 and 2024 isotonic calibrator yielded Brier **.00459023**, BSS **+.02652**, PR-AUC **.07951**, ROC-AUC **.90344**. Fixed BSS reference: 2023 prevalence **.00473866**. At the frozen **.05** cutoff: POD **.12378**, FAR **.85492**, CSI **.07157**, ETS **.06940**. The largest 0–10% reliability bin (301,522 cells) forecast mean **.00096** versus observed frequency **.00456**, again underforecasting; upper bins are extremely sparse. The high FAR and reliability gaps remain limitations; no threshold was adjusted.

## 23. Ensemble Baseline

On the identical **75-case / 97,575-cell** five-member common population, the threshold-fraction baseline versus frozen calibrated ML gave Brier **.0228866 vs .0208497** (heavy) and **.00502342 vs .00493453** (very heavy). These matched-population comparisons must not be conflated with full-population Brier values.

## 24. Applicability Diagnostics

Frozen policy: `NO_USER_FACING_APPLICABILITY_CUTOFF`; all 232 cases remained in the primary result. The mean fraction of 22 forecast features outside 2023 p01–p99 was **.02513**. Q700 was below/above its 2023 bounds in **.00161/.00409** of cells; PWAT **.00032/.00476**; moisture-transport proxy **.00862/.05603**. These are descriptive, not rejection criteria.

## 25. Distribution Shift

The corresponding 2024 outside-bound fraction was **.04161**, versus **.02513** in 2025 on its different eligible population. The most visible 2025 signal is moisture-transport proxy above the 2023 p99 in **5.60%** of cells. No normalization, model, or cutoff changed and no climate-trend attribution is made from three years.

## 26. 2024 vs 2025 Stability

2024 validation Raw/M1 RMSE was **17.1297/16.7975 mm**; 2025 final Raw/M1 was **16.1657/15.5736 mm**. Heavy Brier changed **.0210700 → .0198313**, PR-AUC **.31489 → .21736**. Very-heavy Brier changed **.00609501 → .00459023**, PR-AUC **.12653 → .07951**. Extreme FSS in both years favored Raw over selected M1. These are descriptive comparisons across different cases/event rates, not a basis for re-selection.

## 27. Relationship to 2019 Benchmark

The separate reforecast-lineage 2017/2018/2019 experiment reported Raw **19.7735 mm**, Global XGBoost **17.8487 mm**, **9.73%** reduction. It is **not pooled** with 2023/2024/2025 operational-lineage metrics. The selected final models and source populations differ.

## 28. Scientific Limitations

The selected-range sample is not a current-date operational service. IMD annual daily labels lack explicit accumulation bounds. Spatial cells are correlated within cases; 301,832 cells are not independent forecast cases. Probability upper reliability bins are sparse, especially very-heavy. No predeclared uncertainty interval was frozen, so none was invented. The regime classes are classifier reproductions of forecast-only pseudo-labels, not observed circulation truth. Neither improved continuous error nor positive BSS guarantees good deterministic extreme detection or spatial FSS.

## 29. Final Claims

Continuous rainfall: selected M1 improves RMSE versus Raw on the frozen primary population. Extreme detection: M1 has lower FAR but worse POD/CSI/ETS at both thresholds. Spatial extremes: Raw beats M1 at every FSS scale. Probability: Heavy and Very Heavy have positive BSS against the fixed 2023 prevalence reference, but Very Heavy has high cutoff FAR. Regime conditioning: M4 beats M3 on RMSE but neither beats M2. Applicability: all cases retained; shift diagnostics descriptive only.

## 30. Artifact Freeze

`experiments/recent_historical/phase4j_operational_final_test_v1/` contains immutable authorization/state records, exact population/observation pairing arrays and manifests, M0–M4 predictions, regime/probability/ensemble predictions, all metric tables, and `FINAL_TEST_RESULT.json`. The result SHA-256 is **`04a7fc2a434d24449365e2cb9978cbc8584f5cc87ea4f132cfaf6e7fc7a4abca`**. Its manifest binds upstream model/calibration/threshold/source hashes, prediction and metric hashes, population hash, authorization hash and UTC completion time. The append-only `ARTIFACT_INTEGRITY.json` inventories 37 Phase 4J files and has SHA-256 **`b386785ee0c2be3162456f24e5d5cea0cd24b05767f3d67c9459b908359bcf1a`**. Do not rewrite the result.

## 31. Reproducibility

Phase 4J focused tests independently recalculate continuous and threshold metrics from frozen arrays, verify prediction/metric hashes, masks, ensemble alignment, FSS bounds, authorization and the no-second-test guard. The final focused run passed **11 tests**; the full backend suite passed **157 tests** with one upstream Starlette/AnyIO deprecation warning; Python compilation passed. Protected read-only verification rehashed Phase 4B **813**, Phase 4C **13**, Phase 4E **64,610**, and Phase 4F **28,335/28,351/28,383** year files, plus IMD 2023–2025 sources, Phase 4D/H locks, Phase 4G 2023–2025 manifests, and Phase 4I `FINAL_TEST_READY`. A future identical-artifact reproducibility audit may verify hashes and outputs but may not reopen model selection or create a second holdout claim.

## 32. Final Decision

Deterministic primary: **`SELECTED_MODEL_IMPROVED_RMSE`**. Extreme spatial: **`RAW_BETTER`**. Heavy and very-heavy probability: separately positive BSS, with high very-heavy FAR. Project-level status: **`OPERATIONAL_ERA_BENCHMARK_COMPLETE`**. The exact next task is an independent read-only scientific audit of the frozen Phase 4J evidence; any changed model must use a new experiment version and cannot call 2025 untouched again.
