# Production Storage and Chunking

Status: Phase 1D design based on measured Phase 1C July storage.

## Format decision

Use immutable GRIB/index/IMD bytes for the source cache, Zarr v3 for normalized
multi-year arrays, JSON/CSV for manifests/QC, and NetCDF only for small immutable
audit/exchange artifacts. Zarr is selected because initialization-aligned chunks
support daily commits, monthly QC, time-slice model reads, and spatial FSS without
rewriting a multi-year monolith. NetCDF remains more convenient as one portable
audit file, but the July benchmark showed fixed-file append friction. Pin the
Zarr schema/version and verify reads on Windows and Linux before the first season.

Source cache, normalized arrays, manifests/QC, and regenerable training views
are separate. Source GRIB is stored once; daily NetCDF and consolidated Zarr are
not both retained across the production corpus.

## Exact chunks

| Array dimensions | Chunk | dtype | uncompressed bytes | Rationale |
|---|---|---|---:|---|
| forecast `(init,product,member,49,49)` | `(1,3,5,49,49)` | float32 | 144,060 | atomic daily rainfall bundle; one chunk for spatial FSS/all-member QC |
| observation `(init,product,49,49)` | `(1,3,49,49)` | float32 | 28,812 | exact daily products and full spatial slice |
| mask `(init,product,49,49)` | `(1,3,49,49)` | uint8 | 7,203 | same access geometry as observation |
| atmosphere `(init,lead,variable,51,81)` | `(1,3,1,51,81)` | float32 | 49,572 | daily commit, variable-selective training, full context map |

Chunks are small enough for retry and random initialization reads but large
enough to avoid cell-level object explosion. Write a staging group per daily
unit, promote only after child QC, and consolidate metadata only after the month
gate. Do not modify accepted chunks in place.

## Measured-based 20-year projection

Scaling July's 31 initialization measurements by `2440/31` gives:

| Category | Projected bytes |
|---|---:|
| NOAA precipitation | 97,634,994,401 |
| NOAA atmosphere | 25,772,566,195 |
| NOAA indexes | 640,769,266 |
| cache receipts | 24,848,803 |
| IMD annual files (20 x measured 2019 file) | 508,636,640 |
| normalized Zarr (July consolidated-size scaling) | 682,422,506 |
| manifests | 675,187,355 |
| QC tables | 3,362,635 |
| weight/audit support | 4,550,679 |
| projected retained production footprint | 125,947,338,480 |

Projected NOAA network transfer from July's measured HTTP bodies is
123,387,258,379 bytes: 96,974,392,028 precipitation, 25,725,094,972 atmosphere,
636,467,861 indexes, plus 51,303,519 for retry traffic at July's observed rate.
IMD adds an estimated 508,636,640 bytes because one annual file serves all dates,
not one file per initialization. The combined measured-based network budget is
therefore 123,895,895,019 bytes. Retained-source projections are slightly larger
than successful-body transfer because they use on-disk category measurements.

These are decimal bytes and linear extrapolations. They assume July-2019 mean
object sizes/compression, identical variables/leads/members, one similarly sized
IMD annual file per year, and no failed-attempt payload retention. Archive-era
size changes, filesystem allocation, Zarr metadata, retry traffic, audit samples,
backup and version turnover add uncertainty.

Minimum free working space is 256 GB (just over 2x the 125.95 GB retained
projection). Recommended working storage is a 500 GB SSD so staging, review
artifacts, backups, and one version transition do not force destructive cleanup.

## Phase 1E implementation evidence

The 2019 seasonal Zarr implements the frozen shapes and chunks exactly and has
tree SHA-256
`895cecb614a8d39b5e251b8608bb613f5695202c4fdc4b8752e71fd8d1fcc18d`.
It occupies 26,411,897 bytes. A final retention pass removed 238 redundant daily
NetCDFs after recording hashes and retained ten bounded audit artifacts: four
monthly storage benchmarks plus paired daily files for a complete-ensemble case,
the known anomaly, and the September-to-October boundary. The disposition is
machine-readable in
`data/manifests/phase1e/2019-JJAS/netcdf_retention_manifest.json`.
