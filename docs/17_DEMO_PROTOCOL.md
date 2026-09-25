# SIH Demo Protocol

## Demo goal

Prove:

> VarshaSetu changes a raw NWP rainfall forecast in a scientifically meaningful way and quantifiably improves forecast skill.

The demo is not primarily a website tour.

## Recommended 6–8 minute structure

### 1. Problem — 30 seconds
- raw NWP errors depend on weather regime,
- one correction may not work for all regimes,
- heavy rain is high impact.

### 2. Forecast metadata — 30 seconds
Show:
- forecast source,
- initialization,
- lead,
- valid date,
- accumulation.

### 3. Raw NWP — 30 seconds
Display raw rainfall grid.

### 4. Regime engine — 45 seconds
Display validated probabilities/state.

Explain:
- regime is inferred from forecast-time atmospheric fields,
- correction specialists respond differently.

### 5. Corrected forecast — 45 seconds
Show corrected map beside raw.

### 6. Observation reveal — 45 seconds
For a held-out historical case:
- show observed map,
- raw error,
- corrected error.

### 7. Heavy-rain probability — 45 seconds
Show:
- correct 24-hour threshold definition,
- probability grid,
- district risk summary,
- calibration status.

### 8. Verification — 90 seconds
Show:
- Raw NWP,
- MOS,
- Global ML,
- Regime-aware,
- Soft MoE if implemented.

Mandatory:
- RMSE,
- ETS,
- CSI,
- POD,
- FAR,
- FSS.

Show event counts.

### 9. Regime ablation — 45 seconds
Answer:
> Does regime awareness itself add skill?

### 10. Limitations & scaling — 30 seconds
Briefly say:
- current data source/domain,
- what changes for NCMRWF deployment.

## Core visual

The most persuasive display is:

```text
RAW NWP | CORRECTED | OBSERVED | ERROR REDUCTION
```

same case, same valid time, same color scale.

## Demo integrity

Never:
- cherry-pick without saying it is a case study,
- imply one event proves aggregate superiority,
- hide a baseline that performs better,
- display fake probability curves,
- call historical observations “live.”

## Offline fallback

Prepare:
- cached model artifacts,
- cached forecast case,
- cached observation,
- cached API fixture,
- local frontend/backend.

The scientific story should work without internet.
