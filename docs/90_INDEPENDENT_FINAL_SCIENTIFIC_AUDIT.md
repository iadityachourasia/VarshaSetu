# Phase 4K — Independent Final Scientific Audit

## 1. Executive Summary

**Decision: `AUDIT_PASSED_WITH_DOCUMENTATION_CORRECTIONS`.** Independent calculations from frozen arrays reproduce the reported 2019 retrospective and 2025 operational-era results. The scientific results are mixed, not invalid: the preselected 2025 M1 Ridge MOS improves overall RMSE against Raw GEFS, but Raw has better heavy and very-heavy spatial Fractions Skill Score (FSS). Stale present-tense holdout wording and incomplete experiment scoping require correction before public presentation. This audit changes no source science, models, APIs, frontend, or earlier documentation.

## 2. Audit Scope

This read-only review checks artifact hashes, holdout and selection lineage, common evaluation masks, independent metric calculations, and public claim wording. It creates only this report and new files under `experiments/recent_historical/phase4k_independent_final_audit_v1/`. The two GEFS lineages are **not pooled**. The audit recalculates metrics using its own NumPy/SciPy functions, not the Phase 4J metric helpers. Its executable source and machine-readable findings are in the [Phase 4K audit directory](../experiments/recent_historical/phase4k_independent_final_audit_v1/README.md).

## 3. Experiment A — 2017–2019

The retrospective experiment uses NOAA GEFSv12 **reforecast** and IMD rainfall, with 2017 training, 2018 validation, and a 2019 final evaluation. The frozen test cache has 255 cases and 331,755 paired grid cells. Independently loading the frozen native XGBoost model and feature cache gives Raw RMSE **19.7734726 mm**, M2 Global XGBoost RMSE **17.8486982 mm**, and **9.7341241%** relative reduction. This is a reforecast result, not an operational-GEFS result. The 2019 held-out evaluation has already happened; “untouched” describes its pre-evaluation state only.

## 4. Experiment B — 2023–2025

The operational-era historical experiment uses NOAA operational GEFS and IMD, with 2023 training/cross-fit, 2024 validation/calibration/model selection, and a **consumed** one-time 2025 final test. The final deterministic common population is 232 cases and 301,832 cells (Day 1: 75; Day 2: 75; Day 3: 82). The five-member ensemble comparison has 75 cases and 97,575 cells. These are selected source-eligible ranges, not a claim about all dates or live forecasting.

## 5. Holdout Governance

The pinned Phase 4I readiness record shows `SEALED` and no 2025 observation access/model inference by its governed code path. The Phase 4J authorization binds the readiness SHA-256; the three transition records document `SEALED → AUTHORIZED_TO_UNSEAL → UNSEALED_FOR_FINAL_EVALUATION → FINAL_TEST_COMPLETED`. No target arrays are present in the Phase 4G forecast-only 2025 deterministic feature tree. Readiness pins the development source/artifacts. These are strong repository-level controls, not proof that unrelated machine-wide observation access was impossible. **2025 is consumed and must never again be described as untouched or sealed.**

## 6. Model Selection Integrity

The pinned 2024 common deterministic validation population contains 183 cases and 238,083 cells. Its frozen RMSE values are M0 **17.1297**, M1 **16.7975**, M2 **16.8459**, M3 **17.4134**, M4 **17.2628** mm. M1 Ridge (alpha 0.1) was selected by the frozen primary RMSE rule before 2025 unsealing. Heavy/very-heavy models use 2024 isotonic calibration with frozen thresholds 0.10/0.05. The lower 2025 M2 RMSE is a secondary result; it does **not** replace preselected M1 as the primary final-test model.

## 7. 2025 Primary Verification

| Forecast | RMSE (mm) | MAE (mm) | Bias (mm) |
|---|---:|---:|---:|
| M0 Raw | 16.165725 | 7.653611 | −1.264967 |
| M1 preselected Ridge | 15.573562 | 7.580239 | −1.202315 |
| M2 Global XGBoost, secondary | 15.002232 | 7.398711 | −0.926603 |
| M3 hard regime, secondary | 15.460804 | 8.040451 | 0.165679 |
| M4 soft regime, secondary | 15.215325 | 7.968190 | 0.251335 |

Independent M1 minus Raw RMSE is **−0.592163 mm**, or **−3.663079%** of Raw. The frozen primary classification `SELECTED_MODEL_IMPROVED_RMSE` is supported. Identical 301,832 paired cells underlie all M0–M4 direct comparisons. M1 improves 166 cases, worsens 66, and ties none; the median per-case RMSE change is −0.387520 mm.

## 8. Lead-Specific Verification

| Lead | Cases | Raw RMSE (mm) | Selected M1 RMSE (mm) |
|---|---:|---:|---:|
| Day 1 / 24 h | 75 | 15.595093 | 15.350118 |
| Day 2 / 48 h | 75 | 16.015040 | 15.278971 |
| Day 3 / 72 h | 82 | 16.803049 | 16.036479 |

Independent case and lead calculations match the frozen final result. They are descriptive subgroups, not alternate model-selection populations.

## 9. Extreme Verification

The exact frozen 24-hour thresholds are heavy **≥64.5 mm** and very heavy **≥115.6 mm**. The 2025 common population contains 6,760 heavy event cells and 1,430 very-heavy event cells. At the heavy threshold, Raw POD/FAR/CSI/ETS are **0.05577/0.74983/0.04778/0.04369**; selected M1 yields **0.02086/0.67056/0.02001/0.01867**. At the very-heavy threshold, Raw yields **0.02168/0.81871/0.01975/0.01924**, and M1 yields **0.00979/0.39130/0.00973/0.00965**. M1 improves RMSE but loses CSI and ETS at both thresholds; its lower FAR is accompanied by many fewer event forecasts. Independent hit/miss/false-alarm counts reproduce frozen figures for all M0–M4; see `independent_metric_check.json`.

## 10. FSS Verification

Independent 49×49 two-dimensional neighborhood calculations use the frozen case masks, 50% minimum valid neighborhood fraction, zero padding beyond the domain, and matched cases with defined denominators for both compared forecasts. Raw exceeds M1 at every scale:

| Threshold | Matched cases | 1×1 Raw/M1 | 3×3 Raw/M1 | 5×5 Raw/M1 | 9×9 Raw/M1 |
|---|---:|---:|---:|---:|---:|
| Heavy | 214 | .0912/.0392 | .1561/.0667 | .1949/.0836 | .2523/.1063 |
| Very heavy | 121 | .0390/.0193 | .0860/.0379 | .1237/.0537 | .1713/.0711 |

Thus the frozen spatial classification `RAW_BETTER` is supported. This does not negate continuous-RMSE improvement.

## 11. Probability Verification

The frozen classifiers, isotonic calibrators, and decision thresholds were selected on 2023/2024 only. Independently recomputed 2025 heavy Brier is **0.01983131**, BSS **0.094835** against the frozen 2023-prevalence reference **0.01864335**; PR-AUC is **0.217360**, ROC-AUC **0.894552**. Very-heavy Brier is **0.00459023**, BSS **0.026523** against reference **0.00473866**; PR-AUC is **0.079514**, ROC-AUC **0.903440**. The audit separately recalculates the PR-AUC and ROC-AUC from rank/precision-recall definitions, as well as Brier/BSS and categorical thresholds. At threshold 0.10, heavy POD/FAR/CSI/ETS are **.27796/.69576/.16994/.15942**. At 0.05, very-heavy values are **.12378/.85492/.07157/.06940**. Reliability is limited, especially sparse upper bins and very-heavy false alarms; “calibrated” describes the fitted procedure, not a guarantee of 2025 perfect reliability. Heavy PR-AUC fell from **0.314891** on 2024 validation to **0.217360** on 2025 test; very-heavy PR-AUC fell from **0.126526** to **0.079514**, despite positive final-test BSS. The 2024 and 2025 raw/selected RMSE pairs were **17.1297/16.7975** and **16.1657/15.5736** mm, respectively; this comparison is descriptive and did not trigger reselection.

## 12. Ensemble Baseline Verification

The independent calculation maps the 75 all-five-member cases back to the same 97,575 observed cells and constructs threshold fractions from c00/p01/p02/p03/p04. Heavy Brier is **0.02288660** for the ensemble fraction versus **0.02084972** for frozen ML on those **same** cells. Very-heavy Brier is **0.00502342** versus **0.00493453**. This is a matched-subset comparison and must not be conflated with the full 232-case probability population.

## 13. Regime Verification

The frozen forecast-only classifier maps the paired 2025 cases to 100 Active, 71 Break/Weak, and 61 Low/Depression Influenced pseudo-regimes. Overall RMSE: M2 **15.002232**, M3 hard **15.460804**, M4 soft **15.215325** mm. M4 beats M3 on RMSE, but neither beats non-regime Global M2. These are classifier/pseudo-label outputs, not independently verified meteorological regime truth or evidence that regime awareness improved overall final-test RMSE.

## 14. Applicability Verification

The frozen policy is `NO_USER_FACING_APPLICABILITY_CUTOFF`; no shifted 2025 case is removed. Independent comparison of frozen 2025 predictor rows with 2023 feature-wise p01–p99 bounds yields **0.0251255** of the 22-feature values outside those bounds, matching the result. This is a descriptive support diagnostic, not a generalization guarantee or climate-trend inference.

## 15. Independent Metric Recalculation

The audit computes RMSE, MAE, bias, POD, FAR, CSI, ETS, Brier, BSS, rank-based ROC-AUC, average-precision PR-AUC, ensemble threshold fractions, applicability fraction, and 2-D FSS from frozen predictions and observations without calling the original scoring module. M0–M4 arrays have the same 2025 paired length. Maximum absolute continuous/event/Brier drift is **7.11×10⁻¹⁵**; rank metrics match at floating-point precision, and FSS matches within 10⁻⁹. The 2019 native XGBoost prediction reproduces the frozen result within floating-point rounding. The independent code is [audit.py](../experiments/recent_historical/phase4k_independent_final_audit_v1/audit.py).

## 16. Supported Claims

- 2019 reforecast M2 reduces RMSE versus Raw by 9.73% on its fixed paired population.
- Preselected 2025 operational-era M1 reduces RMSE versus Raw by 3.66% on its fixed selected-source population.
- The 2025 heavy and very-heavy probability models have positive BSS versus the frozen 2023 reference, with important categorical/reliability limitations.
- Raw outperforms selected M1 on both extreme FSS thresholds at all four scales.
- Secondary M2 has the lowest 2025 overall RMSE among M0–M4, but cannot replace M1 as the preselected headline.

## 17. Claims Requiring Qualification

“AI improves rainfall forecasts” must name the model, experiment, metric and population. “Operational GEFS correction” must mean historical selected-range evaluation, not live production. “Extreme skill” must separate Brier from CSI/FSS. “Calibrated probabilities” must acknowledge 2025 reliability/FAR limitations. “Regime-aware” must identify forecast-only pseudo-regimes and the failure to beat global M2 overall.

## 18. Unsupported Claims

The evidence does not support live or production readiness, universal improvement across cases/metrics, independently verified regime truth, a still-sealed 2025 holdout, or any pooled 2019–2025 skill percentage. Scientific performance itself is not an audit failure; overstating it would be a presentation failure.

## 19. Documentation Discrepancies

The [discrepancy ledger](../experiments/recent_historical/phase4k_independent_final_audit_v1/documentation_discrepancy_ledger.json) records exact file/line locations and future corrections. Material examples are legacy “current 6-hour target” language in `AGENTS.md` and `docs/21`, root README's globally worded blocked state, obsolete fixed packing-bound language in `docs/81`, the pre-unseal instruction in `docs/00_INDEX.md`, and present-tense “untouched” wording in demo documents. Earlier sealed-status documents remain valid historical snapshots if dated and contextualized. No existing documentation was changed during this read-only audit. The index was deliberately left unchanged because the prompt forbids editing existing claims; it should be updated only in a separate authorized correction task.

## 20. Frontend Claim Audit

The [frontend claim audit](../experiments/recent_historical/phase4k_independent_final_audit_v1/frontend_claim_audit.json) finds that `frontend-v2` serves frozen 2019 historical Phase 2B/2C APIs, not Phase 4J 2025 cases. Its 9.73% value is scientifically correct when scoped to the 2019 retrospective study. Present-tense “untouched 2019” and an unqualified “PRIMARY DETERMINISTIC RESULT” could mislead after 2025, whose primary is preselected M1. Historical/nonoperational notices and pseudo-regime caveats are appropriate. No UI code was edited.

## 21. Demo Narrative Recommendations

Use the existing frontend only for authentic 2019 historical maps and district products. Separately show a sourced 2025 report/table of the consumed selected-source benchmark and mixed skill: M1's 3.66% RMSE reduction, Raw's better FSS, probability Brier gains with high FAR, and M2's secondary-best RMSE without re-selection. State the differing NOAA lineages. Do not fabricate 2025 map/district UI from the 2019 API. The [story recommendations](../experiments/recent_historical/phase4k_independent_final_audit_v1/demo_story_recommendations.json) provide a safe sequence.

## 22. Scientific Limitations

The 2025 population is selected and QC-eligible, not every scheduled forecast. IMD annual data use daily labels without explicit accumulation-bound metadata; do not strengthen temporal alignment claims. The operational-era study covers three years and does not establish climate robustness or live operational performance. The independent audit does not rehash the entire large Phase 1F Zarr tree; it checks recorded lineage and pinned cache/model hashes instead. Regime outputs are forecast-only pseudo-regimes. Extreme-event skill is mixed and very-heavy probability reliability remains uncertain.

## 23. Artifact Integrity

The audit verifies the expected Phase 4J result SHA-256 `04a7fc2a434d24449365e2cb9978cbc8584f5cc87ea4f132cfaf6e7fc7a4abca`, Phase 4I readiness `67170a350abb0663aedb2ea129d4eac3ce10ce9d77863af43b4f5c22700b2b48`, Phase 4H protocol `cfe273d765ae943ea0dc394439436af09391a4c25e3684629732394801582770`, and Phase 4G feature freeze `f1520a32aadef460249ba26a39c106f9593fcd3407c23d2967ddc90d889ed67b`. It checks the readiness-pinned development files, frozen Phase 4J prediction/metric files and inventory, 2019 model/cache files, calibrator and threshold metadata. New audit files have a separate hash-addressed [artifact manifest](../experiments/recent_historical/phase4k_independent_final_audit_v1/artifact_manifest.json). No protected artifact was rewritten.

## 24. Final Audit Decision

`AUDIT_PASSED_WITH_DOCUMENTATION_CORRECTIONS` — independently recalculated frozen evidence supports the reported scientific results and holdout lineage. Before external presentation, make a separately authorized, evidence-preserving correction pass over the ledger's stale documentation/UI copy. Do not retrain, recalibrate, change thresholds, reselect on 2025, pool the experiments, or claim operational readiness.
