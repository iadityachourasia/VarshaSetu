# Prototype Training Index Specification

Status: future experiment indices only. No training is authorized by this file.

## Authoritative index

`data/manifests/phase1e/2019-JJAS/eligibility_index.csv` contains one row for
each of 122 initializations and three products (366 rows). Every row includes:

- initialization timestamp;
- forecast product and valid date;
- all eight frozen eligibility booleans;
- component-scoped quarantine reasons;
- daily source-manifest lineage.

The booleans are independent. `REJECTED` means no declared scientific use
remains; it is not the negation of one arbitrary global training flag.

## Generated views

| View | Tier | Rows |
|---|---|---:|
| `control_model_index.csv` | `CONTROL_MODEL_ELIGIBLE` | 52 |
| `full_ensemble_index.csv` | `FULL_ENSEMBLE_ELIGIBLE` | 9 |
| `regime_index.csv` | `REGIME_ELIGIBLE` | 366 |
| `extreme_event_index.csv` | `EXTREME_EVENT_ELIGIBLE` | 52 |
| `fss_index.csv` | `FSS_ELIGIBLE` | 52 |

All 366 rows are `SOURCE_VALID`; 52 are `PAIR_VALID`; none are globally
`REJECTED` because the complete atmospheric context remains usable for future
regime research even where rainfall reconstruction is quarantined.

`REGIME_ELIGIBLE` means only that the forecast-time atmosphere inputs are
complete. It does not imply that a regime label exists. No `regime_id`, heuristic
label, classifier, split, fitted transform, or model artifact was created.

## Future-use rules

1. A future experiment must select its declared tier before constructing splits.
2. Compared methods must use the identical held-out case intersection.
3. The 2019 season must not be silently treated as fully rainfall-training-ready.
4. The 52-case control and 9-case full-ensemble views are small and highly
   selected by reconstruction validity; any use requires a selection-bias review.
5. FSS may later use `fss_index.csv`, but no FSS value exists yet.
6. Every result must retain the source-manifest column and dataset version.

## Quarantine example

For 2019-07-22 Day 2, c00, p01, and p04 are quarantined under strict replay;
p02 and p03 pass. The row remains `SOURCE_VALID=true` and
`REGIME_ELIGIBLE=true`, but pair/control/full-ensemble/extreme/FSS eligibility is
false. This supersedes the earlier expectation that only p01 would be excluded.

## V2 generated views

The authoritative successor index is
`data/manifests/phase1f/2019-JJAS/eligibility_index.csv`.

| View | V2 rows |
|---|---:|
| control model | 255 |
| full ensemble | 173 |
| regime | 366 |
| extreme event | 255 |
| FSS-capable aligned fields | 255 |

These are eligibility views, not trained datasets. Future chronological model
development must use v2, retain case/source lineage, fit preprocessing only on
training years, and compare methods on identical held-out intersections. The
2019 season alone is not an untouched multi-year final test.

## Phase 2A chronological role freeze

The approved prototype split is now 2017 JJAS training, 2018 JJAS validation,
and 2019 JJAS final untouched testing/demo. The final sentence above is retained
as historical context and is superseded by this explicit three-season split.
All product/grid rows belonging to an initialization remain in its annual role;
random grid-cell splitting is forbidden. Every fitted transform, climatology,
pseudo-label threshold, feature choice, and classifier parameter in Phase 2A is
derived from 2017 only. Validation decisions may use 2018. No development step
may read 2019 predictors or observations.

Regime pseudo-label and classifier artifacts do not authorize rainfall-model
training by themselves. Later model comparisons must still use the appropriate
eligibility tier and identical held-out case intersections.

The Phase 2A manifests and materialized indices are now available for both
authorized years. 2017 contains 258 control and 187 full-ensemble eligible
cases; 2018 contains 251 and 176. Both have 366 regime-eligible cases. The
forecast-only regime reproduction result and artifact hashes are in
[`55_PHASE2A_REGIME_VALIDATION_REPORT.md`](55_PHASE2A_REGIME_VALIDATION_REPORT.md).
These prototype regime cases are not rainfall-training cases, and the 2019
held-out split remains excluded from all fitting and validation decisions.

## Phase 2B authorized rainfall-model comparison (2026-09-23)

The earlier status above records the Phase 2A authorization boundary and is
retained as historical evidence. A separate bounded Phase 2B task subsequently
authorized retrospective rainfall modeling on the frozen roles. It constructs
the actual per-year common population from the intersection of control
eligibility, regime/feature availability, paired observations, and finite
valid-cell inputs; 251 and 255 are reference upper bounds, not hard-coded
denominators. The executed case keys, exact cell counts, and selection freeze
are recorded in `data/manifests/phase2b/` and `docs/58`–`docs/62`.

The 2019 values were first opened only after the model-selection manifest was
written and hash-verified. This authorization does not permit retuning against
2019, legacy CSV/model use, or scientific API exposure.
