# Phase 8A: synoptic chart and the context-grid georeferencing check

Date: 2026-10-01. No model, protocol or evidence file was changed. This phase turns six already-served forecast fields into a synoptic chart and settles, with evidence,
how those fields are georeferenced.

## The problem

The Forecast page showed the six wide-domain forecast fields only as separate shaded scalars on the 49 by 49 rainfall grid. A synoptic view (wind direction, height and pressure
patterns) needs the native 51 by 81 grid, and the served atmosphere grids carry **no coordinate sidecar**: the API itself said so. Drawing them on a map requires coordinates,
and assuming them would have been an unverified claim.

## Georeferencing: verified, not assumed

The frozen context-grid definition in code (`backend/app/data/monthly_qc.context_coordinates`) is 5 to 30 degrees N and 55 to 95 degrees E at 0.5 degrees, row 0 at 5 degrees N,
column 0 at 55 degrees E. The Track B grids carry no stored coordinates, but the Track A NetCDF files do. `scripts/verify_context_grid.py` compares the seasonal-mean Track B 2024
field with the seasonal-mean Track A 2018 field, whose coordinates are stored, in index space, for the assumed alignment and for flipped and shifted alternatives:

| Field | Assumed alignment | Latitude flipped | Longitude flipped | Best one-cell shift |
|---|---:|---:|---:|---:|
| Precipitable water | **0.984** | 0.279 | 0.219 | 0.975 |
| Sea-level pressure | **0.991** | -0.393 | 0.618 | 0.981 |
| 850-hPa zonal wind | **0.980** | -0.534 | 0.767 | 0.975 |
| 500-hPa height | 0.922 | 0.322 | 0.403 | 0.937 |

For three fields the assumed alignment is the best of every alternative tried, and any flip is far worse, so orientation and extent are confirmed to the resolution of this test.
The 500-hPa height field is too smooth to resolve a one-cell shift (its best shift is marginally higher, which interannual variability explains); it comes from the same
pipeline as the other three. This is a statement about alignment to within about one cell (0.5 degrees), not a survey-grade georeferencing.
The backend test also checks physical plausibility in the stated orientation: precipitable water over the Arabian Sea exceeds that over the dry Iran/Pakistan desert by more
than 15 kg/m2 in three different monsoon cases, which a flipped grid would reverse. The rendered chart agrees with known July monsoon structure (strong low-level westerlies over
the Arabian Sea and peninsula, a heat low over Pakistan and north-west India, the subtropical ridge over Arabia, moisture peaking over Bengal and the Bay of Bengal).

## What was built

| Item | Where |
|---|---|
| `GET /api/science/operational/{year}/cases/{id}/atmosphere/{field}` now also returns `latitude_centers`, `longitude_centers` and `grid_spacing_degrees`, with a provenance note that states the check above | `backend/app/api/operational.py` |
| Marching-squares contours (saddles resolved, missing cells never drawn), wind arrows in map-conformal geometry (longitude stretched by 1/cos latitude so arrows point where the wind blows), contour-level and interval selection, shaded cells | `frontend-v2/src/lib/synoptic/geometry.ts` |
| Synoptic chart: shaded precipitable water or 700-hPa humidity, 850-hPa wind arrows (one per degree), 500-hPa height contours, sea-level pressure isobars, rainfall-domain outline, layer toggles, contour labels, a colour key and a point reader with exact values; works with the online and the offline basemap | `frontend-v2/src/components/synoptic/synoptic-chart.tsx`, option "Synoptic chart" in the Forecast variable list |
| Zod schema requires the coordinate arrays to match the value matrix and rejects a mismatch | `frontend-v2/src/lib/api/operational.ts` |

## Honesty rules kept

- Every layer is computed from the frozen forecast values; nothing is smoothed, filled or invented, and a cell with a missing value is never drawn.
- The chart states that these are control-member forecast fields, not an analysis, and not a causal explanation of any correction.
- A case whose atmosphere failed quality control shows a message and no chart; an integrity failure is a hard failure, never a chart.
- Operational-era track only: the 2019 reforecast track has no wide-domain chart in the app. One snapshot per case at its own lead; no animation.

## Tests

- Backend `test_atmosphere_api.py` (8): coordinates equal the frozen definition for all six fields, extent and spacing, orientation plausibility in three cases, refusals unchanged.
- Vitest `geometry.test.ts` (11): linear-field contour at the exact coordinate, closed contour of a bowl at the right radius, no drawing through missing values, saddle handling, label
  anchoring, arrow direction and bearing, conformal stretch at 60 degrees latitude, subsampling, calm and missing points, shaded cells; and two more in `operational.test.ts`
  for the coordinate contract.
- Playwright `synoptic.spec.ts` (7): all layers drawn from the 51 by 81 fields, toggles change what is drawn, the point reader equals the API at a chosen point, a quality-control
  failure and an integrity failure show messages and no chart, a 2024 case on a phone screen without overflow, the option exists only for the operational-era experiment.

Two defects found and fixed by these tests: the map container was not mounted during loading, so the map initialised in a zero-size container and stayed black; and a layer toggle
was silently ignored while basemap tiles were still loading.

## Coverage

`SYNOPTIC-OVERLAYS` moves from PLANNED to IMPLEMENTED as a non-mandatory extra, with its scope limits stated on the row. No official requirement status changes.

Gate: `P2_1_SYNOPTIC_COMPLETE`.
