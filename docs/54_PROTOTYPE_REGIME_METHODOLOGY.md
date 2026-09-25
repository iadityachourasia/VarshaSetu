# Prototype Three-Regime Methodology

## Status and scope

Phase 2A defines a transparent prototype regime system with three mutually
exclusive operational classes:

1. `ACTIVE_MONSOON`
2. `BREAK_WEAK_MONSOON`
3. `LOW_DEPRESSION_INFLUENCED`

These are deterministic project pseudo-labels, not official NCMRWF or IMD
labels. Real monsoon states and synoptic drivers can overlap. A production
successor should therefore use hierarchical or multi-label representation.

The implementation is `backend/app/ml/forecast_regimes.py`. It uses only the
GEFS c00 atmospheric forecast initialized at 00 UTC on the frozen
5–30 degrees N, 55–95 degrees E, 0.5-degree context grid. IMD rainfall and all
other valid-time observations are excluded from label definition and classifier
input.

## Cases and temporal isolation

There is one regime case for each initialization and product lead: +24, +48,
and +72 hours. Phase 2A roles are frozen as:

- 2017 JJAS: threshold, normalization, and classifier fitting;
- 2018 JJAS: validation only;
- 2019 JJAS: untouched final test/demo period.

Only `REGIME_ELIGIBLE` cases with a complete six-field atmospheric bundle enter
feature extraction. Missing or fill-valued fields fail closed.

## Base fields

The ordered base-field bundle is U850, V850, Q700, Z500, MSLP, and PWAT. Its
units are respectively m s-1, m s-1, kg kg-1, geopotential metres, Pa, and
kg m-2.

## Area weighting and diagnostics

For a gridded field (x(\phi,\lambda)), the context-domain mean is

\[
\overline{x} =
\frac{\sum_{i,j} x_{ij}\cos\phi_i}
     {N_\lambda\sum_i\cos\phi_i}.
\]

Wind speed and the prototype column-moisture transport magnitude are

\[
S = \sqrt{U_{850}^2 + V_{850}^2}, \qquad M = PWAT\,S.
\]

Spherical relative vorticity is evaluated by centred numerical gradients in
radians (one-sided second-order gradients at domain boundaries):

\[
\zeta = \frac{1}{R\cos\phi}\frac{\partial V_{850}}{\partial\lambda}
       - \frac{1}{R}\frac{\partial U_{850}}{\partial\phi},
\]

where (R=6,371,000\) m. The pressure-range diagnostic is

\[
\Delta p = \max(MSLP)-\min(MSLP).
\]

The frozen ordered feature vector is:

1. area-mean PWAT;
2. area-mean Q700;
3. area-mean U850;
4. area-mean V850;
5. area-mean wind speed;
6. area-mean `PWAT * wind speed`;
7. area-mean MSLP;
8. minimum MSLP;
9. MSLP range;
10. area-mean Z500;
11. area-mean relative vorticity;
12. 90th percentile relative vorticity.

## Training-only standardization

For each feature (x_k), 2017 eligible cases determine

\[
z_k = \frac{x_k-\mu_{k,2017}}{\sigma_{k,2017}}.
\]

Zero training standard deviations are represented by a scale of one. The
resulting means and scales are frozen and applied unchanged to 2018. No 2019
value participates in fitting.

## Deterministic pseudo-label hierarchy

The low/depression score combines four different physical signals rather than
classifying on one scalar:

\[
L = \frac{-z_{p_{min}} + z_{\Delta p} + z_{\zeta_{90}} + z_{PWAT}}{4}.
\]

The low/depression threshold is the 75th percentile of (L) in 2017. A case
at or above that frozen threshold receives
`LOW_DEPRESSION_INFLUENCED`.

For remaining cases, the active score is

\[
A = \frac{z_{PWAT}+z_{Q700}+z_{S}+z_M}{4}.
\]

Its threshold is the 2017 median of (A) among cases below the 2017 low-score
threshold. A remaining case at or above the frozen active threshold receives
`ACTIVE_MONSOON`; all other cases receive `BREAK_WEAK_MONSOON`.

This hierarchy makes the pseudo-label definition reproducible and physically
inspectable. Its quantiles are design choices for a prototype and are not
claimed to be authoritative meteorological thresholds.

## Classifier

A class-weighted multinomial logistic regression with the fixed seed 26080 is
fit to the 2017 pseudo-labels. The classifier has its own 2017-only feature
mean and scale. For standardized vector (z), probabilities are

\[
P(r\mid z) = \frac{\exp(w_r^Tz+b_r)}
                  {\sum_s\exp(w_s^Tz+b_s)}.
\]

Coefficients, intercepts, scales, classes, feature order, and metadata are
stored as validated JSON. No pickle or executable object deserialization is
required. Probabilities are checked to sum to one within `1e-12`.

## Interpretation boundary

Agreement between the classifier and these pseudo-labels measures only
reproduction/consistency with the prototype definition. It does not establish
objective meteorological regime skill. Independent expert or authoritative
labels remain necessary for that claim. Rainfall skill from later regime-aware
post-processing must also be compared with a non-regime post-processor on a
shared held-out case set.

