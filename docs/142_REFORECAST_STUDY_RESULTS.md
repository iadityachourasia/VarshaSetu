# Phase 13: the reforecast study, regime detection and heavy-rain correction on sealed years

Date: 2026-10-03. This is the attempt to close the two partial official requirements (PS-R03 regime classification, PS-R05 improvement over raw) with new, independent data. The plan, the downloads, the frozen protocol, the sealed test and the result are all recorded; the outcome is mixed and is stated as it came out. **PS-R03 is now implemented** (every regime state is detected from the forecast with verdict "validated and useful" on sealed years, against objective labels). **PS-R05 failed its pre-registered rule in round 1** (heavy and very-heavy rain improved with intervals excluding zero, but the frozen mean-error guardrail failed) **and passed in a pre-registered confirmatory round 2 on 2017-2019**, so it is now implemented, with the caveats below. With this, all 14 official requirement IDs are implemented.

## Data acquired (stated before it was fetched, measured size)

| Data | Source | Scope | Size |
|---|---|---|---|
| GEFSv12 reforecast control member (c00), 00 UTC, rainfall to +75 h and six atmospheric fields at +24, +48, +72 h | public NOAA bucket `noaa-gefs-retrospective`, byte ranges only | June to September, 2000-2016 (2,074 initializations, all complete, none unavailable) | about 40 GB (measured about 19.5 MB per initialization day; the estimate given when you approved was 20-25 GB) |
| ERA5 geopotential, 6-hourly, 13 levels, 1.5 degree | public WeatherBench2 store `gs://weatherbench2/datasets/era5`, no credentials | 1 June to 3 October, 2000-2022 (the store ends on 10 January 2023, so 2023 does not exist there) | about 11 GB (1,449 chunks) |
| GEFSv12 reforecast control member, same layout, round 2 | same bucket | June to September, 2017-2019 (366 initializations) | about 6.6 GB measured |
| IMD RF25 rainfall 1981-2016 | already on disk since the regime-validation work | observation reference | not re-downloaded |

Every reforecast message is stored with a receipt (URL, byte range, SHA-256). ERA5 is a **reanalysis**: it was used only to label past days and never as a forecast input (AGENTS.md section 3.5).

## Design (frozen before any outcome was read for the sealed years)

- **Years.** Train 2000-2011, validate 2012-2013, **sealed test 2014-2016**: no earlier model, selection or experiment used these years. The reforecast lineage is never pooled with the operational years.
- **Protocol** `reforecast_study_protocol_v1.json` (sha256 `506c71b429e5c6d9ec4bbcbed09990556ed2e61ecbe9df16461a1cf228d177a7`) pins the hash of every forecast-side file, the rule modules, the grid, the selection rule, the decision tiers, the label definitions, the verdict rule and the mapping from outcomes to coverage statuses. Two disclosed amendments were written before the corresponding step and before any sealed value was read: amendment 1 (the validation years hold too few active and break cases, so those two tasks select C and the threshold by leave-one-year-out over the training years) and amendment 2 (an exceedance-classifier family added after the validation results showed the regression models under-forecast very-heavy rain).
- **R05 models.** Raw; an XGBoost correction on the 22 frozen features (B0) and with eight static geography columns (B1) over a 24-configuration grid (squared error or Tweedie, event-weight cap none, 4 or 8, depth, rounds), selected on the validation years only; regime routing (hard and soft) with three experts; and, from amendment 2, exceedance classifiers P(rain at or above 64.5 or 115.6 mm) with a probability threshold fixed on the validation years.
- **R03 tasks.** Five detection tasks, each a standardised logistic model on forecast-only features (the 12 regime features, the forecast western-disturbance trough indicator, the coastal forcing index, lead and day of year) against a climatology baseline: active and break (IMD core-zone rainfall spells, 1981-2011 climatology), low/depression (ERA5 850 hPa geostrophic vorticity box maximum, 15-25 N, 70-95 E), western disturbance (ERA5 500 hPa, 20-36.5 N, 60-80 E), coastal/orographic rain day (IMD Ghats-coast zone mean). The vorticity labels use the training-years 85th percentile and two consecutive days. The low/depression box was moved from 27 N to 25 N after seeing, on one training year, that the 850 hPa level below the Himalayan foothills gave spurious vorticity; this was done before the freeze.
- **Verdict rule (R03).** Validated needs an AUC lower bound above 0.5 and a positive lower bound of the AUC gain over the climatology baseline; useful also needs an AUC of at least 0.70; a task needs at least 30 positive and 30 negative sealed cases.
- **Opening the sealed years.** A signed unseal record (sha256 `280a9720ae88bd239ca8ccfe6cf2472c4a70b1796e463a94a2168955752f9fd9`) was written after every selection and model was frozen and says so only because no sealed observation, label or reanalysis value existed at that time. The scoring then ran once (an earlier attempt crashed on a code error before writing any output).
- **Compute.** Process-based parallelism throughout (downloads with up to 62 threads in three processes, forecast-side decoding in 12 to 20 processes, grid training in parallel processes with 12 threads each). XGBoost ran on the CPU: the earlier GPU equivalence check was not met, and models selected on one backend and refit on another would change what was frozen.

## Result 1 (R03): all five regime states are detected from the forecast on sealed years

| Task | Sealed cases (positive / negative) | AUC [95 %] | Climatology baseline AUC | Gain [95 %] | Balanced accuracy (chance 0.5) | Verdict |
|---|---|---|---|---|---|---|
| Active monsoon | 418 (68 / 350) | 0.932 [0.899, 0.960] | 0.675 | 0.257 [0.184, 0.332] | 0.816 | validated and useful |
| Break monsoon | 418 (59 / 359) | 0.870 [0.806, 0.928] | 0.424 | 0.446 [0.346, 0.543] | 0.755 | validated and useful |
| Low / depression | 778 (117 / 661) | 0.802 [0.749, 0.851] | 0.401 | 0.401 [0.332, 0.466] | 0.723 | validated and useful |
| Western disturbance | 778 (113 / 665) | 0.721 [0.653, 0.783] | 0.551 | 0.170 [0.085, 0.249] | 0.658 | validated and useful |
| Coastal / orographic rain day | 778 (111 / 667) | 0.976 [0.965, 0.985] | 0.781 | 0.195 [0.151, 0.241] | 0.942 | validated and useful |

How to read it: the detectors discriminate well above both chance and a seasonality-only baseline. The western-disturbance result is the weakest and the least informative: the label is a reanalysis trough and the predictor is a forecast trough, so it largely verifies the forecast height field. The labels are objective rules, not expert analyses, and several are relative by construction (a fixed share of days is positive). Precision is modest for the rarer states (for example 0.25 for western disturbances), which is expected at these prevalences.

## Result 2 (R05): clear improvements, one failed guardrail

Sealed years 2014-2016: 778 cases on 366 initialization dates, 1,012,178 paired cells, 15,756 observed heavy and 3,542 observed very-heavy cell-days.

| Model | RMSE (mm per 24 h) | Mean error (mm) | Heavy CSI / frequency bias | Very-heavy CSI / frequency bias |
|---|---|---|---|---|
| Raw (M0) | 14.32 | +0.46 | 0.085 / 0.35 | 0.050 / 0.25 |
| B0 (22 features) | 12.89 | +1.81 | 0.207 / 0.57 | 0.053 / 0.12 |
| B1 (+ static geography) | 12.75 | +1.76 | 0.224 / 0.62 | 0.055 / 0.15 |
| R_hard (regime routing) | 13.07 | +1.76 | 0.190 / 0.54 | 0.052 / 0.15 |
| R_soft (regime mixture) | 13.02 | +1.77 | 0.191 / 0.53 | 0.050 / 0.13 |
| Exceedance classifier B0 (probability at or above its threshold) | | | 0.236 / 1.66 | 0.141 / 1.58 |
| Exceedance classifier B1 | | | 0.253 / 1.47 | 0.153 / 1.48 |

Paired whole-date bootstrap differences against Raw (95 % for RMSE, 97.5 % for the CSI differences):

| Candidate | RMSE difference | Heavy CSI difference | Very-heavy CSI difference |
|---|---|---|---|
| B1 regression | -1.57 mm [-1.82, -1.33] | +0.139 [0.104, 0.172] | +0.004 [-0.037, 0.045] |
| B1 exceedance classifiers | (the regression arm) | +0.168 [0.142, 0.193] | +0.103 [0.071, 0.136] |

- **RMSE, heavy-rain CSI and very-heavy CSI each improve on Raw with an interval excluding zero**, the very-heavy gain through the exceedance classifiers (regression alone does not detect very-heavy cells: its frequency bias is about 0.15). The same holds for the B0 arm (heavy +0.151, very heavy +0.091 for the classifiers).
- **The frozen bias guardrail failed.** The tier rule requires the mean error to stay within 1.5 mm. The regression arms over-forecast by about 1.8 mm on the sealed years (+1.73, +1.32 and +2.24 mm in 2014, 2015 and 2016) against +0.2 to +0.7 mm for Raw, and the validation years (+0.9 to +1.0 mm) had already hinted at a wet drift. The frozen tier is therefore **none**, although the three improvements are each shown. The guardrail was not relaxed after seeing the result.
- **Regime-awareness does not add value.** R_soft and R_hard are worse than B0 on heavy-rain CSI (differences -0.017 with intervals below zero) and slightly worse on RMSE (+0.13 and +0.18 mm), so the finding of the operational years (regime-aware correction does not beat a global model) holds on independent years too. The correction is nonetheless real: it comes from the event-weighted learning, not from the regimes.
- **Lead.** RMSE improves at every lead for B1 (Day 1 14.10 to 12.37, Day 2 14.24 to 12.61, Day 3 14.76 to 13.50 mm).


## Round 2 (R05): a confirmatory test after the failed guardrail

Round 1 met every improvement but failed the frozen mean-error guardrail, and 2014-2016 cannot be reused. Under **amendment 3**, written before the 2017-2019 forecast-side corpus was built and before any 2017-2019 observation was paired for this study, a second round tested the **frozen B1 bundle with no refit** on the reforecast control member of 2017-2019 (a further 7 GB, measured: three seasons of about 2.2 GB). One parameter was added: the regression output is reduced by delta, the pooled mean error of the same model on 2014-2016 (1.76 mm, read from the round-1 evidence file, not tuned on these years), and clipped at zero; the exceedance classifiers and their validation-fixed probability thresholds are unchanged. A signed confirmation record (sha256 `1d22c6d8349261471d2485f25b7d4462557c91e849c090c46f02056877d3ffbd`) was written first. The years were used by earlier Track A experiments of this project, so the test is labelled **CONFIRMATORY TEST 2017-2019** and never called an untouched holdout; no model, selection, threshold or rule of this study was ever fitted or chosen with them.

764 cases on 366 initialization dates, 993,964 paired cells, 20,812 observed heavy and 5,423 very-heavy cell-days. The forecast-side corpus keeps 258, 251 and 255 control leads in 2017, 2018 and 2019, matching the independently built Track A control counts for 2017 and 2018.

| Forecast | RMSE (mm per 24 h) | Mean error (mm) | Heavy CSI / frequency bias | Very-heavy CSI / frequency bias |
|---|---|---|---|---|
| Raw | 16.66 | +0.34 | 0.096 / 0.43 | 0.029 / 0.22 |
| B1 regression before the correction | 15.10 | +2.45 | (not used for the verdict) | |
| B1 bundle: corrected regression + exceedance classifiers | 14.90 | +0.91 | 0.262 / 1.79 | 0.169 / 1.87 |

Against Raw (95 % for RMSE, 97.5 % for the CSI differences): RMSE -1.76 mm [-2.04, -1.47]; heavy CSI +0.165 [0.143, 0.187]; very-heavy CSI +0.141 [0.106, 0.176]. All three improvements hold, the mean error after the correction (+0.91 mm) is inside the guardrail, and the frequency biases are inside their limits, so the **frozen tier is FULL**.

What this does and does not mean: the wet drift of the regression is real and grows (+1.8, +2.0 and +3.5 mm per year before the correction in 2017, 2018 and 2019); the one-parameter correction brings the pooled error inside the guardrail, but the 2019 year alone remains above it (+1.9 mm), so the correction is not a general cure for the drift. The pass depends on a shift taken from round 1. The very-heavy gain comes from the exceedance classifiers (yes/no forecasts at a fixed probability threshold, not shown to be calibrated).

## What this changes in the coverage

- `REGIME-CLASSIFIER`, `REGIME-WESTERN-DISTURBANCE` and `REGIME-COASTAL-OROGRAPHIC` move to IMPLEMENTED under the pre-registered mapping (each verdict validated and useful), with their limitations stated: objective labels, relative construction, the western-disturbance task largely verifying the forecast height, no specialist rainfall model for the coastal zone, three held-out seasons only. **PS-R03 is now implemented.**
- `IMPROVEMENT-VS-RAW` moves to IMPLEMENTED through the pre-registered round-2 verdict (tier FULL on 2017-2019), with the limitations stated: the first test failed the bias guardrail, the pass depends on a mean-error shift read from it, the years are confirmatory and not untouched, the very-heavy gain comes from exceedance classifiers, regime-awareness adds nothing, and the reforecast lineage is not the operational lineage. **PS-R05 is now implemented; all 14 official requirement IDs are implemented.**
- `REGIME-INDEPENDENT-VALIDATION` stays partial: the new labels are objective rules, not expert analyses.

## What is not established

- Skill on operational forecasts of other years or on a new forecast cycle (the study uses the reforecast control member, a different model version).
- That the regime labels are meteorological truth (they are objective rules); expert-labelled regimes remain unavailable.
- Calibrated probabilities: the exceedance classifiers were evaluated as yes/no forecasts at a fixed threshold, with AUC and Brier score reported, not with a reliability analysis.
- Any benefit of regime-awareness for rainfall correction.
- The cause of the wet drift, and that a constant shift removes it in general (2019 alone stays above the guardrail after the shift).
- Skill of the corrected rainfall field itself for very-heavy cells (the very-heavy gain is from the exceedance classifiers).

## Where it lives

Protocol, freezes, unseal record and results under `backend/app/evidence_data/phase15/`; code in `backend/app/ml/{reforecast_study,regime_tasks,regime_labels_reanalysis}.py` and `scripts/{acquire_reforecast_control,acquire_era5_geopotential,build_reforecast_*,build_regime_task_data,train_reforecast_*,train_regime_tasks,write_reforecast_unseal_record,score_reforecast_study}.py`; API `/api/science/evidence/reforecast/{overview,r05,r03}`; panels on the Verification Lab and Regime Intelligence. Tests: `backend/tests/test_reforecast_study.py`, `test_regime_tasks.py`, `test_regime_labels_reanalysis.py`, `test_reforecast_evidence.py` (which re-derives every decision and verdict from the stored intervals and, locally, recomputes the Raw metrics independently), `frontend-v2/src/lib/api/reforecast.test.ts`, `frontend-v2/tests/e2e/reforecast-study.spec.ts`.
