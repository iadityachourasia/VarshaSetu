# Phase 1B One-Window Pilot Report

Status: **PASS for one-window data engineering/QC; scientific release gate remains BLOCKED**  
Executed: 2026-09-19

## Pilot date and scope

The deterministic first-choice date, 2019-07-15, was used. The forecast is the
NOAA GEFSv12 Reforecast 00 UTC initialization on 2019-07-14, control member
`c00`. The target is the IMD 0.25° Daily Gridded Rainfall record dated
2019-07-15. No date was selected for visual impact, and no model, regime label,
FSS score, district product, endpoint, or legacy artifact was created or changed.

## Source files

### NOAA GEFSv12 Reforecast

- Official object: `GEFSv12/reforecast/2019/2019071400/c00/Days:1-10/apcp_sfc_2019071400_c00.grib2`
- Archive identity: `apcp_sfc`; decoded GRIB short name: `tp`; parameter:
  `Total Precipitation`; units: `kg m**-2`, numerically normalized 1:1 to mm.
- Selected bytes: 0–3,566,336, 3,566,337 bytes.
- Selected-byte SHA-256:
  `545d72b976a2a36dc0e9870ad70eac0f24414ab9341780f01b786190057232d9`.
- Index: 5,960 bytes; SHA-256
  `11a5cf1d39a44791320318f274bdcbc59b77d1a5d5a7c14d46f7f170e314eed7`.
- Source manifest:
  `data/manifests/phase1b/2019-07-15/noaa_gefsv12_2019071400_c00_apcp.json`.

### IMD 0.25° Daily Gridded Rainfall

- Official page: `https://imdpune.gov.in/cmpg/Griddata/Rainfall_25_NetCDF.html`.
- Authorized public route: official form POST `RF25=2019` to `RF25.php`.
- File: `RF25_ind2019_rfp25.nc`, 25,431,832 bytes.
- SHA-256:
  `c551c563b3514d492a2de94c706c1c254d5826656738b4a8e7dbd83841344a5b`.
- Classic NetCDF, CF-1.0; 365 records; `RAINFALL[TIME,LATITUDE,LONGITUDE]`;
  units mm; `_FillValue=-999.0`; `missing_value=-999.0`.
- Global grid: 129 × 135; latitude 6.5–38.5°N ascending; longitude
  66.5–100.0°E ascending; 0.25°.
- Time: `days since 1900-12-31 00:00:00`; no calendar attribute, therefore CF
  default standard calendar; pilot value 43295 at record index 195, labeling
  `2019-07-15T00:00:00`; no time-bound variable.
- Global attributes: `Conventions=CF-1.0`; `history=FERRET V6.82 20-Feb-26`.
- Citation: Pai D.S. et al. (2014), MAUSAM 65(1), 1–18. The official page's
  disclaimer says correctness cannot be guaranteed in all circumstances and
  disclaims liability for errors, omissions, loss, or damage.
- Source manifest: `data/manifests/phase1b/2019-07-15/imd_rf25_2019.json`.

## Exact NOAA message structure and accumulation

Every selected message decoded as `stepType=accum`, member `c00`, on the same
regular latitude/longitude grid. The exact, non-overlapping 24-hour union is:

| Segment | Lead start | Lead end | Duration | Reconstruction source |
|---:|---:|---:|---:|---|
| 1 | +3 | +6 | 3 h | `(0–6) - (0–3)` |
| 2 | +6 | +9 | 3 h | direct `6–9` |
| 3 | +9 | +12 | 3 h | `(6–12) - (6–9)` |
| 4 | +12 | +15 | 3 h | direct `12–15` |
| 5 | +15 | +18 | 3 h | `(12–18) - (12–15)` |
| 6 | +18 | +21 | 3 h | direct `18–21` |
| 7 | +21 | +24 | 3 h | `(18–24) - (18–21)` |
| 8 | +24 | +27 | 3 h | direct `24–27` |

The nine source messages are `0–3`, `0–6`, `6–9`, `6–12`, `12–15`, `12–18`,
`18–21`, `18–24`, and `24–27`. Their message hashes and all required decoded
metadata are in the NOAA manifest and machine-readable QC report.

Mixed GRIB decimal packing scales of 0.01 and 0.1 mm caused 196 negative
subtraction residues, with minimum −0.09 mm. The reconstruction tolerance is the
largest decoded packing quantum plus `1e-12` (0.100000000001 mm); only values
inside it are clamped to zero, and more-negative values fail. Source messages
themselves contain no negative values.

## Timing validation

The exact forecast interval is
`[2019-07-14T03:00:00Z, 2019-07-15T03:00:00Z)`. This equals the externally
verified IMD 08:30 IST previous-day to 08:30 IST current-day convention for the
2019-07-15 observation. Interval equality passed. The NetCDF itself labels the
day at midnight and does not encode time bounds; this distinction is retained in
the manifest and is not represented as file-internal proof of the accumulation
window.

## Grid characteristics and alignment

GEFS is globally 1440 × 721 at 0.25°, with 0–359.75° longitudes and native
north-to-south latitude storage. The adapter reverses latitude to ascending.
Both cropped GEFS and IMD target grids are 49 × 49 with centres spanning
10–22°N and 68–80°E. Their centre coordinates are exactly equal. IMD contributes
1,301 valid cells and 1,100 masked cells; the mask is retained explicitly.

Rainfall was mapped with repository-local first-order conservative spherical
cell-overlap weights. Midpoint-derived cell bounds were validated and the weight
rows sum to one within `1e-10`. Because the two 0.25° grids are co-located here,
the mapping reduces to identity. See `37_REGRIDDING_AND_ALIGNMENT_SPEC.md`.

## QC results

| Quantity | Result |
|---|---:|
| Source messages combined min / max / mean | 0 / 59.25 / 1.395894 mm |
| Accumulated GEFS min / max / mean | 0 / 63.95 / 7.832436 mm |
| Regridded GEFS min / max / mean | 0 / 63.95 / 7.832436 mm |
| IMD valid-cell min / max / mean | 0 / 125.949722 / 5.746570 mm |
| Material negative values after reconstruction | 0 |
| Packing-tolerance residues clamped | 196 |
| IMD missing/masked cells | 1,100 |
| Comparable valid area | 960,237,217,681.0657 m² |
| Source area-weighted integral | 6,818,087,525,825.749 mm m² |
| Target area-weighted integral | 6,818,087,525,825.749 mm m² |
| Conservation relative difference | 0.0 |
| Conservation tolerance | `1e-10` |

Timing, precipitation, spatial, conservation, and provenance QC all passed. The
machine-readable record is
`data/manifests/phase1b/2019-07-15/qc_report_2019-07-15.json`.

## Derived artifacts

- FSS-ready NetCDF:
  `data/processed/pilot/2019-07-15/gefsv12_imd_pair_2019-07-15.nc`, 24,080
  bytes, SHA-256
  `f973e98e7f145c90307fe074a3b76e95eb65a98ba1adadec0f28ccf1183bac0c`.
- Conservative weights: 57,816 bytes, SHA-256
  `37a3fc3244c0ce6c41bf6c580de8748194e7e1dc839e73e0e17285530e245523`.
- Visual QC: `docs/artifacts/phase1b_qc_2019-07-15.png`, 109,845 bytes,
  SHA-256
  `07510a576b48e5f551c8a85686c73095f8622daccbd22a36b811e27548183003`.
- Derived manifest:
  `data/manifests/phase1b/2019-07-15/derived_pair_2019-07-15.json`.

The derived NetCDF contains `raw_nwp_rain_24h`, `observed_rain_24h`,
`valid_mask`, `latitude`, and `longitude`, plus source/window/grid lineage. Its
manifest enforces `training_eligible=false`.

## Measured transfer, storage, runtime, and memory

The original acquisition comprised 3,572,297 NOAA bytes (selected GRIB messages
plus index) and 25,431,832 IMD bytes: 29,004,129 raw bytes total. The pair,
weights, and visual total 191,741 bytes. The final cached validation run used
zero network bytes, took 1.178 seconds, and peaked at 186,462,208 bytes RSS
(about 177.8 MiB).

These one-day, precipitation-only measurements do not validate a linear
extrapolation to the Phase 1A 130–250 GB raw/staging and 8–20 GB processed
planning ranges. A one-month pilot must measure repeated dates, atmospheric
predictors, retries/failures, and compression before revising those estimates.

## Issues and discrepancies found

1. Phase 1A provenance and traceability text said no GEFS field had been decoded,
   while the Phase 1A architecture manifest/report already recorded one decoded
   `0–3` message. Those live-status statements were stale.
2. The Phase 1A architecture's “remaining decisions” repeated GRIB decoding and
   target subsetting even though its own access probe had completed both for one
   message.
3. `docs/07_DATA_SCHEMA.md` still named `nwp_rh700` although the selected GEFS
   minimal predictor contract uses `q700`; this was corrected without claiming
   that predictor acquisition is complete.
4. The official IMD page describes availability through 2024 while its selector
   also exposes 2025. The 2019 pilot is unaffected, but the current endpoint's
   documented coverage is internally inconsistent.
5. The 2019 IMD file has no explicit product-version attribute and its history
   says `20-Feb-26`, later than the represented year; file hash and native
   metadata, rather than an inferred version, are therefore authoritative.
6. The IMD NetCDF date label is midnight and has no time bounds. The 03–03 UTC
   interval comes from official external convention, not from a NetCDF bound.
7. ecCodes `forecastTime` identifies the interval start for these accumulations;
   `startStep`/`endStep` are the unambiguous fields and are used for pairing.
8. Mixed 0.01/0.1 mm GRIB packing precision makes a generic “tiny floating-point
   tolerance” inadequate; the validated tolerance must be tied to packing
   quantum and recorded per run.
9. The first script invocation failed before data processing because direct
   execution did not add the repository root to `sys.path`; the entry point was
   fixed and tested.
10. This workspace still has no Git metadata, so the derived manifest records
    `code_version=unavailable:not-a-git-checkout` and uses per-file code hashes.
11. The Phase 1A Stage 1 plan included one/few atmospheric predictor fields,
    while the Phase 1B task deliberately scoped this one-window pilot to
    precipitation pairing. Atmospheric predictor availability therefore remains
    unvalidated and is explicitly part of the next bounded pilot.

## Automated checks

- Full backend suite: **26 passed**, with one third-party Starlette/anyio
  deprecation warning, in 8.94 seconds.
- `pip check`: no broken requirements.
- Python byte-compilation: passed for `backend/app` and `scripts/data`.
- Reproduction stability: both source manifests, the derived manifest, paired
  NetCDF, weights, and visual retained identical hashes on a cache-only rerun.
- Readiness/API check: five blockers remain, `/api/metrics/overall` returns 409,
  and `/api/status` reports `scientific_readiness.ready=false`.

## Conclusion

The one-window pairing pilot passes. It proves official-source acquisition,
decoded precipitation-window reconstruction, exact daily timing under the
declared external convention, target-domain alignment, mask retention,
conservative-weight generation, conservation QC, and source-to-derived lineage
for one control-member day. It does not prove historical completeness,
predictor availability, event coverage, repeated reliability, training
reproducibility, regime-label validity, model skill, FSS implementation, or
district products. Scientific readiness therefore remains blocked.

The before/after hash record for all 18 protected Phase 0/1A artifacts is
`data/manifests/phase1b/2019-07-15/protected_artifact_integrity.json`; every
entry is unchanged.
