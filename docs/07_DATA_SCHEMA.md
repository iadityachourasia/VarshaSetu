# Data Schema

## 1. Current checked-in prototype schema

The audited CSV contains the following fields.

| Field | Role | Current interpretation | Operational inference safe? |
|---|---|---|---|
| `location_id` | ID | point location | Yes |
| `time` | time | timestamp | Yes |
| `date` | time | display date | Yes |
| `time_ist` | time | IST display | Yes |
| `hour_ist` | time | 6-hour period | Yes |
| `district_name` | geo | district label | Yes |
| `taluka_name` | geo | taluka label | Yes |
| `district_code` | geo | district code | Yes |
| `latitude` | static | latitude | Yes |
| `longitude` | static | longitude | Yes |
| `elevation (m)` | static | elevation | Yes |
| `temperature_2m (...)` | dynamic | source unclear | **Unverified** |
| `rain_6h_accum (mm)` | target | observed/reference rainfall | **No — target** |
| `dew_point_2m (...)` | dynamic | source unclear | **Unverified** |
| `relative_humidity_2m (%)` | dynamic | source unclear | **Unverified** |
| `pressure_msl (hPa)` | dynamic | source unclear | **Unverified** |
| `surface_pressure (hPa)` | dynamic | source unclear | **Unverified** |
| `cloud_cover (%)` | dynamic | source unclear | **Unverified** |
| `wind_direction_10m (...)` | dynamic | source unclear | **Unverified** |
| `wind_speed_10m (km/h)` | dynamic | source unclear | **Unverified** |
| `boundary_layer_height (m)` | dynamic | source unclear | **Unverified** |
| `total_column_integrated_water_vapour (...)` | dynamic | source unclear | **Unverified** |
| `raw_nwp_rain_6h_forecast (mm)` | forecast? | claimed raw NWP rain | **Unverified provenance** |
| `raw_nwp_temp_forecast (...)` | forecast? | claimed NWP temp | **Unverified provenance** |
| `raw_nwp_pressure_msl_forecast (hPa)` | forecast? | claimed NWP pressure | **Unverified provenance** |
| `raw_nwp_wind_speed_forecast (km/h)` | forecast? | claimed NWP wind | **Unverified provenance** |

The saved experiment additionally expects `regime_id`.

## 2. Problem with current semantic schema

The name of a field does not prove:
- source,
- forecast initialization,
- valid time,
- lead,
- whether it is observed or forecast,
- whether it was generated synthetically.

Therefore the target schema must encode these concepts explicitly.

## 3. Target forecast sample schema

Recommended tabular index:

```text
forecast_source
model_version
init_time_utc
valid_time_utc
lead_hours
accumulation_hours
grid_y/grid_x OR lat/lon
```

Example canonical fields:

| Canonical field | Unit | Type |
|---|---|---|
| `nwp_precip_accum` | mm | forecast |
| `nwp_u850` | m/s | forecast |
| `nwp_v850` | m/s | forecast |
| `nwp_q700` | kg/kg | forecast |
| `nwp_mslp` | hPa | forecast |
| `nwp_tcwv` | kg/m² | forecast |
| `nwp_z500` | m²/s² or converted | forecast |
| `nwp_ensemble_mean_precip` | mm | forecast |
| `nwp_ensemble_spread_precip` | mm | forecast |
| `elevation` | m | static |
| `terrain_gradient_x/y` | ratio | static |
| `coast_distance` | km | static |
| `obs_precip_accum` | mm | target/reference |

## 4. Target regime schema

Prefer probabilities plus explicit labels:

```json
{
  "monsoon_state": {
    "active": 0.62,
    "break": 0.08,
    "neutral": 0.30
  },
  "synoptic_driver": {
    "low_or_depression": 0.41,
    "western_disturbance": 0.01,
    "other": 0.58
  },
  "forcing": {
    "orographic": 0.75,
    "coastal": 0.52
  }
}
```

This is a target design, not current implementation.

## 5. Target prediction schema

Per grid cell:

```json
{
  "raw_nwp_rain_mm": 42.1,
  "corrected_rain_mm": 51.7,
  "correction_mm": 9.6,
  "p_heavy_24h": 0.28,
  "p_very_heavy_24h": 0.06,
  "uncertainty": {
    "p10": 31.0,
    "p50": 51.7,
    "p90": 86.0
  }
}
```

Only include uncertainty quantiles once truly implemented.

## 6. Feature safety metadata

Every feature definition should carry:

```text
feature_name
source_dataset
source_variable
forecast_or_static
available_at_issue_time
transformation
units
missing_data_policy
```

Add an automated guard that rejects any dynamic feature not marked `available_at_issue_time=true` for operational inference.

## 7. Phase 1A canonical contracts

The executable core contracts are in `backend/app/data/contracts.py`; the full
field definitions are in `32_FORECAST_DATA_CONTRACT.md` and
`33_OBSERVATION_DATA_CONTRACT.md`.

Forecast timing is keyed by timezone-aware UTC initialization and valid time.
`lead_hours` must equal their exact difference. Accumulated variables additionally
require start, end, and positive duration, with rainfall end equal to valid time.
Operational dynamic fields must declare `available_at_issue_time=true`.

The canonical IMD-aligned rainfall products from a 00 UTC GEFS initialization are:

| Product | Accumulation start lead | Accumulation end lead | Duration |
|---|---:|---:|---:|
| `day1_24h` | +3 h | +27 h | 24 h |
| `day2_24h` | +27 h | +51 h | 24 h |
| `day3_24h` | +51 h | +75 h | 24 h |

The observation window ends at 03:00 UTC/08:30 IST on `valid_date`. A date label
without explicit window timestamps is insufficient for pairing.

### FSS-ready paired array schema

```text
forecast_rain_mm[init_time, product, member, y, x]
observation_rain_mm[init_time, product, y, x]
valid_mask[init_time, product, y, x]
latitude[y]
longitude[x]
```

Required coordinates/attributes include valid time, accumulation start/end,
start/end lead, target-grid ID, member, source-manifest IDs, and regridding-weight
hash. Flattened point rows are a derived view, not the authoritative FSS store.

### Grid V1

- target: IMD 0.25° rectilinear valid-cell grid within 10–22°N, 68–80°E;
- regime context: 0.5° grid within 5–30°N, 55–95°E;
- rainfall regridding: first-order conservative with cell bounds and masks;
- continuous atmospheric regridding: bilinear;
- categorical/static masks: nearest-neighbour.

These bounds and methods are versioned design decisions. Phase 1B validated the
rainfall grid, mask, and first-order conservative path for one co-located GEFS/
IMD day only; see `36_ONE_WINDOW_PILOT_REPORT.md` and
`37_REGRIDDING_AND_ALIGNMENT_SPEC.md`. Multi-date and atmospheric-field
validation remain outstanding.
