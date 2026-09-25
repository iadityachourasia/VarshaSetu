# Phase 4C — Operational vs Reforecast Comparability Audit

Status: **complete diagnostic audit; no scientific gate changed**. Evidence labels below distinguish **VERIFIED FACT** (bytes/code/metadata), **SUPPORTED INTERPRETATION** (consistent with observations but not uniquely proved), and **UNRESOLVED HYPOTHESIS**. All new machine outputs are under [`phase4c_comparability_audit_v1`](../experiments/recent_historical/phase4c_comparability_audit_v1/); the frozen 2017–2019 corpus and Phase 4A/4B records were not modified.

## 1. Executive Summary

**VERIFIED FACT:** All 35 Phase 4B member-products carry the expected Day-1 accumulation intervals. Fourteen fail unchanged Method-A QC; all fourteen use 0.1-mm later / 0.01-mm earlier packing quanta, giving a *derived* 0.055-mm bound. Twenty-seven of 1,887 negative intermediate cells breach that bound, with minimum differences −0.06 to −0.08 mm. The 2019 reforecast also has mixed-precision pairs, so the mere existence of mixed packing is not an operational-only anomaly. Four admitted 2024 cases have large Q700/PWAT feature-range excursions and frozen M2 worsens pooled RMSE from 26.6937 to 28.7093 mm. **Decision: BOTH_MATERIAL.** The next scientific direction is **BUILD_OPERATIONAL_CORPUS**, but only as a separately approved, predeclared, homogeneous operational-era design—not an acquisition or training authorization from this report.

## 2. Motivation

Phase 4A demonstrated one admitted 2024 pilot; Phase 4B predeclared July 18–24 and found source availability did not imply rainfall admission or transferred model skill. The question here is comparability of *representation* and *feature distribution*, not another performance search. No new dates, GRIB ranges, model fits, thresholds or API outputs were produced.

## 3. Phase 4A/4B Evidence

**VERIFIED FACT:** Phase 4B inventoried 7/7 cycles, reconstructed 35 member-products, admitted 21, rejected 14, obtained 4/7 c00-eligible dates and 0/7 complete five-member dates. The four admitted dates have 5,204 paired IMD-valid cells; M2 improved one date and worsened three. Original Phase 4B [protocol](../experiments/recent_historical/phase4b_20240718_20240724_v1/protocol.json) hash is `5e54d38798ef1be96160cdc330602c9feb2e428d3d713d397b44db14d7c3a634`; its artifact-manifest hash is `3183df88bb74f56e45522ae71f5ece7e5b019d1eec7afebfdf40a420a7c45994`. These are not merged with the frozen 2019 9.73% result.

## 4. GEFSv12 Reforecast Configuration

**VERIFIED FACT:** [NOAA's archive description](https://noaa-gefs-retrospective.s3.amazonaws.com/Description_of_reforecast_data.pdf) explicitly says the 2000–2019 reforecasts are *not* archived real-time forecasts: normally one 00 UTC run with c00/p01–p04, and weekly 11-member runs. It describes variable-family GRIB2, three-hour leads in the first 10 days, 0.25° common fields and 0.5° upper-pressure fields. The locally hashed 2019-07-16 c00 APCP sample (`80cbed073c72aead51614a8a6d10412f2fc4cc74767815ef75c6a7d6e569a229`) is 1440×721, 0.25°, GRIB2 edition 2, product template 4.11, representation template 5.3, with `stepType=accum`. Retrospective initial-condition/reanalysis details for this exact case are **UNKNOWN / NOT VERIFIED** from the saved GRIB alone.

## 5. 2024 Operational GEFS Configuration

**VERIFIED FACT:** [NOAA's GEFSv12 change notice](https://www.weather.gov/media/notification/pdf2/scn20-75gefs_v12_changes.pdf) dates operational v12 implementation to 2020-09-23 and specifies FV3/GFSv15.1-based physics, SPPT/SKEB and 31 members; it documents changed GRIB interpolation at that *v11→v12* transition. It does **not** prove a 2019-hindcast→July-2024 internal physics or postprocessing change. [NOAA NCO's product inventory](https://www.nco.ncep.noaa.gov/pmb/products/gens/) documents `pgrb2sp25`, `pgrb2ap5`, `pgrb2bp5`. Locally decoded 2024 APCP is 1440×721, whereas all six sampled +24 h operational atmospheric fields are 720×361. Exact July-2024 executable build, data-assimilation lineage, and product-generation code hash are **UNKNOWN / NOT VERIFIED**.

## 6. Configuration Comparison Matrix

| Property | 2017–2019 GEFSv12 reforecast | July 2024 operational GEFS | Evidence/qualification |
|---|---|---|---|
| Purpose/archive | Retrospective hindcast, variable-family archive | Historical real-time production, grouped lead files | NOAA archive description; Phase 4B receipts |
| Model/version | GEFSv12 family; exact internal build **UNKNOWN** | GEFSv12 operational lineage; July build **UNKNOWN** | 2020 service notice is not a 2024 build record |
| Initialization | 00 UTC once daily in reforecast archive | 00/06/12/18 UTC system; **00 UTC sampled** | NOAA; decoded dates |
| Ensemble | Normally c00 + p01–p04; weekly 11 | System 31; only c00 + p01–p04 sampled/QC'd | Not equivalent ensemble populations |
| Control/perturbations | c00 and perturbed p01–p04 | c00 and perturbed p01–p30 system; first four perturbed inspected | Identity checked by index + GRIB |
| Rainfall grid | 0.25°, 1440×721 sampled | 0.25°, 1440×721 sampled | Actual GRIB |
| Atmospheric grid | 2017 sampled U850/V850/MSLP/PWAT 0.25°; Q700/Z500 0.5° | All six sampled fields 0.5° | Both converted to 0.5° context then aligned to 0.25° target; source representation differs for four fields |
| Output/steps | 3-hour lead cadence; actual alternating intervals | f003/f006/f012/f018/f024/f027 records | Actual GRIB interval keys, not names alone |
| APCP | `tp`, kg m⁻² = mm; `accum` | Same | Decoded identity |
| GRIB edition/templates | 2; PDT 4.11; DRT 5.3; GDT 3.0 sampled | 2; PDT 4.11; DRT 5.3; GDT 3.0 sampled | [ecCodes template guidance](https://confluence.ecmwf.int/spaces/UDOC/pages/181137251/What%2Bare%2Bproduct%2Bdefinition%2Btemplates%2Bin%2BGRIB2%2B-%2BecCodes%2BGRIB%2BFAQ) |
| Packing | Complex spatial differencing | Same | [ecCodes packing keys](https://confluence.ecmwf.int/spaces/ECC/pages/188042102/GRIB%2BKeys) + actual keys |
| Binary scale | 0 in 2019 selected pair | 0 in all 2024 Method-A pairs | Actual keys |
| Decimal scale | 1 or 2 across 2019; sampled pair 2/2 | 1 or 2; 13 pairs 1/1, 20 pairs 1/2, 2 pairs 2/2 | Paired inventory/bytes |
| Reference/bits | Sample 0.0; 12/13 bits for 0–3/0–6 | Sample 0.0; 9/10 bits for Jul18 c00 pair | Field-dependent; not universal |
| Missing values | Sample `numberOfMissing=0` | Sample `numberOfMissing=0`; all cropped arrays finite | Do not generalize to full archives |
| Interval start/end | 0–3, 0–6, 6–12, 12–18, 18–24, 24–27 | Identical all 35 products | No observed reset mismatch for this sampled window |
| Required variables/levels | U/V 850 hPa, Q 700 hPa, Z 500 hPa, MSLP, PWAT | Same six identities/levels/units | Saved source manifests and acquisition metadata |
| Coordinate convention | 0–360° longitude, source north→south, canonical south→north | Same | Actual decoded grid keys |

## 7. Rainfall GRIB Metadata Comparison

**VERIFIED FACT:** The 2019-07-16 reforecast sample's first two messages are 0–3 and 0–6 h, both q=0.01 mm, with maxima 49.15/86.26 mm. The Jul18 2024 c00 first pair uses q=0.1/0.1 mm; representative failing members use q=0.1/0.01 mm. Both use interval-ensemble PDT 4.11 and complex-spatial-differencing DRT 5.3. Actual detailed keys, 35-product first-pair metadata, and 210 operational interval rows are saved as JSON. The reference value, bit count and decimal scale vary by field; a single GRIB precision cannot be asserted for a system.

## 8. Origin of the 0.055 mm QC Bound

**VERIFIED FACT:** [`docs/51`](51_CANONICAL_PRECIPITATION_RECONSTRUCTION.md) and `reconstruct_minimal_accumulation_window` define `q = 2^binaryScaleFactor × 10^(−decimalScaleFactor)` and the *independent nearest-rounding* bound `b=(q_later+q_earlier)/2`. For q=0.1 and 0.01 mm, b=0.055 mm. This is not a global fixed threshold or an empirically tuned tolerance: 2024 accepted pairs also have b=0.01 or 0.1 mm. The old v1 0.1-mm operational cap was superseded for canonical v2. **Scientific limitation:** the half-sum proof assumes the separately encoded fields represent the *same additive underlying cumulative quantity*, are each nearest-rounded on their decoded lattice, and are otherwise temporally/spatially consistent. Packing metadata alone cannot prove those assumptions.

## 9. Packing-Precision Analysis

**VERIFIED FACT:** 2024 pair quanta: 13×(0.1/0.1), 20×(0.1/0.01), 2×(0.01/0.01). The 14 rejects are all in the mixed 0.1/0.01 set, but six mixed products pass. In the archived 2019 Day-1 inventory, 167/610 pairs also have 0.1/0.01; 157 pass and 10 fail canonical Method B. Another 28 have 0.01/0.1; 23 pass and five fail. Thus neither mixed precision nor 0.055-mm bound is new in 2024. Different season/year sampling precludes a causal rate comparison. Decoded float64 subtraction versus float32 arithmetic differs by at most `5.80×10⁻⁶` mm in the 2024 crop—orders of magnitude below 0.005-mm exceedances. The crop changes orientation/extent, not units or values. **SUPPORTED INTERPRETATION:** floating-point roundoff is not the cause. Encoding/field-generation inconsistency beyond the simple nearest-rounding model is implicated; its upstream mechanism is unverified.

## 10. Failed-Product Forensics

**VERIFIED FACT:** Each of the 14 rejected products has 1–4 violating cells. Across 35 products, 1,887 cells are negative and 27 are below their bound. Of all negatives, 1,785 have *both* parent cumulative values ≤1 mm; 26/27 violating cells do too (largest parent among all 27 is 1.06 mm). Violations span 10.25–22°N and 68–80°E, not one obvious corrupt block. Example: Jul18 p03 at 15.75°N/79.5°E has 0–6=0.70, 0–3=0.76, difference −0.06 mm; another has 0–6=0 and 0–3=0.06. Under a true nondecreasing cumulative quantity plus independent nearest rounding at q=0.1/0.01, −0.06 breaches b=0.055. Values are small, but *not* thereby harmless. All remain rejected; no clipping or QC relaxation was performed. The complete per-product parent values and coordinates are in `operational_rainfall_forensics.json`.

## 11. Accumulation-Semantic Comparison

**VERIFIED FACT:** All 35×6 operational message records have the expected explicit starts/ends, `stepType=accum`, statistical process 1, time unit hour, and matching `lengthOfTimeRange`. The 2019 sample shows the same keys for its first six messages. Method B computes `(0–6) − (0–3) + (6–12) + (12–18) + (18–24) + (24–27)` = +3→+27 h in both. No reset or window mismatch is evident *in decoded metadata*. **UNRESOLVED HYPOTHESIS:** product-generation/interpolation may make separately encoded fields nonadditive despite their interval labels; this requires upstream generation documentation or a controlled homogeneous comparison. The IMD annual file still lacks explicit time bounds; its 08:30 IST daily convention is documented externally, not encoded in NetCDF.

## 12. Ensemble-Member Failure Analysis

| Init 2024 | c00 | p01 | p02 | p03 | p04 |
|---|---|---|---|---|---|
| Jul 18 | pass | pass | pass | fail | fail |
| Jul 19 | fail | pass | pass | fail | fail |
| Jul 20 | pass | fail | fail | fail | pass |
| Jul 21 | fail | pass | pass | pass | pass |
| Jul 22 | pass | pass | pass | pass | fail |
| Jul 23 | pass | fail | pass | pass | fail |
| Jul 24 | fail | pass | pass | fail | pass |

Failures by member are c00 3/7, p01 2/7, p02 1/7, p03 4/7, p04 4/7. These are geographically sparse threshold breaches in different members/dates, not evidence that the five-member concept is inherently incompatible. All seven cycles contain at least one failed member, hence no complete five-member P0 baseline. Seven dates are too few for an independent member effect or random-process claim.

## 13. Atmospheric Predictor Comparability

**VERIFIED FACT:** The Phase 4B adapter validates six +24-h forecast fields and maps them to the frozen 22-feature schema. The 2017 source manifest for Jul16 shows U850/V850/MSLP/PWAT sourced at 0.25°, Q700/Z500 at 0.5°; the 2024 sample uses 0.5° for all six. Both are represented on the validated 0.5° context grid, then bilinearly aligned to the 0.25° rainfall grid. Interpolation does not create new meteorological resolution. The 2024 source values have matching units and plausible finite ranges, but that is *numerical compatibility*, not same-distribution evidence. All percentiles below use the hash-verified 2017 model-training cell cache and the same 1,301 paired valid cells per admitted 2024 case. Full p01/p50/p99/outside counts for all 22 features and all four cases are in `feature_distribution_comparison.json`.

| Target-cell field | 2017 p01 / p50 / p99 | 2024 case medians Jul18 / 20 / 22 / 23 | 2024 outside-p01–p99 range |
|---|---|---|---|
| U850 (m/s) | −5.14 / 8.75 / 20.52 | 18.01 / 16.28 / 19.73 / 20.27 | 18.7–47.7% |
| V850 (m/s) | −9.51 / −1.83 / 6.97 | −2.84 / −1.24 / −2.09 / −0.85 | 0–8.1% |
| Q700 (kg/kg) | .00345 / .00869 / .01166 | .0109 / .0112 / .0094 / .0101 | 21.3–32.4% |
| Z500 (gpm) | 5798.87 / 5843.87 / 5874.99 | 5822.65 / 5835.89 / 5853.35 / 5829.31 | 0–12.7% |
| MSLP (Pa) | 99848 / 100635 / 101112 | 100206 / 100276 / 100528 / 100361 | 2.2–9.4% |
| PWAT (kg/m²) | 33.90 / 50.50 / 66.60 | 60.75 / 61.40 / 55.80 / 58.40 | 18.8–30.1% |

## 14. Q700 Distribution Analysis

**VERIFIED FACT:** All four case-level context-area Q700 means, 0.00902–0.00954 kg/kg, exceed the 2017 case/cell-cache p99 0.008563; target-cell medians and 21.3–32.4% above-p99 fractions also shift high. Q700 is sourced at 0.5° in both sampled lineages, so the *four-field source-grid difference* alone cannot explain Q700. It remains possible that the wet week, initialization, process configuration, or a combination contributes. No observation/reanalysis truth field was added to disambiguate them.

## 15. PWAT Distribution Analysis

**VERIFIED FACT:** 2017 target-cell PWAT p99 is 66.60 kg/m²; 2024 case medians are 55.8–61.4 and 18.8–30.1% of paired cells exceed p99. The four context-area means 55.22–56.97 exceed the 2017 p99 53.05. Reforecast source PWAT is sampled at 0.25°, operational at 0.5°, then both are put on the same 0.5° context grid; the source-resolution/product-generation difference is a plausible contributor but is not causally quantified. Units match kg/m², not a ×1000 conversion error.

## 16. Moisture-Transport Analysis

**VERIFIED FACT:** The feature is **an area-mean proxy of `PWAT × hypot(U850,V850)`**, not vertically integrated vector IVT. Its 2017 training p01/p50/p99 are 211.70/452.24/661.48 (proxy units). The four 2024 values are 771.53, 661.08, 724.48, 797.59; three exceed p99. Because this scalar is repeated into every valid cell's 22-feature row, a case-level exceedance means 100% of that case's rows exceed—it is *one case-level diagnostic*, not 1,301 independent anomalies. Stronger low-level winds and PWAT are consistent with physical monsoon variability, but system/representation effects remain possible.

## 17. Meteorological vs System Shift

**SUPPORTED INTERPRETATION:** Finite, correctly labeled Q700/PWAT values and strengthened winds can be meteorologically plausible for a July monsoon week. The 2024 predictor fields nevertheless differ in input product resolution for four variables and operational initialization/ensemble context. Matching units rule out an obvious unit-factor bug; matching interval keys rule out a simple reset mismatch. Seven adjacent days and one reforecast training year are insufficient to attribute the observed distribution shift to meteorology, model system, interpolation, or climate trend. **UNRESOLVED HYPOTHESIS:** upstream accumulation-product postprocessing introduces >nearest-rounding discrepancies. Do not call this “corrupt NOAA data” without additional evidence.

## 18. Frozen M2 Extrapolation Behavior

**VERIFIED FACT:** Saved Phase 4B forecast-only feature matrices and frozen predictions were reused; no model was executed or tuned. On July 18/20/22/23, raw biases are +0.12/−1.48/−5.01/−3.92 mm and M2 biases −8.07/−6.88/−10.03/−6.50 mm. Median M2−Raw corrections are −4.88/−1.34/+0.49/+0.17 mm; 1st-percentile corrections reach −51.59/−31.47/−68.38/−27.04 mm. Cells with Q700 or PWAT above training p99 have mean *absolute-error change* (M2 minus Raw) of −5.80/+2.29/+6.31/+1.26 mm, versus −1.83/−0.54/+0.67/−1.07 in other cells. This association is descriptive and confounded by rainfall intensity and storm location; it is not a post-hoc variable-importance or causal estimate. The much more negative M2 bias and three-date deterioration warrant transfer caution, not frozen-model replacement.

## 19. Regime-Classifier Diagnostics

**VERIFIED FACT:** The four forecast-only class probability vectors for Active / Break-Weak / Low-Depression are approximately `[0.000005, ~0, 0.999995]`, `[0.066339, ~0, 0.933661]`, `[0.000129, ~0, 0.999871]`, `[~0, ~0, 1]`. Respectively 6, 3, 5, 7 of 12 case-level regime inputs lie outside 2017 training-case p01–p99. Extreme softmax probabilities here mean *classifier certainty about its deterministic pseudo-label*, not verified meteorological certainty. Similar broad moisture/wind patterns and classifier extrapolation are both plausible; four admitted cases cannot distinguish them.

## 20. Scientific Interpretation of Phase 4B

**VERIFIED FACT:** The 2024 sources can be decoded and temporally aligned; 21/35 member-products survive the original QC and four c00 cases support honest external diagnostic scoring. **SUPPORTED INTERPRETATION:** both representation-sensitive admission and model applicability are material to transfer. Selection by c00 QC plus four adjacent monsoon cases means the external metrics are not a season-level or unconditional operational sample. The 2019 homogeneous held-out result remains valid *for its reforecast population*; Phase 4B does not validate operational transfer or reverse the original model-selection freeze.

## 21. Applicability-Domain Design

Design only, **not deployed**: check (1) verified source template/units/grid/lead; (2) exact accumulation interval cover; (3) unchanged representation-aware rainfall QC; (4) per-feature 2017 p01–p99 exceedance at cell and case levels, separating repeated area-mean features; (5) a future standardized multivariate distance calibrated on temporally blocked operational validation cases; and (6) tree-leaf support diagnostics if reproducible. A frontend “Model Applicability” indication would require predeclared thresholding, held-out operational calibration, false-alarm/miss evaluation, case-level uncertainty, and explicit non-probabilistic wording. No confidence percentage is justified from current percentiles.

## 22. Future Operationalization Options

Preserve the retrospective v2 corpus/model family. A separate, homogeneous operational-era corpus could characterize actual source-generation configurations, QC admission, predictor distributions and IMD alignment *before* retraining/evaluation. Representation-aware QC research, OOD diagnostics and possible domain adaptation are distinct future proposals, not Phase 4C actions. Decision tree for a future system: **source identity/metadata mismatch → reject; interval mismatch → reject; unchanged QC fail → reject; QC pass + applicability unsupported → research caution/no operational claim; QC pass + independently validated applicability → inference only under separately approved operational model and evaluation gate.** This decision tree itself does not grant operational readiness.

## 23. Scientific Risks

The packing bound relies on assumptions not proved by GRIB metadata; all-2024 violations are near zero but beyond it. The 2019 comparison uses a full season while 2024 is one wet week, so failure-rate differences cannot identify a producer change. Four admitted dates are QC-selected and spatial cells are correlated. All 2024 atmosphere sources are 0.5°, but several 2017 sources were originally 0.25°. IMD daily NetCDF lacks explicit accumulation bounds. Exact 2019-hindcast vs July-2024 operational build/configuration and NOAA production pipeline are **UNKNOWN / NOT VERIFIED**. No raw operational source payload was changed; no rejected product was admitted. A 2024 classifier/skill statement beyond this week would be unsupported.

## 24. Reproducibility

From repository root run `.venv\Scripts\python.exe experiments\recent_historical\phase4c_comparability_audit_v1\diagnose.py`; it reads only cached, hash-verified 2024 message bytes, saved Phase 4B outputs, the 2019 inventory/sample, 2017 feature cache, and IMD day labels for the existing paired mask. It never acquires a network source or invokes model fitting/inference. The new `artifact_manifest.json`/`.sha256` cover diagnostic JSON including official source references. Run `pytest backend/tests/test_phase4c_comparability.py`, the full backend suite, Python compilation and Phase 4B `run.py verify` plus `verify_protected.py`. The original Phase 4A verifier's recursive closed-set scan is superseded for child experiments by listed-file hash checking; its original manifest is unchanged. This audit used ecCodes 2.48 through the existing virtual environment.

## 25. Recommendation

**Decision classification: BOTH_MATERIAL.** Actual 2024 QC attrition is tied to 27 beyond-bound cells in mixed-precision source pairs, while admitted forecasts show substantial Q700/PWAT/transport feature excursions and M2 error deterioration. Causation of either phenomenon is not fully resolved; both are material barriers to an operational-transfer claim. **Recommended next scientific direction: BUILD_OPERATIONAL_CORPUS.** First prepare a versioned, predeclared operational-era source/observation/representation protocol with independent admission and holdout rules; only after separate approval consider acquisition/training. Do not change the frozen QC, retrain, expand dates, expose 2024 in the frontend or declare operational readiness as a consequence of this recommendation.

### Documentation/code discrepancies surfaced

1. [`docs/81`](81_SEVEN_DAY_OPERATIONAL_EVALUATION_2024.md) describes “the 0.055-mm bound” as if fixed across the window; code and decoded 2024 pairs use 0.01, 0.055 or 0.1 mm depending on quanta. All 14 failures happen to be in the 0.055 class. The historical report is preserved; this document supplies the qualification.
2. `AGENTS.md` §3.6 still calls 6-hour rainfall the current project target, while the governed Phase 1F–4C experiment uses +3→+27 h **24-hour** rainfall. This audit does not rewrite governance.
3. The original Phase 4A verifier recursively inventories its parent, so an authorized child directory breaks closed-set equality despite unchanged original files; listed-file hash verification is the appropriate non-mutating check for this nested work.
4. NOAA's v11→v12 interpolation notice must not be paraphrased as evidence of a documented *v12 reforecast→2024 operational* physics upgrade. The latter exact configuration difference remains unverified.
