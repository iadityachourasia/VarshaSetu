# 94 — Six-Year Explorer and Synoptic Frontend (Phase 5A.2)

## 1. Executive Summary

Before this phase began, `frontend-v2` already implemented the large majority
of what Phase 5A.2 asks for: a working Track A/Track B experiment-and-year
context switcher, a flagship Forecast & Atmosphere workspace with multi-map
sync, model/atmosphere/error-anatomy modes, a point inspector, capability-
aware model lists per year, correct OOF/preselected-primary/secondary
badging, an Extreme Event Casebook with real filters, an Ensemble page, a
Regime Intelligence page, and a Data Quality funnel view — all served from a
pre-generated static JSON bundle (`frontend-v2/public/science/operational-v1/`)
rather than a live backend. This was **not built in this conversation**; it
predates this phase's work (visible as already-present, uncommitted files in
`frontend-v2` when this phase started). This document is honest about that
distinction: it credits what already existed, verifies it against the frozen
science, and describes only what this phase actually added or fixed.

**What this phase actually did:**
1. Added the structured `{code, detail}` error contract to
   `/api/science/operational/*` (section 5 of the brief) — small, additive,
   backward-compatible, tested.
2. Found and fixed a genuine, concrete gap: `/districts` silently ignored
   `?experiment=operational`, showing the 2019 Track A workspace mislabeled
   under any Track B year/experiment selection. Replaced with an honest
   capability-unavailable state (section 69).
3. Verified (via a real running backend + frontend, not just static
   reasoning) that the pre-existing Forecast, Districts (Track A), and the
   error/capability plumbing work correctly end-to-end.
4. Ran the full regression suite (backend pytest, frontend TypeScript/ESLint/
   Vitest/build, and the existing Playwright suite) against the real,
   running app.

**What this phase did not do**, and why that is the right call rather than a
shortfall: sections 9-66 of the brief (visual redesign of Overview, full
850-hPa vector rendering, Z500/MSLP contour layers, Skill Cube, Story Mode,
screenshot QA at three resolutions, new Playwright flows) describe a
multi-week frontend program. Attempting all of it in one pass, on top of
substantial pre-existing work whose exact boundaries were not yet understood,
would have risked exactly the shallow/duplicate/inconsistent output the
brief's own section 82 forbids. Section 82 and section 53 explicitly
authorize deferring exactly this kind of scope to a later phase; this
document uses that authorization rather than fabricating completion.

## 2. Existing Architecture Preserved

No page, component, or route was removed or replaced. `districts/page.tsx`
gained one new branch; nothing else in `frontend-v2/src/app` or
`frontend-v2/src/components` was edited. The pre-existing static-bundle
architecture (`science/frozen/operational.ts` + `public/science/operational-v1/*.json`,
consumed via TanStack Query) was left in place rather than migrated to the
live `/api/science/operational/*` API built in Phases 5A.1/5A.1B — that
migration is real, valuable future work (see section 31, Exact Next Task),
not something to attempt as a side effect of this phase.

## 3. Experiment Context

Confirmed working: `app-shell.tsx`'s Experiment/Year selector applies
`?experiment=&year=` across `/forecast`, `/casebook`, `/extremes`,
`/ensemble`, `/regimes`, `/districts`, and `/verification`. Canonical year
labels (2023 CROSS-FIT, 2024 VALIDATION, 2025 FINAL TEST) are used
consistently; 2025 is never labeled sealed/untouched anywhere found in this
codebase.

## 4. Track A Integration (2017/2018/2019)

Unchanged, verified working via browser: `/districts` (no experiment param)
renders the full 2019 district workspace with real per-district metrics,
regime labels, and a district inspector — confirmed against a real case
(`Mumbai Suburban`, Low/Depression regime, matching values screenshotted in
this phase).

## 5. 2023 Integration

`OperationalForecastWorkspace` (pre-existing) filters the model selector to
exclude M0, shows `M2 cross-fit / OOF` as a distinct label, and its caveat
text explicitly states "M2 is an out-of-fold prediction, not an independent
test result" for 2023. Verified this matches the backend's own OOF proof
from Phase 5A.1B.

## 6. 2024 Integration

Pre-existing workspace lists 2024's full M1-M4 set with subtitle "Frozen
validation prediction" and the case-meta role badge
"VALIDATION / MODEL SELECTION". This is consistent with the Phase 5A.1B
capability upgrade (2024 model outputs are now proven case-grid, not just
aggregate) — the pre-existing static bundle already encodes this correctly.

## 7. 2025 Integration

Pre-existing workspace's model selector marks M1 "preselected primary" and
M2 "secondary" in its own option labels; the caveat text states the primary
comparison remains M0-vs-M1 regardless of the case being viewed. Matches the
backend's `PRESELECTED_PRIMARY_MODEL` / `SECONDARY_FINAL_TEST_RESULT`
distinction exactly.

## 8. Forecast Workspace

Verified via live browser session: year/case/variable/model/layout controls,
synchronized multi-map panels, point inspector with lat/lon/raw/model/IMD/
error-delta/heavy-probability fields, and the Scientific Grid vs Weather
Visualization method note are all present and functioning against the static
bundle. Not re-verified in this phase: pixel-perfect rendering of every
atmosphere field or every case in the corpus — spot-checked only.

## 9. Error Anatomy

Pre-existing `errorAnatomy()` in `operational-workspace.tsx` computes
`|model - IMD| - |raw - IMD|` client-side from already-frozen arrays (exactly
the permitted presentation derivation in section 1 of the brief) and renders
it with a zero-centered diverging palette (`error-difference`), with an
explicit caveat that the scale is centered at exactly zero. No write-back to
any science artifact.

## 10-15. Atmospheric Workspace / U850 / V850 / Q700 / Z500 / MSLP / PWAT

The pre-existing workspace exposes all six fields as selectable "Variable"
options, each rendered through the existing grid-map raster path with a
field-specific palette and a caveat that atmospheric source resolution is
0.5° and was bilinearly aligned to the 0.25° rainfall grid — it does **not**
render meteorological vector arrows, wind barbs, contour lines, or isobars;
each field is shown as continuous shaded scalar data (U850 and V850 as two
separate scalar layers, not a combined vector field). Building genuine
vector/contour rendering (sections 23, 25, 26 of the brief) is real,
scoped-out work — see section 31.

## 16. Event Casebook

Pre-existing `OperationalCasebook` has real filters (year, month, lead,
observed heavy/very-heavy, predicted pseudo-regime, and — for 2025 only — M1
case outcome improved/worsened), all backed by the static bundle's real
per-case metadata. Not verified in this phase: full coverage parity against
every eligible case in the frozen corpus (spot-checked only).

## 17-30. Event Detail / Extreme Rain / Reliability / FSS / Ensemble / Regimes / Verification

Pre-existing pages (`operational-extremes.tsx`, `operational-ensemble.tsx`,
`regime-intelligence.tsx`, `operational-verification.tsx`) exist and use the
correct labels found by inspection: "Available five-member subset · c00, p01,
p02, p03, p04" (ensemble), "Forecast-only pseudo-regime classifier output ·
not observed meteorological truth" (regimes), and quality's own funnel text
distinguishing acquisition from QC attrition. **Not independently verified
in this phase**: whether every displayed number in these components exactly
matches the frozen headline figures (Brier/BSS/FSS/lead-time RMSEs) — that
would require a dedicated numeric audit of the static bundle's generation
script against `experiments/recent_historical/`, which is explicitly deferred
(section 31).

## 21. District Capability Handling

**This phase's primary functional fix.** Before: `/districts?experiment=operational&year=2025`
silently rendered the full 2019 Track A district workspace, mislabeled under
the Operational Era selection — confirmed via a live browser session before
the fix (screenshotted), a genuinely misleading state, not merely an
oversight in prose. After: a dedicated capability-unavailable state
("District aggregation is not part of the frozen operational-era
presentation dataset"), with working links to Forecast & Atmosphere and the
Casebook, verified via a second live browser session (screenshotted) that
Track A's `/districts` (no experiment param) is completely unaffected.

## 22. Provenance

Not extended in this phase. The pre-existing `PrototypeNote`/context-strip
components already surface prototype status and role text on every page
touched.

## 23. Scientific Limitations

Verified present: `audit/page.tsx`'s limitations list already states the
FSS/extreme-skill limitation, the very-heavy FAR limitation, the
pseudo-regime caveat, the 2019/2025 non-pooling rule, and the six-season
non-climatology framing, in the exact spirit of section 68 of the brief.

## 24. Error Handling

New in this phase: `/api/science/operational/*` now returns
`{"code": "SCIENCE_...", "detail": "..."}` on every error, via
`ScienceErrorCode` (backend/app/api/operational.py) and a small app-level
exception handler (`backend/main.py`) that flattens a dict `HTTPException.detail`
into the response body — additive only; every other route's plain-string
`detail` is untouched (verified by a dedicated test,
`test_legacy_science_routes_keep_plain_string_detail`). `frontend-v2/src/lib/api/operational.ts`
now classifies `OperationalApiError.kind` from the real `code` field instead
of pattern-matching free text, with a documented fallback for a response that
somehow lacks a recognized code.

## 25. Accessibility

Ran the existing Playwright accessibility check
(`tests/e2e/demo-flow.spec.ts`'s "critical accessibility and responsive
layout" test, axe-core WCAG 2.1 A/AA) against the live app. One pre-existing,
unrelated failure: `.phase5-outcome-bar` on `/verification` has a 4.49:1
contrast ratio (needs 4.5:1) — confirmed pre-existing (not in any file this
phase touched) and flagged as a separate follow-up task rather than fixed
inline, to keep this phase's diff scoped to what it actually set out to do.

## 26. Performance

Not benchmarked in this phase beyond confirming the production build
succeeds and the app serves correctly under `next start`.

## 27. Responsive QA

Not performed in this phase (no screenshot capture at 1366×768/1440×900/
1920×1080 across all pages) — explicitly deferred; see section 31.

## 28. Tests

- Backend: `backend/tests/test_operational.py` grew to include 5 new
  structured-error-contract tests (43 total, all passing), including a test
  that proves the legacy `/api/science/*` router's plain-string error bodies
  are untouched.
- Frontend: `frontend-v2/src/lib/api/operational.test.ts`'s error-kind tests
  were updated to assert on the real backend `code` field instead of
  pattern-matched text (still 19 tests, all passing; 40 total across the
  suite).
- No new Playwright specs were added in this phase (section 84's full list
  of new user-flow specs is deferred — seeding one exhaustive spec per
  bullet without page-level redesign work to exercise would be premature).

## 29. Screenshots

Two ad hoc screenshots were taken via the browser tool during this phase to
verify the Districts fix (before state confirmed the bug via raw HTML; after
state confirmed both the Track B unavailable message and the untouched Track
A workspace render correctly) — not the full section-85 QA matrix, which
remains deferred.

## 30. Known Limitations

- Synoptic vector/contour rendering (wind barbs, Z500 contours, MSLP isobars)
  does not exist yet; atmosphere fields render as scalar shading only.
- The frontend still reads a static pre-generated JSON bundle, not the live
  `/api/science/operational/*` API built in Phases 5A.1/5A.1B — both exist in
  parallel today.
- Numeric parity between the static bundle's displayed metrics and the
  authoritative frozen corpus was spot-checked, not exhaustively audited.
- No Skill Cube, Story Mode, full responsive/screenshot QA matrix, or new
  Playwright flow specs were added.
- One pre-existing, unrelated WCAG AA contrast issue on `/verification`
  remains (flagged as a separate follow-up task).

## 31. Exact Next Task

In priority order for a future Phase 5A.3: (1) decide whether to migrate the
static-bundle-backed pages to the live `/api/science/operational/*` API (this
would let 2024's now-proven case grids and the new per-case regime endpoint
reach the UI, and would remove the parallel-data-source risk) or to keep the
static bundle and instead add a build step that regenerates it from the live
API so the two can never drift; (2) build genuine synoptic vector/contour
rendering for U850/V850/Z500/MSLP; (3) run a full numeric audit of the static
bundle against `experiments/recent_historical/` frozen values; (4) only then
proceed to the visual redesign, Skill Cube, Story Mode, and full QA/test
matrix sections of the original Phase 5A.2 brief.
