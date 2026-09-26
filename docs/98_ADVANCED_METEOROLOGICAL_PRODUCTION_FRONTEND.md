# 98 — Advanced Meteorological Production Frontend (Phase 5A.3)

## 1. Executive Summary

Four of the five major objectives in this phase's brief were built for real
and verified as far as this sandboxed environment allows: the Verification
Skill Cube, Six-Season Observational Analytics (month × year matrix), the
Provenance DAG + Holdout Governance timeline + a finalized Scientific Audit
page, and Judge Story Mode. A canonical model/semantic color system and a
canonical metric-definition/tooltip module were also built and wired
through the shared components several of these draw on. An automated
science-copy guard test was added and verified to actually catch an
injected violation, not just pass vacuously.

**Objective A, professional synoptic meteorology (wind vectors, Z500
contours, MSLP isobars, Q700/PWAT shading, combined presets, the wider
atmospheric domain box), was not built.** This is not a scope trim for
convenience: section 2 explains a concrete, confirmed data blocker. Given
that one of five objectives is a complete miss, not a partial one, section
30's decision is `FINAL_METEOROLOGICAL_FRONTEND_BLOCKED` -- not a "minor
notes" characterization of what is otherwise a materially incomplete
result against this brief's own title.

## 2. Environment Constraint (read before trusting any "verified" claim below)

This session first spent real effort trying to get a live backend running,
on **both** tracks, before concluding neither could serve real data here:

- **Track B (2023-2025)**: confirmed in Phase 5A.2D and reconfirmed here --
  the `experiments/recent_historical/` frozen artifact tree is
  `.gitignore`d and absent from this checkout.
- **Track A (2019)**: newly investigated this phase. `data/manifests/phase2c/`
  (per-case metadata JSON for all 255 cases) IS present in this checkout,
  and a minimal FastAPI app mounting only `science.router` (bypassing the
  legacy `routes.py` import chain, which pulls in pandas/joblib/scikit-learn
  transitively for training-time code never executed at serve time) does
  start. But `GET /api/science/status` returns `503 Phase 2C artifact
  manifest integrity failure`: `sha256_file(artifact_manifest.json) !=`
  the hash recorded in `artifact_manifest.sha256`, on the actual bytes
  checked out in this container. This was not worked around (regenerating
  the hash or bypassing the check would be tampering with a protected
  integrity control) -- it is reported as a real, checkout-specific
  discrepancy for someone with access to the canonical checkout to
  investigate (likely a line-ending or serialization difference introduced
  somewhere in how this container's clone was produced).
- Consequently `/verification`'s own page (`app/verification/page.tsx`)
  cannot be reached at all here (it does a server-side Track-A fetch before
  `OperationalVerification` -- and therefore the new Skill Cube tab inside
  it -- ever mounts), exactly as documented in docs/97 section 2.

**Why this matters for objective A specifically**: the static frontend
bundle's per-case atmosphere arrays (`public/science/operational-v1/cases/*.json`,
`atmosphere.forecast_u850` etc.) are pre-clipped to the 1301-cell rainfall
target domain, not the wider 51×81 atmospheric context domain the brief's
section 13 describes (5-30°N, 55-95°E, 0.5°). The live backend's
`/cases/{id}/atmosphere/{field}` endpoint does carry the wider `[51, 81]`
shape -- but with neither backend reachable, there is no real wide-domain
atmosphere value array anywhere in this environment to render a wind vector
or a Z500 contour against. Building vector/contour rendering code against
fabricated placeholder values would violate this project's explicit "do not
fake meteorological structures" rule; building it untested against real
values was judged too high-risk to ship. See section 4 for exactly what
would need to be true to unblock this.

**What was and wasn't independently verified here**, precisely:

- Verified passing, real headless Chromium, this session: Story Mode's
  full scene sequence (launch/next/back/keyboard/exit/re-entry-resets/
  last-scene), the Six-Season month×year heatmap, and the Provenance DAG +
  Holdout Governance + Limitations panel on `/audit` (`tests/e2e/
  story-mode-and-audit.spec.ts`, 4/4 passing, run via a throwaway
  frontend-only local Playwright config created and deleted within this
  session, matching the precedent set in docs/97).
- Verified via `npm run typecheck` / `npm run lint` / `npm run build` /
  `npm test` only (not browser-executable here): the Verification Skill
  Cube, since it lives inside `OperationalVerification` on the
  SSR-blocked `/verification` route.
- Not attempted: objective A (section 2 above).

## 3. Synoptic Meteorology

**Not built.** See section 2. No wind vector renderer, no contour/isobar
generation, no Q700/PWAT shading upgrade, no combined presets, no wider-
domain map, no target-domain overlay box, and no synoptic point inspector
were added. The existing Atmosphere mode in Forecast & Atmosphere
(raster color-shaded U850/V850/Q700/Z500/MSLP/PWAT on the narrow, already-
available domain) is unchanged.

## 4. Wind Vectors

Not built (section 2/3). To build this for real: (a) a live backend
reachable from a frontend dev session, and (b) confirmation that
`/cases/{id}/atmosphere/{field}` genuinely returns the documented `[51, 81]`
wide-domain shape with real, physically sensible U/V values at that
resolution. Given both, the actual rendering work (deterministic zoom-aware
decimation, a canvas or MapLibre custom layer drawing arrow glyphs, a
derived-speed point inspector labeled "Derived display wind speed") is a
contained, well-understood piece of frontend work -- the blocker here is
data access in this environment, not algorithmic difficulty.

## 5. Z500 Contours

Not built (section 2/3). No contouring library (d3-contour, or equivalent)
is currently a dependency; none was added, since there is no real wide-
domain Z500 array in this environment to contour against, and adding an
untested dependency for code that cannot be visually verified here was
judged not worth the risk.

## 6. MSLP Isobars

Not built (section 2/3), same reasoning as Z500.

## 7. Moisture Fields

Not built (section 2/3). Q700/PWAT remain on the existing raster display
only; no ordered scientific moisture-scale upgrade or PWAT+wind combined
view was added.

## 8. Combined Overlays

Not built (section 2/3). None of the five curated presets exist.

## 9. Skill Cube

Built: `components/verification/skill-cube.tsx`, a new "Skill Cube" tab in
`OperationalVerification`. Year × Model × Metric-family × Event, filterable,
not a literal 5-D visualization. Reuses the exact same live queries
`OperationalVerification` already held from Phase 5A.2D (deterministic/
probability/FSS metrics for 2024 and 2025) -- no new network requests were
added. Continuous, Extreme, Probability, and Spatial each get their own
independent color-scale computation (`cellStyle()` normalizes against only
that table's own values, never mixed across metrics). Selecting "2023
(cross-fit only)" replaces the matrix with an honest unavailable message
naming why, rather than showing empty or fabricated cells. 2024/2025 role
labels ("Validation" / "Final test") are always visible next to the year,
never letting a comparison happen without that context. Track A is never
offered as a column here -- the cube covers Track B only, stated explicitly
in its own intro paragraph.

## 10. Lead-Time Matrix

Already existed from Phase 5A.2D (`OperationalVerification`'s "Lead Time"
tab, Day 1/2/3 Raw/M1-M4 RMSE) and is unchanged this phase -- the brief's
final-response-format heading is satisfied by that pre-existing, still-
correct tab, not a new duplicate.

## 11. Six-Season Observations

The `/observations` page (`SixSeasonObservations`) was already substantially
built before this phase -- real per-year summaries across all six seasons,
a daily event-calendar timeline with Heavy/Very-Heavy markers, and the
required non-climatology disclaimer already prominent at the top, all from
a static `observations_six_seasons.json` (750 real daily IMD records, no
live backend needed). This phase added the one genuinely missing piece: a
month × year matrix (section 12) with a metric selector, computed
client-side from the same already-trusted 750-record array -- not a new
science artifact.

## 12. Event Timeline

Unchanged this phase (already real, per section 11) -- daily Heavy/Very-
Heavy markers with hover detail (date, event type, cell counts), plus a
per-year "browse forecast-paired historical cases" link. Per-day linking to
one specific case was considered and not added: the observation records
carry no `case_id` field to link against precisely, and guessing one would
risk mislinking a day to the wrong case.

## 13. Provenance DAG

New: `lib/provenance-dag.ts` (the full NOAA GEFS → ... → M1/M2 fork →
regime classifier → M3/M4 → probability models → calibration →
verification → frozen results lineage, matching the brief's diagram) +
`components/audit/provenance-dag.tsx`, added to `/audit`. Clicking a node
shows input source, output artifact type, year role, feature count, model
family, scientific status, integrity status, and a documentation reference
-- never an absolute local path. Deliberately does not draw literal SVG
connector lines between nodes (kept to the same simple, robust click-to-
detail grid pattern already proven on the Quality page's smaller DAG,
rather than a fragile pixel-positioned graph); the fork/merge structure is
shown by which nodes share a row, not by drawn edges.

## 14. Holdout Governance

New: `components/audit/holdout-governance.tsx`, the full 2023 → 2024 →
FREEZE → 2025 → CONSUMED timeline, added to `/audit` alongside the
pre-existing single-moment SEALED → AUTHORIZED → UNSEALED ONCE → FINAL TEST
COMPLETED flow (kept, not replaced -- they answer different questions: the
years-long chain versus the one unsealing act).

## 15. Scientific Audit

`/audit` was rebuilt to include, in order: the new holdout governance
timeline, the pre-existing single-moment holdout flow, the new provenance
DAG, the pre-existing frozen-claim-boundary metrics, the new (extracted,
expanded) Limitations panel, and the pre-existing protected-artifact hash
list. No certification seal is claimed anywhere; the page's own subtitle
says "Internal Independent Reproducibility Audit."

## 16. Story Mode

New: `components/story/story-mode.tsx`, a 12-scene guided full-screen
overlay exactly matching the brief's scene list (Problem, Two Experiments,
Forecast Correction, Synoptic Context, Regime-Aware Processing, 2019
Benchmark, 2025 Final Test, Scientific Transparency, Extreme Rain
Probability, Uncertainty, Data Integrity, Reproducible Science), triggered
by a "Present VarshaSetu" button in the global header (`app-shell.tsx`).
Every number in it is one already verified and displayed elsewhere in this
app; Story Mode narrates existing frozen evidence and fetches nothing of
its own. Scene 4 (Synoptic Context) was worded to match what is actually
shipped (raster atmosphere fields) rather than claiming the unbuilt vector/
contour rendering from objective A. Next/Back/Exit, ArrowRight/ArrowLeft/
Escape keyboard navigation, a "Scene N of 12" progress readout with a
progress bar, and `prefers-reduced-motion` handling (the progress-bar fill
transition is disabled under that media query) are all implemented and
verified end-to-end in this session (see section 2). No auto-advance exists
at all (not merely defaulted off). The rest of the product does not depend
on Story Mode in any way -- confirmed by a test that loads a page and
asserts no dialog is open by default.

## 17. Presentation View

Not built this phase. A separate "collapse sidebar, hide provenance
details" mode distinct from Story Mode was judged lower priority than the
Skill Cube/DAG/Story Mode given the time available, and is a reasonable
candidate for a future pass; nothing about it is blocked the way objective
A is.

## 18. Model Color System

New: `lib/model-colors.ts` + new CSS custom properties (`--model-m0`
through `--model-m4`, `--model-imd`) in both `:root` and `.dark` in
`globals.css`, plus a new `ModelLadderRail` component
(`components/science/operational-charts.tsx`) showing all five models with
consistent color, label, and governance role (M1 "Preselected primary",
M2 "Secondary result", never visually crowning M2). `.model-dot.model-m0`
through `.model-m4`/`.model-imd` CSS classes let any component apply the
canonical color without hardcoding a hex value.

## 19. Semantic Color System

New: `--semantic-positive`/`--semantic-caution`/`--semantic-negative`/
`--semantic-info` CSS custom properties, in a separate namespace from the
model colors above specifically so M3's orange-ish hue (`--model-m3`) can
never be mistaken for or coupled to the "caution" semantic color
(`--semantic-caution`, which reuses the pre-existing `--amber`) -- the two
are independent tokens with independently chosen values in both themes.

## 20. Chart / Map / Metric Standards

New canonical metric-definition source: `lib/metric-definitions.ts` (RMSE/
MAE/Bias/POD/FAR/CSI/ETS/FSS/Brier/BSS/PR-AUC/ROC-AUC), backing a new
`MetricTerm` tooltip component (`components/science/common.tsx`, using the
already-installed Base UI Tooltip primitive, which is keyboard-focusable,
not hover-only). Wired into the shared `DeterministicCategoricalTable` and
`ProbabilityQualityCards` components (used by both Extreme Rain and
Verification) and into Verification's Continuous-tab table headers and the
new Skill Cube. Map-legend standardization (Q700/Z500/MSLP/wind-vector
legends specifically) is not applicable this phase since those layers were
not built (section 3-8); the existing Rainfall/Probability/Error-difference
legends are unchanged.

## 21. Accessibility

Verified this session (real headless Chromium, section 2): Story Mode is
fully keyboard-operable (Escape/ArrowLeft/ArrowRight, focus moves into the
dialog on open), the Skill Cube's and MetricTerm's interactive elements are
real focusable buttons (Base UI Trigger, not a hover-only tooltip), and the
new `.phase5-tab-row`/`.phase5-provenance-row` buttons use
`aria-pressed`/`aria-selected` consistently with the CSS active-state
selector extended in Phase 5A.2D to match both. A full axe scan of the four
new/changed client-only surfaces (Story Mode overlay, Six-Season heatmap,
Audit DAG/timeline/limitations) was not re-run this phase (Phase 5A.2D's
axe scans covered Casebook and Extreme Rain specifically); doing so is a
reasonable next-session addition, not attempted here due to time.

## 22. Performance

Not benchmarked with browser profiling (no measured need was found or
suspected -- none of this phase's new components do per-frame or per-pixel
work; the Skill Cube's `cellStyle()` normalization runs over at most 10
values per table). Given objective A (the one workload category the brief
itself flags as "CPU-sensitive," section 68) was not built, there was
nothing in that category to profile or memoize this phase.

## 23. Responsive Design

Not independently re-verified at 1366×768/1440×900/1920×1080 this phase
beyond what Phase 5A.2D already established for the shared `.phase5-*` CSS
classes the Skill Cube, Provenance DAG, and Story Mode all reuse. New
`@media(max-width:900px)`/`@media(max-width:760px)`/`@media(max-width:600px)`
rules were added for the provenance DAG two-column layout, the FSS
side-by-side spatial matrix, and Story Mode's headline/grid sizing
respectively, but only reviewed by reading the CSS, not by taking real
screenshots at those breakpoints.

## 24. QA Matrix

Not executed. A real 15-page × 3-breakpoint × 2-theme screenshot matrix
needs either a live backend (for the ~11 pages that need one) or a much
larger mocked-route fixture set than this session built; neither was
attempted at that scale this phase, matching the honest-gap pattern
established in docs/97.

## 25. Automated Tests

New this phase: `tests/e2e/story-mode-and-audit.spec.ts` (4 tests, **run
and passing** in this session), `src/lib/metric-definitions.test.ts` (2
tests), `src/lib/science-copy-guard.test.ts` (10 tests, and independently
sanity-checked in this session by injecting a real violation into a scratch
file and confirming the test fails, then removing it and confirming it
passes again -- see section 26). Wind vector/contour/isobar/target-domain/
preset-switching/Skill-Cube-filtering tests from the brief's section 69
were not added for the features that were not built; a Skill-Cube-filtering
test was not added because the page hosting it cannot be reached in this
environment (section 2), though the component itself passed typecheck/
lint/build.

## 26. Scientific Copy Guards

`src/lib/science-copy-guard.test.ts` scans every non-test `.ts`/`.tsx` file
under `src/` for eight forbidden phrases (live forecast, operationally
proven, universal improvement, true monsoon regime, 2025 untouched,
six-year climatology, extreme-rain improvement overall, combined
2019-2025 skill) and fails if any occurs without a negation word in the
~50 characters before it -- a heuristic, not a full parser, chosen because
a naive substring match would flag this app's own correct, repeated,
negated usage ("not a live forecast," "not live forecasting") as
violations. Verified real: injecting an unguarded "operationally proven ...
universal improvement" sentence into a scratch file made the relevant two
sub-tests fail with the exact violating text quoted; removing the scratch
file restored all 10 passing. All ten currently pass against the real
codebase.

## 27. Known Limitations

- Objective A (synoptic meteorology: wind vectors, Z500 contours, MSLP
  isobars, Q700/PWAT shading upgrade, combined presets, wide-domain
  overlay, synoptic point inspector) was not built -- see section 2 for the
  concrete data blocker and section 4 for what would unblock it.
- Presentation View (distinct from Story Mode) was not built.
- The Skill Cube could not be browser-verified in this environment (lives
  on the SSR-blocked `/verification` route); typecheck/lint/build only.
- No new axe scan, responsive screenshot matrix, or performance profiling
  was run this phase beyond what section 21-24 describe.
- Track A's own backend has a real, unresolved hash-integrity failure on
  this checkout's `artifact_manifest.json` (section 2) -- worth
  investigating separately; not touched here since bypassing an integrity
  check is against this project's own rules.

## 28. Final Product Walkthrough

Not executed as a single connected E2E path (the brief's "judge path"
Overview → 2025 result → Forecast → Error Anatomy → Synoptic → Probability
→ Ensemble → Regime → Verification → Quality → Audit) -- most of those
pages need a live backend this container does not have, and the one
missing leg specifically (Synoptic) does not exist to walk through at all.
Individual legs were verified separately where possible: Story Mode,
Six-Season Observations, and Audit in this session (section 2); the
remaining pages' correctness rests on Phase 5A.2C/5A.2D's own prior
verification, unchanged by anything in this phase except `/audit` and
`/observations` (both re-verified here) and `app-shell.tsx` (adds only the
Present button + Story Mode mount, verified not to break the pages that
were checked).

## 29. Protected Science Integrity

Verified: `git status` shows zero changes outside `frontend-v2/` for the
entirety of this phase's work. No file under `backend/`, `data/`,
`experiments/`, or any frozen Phase 2/4 artifact was read for anything
other than the pre-existing Track-A backend investigation in section 2
(read-only `curl`/import probes against a throwaway venv in `/tmp`, never
against the checked-out repository's own files, and no artifact was
regenerated, rehashed, or bypassed).

## 30. Final Decision

**FINAL_METEOROLOGICAL_FRONTEND_BLOCKED**

Four of five major objectives (Skill Cube, Six-Season Observations,
Provenance/Holdout/Audit, Story Mode) were built for real, with genuine
verification wherever this environment allows it, plus a real color system
and metric-definition standardization threaded through the shared
components several of them use. Objective A -- professional synoptic
meteorology, the capability this phase's own title leads with -- was not
built at all, blocked by a confirmed absence of real wide-domain atmosphere
data in this sandboxed environment (section 2), not by a decision to skip
it. That is a material rendering/data gap against this brief, not a minor
note, so this session reports the honest, harder answer rather than the
more flattering one.

## 31. Exact Next Task

Before anything else: get a live backend (either track) reachable from a
real frontend dev session, with the real frozen corpus present, and use it
to (a) resolve Track A's `artifact_manifest.json` hash-integrity failure on
whatever produced this checkout, then (b) confirm the live
`/cases/{id}/atmosphere/{field}` endpoint's real `[51, 81]`-shaped values
are physically sensible at that resolution. Only then attempt objective A
(wind vectors, Z500 contours, MSLP isobars) for real. In parallel, or if
objective A remains blocked, the next-highest-value work is: a real axe
scan and responsive screenshot matrix for this phase's new client-only
surfaces (Story Mode, Six-Season heatmap, Audit), and independently
verifying the Skill Cube on a machine where `/verification` is reachable.
