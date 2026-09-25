# Phase 1C One-Month Acquisition Pilot

Status: **PARTIAL — multi-year acquisition not approved**  
Period: 2019-07-01 00 UTC through 2019-07-31 00 UTC  
Executed: 2026-09-19

## Scope and scientific boundary

The pilot attempted every calendar-day initialization, all three exact 24-hour
rainfall windows (`+3..+27`, `+27..+51`, `+51..+75`) for `c00` and `p01`–`p04`,
and control-member U850, V850, Q700, Z500, MSLP, and PWAT at +24/+48/+72 hours.
It reused the official IMD 2019 file acquired in Phase 1B. It did not select days
by rainfall, train a model, create regime labels, calculate FSS, or approximate
district boundaries.

All artifacts remain `training_eligible=false`; scientific inference remains in
`stabilization_blocked` mode.

## Outcome

- Initializations: 31 attempted; 30 PASS, 1 PARTIAL, 0 FAIL, 0 BLOCKED.
- Rainfall cases: 464/465 complete (99.785%).
- Atmospheric snapshots: 558/558 valid (100%).
- IMD product pairings: 93/93 exact-date records, covering 33 unique observation
  dates from 2019-07-02 through 2019-08-03 (record indexes 182–214).
- The one persistent failure is 2019-07-22 00 UTC, `p01`, `day2_24h`. Two cells
  in the nested `36–42 h minus 36–39 h` reconstruction yield −0.2 mm. Both
  messages have 0.1-mm decimal packing precision, so the result exceeds the
  existing 0.1-mm packing-residue tolerance and is rejected, not clipped.
- A first-attempt July 31 Q700 index timeout was independently retried. The
  official object exists, all three messages then passed, and the cache preserved
  all previously valid bytes.

## Rainfall acquisition completeness

| Product | Member | Expected | Complete | Missing | Failed | Completeness % |
|---|---:|---:|---:|---:|---:|---:|
| day1_24h | c00 | 31 | 31 | 0 | 0 | 100.000 |
| day1_24h | p01 | 31 | 31 | 0 | 0 | 100.000 |
| day1_24h | p02 | 31 | 31 | 0 | 0 | 100.000 |
| day1_24h | p03 | 31 | 31 | 0 | 0 | 100.000 |
| day1_24h | p04 | 31 | 31 | 0 | 0 | 100.000 |
| day2_24h | c00 | 31 | 31 | 0 | 0 | 100.000 |
| day2_24h | p01 | 31 | 30 | 0 | 1 | 96.774 |
| day2_24h | p02 | 31 | 31 | 0 | 0 | 100.000 |
| day2_24h | p03 | 31 | 31 | 0 | 0 | 100.000 |
| day2_24h | p04 | 31 | 31 | 0 | 0 | 100.000 |
| day3_24h | c00 | 31 | 31 | 0 | 0 | 100.000 |
| day3_24h | p01 | 31 | 31 | 0 | 0 | 100.000 |
| day3_24h | p02 | 31 | 31 | 0 | 0 | 100.000 |
| day3_24h | p03 | 31 | 31 | 0 | 0 | 100.000 |
| day3_24h | p04 | 31 | 31 | 0 | 0 | 100.000 |

The exact case inventory is
`data/manifests/phase1c/2019-07/rainfall_acquisition_completeness.csv`.

## Observation and event coverage

The target grid is 49×49. Every field has 1,301 valid and 1,100 masked cells;
missing cells remain masked. Event statistics use only IMD observations and the
central 24-hour thresholds: heavy ≥64.5 mm and very heavy ≥115.6 mm.

| Category | Days with at least one cell | Grid-cell events | Maximum observed rainfall |
|---|---:|---:|---:|
| Heavy | 32 | 1,452 | 364.385 mm |
| Very heavy | 27 | 347 | 364.385 mm |

North/South Goa counts were not computed because no authoritative district
geometry is integrated. Full daily max/mean/p90/p95/count/area fractions are in
`data/manifests/phase1c/2019-07/event_coverage.csv`.

## QC summary

| Check | Pass | Fail | Warning |
|---|---:|---:|---:|
| Exact rainfall windows | 464 | 1 | 0 |
| Rainfall conservation, tolerance 1e-10 | 464 | 0 | 0 |
| Atmospheric metadata/snapshot validation | 558 | 0 | 0 |
| IMD exact-date availability | 93 | 0 | 0 |
| Predictor initial plausibility bounds | 6 monthly fields | 0 | 0 |
| Cache-only network isolation | 1 run | 0 | 0 |

Across accepted rainfall windows, 93,357 negative packed differences were within
the pre-existing tolerance and were explicitly set to zero; their minimum was
−0.1 mm. These are counted, not hidden. The rejected −0.2-mm values are outside
that rule.

## Reproducibility and lineage

Source manifests record official object URL, member, index hash, retained byte
range, message metadata, size, and SHA-256. Daily derived manifests hash their
source manifest, paired NetCDF, atmospheric NetCDF, processing code, and weights.
The monthly collection manifest hashes all 62 child manifests. Cache entries have
sidecar receipts and are finalized atomically; identity or checksum disagreement
fails closed. Network-failure tests cover 404, timeout/retry, truncation,
unreceipted partial content, checksum mismatch, and valid cache reuse.

The final unchanged cache-only repeat transferred zero bytes and found 62/62
daily source/derived manifest hashes unchanged, with no new or removed child.
Its result is recorded in
`data/manifests/phase1c/2019-07/execution_cache_validation.json`.

## Runtime and resource observations

Initial acquisition took 1,878.18 s (60.59 s/initialization) and peaked at
252,710,912 bytes RSS. The first fully offline run took 769.05 s. Its measured
stages were 657.70 s precipitation decode/crop, 74.87 s atmospheric
decode/interpolation, 0.79 s rainfall reconstruction/regridding QC, 3.51 s
artifact writes, and 11.16 s monthly consolidation/format benchmarking. The
unchanged warm-cache repeat took 306.53 s; timing variability is therefore
reported rather than hidden. Global
GRIB decoding before regional crop is the dominant local bottleneck; network was
the dominant initial wall-time cost.

## Decision

`DO_NOT_APPROVE_MULTIYEAR_ACQUISITION`

Retrieval, predictor availability, observation matching, conservation, and
resume behavior are strong. However, Phase 1C is PARTIAL because a genuine
rainfall accumulation case remains rejected, and the production historical plan
has not yet frozen its policy for this archive inconsistency, storage format,
versioning, or concurrency. Scaling before that review would multiply an
unresolved scientific exclusion rule across 20 years.

## Evidence files

- `data/manifests/phase1c/2019-07/monthly_collection_manifest.json`
- `data/manifests/phase1c/2019-07/initialization_status.csv`
- `data/manifests/phase1c/2019-07/predictor_availability.csv`
- `data/manifests/phase1c/2019-07/execution_initial.json`
- `data/manifests/phase1c/2019-07/execution_resume.json`
- `data/manifests/phase1c/2019-07/execution_cache_validation.json`

## Phase 1D append-only packing correction

Phase 1D confirmed that the +36→+39 and +36→+42 messages both have decimal
scale factor 1, but they do **not** have the same effective quantum. Their binary
scale factors are 0 and 1, respectively, so the decoded spacings are 0.1 and
0.2 mm. The maximum independent differencing error is therefore 0.15 mm, still
below the observed 0.2 mm decrement. The Phase 1C rejection and all historical
artifacts remain unchanged. `docs/42_GEFS_ACCUMULATION_ANOMALY_REPORT.md` is the
authoritative corrected explanation.
