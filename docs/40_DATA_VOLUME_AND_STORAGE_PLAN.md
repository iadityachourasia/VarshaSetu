# Phase 1C Data Volume and Storage Plan

Status: measured July 2019 pilot; projections are estimates, not acquired data.

## Measured retained storage

| Artifact category | Measured bytes |
|---|---:|
| NOAA precipitation messages | 1,240,444,601 |
| NOAA atmospheric messages | 327,438,341 |
| NOAA indexes | 8,140,921 |
| Cache receipts | 315,702 |
| Existing IMD 2019 source | 25,431,832 |
| Daily rainfall-pair NetCDFs | 5,644,976 |
| Daily atmospheric-context NetCDFs | 9,307,068 |
| Regridding weights | 57,816 |
| Daily manifests | 8,578,200 |
| QC CSV tables | 42,722 |
| Consolidated NetCDF evaluation artifact | 14,805,712 |
| Consolidated Zarr evaluation artifact | 8,670,122 |

NOAA source bytes excluding receipts total 1,576,023,863. Derived/evaluation
bytes total 47,106,616. The complete measured July working set including cache
receipts and the already-existing annual IMD file is 1,648,878,013 bytes. The
IMD incremental network transfer for Phase 1C was zero.

Initial successful HTTP response bodies totalled 1,566,973,197 bytes. The
independent July 31 retry transferred another 651,807 bytes. Thus measured task
network transfer was 1,567,625,004 bytes. The cache-only validation transferred
zero bytes.

Per-initialization NOAA-plus-derived retained storage, excluding the annual IMD
file, is about 52.36 MB. This is an observed July average, not a fixed archive
constant.

## NetCDF versus Zarr measurement

| Criterion | NetCDF | Zarr 3.2.1 |
|---|---:|---:|
| Consolidated size | 14,805,712 B | 8,670,122 B |
| Mean random rainfall-slice read | 0.02780 s | 0.01270 s |
| Full rainfall-array read | 0.02939 s | 0.78109 s |
| Append practicality | fixed classic file requires rewrite | initialization chunks can be extended |
| Metadata | CF-style variables/attributes | explicit group/array schema required |
| Portability | single, broadly portable file | many files/object-store friendly |

These timings are one Windows workstation run. A warm repeat measured 0.01391 s
versus 0.00382 s for the random slice and 0.01202 s versus 0.95395 s for the full
read, showing material cache/runtime variability; neither run should be
generalized as a universal format benchmark. Retain daily NetCDF artifacts for inspectability
and exchange. For a reviewed multi-year plan, prefer a versioned consolidated
Zarr array for initialization-wise random access and appendability, while keeping
source GRIB ranges immutable. Freeze the Zarr version/schema and benchmark on
the actual target disk before bulk acquisition.

## Projections

The pipeline's strict linear projection excludes the annual IMD file and cache
receipt overhead: 6,387,803,821 bytes for one 122-day JJAS season and
127,756,076,412 bytes for 20 JJAS seasons.

An inclusive planning projection scales NOAA, receipts, and derived bytes by
122/31 and adds one observed-size IMD annual file per year:

- one JJAS season: 6,414,478,093 bytes;
- 2000–2019 JJAS: 128,289,561,860 bytes.

Assumptions: 122 initialization days per JJAS, July 2019 mean object sizes and
compression, the same five precipitation members, control-only atmosphere, the
same variables/leads/domains, one similarly sized IMD file per year, and no
provider/schema changes. Filesystem allocation overhead, backup copies, failed
attempt payloads, temporary working space, future variables, and redundant
formats can increase the requirement. A production plan should reserve at least
2× the projected retained footprint for safe processing and version turnover.

## Recommendation boundary

Storage appears feasible on the measured workstation, but this report does not
authorize 2000–2019 acquisition. The unresolved rainfall accumulation exception,
dataset-version freeze, chunk/concurrency design, and QC admission policy require
review first.
## Phase 1D append-only production update

The prerequisite review named above is complete. The isolated anomaly is
fail-closed and the version/chunk/concurrency policy is frozen; see
`docs/42_GEFS_ACCUMULATION_ANOMALY_REPORT.md` through
`docs/46_PRODUCTION_STORAGE_AND_CHUNKING.md`. The measured-based production
layout avoids retaining duplicate daily NetCDF and consolidated Zarr copies and
projects 125,947,338,480 bytes retained. Reserve at least 256 GB free; 500 GB SSD
is recommended. This authorizes only a controlled one-season acquisition and
does not unblock scientific training or endpoints.
