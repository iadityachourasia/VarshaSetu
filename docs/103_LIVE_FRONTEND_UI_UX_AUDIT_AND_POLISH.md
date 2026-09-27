# Live frontend UI/UX audit and polish — 2026-09-27

This is the pre-deployment audit record. The subsequent implementation, regression results, and deployment check are recorded in `104_FRONTEND_HARDENING_AND_POLISH.md`.

## Scope and scientific boundary

This pass inspected the deployed [Vercel frontend](https://varshasetu.vercel.app/) in a real Chromium browser and the [Render backend](https://varshasetu.onrender.com/), then changed only local frontend presentation and browser regression coverage. The continuation base was fast-forwarded to `origin/master` (`10bee1b`); its sole new change was README copy. There was no retraining, inference rerun, threshold change, rescore, or deployment.

The 2019 and 2025 populations remain separate. The 2025 M1 result remains preselected primary and M2 remains secondary. Track B districts remain unavailable. Scientific Grid and Weather Visualization retain their existing semantics.

## Live audit

All twelve routes loaded: `/`, `/forecast`, `/casebook`, `/extremes`, `/ensemble`, `/regimes`, `/districts`, `/verification`, `/observations`, `/quality`, `/methodology`, and `/audit`. The inspected live controls also included the experiment/year switch, forecast map display controls, Story Mode launch/exit, and theme toggle. Production viewport checks covered 1920×1080, 1440×900, 1366×768, 1280×720, 834×1112, and 390×844. Both light and dark themes were checked on representative forecast/overview surfaces. This does not claim an exhaustive interaction/state matrix for every route.

Live `/forecast?experiment=operational&year=2025` requested same-origin `/api/science/...` endpoints through the Vercel proxy; sampled case, geometry, rainfall, probability, regime, and ensemble requests returned HTTP 200. The Render root, `/api/science/status`, and `/api/science/operational/status` responded. The operational status identified the historical GEFS experiment, NOAA forecast source, IMD observation source, and completed 2025 final-test role. No sampled browser warning appeared on the loaded operational forecast. The deployment does not expose a reliable commit identifier, so exact deployed SHA cannot be asserted. Its pre-fix layout and copy matched local source before this pass; production remains visually behind the local repairs until Vercel deploys a new commit.

## Defect ledger

| ID | Route / viewport / theme | Severity | Category | Observed defect and root cause | Local fix and regression | Status |
| --- | --- | --- | --- | --- | --- | --- |
| UI-103-01 | All routes, 1280–1440 desktop, both themes | P1 | Sidebar / responsive | At the compact 65px rail breakpoint, `nav-group-label` stayed visible and extended beyond the rail into page content. The rail also lacked an overflow boundary. | Hide group labels in compact and presentation modes; retain visual group dividers and allow vertical scrolling. Geometry checked at 1280/1366/1440. | Fixed locally; deploy pending |
| UI-103-02 | All routes, 390px mobile, both themes | P1 | Navigation / responsive | The grouped navigation remained vertically stacked after `nav-list` switched to a row, and section headings ran together. This consumed about one third of the opening viewport. | Render groups and labeled links as a single horizontally scrollable row; keep accessible link text and active state. Mobile geometry regression added. | Fixed locally; deploy pending |
| UI-103-03 | Overview, 1440px, both themes | P1 | Benchmark / alignment | Phase 5 benchmark article markup had no card-level styles; labels and values appeared as loose lines. The six status items were `span` elements while CSS only targeted `div`, so they had no padding or surface. | Style the actual `article`, `dl`, and status `span` structure with clear two-track separation, tabular values, borders, and spacing. Browser regression checks two benchmark cards and six padded evidence items. | Fixed locally; deploy pending |
| UI-103-04 | Forecast, map loading state | P2 | Loading | Briefly empty/loading geography can precede the rendered map. This is a bounded external map-tile/loading transition; the scientific rainfall layer and labels remain present. | No scientific/map behavior changed. | Observed, not blocking |
| UI-103-05 | Dense science panels across routes | P2 | Typography | Several provenance and caveat labels are approximately 9–11px. They remain readable at desktop sizes but merit a later controlled typography pass. | No broad typography rewrite in this bounded correction. | Open polish note |

No P0 defect was reproduced in the inspected states. Pages beyond the global chrome had no additional reproducible P1 in this pass. Casebook, Extreme Rain, Ensemble, Regimes, Districts, Verification, Observations, Quality, Methodology, and Audit kept their existing scientific content and were visually inspected at 1440px in the live browser. The local production capture subsequently covered every route at three judge desktop resolutions.

## Page and component review

The Overview's paired benchmarks now have individual hierarchy, aligned Raw/corrected/Case rows, and visible links. Forecast's map pane labels, raw/M1/IMD distinction, case metadata, and Scientific Grid/Weather Visualization control were retained. Casebook filters and pagination, Extreme Rain tabs/caveat, five-member Ensemble wording, forecast-only pseudo-regime descriptions, the Track B district unavailable state, Verification's primary/secondary hierarchy and tables, descriptive Observations wording, the Quality counts (1125/615/218), Methodology flow, and Audit provenance/holdout presentation were present in the live route review. The dense Audit governance row remains a lower-priority polish candidate.

The global header remained consistent across route navigation. Story Mode opened and exited in live Chromium; the existing local Story Mode browser tests exercise its scenes, back/next, keyboard and exit behavior. The sidebar repair keeps icons on compact desktop and visible text on mobile. The mobile header remains multirow by design because it carries experiment/year and presentation controls.

No chart series, map interpolation, colors encoding model identity, table values, probability labels, thresholds, scientific wording, tooltip data, or error/fallback path was changed. This report does not call unexecuted scientific audits “passed.”

## Verification and screenshots

Local optimized Next.js production build succeeded. TypeScript succeeded; Vitest ran 76/76 passing tests. ESLint had zero errors and one existing `window.location.assign()` navigation warning in `app-shell.tsx` line 59. The three new focused Chromium regressions passed. A separate production-build capture visited all 12 routes at 1366×768, 1440×900, and 1920×1080: 36/36 HTTP 200, with no document horizontal overflow or uncaught page errors in its sampled settle window. Before/after captures, plus the 36 local route images and mobile dark/light samples, are in ignored `frontend-v2/test-results/`; they are local QA artifacts, not published assets. The capture at 1366px on Forecast occurred while geography tiles were still loading; loaded live map inspection verified the map panels and overlays.

The full Playwright run executed 38 tests: 37 visibly passed and one failed. The failure was `release-consistency.spec.ts`'s requirement for at least one HTTP-200 vector tile from `tiles.openfreemap.org` in 25 seconds. This machine's shell-launched browser was denied outbound internet access; the same suite's offline fallback test passed, as did the local rainfall/map-science tests. The runner then remained open during Windows web-server teardown after all 38 results were printed and was interrupted, so there is no clean final Playwright process exit to claim. Axe checks in the existing suite passed for Casebook and Extreme Rain and cover the core demo path, rather than every possible state of every route. Browser snapshots do not substitute for complete WCAG certification.

The frontend-only diff contains no `data/` or `experiments/` changes. `FINAL_TEST_READY`, `FINAL_TEST_RESULT`, and Phase 4J/4K/4L scientific artifacts were not modified. The API proxy/rewrite and backend were not edited, so backend regression tests were outside this change scope.

## Deployment and decision

This local correction requires a reviewed commit and push of the frontend/report changes, followed by the repository's Vercel Git deployment and a post-deploy visual check at 1366px and 390px. Render requires no redeployment for this frontend-only diff. No push or deployment was performed in this pass. Until Vercel deploys, the three P1 defects remain visible on the public site, even though the local production build is repaired. The live release gate is `LIVE_FRONTEND_POLISH_BLOCKED`: the public site still contains those material visual defects and the online vector-tile test cannot pass in the current shell network environment. Local frontend repairs are ready for review.
