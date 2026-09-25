# Data Provenance Specification

## Why this document is critical

For NWP post-processing, data lineage is part of model validity.

A model can have excellent test metrics and still be operationally invalid if:
- the “raw NWP” field is synthetic or derived from observations,
- an input uses future-valid-time observations,
- timestamps are misaligned,
- accumulation windows differ,
- reanalysis is treated as a forecast.

No scientific dataset may enter the production/training pipeline without a provenance record.

## Current audited prototype

### Checked-in file

`data/GOA_CLEAN.csv`

Observed during audit:
- 44,064 rows,
- 26 columns,
- 12 locations,
- 2020–2025,
- 6-hour temporal records,
- two districts,
- no missing values in checked file,
- no `regime_id`.

### Saved experiment source

The saved report references a different local file:
- `GOA_DATA (1).csv`,
- includes `regime_id`,
- different checksum,
- not included in the ZIP audit.

### Current status

- observational source: **unverified**;
- raw-NWP source: **unverified**;
- regime-label source: **unverified**;
- forecast initialization/lead metadata: **absent**.

### Phase 0 live identity (2026-09-19)

The checked-in file is now resolved portably and validated against
`data/manifests/goa_clean.prototype.json`:

- dataset ID: `goa-clean-prototype-7b01a5f3`;
- filename: `GOA_CLEAN.csv`;
- SHA-256: `7b01a5f35bd32a30c7998401c17d26d1e9b2180fca850b7b5bb56f06fe4cb241`;
- size: 8,107,202 bytes;
- rows: 44,064;
- source columns: 26;
- `regime_id`: absent;
- training eligibility: **false**.

The legacy report source remains absent:

- filename: `GOA_DATA (1).csv`;
- SHA-256: `30e4df58e8b84e13579651aae693dd1885a468f78bd1bc420d6ae0a61f03d1b6`;
- source columns: 27, including `regime_id` (the report counted a generated
  `datetime` column as column 28).

The repository does not claim that either the forecast-like or observation-like
fields are official. A manifest verifies file identity, not scientific lineage.

Do not label the prototype dataset “official NWP” until this is resolved.

## Required provenance record template

Create one YAML/JSON record per source dataset:

```yaml
dataset_id: <stable-id>
display_name: <name>
provider: <IMD/NCMRWF/NOAA/NASA/etc>
source_url: <official URL>
access_date: YYYY-MM-DD
license_or_terms: <text/link>
data_type: forecast | observation | reanalysis | static
model_name: <if forecast>
model_version: <if known>
initialization_frequency: <if forecast>
lead_times: [27, 51, 75]  # rainfall-window end leads for the selected 00 UTC/IMD contract
variables:
  - canonical_name: precipitation
    archive_group: apcp_sfc
    native_name: tp
    units: mm
    accumulation: 24h
    accumulation_windows: [[3, 27], [27, 51], [51, 75]]
spatial_resolution: <degrees/km>
temporal_resolution: <hours>
coverage:
  start: YYYY-MM-DD
  end: YYYY-MM-DD
  region: India
raw_files:
  - filename: ...
    sha256: ...
preprocessing_pipeline: scripts/data/...
known_limitations:
  - ...
```

## Required data classes

### A. Raw NWP forecast

Essential fields:
- source/model,
- initialization timestamp,
- valid timestamp,
- lead hour,
- accumulated precipitation,
- grid,
- units.

Recommended atmospheric predictors:
- U/V winds at selected levels,
- relative humidity/specific humidity,
- MSLP,
- geopotential,
- TCWV,
- vorticity or enough fields to derive it,
- ensemble mean/spread if available.

### B. Observation/reference precipitation

Must document:
- instrument/product type,
- gauge/satellite/merged/gridded,
- time convention,
- accumulation period,
- quality-control status,
- spatial grid/resolution.

### C. Regime-label reference

If labels are derived from reanalysis:
- explicitly say so,
- keep label-generation data separate from operational predictors,
- ensure forecast inference uses forecast-time predictors.

### D. Static geographic data

Examples:
- DEM,
- slope/aspect,
- coastline geometry,
- district polygons.

Store source/license/version.

## Recommended fallback source hierarchy

These are research/development options, not commitments until implemented:

### Observations
- IMD gridded rainfall where accessible and licensed appropriately.
- GPM IMERG as a useful secondary/alternative spatial reference.
- station/rain-gauge observations where legitimately obtained.

### Forecasts
- genuine archived GFS/GEFS forecasts as an open fallback.
- NCMRWF/NCUM/NEPS data if provided/accessible for SIH.

### Regime development
- NCMRWF weather-pattern research outputs for conceptual guidance.
- ERA5/IMDAA for retrospective atmospheric-state analysis, **not** as raw forecast replacement.

## Timing alignment checklist

For every forecast/observation pair verify:

- [ ] initialization time known,
- [ ] lead known,
- [ ] valid period known,
- [ ] forecast accumulation period matches target,
- [ ] timezone converted consistently,
- [ ] observation window matches forecast window,
- [ ] leap/calendar handling correct,
- [ ] spatial regridding documented,
- [ ] missing-data mask documented.

## Hashing

Every raw input artifact used to generate a published model/report should have a checksum.

Use SHA-256.

The report should include source hashes or a manifest hash.

## Data retention

Never overwrite raw downloaded data.

Recommended:

```text
data/
├── raw/
├── interim/
├── processed/
├── static/
└── manifests/
```

Raw data should be immutable.

## Phase 1A source decision (2026-09-19)

The selected primary architecture is NOAA GEFSv12 Reforecast paired with IMD
0.25° Daily Gridded Rainfall. The secondary/fallback reference is NASA GPM IMERG
Final V07. See `31_AUTHORITATIVE_DATA_ARCHITECTURE.md` for the evidence and
trade-offs and `35_DATA_ACQUISITION_PLAN.md` for the staged acquisition plan.

At Phase 1A close this was a source selection, not a provenance resolution. The
statement then recorded that no IMD file and GEFS daily window had been acquired
and paired. Phase 1B has since created one checksummed official pair; see the
dated update below. Consequently:

- the current prototype remains unverified and training-ineligible;
- the scientific readiness gate remains blocked;
- a source/product web page is not a file manifest;
- the common usable period remains conditional on file-level inventory and QC;
- NCMRWF remains the intended deployment source, pending actual historical grid
  access or a formal data agreement.

`data/manifests/authoritative_data_architecture.v1.json` records the Phase 1A
decision and a small official NOAA access probe. It explicitly has
`training_eligible=false` and `readiness_effect=none`. The original manifest and
Phase 1A architecture report show that the probe also decoded and geographically
subset one `0-3` GRIB message; the earlier “index only” wording here was stale.

## Phase 1B provenance update (2026-09-19)

One official pair now exists for 2019-07-15: GEFSv12 initialization
2019-07-14 00 UTC, member `c00`, leads +3 to +27, and official IMD annual file
`RF25_ind2019_rfp25.nc`. Source and derived manifests are under
`data/manifests/phase1b/2019-07-15/`; the human evidence is in
`36_ONE_WINDOW_PILOT_REPORT.md`.

This resolves file-level identity, native metadata, exact-window construction,
mask handling, and lineage only for one day. The pair manifest explicitly keeps
`training_eligible=false`; historical completeness, full predictor provenance,
regime labels, and training reproducibility remain blocked.

## File-level manifest requirement

Every acquired file or retained byte range must pass
`backend/app/data/contracts.py::SourceFileManifest`. In addition to the earlier
template, the required fields include byte size, product/version, explicit
request/subset description, provenance status, and forecast initialization/leads
where applicable. A 64-character SHA-256 is mandatory.

The future ingestion inventory must distinguish:

1. source documentation (evidence about a product),
2. an acquisition manifest (identity of bytes received),
3. a derived-artifact manifest (transformations and parent hashes), and
4. a paired-corpus manifest (accepted windows/grid/mask and exclusions).

Only the fourth, after all acceptance checks, can be considered for training.
