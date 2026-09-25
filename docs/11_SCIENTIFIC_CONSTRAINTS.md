# Scientific Constraints — Non-Negotiable

These constraints exist to protect the project from producing convincing-looking but invalid results.

## SC-01 — Forecast-time causality

Operational inference may use only:
- forecast data available at issue time,
- static data,
- previously observed data genuinely available before issue time.

No future-valid-time observations.

## SC-02 — Observation/forecast semantic separation

Every variable must be classified:
- forecast,
- observation,
- reanalysis,
- static,
- derived.

Unknown = not permitted for final operational model.

## SC-03 — Reanalysis is not NWP forecast

Never benchmark “post-processing” by treating ERA5/IMDAA analysis fields as a raw operational forecast.

## SC-04 — Accumulation windows must match

A threshold defined for 24-hour rainfall must be evaluated against a 24-hour accumulation.

## SC-05 — No fabricated scientific UI

No hardcoded:
- metrics,
- probabilities,
- “confidence,”
- rainfall curves,
- pass/fail scientific results
unless visibly labeled as design placeholders.

## SC-06 — FSS needs spatial fields

No 2-D forecast/observation neighbourhood = no valid conventional FSS.

## SC-07 — Held-out test integrity

Final test data must not influence:
- hyperparameters,
- feature selection,
- calibration fitting,
- threshold tuning,
- model choice.

## SC-08 — Regime labels must be reproducible

`regime_id` may not remain an unexplained external column.

## SC-09 — Regime-aware value must be empirically demonstrated

A regime model that does not beat a strong global baseline is not allowed to be described as superior.

## SC-10 — Extreme-event sample size must be disclosed

Every extreme metric must show event count.

## SC-11 — Probability ≠ confidence

Display calibrated event probability only when defined and evaluated.

## SC-12 — Softmax ≠ calibration

Applying softmax to arbitrary scores does not make them statistically calibrated probabilities.

## SC-13 — Truth-source uncertainty must be acknowledged

Satellite/gauge/gridded observations may disagree.

Document truth source and limitations.

## SC-14 — No unsupported novelty claims

Do not claim:
- first regime-aware Indian postprocessor,
- first AI monsoon correction,
unless evidence supports that statement.

## SC-15 — Baselines are mandatory scientific controls

Do not delete MOS/simple baselines to make a complex model look stronger.

## SC-16 — Units are explicit

Every meteorological variable and derived variable must carry known units.

## SC-17 — Timezones are explicit

Store canonical timestamps in UTC where possible.
Convert for UI.

## SC-18 — Negative rainfall prohibited

Corrected rainfall outputs must not be negative.

## SC-19 — Missing data behavior is deterministic

No silent filling with arbitrary defaults in production inference.

## SC-20 — Experiment artifacts are versioned

A reported metric must be traceable to:
- data hash,
- code version,
- model version,
- feature list,
- split.

## SC-21 — Judge-facing claims must survive source inspection

If a claim cannot be demonstrated by:
- code,
- data lineage,
- report,
- test,
then weaken or remove the claim.

## SC-22 — No UI label stronger than backend semantics

Examples:
- use “historical replay,” not “live forecast,” until live forecasting exists;
- use “reference observation,” not “rain gauge,” unless gauge provenance exists;
- use “prototype dataset,” not “official dataset,” unless official source is documented.
