# Nationwide v2 probability cutoff transport — 9 October 2026

## Question and fixed diagnostic

The separate nationwide v2 repair in `docs/168` fixed fold dependence and
cutoff-scale selection but failed its consumed-2024 Brier comparison and
issued zero very-heavy warnings. This addendum asks **where** the already
chosen 2023 out-of-fold warning cutoff loses all 2024 exceedances. It does
not refit or change that model, calibrator, threshold or product default.

The write-once forecast-only protocol
`nationwide_probability_cutoff_transport_protocol_v1.json` (SHA-256
`c1ec72bb409e0186a9eea4efa12bd447e6b3b1e8e296e27964f1e2daeb202bdf`)
was sealed before the full diagnostic. The script rechecked the v2 protocol,
fit seal, all 156 prediction hashes, national feature manifest and every
forecast-feature hash. It recomputed logistic head scores, lead-isotonic
outputs and coherent saved arrays from forecast-only features, asserting
bitwise equality after float32 storage. It did not call the IMD reference
loader or read any 2024 rainfall value. No 2025/2026 observation or forecast
was used. The result is write-once
`nationwide_probability_cutoff_transport_result_v1.json` (SHA-256
`bdd103fa298c5aff77917145fdf82f0da054551cfb6e78834442ac16362ddf7b`).

## Result

The diagnostic covers **796,380 forecast-supported land cells** across
45/50/61 Day 1/2/3 cases. This is the forecast-only footprint. The prior
2024 Brier comparison used **760,812 reference-valid paired cells**;
therefore these cutoff counts must not be compared as if they were the same
verification population. `Warnings` below means probability at or above the
unchanged cutoff, not a public warning.

| Head and lead | Frozen cutoff | Uncalibrated head exceedances | Lead-calibrated maximum | Lead-calibrated exceedances | Saved coherent exceedances |
|---|---:|---:|---:|---:|---:|
| Very heavy, Day 1 | 0.03 | 7,698 | 0.02728838 | 0 | 0 |
| Very heavy, Day 2 | 0.03 | 6,439 | 0.02491874 | 0 | 0 |
| Very heavy, Day 3 | 0.03 | 10,362 | 0.01130670 | 0 | 0 |
| Heavy, all leads | 0.08 | 42,320 | maximum varies by lead | 7,865 | 7,680 |

The very-heavy disappearance occurs during **lead-aware calibration of the
2024 head-score distribution**. Coherence projection leaves its zero count
unchanged. The uncalibrated exceedance counts are not validated warnings and
must not be substituted for the calibrated product. At the heavy cutoff,
float32 storage changes 185 all-forecast-cell decisions relative to the
unrounded calibrated values, mostly because values at the 0.08 boundary
round below the literal threshold. A future protocol should define cutoff
evaluation on the persisted probability precision; v2 evidence stays frozen.

This identifies a cutoff-transport failure, not its meteorological cause or
a calibrated alternative. The consumed 2024 result in `docs/168` remains:
very-heavy Brier 0.003901 versus v1 0.003807, zero warnings among 760,812
paired cells against 3,017 observed events. It is not independent reliability
evidence. Choosing a lower cutoff after seeing this diagnostic would be
post-hoc selection. Regional M2 and all live/default probability labels stay
unchanged; no public warning or national probability promotion follows.

## Reproduction

- `python scripts/diagnose_nationwide_probability_cutoff_transport.py write`:
  exit 0, result SHA above. This command is write-once and must not be rerun.
- `python scripts/diagnose_nationwide_probability_cutoff_transport.py check`:
  exit 0, `CUTOFF_DIAGNOSTIC_REPRODUCED`.
- Focused diagnostic and prior v2 tests: **6 passed**, exit 0, including a
  reference-loader trap and exact threshold-count test.
- Full backend suite with the known working Windows socket setup:
  `python -m pytest backend/tests -q
  --basetemp=data/pytest-cutoff-transport-final-20261009
  -p no:cacheprovider --durations=5`: **860 passed**, exit 0 in 154.68 s.

The next scientific candidate, if attempted, must freeze its own nested
date-block training, calibration, persisted-precision cutoff policy, same-case
comparators and gates before fitting. 2024/2025 are consumed; 2026 remains
sealed by `docs/159` and `docs/174`. This diagnosis alone does not justify
another fit or any change to the displayed threshold.
