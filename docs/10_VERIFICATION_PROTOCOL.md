# Forecast Verification Protocol

## Purpose

Verification must prove that VarshaSetu improves the raw NWP forecast without hiding trade-offs.

The official SIH problem statement explicitly requires:
- RMSE,
- ETS,
- CSI,
- POD,
- FAR,
- FSS.

## General rules

1. Evaluate on held-out data only.
2. Always compare against raw NWP.
3. Include a strong non-regime post-processing baseline.
4. Preserve the same truth dataset and valid periods across models.
5. Report sample counts.
6. Report positive-event counts for threshold metrics.
7. Never aggregate incompatible accumulation periods.
8. Avoid cherry-picked case-study-only claims.
9. Where possible report uncertainty/confidence intervals.

---

## RMSE

\[
RMSE = \sqrt{\frac{1}{N}\sum_i (F_i-O_i)^2}
\]

Interpretation:
- lower is better,
- penalizes large errors strongly,
- useful for rainfall amount error,
- not enough for rare-event/spatial assessment.

## Contingency definitions

For threshold \(T\):

- Hit \(H\): forecast event and observed event.
- Miss \(M\): no forecast event, observed event.
- False alarm \(F\): forecast event, no observed event.
- Correct negative \(C\): neither.

## POD

\[
POD = \frac{H}{H+M}
\]

- range 0–1,
- higher is better,
- answers how many observed events were detected.

## FAR

\[
FAR = \frac{F}{H+F}
\]

- range 0–1,
- lower is better,
- answers what fraction of forecast events were false alarms.

## CSI

\[
CSI = \frac{H}{H+M+F}
\]

- higher is better,
- ignores correct negatives,
- useful for rare threshold events.

## ETS

Random hits:

\[
H_r = \frac{(H+M)(H+F)}{N}
\]

Then:

\[
ETS = \frac{H-H_r}{H+M+F-H_r}
\]

- perfect = 1,
- adjusts for hits expected by chance.

## FSS — Fractions Skill Score

FSS requires gridded forecast and observation event fields.

For a threshold:
1. convert forecast and observation grids to binary exceedance fields,
2. calculate local fraction of exceedances over neighbourhood windows,
3. compare forecast and observed fractions,
4. normalize mean squared fraction error.

Conceptually:

\[
FSS = 1 - \frac{MSE_{fraction}}{MSE_{reference}}
\]

Report across:
- rainfall thresholds,
- spatial neighbourhood sizes,
- forecast leads.

Do not compute FSS on independent station rows without a defensible spatial neighbourhood framework.

## Probability verification — recommended

### Brier Score

\[
BS = \frac{1}{N}\sum_i (p_i-o_i)^2
\]

- lower is better,
- must be accompanied by positive-case count.

### Brier Skill Score

Compare against climatological/reference probability.

### Reliability diagram

Bin probabilities and compare:
- mean forecast probability,
- observed event frequency.

A probability is not “calibrated” because a calibration estimator exists; it must be evaluated.

---

# Evaluation matrices

## A. Model comparison

Always attempt:

| Model | Role |
|---|---|
| Raw NWP | mandatory baseline |
| Linear MOS | transparent statistical post-processing |
| Global ML | non-regime nonlinear baseline |
| Hard regime-aware | current architecture |
| Soft regime MoE | target USP |
| EMOS | when ensemble available |

## B. Breakdown dimensions

Where data are sufficient:
- lead time,
- weather regime,
- district/region,
- rainfall threshold,
- season/month,
- terrain category.

## C. Spatial scales

For FSS select physically meaningful neighbourhood scales based on actual grid resolution.

Do not invent “25 km” unless grid mapping supports it.

---

# Rare-event reporting

If observed-event count:
- `0`: metric such as POD is undefined; say so.
- `<10`: display a severe rare-event warning.
- low enough for unstable inference: report confidence interval/event count.

Never convert undefined metrics to zero unless zero is mathematically the actual score.

---

# Test split

Current audited intention:
- train 2020–2023,
- validation 2024,
- test 2025.

This may change once real NWP archives are adopted.

When changed:
- document reason,
- freeze final test period before tuning,
- update tests and report metadata.

---

# Case-study vs aggregate evidence

A judge-facing case study should show:
- raw forecast,
- corrected forecast,
- observation,
- raw error,
- corrected error.

But the project must separately show:
- aggregate held-out metrics,
- multiple events,
- failure cases.

---

# Minimum verification report schema

```json
{
  "experiment_id": "...",
  "data_manifest": "...",
  "test_period": "...",
  "models": {
    "raw_nwp": {},
    "mos": {},
    "global_ml": {},
    "regime_aware": {}
  },
  "continuous": {},
  "thresholds": {},
  "fss": {},
  "probability": {},
  "regime_breakdown": {},
  "lead_time_breakdown": {},
  "warnings": []
}
```

---

# Correct interpretation

Do not claim:
- “35% more accurate” when metric is RMSE reduction.
Use:
- “35% reduction in RMSE on [specified held-out set]”.

Do not claim:
- “100% POD means perfect forecast.”
FAR/CSI/ETS and sample size matter.

Do not claim:
- “Brier=0 means calibrated” when no positive events occurred.
