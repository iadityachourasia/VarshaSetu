# 2026 GEFS announced-version partition — forecast-only audit

Date: 2026-10-07. NOAA/NWS [Service Change Notice 26-57](https://www.weather.gov/media/notification/pdf_2026/scn26-57_GEFS_Shortwave_radiation_fix.pdf) announced GEFS 12.3.20 from the 15 June 2026 **12 UTC** cycle, subject to postponement. The notice names three short-wave radiation fields whose GRIB storage precision changed; none is among VarshaSetu's selected rainfall and atmospheric fields. This is a notice of an intended change, not an independently obtained production deployment log or proof of numerical equivalence to the 2023 training corpus.

The sealed VarshaSetu JJAS corpus uses **00 UTC** initializations. If the announced time held, 1–15 June 00 UTC precede the change and 16 June–30 September 00 UTC follow it. `scripts/summarize_gefs_version_partition.py` reverified the four sealed month records, the year seal and each of 122 local daily manifest hashes; it read no observations or model predictions. Its write-once result is `data/manifests/research_pilot/2026_gefs_announced_partition_v1.json` (SHA-256 `e32f8a713c5d86f2d241d68a1bfa451c5e8673359e668eb3659aee22a1c0a7b0`).

| Announced-time stratum | Cycles | Strict-QC Day 1 / 2 / 3 | Withheld Day 1 / 2 / 3 | Dates with no eligible lead | Passing cases with dynamic feature-range warning |
|---|---:|---:|---:|---:|---:|
| Before, 1–15 June 00 UTC | 15 | 8 / 5 / 8 | 7 / 10 / 7 | 2 | 3 of 21 |
| After, 16 June–30 September 00 UTC | 107 | 56 / 64 / 72 | 51 / 43 / 35 | 6 | 42 of 192 |

The strata have unequal seasons: the second includes July–September, so its feature-warning rate cannot be attributed to the version change. The 15-day first stratum is also too small for a standalone heavy/very-heavy skill claim. These are availability and applicability counts, not verification scores. The source notice does not state that selected forecast values are invariant, and matching GRIB identifiers cannot prove that. The exact 2023 training version and the actual 2026 switchover still lack authoritative versioned production metadata in the repository.

For later 2026 evaluation, retain the already frozen pooled, paired M4-versus-M2 primary comparison and report before/after calendar strata as sensitivity analyses without selecting a model or threshold on 2026 outcomes. Keep the 2026 independent-year gate open until an aligned IMD reference and sufficient version provenance are available. The version boundary must be reported even if the selected fields were not named in the notice.
