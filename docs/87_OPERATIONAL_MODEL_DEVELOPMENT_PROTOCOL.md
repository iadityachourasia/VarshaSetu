# Phase 4H — Operational Model Development Protocol v1

## 1. Executive Summary

This is a **protocol-only** freeze for an operational-era, historical experiment. No model was fitted, no prediction or calibration was generated, and no 2025 outcome was opened. The machine-readable authority is `experiments/recent_historical/operational_model_protocol_v1/protocol.json`; its exact bytes and the case-ID-only fold manifest are SHA-256 checked by Phase 4H tests. Any changed rule requires a separately versioned v2.

## 2. Motivation

Phase 4G validates deterministic, regime, ensemble and paired-target inputs, but cannot materialize its 26-feature probability matrix: corrected M2 rainfall and three regime probabilities require future model inference. In-sample 2023 versions of those four fields would leak the training target or fitted regime relationship. Phase 4H specifies how a later phase can build them out-of-fold.

## 3. Phase 4G Inputs

The frozen feature-generation manifest SHA-256 is `f1520a32aadef460249ba26a39c106f9593fcd3407c23d2967ddc90d889ed67b`; future split `c400c36d793b68f394774c999bbf6729a439cc9d3bdd415ca9a33f27ce4520b5`; 2024 common-population manifest `f4859ee75e94994b97b0988cd5941a08097a6bcff97527534997a7b49093ce56`; feature contract `100894f11b677b1de20869d7a741ed16d770d2f4dbff415084fe9888a393842f`. Phase 4G validation reports 2023 200 paired deterministic cases / 260,200 cells, 375 regime cases and 76 paired ensemble cases; 2024 183 / 238,083, 375 and 67; 2025 forecast-only 232 deterministic and 375 regime cases. Phase 4H does not open 2025 reference data.

## 4. Experimental Roles

2023 is training and grouped cross-fitting; 2024 is prospective validation, calibration and selection; 2025 is sealed one-time final test. The 2025 forecast-input population is a frozen inventory, not a source for feature/model/threshold design.

## 5. Leakage Threat Model

Threats include random spatial-cell splits, multiple leads from one initialization crossing folds, target-derived pseudo-labels, in-sample upstream stacking features, outer-heldout-fold hyperparameter selection, fitting preprocessing on validation/test, reuse of 2024 calibration rows for calibration selection, and post-2025 retuning. Each is prohibited by the protocol and must be checked in Phase 4I.

## 6. Case-Level Grouping

One forecast case is initialization plus lead/product. All 1,301 paired spatial rows of a deterministic case stay together. All three forecast leads of an initialization, including regime-only cases, share a fold. Cell counts describe gridded coverage, not independent forecast realizations.

## 7. 2023 Cross-Fit Design

Sort the 125 2023 initialization dates and assign five consecutive blocks of 25 dates (`F1`–`F5`). No target or performance is used. The deterministic counts are **40, 39, 44, 43, 34** (total 200); each fold also has 75 regime cases. Each held-out block is excluded from fitting. A three-initialization-day embargo on either side is also excluded from its training set to reduce overlap of Day-3 valid windows across the boundary. This is retrospective grouped cross-fitting, **not a strict prequential simulation**: later 2023 dates may train a model predicting an earlier held-out block. The calendar and lead counts are recorded per fold in `crossfit_folds_2023.json`; QC-driven imbalance is not corrected after viewing labels. The full case-ID assignment is immutable under v1.

## 8. M0 Definition

M0 is raw operational GEFS c00 canonical 24-hour rainfall, with no fit or correction. It uses the exact same paired case/cell mask as M1–M4 for direct 2024 deterministic comparison.

## 9. M1 Definition

M1 is direct-mm Ridge MOS on the frozen 22-feature deterministic vector. Candidate alpha values are 0.1, 1, 10 and 100. Scaling is fitted on the training partition of 2023 only. Negative output is clipped to zero. Select on 2024 common-population RMSE; preserve MAE/bias. For cross-fitted diagnostic use, any selection must be nested within outer-training dates.

## 10. M2 Definition

M2 is global, non-regime XGBoost, direct `reg:squarederror`, histogram CPU, seed 26080, nonnegative output. Its four fixed candidates are depth 4/6 crossed with 200/350 rounds; learning rate .05, row/column sampling .9, lambda 2, minimum child weight 5. No regime class, pseudo-label or probability enters M2. To create upstream stacking features, select its configuration by **2023 grouped inner validation only**, inside each outer-training partition and separately on full-2023 grouped validation for the full fit. This prevents a 2024-target-selected upstream configuration from contaminating 2024 probability-validation features. The 2024 common set can compare the already-frozen candidates and the complete M0–M4 ladder by RMSE, but cannot retroactively change the M2 configuration used in upstream probability features. Fixed boosting rounds avoid early-stopping use of an outer-heldout fold. Depth then round count resolve ties.

## 11. M3 Definition

M3 routes to one of three forecast-only pseudo-label specialists using classifier argmax. Each specialist is fit only on eligible 2023 training cases assigned by training-only pseudo-label rules. A specialist needs at least 30 cases **and** 20,000 paired cells; otherwise its predefined gate uses the same fold-local/full-fit global M2 fallback. In any OOF analysis, neither the chosen expert nor fallback has seen the held-out case target.

## 12. M4 Definition

M4 blends the **same** three M3 expert/fallback predictions with forecast-only regime probabilities summing to one. It does not get a separately trained expert set. OOF analyses require both expert predictions and gating probabilities to be outer-fold isolated; 2024 uses 2023-only fits.

## 13. Regime Pseudo-Label Policy

Reuse Phase 2A's deterministic **forecast-only formulas and three conceptual classes** (ACTIVE_MONSOON, BREAK_WEAK_MONSOON, LOW_DEPRESSION_INFLUENCED), versioned for operational-era fitting. Its 2017-specific fitted-year implementation cannot simply be reused; operational normalization/quantile thresholds must fit on the relevant 2023 training partition only. Do not tune rules against IMD rainfall. These are pseudo-labels, not independently observed meteorological truth.

## 14. Regime Classifier Protocol

Use 12 frozen forecast-only regime features. The bounded candidate set is multinomial logistic C=0.1 or 1.0, with preprocessing fit within 2023 training dates. Choose by 2023 grouped-inner balanced **agreement with deterministic forecast-only pseudo-labels**, smaller C on ties. Never describe that metric as independent meteorological accuracy. Full 2023 fit produces prospective 2024 probabilities.

## 15. OOF Regime Probabilities

For each outer fold, fit pseudo-label thresholds and classifier only on permitted other 2023 dates after embargo, then predict all held-out regime cases. Preserve case order, class order and fit lineage. The three probabilities must be finite, bounded and sum to one. No IMD rainfall or M2 correction is an input.

## 16. OOF M2 Corrections

For each outer fold, choose M2 candidate by training-only grouped inner validation; fit on outer-training paired cases after embargo and predict the held-out paired cases. Record case ID, fold, fit ID, prediction and training/heldout membership hashes. Restore Phase 4G case/pixel ordering exactly. Fail on missing/duplicate predictions or any training/heldout case intersection. No in-sample predictions enter the probability matrix.

## 17. Probability Feature Completion

Only after both OOF paths pass alignment/lineage checks may Phase 4I append four fields to the frozen 22 features: M2 corrected rainfall and three regime probabilities. On 2023 all four are OOF; on 2024 all four are prospective predictions from 2023-only fits. For 2025, use only final frozen upstream fits after Phase 4I's readiness freeze and before any authorized later unseal. The current 26-feature matrix remains **unmaterialized**.

## 18. Heavy Model Protocol

Target is IMD rainfall ≥64.5 mm/24 h. Train on 2023 paired cells with the completed leakage-safe 26 features. Candidates are balanced logistic C=.1/1 and one CPU XGBoost binary configuration (depth 3, 180 rounds, learning rate .05, sampling .9). Weighting derives from 2023 training labels only; no SMOTE or synthetic events.

## 19. Very-Heavy Model Protocol

Target is IMD rainfall ≥115.6 mm/24 h, separate from Heavy. Use the same bounded family but select/calibrate independently; sparse positives may disqualify isotonic. Always report positive cell **and case** counts and undefined metrics explicitly. No assumed transfer of the historical logistic winner.

## 20. Calibration

Chronologically divide 2024 by initialization: first 60% for calibration, remaining dates for selection, with three dates purged around the boundary. All leads of an initialization stay together. Candidate transforms are identity, sigmoid and isotonic; isotonic is eligible only with at least 20 positive forecast cases and 100 positive cells in its calibration block. Select lowest Brier on the disjoint later block, tie order identity/sigmoid/isotonic. Report uncalibrated and calibrated scores separately. Selection of probability-model family also uses this disjoint selection block; if used for both family and calibrator choice, report that selection score as *model-selection validation*, not unbiased calibration performance. 2025 remains the independent final evaluation.

## 21. Decision Thresholds

For each event target independently, search only {0.05, 0.10, …, 0.95} on later 2024 selection dates and maximize CSI, breaking ties to the lowest threshold. Undefined CSI cannot win. Freeze chosen cutoffs before 2025; continuous probability metrics remain distinct from categorical performance.

## 22. Ensemble Baseline

P0 is the valid-five-member fraction exceeding the event threshold, never invented for control-only cases. Head-to-head ML/P0 comparison uses only `COMMON_PROBABILITY_ENSEMBLE_2024`: 67 cases / 87,167 identical cells. Larger ML validation is reported separately, not compared as if denominators matched.

## 23. 2024 Validation Metrics

Deterministic primary RMSE; secondary MAE/bias; heavy/very-heavy POD, FAR, CSI, ETS; FSS only on actual aligned 2-D grids and explicitly valid masks. Probability metrics: Brier, BSS, PR-AUC, ROC-AUC, reliability bins and frozen-threshold POD/FAR/CSI/ETS. BSS reference is the constant 2023 paired-training event prevalence, not a year-specific refit; zero reference Brier makes BSS null with reason. Undefined metrics always carry a reason and event/case counts. Report improved and worsened cases versus Raw and lead-specific performance. Do not choose a new universal winner for each metric.

## 24. Common Comparison Populations

All direct M0–M4 claims use `COMMON_DETERMINISTIC_2024` exactly: 183 cases / 238,083 paired cells, with one mask and identical input availability. The ensemble probability comparison is the separate 67-case common subset. No 2025 result exists in this phase.

## 25. Applicability-Domain Plan

Phase 4C found substantial predictor shift. Candidate *diagnostics*, not a fabricated scalar score, include 2023-training p01–p99 exceedance fraction, extreme feature exceedances, regime-input support and source QC state. Any user-facing cutoff requires predeclared candidates and 2024 validation. Primary future 2025 scoring must include all eligible cases before stratified applicability reporting; do not hide difficult cases.

## 26. Final Model Fit Policy

Choose **Option A: full 2023 only**. Upstream M2 and regime configuration use 2023 inner grouped selection, then full-2023 fit; probability candidates train on 2023 OOF-completed matrix. 2024 selects among already frozen outputs and fits calibrators only in its declared early block. No final refit on 2024 targets before 2025 unseal. This sacrifices sample size but preserves a clean prospective 2024 comparison and simple 2025 calibration lineage.

## 27. 2025 Holdout Governance

2025 IMD observations, events and skill are sealed. Before a **later explicit** unseal require: Phase 4G and fold hashes; model architecture, hyperparameter, regime-rule, probability-model, calibration, threshold and applicability freezes; final model hashes; metric and population definitions; a `FINAL_TEST_READY` manifest; and a specific unseal authorization record. Evaluate outcomes once with no post-test retuning.

## 28. Safe Model Serialization

XGBoost artifacts use native JSON/UBJ. Ridge, logistic, scalers and calibrators use explicit safe JSON/numeric arrays (`allow_pickle=False`). Hash all artifacts and lineage. Pickle/joblib are not authoritative.

## 29. Compute Plan

Default CPU XGBoost; the retrospective CUDA scientific-equivalence failure does not justify silent GPU use here. Approximately 12–14 effective CPU threads for a single fit, no nested oversubscription, peak RAM target ≤18–20 GB, hash-verified Phase 4G matrix reuse and no repeated GRIB decode. A separate approved CPU/GPU equivalence protocol would be required to change device.

## 30. Stop Conditions

Stop on fold/group overlap, source-hash mismatch, population drift, unsafe serialization, different 2024 common mask, 26-feature row misalignment, any 2025 observation access, need to change v1, or scientific-input redefinition. Do not repair by silently changing the frozen protocol.

## 31. Future Phase 4I Execution

Sequence: (A) verify frozen folds; (B) OOF regime probabilities; (C) OOF M2 correction; (D) completed 2023 26-feature matrix; (E) 2023 M0–M4 fits; (F) 2024 common deterministic selection; (G) prospective 2024 upstream probability features; (H) probability candidates, disjoint calibration and validation; (I) final 2023-only model/calibrator/threshold freeze; (J) `FINAL_TEST_READY` and **stop before 2025 outcomes**. The ordering of B/C may be interleaved only when isolation and lineage stay identical.

## 32. Reproducibility

`build_protocol.py` reads only input manifests and case metadata, checks exact frozen SHA-256 values, and deterministically emits canonical sorted-key JSON. It does not load `X.npy`, labels, observations or models. `backend/tests/test_phase4h_protocol.py` regenerates both objects in memory to verify byte equality, group coverage, fixed candidate counts, roles and safe serialization. The fold JSON contains 200 deterministic and 375 regime case assignments; no spatial row is separately assigned.

## 33. Decision Gate

`AUTHORIZED_FOR_OPERATIONAL_MODEL_DEVELOPMENT`: the protocol and ID-only folds are frozen and Phase 4I may implement 2023 grouped training/cross-fit and 2024 validation/calibration under these rules. This **does not** authorize 2025 outcome access, operational deployment, frontend/API changes, or an unbounded search. If any mandatory integrity or leakage check fails, replace this decision with `NEEDS_MODEL_PROTOCOL_REVISION` or `MODEL_DEVELOPMENT_BLOCKED` before training.
