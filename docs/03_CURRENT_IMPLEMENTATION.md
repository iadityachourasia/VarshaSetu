# Current Implementation — As Audited

> Phase 0 update (2026-09-19): the saved report/models are quarantined legacy
> artifacts and are no longer exposed as current results. Training and model
> inference fail closed because the checked-in dataset has unverified provenance,
> no `regime_id`, no forecast init/lead metadata, and a 6-hour target incompatible
> with the retained legacy 24-hour thresholds. The frontend currently renders
> repository scientific-readiness status only. Details are in
> `30_PHASE0_STABILIZATION_REPORT.md`.

## Backend

### Framework

- FastAPI.
- Python scientific/ML stack.
- Models loaded from serialized artifacts.
- Routes expose report metrics and historical prediction functionality.

### Main backend areas

```text
backend/
├── app/api/routes.py
├── app/core/config.py
├── app/data/
│   ├── audit.py
│   ├── loader.py
│   └── splitter.py
├── app/ml/
│   ├── MODELSS.py
│   ├── features.py
│   ├── leakage.py
│   └── models.py
├── app/services/pipeline.py
└── app/verification/metrics.py
```

## Data

Checked-in prototype file:
- `data/GOA_CLEAN.csv`

Observed shape during audit:
- 44,064 rows,
- 26 columns,
- 12 locations,
- North Goa / South Goa,
- 2020–2025,
- 6-hour records at 00/06/12/18.

Important:
- checked-in file does not contain `regime_id`;
- saved report references another source file.

## Current checked-in feature columns

The checked-in CSV includes:
- identifiers/location metadata,
- latitude/longitude/elevation,
- temperature,
- observed 6-hour rainfall target,
- dew point,
- relative humidity,
- MSLP,
- surface pressure,
- cloud cover,
- wind direction/speed,
- boundary-layer height,
- TCWV,
- raw-NWP-prefixed rainfall/temp/pressure/wind fields.

The provenance and forecast-time status of non-target atmospheric columns is unresolved.

## Feature engineering

Current feature engineering creates:
- raw NWP rainfall,
- atmospheric variables,
- NWP atmospheric variables,
- lat/lon/elevation,
- month/day/hour,
- cyclical month/hour features,
- dew-point depression,
- NWP-minus-other-field differences,
- elevation × wind-speed proxy.

## Models

### BaselineNWPModel
Passes raw NWP rainfall through, clipped nonnegative.

### LinearMOSModel
- StandardScaler.
- Ridge regression.
- Transparent baseline.
- Currently extremely important because saved RMSE beats the regime-aware model.

### GlobalMLModel
XGBoost regressor.

### HistGradientBoostingMLModel
Global HGB regressor.

### XGBoost1000Model
1000-tree XGBoost variant.

### RegimeClassifier
- HistGradientBoostingClassifier.
- CalibratedClassifierCV.
- predicts 3 regime classes.

### RegimeAwareMLModel
- uses predicted hard regime,
- selects one of three regime-specific HGB regressors.

### HeavyRainProbabilityModel
- StandardScaler,
- LogisticRegression,
- probability calibration.

### Five-regime heuristic
A separate handwritten softmax scoring method exists but is not the primary ML regime-routing mechanism.

## Current verification

Implemented:
- RMSE,
- MAE,
- bias,
- Pearson correlation,
- R²,
- POD,
- FAR,
- CSI,
- ETS,
- frequency bias,
- Brier score,
- permutation feature importance.

Not implemented:
- FSS.

## Current split

Configured:
- train 2020–2023,
- validation 2024,
- test 2025.

Tests in the audited ZIP were stale and expected a different split.

## Frontend

### Main connected analytical pages

- Operational Forecast.
- Verification & Skill.
- Regime Intelligence.
- Model Comparison / Ablation.
- Feature Importance.
- Calibration.
- Interactive Sandbox.

### Files present but not necessarily normally reachable

Audited repository also contained:
- Data Methodology page.
- Scientific Audit page.
- Jury Defense page.

## What the “Operational Forecast” currently represents

The backend query is a retrospective historical-row lookup.

It is best described as:
- **Historical forecast replay / verification**.

It is not yet a true operational forecast client because there is no:
- NWP cycle ingestion,
- forecast initialization,
- forecast lead dimension,
- live forecast feed.

## Current strongest architectural interpretation

```text
Historical prototype row
    ↓
feature engineering
    ↓
3-class regime classifier
    ↓
hard specialist routing
    ↓
corrected 6h rainfall
    ↓
heavy/VH classifiers
    ↓
saved metrics/API
    ↓
React analytical UI
```

## Current state conclusion

The project is a genuine ML prototype with a useful shell.

It should be evolved, not discarded.
