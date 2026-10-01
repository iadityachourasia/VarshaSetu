# Phase 8B: western-disturbance feasibility study (investigation only)

Date: 2026-10-01. **No classifier, label, model or new download was produced.** This document establishes what is possible with the data and domains the project has, what is
missing, and what would have to be decided and approved before any western-disturbance (WD) work could start. The coverage row stays **PLANNED**.

## 1. The requirement

The problem statement lists western disturbances among the regimes that drive forecast-error differences (`docs/01`). The project classifies three forecast-only pseudo-regimes
(active, break/weak, low/depression); a WD class does not exist (PS-R03 is PARTIAL partly for this reason).

## 2. What a western disturbance is, and when it matters

IMD describes a WD as a cyclonic circulation or trough in the mid and lower troposphere (or a surface low) in the middle-latitude westerlies that originates over the Mediterranean,
Caspian or Black Sea region and moves eastward across north India. WDs are upper-level synoptic systems embedded in the subtropical westerly jet. They are most frequent from
December to March, when they bring most of the precipitation to the western Himalaya and surrounding north India and Pakistan, and they can interact with the summer monsoon,
sometimes with severe consequences; recent studies report that the WD season has extended into late spring and early summer.
(Sources, read as search summaries and not yet checked in full: [Hunt, Turner and Shaffrey 2018, QJRMS](https://reading-9.eprints-hosting.org/73137/7/qj3200.pdf),
[Weather and Climate Dynamics 2025](https://wcd.copernicus.org/articles/6/43/2025/), [2024](https://wcd.copernicus.org/articles/5/345/2024/). Verify the exact figures at the source before
quoting any of them.)

## 3. Where the project's domains sit relative to that

| Domain | Extent | Evidence |
|---|---|---|
| Rainfall verification (all models, all metrics) | 10–22° N, 68–80° E, 0.25° | `docs/37`, `docs/116` |
| Atmospheric context (served, charted) | 5–30° N, 55–95° E, 0.5° | `docs/121` |
| IMD observed rainfall product | 6.5–38.5° N, 66.5–100° E, 0.25° | Phase 1B manifest `imd_rf25_2019.json` (2019 file; other years are the same product and should be confirmed) |
| Region where WDs act (north India, Pakistan, western Himalaya) | mainly north of about 25° N | general meteorology, sources above |

The rainfall verification domain stops at 22° N, so western-disturbance rainfall (north-west India, the Himalaya) is **outside it by construction**, and the 30° N edge of the
atmospheric context clips the southern flank of WD troughs only. A WD regime therefore cannot be verified, or even meaningfully observed, inside the current evaluation domain.

## 4. Data inventory (checked on this machine)

| Need | Available? | Detail |
|---|---|---|
| Wider-domain forecast fields | **Yes, for the operational-era track, without a new download** | The per-message GRIB files held locally for 2023–2025 (header checked on one date per year) are global 0.5° fields (720 by 361, 90° N to 90° S) at lead hours 24, 48 and 72 for 850-hPa U and V, 500-hPa height, precipitable water, sea-level pressure and 700-hPa humidity; rainfall is global 0.25° |
| The same for the 2017–2019 reforecast track | No | Only the cropped 5–30° N, 55–95° E context files are held; global fields were never kept |
| Upper-tropospheric fields (about 200–300 hPa winds, vorticity, potential vorticity, temperature) | **No** | The objective WD trackers in the literature use upper-tropospheric vorticity; none of the fields acquired are at those levels, so a new range-request download from the NOAA GEFS archive would be needed (the existing project tooling can do it; the size has not been measured and an estimate would be speculative) |
| Observed rainfall north of 22° N | **Yes** | The IMD product already acquired covers to 38.5° N; no new observation download is implied |
| A WD label or catalogue for 2017–2019 and 2023–2025 | **No** | See section 5 |

Consequences: any first WD study would be **operational-era only** (2023–2025, with 2023 the only training year), and 500-hPa height (trough detection) is the only
upper-air signal already on disk.

## 5. Label sources (the decisive gap)

| Option | What it gives | Problems |
|---|---|---|
| A. Objective tracking catalogue from reanalysis (Hunt et al. 2018, about 3,000 events over 37 years of ERA-Interim, published by CEDA) | Reproducible, published, physically defined events | Covers 1979–2015 only, so none of the project's years. Using it as a method means re-running tracking on a newer reanalysis (ERA5 for 2017–2025), which is a new data acquisition under a Copernicus licence and a new implementation; the result is still a reanalysis-derived label, usable for evaluation only |
| B. IMD daily weather reports and bulletins that name active WDs | An operational, meteorological source | Text, not a machine-readable catalogue; licence and access unverified; labelling 100–200 days would be manual |
| C. A forecast-only trough heuristic on 500-hPa height | Fully reproducible, no new data | A project convention (pseudo-label), exactly like the existing regimes; it would say nothing about real WDs unless validated against A or B |

## 6. Will there be enough events?

Unknown, and this is the main risk. The whole corpus is June to September; WDs peak in winter. Strong WD-monsoon interaction events exist but are episodic. The existing regime work
already shows how a class with little support starves its specialist (the Break/Weak experts forecast almost no heavy rain). The project's support gate (at least 30 cases and 30
observed event pairs per stratum) cannot be pre-judged without labels. **A counting step with a label source must come before any protocol.**

## 7. Conclusion

- **Feasible in principle**, for the operational-era track, without new downloads for the wider-domain fields and without new observations.
- **Not feasible today as a trained regime**: no label source, no upper-tropospheric fields, the evaluation domain excludes the region where WDs act, and the monsoon-season sample is
  small and unquantified.
- **Honest status stays PLANNED.** It must not be shown as implemented or as partial.

## 8. A staged path that does not build a classifier first

| Stage | Work | Needs approval for |
|---|---|---|
| W0 | Decide label source (A, B or C), season scope and whether the evaluation domain may extend north | the choices; any download |
| W1 | Build labels only (no model), with their provenance, and count events per year | any ERA5 or upper-air download |
| W2 | Count support against the existing gate and decide whether any WD analysis can be statistically supported | stop here if the gate fails |
| W3 | If supported: WD-stratified verification of the frozen models (as for the coastal and orographic zones, `docs/117`), not a new model | a frozen protocol first |
| W4 | A WD-aware correction only after W3 shows a deficiency, under its own protocol | the separate Stage-3-style approval |

## 9. Decisions needed from the project owner

1. Label source: A (re-run tracking on ERA5), B (IMD bulletins, manual), or C (forecast-only heuristic, a pseudo-label), or none.
2. May the evaluation domain be extended north of 22° N for this purpose (new district weights and verification populations are implied)?
3. May upper-air fields or ERA5 be downloaded (explicit file, source, size and licence will be stated before any download)?
4. Is monsoon-season-only (June to September) acceptable, given that WDs peak in winter?

Gate: `P2_2_WD_FEASIBILITY_DOCUMENTED_AWAITING_OWNER_DECISIONS`.
