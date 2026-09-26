# Phase 5B — Final SIH Demo Freeze

## 1. Executive summary

This phase froze VarshaSetu into a judge-ready demonstration package: no
new science, no new major features, only bug fixes, presentation polish,
demo reliability, and documentation. Two genuine reliability bugs were
found and fixed (`/verification`, `/methodology` each went fully blank on
a Track A backend outage despite most of their content not needing it). No
model, calibration, threshold, QC, dataset, or frozen artifact was touched.
The full regression suite was run against a clean production build; every
failure traces to this sandbox's absent backend/corpus, not to a defect
introduced this phase.

**Decision: `SIH_DEMO_READY_WITH_MINOR_NOTES`** (see §9 for the exact
conditions).

## 2. Scope discipline

Per the Phase 5B brief, this phase did not: retrain, recalibrate, or change
any threshold, QC rule, or model selection; modify `FINAL_TEST_RESULT`,
`FINAL_TEST_READY`, or any frozen Phase 2/4 artifact; bypass or mask the
confirmed Track A `SCIENCE_INTEGRITY_FAILURE` (it remains genuinely
unresolved and reported, never hidden behind a fallback); or begin a new
feature-development cycle. Every change below is a bug fix, a presentation
feature explicitly requested by this phase's brief, or documentation.

## 3. What was built this phase

- **Official demo cases** (`docs/presentation/OFFICIAL_DEMO_CASES.md`):
  Track B official (`20250714_day2_24h`) and backup
  (`20250903_day2_24h`) cases selected for complete data availability and a
  near-neutral case-level RMSE delta — explicitly not the best-performing
  case. The existing Track A anchor (`20190802T000000Z_day3_24h`) is
  preserved unchanged.
- **`?demo=official` preset** on `/forecast` — a real redirect to the exact
  query parameters a presenter would type by hand; never bypasses data
  loading or constructs a result object. Verified end-to-end with real
  headless Chromium.
- **Presentation View** — collapsible sidebar/header chrome, a "P"
  keyboard shortcut (guarded against firing while typing in a form
  control), and a persistent "Reset Demo" link. A real placement bug was
  found and fixed during this work: the Reset Demo link was initially
  placed inside `.sidebar-foot`, which a pre-existing `@media` breakpoint
  already hides at common demo viewports (1440×900 and below) — caught by
  a failing Playwright test, not by inspection, and fixed by relocating it
  to `.header-actions`. Verified end-to-end with real headless Chromium.
- **Story Mode reordered** to the official 12-scene sequence (The Problem
  → Two Experiment Tracks → Forecast Case → Correction vs. Observation →
  Synoptic Context → Pseudo-Regime Architecture → Extreme Probability →
  2019 Benchmark → 2025 Final Test → Extreme-Skill Limitation → Data
  Quality → Reproducibility), each scene trimmed to one message/one
  visual/one takeaway. Verified end-to-end with real headless Chromium.
- **`scripts/demo/preflight-demo.ps1` extended** with Track B (2025)
  checks and a three-state `DEMO_PREFLIGHT_RESULT`
  (`READY`/`READY_WITH_OFFLINE_MAP`/`BLOCKED`). Code-complete and
  structurally verified (brace/paren/quote balance); **could not be
  executed** in this sandbox (no PowerShell interpreter, no reachable
  backend on either track) — must be run on the real dev machine before
  demo day.
- **Route inventory audit** (`docs/presentation/ROUTE_INVENTORY.md`) —
  every one of the 12 routes classified WORKING or
  WORKING_WITH_LIMITATION with evidence; nothing landed in NOT_FOR_DEMO.
  This audit is what surfaced the two reliability bugs below.
- **Two reliability bugs found and fixed**:
  - `/verification` previously combined the Track A fetch and the entire
    Track B section behind one `Promise.all().catch()` — a Track A outage
    blanked the whole page, including Track B content that never needed
    Track A. Now Track A's fetch is independent; on failure only its own
    section shows a scoped notice while the 2025 benchmark and the 7-tab
    `OperationalVerification` component still render fully.
  - `/methodology` was ~90% static prose that never called an API, yet the
    whole page was gated behind one small `/status` call. Now the static
    content always renders; only the two small live-data strips degrade.
  - Both fixes were verified against a clean rebuild with the Track A
    backend genuinely unreachable, confirming the exact intended
    degradation (not just that the page didn't crash).
- **Judge-ready presentation deliverables** (`docs/presentation/`):
  `FINAL_PPT_FACTS.md` (sourced numbers, sanctioned vocabulary),
  `FINAL_ARCHITECTURE_DIAGRAM_SPEC.md` (what's actually built, distinct
  from the aspirational target in `docs/04`), `FINAL_DEMO_NARRATION.md`
  (90s/2min/30s scripts aligned scene-for-scene with Story Mode),
  `JUDGE_QA.md` (anticipated questions with honest, sourced answers).
- **README finalized** — added the previously entirely-missing
  `frontend-v2` documentation (setup, dev commands, demo launcher,
  documentation map), while leaving the legacy-CSV blocker section and
  every scientific number untouched and verified consistent.
- **Secret scan / dead-UI sweep** — no secrets, no hardcoded scientific
  values, no debug console output found in `frontend-v2/src`. Legacy
  `print()` statements in the quarantined `backend/app/services/pipeline.py`
  were left untouched as explicitly out-of-scope legacy code.

## 4. Regression evidence

Full detail in `docs/presentation/FINAL_SUBMISSION_CHECKLIST.md`. Summary:

| Check | Result |
|---|---|
| TypeScript (`npm run typecheck`) | Clean, 0 errors |
| ESLint (`npm run lint`) | 0 errors, 1 pre-existing unrelated warning |
| Vitest (`npm run test`) | 73 / 74 passed — the 1 failure is a pre-existing, environment-only `ENOENT` on a gitignored corpus file, confirmed to predate this phase |
| Production build (`next build`) | Clean, all 12 routes compile |
| Playwright, full suite (real headless Chromium, clean build) | 13 / 35 passed — every one of the 13 passes is a test that needs no live backend; every one of the 22 failures traces to `ECONNREFUSED` (Track A) or the missing `experiments/` corpus (Track B), individually inspected, zero regressions from this phase |

## 5. What this session could not verify directly (environment constraint)

Unchanged from every prior phase's documented finding: this sandboxed
container has neither a runnable Track A backend (a real, unbypassed
SHA-256 mismatch on the checked-out `artifact_manifest.json` — investigated
and correctly left unresolved, never bypassed) nor the Track B
`experiments/recent_historical/` corpus (gitignored, absent). This phase's
own new work — the extended preflight script's Track B checks, and the 22
Playwright tests that need a real backend — could not be executed here for
the same reason. This is a pre-existing environment gap, not something
this phase introduced or could resolve from within this sandbox.

## 6. What still needs the real dev machine before demo day

1. Run `scripts/demo/preflight-demo.ps1` for real; confirm
   `DEMO_PREFLIGHT_RESULT=READY` (or `READY_WITH_OFFLINE_MAP` if the
   external map-tile provider is unreachable that day).
2. Re-run the full Playwright suite; the 22 tests that failed here for lack
   of a backend should turn green — any that don't are new evidence to
   investigate, not an expected outcome.
3. Capture the real screenshot pack per
   `docs/78_SIH_RECORDING_SHOT_LIST.md`, using only real, rendered
   application screens (no dev consoles, skeletons, broken tiles, or fake
   data — this could not be produced honestly from this sandbox).
4. Do a live run-through of `docs/presentation/FINAL_DEMO_NARRATION.md`'s
   90-second script on the actual presentation hardware, timing it for
   real (target 60-90s, hard ceiling 120s).
5. Confirm Presentation View and the Reset Demo link at the actual
   projector/recording resolution.

## 7. Risks and honest caveats

- The extended preflight script and 22 backend-dependent Playwright specs
  are code-complete and believed correct (written against this session's
  own verified source, following the same patterns as the specs that did
  run and pass), but **unexecuted** — §6 items 1-2 are not optional
  pre-demo steps, they are the actual proof these work.
- If the real dev machine's Track A backend still shows the manifest hash
  mismatch this session found, that is a genuine, separate blocker to
  resolve before relying on any Track A page — it must not be bypassed.
- The near-neutral 2025 official demo case was chosen for honesty, not for
  visual drama — a presenter unfamiliar with `docs/presentation/OFFICIAL_DEMO_CASES.md`'s
  reasoning might be tempted to switch to a more "impressive" case; doing
  so would undercut the project's own stated commitment to non-cherry-picked
  demonstration.

## 8. Documentation updated this phase

`docs/00_INDEX.md`, `README.md`, and the seven new files under
`docs/presentation/` (`OFFICIAL_DEMO_CASES.md`, `ROUTE_INVENTORY.md`,
`FINAL_PPT_FACTS.md`, `FINAL_ARCHITECTURE_DIAGRAM_SPEC.md`,
`FINAL_DEMO_NARRATION.md`, `JUDGE_QA.md`, `FINAL_SUBMISSION_CHECKLIST.md`).
This file.

## 9. Decision gate

**`SIH_DEMO_READY_WITH_MINOR_NOTES`**

The product, presentation layer, and documentation are ready for the
judge-facing demo, conditional on completing the five real-machine steps in
§6 before demo day — none of which is a code change, all of which are
verification steps this sandboxed environment cannot perform. No scientific
claim, model, or frozen artifact changed this phase. The two reliability
bugs found were fixed and verified; no other defect was found in the 12-route
audit. This is not `SIH_DEMO_READY` outright only because §6's real-machine
verification has not yet happened anywhere — it is not a code-quality
reservation.

## 10. Next task after this freeze

Per the Phase 5B brief: **stop all product development.** The only
legitimate follow-on work is completing §6's real-machine verification
steps and, if any of them surfaces a genuine defect, a narrowly scoped fix
for that specific defect — not a new feature-development cycle.
