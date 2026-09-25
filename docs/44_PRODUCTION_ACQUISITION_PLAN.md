# Production Acquisition Plan

Status: plan only. Acquisition is `NOT_STARTED`; training is prohibited.

## Frozen scope

Acquire 00Z GEFSv12 Reforecast initializations for June 1 through September 30
of 2000-2019: 122 dates per year, 2,440 initialization dates. Products are
Day 1 +3→+27 h, Day 2 +27→+51 h, and Day 3 +51→+75 h. Control atmospheric
snapshots are +24/+48/+72 h. A September 30 initialization retains all products,
so its observations extend through October 3; it is never truncated at the
initialization-season boundary. Each year's IMD annual file covers those dates.

Rainfall members are c00 and p01-p04. Control-only predictors are U850, V850,
Q700, Z500, MSLP, and PWAT. The exact archive families and decoded identities
are frozen in the plan manifest; notably Q700 is `spfh_pres_abv700mb`, Z500 is
decoded in `gpm`, and rainfall is archive family `apcp_sfc` / GRIB `tp`.

## Independently retryable unit

One initialization date is the acquisition unit. Its independently recorded
children are rainfall members, control atmospheric fields/leads, and observation
dates. Bytes first enter unique staging paths; validated hashes and range
receipts are promoted to immutable cache objects. A unit manifest is committed
atomically after QC. One child failure cannot corrupt or erase completed peers.

Execution must occur in small reviewed batches. The first allowed future batch
is one complete JJAS season, followed by monthly and seasonal review before any
additional year.

## Conservative concurrency and retry

- NOAA range requests: 3 concurrent requests.
- GRIB decode: 2 processes, bounded by memory.
- Local normalization/QC: 2 workers.
- IMD annual download: 1 at a time.

Each HTTP component gets at most five attempts with 2/4/8/16/32-second backoff
plus server `Retry-After` when present. Retry 408, 425, 429, 500, 502, 503 and
504. Authentication/authorization failures, confirmed 404, and scientific
schema/identity failures are non-retryable. Validate `Content-Range`, length,
SHA-256 and message identity. Never promote partial files. Exhaustion creates
`PERMANENT_FAILURE` and component-scoped quarantine metadata.

## Monthly/corpus gates and split design

The gate is defined in `docs/43_CORPUS_ADMISSION_POLICY.md`. Training views are
generated only from eligibility metadata, never directory presence. A primary
chronological candidate is train 2000-2013, validation 2014-2016, and untouched
final test 2017-2019. Before fitting, confirm regime and extreme-event coverage
using training/validation only; if inadequate, change the split under a new
documented split version without looking at test scores. Rolling-origin folds
ending before 2017 are the sensitivity analysis. Random row splits are forbidden.

## Decode bottleneck result

The NOAA index already selects only the 25 precipitation messages needed through
+75 h. ecCodes must expand each selected global 1440 x 721 message before the
regional crop; regional slicing after decode does not reduce this work. Caching
normalized daily regional arrays prevents repeat decode during later QC/training.
On the cached July 22 five-member subset, a warmed sequential decode took the
measured 20.77 seconds; two processes took 6.94 seconds (2.99x in this single
run) and produced identical decoded-value SHA-256 digests. The preceding cache
warm-up took 14.20 seconds, showing material runtime variability. Exact values
and member digests are in
`data/manifests/phase1d/cached_decode_benchmark.json`. This is workstation
evidence, not a universal promise.
Two decode workers are therefore the conservative starting limit. No scientific
value or grid changes.

## Phase 1E execution note

The 2019 JJAS prototype used three concurrent NOAA range requests, five retries,
exponential backoff, checksum/length/`Content-Range` validation, and immutable
cache resume. Cache-only replays transferred zero bytes and reproduced all 244
daily source/derived manifest hashes.

One performance discrepancy remains: the executed implementation decodes GRIB
and performs local QC serially rather than using the planned two decode processes
and two QC workers. This does not change values or provenance, but it must be
benchmarked and resolved before multi-year acquisition. Do not reinterpret the
plan's worker counts as executed evidence.

## Phase 1F reconstruction update

Future precipitation processing must use the approved v2 canonical
reconstruction in doc 51 and must identify the v2 corpus version. V1 is not to
be silently rebuilt with changed semantics. The 2019 prototype season satisfies
the required one-season review gate. No acquisition occurred in Phase 1F.
Frozen request/retry/worker settings above remain unchanged; the separate
diagnostic recovery used local process parallelism only and is not an
acquisition-concurrency benchmark or policy change.
