# SIH26080 outcome closeout — 8 October 2026

This document describes the **integrated original checkout**. It is an
evidence-based local research pilot, not a public weather-warning service.
The dirty working tree and all frozen experiment evidence were preserved. No
2026 IMD rainfall value was decoded or paired, and no new model was fit here.
Read the frozen source, regime, national and probability decisions in
`docs/159`–`docs/168` before interpreting any score below.

## Outcome matrix

| SIH outcome | Implemented and connected | Tested/scientifically passed | Failed or externally blocked |
|---|---|---|---|
| Weather regimes | Forecast-time active, break/weak and low/depression pseudo-regime probabilities feed regional M3/M4 correction comparisons. A separate coastal/orographic diagnostic exists. Definitions, provenance and a blind 72-case reviewer handoff are versioned. | Causal forecast-only/pseudo-label and handoff integrity tests pass. The pseudo-label comparison is **not** an independent meteorological accuracy test. | M3/M4 have not established improvement over the strongest matched global M2. Coastal/orographic forcing is not a calibrated correction input. **BLOCKED:** zero independent expert labels or adjudications, case-level dated source rights, and a separate winter western-disturbance corpus. |
| Bias-corrected rainfall | Regional Raw M0, linear MOS M1, global M2, hard M3 and soft M4 are served from hash-verified bundles; regional M2 is the live/default correction. A separate full-grid 2023-fit/2024-development M0–M4 ladder exists for research inspection. | Regional replay and same-case verification are reproducible. The sealed national 2024 comparison contains 156 cases and 760,812 reference-valid forecast cells; model arms share eligible cells. | National M2 failed its prespecified 2023 selection. Regional/very-heavy 2024 development gates also failed; east-coast correction failed Raw. National correction is **not promoted**. **BLOCKED:** an untouched comparable year and 2026 source/version clearance. |
| Heavy/very-heavy probability | Regional heavy and very-heavy research probabilities appear with unverified-reliability labels; national v1 fields remain visible only in an opt-in historical research view. The independent v2 repair artifact is preserved separately. | Coherence and forecast-only constraints are tested where applicable. The v1 methodological audit found head-fold leakage and cutoff-space mismatch; v2 repaired those methods before its 2024 pairing. | V2 failed both consumed-2024 paired Brier comparisons: heavy 0.016496 versus v1 0.015524; very-heavy 0.003901 versus 0.003807, and issued **zero** very-heavy warnings against 3,017 events. Neither national head is a validated warning product. **BLOCKED:** independent-year reliability, regional/lead support and a genuinely new frozen protocol if another candidate is attempted. |
| District product | Typed regional `/api/science/live/districts` and map/table expose cycle, source track, model, 24-hour window, verified geometry/weight/manifest hashes, probability status and row coverage. Rows under 95% represented-grid coverage are suppressed. A separate 735-polygon national 2024 research table is local and opt-in. | Regional aggregation has hash, range, missing-cell and suppression tests. National tables are hash-checked and labelled non-official; missing map cells are `null`. | Represented-grid coverage is not full district area coverage. Neither non-official 2021 geometry nor IMD-derived data have public product rights cleared. **BLOCKED:** authorized current boundaries and redistribution decision; independently validated national correction/probability before a national district product. |
| Verification | Raw/M1/M2/M3/M4 scores come from sealed aligned 2-D fields on the same cases. The typed local `/api/science/research/nationwide/verification` serves RMSE, bias, heavy/very-heavy CSI/ETS/POD/FAR and contingency counts, 1/3/5-cell FSS, region/lead breakdowns, date-block uncertainty and evidence hashes. A separate frozen regional historical district-verification API exists. | Hash-chain and same-case API tests pass. Historical replay and existing raw-to-corrected-to-reference studies are separate from new-cycle inference. The national 2024 result is explicitly **consumed development**, not independent skill. | Date bootstrap does not remove spatial/serial dependence. National corrected district skill is not established by the regional historical report. **BLOCKED:** sealed 2026 one-shot scorer until all four `docs/159` source/version gates pass, and later independent performance before promotion. |

## Product decision and scientific limits

- **Default remains regional M2 global XGBoost**, with regional coverage only.
  M3/M4 are comparison arms; the national M2 ladder is historical development
  research; the east-coast candidate and national probability v2 failed.
- A new NOAA forecast cycle proves inference and provenance without reading
  observations. It is not a verification score. A 2025 historical replay is a
  pipeline reproduction, not a new independent test.
- Full-India Raw maps and the 129×135 national research map use different
  documented research masks. Neither establishes national corrected skill or
  official district geography. The national ensemble product remains withheld
  because complete nationwide member fields are absent.
- No source, prediction, score or threshold in a frozen artifact was changed.
- The current regional bundle verifier requires finite 49×49 fields and
  rejects a partial or corrupt cycle. Its served mask therefore has 2,401
  true cells for the sampled cycle. The district aggregator separately has a
  missing-cell suppression test; it never substitutes zero for a NaN.

The national correction failure is specific: 2023 date-fold heavy CSI was
0.07166 for Raw, 0.06565 for direct M2 and 0.06743 for the residual arm, so
neither correction passed selection. On consumed 2024 development pairs,
national M2 heavy CSI was 0.10178 versus Raw 0.06567, but M2 fell below Raw
in the east/northeast (0.01931 versus 0.05835), east-coast peninsula (0.05004
versus 0.06350), and north of the former model domain (0.02848 versus
0.06836). National very-heavy CSI also fell from Raw 0.02529 to M2 0.01466.
These facts explain the no-promotion decision; the aggregate 2024 gain does
not override the prespecified selection and regional gates.

## Exact external dependencies and shortest path

1. Obtain the complete authorized **annual IMD 2026 RF25** reference with
   terms and 03–03 UTC coverage; keep the existing 125 daily grids as a
   separate provisional sensitivity source.
2. Obtain authoritative actual 2026 GEFS deployment identity, exact 2023
   training patch, and numerical/processing comparability evidence for every
   selected predictor. Run the existing metadata preflight first; only when
   all four gates clear may the sealed one-shot 2026 score read observations.
3. Have two qualified independent meteorologists complete the 72-case blind
   forms, with source rights, consent and conflicts recorded; have a distinct
   adjudicator resolve disagreements. Acquire a separately governed wider
   winter corpus before any western-disturbance rainfall claim.
4. Obtain authorized current district geometry and rights. Acquire complete
   nationwide ensemble members only if an ensemble product will be claimed.
5. After independent-year source clearance, assess national correction by
   region, lead and event support, and probability reliability with the frozen
   gates. Promote only a model that passes; otherwise retain regional M2 and
   present the failed result to evaluators honestly.

## Integration change scope

This increment adds a typed, opt-in sealed verification endpoint and national
verification detail on `/india`; versions the regional field and district API
schemas (`live_field_v2`, `live_district_v2`) with explicit lead,
initialization and common valid-cell mask; suppresses insufficiently covered regional district rows;
shows coverage and withheld counts; and updates API/UI contracts and tests.
It makes no training, scorer, source acquisition or model-default change.

## Verification record

All commands ran in this original checkout on 8 October. The Windows
socket-restricted first direct HTTP smoke attempt failed with `WinError 10013`
before reaching the server; its explicitly socket-enabled rerun passed. The
failed attempt is **not** a pass.

| Check | Final result |
|---|---|
| `python -m pytest backend/tests -q --basetemp=data/pytest-sih-outcomes-final3-20261008 -p no:cacheprovider --durations=5` | **837 passed**, exit 0, 311.33 s, after the final API contract change |
| Focused live API/pipeline and national API tests | **37 passed** together, exit 0, after the final API contract change |
| `python scripts/nationwide_research.py check` | Exit 0; 328 feature cases, 156 prediction hashes, 5,105 land cells, full five-region partition |
| `python scripts/summarize_nationwide_research.py check` | Exit 0; 102 initialization dates and uncertainty hash |
| `python scripts/build_nationwide_district_research.py check` and `python scripts/build_nationwide_district_tables.py check` | Both exit 0; 735 research polygons and 156 table hashes |
| `python scripts/nationwide_probability_v2.py check` | Exit 0; protocol, score and 156 preserved prediction hashes; this is **integrity**, not scientific promotion |
| `python scripts/build_source_year_ledger_v4.py --check`, `python scripts/probe_2026_source_clearance.py --check`, `python scripts/acquire_regime_support_docs.py --check`, `python scripts/audit_four_workstreams.py --check` | All exit 0; source audit reports four open gates, bibliographic intake reports **zero** expert labels |
| `python scripts/score_2026_frozen_inference.py --preflight` | Exit 0 with `BLOCKED_BEFORE_OBSERVATION_READ`, 213 sealed forecast cases, zero observation reads |
| `python scripts/live/run_live_cycle.py replay --date 20250926` | Exit 0; all three leads have 1,301 paired cells, worst frozen-array difference 1.11×10⁻¹⁶; existing replay bundle retained |
| Frontend `npm run typecheck`, `npm run lint`, `npm test -- --run`, `npm run build` | All exit 0; 31 Vitest files/**212 tests** and 19 generated static pages |
| Demo launcher preflight and Chromium India/live browser slice | `DEMO_PREFLIGHT_RESULT=READY` twice; **7 end-to-end tests passed** |
| Direct loopback API smoke on live field, live districts and national verification | Exit 0; 2,401 regional valid cells, 188 included/0 withheld districts for sampled cycle, 45 national Day-1 cases and 219,465 paired cells |
| `git diff --check`; C: free disk | Exit 0 (line-ending notices only); 192,341,315,584 free bytes (~179.1 GiB) after the final browser run |

## Files changed in this increment

`backend/app/live/districts.py`, `backend/app/api/live.py`,
`backend/app/api/nationwide_research.py`, `backend/tests/test_live_api.py`,
`backend/tests/test_nationwide_research_api.py`,
`frontend-v2/src/lib/api/live.ts`, `frontend-v2/src/lib/api/live.test.ts`,
`frontend-v2/src/components/live/live-cycle.tsx`,
`frontend-v2/src/lib/api/nationwide-research.ts`,
`frontend-v2/src/components/india/nationwide-research.tsx`,
`frontend-v2/tests/e2e/india-coverage.spec.ts`, `docs/12_API_CONTRACT.md`,
`docs/13_UI_DATA_CONTRACT.md`, `docs/00_INDEX.md`, and this document.
The checkout had substantial other uncommitted and untracked work before this
increment. Nothing was committed.
