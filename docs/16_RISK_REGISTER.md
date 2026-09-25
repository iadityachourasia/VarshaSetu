# Risk Register

| ID | Risk | Severity | Probability | Current status | Mitigation |
|---|---|---:|---:|---|---|
| R01 | Raw NWP fields not authentic forecast data | Critical | Medium/High | July 2019 GEFS reforecast source lineage validated; historical corpus absent | Resolve pilot exception, then reviewed historical manifests |
| R02 | Future-valid-time atmospheric leakage | Critical | Medium/High | July forecast-time atmospheric pilot passed; prototype/model features remain unresolved | Feature registry + source audit before training |
| R03 | Missing `regime_id` methodology | Critical | High | Unresolved | Reproducible label pipeline |
| R04 | Scientific training cannot reproduce from clean authoritative inputs | Critical | High | Confirmed; training blocked | Complete authoritative pairing/labels, then clean-run training |
| R05 | Wrong accumulation thresholds | Critical | High | Verified in audited version | Build correct 24h product |
| R06 | No FSS | Critical | Certain | Verified | Gridded data + implementation |
| R07 | No district grid product | High | Certain | Verified | Geo aggregation |
| R08 | Extreme-event scarcity | High | High | Verified | Longer history/weighted modeling |
| R09 | Regime model weaker than MOS overall RMSE | High | Medium | Verified saved result | Improve labels/gating; honest ablation |
| R10 | Frontend displays generated/static science | High | High | Verified | UI contract |
| R11 | Dataset provenance challenged by judges | Critical | High | July source→daily→monthly hashes exist; training corpus lineage unresolved | Preserve hierarchy through reviewed corpus acquisition |
| R12 | Complex model overfits | High | Medium | Ongoing | Keep strong baselines |
| R13 | Grid misalignment creates fake skill changes | Critical | Medium | 464 rainfall mappings and 558 context fields passed; multi-year variation untested | Preserve monthly alignment/conservation gates |
| R14 | Event thresholds mismatched after resampling | High | Medium | Future risk | Unit/accumulation metadata |
| R15 | FSS misinterpreted as universal skill | Medium | Medium | Future risk | multi-scale reporting |
| R16 | Calibration claim based on few/zero events | High | High | Verified current issue | reliability + sample warnings |
| R17 | Demo depends on internet/upstream NWP | Medium | Medium | Future | cached replay |
| R18 | NWP model version change causes drift | Medium | Medium | Future | model/version metadata |
| R19 | District mean hides local extreme | Medium | High | Future | max/p90/area fraction |
| R20 | Overengineering delays mandatory work | High | High | Management risk | roadmap gates |
| R21 | IMD access, terms, file version, or missing-value metadata blocks ingestion | Critical | Medium | 2019 official file acquired; no version attribute; broader access untested | Preserve file hashes/native metadata; test repeated official acquisition |
| R22 | GEFS byte-range messages remain global and exceed laptop budget | High | Medium | July transfer measured at 1.568 GB; 20-JJAS inclusive projection 128.3 GB | Reviewed chunk/concurrency plan; reserve processing headroom |
| R23 | Mixed GEFS 3/6-hour step ranges are accumulated incorrectly | Critical | Medium | 464/465 passed; one −0.2-mm `p01` nested difference fails tolerance | Resolve archive inconsistency and freeze exclusion/admission policy before scale |
| R24 | 03 UTC IMD day is joined to a midnight/lead-24 forecast window | Critical | Medium | One interval matched using official external convention; NetCDF lacks bounds | Persist explicit +3..+27 windows and timing basis for every pair |
| R25 | Regridding changes rainfall mass or masks ocean/missing cells incorrectly | Critical | Medium | One co-located conservative mapping and mask passed | Repeat nontrivial grids/dates; retain weights, bounds, conservation and masks |
| R26 | District boundaries are unofficial, stale, or topologically invalid | High | Medium | Source selected; file unresolved | Survey of India version/hash/terms + topology QC |
| R27 | Regime context is too narrow or labels become target-derived | Critical | Medium | Two-domain and label design only | Context-domain sensitivity, component labels, leakage tests, expert review |
| R28 | Archive object-family documentation is too coarse for exact levels | High | Medium | Q700 is in `spfh_pres_abv700mb`, not documented `spfh_pres`; contract corrected | Validate decoded metadata for every variable/version |
| R29 | Retry history is mistaken for permanent source missingness | Medium | Medium | July 31 Q700 transient failure recovered independently | Preserve initial/resume logs and distinguish retry success from archive gaps |

## Highest-priority mitigation sequence

```text
R04 → R01/R02/R03 → R05 → R06/R07 → R08/R09 → R10
```

## Judge-question risk

Prepare evidence for:
- Where exactly did raw NWP come from?
- What data are available at forecast issue time?
- How are regimes labeled?
- Why does regime awareness beat/not beat MOS?
- Where is FSS?
- How many heavy-rain events are in the test set?
- What accumulation period defines heavy rainfall?
# Phase 1D risk update (2026-09-19)

The July 22 p01 Day-2 anomaly is classified `SOURCE_INCONSISTENCY`, not packing
quantization: its 0.2 mm decrement exceeds the 0.15 mm bound derived from the
actual GRIB scale factors. Risk is controlled by component-scoped fail-closed
quarantine and explicit eligibility tiers. Residual risk remains that additional
archive inconsistencies may occur during historical acquisition; monthly QC and
small reviewed batches are mandatory. The corpus plan is not acquired and no
training is authorized.
