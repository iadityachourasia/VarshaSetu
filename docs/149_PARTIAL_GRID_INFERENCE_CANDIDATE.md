# Partial-grid frozen-model candidate: June 2024 development validation

Date: 2026-10-07. This **research candidate** replays all 30 June 2024 GEFS
00 UTC cycles with the frozen Track B models under the sealed
`partial_grid_inference_protocol_v1.json`. It is outside `data/live`, the
worker, API and dashboard. The forecast-only seal is
`partial_grid_inference_forecast_result_v1.json`; a separate, later
observation-paired score is `partial_grid_inference_score_v1.json`. Both have
SHA-256 sidecars and each retained case has a hash-verified mask, field array,
district table and source/model lineage.

## Method and refusal gates

The candidate constructs the exact canonical accumulation where possible.
For a material negative nested difference, it marks that cell NaN. It builds
the existing 22 forecast-time features with a temporary zero only in invalid
rain rows, **slices those rows out before calling the frozen models**, and
scatters NaN back afterward. The forecast-only regime vector comes from the
same atmospheric context. On strict-pass leads, the raw grid and each ready
M0/M2/M4 output must match the full-grid path within 1e-6.

The regional gate is 99% valid cells and the district gate is 95% weighted
valid area. Unsupported districts have null forecast means and a coverage
reason. Frozen heavy/very-heavy calibrators are also subject to the existing
coherence gate, `P(very heavy) ≤ P(heavy)` at every eligible cell. A failure
produces a **lead refusal with no forecast or district arrays**. We do not
clip, reorder or relabel those probabilities.

| Forecast-side gate | June 2024 count |
|---|---:|
| Planned date/lead cases | 90 |
| Regional spatial gate passed | 90 |
| Strict rainfall QC passed | 35 |
| Frozen model/probability gates passed | 55 |
| Frozen probability-order refusals | 35 |
| Newly available versus strict rainfall QC, with all model gates passed | 35 |
| District-by-ready-lead values withheld below 95% coverage | 146 |

All 35 model refusals were the very-heavy-above-heavy probability error.
Fifteen of those leads had passed strict rainfall QC, so probability
coherence is an independent blocker. The earlier mask-only result had 55
strictly withheld June 2024 leads; 20 of those remain refused by the model
gate. The candidate therefore does **not** claim to recover all masked leads.

## Same-cell development score

IMD 0.25-degree daily rainfall was paired to the 03–03 UTC valid-date window
only after the forecast-only candidate seal. Every M0/M2/M4 comparison uses
the identical jointly valid cells. June 2024 was already used for development
validation in prior work; these numbers are not independent-year skill.

| Ready-case stratum | Cases | Paired cells | Model | RMSE (mm) | Mean bias (mm) | Heavy CSI |
|---|---:|---:|---|---:|---:|---:|
| All ready | 55 | 71,376 | Raw M0 | 15.344 | −0.018 | 0.050 |
| All ready | 55 | 71,376 | Global M2 | **13.983** | 1.197 | 0.139 |
| All ready | 55 | 71,376 | Regime M4 | 14.213 | 2.004 | 0.153 |
| Strict-withheld, now ready | 35 | 45,356 | Raw M0 | 15.246 | −0.144 | 0.055 |
| Strict-withheld, now ready | 35 | 45,356 | Global M2 | **13.572** | 0.625 | **0.129** |
| Strict-withheld, now ready | 35 | 45,356 | Regime M4 | 14.035 | 1.713 | 0.124 |

Across all ready cases, a 1,000-repeat initialization-date bootstrap gave
M4 minus M2 RMSE interval **+0.014 to +0.475 mm** and heavy CSI interval
**−0.013 to +0.029**. The RMSE interval is entirely worse for M4; the CSI
interval includes zero. These are descriptive development intervals with
remaining spatial and serial dependence. Very-heavy events remain sparse;
the stored hit/miss/false-alarm counts must accompany any interpretation.

## Decision

The cell mask can recover some forecast coverage without changing eligible
rainfall values, but the frozen probability incoherence prevents a complete
probability bundle on 35/90 leads. M4 does not pass a persuasive promotion
case over M2 on this development set. **Keep the strict global product as
default.** Next investigate a separately frozen, development-only coherent
probability method and verify its reliability; then test partial-grid
publication semantics and independent-year performance. No operational or
public-warning use follows from this candidate.

Reproduce focused checks with
`python -m pytest backend/tests/test_partial_grid_candidate.py backend/tests/test_partial_grid_score.py -q`.
The complete backend suite passed **749 tests** on 7 October 2026 with a
repository-local pytest temp directory; one Starlette dependency deprecation
warning remains. A transient Windows Access Denied during a staging-directory
rename was reproduced in the corpus test and fixed with a bounded retry for
that specific error. The forecast and score sidecars reproduce their hashes.
