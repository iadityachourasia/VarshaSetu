# Phase 4D — 2023–2025 Operational Corpus Protocol and Acquisition Freeze

Status: **protocol frozen, acquisition not started**. Machine protocol: [`protocol.json`](../experiments/recent_historical/operational_corpus_protocol_v1/protocol.json), SHA-256 `235f53a10a013de0e8a94eb07f7526f22ac0b624b1bbbb5473c872bf628c2c47`. Feature contract: [`feature_contract.json`](../experiments/recent_historical/operational_corpus_protocol_v1/feature_contract.json), SHA-256 `100894f11b677b1de20869d7a741ed16d770d2f4dbff415084fe9888a393842f`. Both byte sequences are frozen; a correction requires v2, not an in-place edit. This report interprets the protocol and does not authorize training, inference, backend exposure, or a live product.

## 1. Executive Summary

Create a **separate** NOAA operational GEFS + official IMD 0.25° corpus, tentatively `operational_gefs_imd_2023_2025_v1`. Predeclare 375 00Z initializations and 1,125 date×lead cases, retaining failed/missing cases in the denominator. Three 24-hour windows and five sampled rainfall members are in scope. The 2023/2024/2025 train/validation/test split is conditional on the all-year source-compatibility inventory. Decision: **AUTHORIZED_FOR_ACQUISITION**, limited to the gated Phase 4E procedure below; no bulk transfer was made here.

## 2. Scientific Motivation

The 2024 external week exposed both packing-sensitive rainfall admission and predictor shift. A homogeneous operational-era experiment can investigate those phenomena without silently treating reforecasts and operational forecasts as one training population. A new corpus is a prerequisite, not a claim that new models will improve skill.

## 3. Relationship to 2017–2019 Benchmark

The frozen retrospective benchmark remains Raw GEFS RMSE 19.7735 mm, M2 Global XGBoost 17.8487 mm, a 9.73% reduction on untouched 2019. Operational data, QC and later scores must have different versions and reports. Neither this design nor the small 2024 transfer test supersedes that benchmark.

## 4. Evidence from Phase 4A

Actual official IMD annual files for 2023/2024/2025 are locally hashed and span all required dates. Selected NOAA July 15 c00 `.idx` objects returned HTTP 200 for all three years; only 2024 selected GRIB bytes were decoded. One 2024 Day-1 pilot failed unchanged QC, the following cycle passed. The 2023/2025 raw-message semantics and year-round availability remain unproved. See [Phase 4A](80_RECENT_HISTORICAL_FEASIBILITY.md).

## 5. Evidence from Phase 4B

The predeclared July 18–24 2024 Day-1 experiment found 7/7 source-index availability, 21/35 accepted rainfall member-products, 4/7 c00-valid cases, and 0/7 complete five-member cases. Its actual range transfer was 73,300,764 bytes plus 836,166 bytes of indexes for seven dates. This week is not a seasonal acceptance or skill estimate. See [Phase 4B](81_SEVEN_DAY_OPERATIONAL_EVALUATION_2024.md).

## 6. Evidence from Phase 4C

Decision `BOTH_MATERIAL`: 14 rainfall member-products failed the frozen bound and admitted forecasts showed Q700/PWAT/moisture-transport shift. Mixed packing also occurs in 2019 reforecasts. Neither source corruption nor a particular producer change was proved. See [Phase 4C](82_OPERATIONAL_REFORECAST_COMPARABILITY_AUDIT.md).

## 7. Operational GEFS Source Timeline

| Period | Selected raw GEFS families | Classification | Evidence limit |
|---|---|---|---|
| 2020-09-23 | GEFSv12 operational implementation, 31-member system, 00/06/12/18Z | VERIFIED CHANGE before corpus | [NWS GEFSv12 notice](https://www.weather.gov/media/notification/pdf2/scn20-75gefs_v12_changes.pdf), [NOAA EMC](https://www.emc.ncep.noaa.gov/emc/pages/numerical_forecast_systems/gefs.php) |
| 2023-06-01–10-03 | `pgrb2sp25/ap5/bp5`; July 15 c00 indexes sampled | NO DOCUMENTED CHANGE FOUND within selected raw families; exact build UNKNOWN | [NCO GEFS products](https://www.nco.ncep.noaa.gov/pmb/products/gens/), local Phase 4A probe |
| 2023-12-05 | NAEFS v7 downstream bias-corrected products changed | VERIFIED CHANGE **outside** selected raw families | [NWS SCN23-104](https://www.weather.gov/media/notification/pdf_2023_24/scn23-104_naefs_v7.0.pdf) |
| 2024-06-01–10-03 | July 2024 selected raw fields actually decoded; other dates not | Selected sample VERIFIED; all-season continuity UNKNOWN | Phase 4B receipts/Phase 4C metadata |
| 2025-06-01–10-03 | July 15 c00 indexes sampled; payload not decoded | NO DOCUMENTED CHANGE FOUND in selected raw families; exact build UNKNOWN | NCO change record and local Phase 4A probe |

The [NCO production change log](https://www.nco.ncep.noaa.gov/pmb/changes/) and [NWS notification index](https://www.weather.gov/notification) reveal no identified 2023–2025 notice establishing a material change to these **raw** selected fields. That is not proof of identical physics, postprocessor builds, GRIB packing, or archive completeness. NAEFS v7 must not be mistaken for a raw GEFS change. The NOAA [reforecast description](https://noaa-gefs-retrospective.s3.amazonaws.com/Description_of_reforecast_data.pdf) explicitly concerns a different retrospective product.

## 8. Source-Version Compatibility

The proposed split is **conditionally compatible**, not confirmed homogeneous. Phase 4E must first inventory all 375 cycles and compare source family, member identity, cycle, native grid, parameter/level/units, GRIB product/grid/representation templates, interval starts/ends and step types across years. A material discontinuity stops acquisition for a v2 review; do not patch the v1 definition. The exact 2023/2024/2025 GEFS executable builds and APCP postprocessor implementations are **UNKNOWN**.

## 9. Corpus Temporal Definition

For each of 2023, 2024 and 2025 include every calendar date **June 1–October 3 inclusive**: 125 initializations/year, 375 total. Three products give 1,125 scheduled cases. Leap day 2024 falls outside the season. The extra October 1–3 initializations relative to a strict June–September JJAS subset are an intentional Phase 4D scope choice; they are **not** silently equated with the old 122-day JJAS benchmark. October 3 Day-3 maps to October 6 IMD. No date may be dropped because it fails QC or scores poorly.

## 10. Forecast Cycles

Only 00 UTC initializations. Other available operational cycles are excluded. Every receipt must carry full initialization UTC, not only a calendar date.

## 11. Forecast Leads

| Product | 24-hour target | Required selected APCP lead files per member | Atmosphere lead | IMD date |
|---|---|---|---|---|
| Day 1 | +3→+27 h | f003, f006, f012, f018, f024, f027 | f024 | init+1 |
| Day 2 | +27→+51 h | f027, f030, f036, f042, f048, f051 | f048 | init+2 |
| Day 3 | +51→+75 h | f051, f054, f060, f066, f072, f075 | f072 | init+3 |

The 16-file rainfall union is an **inventory/minimal expected set**, not permission to infer interval semantics from lead names. Expected segment arithmetic is `(0–6)-(0–3)+(6–12)+(12–18)+(18–24)+(24–27)`, `(24–30)-(24–27)+(30–36)+(36–42)+(42–48)+(48–51)`, and `(48–54)-(48–51)+(54–60)+(60–66)+(66–72)+(72–75)`. The canonical exact-cover implementation decides using *decoded* intervals. Only Day-1 intervals were fully decoded in the 2024 week; Day-2/3 require explicit metadata confirmation before payload expansion.

## 12. Rainfall Data Contract

`pgrb2sp25`, APCP surface, GRIB2, c00/p01/p02/p03/p04. Per cycle: 16 distinct lead files × five members = 80 selected APCP messages if all expected intervals exist. Source rainfall sampled at 1440×721 / 0.25°; verify native grid per message. Control eligibility is independent of the four perturbations. No partial ensemble probability is called five-member P0.

## 13. Atmospheric Data Contract

At +24/+48/+72 h, c00 only: `ap5` UGRD 850 mb (m/s), VGRD 850 mb (m/s), HGT 500 mb (gpm), PWAT entire atmosphere (kg/m²); `bp5` SPFH 700 mb (kg/kg), PRES mean sea level (Pa). Eighteen selected fields/cycle. Decoded 2024 sample is 720×361 / 0.5°; verify each year. Q700 is specific humidity, not relative humidity. All product identities come from indexes **and** decoded GRIB metadata.

## 14. Spatial Domains

Rain target: 10–22°N, 68–80°E, 49×49 at 0.25°. Atmospheric context: 5–30°N, 55–95°E, 51×81 at 0.5°. Normalize source north→south latitude and 0–360° longitude before cropping. Bilinear interpolation aligns atmosphere to target-cell centers and **does not create meteorological source resolution**. IMD finite, non-fill cells define the date-specific comparison mask; do not assume one invariant 1,301-cell mask from a week.

## 15. IMD Observation Contract

Reuse official `RF25_indYYYY_rfp25.nc` files, SHA-256: 2023 `1fa0cbcb56769fd3cd2702e36dc3ee1b81b74755b77c7f058c70dfc3afb82831`; 2024 `1ef02aeba5694dbb57a6cca23a3c2cc11740affb185137c1eacbeab59893228a`; 2025 `7d03cd397ebb1d7209ffae947d3965113643e1f30023cca657f0aa2c800af035`. `RAINFALL(TIME,LATITUDE,LONGITUDE)`, mm/day, -999 fill and nonfinite excluded. 2023/2025 `TIME.calendar` is missing; 2024 is `GREGORIAN`. Use init+1/+2/+3 date labels. The usual IMD 08:30 IST daily window is documented externally by [IMD](https://api.imd.gov.in/public/api_reference.html), but the annual NetCDF lacks explicit accumulation bounds; do not claim file-internal proof of exact 03–03 UTC alignment. No redownload while hashes match.

## 16. Rainfall Reconstruction

Use unchanged `backend.app.data.accumulation.reconstruct_minimal_accumulation_window`: build native direct and supported difference segments from decoded interval metadata; exact-cover dynamic programming minimizes subtraction count then segment count, with deterministic tie-break. For a subtraction, derive each GRIB quantum `q=2^binaryScaleFactor × 10^(−decimalScaleFactor)` and bound `(q_total+q_prefix)/2`. A missing exact cover rejects the affected member-product.

## 17. QC Policy

Reject any intermediate cell below `−(bound+1e−12)` mm, nonfinite/final negative result, incompatible identity/grid, or missing required message. The **existing canonical implementation** normalizes only a negative intermediate *within its derived packing bound* to zero; this is a frozen rounding treatment, not permission to clip beyond-bound values or replace missing rainfall with zero. The method assumes additive underlying accumulations and independent nearest packing; metadata alone cannot prove that physical assumption. Record subtraction counts, bound violations and rejection reasons per member. No numerical tolerance change is authorized.

## 18. Eligibility Matrix

Store separate booleans for `SOURCE_AVAILABLE`, `CONTROL_RAINFALL_VALID`, `ATMOSPHERIC_INPUTS_VALID`, `DETERMINISTIC_ELIGIBLE`, `P01_VALID`–`P04_VALID`, `FULL_5_MEMBER_ENSEMBLE_ELIGIBLE`, `REGIME_ELIGIBLE`, `PROBABILITY_MODEL_ELIGIBLE`, `OBSERVATION_AVAILABLE`, and `FINAL_PAIRED_EVALUATION_ELIGIBLE`. Exact conjunctions are frozen in `protocol.json`. A source-missing case still occupies the scheduled denominator. A valid c00 may be deterministic-eligible without a complete ensemble. Forecast eligibility does not require IMD; paired evaluation does. In 2025, `OBSERVATION_AVAILABLE` and paired eligibility remain **unresolved/not emitted** until unseal: file-header date coverage can be checked, but valid-cell contents, events and paired scores cannot be exposed.

## 19. Feature Schema

The machine [feature contract](../experiments/recent_historical/operational_corpus_protocol_v1/feature_contract.json) lists exact ordered 22 deterministic, 26 probability and 12 regime inputs; each has source/level/hour through the lead mapping, native-grid class, transformation, units and missing policy. All six atmosphere fields are bilinear-aligned; regime diagnostics are computed on the 0.5° context. No target/observed rainfall predictor. A future operational M2 correction used in a 2023 probability training row **must be out-of-fold/cross-fit**, not an in-sample training prediction. The cross-fit recipe requires its own pretraining freeze; this protocol does not authorize a probability fit.

## 20. Regime Policy

Choose **A: reuse the deterministic forecast-only pseudo-label construction and formulas**, versioned for operational-era refitting. Fit any standardization, thresholds and classifier using 2023 only; freeze before 2024 model selection. Do not call pseudo-labels observed meteorological truth. Do not silently transfer 2017 scale/threshold estimates or redesign the formula in 4D. A source discontinuity triggers protocol review before fitting.

## 21. Distribution-Shift Metadata

For **every admitted forecast case** retain each feature's min/max, p01/p50/p99, spatial mean, missing fraction, and fraction outside frozen retrospective reference bounds, plus source-grid and packing fingerprints. Q700, PWAT and PWAT×850-hPa-speed receive particular scrutiny. These are diagnostic, not eligibility filters; unusual but valid meteorology must remain. Compute a training-only operational reference later without 2025 outcome access.

## 22. Training/Validation/Test Split

Conditional, disjoint: 2023 training/development; 2024 validation, calibration, model/hyperparameter and threshold selection; 2025 one-time final test. Full source-compatibility inventory comes first. No model is trained in 4D. Do not optimize frozen retrospective M0–M4 against these data or retroactively change the 2019 result.

## 23. Leakage Prevention

IMD is target-only. No future-valid observation/reanalysis, 2025 observed event frequency, target-derived feature, or year-crossing scaler can enter forecast inference. 2024/2025 outcomes cannot determine which dates are retained; only frozen objective source/QC rules do. For probabilistic stacking, cross-fit 2023 correction features and freeze that exact procedure before 2024 calibration. Evaluate models on common case/cell masks when making head-to-head claims.

## 24. 2025 Holdout Sealing

Keep 2025 IMD values in a separate read-restricted holdout location; record previously verified file hash and header/date coverage only. Phase 4A already inspected 2025 file validity, so “never opened” would be false; no 2025 *performance* was previously evaluated. Phase 4E may inventory 2025 NOAA metadata and apply forecast-only QC without IMD access. Before test unseal, hash the feature/QC/eligibility policy, model families/hyperparameters, regime construction, calibration/thresholds, and operational selection manifest. Log who/when/why unsealed. Run once; no post-test retuning.

## 25. Inventory Strategy

First enumerate all 375 dates × three products × five members/required fields/hours using lightweight NOAA `.idx` sidecars. Record present **and missing** rows under the frozen key/schema in `protocol.json`. Distinguish `INDEX_PRESENT`, `MESSAGE_PRESENT`, `MESSAGE_MISSING`, `SOURCE_UNAVAILABLE`, `SOURCE_FORMAT_CHANGED`. Fetch/parse indexes with bounded retries, then compare expected parameter/level/interval/grid/template metadata between years. A success count alone cannot establish source homogeneity. Expected selected ranges: 98 per date / 36,750 total; distinct index objects can be fewer because several fields share an object.

## 26. Acquisition Strategy

Only after the source gate passes: 2023 selected byte ranges → hashes/receipts/QC; then 2024; then 2025 **forecast** ranges/QC under outcome seal. Use official NOAA cloud, `.idx`-addressed HTTP byte ranges, bounded timeouts/retries/backoff, content-hash idempotency and resumable immutable receipts. Avoid whole-global-GRIB downloads. Retain currently frozen worker settings unless a separate representative concurrency benchmark justifies a versioned change; avoid nested native threads and keep 18–20 GB normal RAM cap. No bulk transfer in Phase 4D.

## 27. Provenance

Per record capture provider, source/object and index URL, date/cycle/member/hour/parameter/level, source index and GRIB metadata, exact byte range, retrieval UTC, SHA-256, local **relative** path and protocol hash. Human-readable receipt + machine manifest must agree. Archive hashes, missing-source status and retrieval failures. NOAA's [NCEI note](https://www.ncei.noaa.gov/products/weather-climate-models/global-ensemble-forecast) cautions that NODD cloud holdings are not an official permanent archive; preservation is a project responsibility.

## 28. Dataset Versioning

`operational_gefs_imd_2023_2025_v1` identity incorporates this protocol hash, dates/cycle/leads/members/variables, source families, IMD mapping and canonical QC. Raw immutable files go under `data/operational_gefs/v1/{year}/...`; derived inventory/decoded/QC/features, future model artifacts and evaluation results occupy separate versioned directories. No files enter the reforecast corpus. QC, source, feature or split changes require a new dataset/protocol version.

## 29. Dataset Card

**Purpose:** independent operational-era forecast/postprocessing research. **Sources:** NOAA/NCEP GEFS raw `pgrb2sp25/ap5/bp5` ([NOAA product inventory](https://www.nco.ncep.noaa.gov/pmb/products/gens/)); official [IMD RF25 annual rainfall](https://imdpune.gov.in/cmpg/Griddata/Rainfall_25_NetCDF.html). **Time:** 2023–2025 June 1–October 3 00Z, Day 1–3. **Space:** 10–22°N, 68–80°E rainfall, 5–30°N, 55–95°E atmosphere. **Members/variables:** c00/p01–p04 APCP; six c00 atmospheric fields. **Reference:** IMD daily mm, date-aligned with time-bound caveat. **QC/eligibility:** canonical packing-aware member-specific; independently retained flags. **Known differences:** operational versus retrospective archive and 0.5° operational atmosphere; 2024 packing/Q700/PWAT shift; exact yearly builds unknown. **License/citation:** cite NOAA/NCEP and IMD source pages and preserve provider access terms per downloaded object; access/licensing concern is a stop gate. **Uses:** research corpus, future explicitly frozen chronological model study. **Non-uses:** live operational claims, mixing with 2017–2019 training, 2025 tuning, district/frontend release absent separate validation. **Version/hashes:** above protocol, feature contract and IMD SHA-256s; future source-manifest hash pending acquisition.

## 30. Storage Estimate

Measured Phase 4B Day-1 sample: 10.47 MB selected GRIB/date and 0.119 MB index/date. Measured Phase 4A July-16 c00 selection: 7.96 MB for 25 rainfall fields + 4.20 MB for 18 atmosphere fields; scaling 16 required rainfall hours × five members and 18 atmosphere fields over 375 dates suggests **~11.1 GB selected GRIB** (decimal), assuming similar field sizes. A separate Phase 4B field-count extrapolation gives **~10.7 GB**. Plan **11–16 GB expected** selected ranges; **~25 GB conservative** for variability/retries, not whole-file acquisition. Indexes **~0.12–0.2 GB expected**, **0.3 GB conservative**. Existing IMD three files total **76,365,196 bytes (~0.076 GB)**. Bounded decoded/Zarr staging **~5–10 GB expected / 15 GB conservative**; feature matrices/QC/prediction outputs **~2–5 GB expected / 10 GB conservative**; receipts/manifests **<0.5 GB expected / 1 GB conservative**; temporary staging **~5 GB expected / 10 GB conservative**. Total local planning envelope **~25–40 GB expected**, **~60 GB conservative** including duplicates/overhead. These are unmeasured planning bounds, not capacity guarantees. Measured free C: space at protocol time: **106,531,663,872 bytes (99.2 GiB)**. Stop below 40 GB free or when remaining estimated transfer plus 20 GB exceeds free space; do not stage full three-year arrays in RAM.

## 31. Processing Estimate

Phase 4B measured ~1.3 min for seven-date Day-1 indexes and ~8.8 min for serial range retrieval, excluding inference/QC. Scaling roughly 32→86 index objects and 36→98 selected fields/date over 375 dates gives **~3.1 h index** and **~55 h serial range transfer** under *identical throughput*; network/service variability may dominate. Allow hours–days with retries. GRIB decoding, canonical reconstruction, atmosphere interpolation, feature generation, QC and future training/validation were **not separately timed on a representative three-lead workload**, so no defensible point estimates exist; benchmark one staged representative week in Phase 4E, report wall time/peak RAM, then extrapolate without changing frozen worker settings absent approval. Future model training/evaluation is a separate phase, not included in an acquisition schedule promise.

## 32. Stop Conditions

Stop on material raw-source/version/GRIB interval mismatch; missing mandatory predictor or changing grid/units; persistent corruption; unsafe disk headroom; failure to isolate 2025 outcomes; altered IMD time/coordinate semantics; licensing/access issue; or need for a QC/feature/split change. Freeze a v2 decision before resuming, rather than adapting v1 in place. Normal scientifically rejected cases remain in the denominator and do not alone justify changing QC.

## 33. Future Training Plan

**Design only:** after acquisition/source/QC audit and a separately approved training freeze, compare operational M0 Raw, M1 Ridge, M2 Global XGBoost, M3 hard forecast-regime routing, M4 soft mixture, plus separately trained/calibrated heavy and very-heavy models. 2023 fit, 2024 select/calibrate, 2025 one-time test. Do not assume retrospective hyperparameters transfer. Keep 2019 benchmark and original model artifacts unchanged.

## 34. Applicability-Domain Research Plan

Explore univariate excursions, multivariate distance, out-of-support cell fraction, regime-input support, source fingerprints and rainfall QC status. No arbitrary “confidence” scalar. Define any guardrail on 2023 and assess validity/coverage–skill tradeoff on 2024 only, before 2025 unseal. Shift diagnostics must not become post-hoc corpus rejection.

## 35. Risks

Major uncertainties: no decoded 2023/2025 payload, unproved Day-2/3 APCP intervals, unknown exact GEFS production builds, non-permanent cloud retention, packing-bound rejects, changing native product grids, 2024 predictor shift, IMD time-bound metadata absence, correlated grid cells, 2025 holdout access control, and storage/network variance. The source-continuity conclusion is **absence of a documented blocker**, not proof of uniform production code. Earlier docs mention 122 June–September starts; this protocol deliberately has 125 through October 3 and cannot be pooled into those denominators.

## 36. Decision Gate

**AUTHORIZED_FOR_ACQUISITION**, conditional on Phase 4E beginning with the complete, read-only **all-year index/metadata compatibility inventory** and stopping *before GRIB payload acquisition* if a material discontinuity is found. This authorizes only the predeclared, staged corpus acquisition once the source gate passes. It does **not** authorize model training, QC relaxation, frontend/API publication, or 2025 outcome opening. If the inventory proves the split incoherent, the next decision is `NEEDS_PROTOCOL_REVISION` or `NO_GO` under a new frozen protocol—not a silent edit to this v1 hash.

Validation evidence (2026-09-24): five focused Phase 4D protocol tests passed; full backend suite **102 passed, 0 failed** (one existing Starlette/AnyIO deprecation warning); Python compilation passed. Existing Phase 4B manifest verified **813** listed files; protected Phase 4A **145**, Phase 2B **5** model files plus freeze/manifest, and Phase 2C **525** listed files verified. Phase 4C manifest hash and all three cached IMD annual-file hashes matched. The old Phase 4A closed-set verifier is not run because its recursive directory-equality assumption predates child experiments; the protected listed-file verifier is the non-mutating replacement. No source GRIB was decoded, downloaded, or inferred in Phase 4D.
