# Phase 4I — Operational-Era Model Development, 2023–2024

## 1. Executive Summary

Decision: **`FINAL_TEST_READY`** for a later, separately authorized 2025-outcome evaluation—not operational deployment. The frozen Phase 4H protocol was executed on Phase 4G source-eligible 2023/2024 populations. The untouched 2025 outcome status remains **SEALED**. On 183 common 2024 deterministic cases (238,083 paired cells), **M1 Ridge MOS** had the lowest model-selection RMSE, 16.7975 mm versus Raw 17.1297 mm. This is a 2024 validation/model-selection outcome, not final-test skill. Extreme-event FSS was markedly worse for the selected correction than Raw; probability modeling is reported separately.

## 2. Frozen Protocol

Authority: `experiments/recent_historical/operational_model_protocol_v1/protocol.json`, SHA-256 `cfe273d765ae943ea0dc394439436af09391a4c25e3684629732394801582770`; five-fold manifest SHA-256 `151f574906666648e673d0e3d6e918405156b5bd5a2a2122589a755a2a4a0f95`. Phase 4G feature freeze `f1520a32aadef460249ba26a39c106f9593fcd3407c23d2967ddc90d889ed67b` and split `c400c36d793b68f394774c999bbf6729a439cc9d3bdd415ca9a33f27ce4520b5` matched before training. Bounded candidate sets, year roles, masks, QC and thresholds were not changed.

## 3. Cross-Fit Verification

Five contiguous 25-initialization-date blocks have **40/39/44/43/34** paired deterministic cases and 75 regime cases each. All leads of an initialization and all 1,301 valid rows of a paired case stay together; each outer fit excludes its held-out block and three neighboring initialization dates on either side. The execution-time fold-verification artifact records exact training/heldout/embargo counts and hashes. Every 2023 case is held out exactly once.

## 4. 2023 OOF Regime Classifier

For each outer fold, Phase 2A forecast-only score formulas were refit as a **versioned operational 2023 rule** using only permitted training dates. Multinomial logistic C=.1/1 was selected by training-only two-block inner grouped validation. Fixed three-class macro recall counts a class absent from an inner validation block as zero rather than mistaking one-class agreement for full balanced agreement. Aggregate OOF balanced **agreement with deterministic forecast-only pseudo-labels** was **0.8806** across all 375 cases; the confusion matrix and each fold's agreement are preserved. This is not independent meteorological regime accuracy. Training pseudo-label rules, classifier coefficients, membership and prediction hashes are saved per fold. No IMD rainfall enters labels or classifier features.

## 5. 2023 OOF M2

For each outer fold, four frozen CPU XGBoost candidates (depth 4/6 × 200/350 rounds) were compared only inside its permitted 2023 training dates; the selected candidate fit those dates and predicted the held-out fold. All **260,200** paired rows have exactly one nonnegative OOF M2 correction; missing/duplicate counts are zero. The 2023 OOF RMSE was **14.6447 mm**, Raw **15.0881 mm**; MAE 6.7397 vs Raw 6.3323 mm, bias −0.0538 vs Raw −0.7360 mm. Cases improved/worsened versus Raw: **118/82**. These are *training-development OOF diagnostics*, not an independent-year test. OOF M2 was weak for very-heavy deterministic detection (CSI 0 against 1,233 observed event cells), a limitation not tuned away.

## 6. Probability Feature Completion

The frozen 22 Phase 4G forecast-only columns are followed by OOF M2 rainfall and OOF regime probabilities on 2023 (260,200 × 26 float32), and by **2023-fitted prospective** M2/regime predictions on 2024 (238,083 × 26). Case IDs, original row starts, target-grid pixel order, finite values and lineage hashes were checked. 2023 matrix SHA-256 `43c29e5721c3da0568a9f8a0c45bb9190ac6e0ac8c0b8aa07d224d16360e0a65`; 2024 matrix `7aee01ae505fa81cc11403b43de6a672dd86a8ad6a4eaf04f2d4bb8fc8fc28eb`. No in-sample upstream field substituted for an OOF field.

## 7. M0

Raw operational GEFS c00 24-hour rainfall, unchanged, on the same 2024 paired mask as M1–M4. It is a genuine forecast baseline, not a model fit.

## 8. M1

Ridge MOS was fitted on 2023 only using the frozen 22 features, training-only scaling and nonnegative output. Four predeclared alphas were evaluated on 2024; **alpha 0.1** minimized its RMSE. Coefficients and preprocessing are safe JSON.

## 9. M2

Global non-regime XGBoost used direct-mm squared-error loss on CPU, no CUDA. For leakage-safe upstream stacking, its configuration was selected by 2023 grouped-inner validation: **depth 6, 200 rounds**, learning rate .05, row/column fraction .9, lambda 2, minimum child weight 5. All four bounded candidates were fit on 2023 and descriptively scored on 2024; the upstream/lattice comparator configuration was not retrospectively changed by 2024 probability-target outcomes. It excludes regime identifiers/probabilities.

## 10. M3

Hard routing uses the 2023-fitted forecast-only classifier argmax and three pseudo-label specialists. All three passed the frozen support rule of ≥30 forecast cases and ≥20,000 cells; none used fallback in the final full-2023 fit. Experts use the same bounded M2 configuration and never train on 2024 targets.

## 11. M4

Soft mixture weights the **same M3 experts** by 2024 prospective regime probabilities. It had better RMSE than M3 but worse than M2 and M1 overall. No hidden M4-only expert set was fitted.

## 12. 2024 Deterministic Validation

Every row below is on the same **183 cases / 238,083 cells**; cells within cases are correlated. Units are mm/24 h for forecast/IMD reference and mm for error metrics.

| Method | RMSE | MAE | Bias | Cases better/worse than Raw |
|---|---:|---:|---:|---:|
| M0 Raw | 17.1297 | 8.2170 | −0.8542 | 0 / 0 (183 ties) |
| M1 Ridge MOS | **16.7975** | 9.2104 | +1.3274 | 104 / 79 |
| M2 Global XGBoost | 16.8459 | 9.1075 | +2.2352 | 113 / 70 |
| M3 Hard Regime | 17.4134 | 9.6935 | +3.1147 | 92 / 91 |
| M4 Soft Regime | 17.2628 | 9.6558 | +3.1466 | 102 / 81 |

M1 reduces 2024 RMSE by approximately **1.94%** relative to Raw on this selected source-eligible population, but has worse MAE and extreme skill. This is not proof of operational transfer or 2025 performance.

## 13. Lead-Specific Results

| Method | Day 1 RMSE | Day 2 RMSE | Day 3 RMSE |
|---|---:|---:|---:|
| Raw | 15.7703 | 16.9200 | 18.2122 |
| M1 | 15.5470 | 16.8131 | 17.6283 |
| M2 | 16.2630 | 16.8666 | 17.2351 |
| M3 | 16.9997 | 17.4990 | 17.6319 |
| M4 | 16.8450 | 17.3572 | 17.4765 |

Day-1/2/3 admitted case counts are 51/61/71, not 125 each; unchanged QC causes lead imbalance.

## 14. Case-Level Outcomes

The improved/worsened counts above compare per-case RMSE to Raw, not individual cell wins. M2 improves more cases than M1 despite its slightly worse cell-pooled overall RMSE. The report preserves this distinction and all failure cases.

## 15. Regime-Aware Comparison

On the exact common 2024 set, M2 RMSE **16.8459**, M3 **17.4134**, M4 **17.2628**. Soft routing is better than hard routing, but neither beats Global. By forecast-predicted regime, case counts Active 59 / Break-Weak 46 / Low-Depression 78; RMSE M2/M3/M4 respectively: Active **15.579/15.714/15.571**, Break-Weak **8.988/9.426/9.334**, Low-Depression **20.846/21.731/21.550**. These are classifier-predicted pseudo-regime groups, not externally verified meteorological regime truth. One small Active subgroup improvement by M4 does not establish overall regime-conditioned skill.

## 16. Extreme Deterministic Verification

2024 paired IMD event cells: Heavy **6,366**, Very Heavy **1,589**. At the inclusive 64.5/115.6 mm/24 h thresholds, Heavy CSI M0/M1/M2/M3/M4 is **0.0747/0.0257/0.2130/0.2299/0.2267**; Very-Heavy CSI **0.0153/0.0069/0.0437/0.0528/0.0354**. Full POD/FAR/CSI/ETS, hits, misses, false alarms, undefined reasons and matching denominators are in `deterministic_models/validation_manifest.json`. The RMSE-selected M1 is *not* the extreme-categorical winner; no per-metric model was relabeled universally best.

## 17. FSS

The frozen Phase 2C 2-D 49×49 implementation, paired pixel mask, 50%-valid local rule and clipped boundaries were reused. Thresholds are Heavy and Very Heavy; neighborhoods 1×1, 3×3, 5×5 and 9×9 target cells. Raw versus RMSE-selected M1 FSS:

| Threshold | Neighborhood | Raw | M1 | Matched defined cases |
|---|---:|---:|---:|---:|
| Heavy | 1 | .1390 | .0501 | 160 |
| Heavy | 3 | .2184 | .0791 | 160 |
| Heavy | 5 | .2389 | .0875 | 160 |
| Heavy | 9 | .2591 | .0924 | 160 |
| Very Heavy | 1 | .0302 | .0136 | 103 |
| Very Heavy | 3 | .0531 | .0240 | 103 |
| Very Heavy | 5 | .0650 | .0274 | 103 |
| Very Heavy | 9 | .0706 | .0275 | 103 |

Raw is better at every listed extreme FSS scale. The artifact also records per-method and matched-case denominators and null reasons. FSS neighborhoods are grid-cell scales, not exact kilometer radii.

## 18. Heavy Probability Model

Target: IMD ≥64.5 mm/24 h. 2023 training: **4,851 positive cells across 146 event-bearing cases**. Within the frozen logistic C=.1/1 and one depth-3/180-tree XGBoost candidate set, the selected base was **class-balanced logistic C=1**. Its 2023 inputs include only fold-isolated OOF upstream fields. Logistic parameters/scaler are safe JSON, not pickle.

## 19. Very-Heavy Probability Model

Target: IMD ≥115.6 mm/24 h. 2023 training: **1,233 positive cells across 71 cases**. The independently selected base was **class-balanced logistic C=.1**. This outcome was not forced from the older reforecast study.

## 20. Calibration

The 125 chronological 2024 initialization dates were split before fitting: first 72 dates for calibration, six boundary dates purged (three on either side of the nominal 75-date/60% boundary), final 47 dates for model/calibrator/threshold selection. On the paired population these contain **108/7/68** cases. Heavy calibration has 5,047 positive cells in 106 event-bearing cases; Very Heavy 1,256 in 71. Both pass the frozen isotonic sufficiency gate (≥20 event-bearing cases and ≥100 event cells); **isotonic** won Brier selection for both. This is fitted calibration, not a claim of perfect reliability. The selection block used to choose candidates is not an independent test.

## 21. Threshold Selection

On the disjoint 2024 selection block, the fixed 0.05–0.95 grid maximized CSI at **0.10 Heavy** and **0.05 Very Heavy**, lowest cutoff on ties. These are probability decision cutoffs, not rainfall thresholds. Every candidate score/hit/miss/false-alarm count is in the saved threshold tables and versioned `thresholds/*.json`.

## 22. Probability Validation

The 68-case, **88,468-cell 2024 selection block** is out of sample for base training and calibration fitting, but its scores helped select the base/calibrator/cutoff. They are therefore model-selection diagnostics, **not independent final-test estimates**.

| Target | Event cells / cases | Brier | BSS vs fixed 2023 prevalence | PR-AUC | ROC-AUC | POD | FAR | CSI | ETS |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Heavy | 1,242 / 47 | .011798 | .14899 | .28116 | .92536 | .37118 | .67535 | .20945 | .20222 |
| Very Heavy | 329 / 29 | .003369 | .09104 | .19997 | .95517 | .35258 | .76327 | .16501 | .16284 |

Ten-bin reliability counts/means/frequencies, uncalibrated candidate Brier scores and full-2024 descriptive metrics are in the two validation JSON files. Sparse tail bins and high FAR remain limitations.

## 23. Ensemble Baseline

P0 is the threshold-exceeding fraction of QC-valid c00/p01/p02/p03/p04 members, strictly on the same **67 cases / 87,167 cells** as the selected ML probability. Heavy Brier: P0 **.028660**, selected ML **.023595**. Very-Heavy Brier: P0 **.006769**, selected ML **.006202**. This full common set includes some calibration-fitting dates; it is a descriptive head-to-head on matched cells, not an independent calibration test. The larger 183-case ML population is reported separately.

## 24. Distribution Shift

On admitted paired cells, the 2024 above-2023-p99 fractions are **2.53% Q700**, **2.58% PWAT**, and **15.30%** for the PWAT×850-hPa-wind-speed area-mean proxy. The latter is a proxy, not vertically integrated vapor transport. The mean fraction of the 22 deterministic features outside their own 2023 p01–p99 range is **4.16%**. These are conditional-on-QC descriptive shifts, not causal attribution or a climate-trend claim.

## 25. Applicability Diagnostics

The versioned policy is **`NO_USER_FACING_APPLICABILITY_CUTOFF`**. No 2024 or future test case was filtered from the primary score for being out of support. A scalar “confidence” or operational warning threshold was not invented. Source QC and feature-support signals remain available for later validation.

## 26. Final Model Selection

The frozen primary objective was 2024 common-population RMSE, tie order M0→M4. **M1 Ridge MOS** won, despite M2 improving more cases and M2/M3 doing better on deterministic Heavy CSI. The same M2 configuration selected by 2023 inner validation served as the upstream probability feature and global M2 ladder comparator; its four 2024 candidate scores were recorded without altering the stacking feature after seeing 2024 targets. The model-selection freeze preserves all choices and their hashes.

## 27. Final Artifact Freeze

Authoritative models use native XGBoost JSON and safe explicit JSON for Ridge, logistic classifiers, pseudo-label configuration and calibrators; arrays use `.npy` with `allow_pickle=False`. Every output file is hashed in `FINAL_TEST_READY.json`. Models remain fit on **2023 only** (Option A); only declared 2024 calibration transforms were fit on the early calibration block. No 2024 target refit of base models occurred.

## 28. FINAL_TEST_READY

`experiments/recent_historical/phase4i_operational_model_development_v1/final_freeze/FINAL_TEST_READY.json` SHA-256 **`67170a350abb0663aedb2ea129d4eac3ce10ce9d77863af43b4f5c22700b2b48`**. It binds Phase 4G/4H hashes, both OOF artifacts, both completed matrices, all model/calibrator/threshold artifacts, metric definitions, common populations, applicability policy, the 232 eligible 2025 *forecast-only case IDs*, code hashes and the still-required explicit unseal authorization. Changing a frozen scientific rule or result requires versioning; do not mutate this file to make later results look favorable.

## 29. 2025 Holdout Audit

The Phase 4I data loader accepts paired 2023/2024 only and raises before constructing a 2025 paired-data path. Phase 4I did not read 2025 IMD, target arrays, event counts, forecasts for scoring, predictions or skill. The frozen Phase 4G split still declares `test_outcomes=SEALED`; `FINAL_TEST_READY` explicitly says authorization is **not granted**. This code-path audit is not a claim of machine-wide access control.

## 30. Compute Performance

CPU XGBoost only, nominal 12 worker threads within each single fit; no CUDA or Phase 4F concurrency change. The five OOF M2 fold records total about **75 seconds** on the local machine; OOF regime fitting about **0.2 seconds**; full deterministic ladder, FSS and applicability about **13.7 seconds**; both probability target paths about **8.3 seconds** combined, excluding repeated input integrity checks and documentation/testing. Peak process RAM was **not instrumented**, so no peak-RAM number is claimed. Matrices were reused from Phase 4G without GRIB re-decoding.

## 31. Scientific Limitations

The 2024 sample is source-QC-selected, with only 51/61/71 Day-1/2/3 cases; spatial cells are correlated; 2024 is a model-selection year; 2025 independent performance is unknown. IMD file timing lacks explicit accumulation bounds. Pseudo-label agreement is not independent meteorological accuracy. Extreme FSS loss and high probability FAR prohibit broad “better extremes” claims. The exact operational GEFS executable/physics build remains unverified despite structural source checks. The legacy `AGENTS.md` six-hour-target sentence is historical and conflicts with this separately frozen 24-hour corpus; no governance or threshold was altered here.

## 32. Reproducibility

`phase4i_operational_model_development_v1/run.py` exposes ordered stages `a,b,c,d,f,g,h,j`; all paths are isolated to that directory, and the script checks frozen source/protocol hashes before paired-data access. Per-fold train/heldout/embargo IDs, chosen candidates, model SHA-256, prediction SHA-256 and row counts are saved. The Phase 4I tests verify case isolation, safe serialization, 26-feature alignment, calibration separation, threshold rule, ensemble common-cell comparison, FSS bounds, final manifest completeness and the 2025 denial. The backend suite passed **146 tests** with one upstream Starlette/AnyIO deprecation warning; Python compilation passed. Read-only protected verification covered Phase 4A 145 listed files, Phase 4B 813, Phase 4C 13, Phase 4E 64,610 and Phase 4F 28,335/28,351/28,383 year files, plus the Phase 2B/2C locks, Phase 4D/4H pins and all three Phase 4G year manifests. No protected or frontend/API file was edited.

## 33. Decision Gate

**`FINAL_TEST_READY`**, subject to the explicit later unseal authorization required by Phase 4H. This decision means 2023 cross-fitting/training and 2024 validation/calibration/selection are frozen, with 2025 outcomes still sealed. It does **not** say the selected operational-era model beats Raw on extreme spatial skill, nor that the system is live or production-ready. The exact next separately authorized scientific task is a one-time 2025 final test under the frozen metric/population rules; do not start it within Phase 4I.
