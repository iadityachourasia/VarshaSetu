# UI Scientific Data Contract

## Primary rule

> The frontend renders scientific values; it does not invent them.

The Regime Intelligence entry displays a development notice for the 2019
reforecast context or when the operational catalogue is unavailable. Verified
operational-era data remains available when present; an artifact integrity
failure remains an explicit error rather than a development notice.

Ensemble & Uncertainty currently has a matched 2025 operational-era subset.
The shared navigation targets that experiment directly, and unsupported
Ensemble URLs redirect there instead of showing a misleading 2019 empty state.

Any scientific number must map to a documented backend field or a transparent arithmetic transformation of backend fields defined in this file.

## Current issues to remove

The audited frontend contained examples of:
- multiplied synthetic rainfall trajectory values,
- static exceedance probabilities,
- static dataset mean cards,
- static accuracy/improvement text,
- controls not connected to backend computation,
- filters not connected to analysis,
- a “calibrated” label stronger than the evidence.

## Required mapping

| UI element | Source |
|---|---|
| Raw rainfall | backend forecast field |
| Corrected rainfall | backend prediction field |
| Observation | backend historical reference field only |
| Correction magnitude | corrected − raw |
| Regime probability | regime API |
| Heavy probability | calibrated threshold API |
| Very-heavy probability | calibrated threshold API |
| RMSE | verification report |
| ETS/CSI/POD/FAR | verification report |
| FSS | verification report |
| Model improvement | calculated in backend/report |
| District statistics | district aggregation API |
| Data source | forecast-run metadata |
| Lead | forecast-run metadata |

## Map layout

Judge-facing core map:
- Raw NWP.
- Corrected forecast.
- Observation.
- Error reduction.

Use synchronized extent/color scale where scientifically appropriate.

## Historical replay labels

When observation is available:
- explicitly show `Historical Replay`.
- include `Valid Time`.
- include `Lead`.
- include `Observation Source`.

Do not label it “live forecast.”

## Operational mode

Observation panel should be hidden or marked unavailable until after verification data arrive.

## Probability display

Display:
- event definition,
- accumulation period,
- probability,
- calibration status.

Example:

```text
Heavy Rain ≥64.5 mm / 24h
Probability: 42%
Calibration: validated on 2024 validation period
```

If calibration is not validated:
```text
Prototype probability — calibration under evaluation
```

## Insufficient-event state

For zero/too-few positive cases:

```text
Insufficient held-out events for reliable calibration assessment.
```

Never show:
```text
Brier 0.0000 — Excellent
```

without event context.

## Dashboard hierarchy

### First screen
Answer:
1. What did raw NWP predict?
2. What did VarshaSetu change?
3. Why?
4. Was it better?

### Verification screen
Answer:
1. Does it improve aggregate held-out skill?
2. Does it improve heavy-rain events?
3. At what spatial scale?
4. Does regime awareness add value?

## Allowed client-side computations

Safe:
- display formatting,
- percentage formatting,
- simple difference if both source values supplied,
- chart transformations that preserve values.

Not safe:
- generating new scientific probability values,
- multiplying one forecast into a time series,
- manufacturing confidence intervals,
- changing metric definitions.

## Scientific placeholder design

If backend not ready, use:

```text
Not yet implemented
```

or a visibly labeled design placeholder.

Never use realistic fake numbers in production/demo mode.
