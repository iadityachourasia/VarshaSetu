# Monthly Authoritative-Data QC Specification

Status: Phase 1C gate definition. Passing this gate does not by itself make a
month training-eligible.

## Case states

Every expected initialization, rainfall case, predictor snapshot, and
observation pairing must have exactly one state: `PASS`, `FAIL`, `BLOCKED`, or
`PARTIAL`, with a reason for every non-PASS state. Missing cases are never removed
from denominators.

## Source and cache gates

Hard fail or block when any of the following occurs:

1. official URL/object identity is missing;
2. cached bytes lack a matching receipt, byte count, range identity, or SHA-256;
3. HTTP status/range length is wrong or a partial file is presented as final;
4. decoded initialization/member/variable/level/lead/unit differs from request;
5. a missing member is replaced by another member;
6. child/source hashes do not validate.

Retries are independent by object/message, use bounded backoff, write temporary
content separately, and atomically finalize only verified bytes. A cache-only
repeat must make zero network requests and preserve child hashes when source and
processing code are unchanged.

## Rainfall gates

- Exact windows are +3..+27, +27..+51, and +51..+75 hours.
- Each window must contain eight gap-free, non-overlapping three-hour increments.
- Native direct/nested interval semantics come from decoded `stepRange`.
- Source units must be liquid-water-equivalent kg m**-2, normalized 1:1 to mm.
- Negative packed differences may be zeroed only within the documented packing
  tolerance and must be counted with the minimum retained residue.
- Any more-negative value fails that product; tolerance cannot be widened to
  improve completeness.
- Output must be finite and nonnegative on the 49×49 target grid.
- First-order conservative mapping must have relative domain-integral error at
  or below 1e-10 on the paired valid mask.

## Atmospheric gates

For each initialization and +24/+48/+72 lead, validate U850, V850, Q700, Z500,
MSLP, and PWAT using decoded metadata. Crop only the 5–30°N, 55–95°E source
region and bilinearly interpolate smooth fields to the 0.5° context grid. Units
are preserved. Non-finite values or uncovered target coordinates fail. Monthly
min/max/mean/missing fraction and warning-bound excursions are reported; warning
bounds never authorize clipping.

## Observation and pairing gates

The IMD field must match the exact valid date and represent `[D-1 03 UTC,
D 03 UTC)`. The source checksum, record index, date label, 49×49 crop, 1,301
valid cells, 1,100 masked cells, and missing-value policy are retained. Missing
is not zero and a nearby date cannot be substituted.

## Monthly admission result

A month is `PASS` only when all expected cases pass all hard gates. Any mixture
of passing and failed/blocked cases is `PARTIAL`; all failed is `FAIL`; all
unavailable is `BLOCKED`. A monthly collection manifest must hash its daily
children and remain `training_eligible=false` until a later corpus-level review
also resolves provenance, split policy, leakage, event sufficiency, regime-label
methodology, and all acceptance criteria.

Phase 1C July 2019 is `PARTIAL` because one `p01` Day-2 rainfall product fails
the negative-residue gate. It cannot be silently admitted by dropping that case.
## Phase 1D admission outcome extension (2026-09-19)

Monthly QC now has explicit outcomes `MONTH_ACCEPTED`,
`MONTH_ACCEPTED_WITH_QUARANTINED_SAMPLES`, and `MONTH_REJECTED`. Component
failures are mapped to the eligibility tiers in
`docs/43_CORPUS_ADMISSION_POLICY.md`; a valid control case is not removed solely
because a perturbation member failed, and an incomplete ensemble never enters a
full-ensemble view. The historical July statement used the pre-freeze blanket
tolerance and is superseded by the executed note below.

## Phase 1E execution note

Strict packing-aware replay assigns all four 2019 JJAS months
`MONTH_ACCEPTED_WITH_QUARANTINED_SAMPLES`. Rainfall validity is June 134/450,
July 137/465, August 151/465, and September 192/450; every one of the 2,196
required atmospheric snapshots passes. See `47_2019_JJAS_CORPUS_REPORT.md`.

## V2 monthly QC supersession

The eight-three-hour-segment gate is retained only as v1 history. A v2 monthly
run validates the canonical minimal exact cover in docs 51–52. For each target
window it records selected native intervals, subtraction count, packing bound,
normalized representation-residue count, final finiteness/nonnegativity, and
conservative-remapping error. A synthetic increment not selected by the
canonical cover cannot reject a v2 product. Every selected boundary difference
still fails closed when it exceeds its representation-aware bound.
