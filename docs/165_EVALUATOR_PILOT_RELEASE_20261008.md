# VarshaSetu evaluator pilot — verified release state, 8 October 2026

This is the current decision record for the integrated original checkout. It builds on the immutable four-workstream disposition in `docs/164` and `four_workstreams_closeout_v1.json`; it does not revise a frozen experiment. The pilot is a **regional, local research demonstration of real NOAA GEFS post-processing**. The default correction is **M2 global XGBoost**. New-cycle output is forecast-only and unverified. It is not an NCMRWF forecast or a public warning.

## SIH26080 requirement decision matrix

The generated code-coverage table in `docs/22` reports all 14 PS IDs as implemented. That word means reachable, evidence-linked capability, not independent scientific success. The distinctions below are what presenters must use.

| PS requirement | Implemented and tested | Scientific state and release boundary |
|---|---|---|
| R01 real NWP; R02 AI post-processing; R05 Raw comparison; R06 corrected grid | Yes: canonical 24-hour GEFS input, Raw/MOS/M2/M3/M4, verified regional arrays and historical comparisons. A new cycle runs without observation input. | M2 is the strongest supported regional product default. Regime correction has not shown added heavy-rain skill against its matched global control. NOAA results are not NCMRWF-transfer evidence. |
| R03 regime classification; R04 regime-conditioned correction | Yes: forecast-time detectors and hard/soft correction arms, with objective/pseudo-label evaluations. | **Expert validation open**: 72 blinded cases, zero independent expert labels and zero adjudications. Western-disturbance winter rainfall corpus has zero cases. Do not claim expert-validated regimes or regime-added correction skill. |
| R07 heavy/very-heavy exceedance probability | Yes: 24-hour threshold heads, frozen outputs, probability verification and API fields. The live API now emits `RESEARCH_ONLY_RELIABILITY_UNVERIFIED` for probability fields and district columns. | **Reliability/promotion failed or open**: the prespecified ordinal candidate failed very-heavy Brier and uncertainty gates (`docs/160`); frozen new-cycle probability reliability is unknown. No public warning threshold is authorized. |
| R08 district table/map | Yes for the established regional 10–22°N, 68–80°E research product with area weights and coverage caveats. | 2021 simplified research geometry is not an official current boundary; rights and national coverage remain open. East-coast stage correction failed its consumed-2024 Raw comparison and is disconnected. |
| R09–R14 RMSE, ETS, CSI, POD, FAR, FSS | Yes: metric functions, gridded spatial fields, tests and historical reports. | Report same-case populations, 24-hour threshold event counts, source track, lead and uncertainty. No 2026 independent score exists. |

## Final checks after the live-status change

All commands ran in the original checkout; test temporary files and build output are ignored. A first sandboxed focused backend run stalled before results and was interrupted. A first sandboxed Vitest run failed to load temporary worker modules (12 suites failed to import; no assertion failure). A first sandboxed Next build was denied Windows path canonicalization. None is counted as a pass. Socket/path-enabled reruns completed:

| Check | Final result |
|---|---|
| Full backend: `python -m pytest backend/tests -q --basetemp=data/pytest-evaluator-pilot-final-20261008 -p no:cacheprovider --durations=5` | **819 passed**, one Starlette/AnyIO dependency deprecation warning; 247.39 s; exit 0. |
| Focused live API after status-field change | **10 passed**, same warning; exit 0. |
| Explicit live/all-India/atmosphere API smoke slice | **23 passed**, same warning; exit 0. |
| Frontend `npm run typecheck`, `npm run lint`, `npm test`, `npm run build` | All exit 0; Vitest **31 files / 212 tests**; Next generated **18 pages**. |
| Targeted live browser test against local FastAPI/Next | **4 passed**; confirms M2 initial field, probability status, regional district table and replay labeling. |
| Optional compliance-page build and browser test (`NEXT_PUBLIC_SHOW_COMPLIANCE_PAGE=1`) | Build exit 0; **5 browser tests passed**, including the implementation-versus-validation note, API-derived counts and page links. The default build keeps this page hidden. |
| Historical replay `run_live_cycle.py replay --date 20250926` | Exit 0; three leads × 1,301 paired cells, maximum frozen-artifact difference **1.11×10⁻¹⁶**. The already existing replay bundle was reused. |
| `audit_four_workstreams.py --check`, source-clearance audit, source-year ledger v4, east-coast seal, RSMC document receipts | All exit 0. The four-workstream result remains `INTEGRATED_WORK_COMPLETE_SCIENTIFIC_GATES_OPEN`. |
| 2026 daily candidate `--check-2026` and GEFS radiation-transition `--check` | Both exit 0. The daily receipt verifies **125 files / 8,707,500 bytes** with `observation_values_decoded=false`; the radiation check verifies metadata only and does not establish executable identity. |
| Frozen 2026 annual scorer and daily sensitivity preflights | Both exit 0 by **blocking before value decoding**. Annual: 213 forecast leads, `BLOCKED_BEFORE_OBSERVATION_READ`; daily: `BLOCKED_BEFORE_VALUE_DECODING`. |
| `git diff --check`; disk | Exit 0 (line-ending notices only); C: free **190,233,280,512 bytes**, about 177.2 GiB, above the 50 GiB floor. |

## Files changed for this increment

`backend/app/api/live.py` and `backend/tests/test_live_api.py` add and verify typed research-only probability status without changing any stored forecast array, threshold or model. `frontend-v2/src/lib/api/live.ts` and its test validate the status. `frontend-v2/src/components/live/live-cycle.tsx` opens on M2, distinguishes M3/M4 comparison arms and displays the probability boundary on maps and district tables; its browser test covers those behaviors. The compliance page now states that code coverage is not scientific promotion; its browser test checks that note when the optional page is enabled. `docs/12`, `docs/13` and `docs/17` update the API/UI and evaluator instructions. This report and `docs/00_INDEX.md` close the evidence loop. The original checkout already contained substantial uncommitted and untracked work before this increment; no commit was made.

## Exact remaining dependencies and next decision

1. **Independent 2026 score:** obtain a complete authorized annual IMD 2026 RF25 file with 03–03 UTC and terms evidence; an actual cycle-specific 2026 GEFS executable/deployment record; the exact 2023 training patch; and a selected-predictor comparability review. The calendar year is still incomplete on this date. The 125 real-time daily grids remain a distinct provisional sensitivity source. Do not open, pair or score 2026 observations until all four gates clear.
2. **Independent regime evidence:** two qualified meteorologists must independently label the 72 blinded cases, and a distinct adjudicator must resolve disagreements using dated case-level sources with rights and consent/conflict records. A separately sourced wider-domain winter corpus is needed for western-disturbance rainfall claims. No synthetic or forecast-derived label can substitute.
3. **Extreme probabilities:** the ordinal gate is final and failed. No new candidate was fitted in this release: 2024 and 2025 outcomes are consumed diagnostics and 2026 is sealed, leaving no reserved independent reliability period. Additional fitting is justified only under a newly frozen, scientifically distinct development protocol with enough event-bearing initialization dates and a reserved comparison period. A consumed 2024/2025 diagnostic cannot become an independent reliability result.
4. **India-wide correction:** the first east-coast stage has 156 same-case consumed-2024 comparisons and failed Raw on aggregate RMSE, heavy CSI and FSS, including zero very-heavy forecast events from the global model. Diagnose and freeze a new recipe before fitting; promotion requires an untouched comparable year plus authorized geometry and redistribution rights. The established regional M2 pipeline remains the only corrected product.
5. **Operational use:** obtain NCMRWF historical forecast grids and terms for a separate adapter/evaluation track, official or authorized district boundaries, IMD/geometry publication rights, independent-year performance and forecaster governance before any public product or warning use.

The shortest evaluator path today is the local, cached Raw → M2 → IMD historical comparison, its aggregate metrics and event counts, then the observation-free new-cycle and district workflow. Present the failed regime/probability/east-coast controls as evidence of fair model selection, not as successes.

The original checkout's four task-owned worktree results were already checked path by path in `docs/163`: 25 owned paths, 19 byte-equal and six containing later integration work. No clean-`master` fallback, commit, or overwrite of the integrated original checkout occurred. The separate task chats were archived previously; archiving is the available chat cleanup action, not permanent deletion.
