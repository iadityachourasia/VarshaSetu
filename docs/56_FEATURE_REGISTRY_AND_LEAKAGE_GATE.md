# Feature Registry and Leakage Gate

## Policy

Every input is assigned one availability class: `STATIC`, `FORECAST_TIME`,
`DERIVED_FORECAST_TIME`, `OBSERVATION_TARGET`, or
`FORBIDDEN_FOR_INFERENCE`. The executable registry is
`backend/app/ml/forecast_regimes.py::FEATURE_REGISTRY`; its versioned artifact
is written by the Phase 2A regime build.

The regime classifier admits only `FORECAST_TIME` and
`DERIVED_FORECAST_TIME`. Feature order is exact and validated. Unknown,
missing, reordered, target-like, or observation-derived fields fail closed.

## Registry

| Input | Availability | Regime input | Status / source |
|---|---|---:|---|
| U850 | FORECAST_TIME | yes | GEFS c00 at +24/+48/+72 |
| V850 | FORECAST_TIME | yes | GEFS c00 at +24/+48/+72 |
| Q700 | FORECAST_TIME | yes | GEFS c00 at +24/+48/+72 |
| Z500 | FORECAST_TIME | yes | GEFS c00 at +24/+48/+72 |
| MSLP | FORECAST_TIME | yes | GEFS c00 at +24/+48/+72 |
| PWAT | FORECAST_TIME | yes | GEFS c00 at +24/+48/+72 |
| PWAT area mean | DERIVED_FORECAST_TIME | yes | Context-grid calculation |
| Q700 area mean | DERIVED_FORECAST_TIME | yes | Context-grid calculation |
| U850/V850 area means | DERIVED_FORECAST_TIME | yes | Context-grid calculation |
| Wind-speed area mean | DERIVED_FORECAST_TIME | yes | From forecast U850/V850 |
| Moisture-transport area mean | DERIVED_FORECAST_TIME | yes | Forecast PWAT times wind speed |
| MSLP mean/minimum/range | DERIVED_FORECAST_TIME | yes | Forecast MSLP only |
| Z500 area mean | DERIVED_FORECAST_TIME | yes | Forecast Z500 only |
| Vorticity mean/p90 | DERIVED_FORECAST_TIME | yes | Forecast U850/V850 only |
| Latitude/longitude | STATIC | no for regime prototype | Existing grid coordinates |
| Elevation | STATIC | no | Interface placeholder; authoritative source required |
| Terrain gradient | STATIC | no | Interface placeholder; authoritative source required |
| Distance to coast | STATIC | no | Interface placeholder; authoritative source required |
| District membership | STATIC | no | Interface placeholder; authoritative polygons required |
| IMD observed rainfall | OBSERVATION_TARGET | no | Verification/target only |
| Future observed temperature | FORBIDDEN_FOR_INFERENCE | no | Future information |
| Future observed humidity | FORBIDDEN_FOR_INFERENCE | no | Future information |

No static geography value is fabricated. Latitude and longitude already exist
as coordinates, but Phase 2A does not add them to the large-scale regime vector.

## Temporal leakage gate

Phase 2A enforces 2017 training, 2018 validation, and 2019 held-out test roles.
All three product cases from a forecast initialization stay in the same annual
split. Normalizers, climatological statistics, score percentiles, rule
thresholds, logistic coefficients, and model-selection decisions use 2017
only. The regime build has no 2019 data input and records
`held_out_test_accessed: false`.

The gate does not authorize scientific APIs or rainfall-model training.

