# Phase 4G — Operational Feature Dataset, 2023–2025

## 1. Executive Summary

Decision: **FEATURE_DATASET_PARTIAL**. The exact 22-column forecast-only deterministic matrix, 12-column forecast-only regime inputs, five-member rainfall subset, and paired 2023/2024 IMD targets are built and hashed. The frozen 26-column probability matrix is **not** available: its four final columns require a future M2 correction and three regime-classifier probabilities, while Phase 4G explicitly prohibits model inference. No substitute, in-sample prediction, zero, or NaN column is presented as a valid 26-feature input. No model was trained, calibrated, or run. The 2025 observation holdout remains sealed.

## 2. Source Corpus

Source: NOAA operational GEFS selected-range and cached decoded/QC products from Phase 4F, `operational_gefs_imd_2023_2025_v1`. Its 36,750 selected messages remain immutable. IMD RF25 2023/2024 files are target-only, with verified SHA-256 `1fa0cbcb56769fd3cd2702e36dc3ee1b81b74755b77c7f058c70dfc3afb82831` and `1ef02aeba5694dbb57a6cca23a3c2cc11740affb185137c1eacbeab59893228a`. No 2025 IMD file was opened by Phase 4G.

## 3. Frozen Protocol

Phase 4D protocol SHA-256 `235f53a10a013de0e8a94eb07f7526f22ac0b624b1bbbb5473c872bf628c2c47`; feature contract `100894f11b677b1de20869d7a741ed16d770d2f4dbff415084fe9888a393842f`; Phase 4E selected-range manifest `4264225ad4845c26de320a05fbb14439a950dfffbdf3fd380964743c048f9e6a`. Phase 4F year manifests and experiment manifest match their documented hashes. Used cached array files are individually checked against their Phase 4F year manifest before read. No canonical QC or source-eligibility rule changed.

## 4. Feature Dataset Version

`operational_features_2023_2025_v1`, separate from the retrospective 2017–2019 corpus, at `data/operational_derived/operational_features_2023_2025_v1/`. Stage A writes `2023/train` and `2024/validation`; only after its freeze exists does Stage B write `2025/test_sealed`. NumPy `.npy` uses `allow_pickle=False`; JSON manifests are sorted, content-stable, and hash-addressed. Individual case row ranges and target-grid pixel indices enable future case/mask retrieval without GRIB re-decoding.

## 5. Eligibility Rules

The 22-feature deterministic source requires c00 canonical rainfall QC and all six atmosphere fields. Paired training/validation adds a valid IMD cell. Regime features require atmosphere only. Ensemble baseline requires all five independent rainfall member products plus the paired IMD cell in 2023/2024. The 26-column probability dataset additionally requires a leakage-safe future corrected-rainfall prediction and three regime probabilities, so **zero rows are currently 26-feature complete**; c00-plus-atmosphere counts are explicitly labeled *probability-source candidates*, not probability-model eligibility.

## 6. 2023 Training Population

375 scheduled cases; 200 paired deterministic cases / 260,200 spatial cells; 200 probability-source candidate cases but zero complete 26-feature probability cases; 76 paired full-ensemble cases / 98,876 spatial cells; 375 regime-input cases.

## 7. 2024 Validation Population

375 scheduled cases; 183 paired deterministic cases / 238,083 spatial cells; 183 probability-source candidate cases but zero complete 26-feature probability cases; 67 paired full-ensemble cases / 87,167 spatial cells; 375 regime-input cases.

## 8. 2025 Sealed Population

375 scheduled forecast cases; 232 deterministic forecast-only cases / 557,032 grid cells, 232 probability-source candidate cases but zero complete 26-feature cases, 75 full-ensemble forecast-only cases / 180,075 grid cells, and 375 regime-input cases. There is no IMD join, target, event label, event count, observation date field, score, or forecast-model output. The 2,401 cells/case here are forecast grid cells, **not paired valid IMD cells**.

## 9. Deterministic Feature Schema

Exactly the frozen ordered Phase 2B/Phase 4D list: raw c00 24-hour rainfall; bilinear-aligned U850, V850, Q700, Z500, MSLP, PWAT; twelve Phase 2A context diagnostics; latitude, longitude; and lead hours. Exact names/order and unit map are in the hash-verified Phase 4D `feature_contract.json` and Stage A freeze. Construction is float64, persisted matrix float32. Leads are 24, 48, 72 h. Rainfall is mm/24 h; U/V m/s, Q700 kg/kg, Z500 gpm, MSLP Pa, PWAT kg/m². No target enters predictors.

## 10. Probability Feature Schema

The frozen order is the above 22 plus `frozen_m2_corrected_mm`, `regime_p_active`, `regime_p_break_weak`, `regime_p_low_depression`. Phase 4D explicitly calls the 2023 correction a future out-of-fold/cross-fit prediction. Neither that prediction nor an operational-era trained regime classifier exists within this task's permitted actions. The original 2017–2019 classifier/model artifacts were protected, not run. A 22-column source reference and explicit missing-column manifest are stored, **not** a mislabeled 26-column array.

## 11. Regime Inputs

All 375 atmospheric-source cases/year yield the frozen 12 ordered forecast-only diagnostics in float64. They are inputs for later operational-era pseudo-label/classifier work; they are not meteorological truth labels or classifier probabilities. No pseudo-label thresholds or classifier are fit in Phase 4G.

## 12. Atmospheric Interpolation

The unchanged Phase 2B `bilinear_to_target` aligns each 51×81 0.5° context field to 49×49 0.25° target-cell centers in float64. This does **not** create additional meteorological source resolution. The same coordinate arrays, ordering and interpolation code are applied in all three years.

## 13. Derived Features

The unchanged Phase 2A `extract_regime_features` computes cos(latitude)-weighted context means, wind-speed and PWAT×speed proxy, MSLP minimum/range, and spherical relative-vorticity mean/p90. The proxy is **not** vertically integrated water-vapor transport. Units and formulas retain the Phase 2A/4D meanings.

## 14. Observation Alignment

Day 1/2/3 maps to IMD date initialization +1/+2/+3 calendar days. The existing IMD reader rejects missing dates, nonfinite/fill and negative valid rainfall, and the builder requires the exact 49×49 10–22°N/68–80°E coordinate grid. The annual files carry date labels but no explicit accumulation bounds; 03–03 UTC equivalence relies on the documented IMD convention, not a file-internal time-bounds variable.

## 15. Heavy Labels

Inclusive `IMD >= 64.5 mm/24 h` on paired valid 2023/2024 cells only. Training 2023 Day 1/2/3 event-cell counts: **1,259 / 1,818 / 1,774** (4,851 total, across 146 forecast cases with at least one event cell). Validation 2024: **1,513 / 2,172 / 2,681** (6,366 total, across 160 event-bearing cases). These are spatial cells, not independent storms.

## 16. Very-Heavy Labels

Inclusive `IMD >= 115.6 mm/24 h`. Training 2023 Day 1/2/3 event-cell counts: **347 / 423 / 463** (1,233 total, across 71 event-bearing cases). Validation 2024: **403 / 530 / 656** (1,589 total, across 103 event-bearing cases). No 2025 event count exists in this phase.

## 17. Valid-Cell Masks

2023/2024 valid cells are the intersection of finite 22 forecast features and finite/non-fill/nonnegative IMD observations. `pixel_index.npy` encodes the exact 49×49 target cell for each row; `cases.json` provides the start/count range and case ID. Each admitted 2023/2024 case has 1,301 valid cells in this dataset, verified by actual daily masks rather than assumed in advance. Missing observations are never converted to zero. The 2025 forecast-only mask is finite forecasts only.

## 18. Common Comparison Populations

`COMMON_DETERMINISTIC_2024`: **183 cases / 238,083 cells** with exact case IDs and pixel indices. `COMMON_PROBABILITY_ENSEMBLE_2024` is presently a **source-only candidate intersection** of 67 cases / 87,167 cells; it cannot become a completed probability-model-versus-ensemble comparison until the four missing probability predictors are generated under separate authorization. See `common_comparison_populations_2024.json`. No head-to-head score is computed here.

## 19. Ensemble-Baseline Population

76/67/75 full-five-member cases in 2023/2024/2025, respectively. Matrices retain five actual QC-passing 24-hour rainfalls; no member is fabricated and no fraction/verification score is evaluated. Source-only 2025 files have all 2,401 grid cells/case.

## 20. Lead Distribution

Deterministic Day 1/2/3 cases: 2023 **46/78/76**, 2024 **51/61/71**, 2025 forecast-only **75/75/82**. Scheduled denominator is 125 per lead/year. Day 1 is underrepresented, especially in 2023/2024, because of unchanged rainfall QC.

## 21. Calendar Distribution

Every June 1–October 3 initialization is retained in the source denominator. The per-year `attrition` JSON records scheduled/QC-pass counts by month, product and member, including October 1–3. No date is replaced using rainfall outcomes. Compared with 2023's 200 admitted c00 cases, 2024 admits 183 and 2025 source-only 232; these are selected subsets, not an unconditional seasonal population.

## 22. QC Attrition

Phase 4F unchanged c00 rainfall QC passes 200/375, 183/375 and 232/375 by year; full-five-member passes 76/375, 67/375 and 75/375. Atmosphere passes all 375/year. Month/lead/member scheduled and pass counts are retained in every year manifest; source-QC fails remain in the scheduled denominator. The feature build introduces no extra case losses beyond source QC and matched observation masks in 2023/2024.

## 23. Training Feature Statistics

All 22 fields have min/max/mean/p01/p50/p99/missing fraction in the 2023 year manifest. Examples (paired-cell population): Q700 mean **0.008130 kg/kg**, p99 **0.012095**; PWAT mean **48.983 kg/m²**, p99 **68.95**; area-mean PWAT×850-hPa-speed proxy mean **458.04**, p99 **666.45**. Missing fraction is zero for admitted rows. Case-repeated diagnostics must not be interpreted as independent cell samples.

## 24. Validation Feature Statistics

The same complete 22-field statistics are in the 2024 year manifest. Q700 mean **0.008987 kg/kg**, p99 **0.012500**; PWAT mean **53.453 kg/m²**, p99 **71.575**; transport-proxy mean **505.03**, p99 **783.44**. Missing fraction is zero for admitted rows. No 2024 normalization was fit.

## 25. Distribution-Shift Notes

The 2024 admitted-cell Q700, PWAT and transport-proxy means and upper percentiles exceed 2023's; this is descriptive conditional-on-QC evidence, not attribution to a model/configuration or a climate trend. No valid unusual case was removed for falling outside 2023 ranges. No 2025 feature distribution was inspected for model design.

## 26. Feature Freeze

Stage A `feature_generation_manifest_v1.json` SHA-256 **`f1520a32aadef460249ba26a39c106f9593fcd3407c23d2967ddc90d889ed67b`**. It binds the builder and reused Phase 2A/2B/IMD-reader source hashes, frozen names, units, dtypes, interpolation, missing-data policy, thresholds, and 2023/2024 year-manifest hashes. A later implementation/contract change requires a new version; Stage B refuses a changed builder hash.

## 27. 2025 Holdout Enforcement

The only observation opener accepts years 2023/2024 and raises `PermissionError` for 2025 before constructing its file path. Stage B does not call it. Tests exercise the denial. The `2025/test_sealed` tree has no target, event-label or observed metric artifact and no observation-derived valid date. This proves the Phase 4G path's behavior, not a machine-wide access control against unrelated programs.

## 28. Dataset Manifests

Year manifests: 2023 `d5f4b832a83d2daa40c14daf8b02b3a18bbdbe6bb854c74c7b068c014267be04`; 2024 `d7e4c78159debd15183b45f69bce5e9dd15631f4a2aa72bdc4b801dd52873c68`; 2025 `d62fc0280208cb2dd94e513ecbdbd3089d5c97bbe11448ee04d296d23ec0e541`. Future split manifest SHA-256 `c400c36d793b68f394774c999bbf6729a439cc9d3bdd415ca9a33f27ce4520b5`; Phase 4G experiment manifest `d5ee92644b64dd496c9070b4868ac25b7f5cab967a9f977581e828798d1eac08`; common-population manifest `f4859ee75e94994b97b0988cd5941a08097a6bcff97527534997a7b49093ce56`; catalogue `fd08568e1da80b4c27bbcbac0c4d6a23976f280900e8cfc0f68a3cd989e5c38c`. Each year manifest hashes the deterministic, regime, ensemble and explicit incomplete-probability artifacts. Full case IDs reside in the split JSON, not inferred from aggregate counts.

## 29. Reproducibility

From repository root: `.venv\Scripts\python.exe -m experiments.recent_historical.phase4g_features_v1.build a`, then `...build b`, then `...finalize`. Stage A must precede Stage B. Re-runs compared existing array values and JSON bytes and reproduced the same Stage A freeze, all three year-manifest hashes, split hash and experiment hash. No random seed, current time, GRIB decode, or network request participates. The separate verifier checks every saved output hash, dtype, shape, target threshold and 2025 seal. Protected checks passed: Phase 4A 145 listed files, Phase 4B 813, Phase 4C 13, Phase 4E 64,610, and Phase 4F 28,335/28,351/28,383 by year. Phase 2B/2C listed/model locks passed their existing verifier. The backend suite passed **131 tests**, with one upstream Starlette/AnyIO deprecation warning; Python compilation passed.

## 30. Storage

The new version contains **38 files / 106,212,759 logical bytes** in bounded year-specific `.npy` arrays plus compact JSON. It reuses Phase 4F cached regional arrays without recopying raw GRIB. No pickle/joblib artifact is authoritative. Year-sized matrices are well below the 18–20 GB RAM policy; the builder keeps only one year in memory at a time.

## 31. Processing Performance

The first Stage A run reported **71.7 seconds for 2023**; the 2024 per-year timing was not retained separately from the command's verbose output. Stage B 2025 forecast-only construction reported **5.3 seconds**, excluding input-hash verification and reporting overhead. No CPU/GPU performance or peak-RAM benchmark was undertaken; Phase 4F concurrency settings were not changed. These are local execution diagnostics, not production throughput guarantees.

## 32. Scientific Limitations

The 26-column probability schema depends on model inference and 2023 cross-fitting that are outside Phase 4G. The 2024 full-ensemble intersection is much smaller than the control candidate set. Day-1 QC attrition biases admission by lead. IMD annual file timing lacks explicit bounds. Spatial cells within one case are correlated. Exact operational GEFS executable/physics builds remain unverified even though selected decoded structural signatures match. The `AGENTS.md` legacy 6-hour-target sentence and active 24-hour corpus contract conflict; Phase 4D/4F explicitly govern this dataset. `docs/81` describes a pilot 0.055-mm packing bound as if fixed, whereas the canonical bound varies by source-message quanta; this work did not alter the historical report. No operational skill or transfer claim follows from feature availability.

## 33. Decision Gate

**FEATURE_DATASET_PARTIAL**. The 2023/2024 deterministic, regime and ensemble-source datasets are suitable for a separately authorized model-development plan; the Phase 4D-frozen *complete* probability dataset is not. The next authorized planning task must resolve how 2023 out-of-fold M2 corrections and regime-classifier probabilities will be generated without training leakage, then freeze that procedure before any probability model fit. Keep 2025 observations sealed and do not infer or score 2025 from this phase.
