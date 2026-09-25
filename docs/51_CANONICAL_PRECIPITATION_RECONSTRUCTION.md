# Canonical Precipitation Reconstruction

Status: Phase 1F approved specification for
`varshasetu-gefs12r-imd025-jjas-2000-2019-v2`.

## Verified archive interval structure

The cache-only audit decoded all 15,250 precipitation messages in 122 JJAS
initializations and five members. The machine inventory is
`data/manifests/phase1f/2019-JJAS/interval_inventory.csv`. Every member/cycle
has 25 accumulated-precipitation messages through +75 h, alternating native
three-hour and six-hour ranges:

`0-3, 0-6, 6-9, 6-12, ..., 66-72, 72-75`.

This result comes from decoded `startStep`, `endStep`, `stepRange`, `stepType`,
statistical-processing keys where exposed, and packing metadata. It is not
inferred from filenames. `stepType=accum` throughout. ecCodes 2.48 returns no
computed `packingError` for these complex-packed messages; the inventory
therefore retains binary/decimal scale factors, bit count, reference value,
packing type, and the derived decoded-value quantum.

## Previous method A

V1 reconstructed each 24-hour target as eight three-hour increments. Four were
native three-hour messages and four were differences between independently
packed nested fields. Thus every member-product performed four subtractions.
This was algebraically valid with exact fields, but it made unused diagnostic
three-hour increments admission-critical.

Across 1,830 cases, the diagnostic ledger records 7,320 method-A subtractions,
394,752 negative intermediate cell occurrences, and 13,349 packing-bound and
v1-policy violations. These counts are occurrences across intervals, not unique
geographical cells. Method A admitted 614 products.

## Canonical method B

The implementation in `backend/app/data/accumulation.py` constructs candidate
native intervals and same-base nested differences from message metadata. A
deterministic exact-cover dynamic program minimizes `(subtractions, segments)`.
It does not hard-code a date/member formula. The verified archive yields:

- Day 1: `(0-6 - 0-3) + 6-12 + 12-18 + 18-24 + 24-27`;
- Day 2: `(24-30 - 24-27) + 30-36 + 36-42 + 42-48 + 48-51`;
- Day 3: `(48-54 - 48-51) + 54-60 + 60-66 + 66-72 + 72-75`.

Each target has five non-overlapping segments and one unavoidable subtraction.
Exact coverage is 24 hours with no gap or overlap. Across the season this is
1,830 subtractions, 79,359 negative intermediate cell occurrences, and 1,907
packing-bound violations. Method B admits 1,468 products; every admitted final
field is finite and nonnegative.

## Mathematical equivalence and packing implication

Without packing error, replacing two synthetic three-hour increments by their
native six-hour accumulation is simple regrouping, so methods A and B have the
same 24-hour sum. Tests prove this with exact synthetic fields. For the 614
cases accepted by both methods, the observed final-field mean absolute
difference is `0.0000361616 mm`, the median is zero, p90/p95/p99 are at
floating-point roundoff, and the maximum is `0.05 mm`. The nonzero tail follows
from method A normalizing additional admissible packed-field residues that
method B never constructs.

## Packing policy

For the single selected difference, the maximum independent nearest-rounding
error is `(q_total + q_prefix) / 2`, with each quantum derived from the encoded
binary and decimal scale factors. A negative residue may be normalized to zero
only inside that bound. A residue beyond the bound rejects the product. No
generic epsilon and no acceptance-oriented tolerance is used.

The v1 fixed 0.1 mm operational cap does not carry into v2. Removing it does not
loosen the mathematical bound: the bound remains representation-specific and
can be smaller or larger than 0.1 mm. This semantic change requires v2 and does
not alter v1 evidence.

## July 22 interpretation

The historical p01 `+39→+42` source inconsistency remains real as a derived
three-hour diagnostic. It is not required by the canonical Day-2 cover, which
uses native `+36→+42`; p01 Day 2 therefore passes v2. The former p04 Day-2
failure was likewise in an unused synthetic interval and now passes. c00 Day 2
still fails because its unavoidable `+27→+30` difference exceeds its packing
bound. The anomaly report is preserved; only its consequence for the canonical
target is superseded.

## Decision

The method has exact timing, native interval use, a mathematically derived
packing rule, deterministic replay, materially improved eligibility, complete
lineage, and fail-closed exclusions. It is approved for v2.

`CANONICAL_RECONSTRUCTION_APPROVED`
