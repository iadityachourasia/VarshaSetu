# Final Submission Checklist — Phase 5B

Checked against this repository's own gates (`docs/14_ACCEPTANCE_CRITERIA.md`
"UI Gate" and "Demo Gate") and this phase's brief, not a generic checklist.
Each item states what was actually verified, where, and by what evidence —
consistent with this project's rule against claiming a check ran when it
did not.

## Full regression results (Task 33, this session, clean production build)

- **TypeScript**: `npm run typecheck` — clean, 0 errors.
- **ESLint**: `npm run lint` — 0 errors, 1 pre-existing warning unrelated to
  this phase (`app-shell.tsx`'s `window.location.assign` in
  `ExperimentContextControl`, predates this phase).
- **Vitest**: `npm run test` — **73 of 74 tests passed**. The one failure
  (`communication.test.ts`'s displayed-value-vs-frozen-artifact hash check)
  fails with `ENOENT` on `experiments/recent_historical/.../FINAL_TEST_RESULT.json`
  — that source file is gitignored and genuinely absent in this sandbox,
  confirmed pre-existing (the test predates this phase's first commit).
- **Production build**: `next build` — clean, all 12 routes compile.
- **Playwright** (`npx playwright test`, full suite, real headless
  Chromium, clean build): **13 of 35 tests passed** — see the itemized
  breakdown below.

## UI Gate (`docs/14_ACCEPTANCE_CRITERIA.md`)

- [x] No fake scientific values — confirmed by this phase's secret/dead-UI
  scan (no hardcoded metrics found in `frontend-v2/src`) and by every page
  reading either a live API call or a frozen, hash-pinned JSON artifact.
- [x] Every displayed scientific value has a backend/artifact source — see
  `docs/presentation/ROUTE_INVENTORY.md` for the exact source of each
  route's data.
- [x] Historical vs. operational modes clearly labeled — "Historical
  prototype" appears in the header on every page; every page's copy
  distinguishes Track A (2019) from Track B (2025) explicitly.
- [x] Threshold accumulation visible — Heavy (≥64.5mm) / Very Heavy
  (≥115.6mm) per 24h thresholds are stated on Extreme Rain and Verification.
- [x] Source/model/lead visible — case cards and the model ladder table show
  initialization, lead, and model identity throughout.
- [x] Raw/corrected/observed comparison uses consistent units — all in mm,
  same target grid, confirmed by direct source reading of the comparison
  components.
- [x] Judge can find mandatory metrics quickly — Overview links directly to
  Verification and Forecast; Story Mode's 12-scene sequence surfaces every
  mandatory number in order.

## Demo Gate (`docs/14_ACCEPTANCE_CRITERIA.md`)

- [x] At least one held-out case selected — three official cases now
  documented (`docs/presentation/OFFICIAL_DEMO_CASES.md`): 2019 anchor,
  2025 official, 2025 backup.
- [x] Replay from stored artifacts — every route reads a frozen artifact or
  a live API backed by one; nothing computes a fresh result at request
  time.
- [x] Aggregate held-out report shown — Verification page shows both
  tracks' aggregate model-comparison tables.
- [x] Event counts shown — Heavy/Very-Heavy observed-cell counts appear on
  case cards and in Story Mode's "2019 Benchmark"/"2025 Final Test" scenes.
- [x] Known limitations shown — the extreme-skill limitation, high FAR, and
  the pseudo-regime caveat are all first-class UI content, not buried.
- [x] Offline fallback for demo artifacts prepared — `withStaticFallback`
  (`frontend-v2/src/lib/data-source.ts`) backs every Track B client
  component; verified this session with a real headless-Chromium run
  against a genuinely unreachable backend (`operational-fallback.spec.ts`).
- [x] No external dependency that can silently break the entire
  demonstration — the map-tile preflight already distinguishes
  READY / READY_WITH_OFFLINE_MAP / BLOCKED (`scripts/demo/preflight-demo.ps1`);
  this phase additionally fixed two pages (`/verification`, `/methodology`)
  that previously went fully blank on a Track A outage even though most of
  their content did not depend on it (see `docs/presentation/ROUTE_INVENTORY.md`).

## This phase's own deliverables

- [x] `docs/presentation/OFFICIAL_DEMO_CASES.md` — official/backup 2025
  cases and the preserved 2019 anchor, with non-cherry-picked selection
  reasoning.
- [x] `?demo=official` preset on `/forecast` — verified end-to-end with
  real headless Chromium.
- [x] Presentation View (collapsible chrome, "P" shortcut, Reset Demo link)
  — verified end-to-end with real headless Chromium, including the
  keyboard-shortcut-ignored-while-typing case.
- [x] Story Mode reordered to the official 12-scene sequence — verified
  end-to-end with real headless Chromium.
- [x] `scripts/demo/preflight-demo.ps1` extended with Track B checks and a
  three-state result — code-complete, structurally verified (brace/paren/
  quote balance); **could not be executed** in this sandbox (no PowerShell
  interpreter; no reachable backend on either track). Needs a real run on
  the Windows dev machine before the actual demo day.
- [x] `docs/presentation/ROUTE_INVENTORY.md` — honest per-route
  classification, two real reliability bugs found and fixed
  (`/verification`, `/methodology`).
- [x] `docs/presentation/FINAL_PPT_FACTS.md`, `FINAL_ARCHITECTURE_DIAGRAM_SPEC.md`,
  `FINAL_DEMO_NARRATION.md`, `JUDGE_QA.md` — this document's companions.

## What this session could not do (and why) — needs the real dev machine

- **Screenshot pack**: this sandboxed container has no reachable Track A or
  Track B backend (a real, unbypassed hash-integrity failure on Track A's
  checked-out manifest; Track B's `experiments/recent_historical/` corpus is
  gitignored and absent here). A screenshot pack built from this
  environment would either show `ErrorState` on every Track A page or would
  require fabricating what a working page looks like — both are worse than
  not producing the pack. **Action required on the real machine**: run
  `scripts/demo/start-demo.ps1`, confirm `preflight-demo.ps1` reports
  `DEMO_PREFLIGHT_RESULT=READY`, then capture real screenshots per
  `docs/78_SIH_RECORDING_SHOT_LIST.md`'s shot list.
- **Recording-machine QA and viewport/performance measurement**: needs the
  actual presentation laptop, its GPU/browser, and real network conditions.
  Not something a sandboxed container's `next start` timing represents
  faithfully — see `demo-performance.spec.ts` for the assertions to re-run
  there.
- **Live PowerShell execution of the extended preflight script**: no
  PowerShell interpreter exists in this Linux sandbox. The script was
  verified for structural correctness (balanced braces/parens/quotes) but
  never actually executed.
- **The full Playwright suite was actually run this session** (Task 33)
  against a clean production build, with a real headless Chromium, to get
  a precise pass/fail count rather than leaving it as an estimate: **13 of
  35 tests passed**. All 13 passes are exactly the tests that need no live
  backend (`demo-preset-and-presentation-view.spec.ts`,
  `story-mode-and-audit.spec.ts`, `operational-fallback.spec.ts`'s
  route-mocked specs, `operational-accessibility-responsive.spec.ts`'s
  mocked-data specs). All 22 failures are exactly the tests that need a
  real backend and the real `experiments/` corpus
  (`operational-track-b.spec.ts`, `operational-extreme-verification.spec.ts`,
  `demo-flow.spec.ts`, `release-consistency.spec.ts`, `mapping.spec.ts`,
  `demo-performance.spec.ts`) — each failure was individually inspected and
  traces to `ECONNREFUSED 127.0.0.1:8000` (Track A) or the equivalent
  missing Track B corpus, not to a code defect. One failure
  (`operational-extreme-verification.spec.ts`'s "Model selection story"
  assertion) was specifically checked to confirm it is not a side effect of
  this session's `/verification` fix — it isn't; that test exercises the
  `OperationalVerification` client component, which this session did not
  touch. **Zero regressions from this session's changes.** Run the full
  suite again on the real machine before demo day; a live backend should
  turn most or all of these 22 green, and any that don't are new evidence
  to investigate, not an expected outcome.

## Explicitly out of scope for this freeze phase (per the Phase 5B brief)

- No model retraining, recalibration, threshold change, or QC change.
- No modification to `FINAL_TEST_RESULT`/`FINAL_TEST_READY` or any other
  frozen Phase 2/4 artifact.
- No bypassing or masking of the confirmed Track A `SCIENCE_INTEGRITY_FAILURE`
  — it remains genuinely unresolved and is reported, not hidden.

## Decision inputs for `docs/99_FINAL_SIH_DEMO_FREEZE.md`

The two genuine reliability bugs found and fixed this phase
(`/verification`, `/methodology`) argue for **not** blocking on them — they
are fixed and verified. The unexecuted-in-this-sandbox items above
(screenshot pack, PowerShell preflight run, five backend-dependent
Playwright specs, recording-machine QA) are real gaps that require the
actual dev machine and cannot be honestly marked done from here. This
points toward `SIH_DEMO_READY_WITH_MINOR_NOTES`, contingent on those items
being completed on the real machine before demo day — see `docs/99` for the
final decision once all Phase 5B tasks are complete.
