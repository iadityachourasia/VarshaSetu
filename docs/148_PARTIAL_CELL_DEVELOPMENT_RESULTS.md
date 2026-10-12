# Partial-cell accumulation: development and validation result

Date: 2026-10-07. This is a **Track B operational-GEFS development study**, not
an independent-year test or an operational product. The protocol was sealed in
`data/manifests/research_pilot/partial_cell_development_protocol_v1.json`
before this partial-cell pairing with IMD observations. The write-once result
and SHA-256 sidecar are `partial_cell_development_result_v1.json/.sha256`.

## Question and controls

The canonical 24-hour minimum-subtraction rule refuses an entire 49×49 lead
when any packed precipitation difference is materially negative. The
experimental rule marks only those cells NaN. It uses the same exact temporal
decomposition and preserves the canonical rainfall array **bit for bit** on
every strict-pass case. It never changes the live worker, model input or
district API. Its values were compared with locally held, hash-verified IMD
0.25-degree 03–03 UTC daily rainfall on the matching valid date; missing
forecast or reference cells were excluded from all scores.

June 2023 was the design/development set and June 2024 the development
validation set. Both years have been used in earlier project research. The
2025 consumed test and 2026 independent-test candidate were excluded.

| Measure | June 2023 | June 2024 | Combined |
|---|---:|---:|---:|
| Date/lead cases | 90 | 90 | 180 |
| Strict-pass leads | 49 | 35 | 84 |
| Strict-withheld leads | 41 | 55 | 96 |
| Leads retaining ≥99% regional cells under mask | 90 | 90 | 180 |
| Minimum regional valid fraction | 99.25% | 99.25% | 99.25% |
| District-by-lead values below 95% weighted area coverage | 124 | 218 | 342 |
| Leads with at least one such district | 36 | 55 | 91 |
| IMD-valid cells excluded by mask | 137 | 267 | 404 |
| IMD heavy-rain events in excluded cells (≥64.5 mm/24 h) | 0 | 1 | 1 |
| IMD very-heavy events in excluded cells (≥115.6 mm/24 h) | 0 | 0 | 0 |

The 342 unsupported district values are out of 33,840 possible
district-by-lead values (188 districts × 180 leads). The worst district area
coverage on a lead was **21.3%**, despite that lead's high regional coverage.
The missing-cell event counts are small and descriptive; they cannot prove
missingness is meteorologically random. The invalid cells and the 95% rule
must remain visible in any later product.

The result also stores paired raw-GEFS error sums and heavy/very-heavy
contingency counts for every case. On the 2024 strict-withheld stratum, raw
rainfall had 71,288 jointly valid cells, RMSE 14.887 mm and mean bias
−0.422 mm. These describe cases previously unavailable to the strict
whole-grid product. They are **not** a same-case skill improvement over a
strict forecast, because that forecast has no value on those leads. No
corrected-model or calibrated-probability inference was run in this study.

## Decision

The diagnostic supports pursuing a **versioned partial-grid inference path**.
It does not promote the mask into the current worker. Before that path can
publish a grid or district value, it needs a frozen full-pipeline protocol,
finite/nonnegative predictions only on supported cells, explicit NaN and
coverage metadata, suppression of districts below 95% weighted coverage,
same-case raw/global/regime comparisons, and later independent-year
verification. The strict product remains the default.

Reproduce the core evidence checks with
`python -m pytest backend/tests/test_partial_cell_development.py -q`.
The full backend suite passed 741 tests on 7 October 2026 using the local
pytest temp directory (`--basetemp=data/pytest-partial-firstfail
-p no:cacheprovider`), with one Starlette dependency deprecation warning.
The result SHA-256 sidecar and `git diff --check` also verified.
