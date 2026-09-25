# Corpus Admission Policy

Status: frozen for `varshasetu-gefs12r-imd025-jjas-2000-2019-v1`.

## Admission unit and evidence

Eligibility is recorded for each `initialization x product`, with validity kept
separately for c00, each perturbation member, the atmospheric bundle, the exact
observation, alignment, and mask. A failed optional component cannot silently
invalidate or validate another use case. Source bytes are never repaired.

## Eligibility tiers

| Tier | Required evidence |
|---|---|
| `SOURCE_VALID` | immutable bytes, receipt/hash, expected provider, message identity, metadata and decode pass |
| `PAIR_VALID` | source-valid c00 rainfall and observation, exact time window/date, same target grid |
| `CONTROL_MODEL_ELIGIBLE` | pair valid plus c00 rainfall and complete valid control atmospheric bundle |
| `FULL_ENSEMBLE_ELIGIBLE` | pair valid plus c00 and every p01-p04 rainfall member for the same product/timing; no substitution |
| `REGIME_ELIGIBLE` | valid source, timing, and complete forecast-time atmospheric context; no regime label implied |
| `EXTREME_EVENT_ELIGIBLE` | pair valid, correct 24-hour truth, and forecast inputs required by the declared extreme experiment |
| `FSS_ELIGIBLE` | pair valid plus aligned two-dimensional forecast/reference fields and valid spatial mask |
| `REJECTED` | no declared scientific use remains eligible; component-scoped failures are retained as reasons |

The implementation is `backend/app/data/corpus_policy.py`. It emits independent
machine-readable booleans, not a single sample-wide training flag.

## Quarantine rules

A malformed member-product is quarantined at the narrowest scientifically valid
scope. It is never clipped beyond the frozen negative-residue rule, replaced by
another member, or filled spatially/temporally. Permanent missing/corrupt source,
identity mismatch, wrong timing, invalid observation, non-finite values, or a
material negative increment creates an explicit reason and source lineage.

For the July 22 case: source files remain valid and inspectable; the p01 Day-2
derived member-product is rejected. c00, the observation, and atmosphere remain
valid, giving `CONTROL_MODEL_ELIGIBLE=true`, `FULL_ENSEMBLE_ELIGIBLE=false`,
`REGIME_ELIGIBLE=true`, `EXTREME_EVENT_ELIGIBLE=true`, and
`FSS_ELIGIBLE=true` for control-based uses.

## Monthly gate

Every month receives one machine-generated outcome after source identity/hash,
message count, timing, observation date, accumulation reconstruction,
packing-negative, atmospheric variable/level/unit/lead, target-grid/mask,
conservation, completeness, and lineage checks:

- `MONTH_ACCEPTED`: all expected units pass.
- `MONTH_ACCEPTED_WITH_QUARANTINED_SAMPLES`: month-level contract and lineage
  pass, but explicitly identified units are excluded from relevant tiers.
- `MONTH_REJECTED`: provider/schema/lineage or another month-wide invariant
  fails, so no unit enters a training view pending review.

July 2019 is the second state, not a fabricated 100% pass.

## Corpus and comparison rules

Experiment denominators come from their tier: control experiments use all
`CONTROL_MODEL_ELIGIBLE` cases; full-ensemble experiments use all
`FULL_ENSEMBLE_ELIGIBLE` cases. Every published model comparison must evaluate
all compared models on the identical intersection of valid case IDs unless the
table is explicitly labeled as non-paired. `shared_case_intersection` encodes
this rule and prevents availability from creating an apparent skill advantage.

## Phase 1E executed outcome

The 2019 JJAS season is
`SEASON_ACCEPTED_WITH_QUARANTINED_SAMPLES`. Of 366 initialization/product rows,
366 are `SOURCE_VALID`, 52 are `PAIR_VALID` and control-model eligible, 9 are
full-ensemble eligible, and 366 are atmosphere-only `REGIME_ELIGIBLE`. No row is
globally `REJECTED` because forecast-time atmosphere remains valid even when its
rainfall product is quarantined. These counts are evidence, not permission to
train; `training_eligible=false` remains set.

## V2 canonical reconstruction addendum

For `varshasetu-gefs12r-imd025-jjas-2000-2019-v2`, rainfall admission applies
to the exact canonical 24-hour target decomposition in doc 51. An unused
synthetic three-hour diagnostic failure does not reject that target. The one
selected boundary difference must remain within its half-sum packing-quantum
bound; there is no generic epsilon or separate 0.1 mm cap. All other tier rules
remain unchanged.

The executed v2 counts are 255 control/pair/extreme/FSS rows, 173 complete
ensemble rows, and 366 regime rows. July 22 Day 2 remains control-ineligible
because c00 fails, despite p01 and p04 becoming valid under the canonical cover.

## Phase 2A seasonal subset outcome

The bounded 2017/2018 train/validation subsets are each admitted with
quarantined samples; their source lineage and tier counts are recorded in
[`53_PHASE2A_2017_2018_CORPUS_REPORT.md`](53_PHASE2A_2017_2018_CORPUS_REPORT.md).
2017 has 258 control-model eligible, 187 full-ensemble eligible, and 366
regime-eligible rows. 2018 has 251, 176, and 366 respectively. Rainfall
member-product availability is 1,489/1,830 and 1,476/1,830. These appended
outcomes apply the same v2 tier semantics; they do not change any existing
2019 count or make these subsets rainfall-model training authorization.
