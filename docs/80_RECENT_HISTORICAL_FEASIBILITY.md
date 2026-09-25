# Phase 4A — Recent Historical Operational GEFS Feasibility

Status: **GO for a separately authorized, bounded external-historical evaluation**; not operational readiness, not a new training corpus, and not a frontend release. Audit performed 2026-09-24 IST. The unmodified 2017/2018/2019 GEFSv12-reforecast → IMD experiment remains the authority for published prototype skill.

## 1. Executive summary

Actual official IMD annual 0.25° NetCDF files for 2023, 2024 and 2025 were downloaded, hashed, decoded, and checked across the required June 1–October 3 dates. Official NOAA-hosted historical *operational* GEFS indexes for representative July 2023/2024/2025 cycles were reachable. A predeclared 2024-07-15 00Z Day-1 case failed the unchanged canonical packing-bound rule and was quarantined. The next chronological cycle, 2024-07-16 00Z, passed the same rule, the six-predictor GRIB identity checks, the frozen 22-feature schema, and inference-only loading of the frozen Global XGBoost, regime classifier, and both calibrated probability models. Its forecast was evaluated only afterward against the matching July 17 IMD field. This is a feasibility demonstration, not evidence of transferred population skill.

All work and approximately 86 MB of source/probe files are isolated under `experiments/recent_historical/`. No frozen corpus, model, calibrator, API, frontend, metric, or selection manifest was changed. The experimental artifact manifest covers 145 files / 86,122,476 bytes and has SHA-256 `f117a0d8da650ff6f9c7081f1c819b41992d9c579ba811845f56bc372d6c0b8a`.

## 2. IMD 2023 availability

**Verified actual file**, not merely a website entry: provider-form `POST RF25=2023` returned NetCDF classic (`CDF\001`), 25,431,832 bytes, SHA-256 `1fa0cbcb56769fd3cd2702e36dc3ee1b81b74755b77c7f058c70dfc3afb82831`. It contains 365 consecutive daily records, including all 125 required dates June 1–October 3. Its `TIME` variable has no explicit `calendar` attribute; the reader uses the standard/CF default and verified consecutive day values. This omission must be retained as metadata, not silently labeled `GREGORIAN`.

## 3. IMD 2024 availability

**Verified actual file**: `POST RF25=2024` returned NetCDF classic, 25,501,532 bytes, SHA-256 `1ef02aeba5694dbb57a6cca23a3c2cc11740affb185137c1eacbeab59893228a`. It contains 366 consecutive daily records and all 125 required dates. Its `TIME.calendar` is `GREGORIAN`. The July 17 record supplied the one-case reference after model inference was complete.

## 4. IMD 2025 availability and completeness

The [IMD product page](https://imdpune.gov.in/cmpg/Griddata/Rainfall_25_NetCDF.html) still says the series ends in 2024. **Nevertheless the actual 2025 file is verified and complete for the required period**: `POST RF25=2025` returned a readable NetCDF classic file of 25,431,832 bytes, SHA-256 `7d03cd397ebb1d7209ffae947d3965113643e1f30023cca657f0aa2c800af035`, with 365 consecutive daily records and all 125 June 1–October 3 records. Its `TIME` variable, like 2023, omits an explicit `calendar`. The page-text/actual-file discrepancy is real; a selector entry alone was not used as proof.

## 5. Official NOAA operational GEFS sources

The actual source is NOAA's public `noaa-gefs-pds` bucket, documented by the [NOAA/AWS GEFS registry](https://registry.opendata.aws/noaa-gefs/) and [NOAA NCO product inventory](https://www.nco.ncep.noaa.gov/pmb/products/gens/). The exact investigated pattern is `gefs.YYYYMMDD/00/atmos/{pgrb2sp25,pgrb2ap5,pgrb2bp5}/gec00.t00z.*.fNNN` with `.idx` sidecars. Representative July 15 00Z control indexes for 2023, 2024 and 2025 returned HTTP 200 for 0.25° rainfall `f024/f075` and 0.5° atmospheric primary/secondary `f024`. This is a **spot-check**, not proof that every JJAS initialization is complete. For 2024 July 15 and 16, 35 selected index sidecars per initialization were checked without failures; actual 12-message GRIB range sets were decoded for each Day-1 candidate.

The [NOAA/NCEI GEFS page](https://www.ncei.noaa.gov/products/weather-climate-models/global-ensemble-forecast) expressly says its own archive ends in September 2020 and that NOAA Open Data Dissemination cloud data are **not officially archived**. Thus S3 availability today must not be treated as a retention guarantee. NOMADS/NCEP's rotating access is not a verified 2023–2025 historical archive. The NOAA public bucket, rather than the 2000–2019 reforecast bucket, supplied this probe.

## 6. GEFSv12 reforecast versus operational GEFS

The [reforecast description](https://noaa-gefs-retrospective.s3.amazonaws.com/Description_of_reforecast_data.pdf) documents a retrospective 2000–2019 archive with daily `c00,p01–p04` (and more on some weekly dates), variable-family GRIB files, and retrospective initial conditions. [NOAA EMC](https://emc.ncep.noaa.gov/emc/pages/numerical_forecast_systems/gefs.php/) documents operational GEFSv12 from September 2020, 00/06/12/18 UTC cycles, 31 members (30 perturbed plus control), and an evolving operational analysis/production context. The 2024 records are grouped lead-file products, not the reforecast's variable-family objects. Identical decoded variable identities on one date do not establish identical forecast-error distributions, packing, initialization, or long-term production versions. The NCEI page's generic “21 members” description conflicts with EMC/NCO's 31-member operational configuration; use dated actual inventory per cycle, not that generic count.

## 7. Required model predictor compatibility matrix

Frozen model order is `raw_c00_rain_mm`, U850, V850, Q700, Z500, MSLP, PWAT, twelve forecast-derived regime diagnostics, latitude, longitude, lead hours: exactly 22 inputs. Phase 2C appends frozen M2 rainfall and three forecast-only regime probabilities to make 26. The following 2024 July 16 `+24 h` GRIB messages were **decoded and validated** using existing identity checks. The `+48/+72 h` entries were verified in July 15/16 index metadata but **not decoded** in this bounded probe.

| Required field | Reforecast object / decoded identity | Operational object / index identity | Level, actual units, source grid | Frozen transformation | Finding |
|---|---|---|---|---|---|
| Raw c00 24-h rainfall | `apcp_sfc` / `tp` | `pgrb2sp25` / `APCP`, decoded `tp` | surface, kg m⁻², 0.25° | exact interval cover; 1 kg m⁻² = 1 mm; 49×49 target crop | Day 1 verified on July 16; July 15 QC failed |
| U850 | `ugrd_pres` / `u` | `pgrb2ap5` / `UGRD`, decoded `u` | 850 hPa, m s⁻¹, 0.5° | context crop; bilinear alignment to target | verified +24; +48/+72 index-only |
| V850 | `vgrd_pres` / `v` | `pgrb2ap5` / `VGRD`, decoded `v` | 850 hPa, m s⁻¹, 0.5° | same | verified +24; +48/+72 index-only |
| Q700 | `spfh_pres_abv700mb` / `q` | `pgrb2bp5` / `SPFH`, decoded `q` | 700 hPa, kg kg⁻¹, 0.5° | same | verified +24; +48/+72 index-only |
| Z500 | `hgt_pres_abv700mb` / `gh` | `pgrb2ap5` / `HGT`, decoded `gh` | 500 hPa, gpm, 0.5° | same | verified +24; +48/+72 index-only |
| MSLP | `pres_msl` / `msl` | `pgrb2bp5` / `PRES` at mean sea level, decoded `msl` | mean sea level, Pa, 0.5° | same | verified +24; do **not** substitute 0.25° `PRMSL` without policy |
| PWAT | `pwat_eatm` / `pwat` | `pgrb2ap5` / `PWAT`, decoded `pwat` | entire atmosphere, kg m⁻², 0.5° | same | verified +24; do **not** substitute another column definition |

The twelve diagnostics are recomputed from these six 0.5° forecast fields by the frozen Phase 2A code, then repeated per target cell. Coordinates and lead are static/forecast-known. No observation is an inference feature. Bilinear interpolation aligns grids; it does not invent meteorological source resolution.

## 8. Ensemble-member compatibility

Operational index sidecars for `gep01`–`gep04` at July 15/16 `f024` exist and identify their respective perturbed members. They were **not** fully decoded for every required interval and were **not** substituted for the reforecast members as though the forecast systems were homogeneous. Frozen M2, the regime classifier, and the selected heavy/very-heavy probability models use control-based features and ran without full-ensemble input. Phase 2C's P0 five-member threshold-fraction comparator specifically needs c00+p01–p04 all valid on a matched case; it remains **unverified/not computed** here. Other operational perturbed members do not silently replace missing p01–p04.

## 9. Forecast accumulation alignment

For both 2024 index-probed initializations, all 25 control `APCP` leads `+3,+6,…,+75` were present. Index rows show the same alternating native three-/six-hour interval pattern relevant to the frozen Phase 1F exact-cover method. Actual decoded July 16 Day-1 coverage was `(0–6 − 0–3) + 6–12 + 12–18 + 18–24 + 24–27`, exactly `+3→+27 h`, five non-overlapping segments, one subtraction, zero negative-residue normalizations, finite nonnegative 49×49 output. The one difference's packing bound was 0.01 mm. July 15's equivalent difference had 34 negative cell occurrences, including two below the 0.055-mm bound (minimum −0.06 mm); that entire Day-1 rainfall product was quarantined. No bound was relaxed. Day 2 `+27→+51` and Day 3 `+51→+75` have index coverage but no actual reconstruction/QC result in this phase.

## 10. Observation time alignment

The frozen contract pairs a 00Z initialization's Day 1 `+03→+27 h` with the following IMD valid date's `03:00→03:00 UTC` 24-hour window, equivalent to 08:30→08:30 IST. [IMD's API reference](https://api.imd.gov.in/public/api_reference.html) describes its past-24-hour rainfall convention as 08:30 IST previous day to 08:30 IST current day, and [IMD rainfall information](https://imdgeospatial.imd.gov.in/Rainfall/) labels 24-hour rainfall at 08:30 IST. The July 16 operational forecast was paired with the July 17 IMD daily record only after explicitly matching those windows. **Limitation:** the annual gridded NetCDF itself contains date-only `TIME` labels and no accumulation time bounds; provider documentation of that exact file's window remains less explicit than ideal. This is the same documented convention used in the frozen 2017–2019 corpus, not a newly inferred shift.

## 11. Actual 2024 sample acquisition

Candidate rule: begin with 2024-07-15 00Z, then use the immediately following 2024-07-16 00Z only if source/canonical QC blocks the first; never select by verification score. Both cycles' small indexes were acquired first. Twelve selected GRIB byte ranges per candidate (six rainfall, six atmosphere) were then retrieved with HTTP 206 and exact `Content-Range`, byte-count, `GRIB`/`7777`, SHA-256 and decoded identity validation. July 15's control rainfall failed canonical QC before any inference. July 16 passed and was inferred before opening its July 17 observation for scoring. No full GRIB lead file, full season, or reforecast source was downloaded/re-decoded.

## 12. Real file metadata

All IMD files: `RAINFALL(TIME,LATITUDE,LONGITUDE)` float32, millimetres, 129×135 at 0.25° from 6.5–38.5°N and 66.5–100°E; `_FillValue=missing_value=−999`. Target crop is 49×49, 10–22°N / 68–80°E, with 1,301 valid and 1,100 masked cells on each required day. Dates are daily and contiguous. 2023/2025 lack an explicit calendar attribute; 2024 declares `GREGORIAN`. GRIB rain is global 1440×721 at 0.25°; all six operational atmosphere messages are global 720×361 at 0.5°, then cropped to the established 51×81 context grid (5–30°N, 55–95°E). Actual July 16 decoded step/init/member, level, units and grid metadata are in `noaa/20240716T00Z/case_probe.json`.

## 13. Source provenance and hashes

The three IMD source SHA-256 values are in sections 2–4 and their source/HTTP/file metadata in `imd/imd_{year}_manifest.json`. The source endpoint is `https://www.imdpune.gov.in/cmpg/Griddata/RF25.php`, official form `RF25=year`; the response attachment names `RF25/indYYYY_rfp25.nc`. Actual 2024 NOAA index sidecars, exact source object URLs, downloaded byte ranges, HTTP receipts, decoded metadata, and per-range hashes are retained under `noaa/20240715T00Z/` and `noaa/20240716T00Z/`. The 2023/2025 representative checks are in `noaa/cross_year_archive_probe.json`. `artifact_manifest.json` and its sidecar hash the entire isolated experimental evidence set. These hashes establish byte integrity, not meteorological truth.

## 14. Existing QC results

IMD: 125/125 required dates per year, nonnegative valid rainfall, constant 1,301-cell target mask, no zero-valid day, native coordinate orientation and dimensions intact. NOAA: all selected 2024 indexes present; retrieved ranges complete; c00 init/member, accumulation/instantaneous step type, variable/level/unit, monotone coordinate, finite atmosphere and target/context shapes checked with existing code. July 15 fails one canonical product because of two material negative intermediate cells; July 16 Day 1 passes. These are **two local cases only**, not a seasonal acceptance rate. No 2023/2025 GRIB data field was decoded.

## 15. Feature-schema compatibility

The July 16 forecast-only feature matrix had shape `2401×22`, exactly the frozen Phase 2B ordered schema, float32, finite. The 0.5° context fields were bilinearly aligned with the unchanged implementation; 12 derived regime fields came from the unchanged forecast-only extraction. The frozen model-selection manifest, Global XGBoost JSON, Phase 2A logistic JSON, Phase 2C selection manifest, both probability models and both calibrators were hash-checked before inference. Probability input was exactly `2401×26`. Predictions were computed across the 49×49 grid; scoring used only the 1,301 IMD-valid paired cells. A future external dataset must have a new dataset/version identifier and repeat this gate per case; it must never be appended to the homogeneous reforecast corpus.

## 16. Distribution-shift observations

Against the 2017 training-cell feature cache's 1st–99th percentile ranges, the July 16 case-level PWAT mean was 57.747 versus a training p99 of 53.050 kg m⁻², Q700 mean 0.009672 versus 0.008563 kg kg⁻¹, and moisture-transport mean 695.39 versus 661.48 in its derived units. These three scalar diagnostics were therefore above the reference p99 for all 1,301 paired cells. About 30% of Q700 target-cell values and 24% of PWAT target-cell values also lay outside the respective 2017 p01–p99 ranges. This single date is a **shift warning**, not proof of climatological drift or model failure. It reinforces the need for a multi-date external validation before any product claim or recalibration proposal.

## 17. Frozen-model inference feasibility

**Verified for one July 16 Day-1 case.** The existing M2 Global XGBoost predicted nonnegative corrected rainfall; the frozen forecast-only regime classifier emitted `[0.004457, ≈0, 0.995543]` for its *project pseudo-label classes*, not independent meteorological truth. Frozen calibrated heavy XGBoost+sigmoid and very-heavy logistic+isotonic produced values within [0,1], with full-grid means 0.1101 and 0.0179 respectively. No model was fit or recalibrated, no 2019 selection changed, and IMD data were absent from the inference script. The July 15 failed product was not inferred.

## 18. Optional one-case results

On **2024-07-16 00Z Day 1 → IMD July 17**, exactly 1,301 common valid land cells: Raw operational GEFS RMSE/MAE/bias = **20.3662 / 10.9538 / +0.3663 mm**; frozen M2 correction = **19.5035 / 10.2870 / −1.9128 mm**. The observed field had 61 heavy and only seven very-heavy cells. At the frozen probability cutoffs, heavy Brier = 0.04058, BSS against 2017 climatology = 0.1133, PR-AUC = 0.2143; very-heavy Brier = 0.005543, BSS = −0.0343, PR-AUC = 0.0378. Raw heavy CSI was 0.0139 while deterministic correction's was 0; the corrected field forecast zero heavy/very-heavy threshold exceedances. One-case heavy FSS was 0 for correction at all frozen scales, versus Raw 0.0274/0.0564/0.0790/0.1018 at 1/3/5/9 cells. These scores **do not establish a new skill ranking**; the very-heavy sample is extremely small, and this one case cannot validate calibration or operational transfer. Detailed counts, undefined metric reasons, ROC-AUC, FSS and feature diagnostics are in `evaluation.json`.

## 19. 2023 and 2025 expansion feasibility

Both annual IMD files passed complete required-period checks, and July 15 operational NOAA control indexes for both years are available. This makes subsequent small-case probing plausible. It does **not** prove all 122 monsoon initializations, lead files, exact accumulation intervals, atmospheric fields or five rainfall members survive source QC in either year. Any expansion must begin with a versioned source inventory and case-tiered admission, not an automatic 366-case assumption.

## 20. Estimated data volume

From the actual July 16 `.idx` byte offsets, selecting 25 control rainfall messages through +75 h is 7,961,855 bytes and 18 c00 atmosphere messages at +24/+48/+72 is 4,196,149 bytes: **12,158,004 bytes per initialization** before indexes/receipts. At 122 JJAS initializations × three years, a same-size control-only source estimate is **4.45 GB**. Adding p01–p04 rainfall at the same measured control-message size yields **16.11 GB** selected source ranges, not whole GRIB lead files. Three annual IMD files total **76.37 MB**. This extrapolation ignores variability, missing/retried files, metadata, normalized arrays, staging and duplication; reserve approximately 10–15 GB control-only or 35–50 GB for a five-member audited workflow. About 107 GB was free on the local NVMe during this probe. These are planning estimates, not authorized downloads.

## 21. Estimated processing time

The current per-initialization contract implies roughly 43 selected control GRIB messages (25 rainfall + 18 atmosphere), or 143 with five rainfall members, before source-index reads. Across three JJAS seasons that is approximately 15,738 or 52,338 selected GRIB range requests respectively, plus indexes and retries. Two bounded 12-message probes completed in tens of seconds each on this workstation, but they are **not** a stable throughput benchmark. Plan at least hours to a few days of staged acquisition/decoding/QC with month gates, network throttling and cache reuse; benchmark a representative week before committing worker counts. Do not change frozen Phase 1 acquisition concurrency from this feasibility run.

## 22. Storage requirements

The measured 86 MB isolated probe fits easily, but a broader study needs immutable source receipts/ranges, normalized chunked arrays, separate experimental manifests, temporary download headroom and backups. Maintain the existing 18–20 GB normal RAM cap and NVMe caching policy; decode global GRIB messages in bounded workers before regional crop. Do not load three annual forecast corpora into RAM. A source-retention plan matters because NOAA/NCEI explicitly says NODD data are not officially archived.

## 23. Scientific risks and documentation/code discrepancies

- One of two predeclared Day-1 cases failed the mathematically frozen packing gate. No seasonal acceptance fraction may be inferred from two cases.
- Exact gridded-IMD accumulation time bounds are not encoded in the downloaded NetCDF; the matching 08:30 convention comes from existing project governance and official IMD rainfall-service documentation, not a file-level bounds variable.
- The IMD page says 1901–2024 although a complete 2025 file is actually downloadable; annual files have no explicit product-version attribute, and 2023/2025 omit `TIME.calendar`.
- NOAA/NCEI's generic 21-member language conflicts with the NOAA EMC/NCO 31-member operational configuration. Actual per-cycle/member provenance is required.
- `AGENTS.md` §3.6 still calls the “current project target” 6-hour rainfall, a legacy statement contradicted by the active canonical Phase 1F/2B/2C **24-hour** code, docs 51/58/63 and model feature contract. This audit followed the frozen current 24-hour path and did not edit governance.
- `docs/32` retains historical v1 eight-increment and 0.1-mm-cap language before its v2 supersession; doc 51 and `reconstruct_minimal_accumulation_window` are authoritative for this probe.
- Reforecast-specific acquisition/object naming and homogeneous dataset version cannot be reused for grouped operational files. The new adapter must be external-versioned; no backend/API alteration was made here.
- Frozen correction improved one-case RMSE but suppressed deterministic heavy exceedances and failed to improve this case's heavy FSS; the very-heavy BSS was negative. No cherry-picked positive claim is warranted.
- Public NOAA cloud retention, full-member completeness, later operational configuration changes, IMD reuse/redistribution terms, and seasonal calibration transfer are unresolved.

## 24. Recommended next implementation scope

A **separate**, explicitly approved Phase 4B should define an external-operational dataset version and bounded source inventory for a predeclared representative week in 2024 (then limited 2023/2025 cross-checks), implement resumable official-range acquisition and grouped-file mapping without changing frozen adapters, apply the unchanged exact-cover packing QC and case-tiered admission, run frozen inference only on admitted common cases, and report paired raw/corrected/probability/FSS scores with uncertainty and transfer diagnostics. Confirm exact gridded-IMD timing and distribution rights with IMD if the product will be redistributed. Audit p01–p04 through all required steps before computing the five-member P0 comparator. Do **not** authorize a three-year acquisition or frontend tab from this one-case result.

## 25. Complete source references

All external sources accessed 2026-09-24 IST; source bytes/receipts are in the isolated experimental manifest.

1. [IMD Pune, annual 0.25° gridded NetCDF page](https://imdpune.gov.in/cmpg/Griddata/Rainfall_25_NetCDF.html), including Pai et al. (2014) citation and IMD accuracy/liability disclaimer. No general redistribution permission was established; cite IMD/Pai and verify distribution terms before sharing raw files.
2. [IMD Pune official RF25 form endpoint](https://www.imdpune.gov.in/cmpg/Griddata/RF25.php), annual downloads by `POST RF25=year`; hashes in local manifests.
3. [IMD API Reference](https://api.imd.gov.in/public/api_reference.html) and [IMD Rainfall Information](https://imdgeospatial.imd.gov.in/Rainfall/), 08:30 IST past-24-hour context.
4. [NOAA Global Ensemble Forecast System, AWS Open Data Registry](https://registry.opendata.aws/noaa-gefs/), official bucket/access and attribution/no-endorsement terms.
5. [NOAA/NCO GEFS operational product inventory](https://www.nco.ncep.noaa.gov/pmb/products/gens/), 0.25° selected and 0.5° primary/secondary file families, cycles/leads/members.
6. [NOAA/EMC operational GEFS configuration](https://emc.ncep.noaa.gov/emc/pages/numerical_forecast_systems/gefs.php), operational GEFSv12 implementation and configuration.
7. [NOAA/NCEI GEFS archive note](https://www.ncei.noaa.gov/products/weather-climate-models/global-ensemble-forecast), cloud-data retention qualification and NCEI archive boundary.
8. [NOAA GEFSv12 reforecast description](https://noaa-gefs-retrospective.s3.amazonaws.com/Description_of_reforecast_data.pdf), retrospective archive format/member structure.
9. Actual official NOAA 2024 source example: [July 16 c00 +24 h 0.25° index](https://noaa-gefs-pds.s3.amazonaws.com/gefs.20240716/00/atmos/pgrb2sp25/gec00.t00z.pgrb2s.0p25.f024.idx). Exact consulted objects and hashes are in local receipts.

## Decision gate

**GO** — A genuine operational 2024 case passed unchanged canonical rainfall and six-field predictor QC, produced the exact frozen feature matrices and safe-model outputs, and was paired with a complete official IMD day only after inference. GO authorizes proposing a *separate limited external-evaluation phase only*. It does **not** establish model transfer skill, seasonal data completeness, operational readiness, full-season acquisition, retraining, API change or frontend integration.
