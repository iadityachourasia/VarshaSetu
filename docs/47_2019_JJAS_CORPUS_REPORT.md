# 2019 JJAS Prototype Corpus Report

Status: executed Phase 1E evidence. Scientific APIs and model training remain blocked.

## Decision

The 2019 JJAS subset of
`varshasetu-gefs12r-imd025-jjas-2000-2019-v1` is
`SEASON_ACCEPTED_WITH_QUARANTINED_SAMPLES`.

All 122 expected 00 UTC initializations from 2019-06-01 through 2019-09-30
were acquired. Day-2 and Day-3 valid periods are preserved through 2019-10-03.
This is a provenance-complete prototype season, not a training-ready rainfall
corpus: only eligibility-filtered views may be used in later tasks.

## Completeness

| Component | Expected | Valid | Quarantined/missing | Permanent source failures |
|---|---:|---:|---:|---:|
| rainfall member-products | 1,830 | 614 | 1,216 | 0 |
| control atmosphere snapshots | 2,196 | 2,196 | 0 | 0 |
| IMD forecast-product pairings | 366 | 366 | 0 | 0 |

Rainfall completeness is 33.55%. This unexpectedly low result follows the
frozen packing-aware reconstruction rule; it is not a transport-availability
problem and was not repaired by clipping or substitution.

### By product

| Product | Expected | Valid | Quarantined | Completeness |
|---|---:|---:|---:|---:|
| Day 1 (+3 to +27 h) | 610 | 253 | 357 | 41.48% |
| Day 2 (+27 to +51 h) | 610 | 185 | 425 | 30.33% |
| Day 3 (+51 to +75 h) | 610 | 176 | 434 | 28.85% |

### By member

| Member | Expected | Valid | Quarantined | Completeness |
|---|---:|---:|---:|---:|
| c00 | 366 | 52 | 314 | 14.21% |
| p01 | 366 | 149 | 217 | 40.71% |
| p02 | 366 | 139 | 227 | 37.98% |
| p03 | 366 | 132 | 234 | 36.07% |
| p04 | 366 | 142 | 224 | 38.80% |

### Monthly admission

| Month | Admission | Rainfall valid/expected | Atmosphere valid/expected |
|---|---|---:|---:|
| June | `MONTH_ACCEPTED_WITH_QUARANTINED_SAMPLES` | 134/450 | 540/540 |
| July | `MONTH_ACCEPTED_WITH_QUARANTINED_SAMPLES` | 137/465 | 558/558 |
| August | `MONTH_ACCEPTED_WITH_QUARANTINED_SAMPLES` | 151/465 | 558/558 |
| September | `MONTH_ACCEPTED_WITH_QUARANTINED_SAMPLES` | 192/450 | 540/540 |

## Packing anomaly finding

Phase 1C accepted July using a blanket 0.1 mm tolerance. Phase 1D subsequently
froze the stricter rule that a negative reconstructed increment may be clamped
only when it lies within both the pair-specific packing-error bound and the
0.1 mm operational cap. Replaying all four months under that exact rule rejects
1,216 member-products.

The relevant GRIB2 complex-packing template defines binary and decimal scale
factors, and NOAA's reference packing implementation uses nearest-integer
rounding. The pair-specific half-quantum bound is therefore the controlling
test; the blanket cap alone is insufficient. See the
[NCEP template 5.3 specification](https://www.nco.ncep.noaa.gov/pmb/docs/grib2/grib2_doc/grib2_temp5-3.shtml)
and [NOAA NCEPLIBS-g2c `compack.c`](https://github.com/NOAA-EMC/NCEPLIBS-g2c/blob/develop/src/compack.c).

The known 2019-07-22 p01 Day-2 anomaly remains quarantined. Strict replay also
quarantines c00 and p04 for that product, so the earlier documentation statement
that the control case remained eligible is superseded by this executed evidence.

## Observation and mask

The cached official IMD 0.25-degree 2019 annual file was reused with zero IMD
network bytes. The 03 UTC to 03 UTC convention and existing mask were preserved.
There are 124 unique valid dates, 1,301 valid cells and 1,100 masked cells per
date (45.8142% masked), or 161,324 valid and 136,400 masked date-cells.

## Seasonal Zarr

Authoritative path:
`data/processed/phase1e/2019-JJAS/varshasetu-gefs12r-imd025-2019-jjas-v1.zarr`

| Array | Shape | Chunk |
|---|---|---|
| `forecast_rain` | `(122,3,5,49,49)` | `(1,3,5,49,49)` |
| `observation_rain` | `(122,3,49,49)` | `(1,3,49,49)` |
| `valid_mask` | `(122,3,49,49)` | `(1,3,49,49)` |
| `atmosphere` | `(122,3,6,51,81)` | `(1,3,1,51,81)` |

The Zarr contains 1,242 files, occupies 26,411,897 bytes, and has tree SHA-256
`895cecb614a8d39b5e251b8608bb613f5695202c4fdc4b8752e71fd8d1fcc18d`.
All negative forecast values are the explicit `-999` quarantine fill; no
accepted forecast value is negative.

The final storage pass removed 238 redundant daily NetCDFs (57,396,556 bytes)
after recording path, size, and SHA-256. Ten bounded NetCDF audit artifacts are
retained: four monthly format benchmarks and paired rainfall/atmosphere files
for 2019-06-11, 2019-07-22, and 2019-09-30. The disposition ledger is
`data/manifests/phase1e/2019-JJAS/netcdf_retention_manifest.json`.

## Cache and reproducibility

Every month completed a cache-only replay with zero network bytes and no changed
daily source/derived manifest hashes: June 60/60 unchanged, July 62/62, August
62/62, and September 60/60. The acquisition used three concurrent NOAA range
requests, five retries, exponential backoff, length and `Content-Range`
validation, and the verified cached IMD file.

## Documentation/code discrepancies found

1. Phase 1C's blanket 0.1 mm acceptance rule conflicts with the later frozen
   pair-specific packing bound. The old 464/465 July statement is not valid
   under the frozen rule; strict July is 137/465.
2. The Phase 1D July example said c00 remained eligible on 2019-07-22 Day 2.
   Strict replay finds c00, p01, and p04 invalid for that product.
3. The downloader used eight NOAA workers, three retries, and 0.5-second initial
   backoff while the production plan required three, five, and two seconds.
   The implementation was corrected before the executed season acquisition.
4. Monthly manifest validation and paths were hard-coded to July. They were
   generalized to calendar-correct `YYYY-MM` processing.
5. The monthly Zarr schema/chunks did not match the frozen Phase 1D layout. They
   were corrected and the exact seasonal shapes/chunks are validated by tests.
6. The pipeline retained every daily NetCDF despite the storage plan. The final
   retention pass now keeps only the ten audit artifacts described above.
7. The production plan specifies two GRIB decode processes and two local QC
   workers. The executed script used the correct three-request network limit but
   performed decode/QC serially. Values are deterministic, but this remains a
   performance discrepancy to resolve before multi-year acquisition.
8. The first Phase 1E July build reused the complete Phase 1C source cache and
   was itself cache-only. The generic execution filename was overwritten by the
   second verification replay; final zero-network/hash-stability evidence is
   preserved, but the first Phase 1E execution record is not separate.
9. The workspace has no Git metadata, so Git diff/status evidence cannot be
   produced. File-level manifests and hashes are the available change evidence.
10. The supplied Phase 1E request text is truncated after the final heading
    `### Season Admis`; all operational requirements before that truncation were
    executed, but no unseen final-template text can be reconstructed exactly.
11. The new eligibility unit test initially used 2019-07-22 as a synthetic
    control-valid/p01-invalid example, mirroring the superseded documentation.
    It was changed to an actually control-valid June case so test wording no
    longer contradicts the executed corpus.

## Guardrails

No model was trained, no `regime_id` or heuristic regime label was created, FSS
was not computed, and no scientific API was unblocked. `training_eligible=false`
remains explicit. The next scientific task must review the unexpectedly broad
packing-related quarantine before any training split or result claim.

## Phase 1F superseding reconstruction result

This report remains the immutable v1 execution record. Phase 1F established
that v1 unnecessarily made four synthetic differences admission-critical per
product. The separately versioned v2 canonical replay accepts 1,468/1,830
rainfall products, with 255/366 control and 173/366 full-ensemble rows. V1
counts and hashes above are not rewritten. See docs 51 and 52 for the approved
method, full coverage, residual quarantines, and v2 hashes.
