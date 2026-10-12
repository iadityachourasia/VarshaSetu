# 2023–2026 common-footprint feature comparison — 8 October 2026

This is an **exploratory forecast-feature distribution diagnostic**, not a
GEFS version clearance, independent skill test, rainfall verification, model
selection or public product. It reads no 2026 observation value or rainfall
target and does not fit or promote a model. Regional M2 remains default.

## Protocol and population

The 2023 training feature matrix has a fixed set of 1,301 grid pixels per
case. The sealed 2026 forecast arrays have 2,401 cells per lead. The study
restricts every 2026 array to the exact ordered 2023 pixel indices, then
compares **all 19 dynamic features** in the same initialization month and
Day 1/2/3 lead. Latitude, longitude and lead fields are used for alignment,
not distribution claims. All source-feature and forecast-case hashes are
verified. The 2026 forecast-year seal is reproduced from local receipts.

The v1 protocol (SHA-256
`bd50eac26610ebc576025ffe42217fccd18d9275267f69af2b5df7c0808784fd`)
was superseded **before any distribution result was computed** because its
case-rule wording did not fully disclose that the existing 2023 training
corpus inherits historical forecast/reference admission. The v2 addendum
(SHA-256 `d97c20975230cad5a666568ca7b7f47ee626d30893166be125693f29d495c7fc`)
records this selection difference, the already inspected 2026 range-warning
counts and a one-case static-grid smoke check. Neither protocol was edited
after receipt. The result used v2 and is explicitly exploratory.

The comparison includes **192** June–September 2023 training cases and **213**
strict-QC 2026 forecast leads in 12 month/lead strata. The eight October 2023
training cases are excluded. The years are **not matched by date, weather
event, or admission process**. No 2026 outcomes or observed rainfall enter
the case selection. Source cases and the full-grid versus regional footprint
are never silently treated as equal.

## Results and limits

For each month/lead/feature the write-once result reports 2023 and 2026
cell-value p01, median and p99, median difference, and the share of 2026
values outside that 2023 stratum's p0.1–p99.9 interval. The result is
`2026_feature_comparability_result_v1.json` (SHA-256
`202f153ec16c75ef44375dbac4d8aefa2f4eef6156a3b411f84cde84a9891a80`).
These quantiles are descriptive; cells and dates are dependent, and no
confidence interval or version hypothesis test is claimed.

| Direct forecast field | Forecast-cell share outside same-month/lead 2023 interval, pooled over 2026 leads |
|---|---:|
| Raw c00 rainfall | 0.23% |
| U850 | 0.27% |
| V850 | 1.00% |
| Q700 | 4.67% |
| Z500 | 10.85% |
| Mean sea-level pressure | 5.28% |
| Precipitable water | 3.01% |

The area-summary features have much larger outside fractions: `pwat_area_mean`
44.13%, `q700_area_mean` 40.38%, `z500_area_mean` 24.88%, and
`mslp_area_mean` 20.19%. An area summary is one value repeated across the
1,301 pixels in a case; its fraction is effectively a **case frequency** and
must not be interpreted like a pixel-field fraction. The smallest 2023
month/lead stratum has only nine cases, so its extreme range is unstable.

September shows the strongest direct-field shift in these descriptive data:
Z500 outside fractions are 43.3%, 35.0% and 29.6% for Day 1–3; mean sea-level
pressure outside fractions are 18.3%, 20.9% and 20.8%. This does **not**
identify a software change. Different monsoon states, historical reference
admission, forecast QC, and any model-version change are confounded. The
forecast-only range audit in `docs/170` also reports September warnings, but
its all-season 2023 training interval and this month/lead interval answer
different descriptive questions.

The four `docs/159` source gates remain open. Actual cycle-specific 2026
GEFS deployment identity, the exact 2023 training executable patch and a
provider-supported selected-predictor processing review are still needed.
A numerical distribution comparison cannot replace those records or establish
equivalence. The complete authorized annual 2026 IMD reference remains
unavailable; the one-shot score remains blocked before observation access.

## Executed checks and files

- `python scripts/compare_2023_2026_forecast_features.py write`: exit 0;
  produced exactly 12 strata under the frozen v2 addendum, 192/213 cases,
  all 19 dynamic features, common 1,301-cell footprint and a new SHA receipt.
- `python scripts/compare_2023_2026_forecast_features.py check`: exit 0;
  recomputed the result from source receipts exactly, without overwrite.
- Focused `backend/tests/test_2026_feature_comparability.py`: **3 passed**
  after correcting an initially wrong test expectation at the 99.9th-percentile
  boundary; that first run failed 1/3 and is not counted as a pass.
- Combined feature-audit slice: **7 passed**. Final full backend
  `python -m pytest backend/tests -q
  --basetemp=data/pytest-common-footprint-final-20261008
  -p no:cacheprovider --durations=5`: **844 passed**, exit 0 in 393.17 s.
- Source gate `python scripts/probe_2026_source_clearance.py --check`:
  `OPEN_NO_CLEARANCE`, four blockers. Frozen scorer `--preflight`:
  `BLOCKED_BEFORE_OBSERVATION_READ`, 213 forecast cases and zero observation
  reads. Both exited 0 without creating a clearance manifest.
- Added `scripts/compare_2023_2026_forecast_features.py`, the focused test,
  the v1/v2 protocol JSON and sidecars, the result JSON and sidecar, and this
  document. Existing source, forecast, model and score artifacts were not
  modified. No 2026 observation was decoded or paired.
