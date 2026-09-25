# Data Acquisition Plan

Status: Stage 2 July 2019 pilot completed PARTIAL. Bulk acquisition remains
unauthorized pending resolution of one rainfall accumulation exception and a
reviewed production acquisition plan.

## Directory layout

The existing prototype file remains untouched. Future large data uses ignored
directories and small checked-in manifests:

```text
data/
├── GOA_CLEAN.csv                    # quarantined Phase 0 prototype identity
├── manifests/                       # checked-in source/file/inventory records
├── raw/                             # immutable, not committed
│   ├── forecasts/gefsv12/
│   ├── observations/imd/
│   ├── observations/imerg/
│   └── static/district_boundaries/
├── interim/                         # decoded/subset grids, not committed
├── processed/                       # versioned scientific products, not committed
│   ├── forecast_grids/
│   ├── observation_grids/
│   ├── paired/
│   └── regime/
└── samples/                         # only tiny redistributable fixtures
```

Before acquisition, `.gitignore` must ignore `data/raw/`, `data/interim/`, and
`data/processed/`, while keeping `data/manifests/` visible. Do not commit a sample
until redistribution terms and purpose are documented.

## Stage 0 — access and legal confirmation

1. Record provider, official product page, license/terms, citation, access date,
   authentication method, and contact route.
2. Obtain one actual IMD NetCDF through its official mechanism. If manual access
   or permission is required, stop and request it; do not scrape around controls.
3. Select and pin a GRIB/NetCDF stack only when the pilot requires it. Candidate
   tools are ecCodes/cfgrib/xarray; record native-library versions.
4. Finalize Survey of India boundary access/terms and exact file version.

Exit: legal/access record exists for every source. Readiness remains blocked.

## Stage 1 — one-window paired pilot

Acquire the smallest source-backed test:

- one GEFS 00 UTC initialization;
- control member only;
- `apcp_sfc` messages needed for one +3..+27-hour window;
- one/few atmospheric fields at one declared lead;
- one matching IMD daily NetCDF;
- target and context spatial subsets created locally;
- no training.

Validate GRIB open, native variable/level/units, step ranges, coordinates,
geographic crop, IMD fill value and time metadata, exact 03–03 UTC alignment,
and conservative-regridding conservation. Generate raw and derived manifests.

Exit: a reproducible command regenerates one FSS-ready forecast/observation grid.

Phase 1B result (2026-09-19): **PASS** for the fixed 2019-07-15 pair. Official
source bytes, masks, manifests, conservative weights, conservation QC, and the
derived NetCDF are documented in `36_ONE_WINDOW_PILOT_REPORT.md`. This result is
explicitly training-ineligible and does not authorize Stage 3 or model work.

## Stage 2 — one-month size and reliability pilot

Acquire one JJAS month for all five daily precipitation members and minimum
control predictors.
Measure request success/retry rates, actual bytes by variable/message, processing
time, peak RAM, decoded/subset sizes, missing steps, and QC failures. Recalculate
the storage table in `31_AUTHORITATIVE_DATA_ARCHITECTURE.md`.

Exit: reviewed measured budget and complete inventory. No model training.

Phase 1C result (2026-09-19): 31 initializations, 464/465 rainfall cases,
558/558 predictor snapshots after retry, 93/93 IMD product pairings, and a
zero-network cache-only repeat. One `p01` Day-2 case fails because a −0.2-mm
nested difference exceeds the 0.1-mm packing tolerance. Stage 2 is therefore
PARTIAL and does not authorize Stage 3. See documents 38–41.

## Stage 3 — five-year small corpus

Acquire JJAS 2000–2004, three products, control precipitation/predictors. Add all
five precipitation members only after the control corpus passes. Produce paired
grids, masks, QC summaries, district-weight input tests, and event counts.

Exit: coverage and heavy-event sufficiency decision; still do not train unless
all Phase 0 scientific blockers and the relevant acceptance gates are resolved.

## Stage 4 — recommended historical corpus

After explicit review, expand to JJAS 2000–2019. Process year-by-year with
restartable inventories. Atmosphere stays control-only initially; add ensemble
statistics only if a defined experiment needs them. Never overwrite raw chunks.

## NOAA request method

1. Enumerate expected official S3 keys from initialization/member/variable.
2. Fetch and hash `.idx` sidecars.
3. Parse offsets and issue HTTP Range requests only for required messages.
4. Verify HTTP status/content range, GRIB magic, byte count, and checksum.
5. Decode metadata before values; reject unexpected init/member/variable/level.
6. Crop locally, since byte ranges reduce messages but not geography.
7. Use bounded concurrency, retry with backoff, and an append-only acquisition
   log. Never treat an absent object as zero rainfall.

## IMD request method

Use the official IMD download/access route. Preserve original NetCDF bytes and
terms/citation snapshot. Read time, coordinates, units, `_FillValue`,
`missing_value`, and product attributes directly. Do not normalize the file in
place; write derived grids under `interim/` with lineage.

## File-level manifest

Every acquired file or retained byte range records:

```text
dataset_id, provider, source_url, retrieval_date, filename, sha256, byte_size,
data_type, product, version, model_name, initialization_time_utc, lead_hours,
variable, level, units, spatial_resolution, temporal_resolution,
license_or_terms, request_or_subset, provenance_status
```

`SourceFileManifest` validates the core form. Forecast entries require model,
initialization, and lead metadata. Architecture/source pages are not file
manifests and never make a file training-eligible.

## Exact next acquisition task

Resolve and document the 2019-07-22 `p01` Day-2 accumulation inconsistency,
freeze a fail-closed corpus admission policy, then review a production historical
acquisition plan covering exact JJAS years, chunking, concurrency, storage
format/schema version, dataset-version freeze, resumability, QC gates, and total
disk/transfer budget. Do not acquire the multi-year corpus or train a model.
## Phase 1D production-plan update (2026-09-19)

The reviewed production successor is `docs/44_PRODUCTION_ACQUISITION_PLAN.md`
and its immutable machine plan is
`data/manifests/corpus/varshasetu-gefs12r-imd025-jjas-2000-2019-v1.plan.json`.
The next authorized scope is one complete JJAS season in reviewed monthly
batches—not a 20-year command. Acquisition status remains `NOT_STARTED`.

## Phase 2A authorization update (2026-09-22)

The explicit Phase 2A scope supersedes the stale Stage 3/next-task language for
this bounded prototype run only. Acquisition is authorized for every 00 UTC
initialization in 2017 and 2018 JJAS, using v2 canonical reconstruction, all
five rainfall members, the six c00 atmospheric variables, and official annual
IMD rainfall. It does not authorize 2000–2016, rainfall-model training, or any
change to the frozen source/grid/timing contracts. Work remains restartable by
month with immutable checksum receipts and case-scoped quarantine.

The bounded hardware benchmark selected six threads for official NOAA index and
range I/O. The acquisition runner processes initializations serially to avoid a
nested process/thread pool. Independent ecCodes replay/decode work may use the
separately benchmarked eight-process setting; local QC may use four processes.

## Phase 2A execution outcome (2026-09-23)

Both authorized seasons were assembled and admitted
`SEASON_ACCEPTED_WITH_QUARANTINED_SAMPLES`; see
[`53_PHASE2A_2017_2018_CORPUS_REPORT.md`](53_PHASE2A_2017_2018_CORPUS_REPORT.md)
for exact accepted, quarantined, and eligible counts and manifest hashes.
The 2017 and 2018 seasons have 1,489/1,830 and 1,476/1,830 valid
rainfall member-products, respectively. This closes only the explicit Phase
2A acquisition scope and does not change the full 2000–2019 plan status.
