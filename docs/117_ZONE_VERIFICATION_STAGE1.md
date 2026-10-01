# Phase 7C (Stage 1): zone-stratified verification of the frozen models

Date: 2026-10-01. Protocol: `docs/115`, frozen v3 (SHA-256 `a9ff7817…99fd`). Static zones: `docs/116`. Nothing was trained, tuned or selected; the frozen M0–M4 grids were re-aggregated by zone.
This document reports the result of the pre-registered Stage 1 analysis exactly as the protocol defined it, followed by what it does and does not show.

## Method

- Populations: Track A 2018 (development) and 2019 (post-hoc), Track B 2024 (development, already used for selection and calibration) and 2025 (post-hoc). The tracks are never pooled.
- Zones: the four rule-based labels of `docs/116` (they partition the 1,301 land cells) plus all cells. Two overlapping views (any-coastal, any-orographic) are stored for description only and are not part of the decision rule.
- Metrics: RMSE, MAE, bias (forecast minus observation), POD, FAR, CSI, ETS and frequency bias at the IMD 24-hour heavy (64.5 mm) and very-heavy (115.6 mm) categories.
- Support gate: at least 20 cells, 30 cases and 30 observed event cell-case pairs for a categorical score; otherwise `insufficient_support` and no number. Every zone met the gate in every population.
- Uncertainty: paired whole-case bootstrap, 2,000 resamples, seed 26080; intervals are optimistic.
- Q1: metric(zone) minus metric(all cells) per model. Q2: [model minus Raw](zone) minus [model minus Raw](all cells) for RMSE and CSI. Q3 (forcing-strength strata) belongs to Stage 2 and was not run.
- FSS is not reported: the zones are scattered cell sets, so a neighbourhood score would mix zone and non-zone cells (the protocol reports FSS only where a zone is contiguous enough).
- Reproduction gate: the all-cell totals reproduce the published regime evidence (`docs/108`) to 1e-6 mm with exact event counts for all four populations, and the four zones add up to the all-cell totals. A first run exposed a float32 versus float64 threshold difference of one false alarm; the metric was changed to compare in float32 exactly as the frozen metrics do, and the gate then passed.
- Evidence: `backend/app/evidence_data/phase7/zone_verification_{A_2018,A_2019,B_2024,B_2025}.json`, `zone_decision_summary.json`, `zone_verification_manifest.json` (SHA-256 `d967614c1bc9f218d258b7dec78a0858682083c3365a7e13dcd572893f4c89e7`), built by `scripts/build_phase7_zone_verification.py` over `backend/app/ml/zone_verification.py`.

## Results (pooled over cases; Raw, global XGBoost M2 and soft regime M4 shown; the evidence files hold all models)

**Track B 2024 (development evidence)**, 183 cases

| Zone | Cells | Heavy events (share) | RMSE Raw / M2 / M4 (mm) | Bias Raw / M2 / M4 (mm) | Heavy CSI Raw / M2 / M4 | Heavy frequency bias Raw / M2 / M4 |
|---|---:|---:|---|---|---|---|
| ALL | 1301 | 6,366 (100%) | 17.1 / 16.8 / 17.3 | -0.9 / +2.2 / +3.1 | 0.075 / 0.213 / 0.227 | 0.21 / 0.71 / 0.80 |
| COASTAL | 210 | 2,143 (34%) | 22.4 / 24.4 / 25.2 | -3.1 / +4.6 / +6.3 | 0.129 / 0.272 / 0.288 | 0.23 / 1.20 / 1.34 |
| OROGRAPHIC | 245 | 568 (9%) | 14.1 / 13.7 / 13.8 | +0.1 / +1.3 / +2.0 | 0.040 / 0.048 / 0.046 | 0.25 / 0.15 / 0.16 |
| COASTAL_AND_OROGRAPHIC | 109 | 2,627 (41%) | 30.8 / 27.4 / 27.1 | -10.7 / -3.8 / -2.9 | 0.059 / 0.263 / 0.279 | 0.13 / 0.54 / 0.61 |
| OTHER | 737 | 1,028 (16%) | 13.0 / 12.6 / 13.2 | +0.9 / +2.8 / +3.5 | 0.032 / 0.021 / 0.030 | 0.38 / 0.44 / 0.52 |

**Track B 2025 (POST-HOC EXPLORATORY ANALYSIS OF THE COMPLETED 2025 FINAL TEST)**, 232 cases

| Zone | Cells | Heavy events (share) | RMSE Raw / M2 / M4 (mm) | Bias Raw / M2 / M4 (mm) | Heavy CSI Raw / M2 / M4 | Heavy frequency bias Raw / M2 / M4 |
|---|---:|---:|---|---|---|---|
| ALL | 1301 | 6,760 (100%) | 16.2 / 15.0 / 15.2 | -1.3 / -0.9 / +0.3 | 0.048 / 0.073 / 0.088 | 0.22 / 0.15 / 0.20 |
| COASTAL | 210 | 1,841 (27%) | 19.0 / 18.5 / 19.1 | -2.8 / +0.3 / +1.4 | 0.055 / 0.139 / 0.146 | 0.13 / 0.38 / 0.44 |
| OROGRAPHIC | 245 | 653 (10%) | 13.1 / 11.9 / 12.0 | -0.2 / -0.4 / +0.7 | 0.057 / 0.012 / 0.020 | 0.35 / 0.03 / 0.04 |
| COASTAL_AND_OROGRAPHIC | 109 | 2,358 (35%) | 26.3 / 24.6 / 24.2 | -9.6 / -7.5 / -6.1 | 0.033 / 0.083 / 0.106 | 0.07 / 0.13 / 0.18 |
| OTHER | 737 | 1,908 (28%) | 14.1 / 12.8 / 13.0 | +0.1 / -0.5 / +0.7 | 0.053 / 0.004 / 0.021 | 0.45 / 0.02 / 0.06 |

**Track A 2018 (development evidence)**, 251 cases

| Zone | Cells | Heavy events (share) | RMSE Raw / M2 / M4 (mm) | Bias Raw / M2 / M4 (mm) | Heavy CSI Raw / M2 / M4 | Heavy frequency bias Raw / M2 / M4 |
|---|---:|---:|---|---|---|---|
| ALL | 1301 | 6,429 (100%) | 15.6 / 14.0 / 14.2 | +0.4 / -0.6 / -1.1 | 0.076 / 0.039 / 0.016 | 0.41 / 0.11 / 0.04 |
| COASTAL | 210 | 1,764 (27%) | 19.2 / 18.8 / 19.0 | -0.3 / +0.5 / -0.6 | 0.106 / 0.068 / 0.034 | 0.30 / 0.26 / 0.09 |
| OROGRAPHIC | 245 | 474 (7%) | 11.5 / 9.8 / 9.8 | +1.0 / +0.0 / -0.2 | 0.060 / 0.033 / 0.006 | 0.64 / 0.06 / 0.01 |
| COASTAL_AND_OROGRAPHIC | 109 | 2,789 (43%) | 26.8 / 26.1 / 27.0 | -7.3 / -7.2 / -8.5 | 0.078 / 0.037 / 0.014 | 0.15 / 0.09 / 0.03 |
| OTHER | 737 | 1,402 (22%) | 13.1 / 10.7 / 10.7 | +1.6 / -0.2 / -0.4 | 0.053 / 0.000 / 0.000 | 0.98 / 0.00 / 0.00 |

**Track A 2019 (POST-HOC EXPLORATORY ANALYSIS OF THE COMPLETED 2019 FINAL TEST)**, 255 cases

| Zone | Cells | Heavy events (share) | RMSE Raw / M2 / M4 (mm) | Bias Raw / M2 / M4 (mm) | Heavy CSI Raw / M2 / M4 | Heavy frequency bias Raw / M2 / M4 |
|---|---:|---:|---|---|---|---|
| ALL | 1301 | 9,633 (100%) | 19.8 / 17.8 / 18.4 | +0.6 / -1.6 / -2.3 | 0.120 / 0.049 / 0.008 | 0.51 / 0.09 / 0.02 |
| COASTAL | 210 | 3,001 (31%) | 24.6 / 23.9 / 25.2 | -0.1 / -1.3 / -2.9 | 0.201 / 0.089 / 0.016 | 0.51 / 0.17 / 0.04 |
| OROGRAPHIC | 245 | 1,002 (10%) | 17.1 / 14.6 / 14.8 | +0.5 / -1.3 / -1.8 | 0.081 / 0.008 / 0.000 | 0.63 / 0.03 / 0.00 |
| COASTAL_AND_OROGRAPHIC | 109 | 4,075 (42%) | 36.9 / 36.2 / 37.6 | -9.9 / -10.4 / -12.5 | 0.111 / 0.046 / 0.006 | 0.22 / 0.08 / 0.01 |
| OTHER | 737 | 1,555 (16%) | 14.8 / 11.6 / 11.7 | +2.4 / -0.5 / -0.8 | 0.056 / 0.000 / 0.000 | 1.16 / 0.00 / 0.00 |

## What the evidence shows

1. **The Western Ghats coast holds a large share of the heavy rain.** The 109 cells that are both coastal and orographic (8 % of the land cells) contain between a third and 43 % of all observed heavy-rain cell-case pairs in every population.
2. **Raw underforecasts there, in both tracks and all four years.** Raw bias in that zone is roughly −7 to −11 mm per day and Raw forecasts only about 7 to 22 % as many heavy events as were observed there. This is the most consistent result in the stratification.
3. **No frozen model removes it.** On Track B the nonlinear corrected models M2 to M4 reduce the deficit (the linear M1 does not: bias about −9 to −10 mm; M2 to M4 bias −2.9 to −3.8 mm in 2024 and −6 to −7.5 mm in 2025) and raise heavy-event CSI in that zone more than elsewhere (the Q2 interval excludes zero in both years). On Track A the corrected models leave the bias unchanged or larger (about −8.5 to −12.5 mm) and have lower heavy CSI than Raw in every zone. The corrected-model behaviour is therefore track-dependent and must not be generalised from one track.
4. **Coastal-only cells behave differently.** On Track B 2024 the corrected models overforecast there (positive bias, higher RMSE than Raw) while their heavy CSI is higher than Raw.
5. **The interior is where corrected models forecast almost no heavy rain.** In the 737 other cells the corrected models' heavy frequency bias is near zero on Track A and in 2025, and Raw's heavy CSI is as high or higher.

## Decision rule, applied literally

The protocol's rule (development interval excludes zero **and** the final-test point estimate has the same sign, for RMSE, heavy CSI or bias) gives:

| Track | Tests | Development-significant | Geographic gaps | Expected by chance (rough) |
|---|---:|---:|---:|---|
| A (2018 to 2019) | 72 | 46 | 45 | about 3.6 and 1.8 |
| B (2024 to 2025) | 92 | 77 | 72 | about 4.6 and 2.3 |

By the pre-registered rule **Stage 3 is recommended** on both tracks. This should be read with care:

- Q1 compares each zone with all cells, and rainfall magnitude differs strongly between zones, so RMSE, bias and CSI differ between zones even for Raw. Most of the 117 gaps therefore reflect that the zones are different rainfall climates, not that models fail there.
- The OTHER zone is 57 % of the cells, so its difference from all cells is partly arithmetic. The tests share cases and models and are strongly dependent, so the chance counts are only a rough guide.
- The result worth acting on is the specific, replicated Western Ghats-coast deficiency in items 1 to 3, not the count of gaps. The rule was not changed after seeing the results.

## Consequences

- The coastal/orographic row on `/compliance` stays **PLANNED**. Under the protocol it becomes PARTIAL only when Stages 1 and 2 are both complete; Stage 2 has not been run.
- Stage 3 (a geography-aware correction) is **not authorised**. It needs its own frozen protocol and approval, and any such model must be judged against the strongest non-regime baseline, M2, on held-out data. No untouched test period exists, so its independent test would depend on the open data-strategy decision for a new test period.
- Nothing here changes any scientific claim about regime-aware correction: the pseudo-regimes are unchanged, and these zones are a rule-based convention, not a validated regime.

## Limitations

0.25 degrees smooths the Ghats; zone membership is static and rule-based; heavy-event pairs in a zone are spatially and serially correlated; 2024 is a reused development year, and 2019 and 2025 are consumed holdouts analysed post-hoc; FSS is not reported; the heavy-rain figures describe frozen historical-replay models and are not warning skill.

## Tests

`backend/tests/test_zone_verification.py` (7: zone partition, brute-force statistic equality, refusal of unpaired cells, metric formulas, support gate, deterministic paired bootstrap) and `backend/tests/test_zone_evidence.py` (9: manifest and file hashes, reproduction and partition per year, post-hoc labels, no number on unsupported strata, bootstrap declaration, decision-summary consistency).

## Next

Stage 2: forecast-time forcing-strength strata (U850, V850, PWAT, Q700 and the static geometry) with thresholds fitted on the training year only, and the Q3 comparison. Then serve the Stage 1 and 2 evidence through the read-only evidence API and add a zone view to the Verification Lab. Stage 3 stays closed until you approve a protocol.

Gate: `P0_7_STAGE1_COMPLETE`.
