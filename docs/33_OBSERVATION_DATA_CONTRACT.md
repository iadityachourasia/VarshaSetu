# Observation Data Contract

Status: Phase 1C evidence update. Official IMD 2019 has passed source QC and 93
exact product-date pairings; no IMERG file has been acquired.

## Primary reference

The primary reference is IMD 0.25° Daily Gridded Rainfall, a gauge-based daily
analysis over India. Its canonical day ends at 08:30 IST (03:00 UTC). The exact
file/product version, current coverage endpoint, download terms, fill value, and
hash must be captured from each acquired official file rather than assumed.

## Required record fields

| Field | Type | Rule |
|---|---|---|
| `source` | string | India Meteorological Department |
| `source_documentation_url` | URL | official product/method page |
| `source_manifest_id` | string | immutable file manifest |
| `product` | string | 0.25° Daily Gridded Rainfall |
| `version` | string | file/document declared; never guessed |
| `valid_date` | date | date on which the daily window ends |
| `accumulation_start_utc` | UTC timestamp | valid date minus 24 h at 03 UTC |
| `accumulation_end_utc` | UTC timestamp | valid date at 03 UTC |
| `accumulation_hours` | integer | exactly 24 |
| `latitude`, `longitude` | coordinate arrays | source coordinates preserved |
| `grid_definition` | object | CRS, bounds, spacing, order, mask |
| `rainfall_mm` | float grid | nonnegative valid cells; missing stays missing |
| `quality_status` | string/flags | source and local QC state |
| `missing_value_policy` | string | derived from NetCDF attributes/documentation |

`backend/app/data/contracts.py::ObservationGridRecord` enforces the core UTC,
window, grid, and unit invariants.

## Time convention

For IMD valid date `D`:

```text
accumulation_start_utc = D-1 03:00:00+00:00
accumulation_end_utc   = D   03:00:00+00:00
accumulation_hours     = 24
```

The interval is `[start, end)`. Store UTC as authoritative and derive the
08:30-08:30 IST label only for display. A date-only join is forbidden unless the
two explicit windows have first been shown equal.

## Missing and quality data

The acquired official 2019 file declares both `_FillValue=-999.0` and
`missing_value=-999.0`. The reader converts these values to a mask and retains
the source declaration in lineage; missing is never zero. Phase 1C matched 93
product dates (33 unique dates, 2019-07-02 through 2019-08-03) without shifting a
date. Every target crop contained 1,301 valid and 1,100 masked cells.

## Secondary reference: GPM IMERG Final V07

IMERG Final V07 is a separate 0.1° half-hourly global precipitation product. The
Final Run is appropriate for retrospective research and uses monthly gauge
analysis adjustment; Early/Late products are latency products and are not the
default retrospective truth. Earthdata/PPS authentication and product terms must
be followed.

Aggregate the exact half-hour intervals covering 03:00 UTC to 03:00 UTC. Record
the IMERG variable, rate-to-depth conversion, count of expected half-hour slots,
quality fields, and Final V07 granule hashes. Any missing slot blocks that daily
grid unless a pre-declared missing-data policy explicitly marks it unusable.

IMERG scores are reported as secondary sensitivity/cross-check results and are
never labeled IMD or silently substituted into the primary series.

## Spatial contract

- Preserve native reference values and mask before regridding.
- IMD native 0.25° is the target verification grid.
- IMERG 0.1° is conservatively aggregated/regridded to the same target grid for
  comparable secondary scores.
- Store cell bounds; do not treat center points as polygons.
- Record source/target grid hashes and regridding-weight hash.
- Use an explicit common valid mask per paired field; do not compare different
  spatial support.

## Pairing key and acceptance

An accepted pair has:

```text
(forecast_initialization_time_utc, product, accumulation_start_utc,
 accumulation_end_utc, target_grid_id, observation_manifest_id)
```

Acceptance requires exact window equality, valid source manifests, successful
unit conversion to mm, spatial alignment QC, and no missing required forecast
steps. A product without all evidence remains quarantined and training-ineligible.
