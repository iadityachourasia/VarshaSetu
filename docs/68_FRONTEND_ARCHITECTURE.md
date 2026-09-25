# Phase 3A Frontend Architecture

## Scope and cutover boundary

`frontend-v2/` is the independent Next.js application. The original Vite
`frontend/` remains untouched and recoverable. Phase 3A reads frozen
`/api/science` artifacts only. No model training, GRIB decoding, scientific
recomputation, new year acquisition, or legacy 409-gate removal occurs.

The pinned runtime is Next.js 16.3.6, React 19.3.0, TypeScript 5.9.3,
Tailwind 4.3.3, shadcn 4.21.0 with Base UI 1.8.0, MapLibre GL JS 6.11.0,
TanStack Query 5.103.2, Zod 4.6.5, Recharts 3.10.1, Motion 13.4.1,
Lucide 1.47.0, Playwright 1.63.0 and Vitest 5.0.1. TypeScript 6 was not
selected because the pinned OpenAPI generator has a TypeScript 5 peer range.
These versions are exact in `frontend-v2/package.json` and the lockfile.

## Routes and ownership

| Route | Scientific purpose | Data boundary |
|---|---|---|
| `/` | overview, primary test result and capability entry | server-rendered artifact summaries |
| `/forecast` | synchronized Raw, M2-corrected and IMD 2-D fields | client interaction over frozen case arrays |
| `/extremes` | distinct Heavy / Very Heavy calibrated probability fields and reliability | client interaction over frozen probability arrays |
| `/districts` | area-weighted district table, geometry and detail | frozen case table + pinned geometry |
| `/verification` | M0–M4, probability metrics, FSS and honest comparison | server summary + lazy client charts |
| `/methodology` | source/lineage, temporal split and limitations | server-rendered status/provenance |

Server Components fetch the index, verification, and provenance summaries.
Client components are isolated to maps, chart controls, sorting, case
navigation, and theme state. Case arrays use TanStack Query keyed by case ID
and product, avoiding duplicate fetches during navigation. Zod validates
the external JSON boundary; `src/lib/api/openapi.d.ts` is generated from the
FastAPI OpenAPI schema. `SCIENCE_API_URL` is a server-only Next rewrite
target (default localhost:8000); the browser sees only same-origin
`/api/science` URLs. No filesystem path or private key is shipped to clients.

## Grid rendering

The API supplies EPSG:4326, 49 latitude centers, 49 longitude centers,
0.25° cell size, and south-to-north/west-to-east order. `gridFeatures` creates
at most 2,401 polygons in one MapLibre GeoJSON source, excluding masked or
null cells. The worker is pinned locally in `frontend-v2/public/`; no
third-party basemap tiles are requested. The three rainfall maps use the same
extent, mask and palette. MapLibre camera changes propagate through one
guarded synchronization callback; hover/click and keyboard row/column
selection expose exact cell values. The probability map has a separate
0–100% legend. District boundaries are a separate GeoJSON layer; district
fills use actual area-weighted mean rainfall values, not interpolated colors
unrelated to the table.

### Phase 3B/3C rendering supersession (2026-09-24)

The paragraph above describes the original Phase 3A renderer and is retained
as historical architecture evidence. The current implementation is specified
in `docs/73_PROFESSIONAL_MAPPING_SYSTEM.md`: it uses one mask-aware MapLibre
image/raster source per 49×49 field, with Scientific Grid and display-only
Weather Visualization modes. Online geography uses the official OpenFreeMap
Dark/Positron vector styles, OSM-derived tiles and visible attribution;
the pinned district-geometry fallback is available when online tiles fail.
The `gridFeatures` helper remains only as a tested legacy/utility path, not
the current rainfall rendering path. The model arrays and inspection values
are unaffected by this presentation supersession.

## Safe migration / rollback

Run the backend, then build and start `frontend-v2/` as a separate service.
Verify all six routes, the Playwright demo path, and read-only API hashes.
Only then direct the demonstration URL to the new service. Keep the legacy
service and files in place. Rollback is a routing change back to the legacy
service; it does not mutate or replace any science artifact. The old legacy
scientific routes stay blocked in either UI. This document does not declare
operational deployment readiness.
