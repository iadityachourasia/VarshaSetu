# Website visual audit — 9 October 2026

## Scope and evidence

The local evaluator demo was started with `scripts/demo/start-demo.ps1
-IncludeNationwideResearch`. The production frontend and API proxy passed the
demo preflight. A local Chrome audit loaded the 17 known routes at 1440 × 900
and 390 × 844, captured viewport screenshots, and checked page exceptions,
failed local requests, broken images, document overflow and WCAG
2.0/2.1 A/AA rules with axe. Sixteen enabled routes returned HTTP 200. The
`/compliance` route intentionally returned 404 because
`NEXT_PUBLIC_SHOW_COMPLIANCE_PAGE` is off; it is absent from the sidebar.
The enabled routes were `/`, `/forecast`, `/regimes`, `/extremes`, `/ensemble`,
`/districts`, `/verification`, `/india`, `/live`, `/observations`, `/quality`,
`/zones`, `/geoaware`, `/casebook`, `/audit`, and `/methodology`.

The final audit found no page exceptions, failed local assets, broken images,
page-wide horizontal overflow, or axe violations on the enabled routes at
either width. Seven scientific
routes (`/`, `/forecast`, `/india`, `/live`, `/verification`, `/extremes`,
`/districts`) were also checked in the dark theme at desktop width; those
checks had no page exceptions, overflow or axe violations. Screenshots and
JSON reports are generated locally by `frontend-v2/scripts/visual-audit.mjs`
under ignored `frontend-v2/test-results/visual-audit*` directories. This is a
rendering and accessibility audit, not scientific validation or a promise that
every device, browser, and interaction has been exhaustively checked.

## Corrected visual and content defects

1. The app-shell's `2019 · Test` selector was displayed on pages that use
   different source populations, including nationwide 2025 Raw and 2026 live
   inference. It now appears only on the historical case workspace pages to
   which it applies. Each independent page continues to show its own source,
   cycle, period, model and evidence labels.
2. Several narrow-screen native selects clipped their selected values. The
   map selectors now take the available row width and the affected lead,
   population and outcome controls stack at phone widths. The page does not
   gain horizontal overflow.
3. Mobile evidence tables had a serious `scrollable-region-focusable` axe
   violation: keyboard users could not reach the horizontal scroll area.
   Table containers are now tab-focusable with a visible focus outline. A
   regression test checks the scrollable tables on six affected routes.
4. A live-cycle withheld-lead banner displayed a raw Python exception as its
   primary explanation. It now gives a readable GRIB packing quality-control
   reason and exposes the exact original message in a collapsed technical
   detail. The withheld status and source evidence are unchanged.
5. The zones selector uses shorter selected labels while retaining the full
   metric definition and test-population status in the surrounding page.

The visual fixes do not change forecast arrays, model defaults, reference
pairing, masks, verification metrics, probability calibration, or promotion
status. The regional experimental live-cycle correction remains M2; the 2025
historical replay retains its preselected M1. National corrected and
probability maps remain opt-in consumed-development research with their failed
gates visible; the 2026 observation score remains sealed.

The primary edits are in `frontend-v2/src/components/layout/app-shell.tsx`,
`live/live-cycle.tsx`, `maps/map-controls.tsx`, `zones/zone-evidence.tsx`, and
`frontend-v2/src/app/globals.css`. The table focus attribute was applied to
the `district-table-wrap` instances in 16 component files under `zones`,
`live`, `districts`, `regimes`, `verification`, `india`, and the disabled
`compliance` page. The audit and regression checks are
`frontend-v2/scripts/visual-audit.mjs` and
`frontend-v2/tests/e2e/responsive-page-audit.spec.ts`. The contract change is
recorded in `docs/13_UI_DATA_CONTRACT.md`.

The 16 table-container component files are: `zones/zone-evidence.tsx`,
`zones/geoaware-experiment.tsx`, `live/live-cycle.tsx`,
`districts/operational-districts.tsx`, `districts/district-workspace.tsx`,
`regimes/independent-regime-validation.tsx`,
`regimes/coastal-regime-panel.tsx`, `regimes/regime-task-validation.tsx`,
`regimes/regime-evidence-panel.tsx`, `regimes/wd-indicator-panel.tsx`,
`verification/reforecast-study.tsx`,
`verification/district-verification-panel.tsx`,
`verification/all-india-raw-verification.tsx`, `india/india-coverage.tsx`,
`india/nationwide-research.tsx`, and `compliance/ps-coverage.tsx`, all under
`frontend-v2/src/components/`.

## Checks

| Check | Result |
|---|---|
| Production frontend `npm run build` | PASS; 19 pages generated |
| Frontend `npm run typecheck` | PASS |
| Frontend `npm run lint` | PASS |
| Frontend `npm test` | PASS; 31 files, 212 tests |
| Targeted Chromium browser tests before the table fix | PASS; 10 tests |
| Full Chromium browser suite before the table fix | PASS; 167 passed, 5 intentionally skipped, 0 failed (6.7 min) |
| Final mobile table and layout browser regression | PASS; 4 tests |
| Final strict desktop/mobile visual and axe audits | PASS; 16 enabled routes at each width, 0 violations and 0 failed local assets |
| Demo startup/preflights | PASS; `DEMO_PREFLIGHT_RESULT=READY` |
| Static `21st review frontend-v2/src/app --json` | Exit 0; 0 errors, 0 warnings, 206 nonblocking suggestions |

The five skips are the compliance-page tests: that route is deliberately
disabled in this demo build. No browser test was interrupted or failed.
After the final production rebuild, a pre-existing frontend process briefly
served HTML against mismatched static assets. The audit caught HTTP 500s for
those CSS/JS files. The specific stale Next process on port 3200 was verified
and restarted; the referenced CSS now returns HTTP 200 and both final strict
visual audits pass. Rebuilds must stop the active frontend process first.

## Homepage India entry follow-up

The full-width India-wide Raw GEFS entry beneath the six evidence tiles used
the compact shared context-strip layout. At 1242 × 668 its title, footprint
note and link crowded one line. It is now one linked card with the same
bordered surface language as the tiles above: a leading globe icon, a
two-line title/footprint group, and a right-aligned action. Below 820 px the
action moves beneath the text; the source and regional-correction caveat are
unchanged. Only `frontend-v2/src/app/page.tsx` and
`frontend-v2/src/app/globals.css` changed for this follow-up.

The rebuilt production site passed typecheck, lint, and the 19-page build.
Eight targeted homepage/India Chromium tests passed. Visual checks at the
commented 1242 × 668 viewport, 390 × 844 phone width, and 1242 × 668 dark
theme found zero document overflow, no clipped card child, and no failed
local requests. The local demo preflight returned `READY` after a clean
frontend stop, build and restart. No rainfall value, model, mask, evidence
label, or promotion decision changed.

## Six homepage feature tiles follow-up

The six compact evidence tiles now describe six implemented website views
instead of repeating selected 2025 scores: Forecast Explorer, Regime
Intelligence, Extreme Rain, Ensemble & Uncertainty, District Intelligence,
and Verification Lab. The subtitles state historical Raw/corrected/IMD maps,
forecast-time pseudo-regimes, extreme-rain reliability inspection, the 2025
five-member ensemble subset, regional area-weighted districts, and spatial
verification metrics. The six-box grid and existing visual format remain.
This copy-only change is in `frontend-v2/src/app/page.tsx`; its scoped UI rule
is in `docs/13_UI_DATA_CONTRACT.md`. No model, probability, or score changed.

Typecheck, lint, the 19-page production build, and the local demo preflight
passed. Fifteen targeted Chromium homepage/responsive tests passed. Screenshots
at 1800 px, 1242 px, and 390 px confirmed respectively six, three, and one
columns, with six boxes in each layout, no clipped tiles, no document
overflow, and no failed local assets.

## Feature-tile navigation follow-up

All six homepage feature tiles now act as full-area links to `/forecast`,
`/regimes`, `/extremes`, `/ensemble`, `/districts`, and `/verification` in tile
order. The ensemble page retains its existing supported-2025 redirect.
Hover and keyboard focus are visible; the six-box desktop/tablet/mobile grid,
captions and scientific scope are unchanged. This touches
`frontend-v2/src/app/page.tsx`, `frontend-v2/src/app/globals.css`, and the two
homepage Chromium test files. The first browser run had 15 passes and one
failure because an existing assertion still checked padding on the old outer
card; the assertion was updated to inspect the full-area link. The final run
passed all 16 tests, including six click-through destinations and Enter-key
activation. Typecheck, lint, production build and demo preflight passed.
Visual checks at 1800, 1242 and 390 px confirmed six cards, full-card links,
and zero page-wide overflow.

## Repository link and homepage credits

The shared header now places a GitHub icon immediately beside the theme
control. It opens the configured repository
(`https://github.com/iadityachourasia/VarshaSetu`) in a new tab and has an
accessible name, visible keyboard focus, and a 44 px phone touch target. The
homepage credits read “Developed by TEAM METROLOGIX · ADITYA CHOURASIA” in a
quiet footer below the scientific evidence. At 320 px, the year selector and
four header controls remain on one row; at 390 px and desktop they remain
aligned with the theme button.

The first responsive check found the 320 px selector row wrapping; its compact
selector style was adjusted and the final screenshot showed the complete
“2019 · Test” label without page overflow. The final Chromium run passed all
17 homepage and shared-header tests. Typecheck, lint and the 19-page production
build passed; the local demo preflight returned `READY`. No scientific data,
scores, or model behavior changed.
