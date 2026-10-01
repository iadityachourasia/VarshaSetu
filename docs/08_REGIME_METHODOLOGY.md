# Weather-Regime Methodology

> Status update (Phase 6, 2026-10-01): the "Current implementation" section below describes the quarantined legacy prototype. The canonical regime method is the forecast-only pseudo-label design in `docs/54`/`docs/55` (three classes, deterministic labels, logistic classifier, reproduces exactly), used by M3/M4 and shown in the Regime Intelligence page. The hierarchical, multi-label design described here (synoptic, geographic-forcing, western-disturbance heads) is the planned successor, not yet implemented: coastal/orographic and western-disturbance regimes are PLANNED (`docs/22`, `/compliance`).

## Objective

The regime engine exists to answer:

> Under what meteorological state is this NWP forecast being made, and should the post-processing relationship change under that state?

It is not merely a classification visualization.

## Current implementation

### Main operational prototype

Current trained classifier:
- 3 mutually exclusive classes,
- HistGradientBoostingClassifier,
- probability calibration wrapper,
- used for hard specialist routing.

Current labels:
- 0 — Active Monsoon / Coastal Orographic Regime
- 1 — Break / Weak Monsoon Regime
- 2 — Monsoon Depression / Low Pressure System

### Critical limitation

The audited repository does not contain the `regime_id` generation methodology.

Therefore:
- classifier accuracy cannot be scientifically interpreted,
- label leakage cannot be ruled out,
- label reproducibility is currently missing.

### Secondary five-regime heuristic

Handwritten scoring exists for:
- Active Monsoon,
- Break Monsoon,
- Monsoon Low/Depression,
- Coastal/Orographic,
- Transitional/Western Disturbance.

Treat it as **heuristic diagnostic logic** unless validated against an external/reference regime dataset.

## Scientific representation issue

The PS names concepts that are not strictly mutually exclusive.

Example:
- active monsoon can coexist with a monsoon low,
- coastal/orographic forcing can coexist with active monsoon.

Therefore the preferred long-term representation is hierarchical or multi-label.

## Target regime architecture

### Head A — Monsoon state
- active,
- break,
- neutral/transition.

### Head B — Synoptic driver
- monsoon low/depression,
- western disturbance where spatial domain supports it,
- other.

### Head C — Geographic forcing
- orographic influence,
- coastal influence.

These may feed a soft gating network.

## Regime labels — acceptable methods

Potential scientifically defensible strategies:

### Method 1 — Official/research pattern mapping
Map NCMRWF/IMD-defined pattern categories to project regime families where accessible and licensable.

### Method 2 — Rule-derived labels from reanalysis
Use documented thresholds/pattern logic from atmospheric fields.

Requirements:
- rules must be cited,
- labels generated reproducibly,
- label variables kept separate from forecast inference variables where necessary,
- sensitivity analysis performed.

### Method 3 — Unsupervised circulation clustering
Cluster standardized large-scale circulation fields, then meteorologically interpret clusters.

Requirements:
- stable cluster validation,
- mapping to PS regime families documented,
- avoid labeling clusters solely from outcome rainfall.

## Recommended forecast-time predictors

Regime inference should favor large-scale NWP atmospheric predictors such as:
- 850-hPa U/V wind,
- MSLP,
- 700-hPa humidity/moisture,
- 500-hPa geopotential,
- vorticity/circulation proxies,
- TCWV,
- neighbourhood pressure/wind patterns.

A single local station row is insufficient for robust synoptic classification in the long-term architecture.

## Western Disturbance handling

Do not force a Western Disturbance classifier from Goa-local point variables alone.

Western disturbances are synoptic systems and require a wider spatial atmospheric context.

For an MVP centered on Goa:
- prioritize active/break/low/orographic/coastal correctness,
- treat WD support as requiring expanded domain.

## Probability output

Regime probabilities must be the output of a calibrated/validated classifier if displayed as probabilities.

Do not:
- take arbitrary scores,
- apply softmax,
- label them “calibrated.”

## Evaluation

At minimum report:
- class distribution,
- confusion matrix,
- per-class precision/recall/F1,
- balanced accuracy,
- calibration if probabilities are used,
- performance by forecast lead.

Most important:
- prove whether regime conditioning improves rainfall post-processing.

## Core ablation

Required experiment:

```text
Raw NWP
    ↓
Global postprocessor without regime
    vs
Regime-conditioned postprocessor
```

If the regime-aware model does not outperform the non-regime model, do not hide it. Diagnose:
- label quality,
- gating,
- sample size,
- feature design,
- expert overfitting.

## Target MoE gating

Preferred:

\[
\hat{y} = \sum_{r=1}^{R} p(r|X_{forecast}) f_r(X)
\]

rather than:

\[
\hat{y} = f_{\arg\max p(r)}(X)
\]

Soft gating handles regime uncertainty and transitions more gracefully.

## Phase 2A implemented successor

The `regime_id`-methodology limitation above remains true for the legacy
checked-in CSV and saved models, but no longer describes the separate Phase 2A
prototype artifacts. The implemented successor is documented in
`54_PROTOTYPE_REGIME_METHODOLOGY.md` and uses only c00 forecast-time U850, V850,
Q700, Z500, MSLP, and PWAT on the broad context grid. It deterministically fits
normalization and pseudo-label thresholds on 2017, validates a safe-JSON
multinomial logistic classifier on 2018, and leaves 2019 untouched.

These prototype labels do not rehabilitate the legacy pickled classifier, do
not become official labels, and are not wired to scientific APIs in Phase 2A.
The executed train/validation result and its interpretation boundary are
recorded in `docs/55_PHASE2A_REGIME_VALIDATION_REPORT.md`.
Classifier metrics measure consistency with the transparent pseudo-label rule,
not independent meteorological truth.

## External context

NCMRWF publishes research-prototype probabilistic weather-pattern products that include categories such as Active Monsoon, Break Monsoon, and Western Disturbances. Use these as conceptual evidence that weather-pattern probabilities are operationally meaningful, not as a claim that VarshaSetu reproduces that exact system.
