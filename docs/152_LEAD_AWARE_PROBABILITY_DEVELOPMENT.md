# Lead-aware extreme-rain recalibration: consumed 2024 development study

Date: 2026-10-07. The [coherent partial-grid replay](151_COHERENT_PARTIAL_GRID_REPLAY.md)
removed nested-probability refusals, but its very-heavy probabilities had
negative Brier skill and a 9.24-fold warning-frequency bias on June 2024.
This study asks whether a simple forecast-lead adjustment offers evidence
of improvement before considering a new model release. It remains separate
from the live worker, API, dashboard and frozen model selection.

The `lead_aware_probability_protocol_v1.json` was hash-sealed before fitting.
The inputs are the existing 2023-trained heavy and very-heavy logistic base
scores on the 183 Phase 4I 2024 cases (238,083 cells). The original
chronological split fixes **108 early calibration cases**, **7 purged cases**,
and **68 later selection cases**. The fit step decoded only early-block labels
from memory-mapped IMD-derived arrays; it sealed all candidate predictions
and their source/model hashes before the scorer decoded later-block labels.
No 2025 or 2026 outcomes were used. The base-model choices and frozen
isotonic control had themselves been selected with 2024 outcomes, so this
is **consumed development data**, not independent validation.

Both new arms use logistic recalibration of the clipped base-score logit,
with fixed `C=0.1`, no class weighting or tuning. The lead-aware arm adds
Day 2 and Day 3 intercept offsets; Day 1 is the reference. For comparability,
the raw base, frozen isotonic, pooled logistic and lead-aware outputs all
receive the same deterministic nested-event projection. They share every
paired cell. The fixed warning cutoffs remain 0.10 for ≥64.5 mm/24 h and
0.05 for ≥115.6 mm/24 h. No threshold was selected in this study.

Early-block support exceeded the prespecified gate: 5,047 heavy positives
across 106 event-bearing cases and 1,256 very-heavy positives across 71
cases. The very-heavy lead counts were 345/417/494 positive cells and
20/25/26 event-bearing cases for Days 1/2/3. These are cells clustered by
initialization, not independent events.

## Later-block diagnostic

The 68-case selection block has 88,468 common cells, 1,242 observed heavy
and 329 observed very-heavy cell events. BSS uses the unchanged 2023
training prevalence. The original frozen calibrators were selected on this
same block, so their score is descriptive and potentially optimistic.

| Arm | Heavy BSS | Very-heavy BSS | Joint Brier | Heavy frequency bias | Very-heavy frequency bias |
|---|---:|---:|---:|---:|---:|
| Frozen isotonic, projected | +0.1491 | +0.0911 | **0.0151642** | 1.14 | 1.49 |
| New pooled logistic, projected | +0.1455 | +0.0899 | 0.0152195 | 0.86 | 1.01 |
| New lead-aware logistic, projected | +0.1483 | +0.0912 | 0.0151754 | 0.89 | 1.06 |

Lead-aware minus pooled global joint Brier is −0.0000441. A 1,000-repeat
initialization-date bootstrap gives a descriptive 95% interval of
**−0.0001174 to +0.0000146**, crossing zero. Heavy and very-heavy intervals
also cross zero. The lead-aware arm is slightly worse than the frozen
isotonic control on joint Brier. On the tiny purged block there are only
four very-heavy observed cells, so its extreme-event rates are unstable.
The warning frequency bias changes markedly by block: for the lead-aware
arm, very-heavy bias is **4.52** on the early fit block, **16.0** on the
seven-case purge, and **1.06** on the later selection block. Fixed-cutoff
frequency therefore does not transport consistently even within 2024.

The raw, class-weighted base scores have strongly negative Brier skill before
calibration; those scores must not be presented as calibrated event
probabilities. Full ten-bin reliability tables, event counts, CSI, POD, FAR,
ETS, Brier skill, and each lead are in the hash-sealed
`lead_aware_probability_score_v1.json`. The fit manifest and forecast-side
predictions are hash-sealed in `lead_aware_probability_prediction_seal_v1.json`
and the ignored local `data/processed/lead_aware_probability_v1/` cache.

## Decision

**Do not promote the lead-aware arm.** Its apparent improvement over the
pooled recalibrator is small and statistically inconclusive on consumed
2024 data, and it does not beat the frozen control on joint Brier. The
June partial-grid population is different from the Phase 4I population,
so the result cannot be used to claim the 9.24× June warning-frequency bias
has been repaired. Next, a frozen no-refit transport check can apply these
artifacts to the June partial-grid forecast features; final model choice
still requires a genuinely independent year and reliable very-heavy
probabilities. The strict live model remains unchanged.

Reproduce the sealed fit with `python scripts/fit_lead_aware_probability.py`
and its score with `python scripts/score_lead_aware_probability.py`. The
scripts refuse changed protocol, split, source-array or sealed-result hashes.
The fit and score reproduced their sealed outputs byte for byte. Five focused
tests passed; the complete backend suite passed **764 tests** on 7 October
2026. No frontend or live API code changed in this study.
