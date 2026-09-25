# GEFS Accumulation Anomaly Report

Status: Phase 1D forensic result. Classification: `SOURCE_INCONSISTENCY`.

## Scope and immutable evidence

The case is GEFSv12 Reforecast initialization `2019-07-22 00Z`, perturbation
member `p01`, `day2_24h` (+27 through +51 h). The investigation decoded the
existing authoritative cached byte ranges only. The p01 file is 7,727,906 bytes,
SHA-256 `662936bf9236160ca3f0f3aea48d73d6d292e3a480db42e1ad89362d00f5e2cf`.
Its cached official NOAA index is 5,236 bytes, SHA-256
`ad8179a6a1d1a307093812289052020ff0e0b5c2485e663e4803a28ebf527426`.
The receipt retains the exact NOAA S3 URL. No source byte was changed.

The reproducible machine record is
`data/manifests/phase1d/july22_accumulation_anomaly.json`; the producing script
is `scripts/data/investigate_accumulation_anomaly.py`.

## Day-2 message sequence

All nine messages that participate in Day-2 have `shortName=tp`,
`name=Total Precipitation`, `stepType=accum`, `units=kg m**-2`,
`packingType=grid_complex_spatial_differencing`, `referenceValue=0`,
`missingValue=9999`, `numberOfValues=1,038,240`, zero missing values, and a
1440 x 721 regular latitude/longitude grid. Full per-message metadata is in the
machine record.

| Message | stepRange | forecastTime | valid UTC | bits | E | D | quantum mm | min/max mm |
|---:|---|---:|---|---:|---:|---:|---:|---|
| 9 | 24-27 | 24 | 2019-07-23 03:00 | 10 | 0 | 1 | 0.1 | 0 / 84.9 |
| 10 | 24-30 | 24 | 2019-07-23 06:00 | 11 | 0 | 1 | 0.1 | 0 / 199.2 |
| 11 | 30-33 | 30 | 2019-07-23 09:00 | 10 | 0 | 1 | 0.1 | 0 / 113.6 |
| 12 | 30-36 | 30 | 2019-07-23 12:00 | 11 | 0 | 1 | 0.1 | 0 / 196.0 |
| 13 | 36-39 | 36 | 2019-07-23 15:00 | 11 | 0 | 1 | 0.1 | 0 / 169.2 |
| 14 | 36-42 | 36 | 2019-07-23 18:00 | 10 | 1 | 1 | 0.2 | 0 / 189.6 |
| 15 | 42-45 | 42 | 2019-07-23 21:00 | 10 | 0 | 1 | 0.1 | 0 / 106.1 |
| 16 | 42-48 | 42 | 2019-07-24 00:00 | 11 | 0 | 1 | 0.1 | 0 / 125.8 |
| 17 | 48-51 | 48 | 2019-07-24 03:00 | 10 | 0 | 1 | 0.1 | 0 / 111.9 |

`E` and `D` are the binary and decimal scale factors. The precise problematic
increment is message 14 minus message 13:

| Field | shortName/name | stepType/range | start/end | forecastTime | valid UTC | units | packing | bits | reference | E/D | quantum |
|---|---|---|---|---:|---|---|---|---:|---:|---|---:|
| minuend | tp / Total Precipitation | accum / 36-42 | 36/42 | 36 | 2019-07-23 18:00 | kg m**-2 | complex spatial differencing, template 5.3, order 2 | 10 | 0 | 1/1 | 0.2 mm |
| subtrahend | tp / Total Precipitation | accum / 36-39 | 36/39 | 36 | 2019-07-23 15:00 | kg m**-2 | complex spatial differencing, template 5.3, order 2 | 11 | 0 | 0/1 | 0.1 mm |

## Exact affected cells

| Latitude | Longitude | p01 36-39 | p01 36-42 | increment | c00 | p02 | p03 | p04 |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 16.25 | 76.50 | 0.4 | 0.2 | -0.2 | 6.1 | 9.1 | 11.3 | 24.4 |
| 21.00 | 70.75 | 3.2 | 3.0 | -0.2 | 0.0 | 0.0 | 0.0 | 0.8 |

The comparison-member columns are their own +39-to-+42 increments and are
diagnostic only. No member was used as a replacement. The machine record gives
the full 3 x 3 p01 neighbourhood around each cell. Neighbours include several
-0.1 mm residues, but no additional target-domain value below -0.1 mm. Across
the global grid, 300 cells are below -0.1 mm and the minimum is -0.2 mm, which
confirms a field-wide representation/source phenomenon rather than an indexing
error at the two India-domain cells.

Neighbour entries below are `36-39 → 36-42 (increment)` in mm:

| Near 16.25N, 76.50E | 76.25E | 76.50E | 76.75E |
|---|---|---|---|
| 16.00N | 0.0→0.0 (0.0) | 0.0→0.0 (0.0) | 0.4→0.4 (0.0) |
| 16.25N | 0.0→0.0 (0.0) | 0.4→0.2 (-0.2) | 1.4→1.4 (0.0) |
| 16.50N | 0.2→0.2 (0.0) | 1.1→1.0 (-0.1) | 2.8→3.0 (+0.2) |

| Near 21.00N, 70.75E | 70.50E | 70.75E | 71.00E |
|---|---|---|---|
| 20.75N | 6.4→6.8 (+0.4) | 1.4→1.4 (0.0) | 0.1→0.0 (-0.1) |
| 21.00N | 7.1→7.2 (+0.1) | 3.2→3.0 (-0.2) | 1.1→1.2 (+0.1) |
| 21.25N | 13.1→13.2 (+0.1) | 11.5→11.4 (-0.1) | 7.5→8.0 (+0.5) |

## Quantization bound

For these GRIB messages the decoded spacing is
`q = 2^binaryScaleFactor * 10^-decimalScaleFactor`. With an exact zero
reference, the 36-39 field has `q1=0.1 mm` and maximum nearest-rounding error
`0.05 mm`; the 36-42 field has `q2=0.2 mm` and maximum error `0.10 mm`.
Independent quantization therefore permits at most `(q1+q2)/2 = 0.15 mm` error
in their difference. Even the error direction most favorable to a nonnegative
physical increment leaves an upper bound of `-0.05 mm` for a decoded `-0.2 mm`
increment. Thus packing changes can explain small negative increments in
principle, as ECMWF's ecCodes FAQ describes, but cannot mathematically explain
this magnitude for these actual scale factors. ecCodes 2.48 does not expose its
computed `packingError` key for these complex-packed messages, so the audit
derives the bound from the encoded factors rather than substituting a generic
floating-point epsilon. See the [ecCodes precipitation accumulation FAQ](https://confluence.ecmwf.int/display/UDOC/Why%2Bare%2Bthere%2Bsometimes%2Bsmall%2Bnegative%2Bprecipitation%2Baccumulations%2B-%2BecCodes%2BGRIB%2BFAQ).

## Independent archive reconstruction

The official cached NOAA index enumerates the precipitation representation in
the `apcp_sfc` object. It has 36-39 and 36-42 accumulations, but no direct 39-42
message. There is no second valid accumulation combination spanning exactly
39-42, and no alternate NOAA precipitation object was identified for this
member/cycle. Therefore an independent official cell-by-cell reconstruction is
not available. Interpolation, substitution, and estimation are prohibited.

## Root-cause decision and policy

The message identities and intervals are correct, hashes reproduce, ecCodes
decoding is deterministic, and other intervals reconstruct normally. This is
not evidence of a reconstruction or decoder bug. Because the decrement exceeds
the actual packing bound and the archive provides no independent representation,
the exact required status is `SOURCE_INCONSISTENCY`.

The two source values remain unchanged. The complete `p01/day2_24h` component
for this initialization stays quarantined; the operational cap stays 0.1 mm.
Only a residue inside both the message-specific packing bound and the 0.1 mm cap
may be normalized to zero, with an explicit quality flag.

## Documentation/code discrepancy corrected

Phase 1C described both relevant messages using their decimal 0.1 mm precision.
That omitted message 14's `binaryScaleFactor=1`: its effective decoded quantum
is 0.2 mm. The Phase 1C rejection remains correct, but its explanatory wording
was incomplete. This report and an append-only correction in the Phase 1C
report supersede that packing explanation without rewriting its evidence.

## Phase 1E strict seasonal replay correction

The original July pilot used the 0.1 mm operational cap as a blanket tolerance.
The frozen rule is narrower: a negative may be clamped only when it lies within
both the pair-specific half-quantum packing bound and 0.1 mm. Applied to all
2019 JJAS cases, the strict rule accepts 614/1,830 rainfall member-products and
quarantines 1,216. July is 137/465, not the historical 464/465 figure.

On 2019-07-22 Day 2, c00, p01, and p04 are invalid; the earlier statement that
c00 remains eligible is superseded. Source bytes remain valid and inspectable,
and no value was rewritten beyond the frozen rule.

## Phase 1F canonical-target interpretation

The preceding Phase 1E statement remains correct for frozen v1 method A. V2
does not require every synthetic three-hour interval. It uses native six-hour
blocks and only the boundary subtraction required by the target. Therefore the
p01 `+39→+42` anomaly remains an invalid diagnostic interval but does not enter
canonical Day 2; p01 Day 2 passes. The p04 method-A Day-2 failure is also in an
unused diagnostic interval and passes v2. c00 Day 2 remains invalid because its
required `+27→+30` boundary difference exceeds its packing bound. See docs 51
and 52. Historical source and v1 evidence above are unchanged.
