# Phase 11E: Raw GEFS verification over the whole IMD grid

Date: 2026-10-03. Work package WP-D(2) of `docs/134`. The correction models and every earlier verification cover the box 10 to 22 N, 68 to 80 E (1,301 land cells), while the problem statement is about India. This work verifies the **unmodified (Raw) GEFS control rainfall against IMD over the whole IMD grid**, by region, using the already-downloaded global rainfall messages (no new download). **No model is applied anywhere**, so it measures how large the Raw errors are outside the modelling box and says nothing about any correction there. The coverage row `ALL-INDIA-DOMAIN` moves from PLANNED to **PARTIAL**: the whole domain is verified for the Raw forecast, but it is not post-processed.

## Definition (frozen before any observation was compared)

- **Forecast.** The stored control-member (c00) 24 h rainfall at Day 1, 2 and 3 (+3 to +27, +27 to +51, +51 to +75 h), reconstructed with the canonical accumulation rule on the whole IMD grid (6.5 to 38.5 N, 66.5 to 100 E, 129 by 135 cells; GEFS and IMD share the same 0.25 degree grid points, so nothing is regridded). Only leads that passed the **regional** canonical reconstruction in the study corpus are used. At freeze, every all-India field restricted to the regional box was checked to equal the stored regional field exactly.
- **Observation.** IMD RF25 daily rainfall on the day initialization date plus lead day, valid cells only (fill values excluded, never zero-filled). The three IMD files are hash-pinned.
- **Regions** (a fixed latitude-longitude rule, first match wins; a description of where the forecast is checked, not a meteorological regime): inside the modelling box; north of 22 N up to 88 E; east of 88 E (east and north-east India); south of 22 N between 80 and 88 E (east-coast peninsula); south of 10 N up to 80 E.
- **Statistics.** RMSE, bias and MAE per region; heavy (64.5 mm per 24 h) and very-heavy (115.6 mm per 24 h) POD, FAR, CSI, ETS and frequency bias; by lead; 95 percent whole-initialization-date bootstrap intervals (2,000 resamples, seed 26080, optimistic). Support gate: at least 20 cells, 30 cases and 30 observed event pairs, otherwise "insufficient support" and no number.
- **No decision rule.** The analysis is descriptive. 2023 is the training year of the downstream models (this analysis fits nothing, so it has no independent role), 2024 is a reused development year, and 2025 is a consumed holdout labelled "POST-HOC EXPLORATORY ANALYSIS OF THE COMPLETED 2025 FINAL TEST".
- **Frozen artifacts.** `all_india_raw_protocol_v1.json` and `all_india_raw_ledger_v1.json` (the status and array hash of every case) under `backend/app/evidence_data/phase14/`, written by the `freeze` stage of `scripts/build_all_india_raw.py` before `score` opened any observation. The protocol hash is in `all_india_raw_protocol_v1.sha256`.

## Populations

The wider all-India reconstruction fails more often than the regional one (a negative difference beyond the packing bound can occur anywhere on the larger grid), so these populations are **smaller than the regional study and not identical to it**: 172 of 200 regionally eligible cases in 2023, 156 of 183 in 2024 and 167 of 232 in 2025 were kept; the others are listed in the ledger with their reason. For the same reason the Stage 1 comparison could not be applied (the populations differ); in its place the forecast side was checked at freeze (exact equality with the stored regional field) and the scoring was reproduced by an independent per-cell loop (`backend/tests/test_all_india_raw_evidence.py`), which matches the stored cell counts, RMSE, bias and heavy-rain hits for every region of 2025.

## Result (stored values)

RMSE and bias in mm per 24 h with 95 percent intervals; heavy-rain skill of Raw (CSI and frequency bias).

| Region (land cells) | 2024 RMSE | 2024 bias | 2025 RMSE | 2025 bias | 2025 heavy CSI / frequency bias |
|---|---|---|---|---|---|
| All India (4,964) | 16.93 [15.98, 17.88] | +0.63 [+0.37, +0.87] | 15.77 [15.04, 16.44] | -0.02 [-0.19, +0.17] | 0.040 / 0.33 |
| Inside the box (1,301) | 17.09 [15.61, 18.47] | -0.78 [-1.47, -0.14] | 16.76 [15.38, 18.14] | -1.19 [-1.77, -0.61] | 0.044 / 0.22 |
| North of the box (2,618) | 15.79 [14.43, 17.27] | +0.90 [+0.49, +1.27] | 14.88 [13.74, 15.90] | +0.05 [-0.22, +0.31] | 0.039 / 0.36 |
| East and north-east (519) | 22.02 [19.83, 24.13] | +3.32 [+2.32, +4.35] | 17.49 [16.25, 18.74] | +3.24 [+2.64, +3.85] | 0.046 / 0.61 |
| East-coast peninsula (466) | 16.82 [15.03, 18.52] | +0.08 [-1.06, +1.14] | 16.29 [14.93, 17.72] | -0.82 [-1.86, +0.20] | 0.023 / 0.36 |
| South of the box (60) | 10.39 [8.40, 12.66] | +0.97 [+0.10, +1.91] | 10.61 [7.81, 14.05] | +0.44 [-0.29, +1.32] | 0.034 / 0.46 |

## How to read it

- **Raw has little heavy-rain skill anywhere and under-forecasts it everywhere.** Heavy-rain CSI is below 0.1 in every supported region and year and the frequency bias is below 1 (the forecast produces a fraction of the observed heavy-rain cells). The modelling box is not unusual: its heavy-rain skill is similar to the other regions.
- **East and north-east India has the largest errors** (RMSE 17 to 22 mm per 24 h) and a persistent wet bias of about +1 to +3 mm whose interval excludes zero in all three years, while the modelling box has a dry bias in all three years. A correction trained in the box would therefore not simply transfer east.
- **Very-heavy rain** is supported in the larger regions only (about 1,000 or more observed event pairs in the box and the north, a few hundred in the east and the peninsula) and has a CSI of a few hundredths for Raw; the south region has too few events and carries no number.
- **Lead.** RMSE grows with lead in 2025 (about 15.1, 15.4 and 16.7 mm at Day 1, 2 and 3 over all India).

## What is not established

- Any skill or error of a **corrected** forecast outside the box; no model was applied there and none was trained.
- That the regional differences are caused by a meteorological regime or by geography; the regions are a latitude-longitude rule.
- Raw behaviour outside June to early October.
- Independence of the 2023 row for any model (it is the training year of the downstream models) or of the 2025 row (a consumed holdout).

## Tests

`backend/tests/test_all_india_raw.py` (the partition rule, additive statistics against an independent loop, support gate, deterministic bootstrap), `backend/tests/test_all_india_raw_evidence.py` (hash chain, ledger counts, internal consistency of every stored statistic, labels, tamper refusal, API, and the independent recomputation which is skipped, not passed, when the local IMD file or the frozen cache is absent), `frontend-v2/src/lib/api/all-india-raw.test.ts`, `frontend-v2/tests/e2e/all-india-raw.spec.ts`. The Verification Lab shows the section after the district verification.
