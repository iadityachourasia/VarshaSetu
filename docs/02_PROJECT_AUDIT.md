# Current Project Audit — Evidence-Based

## Audit scope

The uploaded ZIP contained approximately 60 files including:
- Python backend,
- React/TypeScript frontend,
- checked-in CSV,
- serialized model artifacts,
- tests,
- saved evaluation reports.

The audit verified code paths instead of trusting UI labels or README claims.

## Executive assessment

### What is genuinely present

The project is not merely a UI mock. It contains:
- real scikit-learn models,
- XGBoost models,
- serialized model artifacts,
- a 3-class regime classifier,
- three regime-specialist rainfall regressors,
- hard regime routing,
- heavy/very-heavy binary probability classifiers,
- chronological train/validation/test configuration,
- continuous and categorical verification metrics,
- FastAPI endpoints,
- React analytical pages consuming backend data,
- saved evaluation reports.

### Why it is not yet scientifically ready

The following are blockers:

1. training data path is machine-specific;
2. checked-in CSV differs from the dataset used by the saved report;
3. checked-in CSV lacks `regime_id`;
4. current experiment cannot be reproduced from a clean clone;
5. predictor provenance is insufficient to establish forecast-time causality;
6. raw NWP provenance is not documented;
7. 24-hour heavy-rain thresholds are applied to a 6-hour target in the audited version;
8. heavy-rain events are extremely rare;
9. FSS is not implemented;
10. no 2-D gridded forecast/observation pipeline exists;
11. no genuine district polygon product exists;
12. several frontend scientific values are hardcoded or constructed.

## Repository evidence

### Machine-specific data path

Audited file:

`backend/app/core/config.py`

contained a source path equivalent to:

```text
C:\Users\...\Downloads\GOA_DATA (1).csv
```

The ZIP instead contained:

`data/GOA_CLEAN.csv`

### Data mismatch

Checked-in `GOA_CLEAN.csv`:
- 44,064 rows,
- 26 columns,
- no `regime_id`.

Saved report source metadata:
- filename `GOA_DATA (1).csv`,
- includes `regime_id`,
- includes generated `datetime`,
- different SHA-256 from checked-in file.

Therefore the saved experiment cannot be regenerated solely from the supplied checked-in CSV.

### Stale tests

Observed test assumptions included:
- Train: 2020–2022
- Validation: 2023
- Test: 2024
- Unseen: 2025

Current configuration contained:
- Train: 2020–2023
- Validation: 2024
- Test: 2025
- Unseen: none.

This makes the test suite an unreliable gate until synchronized.

### Dependency mismatch

Model code imports XGBoost.
The audited backend requirements did not list XGBoost.

## Model reality

### Real components

- Raw NWP baseline.
- Ridge/Linear MOS.
- Global XGBoost.
- HistGradientBoosting regression.
- Calibrated 3-class regime classifier.
- Per-regime HistGradientBoosting regressors.
- Logistic probability models for heavy and very-heavy categories.

### Current regime-aware mechanism

The current primary regime-aware implementation is **hard routing**:

```text
classifier predicts one regime
        ↓
select exactly one specialist model
        ↓
rainfall prediction
```

It is not a soft Mixture-of-Experts.

### Five-regime “physics” logic

The code also contains a five-category handwritten scoring mechanism for:
- Active Monsoon,
- Break Monsoon,
- Monsoon Low/Depression,
- Coastal/Orographic,
- Transitional/Western Disturbance.

This scoring system is:
- manually weighted,
- not demonstrated to be trained,
- not demonstrated to be reliability-calibrated,
- not the main correction routing engine.

Treat it as a diagnostic heuristic unless validation is added.

## Saved performance finding

The saved report showed:
- Raw NWP RMSE ≈ 2.1377
- Linear MOS RMSE ≈ 1.3482
- Regime-aware ML RMSE ≈ 1.3876

Therefore:
- regime-aware ML improved strongly over raw NWP,
- but did **not** beat the simple MOS baseline in overall RMSE.

This means the current evidence does **not** establish that regime awareness is the best post-processing strategy.

## Heavy-rain findings

The historical event count is extremely small at the current 6-hour thresholds.

In the saved 2025 test context:
- only one heavy event was present,
- zero very-heavy events were present.

The saved heavy-event threshold comparison indicated:
- raw NWP: one hit, zero false alarms;
- regime-aware model: one hit, one false alarm.

This is far too small a sample for stable inference and does not prove improvement in heavy-rain skill.

## Threshold accumulation mismatch

Current target:
- 6-hour rainfall accumulation.

Current “heavy” category:
- 64.5 mm.

Current “very heavy”:
- 115.5 mm.

These category boundaries are commonly used by IMD for 24-hour cumulative rainfall products. The project must not apply them to a 6-hour record and describe the result as an equivalent operational 24-hour category.

## Forecast-time leakage risk

Current feature engineering uses both:
- `raw_nwp_*` fields,
- fields such as `temperature_2m`, humidity, pressure, wind, TCWV.

The repository does not establish whether these non-NWP dynamic fields are:
- forecasts available at issue time, or
- observations/reanalysis at valid time.

Derived features include differences between NWP and non-NWP values.

If the latter are valid-time observations/reanalysis, this creates severe operational leakage.

The existing leakage checker only catches suspicious **names**; it cannot verify information timing.

## Spatial/PS gaps

Missing:
- 2-D forecast grid processing,
- observation grid alignment,
- FSS,
- district polygons,
- grid-to-district aggregation,
- spatial error maps,
- live/archived forecast cycle and lead.

## Frontend issues found

Examples of scientific UI constructs that were not genuine backend outputs in the audited version:

- a rainfall trajectory built by multiplying one forecast value,
- static exceedance probabilities for multiple arbitrary thresholds,
- hardcoded mean rainfall/meteorology cards,
- hardcoded reported improvement/accuracy values,
- analysis controls that changed UI state but not scientific calculations,
- filters that did not filter backend analytics,
- simulated authentication,
- hardcoded notifications,
- a hardcoded “scientific audit” list rather than executable checks.

## Strong reusable assets

Preserve:
- FastAPI/React separation,
- baseline ladder concept,
- chronological partition design,
- verification module structure,
- regime classifier abstraction,
- specialist model abstraction,
- oracle-regime diagnostic,
- feature-importance view,
- model-comparison page,
- historical replay/sandbox concept.

## Audit status vocabulary

Use:
- ✅ Fully implemented and verified.
- 🟡 Partially implemented.
- 🟠 Prototype/mock/demo-only.
- ⚠️ Implemented but scientifically/technically weak.
- 🔴 Missing.
- ❌ Broken/non-functional.
- ❓ Cannot be verified.

Never upgrade a status without tests/evidence.
