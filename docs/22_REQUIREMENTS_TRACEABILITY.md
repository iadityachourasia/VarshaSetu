# Requirements Traceability Matrix

<!-- GENERATED:PS-COVERAGE:START -->
## Current status (generated from `backend/app/evidence_data/phase6/ps_coverage.json`)

Status of each official requirement = IMPLEMENTED if every mandatory coverage row for it is IMPLEMENTED, PLANNED if every one is PLANNED, otherwise PARTIAL.
Live view with evidence-resolved figures: the app's `/compliance` page. Do not edit this block by hand; run `python scripts/build_ps_traceability_doc.py`.

| PS ID | Official requirement | Status | Coverage rows (mandatory) |
|---|---|---|---|
| PS-R01 | Ingest / use raw NWP rainfall | IMPLEMENTED | RAW-NWP |
| PS-R02 | AI/ML post-processing | IMPLEMENTED | ML-POSTPROCESSING |
| PS-R03 | Weather-regime classification | PARTIAL | REGIME-CLASSIFIER, REGIME-ACTIVE, REGIME-BREAK, REGIME-LOW, REGIME-COASTAL-OROGRAPHIC, REGIME-WESTERN-DISTURBANCE |
| PS-R04 | Regime-conditioned correction | IMPLEMENTED | REGIME-AWARE-CORRECTION |
| PS-R05 | Demonstrate improvement vs raw NWP | PARTIAL | BIAS-CORRECTED-RAINFALL, IMPROVEMENT-VS-RAW |
| PS-R06 | Grid-level rainfall output | IMPLEMENTED | BIAS-CORRECTED-RAINFALL, GRID-PRODUCT |
| PS-R07 | Heavy-rain exceedance probability | IMPLEMENTED | HEAVY-PROBABILITY, VERY-HEAVY-PROBABILITY |
| PS-R08 | District-level rainfall table/map | IMPLEMENTED | DISTRICT-PRODUCT, DISTRICT-MAP, DISTRICT-TABLE |
| PS-R09 | RMSE | IMPLEMENTED | METRIC-RMSE, VERIFICATION-REPORT |
| PS-R10 | ETS | IMPLEMENTED | METRIC-ETS, VERIFICATION-REPORT |
| PS-R11 | CSI | IMPLEMENTED | METRIC-CSI, VERIFICATION-REPORT |
| PS-R12 | POD | IMPLEMENTED | METRIC-POD, VERIFICATION-REPORT |
| PS-R13 | FAR | IMPLEMENTED | METRIC-FAR, VERIFICATION-REPORT |
| PS-R14 | FSS | IMPLEMENTED | METRIC-FSS, VERIFICATION-REPORT |

Additional (non-mandatory) rows:

| Row | Requirement | Status |
|---|---|---|
| REGIME-INDEPENDENT-VALIDATION | Independent (expert / bulletin) validation of regime labels | PLANNED |
| REGIME-WISE-VERIFICATION | Regime-wise and lead-wise verification | IMPLEMENTED |
| DISTRICT-VERIFICATION | District-level verification | PARTIAL |
| LIVE-INFERENCE | Live / new-cycle forecast post-processing | PLANNED |
| SYNOPTIC-OVERLAYS | Synoptic meteorology overlays (wind vectors, geopotential contours, pressure isobars) | IMPLEMENTED |
| ALL-INDIA-DOMAIN | All-India domain | PLANNED |

<!-- GENERATED:PS-COVERAGE:END -->

## Historical audit (Phase 0-1, superseded by the table above)

The table and evidence list below record the state at the Phase 0-1 audit (September 2026) and are kept for provenance only.

| PS ID | Official requirement | Current audited state | Target evidence | Priority |
|---|---|---|---|---|
| PS-R01 | Raw NWP rainfall | July 2019 official GEFSv12 pilot: 464/465 member/product cases valid; corpus absent | resolve one failed interval, then reviewed corpus acquisition | P0/P1 |
| PS-R02 | AI/ML post-processing | Implemented | model artifact + held-out report | Done/strengthen |
| PS-R03 | Regime classifier | 3-class classifier implemented; labels unreproducible | regime methodology + validation | P0/P2 |
| PS-R04 | Regime-conditioned correction | hard expert routing implemented | hard + soft MoE comparison | P2/P3 |
| PS-R05 | Improvement vs raw | overall RMSE improvement saved; regime model not best MOS | frozen report | P2 |
| PS-R06 | Grid-level forecast | 464 raw-NWP/IMD 0.25° FSS-ready monthly cases exist; no corrected corpus/product | corrected grid artifact/map | P1 |
| PS-R07 | Heavy probability | exact 03–03 UTC 24h contract designed; no eligible data/model | 24h calibrated probability | P1/P2 |
| PS-R08 | District product | authoritative boundary/weight/output contract designed; not implemented | polygon aggregation + API/UI | P1 |
| PS-R09 | RMSE | implemented | unit test + report | Maintain |
| PS-R10 | ETS | implemented | unit test + report | Maintain |
| PS-R11 | CSI | implemented | unit test + report | Maintain |
| PS-R12 | POD | implemented | unit test + report | Maintain |
| PS-R13 | FAR | implemented | unit test + report | Maintain |
| PS-R14 | FSS | 2-D array/mask contract designed; metric still missing | FSS module + spatial report | P1 |

## Phase 1A data-foundation evidence

| Evidence | Repository location | Status |
|---|---|---|
| source comparison and primary/fallback decision | `docs/31_AUTHORITATIVE_DATA_ARCHITECTURE.md` | Complete as design |
| forecast metadata contract | `docs/32_FORECAST_DATA_CONTRACT.md`; `ForecastGridRecord` | Implemented/tested |
| observation metadata contract | `docs/33_OBSERVATION_DATA_CONTRACT.md`; `ObservationGridRecord` | Implemented/tested |
| regime label strategy | `docs/34_REGIME_LABEL_STRATEGY.md` | Design only; no labels |
| staged acquisition plan | `docs/35_DATA_ACQUISITION_PLAN.md` | Complete; bulk acquisition not started |
| architecture decision manifest | `data/manifests/authoritative_data_architecture.v1.json` | Training-ineligible |
| official NOAA Phase 1A access probe | architecture manifest | One `0-3` field decoded/subset; not retained for science |
| one-window official NOAA/IMD pair | `docs/36_ONE_WINDOW_PILOT_REPORT.md`; `data/manifests/phase1b/2019-07-15/` | PASS for engineering QC; training-ineligible |
| one-month official NOAA/IMD pilot | `docs/38_ONE_MONTH_ACQUISITION_PILOT.md`; `data/manifests/phase1c/2019-07/` | PARTIAL: 464/465 rainfall, 558/558 predictors; training-ineligible |

These entries improve traceability but do not satisfy the Phase 0 release gate.

## Recommended non-mandatory traceability

| ID | Enhancement | Reason |
|---|---|---|
| ENH-01 | MOS baseline | scientific control |
| ENH-02 | probability reliability | makes heavy probabilities credible |
| ENH-03 | Brier Skill Score | compare against reference probability |
| ENH-04 | Soft MoE | strongest code-compatible USP |
| ENH-05 | physics-guided features | meteorological credibility |
| ENH-06 | lead-time analysis | medium-range realism |
| ENH-07 | explainable correction | forecaster trust |
| ENH-08 | failure-case browser | scientific maturity |
# Phase 1D traceability update (2026-09-19)

Corpus admission and fairness rules are implemented in
`backend/app/data/corpus_policy.py` and tested by
`backend/tests/test_corpus_policy.py`. The frozen, non-acquired production plan
is validated by `backend/app/data/corpus_models.py` against
`data/manifests/corpus/varshasetu-gefs12r-imd025-jjas-2000-2019-v1.plan.json`.
Anomaly, policy, acquisition, version, and storage evidence is documented in
`docs/42_GEFS_ACCUMULATION_ANOMALY_REPORT.md` through
`docs/46_PRODUCTION_STORAGE_AND_CHUNKING.md`. Scientific endpoints remain
blocked and these artifacts do not satisfy later ML/verification requirements.
