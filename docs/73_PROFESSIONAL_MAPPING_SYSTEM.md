# Phase 3B — Professional Meteorological Mapping System

This is a presentation-only upgrade of `frontend-v2/`. No Phase 2B/2C model, field, event definition, FSS, district calculation, or verification value is changed. The legacy frontend remains intact.

## Architecture and geographic source

Forecast, Extreme Rain and District Intelligence use shared MapLibre lifecycle, settings and controls. The online basemap is OpenFreeMap's OSM-derived vector-tile Dark or Positron style. Defaults are `https://tiles.openfreemap.org/styles/dark` and `/positron`; `NEXT_PUBLIC_OPENFREEMAP_DARK_STYLE` and `NEXT_PUBLIC_OPENFREEMAP_LIGHT_STYLE` permit an approved replacement or self-hosted style. These are public browser configuration, not secrets. MapLibre instances survive case, display and opacity changes. Failure to load a style or repeated tile errors switches to a local fallback built from pinned district geometry. It keeps the science layers usable, but has no roads, city labels, full state/coastline coverage, terrain or satellite imagery. No licensed terrain asset was present, so no relief option is claimed.

Layers are ordered geographic background → scientific raster or district choropleth → outlines and selected cell → online labels. Raster insertion uses the first symbol layer in the active style, not a provider-specific fixed ID. Maps remain north-up and 2-D.

## Grid and visual semantics

The target grid is 49×49 at 0.25°. The raster uses validated outer bounds in MapLibre's NW, NE, SE, SW image-corner order. API rows are south-to-north, so output pixels are flipped north-up. Scientific Grid mode emits one nearest-neighbor pixel per exact source cell, preserving the mask. Weather Visualization subdivides valid cells eightfold and bilinearly interpolates *numerical values before palette mapping* only when all neighboring cells are valid; otherwise it uses the containing cell. Invalid source cells stay transparent. This display does not create new meteorological resolution. Hover/click/keyboard inspection always reads original API arrays. Models, thresholds, district products, FSS and RMSE are untouched. Raw, corrected and observed use one precipitation palette and legend. Probability fields use a separate 0–100% scale.

The controls expose Dark/Light geography, Weather/Scientific display, opacity, boundary visibility, zoom, reset and forecast fullscreen. Desktop forecast cameras synchronize on user movement; selected cells are outlined on all three. Mobile renders one active forecast map and preserves selection between Raw/Corrected/Observed. District colors remain sharp and frozen; no raster interpolation is applied. Phase 3C presentation supersession: the inspector now initially chooses the case-valid district with the highest **forecast corrected mean**, breaking ties by district ID. This deterministic example-selection rule uses no observed rainfall and is not a skill claim. Polygon/table selection highlights and zooms. The UI distinguishes case-valid rows from all domain-intersecting source geometries.

## Attribution, licensing and limitations

Visible, keyboard-accessible online attribution links to OpenFreeMap, OpenMapTiles and © OpenStreetMap contributors/license. Offline attribution links to geoBoundaries and ODbL 1.0. The pinned 2021 ADM2 source, hashes, 188 intersecting geometries, and unresolved 736-metadata versus 735-feature discrepancy remain documented in `docs/65_DISTRICT_PRODUCT_METHODOLOGY.md`. Attribution must remain visible in the demo video. OpenFreeMap's public instance has no guaranteed availability. Offline geographic detail is limited to the pinned district polygons; full offline vector tiles would require separate provisioning. Existing approximate polygon-overlap weights and scientific district outputs are unchanged.

Phase 3C provider compatibility note: the public Dark style references a
`circle-11` city-marker image absent from its served sprite sheet. The
frontend now supplies only that 11-pixel neutral cartographic marker through
MapLibre's missing-style-image resolver. This prevents the missing-image
warning and preserves city markers without altering any scientific layer.

## Performance and QA

Each 49×49 field is converted once per values/mask/display mode via a deterministic WeakMap cache, then updated as a MapLibre image source. Camera movement does not regenerate pixels. Mobile uses one WebGL context instead of three. The MapLibre worker bundle is local. Unit tests cover corner order, north-up orientation, exact cells, masks and non-mutation. Browser tests cover three-map sync, exact inspection after style/display changes, opacity, zoom/reset, mobile switching, district selection and simulated online-style failure. Responsive screenshots and accessibility checks are in `docs/71_FRONTEND_TESTING_AND_QA.md`.

Official references: [OpenFreeMap quick start](https://openfreemap.org/quick_start/), [OpenFreeMap styles](https://github.com/hyperknot/openfreemap-styles), [MapLibre image source](https://maplibre.org/maplibre-gl-js/docs/API/classes/ImageSource/).

## Cartographic label visibility correction (2026-09-24)

The original Phase 3B implementation drew district outlines but no district-name
symbol layer. OpenFreeMap Dark supplies city/state labels, not the 188 pinned
district names, and its served city/state text was gray on a dark map. The
frontend now derives deterministic point-on-surface candidates from the
existing geoBoundaries ADM2 polygons, restricting placement to the validated
target-domain extent. It uses the source's `district_name` and `district_id`
without renaming or inventing features; geometric placement is presentation
only and does not change overlap weights or district rainfall products.

One cached point source feeds three density tiers: a spatially thinned set of
up to 12 regional reference names at initial extent, additional names from
zoom 5.7, and the remainder from zoom 7.2. Normal tiers use MapLibre collision
management; the sparse reference tier and a single selected district can
override collisions so a regional name is not completely suppressed by
basemap labels. Selected districts also keep the existing polygon outline.
All district symbols are above scientific rasters, polygon fills, boundaries,
and ordinary basemap labels. The point source updates when asynchronous
geometry arrives after map mount, including on Extreme Rain. Hovering a map
district reveals its name; the district table remains the keyboard-accessible
selection route.

The online styles declare `https://tiles.openfreemap.org/fonts/{fontstack}/{range}.pbf`
and use Noto Sans Regular/Bold, which the new online district text layers
reuse. Dark city/state text is lightened and given a navy halo; Positron keeps
dark text with a light halo. Only the named major city/state layers, minor
Dark place labels, state boundary, and Dark highway line/road-label layers are
adjusted. Minor Dark place names wait until zoom 6. District boundary strokes
are softened. The local offline style has no glyph endpoint, so its district
symbol layers use locally generated canvas text icons with the same real names;
they require no tile or glyph network request. Offline maps still cannot show
city/state names or roads because those features are absent from the pinned
ADM2 source. Placement is approximate for narrow/concave/multipart source
polygons and does not claim cartographic or administrative centroid accuracy.

Layer order and collision behavior follow the [MapLibre symbol style
specification](https://maplibre.org/maplibre-style-spec/layers/#symbol).
