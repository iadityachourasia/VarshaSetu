# Phase 4B — Seven-Day External Operational Evaluation (2024)

**Later packing-precision interpretation (Phase 4C):** references below to
“the 0.055-mm decoded packing bound” describe this original frozen seven-day
evaluation, not a globally fixed canonical tolerance. Packing-aware subtraction
tolerance is derived from each decoded source-message packing quantum; later
source messages yielded bounds including 0.01, 0.055, and 0.1 mm. See
`82_OPERATIONAL_REFORECAST_COMPARABILITY_AUDIT.md`. The original Phase 4B
results and QC decisions remain historical evidence and are not recomputed here.

Status: **LIMITED GO for an explicitly caveated historical research demonstration; NO GO for an operational-transfer skill claim or frontend integration.** Completed against the predeclared 2024-07-18–24 00 UTC window. The original frozen 2019 9.73% RMSE-reduction result is neither changed nor pooled with this operational-GEFS sample.

## 1. Executive summary

All seven NOAA operational cycles and all required message indexes existed. Actual unchanged canonical reconstruction accepted four of seven c00 Day-1 rainfall products; all seven six-variable atmosphere sets passed. The other three c00 products exceeded the original 0.055-mm Method-A packing bound and were quarantined. None of the seven dates had all five c00/p01–p04 rainfall members accepted, so the original five-member P0 baseline is **not available**. Four dates (5,204 paired IMD-valid cells) were inferred with frozen M0–M4 and frozen heavy/very-heavy classifiers. Across those four, Raw RMSE was **26.6937 mm** and frozen M2 Global XGBoost RMSE was **28.7093 mm**: M2 worsened pooled RMSE by **2.0156 mm (7.55%)**, improving one date and worsening three. This is a small external sample, not a new model-selection or seasonal result.

## 2. Scientific objective

The experiment asks whether official historical *operational* GEFS can satisfy the previously frozen source/QC/feature contracts and what descriptive out-of-sample behavior occurs without training or recalibration. Availability, c00 QC, six-predictor QC, five-member completeness, paired Raw/M2 skill, and frozen-training-range exceedances are independent questions.

## 3. Predeclared evaluation window

The fixed seven 00 UTC initializations are 2024-07-18, 19, 20, 21, 22, 23, and 24. Product: Day 1, +3→+27 h, paired to IMD dates July 19–25 respectively. Phase 4A operational performance examined only July 15 (QC reject) and July 16 (accepted pilot); no July 18–24 operational performance artifact existed before predeclaration. No date was substituted or selected using model performance.

## 4. Protocol hash

The immutable-before-window-acquisition [protocol](../experiments/recent_historical/phase4b_20240718_20240724_v1/protocol.json) SHA-256 is `5e54d38798ef1be96160cdc330602c9feb2e428d3d713d397b44db14d7c3a634`. Its sidecar was written before requesting any July 18–24 NOAA index. It fixes source families, members, accumulation leads, thresholds, geometry, QC, eligibility, models, masks, and metric rules. The entire experiment is separate from the frozen 2017–2019 corpus.

## 5. Operational GEFS source information

[NOAA's GEFS Open Data registry](https://registry.opendata.aws/noaa-gefs/) identifies the public `noaa-gefs-pds` bucket; the [NCO inventory](https://www.nco.ncep.noaa.gov/pmb/products/gens/) documents `pgrb2sp25` 0.25° selected products and `pgrb2ap5`/`pgrb2bp5` 0.5° atmosphere families. This experiment used the actual historical `gefs.YYYYMMDD/00/atmos/` objects, not the 2000–2019 reforecast archive. Each `.idx` line, exact HTTP 206 `Content-Range`, original GRIB message, SHA-256, decoded init/member/step/field/level/unit/grid, and request receipt are saved. No full lead file or season was downloaded. NOAA's generic registry member-count description is not used to infer per-cycle five-member completeness; actual c00/p01–p04 messages were decoded.

## 6. IMD observation provenance

The existing official 2024 RF25 0.25° annual NetCDF from [IMD Pune](https://www.imdpune.gov.in/cmpg/Griddata/Rainfall_25_NetCDF.html) was reused without redownload: 25,501,532 bytes, SHA-256 `1ef02aeba5694dbb57a6cca23a3c2cc11740affb185137c1eacbeab59893228a`. All seven matched observation dates existed; 1,301 of 2,401 target cells were valid on each. The pairing follows the preexisting 03:00–03:00 UTC / 08:30–08:30 IST rainfall convention. The annual file's `TIME` is date-labeled and has **no explicit accumulation bounds**; this timing limitation persists. IMD was not opened by Phase 4B's inference function and was read only in verification.

## 7. Seven-day source inventory

The complete source matrix is `source_inventory.json`: seven rows × 36 selected message identities = 252 selected fields, from 224 distinct small `.idx` objects (some atmosphere fields share an object). **Every selected index field was present and uniquely bounded**. The matrix existed before range acquisition. It is an index-availability statement only, not a rainfall-QC result. Requested range bytes were estimated from offsets at 73,300,764 (plus 836,166 index bytes); 107 GB of NVMe space remained available locally.

| Initialization | c00 indexes | Six atmosphere indexes | p01–p04 indexes | Actual c00 QC | Actual 5-member QC |
|---|---|---|---|---|---|
| Jul 18 00Z | complete | complete | complete | pass | fail (p03,p04) |
| Jul 19 00Z | complete | complete | complete | fail | fail |
| Jul 20 00Z | complete | complete | complete | pass | fail (p01,p02,p03) |
| Jul 21 00Z | complete | complete | complete | fail | fail |
| Jul 22 00Z | complete | complete | complete | pass | fail (p04) |
| Jul 23 00Z | complete | complete | complete | pass | fail (p01,p04) |
| Jul 24 00Z | complete | complete | complete | fail | fail |

## 8. Complete case-admission ledger

The machine-readable `seven_day_ledger.json` retains exactly seven rows and independent eligibility flags. The common paired mask has 1,301 cells for each admitted date. Rejected dates have zero *evaluated* cells, not zero observed rainfall.

| Init 00Z | IMD date | Outcome | c00 rain | Atmosphere | Deterministic/probability | Five-member P0 | Paired cells |
|---|---|---|---|---|---|---|---:|
| Jul 18 | Jul 19 | ADMITTED | pass | pass | yes | no | 1,301 |
| Jul 19 | Jul 20 | RAINFALL_QC_FAILED | fail | pass | no | no | 0 |
| Jul 20 | Jul 21 | ADMITTED | pass | pass | yes | no | 1,301 |
| Jul 21 | Jul 22 | RAINFALL_QC_FAILED | fail | pass | no | no | 0 |
| Jul 22 | Jul 23 | ADMITTED | pass | pass | yes | no | 1,301 |
| Jul 23 | Jul 24 | ADMITTED | pass | pass | yes | no | 1,301 |
| Jul 24 | Jul 25 | RAINFALL_QC_FAILED | fail | pass | no | no | 0 |

## 9. Rainfall reconstruction and QC

All 35 c00/p01–p04 products were reconstructed independently from actual 0–3, 0–6, 6–12, 12–18, 18–24, and 24–27 h GRIB steps using the unchanged `reconstruct_minimal_accumulation_window`: `(0–6) − (0–3) + (6–12) + (12–18) + (18–24) + (24–27)`. Each has one Method-A subtraction. The 0.055-mm decoded packing bound was not loosened. **21/35** member-products passed; **14/35** failed because one or more negative intermediate cells were below the allowed bound. The cached-source supplement `source_audit.json` gives each member's exact negative-cell/violation/minimum counts: 1,887 negative intermediate cells and 27 bound violations across all 35 members. Rejected products have no final rainfall field, so their final-negative-cell count is `null`, not zero. Accepted fields have zero final negative cells. c00 failures: Jul 19, 132 intermediate negatives/1 violation/min −0.06 mm; Jul 21, 143/4/min −0.07; Jul 24, 18/1/min −0.06. Jul 20 c00 had 101 within-bound negatives normalized by the frozen method and was admitted.

## 10. Atmospheric predictor availability

All seven dates supplied actual decoded and QC-passing U850, V850, Q700, Z500, MSLP, PWAT at +24 h on the established 51×81, 0.5° context grid. GRIB identities, units and forecast initialization were validated by the existing NOAA adapter. Context bilinear interpolation to the 49×49 0.25° target **aligns grids; it does not create finer meteorological source resolution**. No valid-time observations enter predictors.

## 11. Ensemble completeness

The seven dates had all five members in indexes but **0/7** had all five actual reconstructed member-products pass unchanged QC. Consequently P0 five-member threshold fractions and P0-vs-classifier scores are **unavailable**, not imputed from a subset. The independent c00 path remains eligible on four dates.

## 12. Frozen-model inference

For the four eligible cases, the code verified the Phase 2A classifier hash, Phase 2B freeze/model hashes, Phase 2C freeze/model/calibrator hashes, exact 22- and 26-column orders, finite input arrays, and `allow_pickle=False` cached matrices. It used the existing atmospheric diagnostic extraction/bilinear interpolation and CPU XGBoost models. No fit, early stopping, recalibration, target observation, or new predictor was used during inference. M0 Raw, M1 safe Ridge, M2 frozen Global XGBoost, and the same three frozen experts for M3 hard argmax/M4 probability blend were run. The selected deterministic identity remains M2 **for the original prototype**, irrespective of this external result.

## 13. Per-case deterministic metrics

Every comparison below uses the same 1,301 IMD-valid cells within that date. All numbers are mm. Exact MAE/bias, threshold counts, and M1/M3/M4 metrics are in each `cases/YYYYMMDD/evaluation.json`.

| Init 00Z | Raw RMSE | M2 RMSE | Raw MAE | M2 MAE | Raw bias | M2 bias | Observed heavy / very-heavy cells |
|---|---:|---:|---:|---:|---:|---:|---:|
| Jul 18 | 36.5685 | 36.2000 | 21.3230 | 18.0625 | +0.1182 | −8.0683 | 152 / 70 |
| Jul 20 | 21.8410 | 24.7494 | 13.0047 | 13.6527 | −1.4837 | −6.8841 | 114 / 17 |
| Jul 22 | 23.5335 | 28.7545 | 9.9830 | 11.9983 | −5.0060 | −10.0306 | 100 / 42 |
| Jul 23 | 21.9567 | 23.3902 | 11.7417 | 11.3596 | −3.9160 | −6.4999 | 103 / 23 |

## 14. Aggregate descriptive metrics

On **four forecast dates / 5,204 spatial cells**, pooled Raw RMSE/MAE/bias = **26.6937 / 14.0131 / −2.5719 mm**; M2 = **28.7093 / 13.7683 / −7.8707 mm**. Thus the correction worsened RMSE, marginally reduced MAE (0.2448 mm), and made negative bias materially larger. Date-level M2 RMSE: 1 improved, 3 worsened, 0 ties. These are descriptive pooled-cell summaries; cells are correlated and are **not 5,204 independent forecast events**. No significance interval or seasonal transfer claim is made.

## 15. Regime-conditioned model comparisons

Pooled RMSE on the *identical four-date mask*: M0 Raw **26.6937**, M1 Ridge **27.6365**, M2 Global **28.7093**, M3 hard **27.6344**, M4 soft **27.6719 mm**. In this sample M3/M4 outperform M2 on RMSE but not Raw; no model-selection decision is changed. The frozen forecast-only classifier assigned the Low/Depression Influenced pseudo-label argmax on all four dates (probability 0.934–≈1), so this week gives little regime diversity. These probabilities reproduce the Phase 2A pseudo-label methodology; they are not verified meteorological regime truth.

## 16. Probability-model results

Frozen thresholds/calibrators remained heavy ≥64.5 mm/24 h, XGBoost+sigmoid, decision p≥0.30; very-heavy ≥115.6 mm/24 h, logistic+isotonic, decision p≥0.05. On the four-date common mask: heavy 469 observed event cells, Brier **0.068399**, BSS **0.220719** versus *frozen 2017 climatology*, PR-AUC **0.451102**, ROC-AUC **0.899681**; p-threshold POD/FAR/CSI/ETS **0.2836/0.4722/0.2262/0.1951**. Very-heavy 152 events, Brier **0.028206**, BSS **0.029529**, PR-AUC **0.124035**, ROC-AUC **0.879386**; POD/FAR/CSI/ETS **0.1842/0.8634/0.0851/0.0681**. Reliability-bin counts and case scores are in `aggregate_summary.json` and each case evaluation. The week has much higher event prevalence than the frozen 2017 climatology; BSS is not evidence of calibration transfer, and very-heavy FAR remains high. No ensemble P0 comparison is possible.

## 17. FSS results

The original 2-D, masked, boundary-aware FSS and pooled numerator/denominator method were applied on the same four dates. Each threshold/scale has four defined cases. Raw versus M2 pooled FSS:

| Threshold | 1×1 | 3×3 | 5×5 | 9×9 |
|---|---|---|---|---|
| Heavy Raw | 0.1284 | 0.1963 | 0.2097 | 0.2392 |
| Heavy M2 | 0.1040 | 0.1431 | 0.1623 | 0.1696 |
| Very-heavy Raw | 0 | 0 | 0 | 0 |
| Very-heavy M2 | 0 | 0 | 0 | 0 |

Very-heavy FSS=0 is **defined** here because IMD events exist but neither deterministic field forecast a very-heavy event. FSS uses the genuine 49×49 field, ≥50% valid neighborhood fraction, out-of-domain zero padding with available-area denominator, and no flatten-before-neighborhood step. The 0.25° grid implies increasingly broad spatial neighborhoods, not exact kilometer distances. Raw beats M2 on heavy FSS at all four scales; no spatial improvement is claimed.

## 18. Distribution-shift diagnostics

The frozen 2017 training feature-cache SHA was checked before comparing each admitted forecast's paired cells to its training p01–p99 interval. All four cases have **zero missing model-feature cells** and physically plausible decoded units/ranges. Case-level Q700-area mean is 0.00902–0.00954 kg/kg versus 2017 p99 0.008563; PWAT-area mean is 55.22–56.97 kg/m² versus p99 53.05; moisture-transport-area mean is 661.08–797.59 versus p99 661.48, above on three of four cases. For target-cell Q700, **21.3–32.4%** of paired cells lie outside training p01–p99; PWAT **18.8–30.1%**. The full 22-feature count/fraction/min/max matrix is in each `evaluation.json`. This is extrapolation warning under a different forecast system/week, **not proof of long-term climate drift**. GRIB units, levels, reference times, and shapes passed decode identity checks; values were not normalized using 2024 statistics or discarded merely for being out-of-range.

## 19. Missing and rejected cases

No NOAA source index, selected byte range, atmosphere field, or matched IMD date was missing. Three c00 dates (Jul 19, 21, 24) were scientifically rejected on the 3–6 h subtraction packing rule; they remain in the denominator and have no model scores. Fourteen total member-products failed that same rule. The seven-day c00 acceptance fraction is 4/7 **for this week only**, not a seasonal rate. The source-to-QC gap is substantial: 7/7 source-available versus 4/7 deterministic eligible versus 0/7 five-member eligible.

## 20. Comparison with the Phase 4A pilot

The July 15 rejection and July 16 accepted pilot remain untouched. Pilot July 16→17 had Raw/M2 RMSE **20.3662/19.5035 mm** on one 1,301-cell case; it was not part of Phase 4B's fixed window or pooled metric. Phase 4B shows several more packing failures and a worse four-date pooled M2 RMSE. Neither isolated pilot nor this four-case subset overturns the homogeneous held-out **2019** comparison (Raw **19.7735**, M2 **17.8487 mm**, 9.73% lower). They instead expose transfer uncertainty from retrospective reforecast to historical operational GEFS.

## 21. Scientific limitations

Only seven scheduled dates/four admitted dates, one lead, one regional 49×49 domain, no full-ensemble comparator, pronounced rain-QC attrition, no independent gridded-IMD time bounds, no operational-system version harmonization study, and a concentrated Low/Depression pseudo-label mix. The per-cell metrics share storms and spatial correlation. Frozen models/calibrators were trained on reforecasts, not 2024 operational products; predictor shifts and larger negative M2 bias suggest transfer risk but cannot identify its cause from this week alone. IMD reuse/redistribution conditions and live operational readiness remain separate unresolved issues.

## 22. Reproducibility instructions

From the repo root with the existing `.venv`: run `run.py inventory`, then `run.py acquire`, `run.py infer`, `run.py evaluate`, `python -m experiments.recent_historical.phase4b_20240718_20240724_v1.summarize`, and `...audit_sources`, in that order. The first two require access to the official NOAA bucket; validated index/range files are reused if present, never silently replaced. The 2024 IMD file is read from the Phase 4A verified cache. `run.py verify` checks the Phase 4B artifact manifest; `verify_protected.py` checks original Phase 4A listed files, Phase 2B model/freeze hashes and the 525 listed Phase 2C files. The original Phase 4A `verify_experiment.py` has a **closed-set recursive root scan**, so adding an authorized child experiment makes that old *inventory equality* check fail even though its original 145 files and hashes remain intact. This is a documentation/tooling discrepancy; the original verifier/manifest were not edited. No GRIB re-decode is needed to inspect saved evaluations. Verification completed with **28 focused tests passed**, **94 full backend tests passed**, Python compilation passed, and all protected hashes matched. The one warning is an upstream Starlette/AnyIO deprecation, not a test failure.

## 23. Source and artifact hashes

IMD source SHA-256: `1ef02aeba5694dbb57a6cca23a3c2cc11740affb185137c1eacbeab59893228a`. Phase 4A protected manifest SHA-256: `f117a0d8da650ff6f9c7081f1c819b41992d9c579ba811845f56bc372d6c0b8a`. Phase 4B protocol SHA-256: `5e54d38798ef1be96160cdc330602c9feb2e428d3d713d397b44db14d7c3a634`. Phase 4B artifact-manifest SHA-256: `3183df88bb74f56e45522ae71f5ece7e5b019d1eec7afebfdf40a420a7c45994`; **813 files / 77,159,225 bytes** verified. The source inventory and every receipt have their own content hashes. The record includes 224 verified index sidecars and 252 exact GRIB range receipts. GRIB receipts record actual UTC retrieval time; index original HTTP timestamps were not captured, so `source_audit.json` records local file modification time explicitly as a weaker timing proxy.

## 24. Estimated expansion costs

This Day-1 five-member/seven-date selection transferred **73.30 MB** of exact GRIB payload plus **0.84 MB** of indexes, ~10.47 MB GRIB per scheduled date. Index collection took ~1.3 minutes and bounded range acquisition ~8.8 minutes by local file timestamps, excluding later inference/auditing. A naive 122-initialization *Day-1-only* extrapolation is ~1.28 GB selected GRIB ranges and ~14.6 MB indexes; it is **not** a budget for Day 2/3, full 31-member, whole-GRIB, source retry, local derivative, or seasonal validation. Actual availability/QC and service retention could dominate. Three concurrent small index requests were used; ranges were serial and cached. CPU XGBoost stayed frozen; GPU was not forced. Peak RAM was not instrumented, so no measured peak is claimed.

## 25. Recommendation for subsequent work

**LIMITED GO** for showing this fixed historical week as an honest *external-transfer diagnostic* with all seven scheduled dates and all QC failures visible. **No operational skill/production claim**: M2 worsened pooled RMSE and heavy FSS, no complete five-member case survived, and predictor ranges shifted. The smallest next task is an independently authorized Phase 4C **protocol-only** decision on whether/how to study packing-bound failures and operational/reforecast comparability (including additional predeclared dates), without changing the frozen bound, retraining, acquiring a season, or modifying the recording-ready frontend. Do not begin that task automatically.

### Documentation/code discrepancies retained

`AGENTS.md` §3.6 still describes the *legacy* 6-hour target while the active canonical Phase 1F/2B/2C and this experiment use the frozen 24-hour target. The original Phase 4A verifier's closed-set recursive scan conflicts with keeping this approved new experiment beneath `experiments/recent_historical/`; listed-file hash verification preserves original evidence without rewriting it. The IMD annual NetCDF omits explicit accumulation bounds. The NOAA registry's generic member-count description is not used as evidence of this week's complete five-member rainfall QC.
