# 100 — Real-Machine Verification of the Cloud Session's Branch (`master-3xhx5v`)

## 1. Purpose

The cloud session that produced Phase 5A.2D/5A.3/5B (`docs/97`, `docs/98`,
`docs/99`) worked in a sandbox without the `experiments/recent_historical/`
corpus and without a runnable Track A backend, so it repeatedly and honestly
flagged large sections of its own work as code-complete but unexecuted. This
session ran that entire branch on the real development machine, with the
real frozen corpus and a live backend on both tracks, to close that gap: run
what could not be run, and fix what it found.

## 2. Environment findings

- The Track A `artifact_manifest.json` hash-integrity failure the cloud
  session hit (`docs/98` section 2) does **not** reproduce here:
  `sha256_file(artifact_manifest.json)` matches `artifact_manifest.sha256`
  exactly on this checkout. It was specific to that sandbox's checkout
  (likely a line-ending/serialization difference), not a real defect.
- Both backends start cleanly here and serve real data: Track A
  `readiness_state: prototype_scientific_ready`, Track B
  `experiment: operational_gefs_2023_2025` with all three years present.
- Frozen numbers spot-checked directly against the live endpoints match the
  checked-in static bundle and this session's own raw JSON reads exactly
  (e.g. 2025 Heavy probability ROC-AUC 0.894551596052136, Brier
  0.019831309998513996).

## 3. Automated checks, run for real

- `pytest backend/tests` — 193 passed (14 environment-only `tmp_path`
  permission errors on this machine, unrelated to this branch or any
  scientific code; `test_operational.py` itself is 50/50).
- `npm run typecheck` / `npm run lint` — clean (0 errors, the same 1
  pre-existing `no-location-assign` warning the cloud session reported).
- `npm test` (Vitest) — 76/76 (74 from the cloud session's work plus 2 new
  cases added in this pass, see section 5).
- `npm run build` — clean, all 12 routes compile.
- `npx playwright test --workers=1` (real backend, real corpus, real
  headless Chrome) — **35/35 passed**, including the four new specs the
  cloud session could only write and statically reason about
  (`operational-track-b.spec.ts`, `operational-extreme-verification.spec.ts`,
  plus the two it did run under mocked fixtures). Running with the default
  2 workers produced resource-contention flakiness (a real backend, a real
  frontend server, and two parallel Chromium instances all fighting for the
  same machine) with a different failure set each run and no code change in
  between -- confirmed as flakiness, not a defect, by the clean single-worker
  run.

## 4. Real defects found and fixed

All four were only reachable with a live backend and real data -- exactly
the residual risk the cloud session's own docs (`docs/97` section 2, `docs/98`
section 31) named and handed off.

1. **Mobile header overflow (real regression).** `.header-actions` (Reset
   Demo link + Presentation View toggle + Present button + experiment/year
   select + theme toggle, accumulated across 5A.2D/5A.3/5B) had no
   wrapping rule at the existing 760px breakpoint, causing 135px of
   horizontal overflow at 390×844. Fixed with `flex-wrap` on
   `.global-header`/`.header-actions` and hiding the Presentation toggle's
   text label at that breakpoint (icon remains, `title` attribute
   preserved). Verified: 0px overflow after the fix, confirmed the same
   overflow reproduces identically on `master` at `/forecast` for an
   unrelated, pre-existing `<select>` sizing issue this session did **not**
   touch (out of scope for this branch's review).
2. **`/extremes?experiment=operational` hard-blocked years other than
   2025** (`app/extremes/page.tsx`). The route wrapper was never updated
   when `operational-extremes.tsx` was rebuilt to be year-adaptive
   (2023/2024/2025) in Phase 5A.2D, so 2023/2024 never reached the
   component that was specifically built to handle them honestly. Fixed by
   removing the stale guard and threading `initialYear` from the URL,
   matching the existing pattern in `regimes/page.tsx`.
3. **Silently wrong 2024 probability metrics** (`lib/operational-probability-metrics.ts`).
   The real live `/2024/metrics/probability` payload nests scalar
   brier/bss/pr_auc/roc_auc fields under `.full_2024_descriptive_metrics`,
   not the `.metrics` key this helper assumed by analogy with 2025 (an
   assumption `docs/97` section 23 explicitly flagged as untested). The old
   fallback logic returned the *wrong but truthy* object (a bag of
   calibration/candidate-model metadata with no scalar fields), which
   crashed the Verification page's Generalization tab
   (`Cannot read properties of undefined (reading 'toFixed')`) the moment a
   real 2024 payload was involved. Fixed to check both known nesting keys
   and to return `undefined` (never a truthy metric-free object) when
   neither is present. Added a unit test reproducing the real shape.
4. **Missing very-heavy false-alarm-ratio caveat in Extreme Rain's
   Probability mode.** The pre-5A.2D component had this caveat; the 5A.2D
   rewrite's shared `ProbabilityQualityCards` is scalar-cards-only and
   dropped it. Restored as a data-driven caveat (shown when the frozen
   `categorical.metrics.FAR >= 0.5`, not a hardcoded per-event string), so
   it reflects whatever the frozen artifact actually says rather than an
   assumption about which event is worse.

## 5. Test-file fixes (no source-behavior change)

Five real-backend-only test bugs in the cloud session's own new specs, none
of which affected app behavior -- all were `getByLabel`/`getByText` locator
ambiguities or wording mismatches, findable only by actually running against
the real UI:

- `getByLabel("Model")` / `getByLabel("Year")` collided with unrelated
  aria-labelled map regions and the global header's "Experiment and year"
  control (substring matching). Switched to `getByRole("combobox", { name: /^Model|Year/ })`
  in both new spec files.
- The Track A regression test's expected boundary-disclaimer regex didn't
  match the app's actual wording (paraphrase drift). Corrected the regex.
- Two more `getByText` collisions (a table cell vs. a caveat paragraph
  quoting the same number; a chart's own figcaption vs. a surrounding
  caveat repeating the same sentence) in the new Verification spec, fixed
  by scoping to `getByRole("cell", ...)` / specific class locators.

## 6. What this confirms about the cloud session's own reporting

Every "not run here, needs a live backend" limitation the cloud session
documented (`docs/97` section 2, `docs/98` sections 2 and 31, `docs/99`
section 5-6) was accurate and specific enough to reproduce and resolve
directly from this session's notes, without re-deriving anything from
scratch. Its `SIH_DEMO_READY_WITH_MINOR_NOTES` / `FINAL_METEOROLOGICAL_FRONTEND_BLOCKED`
decisions were honest, not optimistic -- the defects found here were real,
but narrowly scoped, and none of them was hidden or downplayed in the prior
docs; they were exactly the class of thing flagged as unverified.

## 7. Remaining known-real, out-of-scope item

`/forecast` (Track A, `master`, not this branch) has a pre-existing mobile
overflow at 390×844 from a `<select>` in `.case-selector-main` not
respecting its `width: 100%` constraint at that specific width. Reproduced
identically on unmodified `master`. Not fixed here -- out of scope for
reviewing `master-3xhx5v`, flagged for separate follow-up.

## 8. Objective A (synoptic meteorology) — still not started

Unchanged from `docs/98`: this remains genuinely unbuilt. This session did
not attempt it (out of scope for a verification pass) but can now confirm
the live `/cases/{id}/atmosphere/{field}` endpoint is reachable with the
real backend, which was the stated blocker to starting it.
