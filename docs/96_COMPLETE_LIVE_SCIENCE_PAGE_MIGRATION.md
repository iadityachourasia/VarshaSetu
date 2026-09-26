# 96 — Complete Live Science Page Migration (Phase 5A.2C)

## 1. Executive Summary

Extended the live operational case index with presentation-safe selector/
casebook metadata, then migrated the Forecast case selector, Casebook,
Ensemble, and Regime Intelligence pages to consume `/api/science/operational/*`
as their primary source, each falling back to the static bundle only on a
genuine network failure. Added one new backend endpoint
(`/{year}/metrics/ensemble`) needed for the matched-75-case comparison table.
Extreme Rain and Verification remain on the static path — an explicit,
honest deferral (section 19), not a shortfall: each is a materially larger
migration (four modes / five metric families respectively) than the time
budget for this pass allowed to do properly, and the brief's own framing
("main migration complete with explicitly listed non-blocking limitations")
anticipates exactly this outcome.

## 2. Live Case Index

`backend/app/api/operational.py`'s `OperationalCaseSummary` gained 8 new
fields, all computed from already-loaded frozen artifacts, never fabricated:
`initialization_date`, `month`, `lead_label` (deterministic string formatting),
`valid_date`, `event_heavy`, `event_very_heavy` (from the frozen IMD pairing
array already used for grid reshaping — a threshold comparison over data
already in memory, not new computation), `pseudo_regime_class` (argmax over
the already-proven per-case regime lookup), and
`selected_model_improved_vs_raw` (sign of the existing `m1_minus_raw_rmse_mm`).
Every field is `null` for a case with no frozen backing artifact — proven by
`test_case_index_never_fabricates_metadata_for_ineligible_cases`.

## 3. Selector Metadata

Verified live: a 2024 case outside the deterministic-eligible population
returns `valid_date: null, event_heavy: null` (no fabrication); an eligible
case returns real computed flags (`event_heavy: true` confirmed for a real
2024 case via direct API call during this work).

## 4. Casebook Migration

`operational-casebook.tsx` now sources its full case list from
`loadOperationalCaseList()` (`lib/operational-case-list.ts`), which wraps
`getOperationalCases` in `withStaticFallback`. Filters (month, lead, observed
event, pseudo-regime, selected-model outcome) all operate on the new
`CaseListItem` shape. The "selected-model case outcome" filter now
disappears based on real data availability (`hasCaseOutcomeData`) rather than
a hardcoded `year === 2025` check — verified live: 2023 cases correctly show
no such filter and "M2 OOF" instead of a score.

## 5. Ensemble Migration

`operational-ensemble.tsx` now fetches the case list (filtered by
`ensemble_source_eligible`), each case's five-member grids via
`getOperationalEnsemble`, and the matched-population comparison via the new
`getOperationalEnsembleMetrics`. Verified live: point-inspector cell click
shows all 5 members with values, QC-failed members remain listed (not
dropped), and the comparison table renders the exact frozen Brier scores
(0.02289/0.02085 heavy, 0.00502/0.00493 very-heavy) fetched live, not
hardcoded.

## 6. Regime Migration

`regime-intelligence.tsx` now fetches: the case list (filtered by
`regime_source_eligible`), per-case regime via `getOperationalRegime` (with
year-correct `prediction_role` text: OOF/prospective-validation/final-test),
the aggregate distribution via `getOperationalRegimeSummary`, and (2025 only)
the regime-conditioned M2/M3/M4 RMSE via `getOperationalDeterministicMetrics`.
The advanced attribution caveat (full-375 + paired-232 count reproduction,
not an explicit case-ID array) is preserved in the paired-distribution
section, not surfaced as headline UI.

## 7. Extreme Rain Migration

**Not migrated.** `operational-extremes.tsx` still reads the static bundle.
This page needs four distinct modes (event detection, probability, spatial
skill/FSS, reliability) each with their own live-endpoint wiring
(`getOperationalProbabilityMetrics`, `getOperationalFSS`, and per-case
probability grids) — a real, separate piece of work deferred to the next
pass rather than rushed.

## 8. Verification Migration

**Not migrated.** `operational-verification.tsx` still reads the static
bundle for its Track B panels; Track A's verification is untouched and
correct (it already uses the Track A `/api/science/*` API). Deferred for the
same reason as Extreme Rain.

## 9. Static Fallback Coverage

Casebook, Ensemble, and Regime Intelligence all now use the same
`withStaticFallback` primitive as Forecast/Quality — no page-specific ad hoc
fallback logic was introduced. No new fallback artifacts were created; the
existing static bundle already covers every field these three pages needed
as a fallback source.

## 10. Source Status

All five now-migrated pages (Forecast, Quality, Casebook, Ensemble, Regime
Intelligence) render the same `DataSourceIndicator` chip
(`VERIFIED_API | VERIFIED_STATIC_FALLBACK | UNAVAILABLE | INTEGRITY_FAILURE |
NETWORK_FAILURE`), quiet in normal operation.

## 11. Integrity-Failure Behavior

Unchanged rule, reused: `withStaticFallback` never falls back on
`INTEGRITY_FAILURE` or a real unavailable/ineligible answer. Casebook and
Regime Intelligence both render a dedicated hard-failure `ErrorState` for
that mode, matching Forecast/Quality's existing pattern exactly.

## 12. 2023 Role Safety

Verified live: Casebook's outcome filter absent, "M2 OOF" case labels;
Regime Intelligence's `prediction_role` correctly `OUT_OF_FOLD`; Ensemble's
case list correctly restricted to `ensemble_source_eligible` 2025-only cases
(2023/2024 aren't offered in the Ensemble selector since the matched-
population comparison and the standalone Ensemble page are 2025-specific
artifacts, matching the pre-existing page's original scope).

## 13. 2024 Validation Safety

Casebook and Regime Intelligence both correctly label 2024 as
"VALIDATION" / "PROSPECTIVE_VALIDATION" and never claim final-test status
for it.

## 14. 2025 Final-Test Safety

Regime Intelligence's regime-conditioned M2/M3/M4 table and Ensemble's
matched-population table are both gated to 2025 only, matching their
underlying frozen artifacts' actual scope.

## 15. Request Cancellation

**Not implemented.** TanStack Query's default behavior (each query keyed by
year/case_id) naturally supersedes stale in-flight requests' results once a
new query key is active, but no explicit `AbortController`-based cancellation
was added. Not observed to cause a visible bug in manual testing, but not
verified under rapid-switch stress either.

## 16. Performance

Not benchmarked beyond confirming `demo-performance.spec.ts`'s existing
timings remain reasonable (forecast navigation ~10.3s in this run, up from
~4.9s in Phase 5A.2B's run — the increase is expected: the live case-index
list-fetch and grid-response volume both grew now that all 375 scheduled
cases per year are available rather than the pre-existing smaller demo
subset. Not flagged as a regression requiring action this pass, but worth
watching).

## 17. E2E Tests

No new automated Playwright specs were added for the 2023/2024/2025 case
selector, Casebook, Ensemble, or Regime flows. All were verified manually via
the browser tool instead (live network-request inspection + console-error
checks for each), which is real verification but not a regression-guarding
automated test. Deferred alongside Extreme/Verification migration.

## 18. Track-A Regression

Verified unaffected: Track A `/forecast` (no experiment param) renders
correctly with zero console errors after all changes in this phase.

## 19. Remaining Static Data

Extreme Rain, Verification (Track B panels), atmosphere fields (all pages,
per Phase 5A.2B's documented deferral), and the Ensemble/Regime pages'
underlying grid-geometry (mask/pixel_indices, unrelated to scientific values)
all still read the static bundle.

## 20. Known Limitations

- Extreme Rain and Verification not migrated.
- No request cancellation/dedup layer beyond TanStack Query's own key-based
  behavior.
- No new automated E2E specs for the migrated flows (manual browser
  verification only).
- Case-list fetch volume increased (375 vs a smaller demo subset per year);
  not yet performance-tuned.

## 21. Exact Next Task

Migrate Extreme Rain (four modes: event detection/probability/spatial
skill/reliability, via `getOperationalProbabilityMetrics`/`getOperationalFSS`/
per-case probability grids) and Verification (Track B panels via
`getOperationalDeterministicMetrics`/`getOperationalProbabilityMetrics`/
`getOperationalFSS`/case-level 2025 metrics), using the same
`withStaticFallback` + `DataSourceIndicator` pattern established across the
five pages migrated in this phase — before starting synoptic vector
rendering, the Skill Cube, or Story Mode.
