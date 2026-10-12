# India-wide corrected product: bounded first stage

Date: 2026-10-07. Status: **research scaffolding only; no corrected forecast has been produced outside the 10–22°N, 68–80°E model box**. The existing all-India evidence in `docs/140` verifies Raw GEFS only. It cannot establish corrected skill or justify transferring the regional frozen models to other regions.

## First geographic stage

`backend/app/live/india_stages.py` defines only `EAST_COAST_PENINSULA`, exactly the corresponding non-overlapping region of the frozen Raw-verification partition (`docs/140`): south of or at 22°N, east of 80°E through 88°E, on the 129×135 IMD 0.25° grid. A supplied **static** land mask restricts the footprint. The existing regional model box is excluded by construction. Later regions need separately versioned stage definitions and evidence; no full-India model is inferred from this one.

The forecast-only function accepts a Raw field and a global non-regime corrected field with exactly the same valid cells. Values outside that mask remain NaN; valid rainfall must be finite and nonnegative. It requires source, model and static-mask SHA-256 identifiers and refuses a model whose declared training domain differs from the stage. This is a lineage check, **not** proof that the declared model was appropriately fitted: the caller must independently verify the hashes and training manifest before any real run. No observation enters forecast construction.

Retrospective pairing then intersects the forecast mask with the IMD reference mask, retains the paired Raw/global population, and records squared-error sums plus observed heavy (≥64.5 mm/24 h) and very-heavy (≥115.6 mm/24 h) event counts. The reference is never zero-filled. There is no 2026 pairing or scoring here. The district function accepts an externally built stage-specific overlap matrix, computes weighted forecast coverage, and withholds both means below 95% coverage. It does not label the geometry official or assert district completeness.

## Evidence and publication boundaries

The review gate requires unique paired cases from one stage and one model, a matching district table for each case, at least 30 cases and 30 observed events at **each** threshold, at least 90% of listed stage districts above the 95% weighted-area coverage gate in every case, an untouched independent evaluation year, and a versioned/hash-identified geometry with redistribution rights reviewed. It reports paired Raw and global RMSE but only returns `eligible_for_review`; it does not choose a model, establish skill, authorize a public product, or imply national coverage. A future promotion decision also needs the predeclared raw/global/regime comparison, same-cell categorical/FSS and probability verification, lead and event breakdowns, representative district coverage, uncertainty, and independent reproduction.

The pinned `geoBoundaries` simplified 2021 ADM2 source is traceable but not official current geometry. It contains 735 unique features against 736 advertised and carries ODbL 1.0 obligations (`docs/65`). Its existing weights cover only the regional box. A stage-specific, versioned weight matrix and attribution/share-alike review are necessary before distributing a derived district product. Until then, this module can accept only externally prepared test/research weights and cannot publish district forecasts.

## Population and compute gate

The ignored 2023–2025 GEFS/IMD corpora and all-India Raw cache are available read-only in the original checkout, not copied here. The existing 2025 final test is consumed; 2024 has been used for model selection, and 2023 for training. The 2026 independent-test and version/pairing gates remain sealed. No untouched independent year or stage-trained global model is registered for this extension. No GRIB decoding, observation pairing, training or large data copy was performed for this task. Any bounded training or decode job first needs an approved protocol, verified feature availability and source hashes, an exclusive compute slot, and a new output version.

## Verification

`backend/tests/test_india_stages.py` checks partition agreement with the frozen Raw region, rejection of model-domain transfer, matching valid masks and nonnegative rainfall, same-cell reference pairing and event counts, district withholding below 95% weighted coverage, and the consumed-test/support/rights refusal gate. These are synthetic unit fixtures, not scientific results.

Focused backend checks on this worktree: 17 passed, 12 skipped (`test_india_stages.py`, `test_all_india_raw.py`, `test_district_product.py`). The full backend suite could not collect two existing evidence tests because the ignored `experiments` package is absent from this worktree. A wider run excluding those two files was interrupted after it stalled without further output; it is not a pass. No scientific data computation was attempted.

The module is deliberately not connected to `data/live`, the scheduler, API or dashboard. The strict regional live product remains the only corrected experimental cycle path.

## Frozen east-coast development preparation, 7 October

The versioned `east_coast_development_protocol_v1.json` was SHA-256 sealed (`c6a0add86a22392c2561f13b8fc127753b834bcb2627c95682942883706ecb72`) **before stage-specific model fitting or IMD pairing**. It fixes the east-coast footprint, 2023 fit and consumed-2024 development roles, the Raw/stage-trained-global same-case comparison, 24-hour thresholds, date-block uncertainty, event and district coverage gates, and the prohibition on an independent-skill claim. The 2025 consumed test and sealed 2026 year cannot be used for model selection.

`scripts/build_east_coast_static.py` then reused the pinned 2021 geoBoundaries file locally to build a hash-receipted 129×135 boolean mask and 79 stage-intersecting district overlap rows. The geometry marks **508 static land cells** in the east-coast stage. This differs from the 466 land cells with reference coverage reported in the Raw all-India analysis; the polygon footprint and IMD valid-cell mask are different objects, so no missing reference is filled or silently treated as zero. The local static manifest and every array reproduce under `--check`. The 735-versus-736 upstream feature discrepancy, ODbL review and non-official geometry status remain. These weights are not connected to any product.

The full-grid Raw cache and the already hash-receipted 5–30°N, 55–95°E GEFS atmospheric context provide a bounded stage feature path. `scripts/probe_east_coast_features.py` verified the frozen Raw ledger and six atmospheric array hashes for 2023-06-01 Day 1 and 2024-06-01 Day 2, interpolated only forecast fields, and reproduced finite 22-column feature matrices on all 508 static land cells for each case. The tracked `east_coast_feature_probe_v1.json` records source and feature-value hashes; `--check` recomputes them. This proves **two-case forecast-only feasibility**, not eligibility or event support for a complete year. No observation, target, model or 2026 value was opened by the probe.

Remaining bounded development work is to apply this verified path to the predeclared 2023/2024 corpus with strict source/QC and initialization-date separation. **The exact estimator, hyperparameters, feature preprocessing and model-selection rule require an append-only protocol version before any fit**; protocol v1 freezes the domain, roles and comparison but does not authorize choosing that recipe after seeing outcomes. Then fit a stage-specific non-regime control, pair the same valid cells with authorized IMD annual reference and compare Raw versus global by lead, heavy/very-heavy event support, FSS, bias, RMSE and date-block intervals. District coverage must be computed from the same forecast-valid mask. A later untouched comparable year, authoritative geometry/rights decision and separate promotion review are required before any API or live-cycle connection. No stage-trained model, corrected field, paired development score or India-wide corrected claim exists yet.

## Completed bounded development experiment, 8 October

The preceding section is the historical 7 October preparation state. An append-only `east_coast_development_protocol_v2.json` corrected v1's ambiguous observation-order wording and froze the exact 22-feature XGBoost recipe and source hashes **before any stage fit or observation pairing** (SHA-256 `6849d31ec0412a1e90025d91aa2cf983a336b022e8a97ddd849fc00026951dcb`). Its preflight admitted 172 complete 2023 fit cases and 156 complete 2024 development cases. All six atmospheric fields and Raw fields were hash checked. The annual IMD 2023 and 2024 files were hash checked; 2023 reference values were opened only for fitting, and the model and all 156 corrected 2024 forecast arrays were sealed (`east_coast_fit_seal_v1.json`, SHA-256 `8a8ee88eef2529e01ea756d5777324a8c0b098a9536011c6435f`) **before** the separate score step opened 2024 reference values. No 2025 or 2026 value was read by this experiment.

The fixed 2023 fit used 172 cases and 80,152 paired cells. The 2024 score paired Raw and the stage-trained global non-regime control on exactly 156 cases and 72,696 valid cells (466 reference-valid cells per case, versus 508 static polygon cells). The scored result is immutable (`east_coast_development_result_v1.json`, SHA-256 `4240ea36a5ff0bf7f590038d19bb5e4417a912a4a40a5d8dcb4bdd42be04481f`). A separate lead report has SHA-256 `fd3b421b46e858e7611c91ce70ed69fad73e2641e747ba9779588e773322d5f6` and independently recomputes the aggregate RMSE from sealed per-case arrays. All are **consumed-2024 development evidence**, not an independent test.

| 2024 same-cell metric | Raw GEFS | Stage global correction |
|---|---:|---:|
| RMSE (mm/24 h) | 16.8189 | 16.9972 |
| Bias (mm/24 h) | +0.0811 | +3.4405 |
| Heavy CSI, 1,241 observed events | 0.06350 | 0.02958 |
| Very-heavy CSI, 242 observed events | 0.02158 | 0.00000 |
| Very-heavy forecast events | 42 | 0 |
| Heavy FSS, 1/3/5 cells | 0.1194 / 0.2147 / 0.2724 | 0.0575 / 0.1083 / 0.1444 |

The prespecified date-block bootstrap gives global minus Raw heavy-CSI = **−0.03392**, 95% percentile interval **[−0.09008, +0.01928]** from 2,000 resamples over 102 initialization dates. Spatial and serial dependence remain. The lead breakdown has 45/50/61 cases and 219/489/533 observed heavy events at +24/+48/+72 h. Global heavy CSI is 0.0512/0.0185/0.0277 versus Raw 0.0824/0.1019/0.0184. At the very-heavy cutoff the global model forecasts zero events at every lead, so it is unsuitable for an extreme-rain product. No post-score model or threshold selection is authorized.

All 79 research-geometry district rows met the 95% weighted *forecast* coverage gate in each case, and observed event support exceeded 30 at both cutoffs. The gate still refuses review eligibility because there is no untouched independent year and the non-official geometry/redistribution rights are unresolved. More fundamentally, this first correction fails the Raw comparison on aggregate RMSE, heavy CSI and FSS. It remains research-only and disconnected from the API, live worker and dashboard; M2 in the established regional product remains unchanged. A future stage experiment needs a separately frozen, scientifically motivated recipe and fresh evidence, followed by an untouched comparable year before any promotion.
