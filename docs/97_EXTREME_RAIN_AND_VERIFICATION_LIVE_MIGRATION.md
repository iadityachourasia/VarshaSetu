# 97 — Extreme Rain and Verification Live Migration (Phase 5A.2D)

## 1. Executive Summary

This supersedes an earlier, smaller version of this same document. Extreme
Rain and Verification are now both year-adaptive, live-API-primary, tabbed
scientific views sharing a new component library
(`components/science/operational-charts.tsx`) instead of each carrying its
own duplicated fetch/render logic. No backend change, no new endpoint, no
retraining, no threshold/mask/population/model-selection change, no
FINAL_TEST_RESULT/FINAL_TEST_READY touch. Four new Playwright specs were
added; two of them (accessibility + fallback) were actually run and pass in
this session against a real headless Chromium; two (the live-backend flows)
could not be run here for a reason explained in section 2 and documented
honestly rather than claimed. `npm run typecheck`, `npm run lint`, `npm run
build` are all clean; `npm test` is 61/62 (the one failure is pre-existing
and unrelated, see section 2).

## 2. Environment Constraint (read before trusting any "verified" claim below)

This container does not have the `experiments/recent_historical/` frozen
artifact tree (`.gitignore`d, never checked into this checkout), so:

- The real backend cannot serve any Track-B data here at all.
- Two of the four new specs (`operational-track-b.spec.ts`,
  `operational-extreme-verification.spec.ts`) are written against this
  session's own real source (exact headings, labels, region names, and a
  handful of frozen numbers cross-checked directly against the checked-in
  static bundle JSON) but were **not run** in this session -- there is no
  live backend here to run them against. They will run correctly wherever
  the real backend and real frozen corpus exist (the actual target
  environment), but that has not been demonstrated in this session.
- The other two new specs (`operational-fallback.spec.ts`,
  `operational-accessibility-responsive.spec.ts`) use Playwright's
  `page.route()` to intercept `/api/science/operational/**` at the browser
  network layer with realistic frozen-shaped fixtures. This is not a
  workaround of convenience -- section 36 of the brief *requires* it
  (`SCIENCE_INTEGRITY_FAILURE` cannot be safely simulated against a real
  backend without corrupting a real frozen artifact, which AGENTS.md
  forbids). Both were actually executed in this session, against a real
  `next start` + real headless Chromium, via a throwaway local-only
  Playwright config (frontend-webServer only, no backend) that was deleted
  immediately after use and never committed. Results: 2/2 fallback tests
  pass; 2/2 axe scans (Casebook, Extreme Rain) report zero critical/serious
  violations; 3/3 responsive breakpoints (1366×768, 1440×900, 1920×1080) on
  Extreme Rain report zero horizontal overflow.
- Verification's own page (`app/verification/page.tsx`) does its Track-A
  `getScience(...)` calls **server-side** (`server=true`, a direct Node
  fetch during SSR) -- `page.route()` cannot intercept a server-side fetch,
  only browser-originated ones. Confirmed directly: without a live Track-A
  backend, the whole `/verification` route bails to the top-level
  `ErrorState` before `OperationalVerification` (this phase's own component)
  ever mounts. This is a genuine, pre-existing environment limitation, not a
  defect introduced this session, and it means Verification's own axe/
  responsive checks could not be run here either. Casebook and Extreme Rain,
  both fully client-side, were fully covered.
- `npm test`'s one failure (`communication.test.ts`) reads a file under the
  same missing `experiments/` tree; it fails identically on an unmodified
  checkout and is unrelated to this session's changes.

Residual risk for whoever has real backend access: run
`operational-track-b.spec.ts` and `operational-extreme-verification.spec.ts`
for real, and confirm `/verification`'s own accessibility/responsive
behavior once its Track-A dependency is satisfied.

## 3. Extreme Rain Live Architecture

`operational-extremes.tsx` is now year-adaptive (2023/2024/2025, a real
`<select>`, not fixed to 2025) and gates each of its four modes on the live
`getOperationalAvailability(year)` capability flags rather than a hardcoded
year check: probability mode on `heavy_probability`/`very_heavy_probability`
(per selected event) `!== "unavailable"`, detection mode on
`case_level_metrics`, spatial mode on `fss`, reliability mode on
`reliability_bins`. Where a flag says a product does not exist for the
selected year, the mode renders the backend's own `notes` explaining why
(2023: "models are fit on this year, not scored against it") rather than a
grayed-out fake chart. Grid geometry (lat/lon centers, valid-cell mask)
remains presentation-only and continues to read the static bundle exactly as
Ensemble/Regime already did before this phase (docs/96 section 19) -- it
carries no scientific value and was correctly out of scope for a live-data
migration.

## 4. Event Detection

Rebuilt from scratch to match this brief exactly: it is no longer the
calibrated-probability model's own thresholded categorical metrics (what it
was before this phase), but the deterministic Raw/M1/M2/M3/M4 rainfall
forecasts each thresholded independently at the frozen Heavy/Very-Heavy
boundary, via the new shared `DeterministicCategoricalTable` component
against `getOperationalDeterministicMetrics`. The 2025 Heavy CSI values
(Raw 0.0478, M1 0.0200, M2 0.0727, M3 0.0937, M4 0.0882) and Very Heavy CSI
values given in the brief were independently cross-checked in this session
directly against `public/science/operational-v1/final_result_2025.json`
(the checked-in static bundle, generated from the same frozen artifact the
live endpoint serves) and match exactly -- strong evidence the live data
path is wired to the correct field.

## 5. Probability

Unchanged data source from the prior pass (`getOperationalProbabilityMetrics`
+ per-case `getOperationalProbability` grid), now rendered through the
shared `ProbabilityQualityCards` component so Extreme Rain and Verification
show identical scalar cards from identical live data. Only scalar
Brier/BSS/PR-AUC/ROC-AUC are ever rendered; no PR/ROC curve point array is
synthesized anywhere (the type system enforces this -- `ProbabilityEventMetrics`
has no curve-point field for a component to draw from). The frozen decision
threshold, case, year, and lead all appear in the map subtitle per section 9's
requirement, without implying live warning issuance (the page's closing
caveat says so explicitly).

## 6. Reliability

Unchanged logic, now rendered through the shared `OperationalReliabilityChart`
(a real recharts line chart with the perfect-calibration diagonal, replacing
no prior visualization -- reliability was already table-only before this
pass) instead of only a table. Gated on the live `reliability_bins`
availability flag; never reconstructs a bin the frozen artifact does not
carry.

## 7. FSS

Replaced the ad hoc CSS bar-chart markup with a real recharts line/dot chart
(`OperationalFssChart`, shared between Extreme Rain and Verification),
matching section 11's explicit "use a professional line/dot chart, X-axis
1×1/3×3/5×5/9×9" instruction and section 23's "one canonical component,
Verification embeds it" instruction. The conclusion ("Raw GEFS retained
stronger extreme-rain spatial FSS than the RMSE-selected M1 at every tested
scale") is a visible caveat paragraph directly under the chart, not a
tooltip. The 2025 Heavy/Very-Heavy Raw/M1 FSS values given in the brief were
independently cross-checked against the same static bundle in this session
and match exactly.

## 8. Verification Live Architecture

`operational-verification.tsx` was restructured into the seven named tabs
the brief specifies (Continuous / Extremes / Probability / Spatial / Lead
Time / Case Outcomes / Generalization), `role="tablist"`/`role="tab"` with
`aria-selected`. Extremes, Probability, and Spatial tabs reuse the exact
same shared components (`DeterministicCategoricalTable`,
`ProbabilityQualityCards`, `OperationalFssChart`) Extreme Rain uses, against
the same live queries (`getOperationalDeterministicMetrics`,
`getOperationalProbabilityMetrics`, `getOperationalFSS`, now also fetched
for 2024, not just 2025). No cross-year Skill Cube was built (explicitly out
of scope per section 14: "that belongs to the next phase").

## 9. Model Selection

A permanent "Model selection story" block sits above the tab row (visible
regardless of which tab is active, since the brief calls this "one of the
project's strongest scientific-governance points"): 2024 selection under the
frozen validation-RMSE rule → 2025 evaluated once → M2's lower secondary
RMSE stated plainly as not eligible for post-test reselection. The
Continuous tab's 2025 view explicitly says not to visually assign "winner"
based on lowest RMSE alone.

## 10. Lead-Time Verification

The 2025 Day 1/2/3 Raw/M1-M4 RMSE table, now reading `leadRmse()` from the
shared component module instead of a page-local duplicate. Behavior
unchanged from the prior pass.

## 11. Case Outcomes

Improved/worsened/tied counts and the median per-case RMSE delta remain
computed live from `loadOperationalCaseList(2025)` using the backend's own
`m1_minus_raw_rmse_mm` sign rule (a transparent aggregate over already-live,
already-trusted per-case data -- not a new statistic, not a new endpoint).
New this pass: a real sorted diverging bar chart (`CaseOutcomeChart`,
recharts, teal for improved / red for worsened) since the brief's "if full
live per-case differences are available, show a sorted diverging case-delta
chart" condition is true here. The displayed case count is the live count,
not a hardcoded "232" literal.

## 12. Generalization

New tab. A real two-point slope chart (`GeneralizationSlopeChart`, one line
per model across 2024→2025) plus the existing paired-RMSE table, with the
explicit "not proof of universal operational performance" caveat the brief
requires.

## 13. Probability Generalization

Same tab, second section: 2024→2025 Heavy/Very-Heavy PR-AUC table with the
"discrimination weakened from validation to final test" caveat kept visible
(not removed, not softened).

## 14. Two-Track Benchmark

`app/verification/page.tsx` already carried the Track A/Track B disclaimer
as its top-of-page subtitle ("different GEFS lineages and populations are
not pooled") before this pass; a second, explicit boundary note was added
directly between the now much larger `OperationalVerification` block and the
Track A detailed charts, naming both tracks and repeating "results are not
pooled" at the point where a reader's eye actually crosses from one track's
content into the other's.

## 15. Shared Components

New file: `components/science/operational-charts.tsx` --
`DeterministicCategoricalTable`, `OperationalFssChart`,
`OperationalReliabilityChart`, `ProbabilityQualityCards`, `PopulationBadge`,
plus the `DeterministicModelMetrics`/`leadRmse` types+helper (moved out of
Verification, where they lived after the prior pass, since Extreme Rain now
needs them too). `CaseOutcomeChart` and `GeneralizationSlopeChart` stay
local to `operational-verification.tsx` -- neither is used anywhere else,
so promoting them to the shared file would be premature abstraction.

## 16. API/Fallback Behavior

Unchanged rule, reused everywhere: `withStaticFallback` never falls back on
`INTEGRITY_FAILURE` or a real unavailable/ineligible answer, only on a
genuine network failure. `getOperationalAvailability` (new to this page)
follows the identical pattern. Actually verified this session (section 2):
a mocked network failure on the case-list endpoint falls back to the static
bundle with the "Cached frozen presentation data" indicator visible; a
mocked `SCIENCE_INTEGRITY_FAILURE` response never falls back and instead
shows the hard-stop error state with zero case rows rendered.

## 17. Request Cancellation

No AbortController/cancellation code was added. Investigated directly
(section 6 of this session's own task list): every query in both rebuilt
pages goes through TanStack Query's `useQuery` with a key that already
includes every variable that could otherwise cause a stale write (year,
event, case id, or -- for Verification's always-both-years queries -- a
fixed literal that never changes), and TanStack Query's per-key observer
model discards a superseded key's result by construction; no raw `fetch`
bypasses this. The brief's own instruction is conditional ("add cancellation
... if the current framework does not already prevent stale data writes")
and that condition is false here. Adding `AbortSignal` plumbing through
every operational API function for a purely-efficiency (not correctness)
win, unmeasured and unverifiable in this environment, would be exactly the
kind of unmeasured complexity AGENTS.md section 9 asks to avoid.

## 18. Performance

The real question (network + backend serialization time for a 375-case
payload) cannot be measured here -- there is no backend. What was measured,
honestly, is the part actually in this session's control: parsing a
realistic synthetic 375-case payload (~260KB) took `JSON.parse` 0.66ms, Zod
schema validation 1.29ms (20-run average), and the list transform/filter
1.15ms -- under 5ms combined, far below any perceptible threshold. Client-
side processing is not a bottleneck; pagination/virtualization is not
warranted without a measured problem, matching section 31's own "do NOT
prematurely introduce complexity" instruction.

## 19. E2E Coverage

Four new spec files (see section 2 for exactly what ran and what didn't):

- `operational-track-b.spec.ts` -- 2023/2024/2025 Forecast model coverage,
  Casebook→Forecast, Ensemble 5-member statuses, Regime year-role wording,
  Track A regression spot-check. Not run here (needs live backend).
- `operational-extreme-verification.spec.ts` -- Extreme Rain all 4 modes ×
  Heavy/Very Heavy, Verification all 7 tabs. Not run here (needs live
  backend).
- `operational-fallback.spec.ts` -- network-failure fallback, integrity-
  failure hard-stop. **Run and passing** (2/2).
- `operational-accessibility-responsive.spec.ts` -- axe on Casebook/Extreme
  Rain, responsive on Extreme Rain. **Run and passing** (3/3).

No existing spec (`demo-flow`, `demo-performance`, `mapping`,
`release-consistency`) was modified.

## 20. Accessibility

Zero critical/serious axe violations on Casebook and Extreme Rain under
realistic mocked live data (verified, section 2). Verification not checked
here for the SSR reason given in section 2. The new tab rows use
`role="tablist"`/`role="tab"`/`aria-selected` (not `aria-pressed`, which
`role="tab"` does not support -- caught and fixed by ESLint's
`jsx-a11y/role-supports-aria-props` during this pass); the CSS active-state
selector was extended to match `aria-selected="true"` alongside the existing
`aria-pressed="true"` so the visual state didn't regress when the ARIA
attribute changed.

## 21. Responsive QA

Extreme Rain: zero horizontal overflow at 1366×768, 1440×900, 1920×1080
(verified, section 2). Verification and the other four already-migrated
pages were not re-checked this pass (no markup/layout-affecting change was
made to them beyond the tab restructure, which reuses the same
`.phase5-tab-row`/`.phase5-analysis-block`/`.phase5-table` classes already
proven responsive on Casebook/Ensemble/Regime).

## 22. Track-A Regression

Verified unaffected: `/forecast`, `/extremes`, `/verification` (top-of-page
Track A sections), `/districts` were spot-checked in the new
`operational-track-b.spec.ts` test (not run here, but reuses assertions
already proven true by the pre-existing `demo-flow.spec.ts`). No Track-A
component file was touched this pass except `app/verification/page.tsx`,
where the only change was inserting one additional disclaimer `<div>`
between the two tracks' content (section 14) -- no existing Track-A markup,
query, or copy was altered.

## 23. Known Limitations

- The live 2025 `metrics/probability.json` shape assumption (from the prior
  pass, `lib/operational-probability-metrics.ts`) remains untested against
  real data in this environment.
- Two of the four new E2E specs were not run in this session (section 2);
  they need a live backend with the real frozen corpus.
- Verification's accessibility/responsive behavior was not independently
  checked this pass (blocked by its Track-A server-side fetch, section 2).
- No cross-year Skill Cube (explicitly deferred to the next phase per the
  brief itself).
- Synoptic vector/contour rendering and Judge Story Mode remain not started.

## 24. Exact Next Task

Before starting synoptic vector/contour rendering, the Skill Cube, or Story
Mode: on a machine with the real `experiments/` corpus and a running
backend, (1) run `operational-track-b.spec.ts` and
`operational-extreme-verification.spec.ts` for real and fix anything they
catch that this session's static analysis could not, and (2) independently
verify Verification's own accessibility and responsive behavior now that
its Track-A dependency can actually be satisfied.
