# Route Inventory — Phase 5B Demo Freeze

Status: honest, code-derived classification of all 12 navigable routes for
judge-facing demo purposes. Not a claim about live production readiness —
see `docs/14_ACCEPTANCE_CRITERIA.md` and AGENTS.md section 4 for the
separately governed Phase 0/1 legacy readiness gate, which remains blocked.

## How routes were classified

Each route was read at the source (`src/app/<route>/page.tsx` and the client
components it renders) to determine its actual data dependency, then
exercised where it could genuinely be exercised in this environment:

- **SSR reachability**: every route was fetched from a clean
  `next build` + `next start` in this sandboxed container (which has no
  reachable Track A or Track B backend — see `docs/97`/`docs/98` section 2
  for the full investigation). Every route returned HTTP 200 with either
  real content or an honest, non-fabricated unavailability message — none
  crashed or produced a 500.
- **Client-side / interactive behavior**: verified with a real headless
  Chromium (`/opt/pw-browsers/chromium`) via Playwright, for the subset of
  routes and specs that do not require a live backend (client-only pages,
  or specs that mock the live-API route explicitly). Specs that need a real
  backend with the real `experiments/` corpus were written and type/lint/
  build-checked but **not executed** in this session — this matches every
  prior phase's documented constraint and is not new to Phase 5B.

## Legend

- **WORKING** — fully functional for its designed scope; genuinely
  unavailable states (if any) are clearly, honestly labeled, not silent
  failures or fabricated data.
- **WORKING_WITH_LIMITATION** — functional, but with a real, permanent,
  honestly-labeled scope restriction a presenter/judge should know about in
  advance (e.g., only one track or one year is implemented).
- **NOT_FOR_DEMO** — none. No route in this inventory needed this label;
  every route either works within its documented scope or degrades to an
  honest message. (Kept as a category per the Phase 5B brief; the table
  below states explicitly why nothing landed here.)

## Table

| Route | Classification | Backend dependency | Notes |
|---|---|---|---|
| `/` (Overview) | WORKING | Track A live (`/status`, `/model-comparison`, `/verification`, `/demo-cases`); no client fallback | Entry point headline card. Requires the Track A backend to be healthy — the official demo launcher's preflight script (`scripts/demo/preflight-demo.ps1`) checks this before every demo start, so this is a documented precondition, not a bug. Confirmed: honest `ErrorState`, no fabricated numbers, when Track A is unreachable. |
| `/forecast` | WORKING | Track A live (default/2019); Track B client + static fallback (`?experiment=operational`) | `?demo=official` (new, Phase 5B) redirects to the canonical Track B case via a real query-param redirect — never constructs a result object itself. Verified end-to-end this session with real headless Chromium. |
| `/casebook` | WORKING | Track A live (default/2019); Track B client + static fallback (`?experiment=operational`) | 2017/2018 (non-final-test reforecast years) show an intentional, honestly worded "no independent casebook published" message — this is by design, not a defect. |
| `/extremes` | WORKING | Track A live (default/2019); Track B client + static fallback (`?experiment=operational&year=2025`) | Track B branch (all 4 detection modes, spatial FSS, reliability) was extensively built and axe/responsive-checked with mocked live-API routes in this session (0 critical/serious violations, 0px horizontal overflow at 3 breakpoints). Other operational years show an honest scope message. |
| `/districts` | WORKING_WITH_LIMITATION | Track A live + geometry (default/2019, full polygon-overlap aggregation); Track B district product for 2024/2025 only (Phase 4N, `docs/107`; 2023 none; district-level verification in the Verification Lab, `docs/113`) | The 2023-2025 historical operational corpus was frozen without a district aggregation step. The page states this explicitly (`OperationalDistrictsUnavailable`) rather than fabricating a table from unaggregated grid cells — a genuine, permanent, honestly-labeled gap, not a bug to fix under this freeze. |
| `/ensemble` | WORKING_WITH_LIMITATION | Track B client + static fallback, **2025 only** | The matched five-member-ensemble-vs-calibrated-ML comparison exists only for the 2025 final-test matched subset. 2019, 2023, and 2024 all show an explicit, honest "not available for this selection" message. Presenters should not navigate here expecting any other year. |
| `/regimes` | WORKING_WITH_LIMITATION | Track B client + static fallback only; **no Track A page at all** | There is no dedicated regime-intelligence UI for the 2019 reforecast track — Track A's forecast-only pseudo-regime methodology is documented in prose only (`/methodology`) and in the Track-B-scoped provenance DAG on `/audit`. Track A selection here shows an honest redirect-style message, not an error. |
| `/verification` | WORKING (fixed this session) | Track A live for the 2019 section; Track B is either build-time-bundled JSON or its own static-fallback client component | **Bug found and fixed in this session**: the page previously combined the Track A fetch and the Track B section behind one `Promise.all().catch()`, so a Track A outage blanked the *entire* page — including the Track B content, which never needed Track A. Track A's fetch is now independent; on failure only its own section shows a scoped notice while the 2025 operational benchmark and the 7-tab `OperationalVerification` component still render fully. Verified against a clean rebuild in this session (both the failure-scoped and success paths). |
| `/observations` (Six-Season Observations) | WORKING | **None** — 100% build-time-bundled static JSON (`public/science/operational-v1/observations_six_seasons.json`), no live fetch attempted at all | The single most backend-independent route in the app; cannot fail due to a network or backend issue. Verified passing with real headless Chromium in this session. |
| `/quality` (Data Quality & Provenance) | WORKING | Track B client + static fallback | Verified reachable (HTTP 200, real content) via SSR check in this session; not covered by a dedicated Playwright spec in this repository yet (candidate for future coverage, not a defect). |
| `/methodology` | WORKING (fixed this session) | Track A live, only for two small strips (`method-status`, `provenance-band`); the pipeline/track-timeline/method-grid prose is static | **Same class of bug found and fixed**: ~90% of this page is static prose that never called an API, yet the whole page was gated behind one small `/status` call. Now the static content always renders; only the two small live-data strips degrade to an honest inline notice on failure. Verified against a clean rebuild. |
| `/audit` (Scientific Audit) | WORKING | **None** — provenance DAG, holdout governance timeline, and limitations panel are all sourced from frozen, checked-in data (`@/science/frozen/results`, `@/lib/provenance-dag`), no live fetch | The second fully backend-independent route. Verified passing (provenance DAG node click, holdout lifecycle, limitations panel) with real headless Chromium in this session. |

## Why nothing is NOT_FOR_DEMO

Every route was designed with an explicit fallback or an honest unavailable
message for the parts of its scope that are genuinely incomplete (no
district product for Track B, no ensemble comparison outside 2025, no
regime UI for Track A). None of the 12 routes crashes, hangs, or fabricates
data under any navigation state exercised in this session. The two routes
with a hard live-backend dependency and no fallback (`/`, and the Track A
branch of `/forecast`, `/casebook`, `/extremes`, `/districts`) are exactly
the routes the official demo preflight script checks before every demo
start — their dependency is a documented precondition of the launch
sequence, not an undocumented risk.

## What this session could not verify directly

Consistent with every prior phase in this project: this sandboxed container
has neither the Track A backend (blocked by a real, unbypassed hash-
integrity failure on the checked-out `artifact_manifest.json`) nor the
Track B `experiments/recent_historical/` corpus available. Every claim above
about a route's *live* rendering (as opposed to its honest degraded state)
rests on: (a) direct source reading of the page and its data-fetching path,
(b) the pre-existing, source-accurate Playwright specs written in earlier
phases against the real backend (`operational-track-b.spec.ts`,
`operational-extreme-verification.spec.ts`, `demo-flow.spec.ts`,
`release-consistency.spec.ts`, `mapping.spec.ts`, `demo-performance.spec.ts`
— type/lint/build-checked, not executed here), and (c) this session's own
real-headless-Chromium runs of the subset that needs no backend at all
(client-only pages, and specs that mock the live-API route). This gap is
identical in kind to every earlier phase's documented environment
constraint and is not a new risk introduced by this freeze phase.
