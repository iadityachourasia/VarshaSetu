# Forecast Data Contract

Status: Phase 1A contract with Phase 1C archive corrections; no forecast files
are training-eligible.

## Scope

This contract applies to every forecast variable, member, initialization, and
grid stored by VarshaSetu. A filename or variable name never proves forecast
identity. Records that fail this contract are quarantined before pairing.

## Required record fields

| Field | Type | Rule |
|---|---|---|
| `source` | string | documented provider/archive |
| `source_documentation_url` | URL | official product documentation |
| `source_manifest_id` | string | immutable file/byte-range manifest |
| `model_name` | string | e.g. GEFS |
| `model_version` | string | e.g. v12 reforecast |
| `ensemble_member` | string | never infer silently; `c00`, `p01`, etc. |
| `initialization_time_utc` | UTC timestamp | issue/model initialization time |
| `valid_time_utc` | UTC timestamp | strictly later than initialization |
| `lead_hours` | integer | exactly valid minus initialization |
| `accumulation_start_utc` | UTC timestamp/null | required for accumulated variables |
| `accumulation_end_utc` | UTC timestamp/null | equals valid time for rainfall |
| `accumulation_hours` | integer/null | positive and timestamp-consistent |
| `latitude`, `longitude` | coordinate arrays | finite, unique, ordered by grid metadata |
| `grid_definition` | object | ID, CRS, bounds, spacing, coordinate convention |
| `variable` | string | canonical name |
| `native_variable` | string | GRIB short name |
| `level` | string | surface/column/pressure level, never implicit |
| `source_units` | string | decoded GRIB unit |
| `units` | string | canonical unit after documented conversion |
| `available_at_issue_time` | boolean | must be true for operational predictors |
| `quality_flags` | array | missing/duplicate/negative/regridding flags |

`backend/app/data/contracts.py::ForecastGridRecord` implements the core timing,
unit, grid, and issue-time rules. Storage schemas may add fields but may not
weaken them.

## Canonical variables and units

| Canonical | GEFS native | Level | Source unit | Canonical unit |
|---|---|---|---|---|
| `nwp_precip_accum` | `apcp_sfc` object / `tp` GRIB | surface | kg m**-2 | mm |
| `nwp_u850` | `ugrd_pres` | 850 hPa | m s-1 | m s-1 |
| `nwp_v850` | `vgrd_pres` | 850 hPa | m s-1 | m s-1 |
| `nwp_q700` | `spfh_pres_abv700mb` | 700 hPa | kg kg**-1 | kg kg**-1 |
| `nwp_z500_height` | `hgt_pres_abv700mb` | 500 hPa | gpm | gpm |
| `nwp_mslp` | `pres_msl` | MSL | Pa | Pa or explicitly converted hPa |
| `nwp_tcwv` | `pwat_eatm` | entire atmosphere | kg m-2 | kg m-2 |

The decoder must confirm actual GRIB units. This table is not permission to
override file metadata. Unknown units fail; conversions record source unit,
factor/formula, software version, and test evidence.

## GEFS rainfall timing

For each 00 UTC initialization, produce:

```text
day1_24h = sum of exact 3-hour increments from lead +3 through +27
day2_24h = sum of exact 3-hour increments from lead +27 through +51
day3_24h = sum of exact 3-hour increments from lead +51 through +75
```

Intervals are half-open. The adapter reads GRIB `stepRange`; it does not infer
the step from array position. Nested six-hour totals are differenced against the
corresponding first three-hour total. `reconstruct_accumulation_window` fails
on incomplete or materially negative results.

Phase 1C decoded all six variables at +24/+48/+72 for 31 control forecasts.
The Q700 object-family correction above is based on the live official index and
decoded GRIB metadata, not the filename alone. Detailed evidence is in
`39_PREDICTOR_AVAILABILITY_REPORT.md`.

## Validation invariants

1. `initialization_time_utc < valid_time_utc`.
2. `lead_hours == valid_time_utc - initialization_time_utc` exactly.
3. Accumulation fields are all present or all absent.
4. `accumulation_hours > 0` and equals end minus start.
5. Rainfall accumulation end equals valid time.
6. Source, model, version, member, variable, level, and units are non-empty.
7. Dynamic operational features have `available_at_issue_time=true`.
8. Latitude is within -90..90 and longitude follows the declared convention.
9. Source file/range has a 64-character SHA-256 and positive byte count.
10. `data_type=forecast`; reanalysis is rejected from the raw-NWP adapter.
11. Duplicate keys `(source, model_version, member, init, lead, variable, level,
    grid_id)` are errors unless byte-identical.
12. Non-finite data and undocumented missing sentinels are errors.

## Storage representation

Preserve member and lead dimensions until ensemble statistics are computed.
Recommended processed form is chunked, compressed array storage with explicit
CF-style coordinates and provenance attributes. A required rainfall key is:

```text
(initialization_time_utc, product, ensemble_member, y, x)
```

Derived ensemble mean/spread are new variables with lineage to all member
manifest IDs; they do not replace raw members.

## Versioning and quarantine

Model upgrades are different datasets. Operational GFS/GEFS cycles may not be
silently merged with GEFSv12 reforecast. Failed records go to a quarantine
inventory with reason codes; they are never coerced merely to preserve sample
count.
## Phase 1D packing-negative clarification (2026-09-19)

For nested accumulation differences, decoded precision is derived from both
`binaryScaleFactor` and `decimalScaleFactor`: `q = 2^E * 10^-D`. A negative
residue may be normalized only when its magnitude is within both half the sum
of the two source quanta and the independent 0.1 mm operational cap. Larger
values fail the affected member-product closed. Binary scaling may not be
ignored merely because decimal scale factors match.

## V2 rainfall-contract supersession

The earlier eight-synthetic-three-hour description and Phase 1D 0.1 mm cap
above describe v1 only. For every v2 acquisition, doc 51 is authoritative:
construct a metadata-derived exact cover that lexicographically minimizes
`(subtractions, segments)`, use native intervals where possible, and perform
only the unavoidable boundary subtraction. Any negative difference must be
within half the sum of the two source packing quanta; only
representation-explained cells are normalized. There is no blanket clipping
and no separate v1 operational cap. The target windows are unchanged.
