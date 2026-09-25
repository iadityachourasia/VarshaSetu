# Authoritative Data Architecture

Status: **Phase 1A design complete; scientific release gate BLOCKED**  
Decision date: 2026-09-19  
Machine-readable decision: `data/manifests/authoritative_data_architecture.v1.json`

Phase 1B update (2026-09-19): one official 2019-07-15 GEFSv12/IMD rainfall
pair passed timing, accumulation, alignment, mask, conservation, and lineage QC.
See `36_ONE_WINDOW_PILOT_REPORT.md`. The pair remains
`training_eligible=false`; the architecture's scientific release gate is still
blocked.

Phase 1C update (2026-09-19): all 31 July 2019 initializations, five rainfall
members, three rainfall products, and the six-variable control atmospheric
contract were attempted. Atmospheric availability was 558/558 after an
independent retry; rainfall completeness was 464/465. One `p01` Day-2 nested
accumulation failed the packing-residue gate, so the month is PARTIAL and bulk
acquisition is not approved. See `38_ONE_MONTH_ACQUISITION_PILOT.md`.

This document selects a data architecture. It does not assert that the historical
files have been acquired, paired, quality-controlled, or made training-eligible.
No model or scientific endpoint may use this design record as a substitute for
file-level provenance.

## Decision

The primary development pair is:

```text
NOAA GEFSv12 Reforecast (actual retrospective model forecasts)
                         +
IMD 0.25° Daily Gridded Rainfall (gauge-based reference)
```

The fallback/secondary verification pair is GEFSv12 Reforecast + NASA GPM IMERG
Final V07. IMERG must remain a separately identified truth source; scores from it
must not be merged with or presented as IMD scores.

NCMRWF NCUM/NEPS remains the intended deployment source. The public evidence
reviewed exposes recent forecast products and model descriptions, but not a
practical, documented historical gridded archive for a student team. A formal
data request is therefore required before NCUM/NEPS can replace GEFS.

## Why GEFSv12 reforecast is the primary raw NWP dataset

The NOAA archive contains forecasts rerun with a forecast model from historical
initial conditions; its fields at positive lead are model predictions, not
analysis or reanalysis fields. Reanalysis was used to initialize the experiment,
but that does not turn its positive-lead output into reanalysis. NOAA documents:

- 00 UTC initialization daily from 2000 through 2019;
- five daily members (`c00`, `p01`–`p04`), with an expanded weekly set;
- daily reforecasts extend to day 16; the weekly 11-member configuration extends
  to day 35, beyond the three MVP products;
- GRIB2 files organized by initialization, member, variable, and lead range;
- most variables at 0.25° and 3-hourly through day 10; variables above 700 hPa
  are 0.5°;
- precipitation (`apcp_sfc`), precipitable water (`pwat_eatm`), MSLP
  (`pres_msl`), pressure-level wind, specific humidity, and geopotential height.
  Direct Phase 1C inspection established that exact Q700 is in
  `spfh_pres_abv700mb`; `spfh_pres` itself contains only 1000–800-hPa fields.

The archive is public in NOAA's AWS Open Data bucket. Per-message byte offsets
are available in `.idx` sidecars, so a downloader can retrieve selected GRIB
messages with HTTP byte ranges. Those messages are still global fields; the
archive does not provide server-side geographic cropping. Spatial cropping must
occur locally after decoding.

## Other forecast candidates

### Historical operational GFS/GEFS

NOAA/NCEI documents operational GFS forecast archives, including 0.5° Grid 4
forecast fields from 2006 onward through archive/request systems and newer 0.25°
cloud data from 2021 onward. NOAA's operational GFS and GEFS AWS datasets and
NOMADS are useful for recent out-of-sample demonstrations. They are not the
primary training source because model configurations change over time, cloud
retention and long-term access differ, and assembling a homogeneous 20-year
hindcast is less practical. They are genuine operational forecasts, not analyses,
but require model-version stratification.

### NCMRWF NCUM/NEPS

NCMRWF documents an approximately 12-km global NCUM system with 00/12 UTC
forecasts to about ten days and NEPS with a control plus 22 perturbed members to
about ten days. The reviewed public pages mainly expose recent charts/products.
No documented self-service historical gridded archive was found. Therefore a
formal NCMRWF/MoES request or challenge-provided data package is the only honest
next path. If supplied, NCUM/NEPS should use the same source adapter contract and
be evaluated as the target deployment source; it must not be merged silently
with GEFS.

## Reference rainfall candidates

### IMD 0.25° Daily Gridded Rainfall

IMD's official method report describes a gauge-based 0.25° × 0.25° daily product
over the Indian mainland grid (6.5–38.5°N, 66.5–100.0°E), built with quality
control and interpolation from a large station network. The original documented
long-period product covers 1901–2010; the official NetCDF archive provides yearly
files extending through the entire GEFS 2000–2019 period. Values are daily
rainfall in millimetres, and the operational daily convention is the 24 hours
ending 08:30 IST. The official download mechanism and citation/method report are
identified in the source register.

Phase 1B read the official 2019 NetCDF directly: `_FillValue` and
`missing_value` are both `-999.0`; the grid/time/global attributes, citation, and
official-page disclaimer are recorded in its source manifest. The file contains
no explicit product-version attribute or accumulation time bounds. The official
page text says coverage through 2024 while its selector includes 2025. These
remaining ambiguities are recorded rather than guessed.

### NASA GPM IMERG Final V07

NASA documents IMERG V07 as global 0.1° half-hourly precipitation spanning the
TRMM/GPM era from June 2000 onward. Early and Late runs prioritize low latency;
Final is the research product and incorporates monthly GPCC gauge-analysis
adjustment. Final V07 is therefore the appropriate retrospective secondary
reference. Access is through NASA GES DISC/PPS services and normally requires
Earthdata/PPS registration; geographic subsetting services are available. Its
half-hour fields can be aggregated to the exact 03:00–03:00 UTC contract.

IMERG is not silently interchangeable with IMD: satellite/merged retrieval and
gauge adjustment have different error structure from the IMD gauge-grid product.

### Tiny official access probe

On 2026-09-19, the official `apcp_sfc` index and only its first GRIB message for
the 2000-01-01 00 UTC control forecast were read into memory, not committed or
used for science:

- 5,960 bytes;
- SHA-256 `acdbf4a70f8766de3c5394b529959c8838e47f5cc61e49721f634bc71b935e50`;
- 80 message entries;
- initial step ranges `0-3`, `0-6`, `6-9`, and `6-12 hour acc fcst`.
- first message byte range 0–422,514 (422,515 bytes), SHA-256
  `8bd2ef87b6225298e2ae2184ae98ee948591d3ab9357b960eddac04b896a77eb`;
- ecCodes decoded GRIB2 `tp` / Total Precipitation, surface,
  `kg m**-2`, initialization 2000-01-01 00 UTC, step range `0-3`;
- regular 0.25° global grid, 1440 × 721 (1,038,240 points);
- local 10–22°N, 68–80°E subset contained 2,401 finite points.

This proves public byte-range access, GRIB decoding, variable/timing metadata,
local geographic subsetting, checksum generation, and the mixed 3/6-hour index
semantics for one message. It does **not** prove complete 24-hour reconstruction,
multi-variable/member ingestion, conservative regridding, or IMD pairing.

## Candidate comparison

Scores are ordinal (1 poor, 5 strong) and support the decision; they are not
scientific measurements.

| Candidate strategy | Validity | Authority | Actual forecast | Rain truth | Grid/period | Heavy-event history | Storage/download | Team feasibility | NCMRWF migration | Total / 45 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| GEFSv12 reforecast + IMD 0.25° | 5 | 5 | 5 | 5 | 5 | 5 | 3 | 4 | 4 | 41 |
| GEFSv12 reforecast + IMERG Final V07 | 5 | 5 | 5 | 4 | 4 | 5 | 3 | 3 | 4 | 38 |
| historical operational GFS + IMD | 4 | 5 | 5 | 5 | 3 | 4 | 2 | 2 | 4 | 34 |
| public NCMRWF products + IMD | 5 | 5 | 5 | 5 | 1 | 1 | 1 | 1 | 5 | 29 |

GEFS/IMD wins because it combines genuine forecast status, a homogeneous long
hindcast, a national gauge-based reference, and compatible 0.25° target
resolution. Operational GFS/GEFS is valuable for recent external cases but has
model-version changes and more difficult long-term archive access. Public
NCMRWF pages are not evidence of a downloadable historical grid archive.

## Exact period and sampling season

- Archive overlap candidate: GEFS initializations from
  `2000-01-01T00:00:00Z` through `2019-12-31T00:00:00Z`.
- A pair is eligible only when the corresponding IMD ending date exists and the
  source files, time convention, fill value, and grid pass acquisition QC.
- The first bulk acquisition should be June–September (JJAS) for each year,
  approximately 2,440 daily initializations, rather than all seasons.
- Initialization-date bounds and observation-valid-date bounds are distinct:
  day-1/2/3 windows can end in a later day or year. The final usable paired range
  must come from inventory results, not be inferred from archive marketing text.

## Domains

### Target correction and verification domain

`10.0°N–22.0°N, 68.0°E–80.0°E`, clipped to valid IMD cells for training and
verification. It includes Goa, coastal and inland western India, the Western
Ghats, and an Arabian Sea buffer needed to retain approaching rain systems.
Goa alone is rejected: it is too narrow for stable FSS neighbourhoods, spatial
error structures, and meaningful synoptic context.

### Regime-context domain

`5.0°N–30.0°N, 55.0°E–95.0°E` on a 0.5° context grid. It covers the Arabian
Sea, Indian landmass, Bay of Bengal, and broad monsoon circulation. This larger
domain is justified for regime inference, while the smaller target domain keeps
rainfall correction and storage manageable.

These are Version 1 bounds. The acquisition adapter must verify coordinate order
and cell centers, and the eventual domain may change only through a documented
decision with new storage estimates.

## Target grid and spatial alignment

- Training/verification grid: native IMD 0.25° rectilinear grid, EPSG:4326,
  restricted to valid target-domain cells.
- Rainfall: first-order conservative regridding using explicit source and target
  cell bounds and masks. The pipeline must test domain-integrated rainfall before
  and after regridding and store the weight-file hash.
- Smooth atmospheric fields: bilinear interpolation to the 0.5° context grid.
- Land/categorical masks: nearest-neighbour only; no bilinear mask interpolation.
- Ocean forecast cells may provide context, but observation-dependent training
  and verification use the documented IMD valid-cell mask. Missing IMD cells are
  not zeros.
- GEFS 500-hPa height is natively 0.5° in this archive and should remain on the
  context grid rather than be spuriously sharpened.

## Forecast leads and rainfall product names

The MVP has three 24-hour products from the daily 00 UTC initialization:

| Product | Forecast accumulation leads | UTC window relative to init | Matching IMD day |
|---|---:|---|---|
| `day1_24h` | +3 to +27 h | 03 UTC day 0 to 03 UTC day 1 | ending date day 1 |
| `day2_24h` | +27 to +51 h | 03 UTC day 1 to 03 UTC day 2 | ending date day 2 |
| `day3_24h` | +51 to +75 h | 03 UTC day 2 to 03 UTC day 3 | ending date day 3 |

They are not named “+24/+48/+72-hour accumulations,” because their end leads are
+27/+51/+75. Atmospheric predictor snapshots may be sampled at +24/+48/+72 or
summarized over each rainfall window, but their timestamps and transformations
must be stored explicitly.

## Rainfall accumulation contract

IMD daily rainfall is the 24 hours ending at 08:30 IST, equivalent to 03:00 UTC.
The canonical half-open interval for valid date `D` is:

```text
[D-1 03:00:00 UTC, D 03:00:00 UTC)
```

GEFSv12 reforecast precipitation during days 1–10 alternates between the last
3-hour accumulation and the last 6-hour accumulation at the documented valid
times. The adapter must inspect every GRIB `stepRange`, reconstruct exact 3-hour
increments (for example `0-6` minus `0-3`), and sum exactly eight increments per
daily window. It must not assume one cumulative convention from the filename.

Rules:

1. Convert `kg m-2` liquid-water equivalent to `mm` numerically 1:1 and record
   both source and canonical units.
2. Reject a window with a missing/duplicate step, inconsistent step range,
   material negative differenced amount, or mismatched end timestamp.
3. A tiny negative caused only by numeric tolerance may be clamped to zero; the
   tolerance and count must be reported.
4. Represent time in timezone-aware UTC. IST is derived for display only.
5. Use real Gregorian timestamps; February 29 is included when its eight steps
   and matching observation exist.
6. Never fill missing rainfall steps with zero.
7. Apply IMD heavy (64.5–115.5 mm/24 h), very heavy (115.6–204.4 mm/24 h), and
   extremely heavy (at least 204.5 mm/24 h) categories only after this contract
   passes. Boundary operators in code must follow the cited IMD definition.

## Minimum predictor variables

| Archive variable | Level | Meteorological purpose | MVP? | Size cost | Archive evidence |
|---|---|---|---|---|---|
| `apcp_sfc` object / GRIB `tp` | surface | raw rainfall, ensemble mean/spread, correction baseline | Required; 5 daily members | High | Yes; July pilot |
| `ugrd_pres` | 850 hPa | low-level monsoon flow and upslope component | Required; control first | Medium | Yes |
| `vgrd_pres` | 850 hPa | low-level monsoon flow and shear | Required; control first | Medium | Yes |
| `spfh_pres_abv700mb` | 700 hPa | lower/mid-level moisture | Required; control first | Medium | Yes; 93 decoded |
| `hgt_pres_abv700mb` | 500 hPa | mid-tropospheric trough/ridge context | Required; control first | Medium, native 0.5° | Yes |
| `pres_msl` | MSL | lows, depressions, pressure gradients | Required; control first | Medium | Yes |
| `pwat_eatm` | column | column moisture availability | Required; control first | Medium | Yes |
| derived vorticity | 850 hPa | cyclonic circulation | Derived from U/V | Low processed-only | Yes via U/V |
| temperature | selected level | thermal structure | Deferred | Medium | Yes, not needed initially |
| surface pressure | surface | terrain/pressure context | Deferred | Low/medium | Yes |

Atmospheric ensemble statistics are a later acquisition stage. The initial
architecture uses all five daily members only for precipitation and the control
member for circulation predictors. This captures rainfall spread without a 5×
multiplier on every field.

## FSS-ready representation

Processed arrays will use named dimensions and coordinates equivalent to:

```text
forecast_rain_mm[init_time, product, member, y, x]
forecast_ensemble_mean_mm[init_time, product, y, x]
forecast_ensemble_spread_mm[init_time, product, y, x]
observation_rain_mm[init_time, product, y, x]
valid_mask[init_time, product, y, x]
```

Coordinates include `latitude[y]`, `longitude[x]`, `valid_time`, window start/end,
lead start/end, grid ID, regridding-weight hash, and source-manifest IDs. Chunking
should favor one/few initialization times with full 2-D spatial slices; flattened
station rows are not an acceptable FSS source.

Future FSS will threshold raw/corrected/observed 24-hour fields, compute
neighbourhood fractions at declared physical scales, and report by threshold,
lead/product, scale, and event count. FSS itself is not implemented in Phase 1A.

## District aggregation input contract

Use Survey of India Administrative Boundary Data Base district polygons where
the download/terms can be documented; the Government of India data.gov.in
administrative-boundary catalog is the fallback. Archive the exact boundary
version, retrieval URL/date, CRS, district codes/names, license/terms, and file
hashes. Validate and, if necessary, repair topology with an auditable report.

Precompute area-aware grid/polygon intersection weights keyed by target-grid and
boundary-version hashes. For every valid date, product, and district produce:

- area-weighted mean rainfall;
- maximum valid-cell rainfall;
- area-weighted p90 and p95;
- area fraction at or above heavy and very-heavy 24-hour thresholds;
- area-weighted summaries of calibrated probabilities, once those probabilities
  actually exist;
- valid-area fraction and contributing-cell count.

District computation is deferred. No random or hand-drawn polygon may enter it.

## Storage and compute estimate

These original ranges are planning estimates, not measured acquisition totals. NOAA index-derived
message sizes show that byte-range requests still transfer global compressed
messages before local crop; that dominates raw volume. Estimates include a
20–30% margin for indexes, manifests, chunk metadata, masks, and staging.

| Option | Scope | Raw transfer/retained staging | Processed | Recommended disk | RAM | Training footprint |
|---|---|---:|---:|---:|---:|---:|
| Small | JJAS, 2000–2004, target domain, 3 products, control precipitation + minimum control predictors | 15–30 GB | 1–3 GB | 50 GB | 8 GB | 2–6 GB |
| Recommended MVP | JJAS, 2000–2019; five precipitation members; control atmospheric context; target + context domains | 130–250 GB | 8–20 GB | 300–500 GB | 16 GB | 8–24 GB |
| Large | all seasons, broad India/monsoon domain, five-member atmospheric fields and more variables | 0.8–2.0 TB | 50–150 GB | at least 2 TB | 32–64 GB | 40–120 GB |

Phase 1C subsequently measured an inclusive linear 20-JJAS projection of
128,289,561,860 bytes for the selected five-member rainfall/control-atmosphere
scope, within the original 130–250 GB raw/staging range after decimal/binary and
category differences. See `40_DATA_VOLUME_AND_STORAGE_PLAN.md`; the projection
is not acquired data.

The recommended student workflow uses an external 500-GB SSD, streams selected
GRIB messages, verifies and manifests immutable raw chunks, subsets promptly,
and processes by year. It starts with all five daily precipitation members and
control-only atmospheric predictors; atmospheric ensemble statistics are added
only if evidence shows they justify their cost. The measured one-month budget is
available, but the unresolved accumulation exception still blocks JJAS approval.

## Reanalysis boundary

ERA5/IMDAA may support regime-method research, climatology, and retrospective
diagnostics in a separately identified dataset. Reanalysis rainfall is not the
raw forecast and may not become the correction input. Any reanalysis-derived
label must be reproducible and its operational forecast-time analogue must be
defined before deployment.

## Remaining decisions that require acquisition evidence

Phase 1C resolved repeated IMD/GEFS access and pairing, predictor identity and
context subsetting, and measured one-month transfer/storage. Still needed:

- a reviewed resolution/admission policy for the July 22 accumulation failure;
- a frozen production acquisition/chunk/schema/concurrency plan;
- district-boundary file/version and legal-use record;
- final common paired inventory after file-level QC.

Until these pass, this architecture remains a source-backed design—not a usable
training dataset.

## Documentation/code discrepancies identified in Phase 1A

1. The earlier generic provenance template used rainfall lead labels
   `24/48/72`; exact IMD alignment from a 00 UTC cycle requires end leads
   `27/51/75` and start/end leads, so the template was corrected.
2. The target schema named 700-hPa relative humidity, while GEFS exposes
   pressure-level specific humidity. The Phase 1A contract selected `q700`, and
   Phase 1C located it in `spfh_pres_abv700mb`; conversion to RH would require
   temperature and pressure and is not assumed.
3. Earlier documentation proposed sources as a fallback hierarchy but did not
   select a primary pair, exact grid, exact daily time window, or file-level
   acquisition sequence. Documents 31–35 now make those design decisions while
   retaining the blocked gate.
4. The prior target forecast example could be read as a single tabular/station
   schema. FSS requires preserved 2-D fields, so the authoritative representation
   is now explicitly `(time, product/lead, y, x)` with masks and grid lineage.
5. The prior risk entry “training cannot reproduce” was marked “Verified,” which
   could be mistaken for resolved. It meant the risk was confirmed; the register
   now says scientific training remains blocked.
6. Phase 1A initially had no GRIB decoder. Phase 1B validated one precipitation
   window; Phase 1C validated 464 rainfall windows and 558 atmospheric snapshots.
   One rainfall window remains rejected and the historical corpus is absent.
7. At Phase 1A close the repository contained no IMD/IMERG scientific source file
   or authoritative district-boundary file. Phase 1B acquired and manifested one
   official IMD annual file in ignored local raw storage. The authoritative
   district boundary, broader access record, and corpus inventory remain absent.
8. The workspace is still not a Git checkout, so future acquisition/processing
   reports cannot yet record a real code commit. This pre-existing discrepancy
   remains unresolved.
9. NOAA's archive object family is named `apcp_sfc`, while ecCodes decodes the
   message short name as `tp`. The manifest now records archive group, decoded
   short name, and canonical variable separately.
10. The Phase 1A forecast table placed Q700 in `spfh_pres`; official live indexes
    show that exact level in `spfh_pres_abv700mb`. Phase 1C corrected the contract.
11. The Phase 1A Z500 unit table said metres; ecCodes reports geopotential metres
    (`gpm`). Phase 1C preserves the decoded unit explicitly.
## Phase 1D corpus-freeze update (2026-09-19)

The July 22 p01 Day-2 exception is now classified `SOURCE_INCONSISTENCY` and
component-scoped quarantine is frozen in
`docs/43_CORPUS_ADMISSION_POLICY.md`. Dataset version
`varshasetu-gefs12r-imd025-jjas-2000-2019-v1` freezes the GEFS/IMD architecture
without claiming acquisition or training eligibility. Controlled acquisition may
begin only as one reviewed JJAS season; scientific endpoints remain blocked.
