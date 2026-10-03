# Phase 11D: a forecast-time western-disturbance trough indicator, and a negative association result

Date: 2026-10-03. Work package WP-D of `docs/134`. The feasibility study (`docs/122`) found no label source, no upper-tropospheric fields in the verification data and a rainfall domain that stops where these systems act. This work uses the global 0.5 degree forecast fields that were already downloaded (`docs/122` inventory) to build a **forecast-time trough indicator** and tests, under a frozen protocol, whether it relates to observed rainfall in the region where western disturbances act. The requirement stays PARTIAL: the indicator exists and is served, the regime is **not** classified, and **the pre-registered association check was not met**.

## Definition (frozen before any observation was compared)

- **Indicator.** The mean geostrophic relative vorticity at 500 hPa over 25 to 38 N, 62 to 78 E, computed from the forecast 500 hPa geopotential height alone (spherical centred differences, `zeta = g/f * del-squared Z`), in units of 1e-5 per second. A western disturbance is an upper-level trough, so cyclonic (positive) vorticity is the physical signature the heuristic follows. Inputs are the stored global control-member HGT 500 mb message at lead hours 24, 48 and 72; every raw message's hash is checked against its HASH_VERIFIED receipt before decoding. No observation and no model output enter it.
- **Flag.** The indicator at or above the upper tercile of the 2023 training-year distribution (375 cases, threshold stored in the protocol). The flag is relative to that year, so the share of flagged cases changes between years.
- **Frozen artifacts.** `wd_indicator_protocol_v1.json` (sha256 `cce1d4240b51821981a1ec20b0d88f96de652c0b83436b4e8409e0d956ace18f`) and `wd_indicator_cases_v1.json` (the index and flag of every evaluation case), written by the `freeze` stage before `score` opened any observation. The manifest `wd_indicator_manifest.json` has sha256 `f488085f1e70ad63e582214b885d8230185b57938cde5161e7e78df495018283`.

## Pre-registered check and decision rule

Observed quantity: the IMD area-mean daily rainfall over the valid cells of the box 28 to 36 N, 70 to 80 E (western Himalaya and Punjab plains), on the day initialization date plus lead day. The indicator is said to be associated with rainfall only if, in **both development populations** (2021, never used for any selection; 2024, a reused validation year), the flagged-minus-not-flagged mean rainfall is positive with its 95 percent bootstrap interval (whole initialization dates, 2,000 resamples, seed 26080) excluding zero and the population has at least 30 flagged and 30 not-flagged cases. The consumed years 2022 and 2025 are labelled post-hoc and cannot change the decision.

## Result (stored values; mm per day)

| Population | Cases flagged / not | Mean rain flagged / not | Flagged minus not [95 %] | Spearman [95 %] |
|---|---|---|---|---|
| 2021 (development) | 151 / 224 | 2.78 / 4.13 | -1.35 [-2.2, -0.45] | -0.128 [-0.26, 0.016] |
| 2022 (post-hoc) | 126 / 249 | 3.31 / 4.04 | -0.73 [-1.73, 0.33] | -0.23 [-0.355, -0.092] |
| 2024 (development) | 99 / 276 | 4.19 / 3.21 | +0.98 [-0.01, 2.0] | +0.165 [0.022, 0.298] |
| 2025 (post-hoc) | 81 / 294 | 7.01 / 4.29 | +2.72 [1.19, 4.62] | +0.284 [0.15, 0.408] |

**The decision rule is not met.** In 2021 the difference is negative with an interval excluding zero; in 2024 it is positive but its interval includes zero. The recorded wording is therefore: no association with observed rainfall in the north-west India rain box on the development evidence; the indicator is shown without a claim. The reproduction gate passed in every population (flag counts equal the frozen counts, group counts sum to the scored cases, a group mean equals an independent loop).

## How to read it

- **The sign is not stable.** Flagged cases had less rain in 2021 and 2022 and more rain in 2024 and 2025. A real, stable relation would not change sign; this is a negative result, and the 2025 post-hoc rows are not evidence for an association because the development evidence the rule is based on does not support one.
- **The monsoon season is the wrong season.** The corpus covers June to early October, when rainfall in the box is largely monsoon rainfall, and a trough aloft over north-west India in the monsoon can coincide with either a break or an interaction with the monsoon flow. A winter or pre-monsoon corpus could answer the question the heuristic was meant for; it was not acquired.
- **Why it is still served.** It is a transparent, tested, forecast-only diagnostic of upper-level trough strength with an honest negative evaluation. It shows what a western-disturbance regime would be built on and that the simple version does not carry a rainfall signal in this data, which is information a later labelled study needs.

## What is not established

- That a flagged case contains a western disturbance (no label source exists).
- Any skill of a western-disturbance-aware correction (none exists, and no model uses the indicator).
- Behaviour in winter, when these systems mainly act.
- Anything for the Track A reforecast years (only a 5 to 30 N window was kept for them, which clips the box).

## Implementation and tests

- Pure module `backend/app/ml/wd_indicator.py` (vorticity checked against the analytic spherical Laplacian of a smooth field, trough/ridge signs, no patching of missing values, tercile threshold, bootstrap), builder `scripts/build_wd_indicator.py` (`freeze` then `score`), read-only API `backend/app/api/wd_indicator.py` at `/api/science/evidence/wd-indicator/{overview,result,cases}` (hash chain verified, 503 on tamper), panel on `/regimes`.
- Tests: `backend/tests/test_wd_indicator.py`, `backend/tests/test_wd_indicator_evidence.py` (flags re-derived from the stored index and threshold, decision re-derived, tamper), `frontend-v2/src/lib/api/wd-indicator.test.ts`, `frontend-v2/tests/e2e/wd-indicator.spec.ts`.
- The coverage row `REGIME-WESTERN-DISTURBANCE` moves from PLANNED to PARTIAL with evidence-resolved figures only.
