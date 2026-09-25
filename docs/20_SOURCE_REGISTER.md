# Source Register

## Purpose

This register separates external evidence from project implementation claims.

A source being listed here does **not** mean its data are already integrated.

## Primary problem statement

### SIH26080
- Title: Regime-Aware AI Post-Processing of Monsoon Rainfall Forecasts
- Organization: MoES / NCMRWF
- Source snapshot supplied in project context.
- Recorded URL: `https://sih.gov.in/sih2026PS`
- Current supplied snapshot: dataset link N/A.

## OpenAI Codex workflow

### Introducing Codex
- `https://openai.com/index/introducing-codex/`
- Relevant point: `AGENTS.md` files provide scoped repository instructions such as conventions and test commands.

### How OpenAI uses Codex
- `https://openai.com/business/guides-and-resources/how-openai-uses-codex/`
- Relevant point: prompts work well when structured like issues; persistent repo context can live in `AGENTS.md`.

## NCMRWF weather-pattern context

### NCMRWF probabilistic weather patterns
Example:
- `https://nwp.ncmrwf.gov.in/NCMRWF-WeatherPatterns/ncmrwf_summary_2024070700_30patterns_62W_98E_2S_37N_850hPaWind.html`

This public research-prototype output includes categories such as:
- Active Monsoon,
- Break Monsoon,
- Western Disturbances,
and presents them probabilistically.

Use only as conceptual/scientific context unless direct data integration is explicitly implemented.

## FSS / spatial verification

### ECMWF — Scale-dependent verification of precipitation and cloudiness
- `https://www.ecmwf.int/en/newsletter/174/earth-system-science/scale-dependent-verification-precipitation-and-cloudiness`

Relevant concepts:
- high-resolution precipitation suffers double-penalty under pointwise metrics,
- FSS compares neighbourhood fractions,
- multiple thresholds and neighbourhood scales should be assessed.

## IMD rainfall categories

Official IMD forecast/rainfall products show 24-hour cumulative rainfall categories such as:
- Moderate: 15.6–64.4 mm,
- Heavy: 64.5–115.5 mm,
- Very Heavy: 115.6–204.4 mm,
- Extremely Heavy: ≥204.5 mm.

Example official IMD product:
- `https://mausam.imd.gov.in/backend/assets/aiwfb_pdf/765b247236f8890456ba2dfa6059ed34.pdf`

The project must preserve the accumulation period associated with a threshold.

## Source quality hierarchy

Prefer:
1. official SIH/MoES/NCMRWF/IMD,
2. official dataset documentation,
3. peer-reviewed research,
4. operational centre documentation,
5. secondary sources only if primary source unavailable.

## Citation discipline inside project docs/UI

For every important scientific definition:
- record source URL/DOI,
- avoid copied long passages,
- summarize accurately,
- include access date for volatile pages.

## Phase 1A authoritative data sources

All entries below were accessed on 2026-09-19. Listing a source does not by
itself mean its data have been acquired or integrated. The explicit Phase 1B
entries identify the one source-backed exception.

### NOAA GEFSv12 Reforecast

- Provider: NOAA/NCEP via AWS Open Data.
- Title: *NOAA Global Ensemble Forecast System (GEFS) Reforecast*.
- URL: `https://registry.opendata.aws/noaa-gefs-reforecast/`
- Supports: public bucket, 2000–2019 retrospective forecasts, daily 00 UTC
  initialization, daily/weekly member structure, attribution/access notes.

- Provider: NOAA/NCEP.
- Title: *Description of the GEFSv12 Reforecast Data Set*.
- URL: `https://noaa-gefs-retrospective.s3.amazonaws.com/Description_of_reforecast_data.pdf`
- Supports: GRIB2 layout, resolutions, lead cadence, variables/levels, pressure
  and precipitation units, and alternating precipitation accumulation semantics.

- Provider: NOAA Physical Sciences Laboratory.
- Title: *20 Years of GEFSv12 Reforecasts Now Available at AWS*.
- URL: `https://psl.noaa.gov/news/2022/042122a.html`
- Supports: reforecast status and distinction between historical initialization
  data and positive-lead model predictions.

- Provider: NOAA/NCEP AWS object store.
- Title: live GEFSv12 object listing and `apcp_sfc` index sidecar.
- URL: `https://noaa-gefs-retrospective.s3.amazonaws.com/?list-type=2&prefix=GEFSv12/reforecast/2000/2000010100/c00/`
- Supports: actual object names/sizes and `.idx` availability. The 5,960-byte
  precipitation index and first 422,515-byte GRIB message were fetched in memory,
  hashed, decoded, and locally subset; neither was retained as a file.

- Provider: NOAA/NCEP official GEFSv12 reforecast object store.
- Title: *Phase 1B 2019-07-14 00 UTC `c00` precipitation object*.
- URL: `https://noaa-gefs-retrospective.s3.amazonaws.com/GEFSv12/reforecast/2019/2019071400/c00/Days%3A1-10/apcp_sfc_2019071400_c00.grib2`
- Supports: retained, checksummed byte ranges for all nine GRIB messages needed
  to reconstruct the +3..+27-hour pilot window. Manifest:
  `data/manifests/phase1b/2019-07-15/noaa_gefsv12_2019071400_c00_apcp.json`.

- Provider: NOAA/NCEP official GEFSv12 reforecast object store.
- Title: *Phase 1C July 2019 bounded collection*.
- Object pattern:
  `https://noaa-gefs-retrospective.s3.amazonaws.com/GEFSv12/reforecast/2019/{YYYYMMDD00}/{member}/Days%3A1-10/{family}_{YYYYMMDD00}_{member}.grib2`
- Supports: retained checksummed ranges for 31 initializations, five
  precipitation members through +75 h, and control U850/V850/Q700/Z500/MSLP/PWAT
  at +24/+48/+72. Direct index/GRIB evidence corrected Q700's family to
  `spfh_pres_abv700mb`. Collection manifest:
  `data/manifests/phase1c/2019-07/monthly_collection_manifest.json`.
- Limitation: one `p01` Day-2 nested rainfall increment on 2019-07-22 fails the
  packing-residue gate; this collection is not training-eligible.

### Operational GFS/GEFS archives

- Provider: NOAA/NCEI.
- Title: *Global Forecast System (GFS)*.
- URL: `https://www.ncei.noaa.gov/products/weather-climate-models/global-forecast`
- Supports: operational forecast archive periods/resolutions and historical
  archive/request options; operational data are version-changing forecasts, not
  the homogeneous GEFSv12 reforecast.

- Provider: NOAA/NCEP via AWS Open Data.
- Title: *NOAA Global Forecast System (GFS)*.
- URL: `https://registry.opendata.aws/noaa-gfs-bdp-pds/`
- Supports: recent operational GFS cloud access and organization.

- Provider: NOAA/NCEP via AWS Open Data.
- Title: *NOAA Global Ensemble Forecast System (GEFS)*.
- URL: `https://registry.opendata.aws/noaa-gefs/`
- Supports: current operational GEFS archive, initialization frequency, and lead
  range; candidate for recent external cases rather than primary training.

- Provider: NOAA/NCEP.
- Title: *NOMADS Data Access*.
- URL: `https://nomads.ncep.noaa.gov/`
- Supports: recent operational products and GRIB variable/level/geographic
  filtering, subject to each dataset's retention.

### NCMRWF forecast products

- Provider: NCMRWF/MoES.
- Title: *Severe Weather Forecast Programme—India*.
- URL: `https://nwp.ncmrwf.gov.in/HomePage/index.php`
- Supports: NCUM global analysis/forecast cycles, approximate resolution and
  forecast range, and NEPS member/range description.

- Provider: NCMRWF/MoES.
- Title: *NEPS Products*.
- URL: `https://nwp.ncmrwf.gov.in/HomePage/NEPS-prod-1.php`
- Supports: evidence that public pages expose recent chart products, not a
  documented student-accessible historical grid archive.

- Provider: NCMRWF/MoES.
- Title: *NCMRWF technical report on operational model data processing*.
- URL: `https://nwp.ncmrwf.gov.in/publication/Technical_Report_VHazra_final.pdf`
- Supports: internal model-file processing and GRIB2/NetCDF conversion context;
  not evidence of public historical-file access.

### IMD rainfall reference

- Provider: India Meteorological Department, Pune.
- Title: *High Resolution 0.25 Degree Daily Gridded Rainfall Data*.
- URL: `https://imdpune.gov.in/lrfindex.php/cmpg/Product/cmpg/Griddata/Rainfall_25_NetCDF.html`
- Current official route used by Phase 1B:
  `https://imdpune.gov.in/cmpg/Griddata/Rainfall_25_NetCDF.html` with form POST
  `RF25=2019` to `RF25.php`.
- Supports: official NetCDF product/download context. Phase 1B acquired
  `RF25_ind2019_rfp25.nc` and read `_FillValue=-999`, `missing_value=-999`,
  grid/time/global metadata, citation, disclaimer, and file hash. The file has no
  explicit product-version attribute and no accumulation time bounds. Manifest:
  `data/manifests/phase1b/2019-07-15/imd_rf25_2019.json`.
  Phase 1C reused the identical checksum without network transfer and matched 93
  forecast products to exact IMD records spanning 2019-07-02 through 2019-08-03.

- Provider: India Meteorological Department.
- Title: *Development of a new high spatial resolution (0.25° × 0.25°) long
  period (1901–2010) daily gridded rainfall data set over India*.
- URL: `https://www.imdpune.gov.in/Reports/NCCResearchReports/research_report_18.pdf`
- Supports: gauge basis, method, 0.25° resolution, original period, station input,
  QC/interpolation, and documented India grid/domain.

- Provider: India Meteorological Department.
- Title: *Rainfall Information / Past 24 Hours*.
- URL: `https://imdgeospatial.imd.gov.in/Rainfall/`
- Supports: 24-hour observation ending at 08:30 IST and official heavy,
  very-heavy, and extremely-heavy rainfall category ranges.

- Provider: India Meteorological Department.
- Title: *IMD API Reference*.
- URL: `https://api.imd.gov.in/public/api_reference.html`
- Supports: 08:30-to-08:30 IST past-24-hour time convention.

### NASA GPM IMERG V07

- Provider: NASA GPM.
- Title: *Integrated Multi-satellitE Retrievals for GPM (IMERG)*.
- URL: `https://gpm.nasa.gov/data/imerg`
- Supports: V07 coverage, 0.1°/half-hourly characteristics, Early/Late/Final
  latency distinction, and role of gauge analysis in the Final product.

- Provider: NASA GPM.
- Title: *IMERG V07 Technical Documentation*.
- URL: `https://gpm.nasa.gov/resources/documents/imerg-v07-technical-documentation`
- Supports: official algorithm and product documentation.

- Provider: NASA GPM.
- Title: *Data Directory*.
- URL: `https://gpm.nasa.gov/data/directory`
- Supports: official access routes and subsetting services.

- Provider: NASA PPS.
- Title: *GPM IMERG Final Precipitation L3 Half Hourly 0.1° × 0.1° V07*.
- URL: `https://pps.gsfc.nasa.gov/Documents/V07/doi/3IMERGHH_GIS_30MIN_V07.html`
- Supports: Final half-hourly product identity and access/citation context.

### Spatial alignment and boundaries

- Provider: Earth System Modeling Framework.
- Title: *Regridding*.
- URL: `https://earthsystemmodeling.org/regrid/`
- Supports: conservative regridding via source/target cell overlap and the need
  for explicit grid geometry.

- Provider: Survey of India.
- Title: *Administrative Boundary Data Base (ABDB)*.
- URL: `https://surveyofindia.gov.in/pages/administrative-boundary-data-base-abdb-`
- Supports: authoritative national administrative boundaries through district
  and subdistrict levels.

- Provider: Survey of India.
- Title: *Digital Products / Administrative Boundaries*.
- URL: `https://onlinemaps.surveyofindia.gov.in/Digital_Products.aspx?id=aUJENBZyfoy92ggfHhqVHQ`
- Supports: shapefile product/access context and terms to confirm at acquisition.

- Provider: Survey of India.
- Title: *Vector Data Catalog 2025*.
- URL: `https://www.surveyofindia.gov.in/UserFiles/files/Vector%20Data%20Catalog%202025%281%29.pdf`
- Supports: boundary catalog/version context and Goa district/subdistrict counts.

- Provider: Government of India, National Water Informatics Centre.
- Title: *Admin Boundaries*.
- URL: `https://www.data.gov.in/catalog/admin-boundaries`
- Supports: government fallback boundary source under the portal's published
  terms if Survey of India acquisition is impractical.
