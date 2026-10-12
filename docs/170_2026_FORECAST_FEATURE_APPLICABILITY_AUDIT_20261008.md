# 2026 forecast-feature applicability audit — 8 October 2026

This is a **read-only, forecast-only diagnostic** of the already sealed JJAS
2026 feature-range report. It reads no rainfall reference value, prediction
array, model or GRIB message; it fits no model and does not alter the 2026
one-shot score gate. The existing regional M2 default and all frozen findings
remain unchanged.

## Reproducible population and result

`python scripts/audit_2026_feature_applicability.py` verifies the SHA-256
sidecars for `2026_jjas_feature_range_v1.json`
(`9a732c498d91071e1398fc6c6372313f957d90c1c11ef1f87b2b8fcbe7de504f`)
and `2026_forecast_jjas_year_v1.json`
(`fc0183682a84d864781170169b3b4365b4a92a0b09c8bfffffbf71f4a9108884`),
their cross-link, `observation_read: false`, and the admitted case totals.
The full feature-range report was separately recomputed from the sealed local
forecast-side sources and matched its stored JSON exactly. The range check
uses the 0.001–0.999 quantiles of the **2023 training matrix**. A warning is
one dynamic-feature/case-lead pair with more than 5% of its cells (or its
single area-summary value) outside that feature's training range.

| 2026 month | QC-admitted case-leads | Case-leads with ≥1 warning | Share | Feature/case warnings |
|---|---:|---:|---:|---:|
| June | 40 | 3 | 7.5% | 4 |
| July | 62 | 14 | 22.6% | 20 |
| August | 62 | 0 | 0% | 0 |
| September | 49 | 28 | 57.1% | 99 |
| **JJAS** | **213** | **45** | **21.1%** | **123** |

In September the most frequent warnings are `mslp_area_mean` (20),
`u850_area_mean` (16), `wind_speed_area_mean` (11) and `mslp_minimum` (10).
These are **counts of feature/case warnings**, not counts of distinct days or
proof of a failed forecast. Some area-summary warnings are 100% because a
single summary value lies outside the 2023 interval. The diagnostic does not
establish that September is meteorologically anomalous, that a GEFS software
change caused the shift, or that a correction fails on those cases. The
monthly populations differ, and training-range quantiles are not a calibrated
applicability test.

The 2026 forecast archive has 122 cycles but only 213 strict-QC Day 1–3
case-leads. This report uses exactly those admitted leads, not a selected
subset and not zero-filled missing leads. It cannot repair the 22 frozen
probability-incoherent leads or establish any 2026 rainfall skill.

## GEFS version evidence reviewed on 8 October

The [NWS GEFS 12.3.20 service notice](https://www.weather.gov/media/notification/pdf_2026/scn26-57_GEFS_Shortwave_radiation_fix.pdf)
states an intended 15 June 2026 12 UTC implementation and describes radiation
GRIB precision changes, with postponement possible. The
[NCO model-change history](https://www.nco.ncep.noaa.gov/pmb/changes/) reviewed
on 8 October contains no `12.3.20` entry in its public table. An
[EMC verification page](https://www.emc.ncep.noaa.gov/users/verification/global/gefs/para/main.php)
states the broad GEFS 12.3 family was operational by 19 October 2022, but
does not identify the exact executable patch used for each 2023 training
cycle. These web pages are **bibliographic review**, not newly downloaded,
byte-hashed production logs. The previously sealed DSWRF GRIB packing
boundary (`docs/158`–`docs/159`) remains corroborating output metadata,
not executable identity or selected-predictor equivalence.

The warning concentration in September, rather than at the announced June
boundary, does not establish a software cause. Seasonal distribution, spatial
sampling, strict-QC admission and source-version differences are confounded.
The four `docs/159` gates remain open: complete authorized annual IMD 2026
reference, actual 2026 GEFS deployment identity, exact 2023 training patch,
and selected-predictor comparability. Neither clearance manifest is created;
`score_2026_frozen_inference.py --preflight` must remain blocked before
observation access.

## Checks and change scope

- Stored forecast-only feature-range JSON reproduced exactly from its sealed
  local source population; 213 leads, 123 warnings, zero observation reads.
- `python scripts/audit_2026_feature_applicability.py`: exit 0; printed the
  monthly denominators and counts above without writing an artifact.
- `python -m pytest backend/tests/test_2026_feature_applicability_audit.py -q
  --basetemp=data/pytest-2026-feature-applicability -p no:cacheprovider`:
  **3 passed**. Tests reject a corrupt receipt, an observation-derived flag,
  and a warning outside the admitted year even if its receipt is recomputed.
- Final full backend
  `python -m pytest backend/tests -q
  --basetemp=data/pytest-feature-applicability-final-20261008
  -p no:cacheprovider --durations=5`: **840 passed**, exit 0 in 148.74 s.
- `python scripts/probe_2026_source_clearance.py --check`: exit 0 with
  `OPEN_NO_CLEARANCE` and the same four blockers. Frozen scorer `--preflight`:
  exit 0 with `BLOCKED_BEFORE_OBSERVATION_READ`, 213 cases.
- Files added: `scripts/audit_2026_feature_applicability.py`,
  `backend/tests/test_2026_feature_applicability_audit.py`, this document.
  No frozen manifest, forecast, score or product file changed.
