# Nationwide probability warning-map spatial diagnostic — 9 October 2026

## Decision and evidence role

This is a **consumed-2024 development diagnostic** of the frozen v1, v2 and v4
nationwide probability forecasts. It measures the fractions skill score (FSS)
of thresholded warning maps. It is **not** a probability calibration score, a
new model-selection experiment, independent validation, or a public warning
rule. The v4 very-heavy Brier comparison failed its prespecified gate in
`docs/176`; that decision and the regional M2 corrected-rainfall product
default remain unchanged. No 2025 or 2026 observation values were read.

The write-once protocol is
`data/manifests/research_pilot/nationwide_probability_spatial_protocol_v1.json`
(SHA-256 `9390d22ba23a2016ff1eed789bbaaedb52de33d0ef2dd4a631b14fd9bed63874`).
It was frozen before this diagnostic's observation pairing and pins the
runner/math code, source seals and hashes, cases, thresholds, mask, spatial
rule and uncertainty method. Earlier v1/v2 studies had already consumed 2024;
the freeze is not a claim of project-wide independence. The result is
`data/manifests/research_pilot/nationwide_probability_spatial_result_v1.json`
(SHA-256 `70ea925125f4ac0e5e99a60d4b5ee65645ef5ec8e283781302add505b70e6adc`).
Both have companion `.sha256` receipts.

## Spatial method

The diagnostic reconstructs aligned 129 × 135 forecast and IMD reference
fields on the identical reference-valid forecast cells for all three arms.
The 24-hour observed thresholds are ≥64.5 mm (heavy) and ≥115.6 mm (very
heavy). The forecast is a binary warning at the previously fixed **common
probability cutoff 0.05**. This cutoff is a fair same-cutoff comparator from
the frozen v4 score, not a newly optimized or recommended display threshold.
It differs from v4's own nested development cutoffs of 0.17 and 0.14.

At each 1 × 1, 3 × 3 and 5 × 5 cell neighborhood, FSS is one minus the sum
of squared forecast-minus-observed event fractions divided by the sum of
their squared fractions. Neighborhoods require at least 50% valid in-domain
cells; missing reference or forecast cells never become zero rain. Convolution
uses zero padding outside the grid, and invalid centers are excluded. The
numerator and denominator are summed across cases before their ratio is taken.
A zero denominator is undefined for that case, although such cases remain in
the identical 156-case population. The 1-cell contingency counts exactly
reproduce the frozen common-0.05 score.

There are 156 cases on 102 initialization dates and 760,812 paired cells at
the 1-cell scale. Eligible centers are 760,812, 756,132 and 747,084 at the
three scales, identical across arms. Observed events are 13,320 heavy and
3,017 very heavy. The 95% intervals below use 1,000 paired resamples of
initialization dates; they do not remove spatial or serial dependence.

| Head | Neighborhood | v1 FSS | v2 FSS | v4 FSS | v4 − v1, 95% date interval | v4 − v2, 95% date interval |
|---|---:|---:|---:|---:|---:|---:|
| Heavy | 1 × 1 | 0.1752 | 0.1714 | 0.1796 | +0.0043 [−0.0030, +0.0111] | +0.0082 [−0.0027, +0.0184] |
| Heavy | 3 × 3 | 0.2209 | 0.2079 | 0.2248 | +0.0039 [−0.0074, +0.0147] | +0.0169 [+0.0019, +0.0309] |
| Heavy | 5 × 5 | 0.2390 | 0.2215 | 0.2428 | +0.0038 [−0.0101, +0.0165] | +0.0213 [+0.0046, +0.0378] |
| Very heavy | 1 × 1 | 0.1291 | 0.0000 | 0.1251 | −0.0040 [−0.0206, +0.0126] | +0.1251 [+0.1023, +0.1509] |
| Very heavy | 3 × 3 | 0.1815 | 0.0000 | 0.1646 | −0.0169 [−0.0420, +0.0061] | +0.1646 [+0.1340, +0.1978] |
| Very heavy | 5 × 5 | 0.2072 | 0.0000 | 0.1827 | −0.0245 [−0.0565, +0.0018] | +0.1827 [+0.1482, +0.2217] |

At 3 × 3 cells, the heavy Day 1/2/3 FSS values are v1
0.2310/0.2371/0.2016, v2 0.2457/0.2372/0.1714, and v4
0.2716/0.2299/0.1964. The very-heavy values are v1
0.1591/0.2183/0.1650, v2 0/0/0, and v4
0.1607/0.1831/0.1515. Thus a pooled heavy difference must not be
read as an across-lead gain.

At 0.05, heavy warning counts are v1 84,252, v2 74,989 and v4 79,943,
versus 13,320 observed events. Very-heavy counts are v1 12,445, v2 **zero**
and v4 19,399, versus 3,017 observed events. V2's zero very-heavy FSS is a
consequence of issuing no warnings at this common cutoff, not evidence of
calibration success. V4's high very-heavy warning frequency remains a major
false-alarm concern. Contributing nonzero-denominator cases at 1 cell are
154/153/153 (heavy v1/v2/v4) and 146/131/142 (very-heavy v1/v2/v4).

V4-minus-v1 intervals cross zero at every spatial scale for both heads;
the point estimates for very-heavy are lower than v1. This diagnostic does
not rescue the failed Brier gate or justify any model or threshold promotion.

## Reproduction and remaining work

`python scripts/score_nationwide_probability_spatial.py check` verifies
receipts and source hashes. `deep` additionally recomputes every spatial
field and the exact result JSON; it returned exit 0 with
`WARNING_FSS_REPRODUCED`. Pure-function and runner tests cover aligned fields,
valid masks, undefined no-event cases, 1-cell contingency equivalence and
paired date bootstrap.

| Check | Result |
|---|---|
| Focused spatial tests | 4 passed, exit 0 |
| Spatial protocol/result deep recomputation | Passed, exit 0; both receipt hashes reproduced |
| `python scripts/score_nationwide_probability_spatial.py check` | Exit 0, `WARNING_FSS_HASH_VERIFIED` |
| `python scripts/nationwide_probability_v4.py check` | Exit 0, protocol, 156 predictions and score hash verified |
| Full backend suite, `python -m pytest backend/tests -q --basetemp=data/pytest-probability-spatial-full-20261009 -p no:cacheprovider --durations=5`, with the known Windows socket-enabled setup | **874 passed**, exit 0, 107.50 s |
| `python scripts/score_2026_with_clearance_gate_v2.py --preflight` | Exit 0, `BLOCKED_BEFORE_OBSERVATION_READ`, 213 forecast cases, no score |
| `git diff --check` | Exit 0; existing Windows line-ending notices only |

Final free C: space was 178.19 GiB, above the 50 GiB floor. No artifact was
committed. This increment added `backend/app/ml/probability_spatial.py`,
`backend/tests/test_probability_spatial.py`,
`backend/tests/test_probability_spatial_runner.py`,
`scripts/score_nationwide_probability_spatial.py`, this report and the four
write-once protocol/result JSON and checksum files. It updated
`docs/00_INDEX.md` and added a pointer in `docs/176`. It did not alter
frozen v1/v2/v4 forecasts, scores, 2026 forecasts or product APIs.

An independent, comparable reference year and source-version clearance are
still needed for national skill claims. Very-heavy Brier/reliability and
warning-frequency gates need independently supported improvement. The
spatial metric is useful verification evidence, but cannot replace Brier,
reliability, event frequency, or region/lead support checks.
