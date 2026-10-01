# Phase 6B (P0-4) — Track B district product completion

## 1. Purpose and status

`docs/107` shipped the Track B district product (2024/2025) with one corrected model per request. The PS-facing brief asked for more: all models side by side,
per-district error and improvement against Raw, a selected-district history, and the label *Historical District Decision-Support Prototype*. This phase adds
those on the **same pinned Phase 2C overlap weights** (no new weighting) and the same valid-cell rule. Nothing was trained, tuned or selected, and no skill
score is introduced (district-level verification was done separately under a frozen protocol: `docs/112`, `docs/113`).

## 2. What was built

| Piece | Detail |
|---|---|
| `GET /api/science/operational/{year}/cases/{case_id}/districts/compare` | Raw, IMD and all four corrected models for every district in one response: per model mean, max, heavy / very-heavy area fraction, `error_mm` (model district mean − IMD district mean) and `improvement_vs_raw_mm` = \|Raw − IMD\| − \|model − IMD\| (positive = closer to IMD than Raw); plus `raw_error_mm`, probabilities, IMD replay, pseudo-regime, model roles, the improvement definition, weights/geometry SHA-256 and caveats |
| `GET /api/science/operational/{year}/districts/{district_id}/history?model=` | Descriptive series for one district over all the year's paired cases: case id, initialization, lead, valid cells, and the district **means** of Raw, the chosen model and IMD. **It carries no error, bias, MAE, RMSE, categorical or skill field** (asserted by a test). Cached per (year, district, model). 2023 → 404 `SCIENCE_PRODUCT_UNAVAILABLE`; unknown district → 404 |
| `district_case_means` (`backend/app/ml/district_product.py`) | pure single-district version of the aggregation (identical weighting and validity), unit-tested equal to the full-row aggregation |
| UI (`frontend-v2/.../operational-districts.tsx`) | title area now reads **Historical District Decision-Support Prototype**; table toggle *Selected model / Compare all models*; compare measures *District means · Error vs IMD · Improvement vs Raw* with the definition shown; map option *Selected model error vs IMD* on a labelled diverging scale; inspector table of Raw + M1–M4 (mean, error, "closer/farther than Raw"); history chart (IMD, Raw, selected model) with the descriptive-only note |
| Shared pieces | `DistrictMap` gained an optional `colorFor` prop (default unchanged), `errorColor` in `lib/maps/grid.ts` |

## 3. Verification

| Check | Result |
|---|---|
| Backend `test_district_product.py` | 19/19 (8 new): compare equals the single-model endpoint for **every** model/district (means, max, area fractions, errors, improvement formula, probabilities, model roles) for 2024 and 2025; history points equal the per-case endpoint values (first / middle / last case, M1 2024 and M3 2025) and the compare row for the reference case; history is sorted, unique and **contains no skill token**; pure single-district function equals the full aggregation; 404/422 paths |
| `tsc`, `eslint`, Vitest | clean, 101/101 (3 new schema tests incl. a missing-model rejection and encoded history URL) |
| Playwright `operational-districts.spec.ts` | 9/9 (5 new): label present and no "official warning"; compare table values equal the API for the top district across means, errors and improvement; error-map legend; inspector lists 5 rows; history has three series and no skill statistic; 2024 compare + history. One existing assertion was made `.first()` because the model-role text now also appears in the history caption |
| Browser check | compare table, error map (blue/red diverging with legend), inspector and 232-case history render for 2025; Raigarh example: IMD 100.1 mm, Raw 14.3 mm, M1 13.3 / M2 17.5 / M3 17.8 / M4 17.9 mm |
| Full regression | see §5 |

## 4. Limitations (keep when quoting)

- Improvement is a **single-case, district-mean** quantity. It is not a skill score and must not be aggregated or averaged into one by the UI; district-level verification (event definitions, support rules, improved/worsened counts with uncertainty) is P0-5 and is protocol-first.
- History is descriptive only. Eyeballing a series is not verification.
- Everything in `docs/107` §6 still applies (domain-limited, simplified geometry, valid cells only, live-API only, 2025 consumed holdout, pseudo-regime labels, no 2023 product).
- The compare endpoint computes four aggregations per request (≈0.2 s warm; the first request after a cold start pays the one-time Phase 2C/4J integrity hashing).
- The history chart plots cases ordered by date × lead; the three leads of a date are different samples joined only to show order.

## 5. Regression

Backend suite: 256 passed, 14 errors (all the known Windows `tmp_path` permission error, `docs/101`). Full Playwright, one worker, `next start` and the real backend: **75 passed, 1 failed** - the pre-existing `demo-flow.spec.ts:4` Overview strict-locator failure (`"9.73%"` in two elements since the Overview redesign; identical on the pre-Phase-4N code, `docs/107` §7).

Gate: `P0_4_DISTRICT_PRODUCT_COMPLETE_VERIFICATION_NOT_STARTED` (presentation of frozen aggregates only; no scientific claim added).
