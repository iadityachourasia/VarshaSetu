# Frontend hardening and polish — 2026-09-28

## Scope and scientific boundary

This continuation updates `frontend-v2` presentation, loading behavior, and browser coverage. No scientific data, model, threshold, score, or caveat was changed. The 2019 reforecast and 2023–2025 operational-era experiments remain separate. The 2025 M1 comparison remains preselected primary; M2 remains secondary. Track B district aggregates remain unavailable.

## Reproduction and fixes

In a clean live Chromium run, `/forecast?demo=official` briefly displayed “Loading verified case” and then rendered its three maps. The case-list, detail, rainfall, probability, regime, and ensemble requests completed with HTTP 200. Live `/verification` displayed five `svg.recharts-surface` elements. An endless hang and blank charts were **not reproduced** on the public site, so the case-state and chart work is hardening rather than a confirmed production bug fix.

The case catalogue now distinguishes pending, failed, unavailable, integrity-failed, and empty responses. A selected case missing from the frozen presentation index produces a visible error instead of leaving the detail query disabled and pending. Operational and science fetches have 20-second client and 25-second server timeouts. A timed-out operational response is eligible for the existing verified static fallback; a real API integrity failure or malformed scientific response remains a hard stop.

A local production trace revealed an additional concrete bug during validation: when a response sent headers but stalled while streaming JSON, the timeout escaped the fetch `try` block and was mislabeled as a contract integrity failure. The body read now classifies interrupted transfers as `NETWORK_FAILURE`, while malformed JSON and schema failures remain integrity failures. The browser regression stalls a rainfall response and verifies that the cached-data indicator and map appear after the timeout.

Seven duplicated chart wrappers now use `ChartFrame` with a nonnegative initial Recharts dimension. Verification and operational chart series retain the existing model identity colors. This improves first render and sizing but does not establish that SVG is included in raw server HTML; the browser regression asserts actual client-rendered SVG.

## Visual implementation

The existing dark-teal identity was retained. Inter and JetBrains Mono are bundled with their OFL licenses and loaded through `next/font/local`; the local production build could not fetch `next/font/google` at build time. A pre-paint theme script applies the stored theme before hydration. CSS tokens establish consistent type, spacing, radii, shadows, focus treatment, tabular numerals, card surfaces, table styling, and state-message spacing. Direct 7–10px font declarations were raised to an 11px floor.

The full 248px sidebar remains labeled at 1366px and 1440px. It becomes an icon rail below 1180px, and a focus-managed drawer below 760px. The drawer closes via Escape or overlay and returns focus to its toggle. Header controls share height and alignment, wrap when needed, and preserve the specified accessible names. Forecast controls, map grids, verification charts, the Overview hero and benchmark cards, and scientific tables were checked across desktop, tablet, and mobile widths.

An expanded axe review identified a decorative regime bar with invalid ARIA, missing keyboard focus on three horizontally scrollable tables, and contrast failures in light-theme chrome and the Observations heatmap. The bar is now hidden from assistive technology because its label and number are already visible. Scrollable tables are keyboard reachable. Light accent and caution text was darkened, while heatmap tint ranges were bounded separately by theme so its relative shading remains readable without changing the values.

## Verification

- TypeScript: passed.
- Vitest: 79/79 passed.
- Optimized Next production build with the Render API origin: passed.
- ESLint: zero errors; one pre-existing `window.location.assign()` navigation warning remains in `app-shell.tsx`.
- Full Playwright run against the local production build and live Render dependency: **41/41 passed**, including a repeat after the final accessibility repairs. This includes Track A, Track B, online vector geography, offline map fallback, Story Mode, responsive layouts, and the existing axe checks for serious/critical findings.
- Expanded axe audit after the targeted repairs: **48/48 scans passed**, covering all 12 routes in both themes at 1440px and 390px, with no serious or critical findings.
- The stalled-rainfall browser regression showed `Cached frozen presentation data` and a ready map in 23.7 seconds. A direct post-fix local production run received the operational fields and rendered three maps.

The screenshot sweep script captures 12 routes plus three Forecast year variants in dark and light themes at 1440, 1366, 820, and 390 pixels. It records HTTP status, document overflow, page errors, map/chart surfaces, applied theme, and a CSS validity gate using readable local CSSOM sheets and expected computed tokens. Representative pre-deployment public screenshots are saved in ignored `test-results/polish-before/`; local captures are saved in ignored `test-results/polish-sweep/`.

The final local sweep passed **120/120** captures: HTTP 200, zero document overflow, zero uncaught page errors, correct theme, and a passing CSS gate in every state. All eight Verification captures contained five chart SVGs. The Forecast variants showed ready maps in the captured states. A mobile Verification section-heading squeeze found during the visual review was corrected before this final sweep.

## Deployment

The deployment branch is `master`, as confirmed by the user and `docs/102_FREE_DEPLOYMENT.md`. The frontend is served by Vercel and the frozen-data backend by Render. This change needs only a Vercel redeployment. Verify the public site after pushing `master`; a passing local suite alone does not establish that the new frontend has reached production.
