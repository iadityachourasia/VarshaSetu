# Risk Register

| ID | Risk | Severity | Probability | Current status | Mitigation |
|---|---|---:|---:|---|---|
| R01 | Raw NWP fields not authentic forecast data | Critical | Medium/High | July 2019 GEFS reforecast source lineage validated; historical corpus absent | Resolve pilot exception, then reviewed historical manifests |
| R02 | Future-valid-time atmospheric leakage | Critical | Medium/High | July forecast-time atmospheric pilot passed; prototype/model features remain unresolved | Feature registry + source audit before training |
| R03 | Missing `regime_id` methodology | Critical | High | **Resolved for the canonical research track**: forecast-only pseudo-labels reproduce exactly (`docs/54`, `docs/55`); legacy-CSV labels remain unrecoverable | Keep pseudo-label wording; independent validation planned |
| R04 | Scientific training cannot reproduce from clean authoritative inputs | Critical | High | Confirmed; training blocked | Complete authoritative pairing/labels, then clean-run training |
| R05 | Wrong accumulation thresholds | Critical | High | **Resolved for the canonical track**: 24-hour windows and IMD 24-hour categories; the legacy 6-hour CSV stays quarantined | Maintain unit/accumulation metadata |
| R06 | No FSS | Critical | Certain | **Resolved**: true 2-D FSS for all five models on both tracks (`docs/64`, `docs/108`) | Keep multi-scale reporting |
| R07 | No district grid product | High | Certain | **Resolved**: Track A 2019 and Track B 2024/2025 (`docs/65`, `docs/107`, `docs/111`); district verification `docs/113` | Maintain; 2023 and other regions not covered |
| R08 | Extreme-event scarcity | High | High | Verified | Longer history/weighted modeling |
| R09 | Regime model weaker than MOS overall RMSE | High | Medium | **Still true**: regime-aware models do not beat the global model on RMSE, MAE or bias on either track (`docs/61`, `docs/89`); their heavy-rain event gain is track- and regime-specific and not replicated on the 2019 reforecast track (`docs/108`) | Honest ablation; keep claims scoped |
| R10 | Frontend displays generated/static science | High | High | Mitigated: UI numbers come from hash-verified APIs/evidence, copy-guard tests; residual hardcoded numbers listed in the P3 hardening plan | Extend the guard; generate Story Mode numbers from evidence |
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

## Phase 6 risk additions (2026-10-01)

| ID | Risk | Severity | Probability | Current status | Mitigation |
|---|---|---:|---:|---|---|
| R30 | IMD gridded data redistribution rights are unresolved, yet IMD-derived arrays are in a public release bundle | High | Medium | Open (`docs/80`, `docs/102`) | Resolve and record before any further third-party upload (including remote training services) |
| R31 | Validation year reuse: 2024 has served model selection, calibration and diagnostics; no untouched test period remains (2019 and 2025 consumed) | High | High | Open | New independent period or development-only claims; never call 2019/2025 untouched |
| R32 | A regime-aware gain seen on one track is generalised to the other | High | Medium | Mitigated in wording (`docs/108`): the Track B heavy-rain gain does not replicate on Track A | Name the track in every claim (`docs/91` addendum) |
| R33 | Hash-manifested evidence altered by line-ending conversion on checkout | Medium | Medium | Mitigated: `.gitattributes` marks `backend/app/evidence_data/**` as `-text` | Keep evidence files byte-stable; tests verify hashes |
| R34 | Many-district testing produces chance 'improved/worsened' districts | Medium | High | Mitigated: counts shown beside the expected-by-chance number (`docs/112`, `docs/113`) | Keep the denominator and chance caveat with every district claim |

## Phase 7F risk updates (2026-10-01, `docs/120`)

| ID | Risk | Status now | Residual |
|---|---|---|---|
| R35 | CORS open to every origin with credentials | Mitigated: named origins, no credentials, read-only methods | A directly hosted frontend on a new domain needs `CORS_ALLOW_ORIGINS` |
| R36 | Unverified or truncated data bundle shipped in the image | Mitigated: pinned SHA-256 (equal to GitHub's published digest) checked before extraction, with retry and resume | The checksum must be updated together with any new bundle |
| R37 | Static hand-written audit statements served as if executed | Mitigated: `/api/audit` and `/api/jury-defense` return 410 | None known |
| R38 | No automated checks on push | Mitigated: CI for backend, frontend and Dockerfile | Playwright and the Phase 4 freeze tests remain local |
| R39 | Hand-typed science numbers in Story Mode | Mitigated: figures derived from verified sources and tested | Other pages were checked by the copy guard, not exhaustively audited |

