# VarshaSetu two-day evaluator handoff — 9 October 2026

## Decision

The **local regional research pilot is ready to demonstrate now** at
`http://127.0.0.1:3200` while the launcher-owned services run. The current
launch uses the explicit local-only national research switch. It processes
real NOAA GEFS forecasts, shows a same-case regional Raw/M2/IMD historical
comparison, serves forecast-only new-cycle inference, and maps a hash-verified
129×135 India-wide **Raw** grid. The regional M2 global XGBoost correction
remains the product default. This is not an NCMRWF forecast, an independently
validated India-wide correction, or a public warning service.

The two-day target is an evaluator-ready **evidence presentation and local
pilot**, not clearance of unavailable external evidence. The current calendar
date precedes completion of the annual 2026 IMD reference. The versioned
one-shot scorer still reports `BLOCKED_BEFORE_OBSERVATION_READ` on 213 sealed
forecast leads. No 2026 observation values were opened or paired.

## What to demonstrate in 6–8 minutes

1. Open `/india`: 2025-09-26 Day 1 Raw GEFS on the full 129×135 grid. Say the
   land outline is simplified research geometry. Follow its regional case link.
2. In the historical case, show matched Raw, regional M2 correction and IMD
   reference with the same accumulation window and color scale. Use aggregate
   verification and event counts; describe a selected case as an example.
3. Show the forecast-time active, break/weak and low/depression regime vector
   and M3/M4 comparison arms. Say the labels are forecast-derived proxies and
   regime conditioning has not beaten the matched global control.
4. Open `/live`: show source, cycle, lead, 24-hour window, M2 field, district
   coverage and evidence hash. Explicitly distinguish a replay from a new
   forecast. Probabilities are research-only with unverified new-cycle
   reliability.
5. On `/india`, open the 2024 nationwide research comparison. Switch among
   M0–M4 and probability fields, then show the same-case verification table
   and no-promotion status. Finish with the honest decision: these are
   reproducible development results, but no national model or warning
   threshold passed promotion. The independent 2026 score is sealed.

Use [the full presenter script](17_DEMO_PROTOCOL.md) for timing and fallback.
Before a presentation run
`& .\scripts\demo\start-demo.ps1 -IncludeNationwideResearch` on this machine;
it runs scientific preflight before and after starting the frontend. The
updated preflight checks India Raw source/shape/hash, replay M2 district
lineage, and the national research no-promotion flag. Omit the switch for the
default, regional-only local launch. To change modes, stop the launcher-owned
services with `& .\scripts\demo\stop-demo.ps1` first; never stop an unowned
service. The API remains bound to `127.0.0.1`, and source/data rights are not
expanded by this local view.

## Five-outcome evidence matrix

| SIH outcome | Implemented and tested | Scientific decision | Exact remaining dependency |
|---|---|---|---|
| Regimes | Forecast-time vector and regional hard/soft correction arms; 72-case blinded package and hash-verified RSMC page leads | Pseudo-label outputs are **not expert validation**; M3/M4 added heavy-rain skill is unproven | Two independent meteorologists, a distinct adjudicator, admissible dated case sources/rights; separate wider-domain winter corpus for western disturbances |
| Bias correction | Regional M0–M4 and same-case historical verification; separate full-grid national development ladder | Regional M2 default; national 2023 selection and 2024 regional/very-heavy gates failed; east-coast correction failed Raw | Comparable untouched year and source-version review before any national promotion |
| Heavy/very-heavy probability | Forecast-only 24-hour heads, coherence checks, reliability and spatial diagnostics | Ordinal, national v2 and v4 promotion gates failed; v4 very-heavy Brier interval crossed zero and warning frequency remained high | Independent-year reliability and supported lead/region event counts before warning use |
| District product | Versioned regional M2 API/table with cycle, mask, ≥95% represented-grid coverage and evidence hashes; national 735-polygon table is local research | Research geometry, not official current district boundaries; national correction/probability not promoted | Authorized current geometry, IMD/geometry rights, validated nationwide fields |
| Verification | Aligned 2-D RMSE, CSI, ETS, POD, FAR, FSS, counts, lead/region breakdowns and date-block intervals | Reproducible historical/development results; new-cycle inference has no skill score | Complete annual IMD 2026, actual 2026 GEFS deployment, exact 2023 patch, seven-predictor comparability and human source approval before the one-shot score |

The generated PS coverage table marks all 14 requirement IDs implemented in
code. It does **not** certify independent scientific success. Detailed
definitions, negative results and uncertainty are in `docs/159`–`docs/180`,
especially `docs/169`, `docs/176`, `docs/179` and `docs/180`.

## Verification in the integrated original checkout

| Check | Result |
|---|---|
| Most recent full backend suite (before this handoff's PowerShell/documentation-only edits), Windows socket-enabled pytest run recorded in `docs/180` | **878 passed**, exit 0; not rerun in this handoff |
| Frontend `npm run typecheck`, `npm run lint` | Both exit 0 |
| Frontend `npm test` outside restricted sandbox | **31 files, 212 tests passed**, exit 0. Initial sandbox run had 12 transform-import failures and is not counted. |
| Frontend `npm run build` | Exit 0, 19 static pages generated |
| Chromium India/live slice after rebuilt opt-in launch | **7 passed, 0 skipped**, exit 0; includes the national research map and no-promotion status |
| `audit_four_workstreams.py --check` | Exit 0: integration complete, scientific gates open |
| `nationwide_research.py check`, `nationwide_probability_v4.py check`, `build_regime_report_page_index.py check` | All exit 0; hash/protocol integrity only, not model promotion |
| `score_2026_with_clearance_gate_v2.py --preflight` | Exit 0: `BLOCKED_BEFORE_OBSERVATION_READ`, 213 forecast cases |
| Rebuilt demo launcher preflight with `-IncludeNationwideResearch` | `DEMO_PREFLIGHT_RESULT=READY` twice; India Raw, regional district, sealed national research, API proxy and frontend passed |
| HTTP `/india`, `/live`; `git diff --check`; C: free space | HTTP 200/200, diff exit 0 (line-ending notices), **177.18 GiB** free |

The initial restricted-sandbox Vitest failure was an ENOENT in temporary
transform files, not a test assertion failure; only its completed rerun is a
pass. No decoder or trainer was launched in this handoff. The research
protocols, frozen scores, source receipts and 2026 forecasts were not changed.

## Two-day action boundary

The remaining **local** work is presenter rehearsal, choosing a predeclared
historical example, testing the offline fallback, and packaging the existing
evidence with clear Raw/regional/national labels. No new fit against consumed
2024/2025 outcomes can create an independent test. Do not substitute the 125
provisional 2026 daily grids for the prespecified annual IMD reference.

The project owner must obtain the four source/version items above, qualified
reviewers and source rights, authorized current district geometry and
publication terms, and NCMRWF historical grids/terms if an NCMRWF-specific
claim is desired. These depend on providers or people and cannot be honestly
completed by local code work within two days. After the source gate clears,
run the **v2** human-approved one-shot scoring entrypoint once, inspect
region/lead/event-support and probability reliability gates, and promote only
what passes. A null result retains regional M2.

## Files changed in this handoff

`scripts/demo/preflight-demo.ps1`, `scripts/demo/start-demo.ps1`,
`docs/17_DEMO_PROTOCOL.md`, this document, and `docs/00_INDEX.md`. The
original checkout contains substantial earlier
uncommitted and untracked work; it was preserved. No commit was made.
