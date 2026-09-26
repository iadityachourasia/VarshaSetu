# 95 — Live Operational Frontend Data Migration (Phase 5A.2B)

## 1. Executive Summary

Made `/api/science/operational/*` the primary data source for Track B
(2023-2025) in the two highest-value pages: **Forecast & Atmosphere**
(rainfall, probability, regime, ensemble) and **Data Quality & Provenance**
(the full quality funnel). The pre-generated static bundle
(`public/science/operational-v1/`) is preserved as a bounded fallback for a
genuine network failure only, never a silent substitute. Casebook, Ensemble
(standalone page), Regime Intelligence, Extreme Rain, and Verification remain
on the static bundle — an explicit, documented deferral (section 26 "Known
Limitations"), not an oversight. A real bug was found and fixed during this
work: the fallback logic originally treated *any* non-`OperationalApiError`
exception — including a Zod schema-validation failure on a stale 200 OK
response — as network-failure-eligible, which would have silently masked a
genuine contract violation with cached data. This is now a hard
`INTEGRITY_FAILURE`, covered by a dedicated regression test.

## 2. Previous Static Architecture

`science/frozen/operational.ts` fetched static JSON from
`public/science/operational-v1/{index.json, cases/{year}/{case_id}.json}`,
Zod-validated, and rendered directly — no backend dependency at runtime.
This was built before Phase 5A.2B (see docs/94) and is not being deleted.

## 3. New API-First Architecture

```
Forecast/Quality components
        v
withStaticFallback()  (lib/data-source.ts)
        v
operational.ts (lib/api/operational.ts) -- live, hash-verified
        v
same-origin proxy (/api/science/operational/*)
        v
backend/app/api/operational.py
```

`lib/operational-live-case.ts` composes a full case object primarily from
live endpoints, reshaping each 49x49 grid response back into the same
1301-length, pixel-index-ordered flat array the existing rendering/error-
anatomy/point-inspector code already expects — so none of that code needed
to change.

## 4. Static Fallback Role

`withStaticFallback<T>(liveFetch, staticFetch)` (`lib/data-source.ts`) tries
the live path first. It falls back to the static path **only** when the live
call throws `OperationalApiError` with `kind === "NETWORK_FAILURE"`. Every
other outcome is a terminal result:
- `INTEGRITY_FAILURE` → hard error, no fallback, ever.
- `NOT_AVAILABLE` / `NOT_ELIGIBLE_FOR_CASE` → re-thrown as-is; a real,
  correct "this doesn't exist" answer is not a failure to recover from.
- Any other exception type (e.g. a `ZodError`) → treated as
  `INTEGRITY_FAILURE`, not silently masked (see section 20).

## 5. Scientific Integrity Rules

No artifact under `data/` or `experiments/` was touched. The only backend
change was additive: three new per-year breakdown fields on the existing
`/quality` response (`atmosphere_complete_by_year`,
`deterministic_eligible_by_year`, `scheduled_by_year`), computed from the
already-loaded eligibility records — no new science, no recomputation.

## 6. Track A Preservation

Not touched. Verified live via browser: `/forecast` (no `experiment` param)
renders the unchanged 2019 workspace correctly after this migration.

## 7. 2023 Data Flow

`getOperationalCase(2023, caseId)` → `available_products` includes
`"m2_out_of_fold"` (a capability *label*, distinct from the plain `"m2"`
query-parameter value the `/rainfall` endpoint actually accepts) plus
`"imd"` and `"regime"`. `raw`, `m2`, `imd` rainfall grids, ensemble, and
OOF regime are fetched live; `m1`/`m3`/`m4`/probability are never requested
(not in `available_products`) — matching the backend's own designed
restriction exactly.

## 8. 2024 Data Flow

`available_products` includes `raw, m1, m2, m3, m4, imd` plus
`heavy_probability, very_heavy_probability, regime`. All fetched live per
case — this is the "major acceptance requirement" from the brief, verified
working end-to-end via browser network-request inspection (section 21).

## 9. 2025 Data Flow

Same full set as 2024, plus case-level metrics already available from the
static bundle's `frozen_case_metrics` (unchanged, since the live per-case
endpoint doesn't carry per-case RMSE outside the case list). M1 remains
labeled "preselected primary", M2 "secondary" — unchanged labeling logic,
now fed by live-verified grids.

## 10. Case Index

**Not migrated in this pass.** The case list/browsing dropdown still reads
`science/frozen/operational.ts`'s static `index.json`. Rationale: the live
`/api/science/operational/{year}/cases` list endpoint doesn't carry
`heavy_cells`/`very_heavy_cells` counts the case-selector label uses, and
adding a second per-case fetch just to populate a dropdown label would
violate section 12's explicit "avoid fetching full arrays during case-list
browsing" guidance in spirit. The case *identities* used are the same
(both index and live API are generated from the same frozen eligibility
records), so this is a metadata-only limitation, not a scientific one.

## 11. Rainfall

Live-primary for all fields the case's `available_products` declares (see
sections 7-9). `lib/operational-live-case.ts`'s `flattenGrid()` is the exact
mathematical inverse of the static bundle's `expandedField()` — verified by
the fact that the migrated maps render pixel-identical output to the
pre-migration static-only renders (same case, same visual result, confirmed
by screenshot comparison during this work).

## 12. Probability

Live-primary via `getOperationalProbability`, only when
`available_products` includes `"heavy_probability"` (2024/2025 only, per the
backend's own capability rules). 2023 never requests it.

## 13. Regime

Live-primary via `getOperationalRegime`, mapped from
`{ACTIVE_MONSOON, BREAK_WEAK_MONSOON, LOW_DEPRESSION_INFLUENCED}` probabilities
into the same 3-tuple order the static bundle already used, for all three
years (2023 OOF, 2024 prospective, 2025 final-test — per Phase 5A.1B's proven
attribution).

## 14. Ensemble

Live-primary via `getOperationalEnsemble`; only QC-eligible members are
included in the composed `ensemble_members` record (ineligible members are
simply absent, matching the pre-existing "don't show a blank panel" behavior
this component already had for the static path).

## 15. Atmosphere

**Not migrated — explicit, documented limitation.** The live API's
atmosphere grids are native 51x81 (0.5°); this workspace and its map
component currently render everything against the 49x49 (0.25°) rainfall
domain. The static bundle's atmosphere fields (already resampled onto that
domain by whatever process built it) remain the source for this phase.
Building a true native-resolution synoptic workspace is explicitly deferred
to a later phase (per both this brief's section 31 and the prior phase's
docs/94 deferral) — this migration only had to verify the live path is
stable, which Phase 5A.1B/backend tests already did.

## 16. Verification / 17. Quality / 18. Provenance

**Quality**: fully migrated (see section 1). **Verification**: not migrated
in this pass — still reads Track A's `/api/science/*` (unchanged, correct)
and the static Track B bundle for its operational comparison numbers.
**Provenance**: the reusable `DataSourceIndicator` chip is wired into both
migrated pages' headers; a dedicated provenance drawer consuming
`getOperationalProvenance()` was not built this pass.

## 19. Fallback Manifest

A dedicated `static_fallback_manifest.json` was not created. The static
bundle already has its own hash-lineage file,
`public/science/operational-v1/presentation_science_manifest.json`
(`outputs_sha256` keyed by every bundled file path), which already satisfies
the spirit of section 18's request — creating a second, parallel manifest
would duplicate rather than strengthen that lineage record.

## 20. Integrity-Failure Behavior

**The one real bug found in this phase.** While migrating the Quality page,
the live fetch succeeded at the network layer (200 OK) but the response body
came from a stale backend process (started before the `/quality` endpoint
was extended with three new fields) and failed Zod schema validation. The
original `withStaticFallback` implementation treated any non-
`OperationalApiError` exception as fallback-eligible, so it silently served
cached static data instead of surfacing the contract violation — exactly the
failure mode section 17 forbids, just triggered by an unanticipated error
shape rather than an HTTP error status. Fixed: a non-`OperationalApiError`
exception (including a `ZodError`) is now classified as `INTEGRITY_FAILURE`
and never falls back. Covered by
`data-source.test.ts`'s "regression: a Zod schema-validation failure on a
200 OK response is treated as an integrity problem" test, which reproduces
the exact scenario.

## 21. Caching

No new caching layer was introduced beyond what already existed
(`@tanstack/react-query`'s default per-query-key caching, already in use).
Request deduplication/prefetch (sections 13-14 of the brief) were not built
this pass.

## 22. Performance

Not benchmarked beyond confirming the existing Playwright
`demo-performance.spec.ts` timings remain reasonable after migration
(forecast navigation ~4.9s, case switch ~1.4s in this run — comparable to
the pre-migration baseline).

## 23. Accessibility Fix

Completed as a standalone task before this phase's main work: darkened
`.phase5-outcome-bar`'s teal from `#208574` (4.49:1 contrast, failing WCAG
AA) to `#1d7568` (5.53:1, passing). Full axe/Playwright accessibility suite
now passes 11/11 (previously 10/11).

## 24. Map-Tile Reliability

Not changed in this phase. The existing test suite already separates
"online vector geography loads" from "offline style failure leaves local
science usable" as two distinct Playwright tests (both passed in this run);
decoupling the online test from overall suite pass/fail (so a flaky external
tile provider can never redden the whole suite) was not implemented.

## 25. Tests

- Backend: 43 tests (unchanged count; 3 existing quality assertions extended
  to cover the 3 new response fields).
- Frontend: `data-source.test.ts` (new, 8 tests) covering every fallback
  branch including the integrity-failure fix; `operational.test.ts` quality
  schema/test updated for the 3 new fields (still 19 tests). 48 total, all
  passing.
- Playwright: 11/11 passing (verified against the live migrated app, not
  just the static bundle).
- New end-to-end verification performed via the browser tool (not automated
  as a Playwright spec in this pass): 2023→2024→2025 sequential navigation
  with zero console errors, live network requests confirmed for every field
  per year, and Track A regression confirmed unaffected.

## 26. Known Limitations

- Casebook, standalone Ensemble page, Regime Intelligence, Extreme Rain, and
  Verification still read the static bundle, not the live API.
- Case list/browsing metadata (the year/case dropdown) still comes from the
  static index, not a live paginated endpoint.
- Atmosphere fields are static-bundle-sourced; no native-resolution synoptic
  workspace exists yet.
- No request deduplication/prefetch layer, no dedicated provenance drawer,
  no `static_fallback_manifest.json`, no fallback-regenerator script, no new
  automated 2023/2024/2025 Playwright end-to-end specs (verified manually via
  the browser tool instead), and no map-tile-test/core-suite decoupling.

## 27. Exact Next Task

In priority order: (1) migrate Casebook and the standalone Ensemble/Regime/
Extremes/Verification pages onto the same `withStaticFallback` pattern
established here; (2) add a live, paginated case-index endpoint consumption
path (or extend the live `/cases` response with the missing display
metadata) so the case selector itself becomes live-primary; (3) only then
begin the native-resolution synoptic atmosphere workspace and the automated
2023/2024/2025 Playwright end-to-end specs.
