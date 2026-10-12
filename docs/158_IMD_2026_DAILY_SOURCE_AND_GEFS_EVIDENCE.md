# 2026 IMD daily-source acquisition and GEFS evidence audit

Date: 2026-10-07. This is a source-acquisition result, **not** a 2026 verification result. The frozen forecast archive and model default were unchanged.

## Official annual IMD reference remains unavailable

The third write-once, header-only attempt against IMD's annual RF25 NetCDF endpoint returned HTTP 200 with **zero bytes**. Its protocol and result are `2026_imd_annual_retry_protocol_v3.json` and `2026_imd_annual_retry_result_v3.json` under `data/manifests/research_pilot/`. No NetCDF or annual rainfall values were obtained. The [official annual 0.25° product page](https://imdpune.gov.in/cmpg/Griddata/Rainfall_25_NetCDF.html) remains the intended primary reference. The annual 2026 scorer's preflight still reports `IMD_2026_REFERENCE_CLEARANCE_MISSING` and `GEFS_2026_VERSION_REVIEW_MISSING`.

## Separate IMD real-time daily candidate

The [official IMD daily 0.25° rainfall page](https://imdpune.gov.in/cmpg/Realtimedata/Rainfall/Rain_Download.html) identifies a real-time binary product. Its public official-domain `rain.php` endpoint returned 69,660 bytes per requested date. A single pre-protocol availability request for 30 September 2026 displayed 16 raw hex bytes but decoded no rainfall value; this is disclosed in `2026_imd_realtime_preprotocol_probe_v1.json`. The acquisition protocol was then frozen before any 2026 daily value decoding or forecast pairing.

The bounded, resumable `scripts/acquire_imd_realtime_2026.py` acquisition covered every date **1 June–3 October 2026** (125 grids, 8,707,500 bytes). One 15 July request failed after three attempts because the server closed the connection; a resume fetched only the missing day and rechecked cached hashes. The final manifest `2026_imd_realtime_acquisition_v1.json` (SHA-256 `638e713868e664509176aef207a6117213de437d924dc60f41dc2958cce50db4`) and 125 local per-day receipts verify date, request, byte length and SHA-256. `--check-2026` verified all 125 files and receipts. Raw grids remain ignored, local files; the tracked manifest contains hashes and metadata only. **No 2026 daily rainfall values were decoded, scored or used for fitting.**

A 2025 consumed-test diagnostic compared the real-time grid for 30 September with the locally held official 2025 annual NetCDF. Both had a 129×135 grid, 12,451 missing cells and 4,964 jointly valid cells; 330 valid cells differed. Mean absolute valid-cell difference was 0.00950 mm and maximum was 7.85 mm. Same-day mean absolute difference was far below the previous/next day's 5.12/5.13 mm, supporting the date alignment but **not source equivalence**. The hash-pinned result is `2025_imd_realtime_annual_comparison_v1.json`. An [IMD research report](https://mausam.imd.gov.in/backend/assets/press_release_pdf/Onsetwithrawal_CRS_RESEARCH_REPORT_003_20201.pdf) says its real-time daily analysis is recalculated after year-end as late station data arrive; the observed difference is consistent with, but does not itself prove, that process for this date.

`source_year_ledger_v4.json` appends the complete, unscored daily candidate and the latest empty annual retry without changing earlier ledgers. `2026_imd_realtime_sensitivity_protocol_v1.json` freezes a separate same-case daily-source scorer. Its preflight explicitly requires the **primary annual 2026 score first**, preserving the candidate independent test year. Current preflight is `BLOCKED_BEFORE_VALUE_DECODING` with `PRIMARY_ANNUAL_SCORE_REQUIRED_FIRST`. Even a later daily-source result can only be a provisional sensitivity analysis and cannot promote a model.

IMD's [site disclaimer](https://imdpune.gov.in/disclaimer.html) states that website data should not be reproduced without prior permission. The retrieved disclaimer is hash-pinned in `2026_imd_realtime_access_terms_v1.json`. These grids stay local; raw redistribution and public product rights remain unapproved.

## GEFS version evidence

The downloaded [NWS SCN 26-15](https://www.weather.gov/media/notification/pdf_2026/scn26-15_GEFS_12.3.18.pdf) announced a 12.3.17→12.3.18 change on or about 24 February 2026 for wave-station ensemble statistics. [NWS SCN 26-57](https://www.weather.gov/media/notification/pdf_2026/scn26-57_GEFS_Shortwave_radiation_fix.pdf) announced 12.3.20 from the 15 June 12 UTC cycle for short-wave-radiation GRIB precision. Both notices allow a weather-related postponement. The downloaded [NCO model-change history](https://www.nco.ncep.noaa.gov/pmb/changes/) does not resolve the actual June rollout or the exact 2023 training-corpus patch version. The three local copies and their SHA-256 values are recorded in `2026_gefs_version_source_audit_v1.json`. None of the selected VarshaSetu predictors is explicitly named as changed in SCN 26-57, which does **not** establish numerical equivalence.

Therefore no `2026_gefs_version_clearance_v1.json` was created. The announced-calendar split remains a sensitivity stratum only. The independent-year and public-warning gates remain open.

### Forecast-only radiation packing check

The frozen `2026_gefs_radiation_transition_protocol_v1.json` selected the control-member `DSWRF` 18–24 h average at f024 for 16 June 2023, 15 June 2026 00 UTC, and 16 June 2026 00 UTC. `scripts/probe_gefs_radiation_transition.py` downloaded only the three small NOAA `.idx` files and their indexed GRIB byte ranges, checked HTTP 206 ranges and GRIB identity, and sealed the raw hashes and decoded metadata in `2026_gefs_radiation_transition_result_v1.json`. Its `--check` mode reproduced the six raw hashes and metadata. No observation or VarshaSetu inference was read.

| Cycle | Bits per value | Decimal scale | Binary scale | Selected message bytes |
|---|---:|---:|---:|---:|
| 2023-06-16 00 UTC | 10 | 0 | 0 | 421,944 |
| 2026-06-15 00 UTC | 10 | 0 | 0 | 426,282 |
| 2026-06-16 00 UTC | 16 | 3 | 4 | 914,274 |

This is direct evidence of a changed **published radiation GRIB packing** across the notice's announced 15 June 12 UTC boundary. It is consistent with the [NWS change notice](https://www.weather.gov/media/notification/pdf_2026/scn26-57_GEFS_Shortwave_radiation_fix.pdf), but one field and three cycles do not identify the exact GEFS executable, establish that every listed radiation field changed on that cycle, or prove the selected rainfall predictors are equivalent to 2023. The frozen model and source-version clearance gates remain unchanged.

## Checks and next evidence

- Daily acquisition `--check-2026`: 125 of 125 receipts and file hashes verified, no value decoding.
- Source ledger v4 `--check`: reproduced.
- Dedicated acquisition and daily-reader tests: 5 passed, including tamper refusal and blocked secondary scoring before primary.
- Full backend suite before the radiation probe: 786 passed; its three additional range/cache tests passed. The one-shot radiation evidence integrity check passed.
- The primary annual scorer and secondary daily scorer both refuse before observation-value access in the present state.

Next: obtain the complete authorized annual 2026 IMD file, document its terms and exact 03–03 UTC window, and resolve actual GEFS implementation/version comparability. Run the pre-frozen annual one-shot comparison only after those gates pass. Then run the separately frozen daily-source sensitivity if desired. Neither source should be used to tune 2026 thresholds, models, QC, or masks.
