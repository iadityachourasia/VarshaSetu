# SIH26080 — Official Problem Statement Baseline

## Metadata

- **PS Number:** SIH26080
- **Title:** Regime-Aware AI Post-Processing of Monsoon Rainfall Forecasts
- **Organization:** Ministry of Earth Sciences (MoES)
- **Department:** National Centre for Medium Range Weather Forecasting (NCMRWF)
- **Category:** Software
- **Theme:** Smart Automation
- **Idea-submission deadline in supplied SIH snapshot:** 30 September 2026
- **Dataset link in supplied SIH snapshot:** N/A

## Supplied official description

Rainfall forecast errors over India vary with weather regimes such as:
- active monsoon,
- break monsoon,
- monsoon lows/depressions,
- orographic rainfall,
- coastal rainfall,
- western disturbances.

The challenge is to create an AI/ML rainfall **post-processing** system that:
1. identifies the prevailing weather regime,
2. applies a suitable correction to the raw NWP rainfall forecast,
3. improves district/grid-level rainfall forecasts,
4. especially improves heavy and very-heavy rainfall forecasting.

## Explicit expected outcomes

The supplied official statement lists:

1. **Weather regime classifier**
   - active,
   - break,
   - depression,
   - coastal/orographic rainfall regimes.

2. **Bias-corrected rainfall forecast**
   - improved rainfall forecast compared with raw NWP output.

3. **Heavy-rainfall probability**
   - probability of exceeding operational rainfall thresholds.

4. **District-level rainfall product**
   - user-friendly rainfall forecast table/map.

5. **Verification report**
   - skill comparison using:
     - RMSE,
     - ETS,
     - CSI,
     - POD,
     - FAR,
     - FSS.

## Mandatory vs inferred

### Mandatory from supplied PS

- AI/ML-based post-processing.
- Raw NWP rainfall as the forecast being corrected.
- Weather-regime identification.
- Regime-aware/suitable correction.
- Improved rainfall forecast relative to raw NWP.
- Grid/district-level output objective.
- Heavy-rainfall probability.
- District-level table/map.
- RMSE.
- ETS.
- CSI.
- POD.
- FAR.
- FSS.

### Strong engineering/scientific implications — not separately stated as formal PS requirements

The following are necessary to make the mandatory outputs meaningful but are labeled as engineering/scientific inference:

- historical paired forecast and observation data,
- spatial alignment between forecast and verification grids,
- explicit accumulation period,
- held-out evaluation,
- forecast-time feature availability,
- handling of rare heavy-rain events,
- regime-wise verification,
- forecast lead-time awareness,
- probability calibration evaluation,
- reproducible preprocessing.

## Important scope interpretation

This is **not** primarily a request to replace NWP with a standalone neural weather model.

The core product is a post-processing/calibration layer:

```text
Raw NWP
   ↓
Weather-regime inference
   ↓
Regime-conditioned correction
   ↓
Corrected rainfall / probabilities
   ↓
District/grid product
   ↓
Verification against observations
```

## Requirements traceability IDs

Use these IDs in tasks, tests, and PRs:

| ID | Requirement |
|---|---|
| PS-R01 | Ingest/use raw NWP rainfall |
| PS-R02 | AI/ML post-processing |
| PS-R03 | Weather-regime classification |
| PS-R04 | Regime-conditioned correction |
| PS-R05 | Demonstrate improvement vs raw NWP |
| PS-R06 | Grid-level rainfall output |
| PS-R07 | Heavy-rain exceedance probability |
| PS-R08 | District-level rainfall table/map |
| PS-R09 | RMSE |
| PS-R10 | ETS |
| PS-R11 | CSI |
| PS-R12 | POD |
| PS-R13 | FAR |
| PS-R14 | FSS |

## Source

Primary supplied source:
- `SIH26080.md`
- source URL recorded there: `https://sih.gov.in/sih2026PS`
- supplied snapshot explicitly reported `Dataset Link: N/A`.

This document must be updated if a later official SIH/NCMRWF clarification or dataset package is received.
