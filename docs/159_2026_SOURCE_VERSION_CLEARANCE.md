# 2026 source and GEFS version clearance: open audit

Date: 2026-10-07. This is a metadata-only follow-up to `docs/155`–`docs/158`. It does not modify the frozen forecast archive, comparison protocol, scorer, primary reference choice, model default, or publication gate. No 2026 rainfall value was decoded, paired, fitted, or scored during this audit.

## Complete annual IMD reference

The [IMD 0.25° yearly NetCDF page](https://imdpune.gov.in/cmpg/Griddata/Rainfall_25_NetCDF.html) describes a 365/366-record annual product. On 7 October 2026, a complete calendar-year 2026 file cannot yet contain all 365 daily records. The page's descriptive text still says 1901–2024; that text is not a file-level availability receipt. The third sealed header-only request to the official RF25 endpoint returned HTTP 200 with **zero bytes** (`2026_imd_annual_retry_result_v3.json`). HTTP status alone is therefore not evidence of a 2026 NetCDF file, its 03–03 UTC interpretation, or authorized local use.

The 125 official-domain real-time binary grids dated 1 June–3 October are separately hash-receipted in `2026_imd_realtime_acquisition_v1.json`. They are a **provisional daily candidate**, not the annual NetCDF. A consumed 2025 same-day comparison found differences between the daily and annual products (`docs/158`); substitution would change the prespecified truth source. The [IMD site disclaimer](https://imdpune.gov.in/disclaimer.html) and `2026_imd_realtime_access_terms_v1.json` leave redistribution and public product rights unresolved. The raw grids stay local. The annual source-clearance file is absent.

## GEFS production identity and training comparability

[NWS SCN 26-57](https://www.weather.gov/media/notification/pdf_2026/scn26-57_GEFS_Shortwave_radiation_fix.pdf) says GEFS 12.3.20 would begin with the 15 June 2026 12 UTC cycle, subject to a weather-related postponement. The frozen 00 UTC archive would therefore split between 15 and 16 June **if the announced time held**. The three-cycle NOAA GRIB probe in `2026_gefs_radiation_transition_result_v1.json` directly observed a DSWRF packing change between those 00 UTC cycles, consistent with the notice. It does not identify the running GEFS executable, prove that every notice field changed together, or establish numeric equivalence of VarshaSetu's rainfall and atmospheric predictors. The 2023 radiation sample in that probe is also not an exact 2023 patch-version record.

[NWS SCN 26-15](https://www.weather.gov/media/notification/pdf_2026/scn26-15_GEFS_12.3.18.pdf) describes a February 2026 wave-station change. The [NCO model-change history](https://www.nco.ncep.noaa.gov/pmb/changes/) and the [EMC GEFS description](https://www.emc.ncep.noaa.gov/emc/pages/numerical_forecast_systems/gefs.php) establish the broad GEFS v12 family, but the reviewed public pages do not supply a dated, cycle-specific production log for this June transition or the exact patch that generated the 2023 training corpus. The archived 2023 source manifests inspected here likewise provide forecast identity and byte receipts without an executable version field. The GEFS version-clearance file is absent.

An authoritative NCO production record tying the actual executable to affected cycles, a traceable 2023 version record, and a scoped review of selected predictor processing are still required. Similar GRIB parameter identifiers or a change notice limited to radiation cannot establish forecast numerical equivalence. The before/after calendar strata remain descriptive sensitivity strata with unequal seasonal coverage.

## Reproducible audit and gate

`scripts/probe_2026_source_clearance.py --write` created the write-once `data/manifests/research_pilot/2026_source_version_audit_v1.json` (SHA-256 `b36a2740c3e51fd47cb7f39aa88d09af7a912aac66a96aba422f0c963d82f1b6c`) and its receipt. `--check` re-verifies the five input manifests and reproduces the result. It reads only sealed JSON metadata; it never opens IMD grids, GEFS GRIB values, prediction arrays, or models. Its four blockers are:

1. Complete 2026 IMD annual reference not obtained.
2. Actual 2026 GEFS executable transition unconfirmed.
3. Exact 2023 training GEFS patch unconfirmed.
4. 2023-to-2026 selected-predictor comparability unreviewed.

The audit is `OPEN_NO_CLEARANCE`. It does not create either `2026_imd_reference_clearance_v1.json` or `2026_gefs_version_clearance_v1.json`. The frozen annual scorer must continue to stop before observation access, and the daily-source sensitivity remains downstream of the primary annual score. No 2026 skill, calibrated warning, model promotion, or operational equivalence follows from this source audit.

## 7 October bounded follow-up

`2026_source_review_addendum_v1.json` (SHA-256 sidecar) pins a further metadata-only review. The [current NCO model-change history](https://www.nco.ncep.noaa.gov/pmb/changes/) has no 2026 GEFS 12.3.20 row in its reviewed public table and no exact 2023 training patch row. The [15 June NWS notice](https://www.weather.gov/media/notification/pdf_2026/scn26-57_GEFS_Shortwave_radiation_fix.pdf) describes changes to three short-wave radiation GRIB fields. The 22-column project feature manifest instead uses accumulated rainfall, six forecast atmospheric fields, 12 derived summaries, latitude, longitude and lead. None of the selected source fields is named in that notice. This is a **scope observation**, not proof of identical decoded values, unchanged forecast dynamics, or a confirmed executable transition. The previously observed DSWRF packing boundary remains corroborating output metadata only.

The [official IMD annual product description](https://imdpune.gov.in/cmpg/Griddata/Rainfall_25_NetCDF.html) specifies 365/366 daily records per complete calendar year. On 7 October the 2026 calendar year is unfinished; a complete 2026 annual file cannot yet exist. The last sealed endpoint response was zero bytes, and it was not downloaded again. Local use and redistribution remain a separate terms review, while the 125 real-time daily grids stay a provisional sensitivity source. All four source gates remain open. The primary scorer still returns `BLOCKED_BEFORE_OBSERVATION_READ` with 213 forecast cases; the daily sensitivity preflight returns `BLOCKED_BEFORE_VALUE_DECODING`.

## 9 October selected-predictor metadata follow-up

`172_2026_SELECTED_PREDICTOR_SOURCE_METADATA_20261009.md` records a new,
presealed, hash-verified **forecast-only GRIB header** comparison for the
seven selected source fields on one 2023 training cycle and the 15/16 June
2026 00 UTC boundary cycles. No inspected parameter/level/grid/step identity
key differed; some encoding keys did. This advances the processing inventory
but cannot identify the historical executable or show numerical equivalence.
The complete annual 2026 reference is still impossible before year-end; no
known-empty endpoint retry was made. All four gates and the no-score seal
remain unchanged.

## 9 October clearance-contract follow-up

`173_2026_CLEARANCE_READINESS_AUDIT_20261009.md` records a genuine future
preflight weakness: the hash-pinned v1 scorer does not independently check
annual-day completeness, rights, exact per-cycle versions or seven-field
review inside future clearance manifests. A new supplemental read-only audit
now checks those structural claims and NetCDF metadata without accessing
rainfall values. The v1 scorer/protocol remain untouched and blocked. Before
any actual 2026 score, a versioned entrypoint must enforce the stronger audit
and a human reviewer must authenticate the source evidence.

## 9 October versioned scoring gate

`174_2026_VERSIONED_SCORE_GATE_V2_20261009.md` records the sealed v2
entrypoint that enforces the supplemental audit and a hash-bound human source
approval before it can invoke the unchanged v1 scorer. Both v1 and v2
preflights remain blocked. The four source issues above and the independent
test seal are unchanged; no 2026 observation was opened or scored.

## 9 October EMC 2023 version context

`177_GEFS_2023_EMC_VERSION_EVIDENCE_20261009.md` admits a small, hash-verified
official EMC review PDF. Its June 2023 table lists GEFS 12.3.5 in a
"Current (Ops)" column, but gives no executable identity for each 2023 JJAS
training cycle. This narrows historical context without clearing the exact
2023 patch, actual 2026 deployment, predictor comparability or annual IMD
reference gates. The PDF is local-only, no clearance file exists, and the
one-shot score remains blocked before observation read.
