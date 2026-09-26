# 97 — Extreme Rain and Verification Live Migration (Phase 5A.2D)

## 1. Executive Summary

Completed docs/96 section 21's deferred work: migrated Extreme Rain
(`operational-extremes.tsx`, all four modes) and Verification's Track B
panels (`operational-verification.tsx`) onto the same `withStaticFallback` +
`DataSourceIndicator` pattern already used by the five pages migrated in
Phase 5A.2C (Forecast case selector, Quality, Casebook, Ensemble, Regime
Intelligence). Track A verification (`VerificationView`,
`verification-charts.tsx`) is untouched. No backend changes; no new
endpoints. Two small shared helpers were added
(`lib/operational-probability-metrics.ts`, `lib/stats.ts`), both pure
functions with unit tests.

## 2. Environment Constraint (read before trusting the "verified live" claims below)

Unlike the Phase 5A.2C session, this container does not have the
`experiments/recent_historical/` frozen artifact tree (it is `.gitignore`d
and was never checked into this checkout), so the backend cannot serve any
real Phase 4I/4J data here — `metrics/probability.json`, `metrics/fss.json`,
etc. do not exist on disk in this environment, and installing the backend's
full dependency stack (eccodes, xgboost, zarr, ...) to prove that out was not
attempted. Concretely this means:

- The exact top-level JSON shape the backend serves for
  `/{year}/metrics/probability` was **not** directly inspected for 2025 in
  this session (see section 3).
- The "VERIFIED_API" code path (a real 200 response with real numbers) was
  **not** exercised end-to-end against a live backend with real data, unlike
  the "Verified live" claims in docs/96.
- What *was* verified end-to-end in a real browser (Playwright, headless
  Chromium) against `next start` with the backend genuinely absent: the
  `/extremes?experiment=operational` route renders with zero console errors
  or exceptions, and correctly surfaces the honest failure state (`Data
  unavailable — Frozen probability case catalogue unavailable.`) rather than
  fabricating or silently masking anything, exactly matching the existing
  Casebook/Ensemble/Regime Intelligence behavior under an identical broken-
  backend condition (the Next.js rewrite proxy returns `500`, which
  `classifyOperationalError` correctly treats as a real error to surface,
  not a network failure to paper over with stale cached data).
- `npm run typecheck`, `npm run lint`, `npm test` (61/62 passing — the one
  failure, `communication.test.ts`, is pre-existing and fails identically on
  an unmodified checkout because it also depends on the same missing
  `experiments/` tree), and `npm run build` (full production build,
  including `/extremes` and `/verification`) all pass.

**Residual risk**: before treating this migration as fully proven, someone
with access to the real `experiments/` corpus should load `/extremes` and
`/verification` against a live backend with real 2024/2025 data and confirm
the probability-metrics unwrap logic in section 3 picks the right branch.

## 3. Probability Metrics Shape Tolerance

`getOperationalProbabilityMetrics(year)` returns a loosely-typed
`metrics: Record<string, unknown>` (backend: `dict[str, Any]`, no schema).
Two known real shapes exist for the per-event object:

- **2024** (`probability_heavy_2024.json` / `probability_very_heavy_2024.json`,
  confirmed flat from the checked-in static bundle): `brier`, `bss`,
  `pr_auc`, `roc_auc`, `categorical`, `reliability`, etc. all at the top
  level of `metrics.heavy` / `metrics.very_heavy`.
- **2025 presentation manifest** (`final_result_2025.json.probability`,
  also checked in): the same fields, but one level deeper under a
  `.metrics` key (`metrics.heavy.metrics.brier`, ...).

Docs/92 states the 2025 live endpoint serves `metrics/probability.json`
"verbatim," but that raw artifact file is not present in this checkout to
confirm which of the two shapes it uses. `lib/operational-probability-metrics.ts`'s
`extractProbabilityEventMetrics()` tolerates both (unwraps a `.metrics` key
if present, else reads the object directly) rather than assuming one -- a
real shape difference is read correctly either way instead of being
misread as "unavailable." Unit-tested for both shapes plus the
absent-event and absent-metrics cases. FSS (`metrics/fss.json`) is read
directly with no such tolerance needed: docs/92 states the known Heavy/Very
Heavy Raw/M1 headline numbers were confirmed directly against that endpoint,
and those numbers live in the static bundle at exactly the nested
`matched_raw`/`matched_selected` shape this code reads.

## 4. Extreme Rain Migration

`operational-extremes.tsx`, fixed to 2025 (unchanged scope; the page was
never a multi-year page). Live-API-primary for:

- The per-case calibrated probability grid (`getOperationalProbability`) --
  already served fully expanded 49×49 by the backend's `_scatter_49x49`, so
  the old `expandedField`/`pixel_indices.indexOf` reshape logic was removed
  entirely (matching the same simplification already made for Ensemble in
  Phase 5A.2C).
- The probability metric family: brier/BSS/PR-AUC/ROC-AUC, categorical
  POD/FAR/CSI/ETS, and reliability bins (`getOperationalProbabilityMetrics`),
  now driving all of the headline strip, Detection tab, and Reliability tab.
- FSS (`getOperationalFSS`), now driving the Spatial skill tab.

Grid geometry (lat/lon centers, valid-cell mask) is presentation-only and
continues to read the static bundle exactly as Ensemble/Regime already do
(docs/96 section 19) -- this is not a scientific value and was correctly out
of scope for the previous phase's migration too. The case selector now
sources from the live case index filtered on `probability_source_eligible`,
same pattern as every other migrated page. Each of the three live queries
falls back to the static bundle only via `null` (no static rescue), matching
the exact precedent set by Ensemble/Regime's per-case and metrics queries in
Phase 5A.2C -- no new fallback-wiring code was introduced for this pass.

## 5. Verification Migration (Track B Panels)

`operational-verification.tsx`. Live-API-primary for:

- The verification skill cube and the "2025 lead-time RMSE" table:
  `getOperationalDeterministicMetrics` for both 2024 and 2025. The
  RMSE-per-lead accessor now detects the known year-to-year shape
  difference (2025's `leads[lead].continuous.rmse_mm` vs. 2024's flat
  `leads[lead].corrected_rmse_mm`) structurally -- whichever key is present
  -- rather than a hardcoded `year === 2025` branch.
- The "Validation → completed final test" table's PR-AUC columns:
  `getOperationalProbabilityMetrics` for both years, via the same
  shape-tolerant helper as Extreme Rain.

**"Case outcomes" panel**: there is no dedicated backend endpoint for the
frozen `case_audit` artifact (improved/worsened/median-delta counts). Rather
than leave this one panel on the static bundle or add a new backend
endpoint (out of scope for a frontend-only pass), it is computed here
directly from the already-live, already-proven per-case index
(`loadOperationalCaseList(2025)`), using the exact same
`m1_minus_raw_rmse_mm < 0` sign rule the backend itself uses to derive
`selected_model_improved_vs_raw` (`backend/app/api/operational.py`). This is
a transparent aggregate over real per-case values already trusted and
displayed elsewhere (Casebook), not a new or invented statistic; the "tied"
count is computed from the exact zero case rather than inferred from the
boolean flag (which does not distinguish "worsened" from "exact tie"). The
displayed case count is now the live count rather than the previously
hardcoded literal "232."

Track A's own verification (`VerificationView`, `verification-charts.tsx`,
the 2019 GEFSv12 reforecast panels) is untouched -- it already reads
`/api/science/*` live and was never part of this migration's scope.

## 6. New Shared Helpers

- `lib/operational-probability-metrics.ts` -- `extractProbabilityEventMetrics`
  (section 3). Used by both migrated pages.
- `lib/stats.ts` -- `median`, a pure function used only by the Case Outcomes
  panel. Both have Vitest unit tests (8 new tests total, all passing).

## 7. Known Limitations (carried forward / new)

- Per section 2, the live 2025 probability-metrics shape assumption is
  untested against real data in this environment.
- No new Playwright specs were added (consistent with docs/96 section 17's
  precedent of manual/browser verification only for this kind of pass); the
  Playwright check performed here (headless Chromium against `next start`)
  was ad hoc, not committed as a repeatable spec.
- Synoptic vector/contour rendering, the Verification Skill Cube redesign,
  and Judge Story Mode remain not started, per docs/96 section 21's stated
  ordering.
