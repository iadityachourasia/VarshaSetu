# Phase 3A Frontend Testing and QA

From `frontend-v2/`, run `node_modules/.bin/tsc.cmd --noEmit`,
`node_modules/.bin/eslint.cmd .`, `node_modules/.bin/vitest.cmd run`,
`node_modules/.bin/next.cmd build`, and `node_modules/.bin/playwright.cmd test`
on Windows. The npm script aliases contain the same commands where the npm
launcher is available. Local Playwright uses Chromium separately from the
connected browser MCP. The backend must serve the frozen `/api/science`
artifact store, or Playwright's configured read-only web server starts it.

Unit tests cover rainfall threshold colors, cell-center geometry, masks,
dimension rejection, Zod schema rejection, API errors and read-only fetch
paths. The Playwright video-path test traverses all six routes, verifies the
three forecast maps, forecast-only regime context, Heavy/Very Heavy fields,
district table, FSS, primary 2019 result, and checks for JavaScript errors.
It asserts that all three rainfall maps initialize with the same camera,
then performs a user-initiated pan and asserts they remain synchronized.
The 1440×900 and mobile visual captures confirm that the entire 22°N–10°N
target extent remains visible after map initialization.
The responsive test checks 1920×1080, 1440×900, 1366×768, tablet and mobile
for horizontal overflow and saves screenshots. The extended visual matrix
captures all six routes at the three desktop video resolutions. An axe scan
checks serious/critical WCAG A/AA findings, and a light-mode reload test
checks theme persistence.

Scientific regression protection remains the full backend pytest suite,
Python compilation and hash-verified API artifact loading. Next build
proves production compilation but not scientific truth; Playwright proves
presentation and navigation but not model validity. The two layers must
both pass. The MapLibre worker is served locally to avoid external runtime
assets. No screenshot, chart, or video case is aggregate evidence by itself.
The latest production build emitted 23 static JavaScript chunks totaling
approximately 2.7 MB before transfer compression; route-specific dynamic
imports keep MapLibre and noncritical chart code off unrelated routes.

## Phase 3B map QA (2026-09-23)

`frontend-v2/tests/e2e/mapping.spec.ts` adds exact-cell persistence across
Weather/Scientific display and Dark/Light geography, opacity, zoom/reset,
district selection and a simulated OpenFreeMap outage. The forecast mobile
assertion now expects one active WebGL map and checks switching among Raw,
Corrected and Observed. The existing visual matrix saved Forecast, Extreme
Rain and District screenshots at 1920×1080, 1440×900 and 1366×768, plus a
390×844 forecast capture. The screenshots are under the local Playwright
`frontend-v2/test-results/` output directory; they are QA evidence, not
scientific artifacts. The `grid.test.ts` suite additionally checks raster
corner ordering, north-up output, mask boundaries and cached non-mutation.
The Phase 3B pass recorded 10 unit tests, 6 browser tests, production build,
TypeScript and ESLint passing; backend scientific regressions remained at
86 passing tests. Map behavior and provenance details are in `docs/73`.
