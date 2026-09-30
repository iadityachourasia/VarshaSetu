# Phase 2C District Product Methodology

## Geometry and provenance

The repository had no district geometry before Phase 2C. The pinned source is
the [geoBoundaries India ADM2 API metadata](https://www.geoboundaries.org/api/current/gbOpen/IND/ADM2/),
boundary ID `IND-ADM2-76128533`, 2021 districts, upstream revision `9469f09`.
Its metadata credits Pathways Data Pvt. Ltd. and `lgdirectory.gov.in`; the
license is [ODbL 1.0](https://opendatacommons.org/licenses/odbl/1-0/), which
requires attribution and may impose share-alike obligations on derived
databases. The pinned simplified GeoJSON is
`data/static/phase2c/geoBoundaries-IND-ADM2_simplified.geojson`, SHA-256
`d68db39cd3e2d0892af268e2b0454166368ce3b5b8a78fcda63069ec92a641db`
(7,979,916 bytes). `data/static/phase2c/SOURCE.json` records its source URL,
version, license and limitations. The source is traceable public geometry,
not a claim of official current Indian administrative boundaries.
The geoBoundaries API metadata advertises 736 ADM2 units, but the exact pinned
simplified GeoJSON contains 735 unique `shapeID` features (693 polygons and 42
multipolygons). The missing/merged unit is not identified; this discrepancy
limits any claim of complete national district coverage. The 188 retained
domain-intersecting features are counted from the actual file, not the API
metadata.

Only the 188 district polygons intersecting the existing 10–22° N, 68–80° E
validated meteorological grid are retained in the prototype geometry output.
No corpus or model was expanded to Madhya Pradesh. The full district polygon
is returned for each intersecting district, while aggregation weights are
restricted to intersections with the validated grid. Some intersecting
districts can have no valid paired cells in a particular forecast case and
are omitted from that case's table.

Scope note (Phase 4N, `docs/107`): the same pinned geometry and overlap-weight matrix are also used, unchanged, for a read-only
Track B (operational-era 2024/2025) district aggregation. Nothing in this methodology was altered.

## Grid-to-polygon calculation

Each 0.25° target center defines a 0.25° latitude-by-longitude cell polygon.
Its intersection with each district polygon is computed with Shapely. The
intersection's longitude/latitude planar area is multiplied by cosine of cell
center latitude as an approximate equal-area correction, then normalized
among valid paired grid cells of that district and case. This is more faithful
than unweighted center-point membership but is not geodesic-area exact. The
simplified source geometry can especially distort small/coastal overlaps.

For each valid historical forecast case/district the deterministic table
contains ID/name, valid intersecting cell count, area-weighted raw/corrected
mean, maximum corrected intersecting-cell value, area-weighted heavy and
very-heavy probability, area fraction of corrected cells above each rainfall
threshold, and the case-level dominant forecast-only prototype regime.
The maximum is a cell maximum, not an area-weighted extreme. Missing/invalid
cells have no weight. Area fractions are bounded to [0,1]. These are
retrospective historical products, not live district forecasts.

The weight matrix is `data/manifests/phase2c/district_weights.npy`, stored
without pickle and SHA-256 verified. The frontend-friendly geometry is
`data/manifests/phase2c/districts.geojson`; per-case tables are immutable
`cases/<case_id>.json` files in the same directory. All are covered by the
Phase 2C artifact manifest. Before distributing geometry or a derived district
database, review ODbL attribution/share-alike obligations.
