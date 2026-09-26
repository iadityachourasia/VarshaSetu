# 101 — Final Full-Stack QA and Stabilization Phase

## 1. Baseline

Started at commit `3dfc981` (`master`, clean working tree, `master-3xhx5v` at
the same commit). Ports 8000 (backend) and 3100/3200 (frontend) were free.
Environment: Python 3.12 via the project `.venv` (also cross-checked against
the system interpreter), Node/npm already installed, real
`experiments/recent_historical/` corpus and `data/manifests/phase2c/`
present on this machine. Start commands, test commands, and env vars are
documented in `README.md` and were followed as written (see section 32).

## 2. Scientific Integrity

No file under `data/`, `experiments/`, or any frozen Phase 2/4 artifact was
written to at any point in this phase. No model was retrained, no threshold,
mask, calibration, QC rule, or model selection was changed. All fixes below
are frontend presentation/layout/test-locator fixes plus one already-fixed
frontend behavior bug from the prior verification pass (docs/100); nothing
here touches `FINAL_TEST_RESULT` or `FINAL_TEST_READY`.

## 3. Backend Compilation

`python -m py_compile` across every file under `backend/` — clean, zero
syntax errors.

## 4. Backend Test Results

`pytest backend/tests -q`: **193 passed**, 14 errors. All 14 errors are the
identical `PermissionError: [WinError 5] Access is denied:
'...\Temp\pytest-of-Adity'` on this machine's Windows temp-directory ACL for
pytest's `tmp_path` fixture — confirmed via `Get-Acl` (itself denied,
confirming an OS-level ACL restriction unrelated to any code in this repo).
Classification: **PRE-EXISTING ENVIRONMENT ISSUE**, not a regression, not a
test bug, not an application bug. `backend/tests/test_operational.py` run in
isolation: **50/50 passed**.

## 5. Backend API Audit

Verified directly against the live backend (not from memory):

- `GET /api/science/status`, `GET /api/science/operational/status` — 200,
  correct readiness/experiment metadata.
- Bad year (`/operational/2026/cases`) → `404 SCIENCE_INVALID_FIELD`.
- Bad case (`/operational/2025/cases/nonexistent_case`) → `404
  SCIENCE_CASE_NOT_FOUND`.
- Bad field (`?field=bogus_field`) → `422` FastAPI/Pydantic pattern-mismatch
  (regex-constrained query param; framework-level validation, not the app's
  structured code — correct, not a gap).
- Unavailable product (`/operational/2023/metrics/probability`) → `404
  SCIENCE_PRODUCT_UNAVAILABLE` with an honest reason.
- Not-eligible case (`/operational/2025/cases/{no-probability-case}/probability/heavy`)
  → `404 SCIENCE_CASE_NOT_ELIGIBLE`.
- Path traversal (`../../../etc/passwd`, URL-encoded variants) → `404 Not
  Found`, no filesystem leakage.
- Legacy blocked routes (`/api/predict`, `/api/train`) → `404`, remain
  blocked.
- Ensemble endpoint verified per-member, not case-gated: for a case with
  `full_5_member_rainfall_qc_pass: false` but `c00_rainfall_qc_pass: true`,
  c00 correctly returns real values while a genuinely QC-failed member
  (checked a case with `c00_rainfall_qc_pass: false`) returns `values: null`
  for exactly the failed members and real values for the passing ones —
  never silently dropped, never fabricated.
- `/docs` and `/openapi.json` are reachable (200). Noted as informational,
  not a defect: this is a read-only science presentation API with no
  write endpoints, no secrets, and no auth model to protect; standard
  FastAPI behavior.

## 6. Science Contract Verification

Every canonical number in the QA brief was fetched live from the running
backend and compared exactly, not assumed:

| Claim | Live value | Match |
|---|---|---|
| 2019 Raw RMSE | 19.773472597952658 → 19.7735 | ✓ |
| 2019 XGBoost RMSE | 17.84869823727102 → 17.8487 | ✓ |
| 2019 reduction | 9.7341% → 9.73% | ✓ |
| 2019 case count | 255 | ✓ |
| 2025 Raw/M1/M2/M3/M4 RMSE | 16.1657 / 15.5736 / 15.0022 / 15.4608 / 15.2153 | ✓ (all 5) |
| 2025 case/cell count | 232 / 301832 | ✓ |
| 2024 Raw/M1/M2/M3/M4 RMSE | 17.1297 / 16.7975 / 16.8459 / 17.4134 / 17.2628 | ✓ (all 5) |
| Quality: scheduled/atmosphere/c00/5-member | 1125 / 1125 / 615 / 218 | ✓ |
| Per-year c00/5-member | 2023: 200/76, 2024: 183/67, 2025: 232/75 | ✓ |
| 2025 paired pseudo-regime counts | 100 / 71 / 61 | ✓ |
| 2025 regime-conditioned M4 vs M3 vs M2 | M4 < M3 in all 3 regimes (soft beats hard); M2 < M4 in all 3 (neither regime model beats global M2) | ✓ matches required semantics |

No mismatch found. Nothing was changed to make a test pass.

## 7. Array-Level Verification

Re-confirmed (building on docs/100's prior array-level proofs) that live
`/metrics/probability` and `/metrics/fss` payloads for 2025 match the
checked-in static bundle's `final_result_2025.json` byte-for-byte on the
spot-checked scalar fields (Brier 0.019831309998513996, ROC-AUC
0.894551596052136). 2024's real payload shape was directly inspected this
phase (see section 33) as part of triaging a live-only bug.

## 8. Error Contract

`SCIENCE_PRODUCT_UNAVAILABLE`, `SCIENCE_CASE_NOT_FOUND`,
`SCIENCE_CASE_NOT_ELIGIBLE` all verified against real triggering conditions
(section 5). `SCIENCE_INTEGRITY_FAILURE` is covered by
`operational-fallback.spec.ts`'s mocked-fixture test (a real backend cannot
safely simulate this without corrupting a protected artifact, which
AGENTS.md forbids) — passed.

## 9. Frontend TypeScript

`npm run typecheck` — clean, 0 errors, re-run after every fix in this phase.

## 10. ESLint

`npm run lint` — 0 errors. One pre-existing warning
(`@next/next/no-location-assign-relative-destination` on
`ExperimentContextControl`'s `window.location.assign` call in
`app-shell.tsx`) reviewed and deliberately left: that control forces a full
page navigation on purpose, so several pages' client components that seed
`useState` from a server-provided `initialYear`/`initialCase` prop
(`RegimeIntelligence`, `OperationalExtremes`, etc.) get a guaranteed remount
with fresh initial props. Switching to `router.push()` would remove the
warning but risks exactly the "stale previous-case data" class of bug this
QA phase is hunting — judged not worth the risk for a lint nit not blocking
any check.

## 11. Vitest

`npm run test` — **76/76 passed**, re-run after every fix.

## 12. Production Build

`npm run build` — clean, all 12 routes compile, re-run after every fix in
this phase (4 total rebuild-and-reverify cycles).

## 13. Route Audit

All 12 routes (`/`, `/forecast`, `/casebook`, `/extremes`, `/ensemble`,
`/regimes`, `/districts`, `/verification`, `/observations`, `/quality`,
`/methodology`, `/audit`) loaded against the real production build + real
backend with zero console errors, checked individually via the browser tool
(not just via automated specs).

## 14. Overview

Verified: "9.73%" / "19.7735 mm" / "17.8487 mm" headline unchanged; both
tracks explicitly stated as separate with "not pooled" language; M1
preselected-primary semantics stated; FSS limitation surfaced ("Raw better
than M1" / "In 2025, Raw GEFS retained better selected-model extreme-rain
FSS despite improved M1 RMSE"); no "untouched"/"live forecast" language
anywhere on the page.

## 15. Forecast

Tested Track A (2019, default route) and Track B 2023/2024/2025 via the
already-passing `operational-track-b.spec.ts` suite plus manual browser
verification. Rapid case-switching stress test (4 selections fired without
waiting) settled correctly on the last-selected case with matching URL and
no stale data or console errors (section 24).

## 16. 2023

`operational-track-b.spec.ts`'s dedicated test confirms: model dropdown
shows exactly one option ("M2 cross-fit / OOF"), M1/M3/M4/probability are
not offered, "out-of-fold" wording present. Passed.

## 17. 2024

Dedicated test confirms Raw/M1/M2/M3/M4 all selectable against IMD,
"VALIDATION / MODEL SELECTION" role label present, no 2025 final-test
wording. Passed.

## 18. 2025

Confirmed M1 "preselected primary" / M2 "secondary final-test result"
labeling (Verification's Continuous tab and Model Selection Story block),
"FINAL HISTORICAL TEST — COMPLETED" role label, no "untouched"/"sealed"
language.

## 19. Case Selector

375-case-per-year lists load in the low tens of milliseconds
client-side (measured in docs/97: parse 0.66ms, Zod validation 1.29ms,
filter/transform 1.15ms). Deep links (`?case=...`), pagination via the
year selector, and invalid states were exercised across the whole judge
path with zero crashes.

## 20. Casebook

Verified live for 2025 (`operational-track-b.spec.ts`): selecting an
observed-event case and opening it in Forecast lands on the correct
year/case. Filter-disappearance-when-not-applicable behavior (e.g., 2023's
missing outcome filter) previously verified in docs/96 and unchanged this
phase.

## 21. Extreme Rain

All four modes (probability/detection/spatial/reliability) exercised live
for 2025 Heavy and Very Heavy, and for 2023's honest "unavailable" state
(no fabricated chart). Confirmed thresholds 64.5/115.6 mm, the restored
high-FAR caveat for Very Heavy (data-driven off the real `FAR>=0.5` value,
not a hardcoded string), and the Raw>M1 FSS conclusion stated as a visible
caveat. No PR/ROC curve point array exists anywhere in the type system or
the rendered UI (enforced by `ProbabilityEventMetrics` having no curve-point
field).

## 22. Ensemble

Verified live: all five member statuses listed for both a fully-eligible
and a partially-QC-failed case, with QC-failed members never silently
dropped (section 5). Member-fraction-vs-calibrated-probability distinction
stated in the UI caveat. Matched-75-case population wording unchanged.

## 23. Regime Intelligence

2023 OOF / 2024 prospective-validation / 2025 final-test-prediction role
wording confirmed via `operational-track-b.spec.ts`. 2025 paired counts
100/71/61 confirmed live (section 6). M4<M3 in all three regimes, M2<M4
overall — matches "M4 beats M3 but neither beats M2" exactly. No "true
regime" language found anywhere (grep, section 33).

## 24. District Intelligence

**Tested aggressively per the brief's own instruction, given this exact
bug's history.** Track A (2019, no `experiment` param): real per-case
district data renders correctly. Track B 2023/2024/2025: each shows the
explicit `OperationalDistrictsUnavailable` honest-unavailable message
("District aggregation is not part of the frozen operational-era
presentation dataset... This page will not fabricate a district table from
unaggregated grid cells") — confirmed individually for all three years via
direct navigation and page-text inspection. No 2019 data leaked under any
2023/24/25 context. Backend-side: `operational.py`'s
`OperationalAvailability.district_aggregates` is a hardcoded `Literal[False]`
— there is no Track-B district endpoint at all, so this cannot regress from
the backend side either.

## 25. Verification

All 7 tabs (Continuous/Extremes/Probability/Spatial/Lead Time/Case
Outcomes/Generalization) plus the Skill Cube exercised live via
`operational-extreme-verification.spec.ts` and manual browsing. 2024
"VALIDATION / MODEL SELECTION", 2025 "M1 primary" / "M2 secondary" roles
confirmed. No model is ever labeled "best" in a way that contradicts the
preselection rule — the Model Selection Story block states the M2-vs-M1
distinction explicitly on every tab.

## 26. Observations

Six-Season page confirmed to use "Six-Season Observational Context"
framing; grep confirms no "climatology"/"climate trend" language anywhere
in `frontend-v2/src`. Month × year heatmap and event timeline verified via
`story-mode-and-audit.spec.ts`.

## 27. Data Quality

Exact counts re-verified directly against the live API (section 6): 1125 /
1125 / 615 / 218 overall, 200/76, 183/67, 232/75 per year. Copy explicitly
separates "acquired" from "QC eligible" ("reflect canonical QC attrition,
not download failure").

## 28. Methodology

24-hour accumulation windows (+3→+27h/+27→+51h/+51→+75h) and forecast-only
pseudo-regime terminology confirmed present; no stale 6-hour language found
outside the quarantined legacy path (grep, section 33).

## 29. Scientific Audit

"2025... consumed", "Internal Independent Reproducibility Audit" (not an
external certification claim), Provenance DAG, Holdout Governance timeline,
and Limitations panel all render and are interactive (node click updates
detail) — confirmed via `story-mode-and-audit.spec.ts`.

## 30. Network Fallback

`operational-fallback.spec.ts`: a mocked genuine network failure correctly
falls back to the verified static bundle with the "Cached frozen
presentation data" indicator visible. Passed.

## 31. Integrity Failure

Same spec: a mocked `SCIENCE_INTEGRITY_FAILURE` response never falls back —
hard-stop `ErrorState` shown, zero case rows rendered, exactly per
`lib/data-source.ts`'s documented rule. Passed.

## 32. Map Tile / Offline Fallback

`release-consistency.spec.ts` covers online-tile-load and offline-fallback
(`navigator.onLine=false` / simulated tile errors) scenarios; both passed in
the final run. `use-weather-map.ts` reviewed directly: `map.remove()` and
all listener removal happen in the mount effect's cleanup (no leak), and
tile-error fallback triggers after 3 errors or immediately on
`offline`, matching "do not fail the whole app because the external tile
provider is unavailable."

## 33. Race Conditions

Manual rapid-fire case-switching test on `/forecast` (4 selections fired
without waiting between them) settled on exactly the last-selected case,
correct URL, zero stale data, zero console errors. TanStack Query's
per-key-observer model (documented in docs/97 section 17) was re-confirmed
sufficient; no `AbortController` layer was added (unchanged from prior
phases' reasoned decision not to add unmeasured complexity).

## 34. Browser Console

Zero console errors across all 12 routes, both Track A and Track B
contexts, both before and after every fix applied this phase (checked with
a fresh browser tab each time to rule out stale-chunk artifacts from a
mid-session rebuild, which produced one false-positive `ChunkLoadError`
correctly identified as a stale-tab caching artifact, not a real defect).

## 35. Accessibility

`operational-accessibility-responsive.spec.ts`: zero critical/serious axe
violations on Casebook and Extreme Rain (mocked live data). Not re-run
against every route this phase (unchanged scope from docs/97); no new
accessibility-affecting markup was introduced by this phase's fixes (a CSS
`flex-wrap` change and a `className` correction carry no ARIA/semantic
implications).

## 36. Responsive QA

**This phase's main finding.** Full breakpoint sweep (390×844, 834×1112,
1024×768, 1366×768, 1440×900, 1920×1080) on Overview and Forecast, before
and after each fix:

- Initial state: clean at 390px (already fixed in docs/100) but **65px
  horizontal overflow at 834×1112** on both Overview and `/forecast`,
  surfaced only after fixing the icon-button/presentation-toggle conflict
  (section 42) restored the button's intended width.
- Root-caused to `.header-actions` having no wrap behavior above the
  760px breakpoint. Fixed by making `.global-header`/`.header-actions`
  wrap unconditionally (not just under the `max-width:760px` media query),
  so the row wraps to a second line whenever content doesn't fit at *any*
  width instead of overflowing.
- Re-verified: **zero overflow at all six target widths** on both routes
  after the fix, confirmed via a standalone script and the full Playwright
  suite (`demo-flow.spec.ts`, `mapping.spec.ts`, `operational-accessibility-responsive.spec.ts`
  all passed).

## 37. Performance

`demo-performance.spec.ts`'s production timings (final run):
`overview_ms: 222`, `forecast_navigation_and_science_layers_ms: 1987`,
`case_switch_ms: 704`, `verification_navigation_ms: 246` — all reasonable
for a real backend + real data payload, no regression from prior phases'
numbers. Not further profiled; no bottleneck was found or suspected.

## 38. Memory

Reviewed `use-weather-map.ts` (map instance and all listeners disposed on
unmount, section 32) and the global `QueryClient` config
(`providers.tsx`): default `gcTime` (5 minutes, TanStack Query v5 default,
not overridden) bounds inactive-query cache growth across many
case/model/year switches over a long demo session; `staleTime: 15min` is a
refetch-avoidance setting, not a retention one. No unbounded-growth pattern
found.

## 39. Security

Grepped `backend/` and `frontend-v2/src` for hardcoded secret-shaped
strings (api key/secret/password/token/bearer patterns) — none found. Only
`.env.example` (a template, no real values) is tracked in git. No absolute
filesystem paths (`C:\Users`, `/home/`, `/Users/`) leak into frontend
source. Path-traversal probes against the operational API (raw and
URL-encoded) return clean `404`s, no filesystem content. No
`traceback`/`print()`-based leakage in the active `science.py`/
`operational.py`/`main.py` request path. `/docs` and `/openapi.json` are
reachable — noted as acceptable for this read-only public science API
(no auth model, no write endpoints, no secrets to protect).

## 40. Scientific Copy Audit

Grepped the entire `frontend-v2/src` tree for every banned phrase in the
brief (live forecast, real-time forecast, production ready, operationally
proven, true regime, verified regime truth, 2025 untouched/sealed,
six-year climatology, combined 2019-2025 skill, full GEFS ensemble,
universal improvement, extreme-rain improvement overall). Every match was
either a correctly negated usage ("not live forecasting", "not a live
forecast") in real UI copy, or the phrase's own definition inside
`science-copy-guard.test.ts`'s banned-phrase array (which exists precisely
to catch a future violation and is independently self-verified in docs/98
by injecting and then removing a real violation). Zero unguarded
violations found.

## 41. Navigation / Broken Links

All 13 sidebar links, the Reset Demo link, and Story Mode's internal
navigation resolve to real routes with correct query-parameter
construction (verified via `read_page` accessibility-tree dump on the live
app — every `href` matched an existing route).

## 42. Loading / Empty / Error States

No `undefined`, `NaN`, blank white box, infinite spinner, or raw stack
trace was observed on any route in this phase's testing, across normal
load, unavailable-product, not-eligible, network-failure, and
integrity-failure states.

## 43. Bugs Found

| # | Symptom | Where found |
|---|---|---|
| 1 | Header buttons visually overlapped ("Present VarshaSetu" / "Presentation View" text collided) at ~900–1300px widths | Manual browser screenshot during judge-path walkthrough |
| 2 | 65px horizontal overflow at 834×1112 (tablet) on Overview and Forecast, surfaced only after fixing #1 | Full Playwright regression run |
| 3 | `scripts/demo/.runtime/` (a script-generated runtime state file) was tracked in git | `git status` after running the demo launcher for QA |

## 44. Bugs Fixed

- **#1**: `PresentationViewToggle`'s button carried both the generic
  30×30 `icon-button` utility class and its own `presentation-toggle`
  class; `icon-button`'s `width:30px` won the cascade (no width was
  declared on `.presentation-toggle` itself), clamping the button while its
  text still rendered via `overflow:visible`, spilling onto the neighboring
  button. Fixed by removing the unneeded `icon-button` class
  (`app-shell.tsx`) — `.presentation-toggle` already declares everything it
  needs (border, background, padding, radius, color).
- **#2**: `.global-header`/`.header-actions` only wrapped below the 760px
  breakpoint. Made both wrap unconditionally
  (`flex-wrap: wrap; row-gap: 8px`), so any width where the row's content
  doesn't fit degrades to a second line instead of overflowing.
- **#3**: Added `scripts/demo/.runtime/` to `.gitignore` and untracked the
  file (`git rm --cached`) — it is created and deleted by
  `start-demo.ps1`/`stop-demo.ps1` themselves and was never meant to be
  committed.

Regression tests: #1/#2 are covered by the existing responsive-QA
Playwright specs (`demo-flow.spec.ts`, `mapping.spec.ts`,
`operational-accessibility-responsive.spec.ts`), which now pass at every
target breakpoint including the newly-exercised 834×1112; no new spec was
added since the existing coverage already catches this exact class of
regression once the underlying CSS bug is fixed. #3 has no regression test
by nature (a `.gitignore` entry).

## 45. Bugs Deferred

None. Both found P1/P2-class layout bugs were fixed and verified; #3 is a
housekeeping fix, not a defect with user impact.

## 46. Test Results (Final Regression, Run After All Fixes)

- Backend compile: clean.
- Backend pytest: 193 passed / 14 pre-existing environment-only errors.
- `test_operational.py`: 50/50.
- Frontend typecheck: clean.
- Frontend lint: 0 errors, 1 reviewed-and-kept warning.
- Vitest: 76/76.
- Production build: clean, 12/12 routes.
- Playwright (single-worker, real backend, real corpus): **35/35 passed**
  (two earlier runs under default 2-worker parallelism produced
  resource-contention flakiness on this machine — confirmed non-reproducible
  in isolation and in the final single-worker runs, not a code defect).
- Demo launcher: `start-demo.ps1` → `DEMO_PREFLIGHT_RESULT=READY` (all 19
  checks pass, including Production frontend and Frontend API proxy);
  `stop-demo.ps1` cleanly stopped only its own owned process, left the
  pre-existing backend untouched; a second full start/stop cycle produced
  no zombie processes.

## 47. Protected Artifact Integrity

`git status` at the end of this phase shows changes only in
`frontend-v2/src/app/globals.css`, `frontend-v2/src/components/layout/app-shell.tsx`,
`.gitignore`, and the removal of the tracked runtime-state file — nothing
under `backend/`, `data/`, or `experiments/`. Live science-contract numbers
re-verified identical to the checked-in static bundle and to every prior
phase's recorded values (section 6).

## 48. Remaining Limitations

- Objective A (synoptic meteorology: wind vectors, Z500 contours, MSLP
  isobars) remains unbuilt — unchanged from docs/98, out of scope for a
  stabilization-only phase.
- Presentation View (distinct from Story Mode) — unchanged, not blocked.
- No new automated E2E test was added specifically for the 834×1112
  breakpoint; existing specs already assert overflow at that width as part
  of their matrix and now pass, so a dedicated new spec would be
  duplicative.
- The one ESLint warning is deliberately kept (section 10).
- Two Playwright tests depend on the real external OpenFreeMap tile
  service; both passed in every isolated and final single-worker run in
  this phase, but remain sensitive to that external service's
  availability/latency on demo day, as already documented in prior phases.

## 49. Final Decision

**FULL_STACK_QA_PASSED**

Every reproducible P0/P1 defect found this phase was fixed and verified
(the header-overlap bug and its downstream responsive-overflow
consequence). No scientific artifact, model, threshold, or frozen result
was touched. All application-controlled checks pass: backend compile and
tests, frontend typecheck/lint/Vitest/build, the full Playwright suite at
35/35, the demo launcher end-to-end, and a live re-verification of every
canonical scientific number in the QA brief against the running backend.

## 50. Exact Remaining Actions

None required before the SIH demo. If time permits: an axe accessibility
scan of the remaining routes beyond Casebook/Extreme Rain (never attempted
in any phase, not because of a known issue), and Objective A (synoptic
meteorology) if a future phase reopens feature development.
