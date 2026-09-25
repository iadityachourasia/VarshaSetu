# ML Methodology

## Scientific task

Predict/calibrate observed rainfall from raw NWP and forecast-time predictors while preserving:
- causality,
- spatial/temporal holdout integrity,
- extreme-event skill,
- regime-specific effects,
- interpretability.

## Current baseline ladder

### B0 — Raw NWP
No correction.

Purpose:
- mandatory reference.

### B1 — Linear MOS
Current implementation:
- StandardScaler,
- Ridge regression.

Purpose:
- strong transparent benchmark.

Important audited result:
- saved overall test RMSE was slightly better than current regime-aware model.

Never remove this baseline simply because it is “not advanced AI.”

### B2 — Global ML
Current:
- XGBoost,
- global HGB.

Purpose:
- tests whether nonlinear post-processing helps without regime conditioning.

### B3 — Hard Regime-Aware ML
Current:
- one regime classifier,
- one specialist HGB per regime,
- hard argmax routing.

Purpose:
- core existing PS-aligned prototype.

### B4 — Soft Regime Mixture-of-Experts
Planned recommended model.

Output:
\[
\hat{y}=\sum_r p_r f_r(X)
\]

Purpose:
- use probabilistic regime uncertainty instead of brittle hard switching.

### B5 — Ensemble distributional/EMOS
Recommended when genuine ensemble NWP is available.

Purpose:
- calibrated distribution/probability benchmark.

## Current target issue

Audited target:
- `rain_6h_accum (mm)`.

Heavy/very-heavy probability should not use 24-hour categories directly on this 6-hour target.

Develop:
- corrected 6-hour post-processing if scientifically useful,
- separate 24-hour accumulation product for IMD-style daily heavy categories.

## Residual vs direct target

Current regression predicts rainfall directly.

Evaluate a residual formulation:

\[
\Delta R = R_{obs} - R_{nwp}
\]

then:

\[
R_{corrected}=\max(0,R_{nwp}+\widehat{\Delta R})
\]

Benefits:
- explicit correction interpretation,
- judge-friendly,
- may regularize toward raw NWP.

Do not assume residual formulation is better; benchmark it.

## Feature groups

### Mandatory/likely
- raw NWP precipitation,
- lead time,
- forecast atmospheric variables,
- static geography,
- seasonal/cyclical time fields.

### Physics-guided candidates
- moisture-flux convergence,
- vorticity,
- pressure gradients,
- neighbourhood precipitation,
- orographic upslope forcing,
- coastline distance/onshore-flow interaction.

Every derived feature must be reproducible.

## Feature leakage control

Current string matching is insufficient.

Target approach:
- maintain a feature registry,
- each feature declares `available_at_issue_time`,
- operational dataset builder refuses unknown/unsafe fields.

## Splitting protocol

Do not randomly split rows from the same meteorological events.

Minimum:
- chronological year holdout.

Better:
- year + event holdout,
- optionally spatial holdout for generalization testing.

Hyperparameters must be selected without touching final test years.

## Rare-event strategy

Evaluate:
- class weights,
- event-balanced batches,
- threshold-specific models,
- quantile/distributional losses,
- oversampling only with subsequent calibration on natural-frequency data.

Do not report an extreme model based only on ROC-AUC when positive frequency is tiny.

## Probability modeling

For threshold \(T\):

\[
P(R_{24h} \ge T | X)
\]

Required:
- independent held-out Brier score,
- reliability,
- positive-event count,
- threshold sample size.

Recommended:
- Brier Skill Score against climatology.

If there are zero positive test cases:
- label reliability assessment unavailable/insufficient,
- do not present near-zero Brier as “perfect calibration.”

## Non-negativity

Corrected rainfall must be nonnegative.

Possible methods:
- clipping as current prototype,
- nonnegative distributions,
- log/Box-Cox transformed target with careful inverse transform.

## Hyperparameter tracking

Every trained artifact should record:
- estimator class,
- all hyperparameters,
- seed,
- feature list,
- training range,
- data hash,
- code commit,
- metric report.

## Model serialization

Prefer portable/version-aware serialization.

For XGBoost:
- consider native model save format,
- record package version.

For sklearn:
- record exact versions,
- do not assume arbitrary future pickle compatibility.

## Model selection

Do not select the final model solely by RMSE.

Selection must consider:
- overall RMSE,
- heavy-event ETS/CSI/POD/FAR,
- FSS spatial skill,
- reliability,
- regime consistency,
- lead-time stability.

## Core scientific hypothesis

The project should test:

> Does conditioning post-processing on the weather regime add skill beyond a strong non-regime post-processor?

This is the central experiment.
