# API Contract

## Principles

- Scientific values originate in backend services.
- Responses must carry metadata needed to interpret forecasts.
- Frontend must not reconstruct scientific values by multiplying or guessing.
- Pydantic response models are recommended for all production endpoints.

## Current API

The audited backend exposes report/metrics, historical forecast lookup, provenance-like output, audit/Jury Defense content, and sandbox inference.

Some names/semantics are stale and should be normalized.

## Target API version

Use an `/api/v1` namespace when refactoring is justified.

---

# Core entities

## ForecastRun

```json
{
  "run_id": "string",
  "source": "GEFS",
  "model_version": "string",
  "init_time_utc": "2026-07-15T00:00:00Z",
  "available_leads_hours": [24, 48, 72],
  "domain": "goa",
  "data_status": "complete"
}
```

## RegimeState

```json
{
  "run_id": "...",
  "lead_hours": 24,
  "monsoon_state": {
    "active": 0.62,
    "break": 0.11,
    "neutral": 0.27
  },
  "synoptic_driver": {
    "low_or_depression": 0.34,
    "other": 0.66
  },
  "method_version": "..."
}
```

Only expose categories actually implemented.

## GridForecastMetadata

Avoid returning giant grids as nested JSON for production.

Return:
- tile/raster endpoint,
- object URI,
- compact binary format,
or use a dedicated grid subset API.

---

# Recommended endpoints

## `GET /api/v1/forecast-runs`

List available forecast/hindcast runs.

## `GET /api/v1/forecast-runs/{run_id}`

Run metadata.

## `GET /api/v1/forecast-runs/{run_id}/regime?lead_hours=24`

Regime probabilities.

## `GET /api/v1/forecast-runs/{run_id}/districts?lead_hours=24`

Example:

```json
{
  "thresholds": {
    "heavy_24h_mm": 64.5,
    "very_heavy_24h_mm": 115.6
  },
  "districts": [
    {
      "district_id": "...",
      "district_name": "...",
      "raw_mean_mm": 42.0,
      "corrected_mean_mm": 49.2,
      "corrected_max_mm": 118.0,
      "p90_mm": 83.4,
      "area_fraction_heavy": 0.22,
      "area_fraction_very_heavy": 0.03
    }
  ]
}
```

## `GET /api/v1/verification/experiments`

List immutable experiment reports.

## `GET /api/v1/verification/experiments/{id}`

Return full verification report.

## `GET /api/v1/verification/experiments/{id}/fss`

Return FSS matrix/curves.

## `GET /api/v1/historical-replay`

Inputs:
- run,
- valid time,
- lead,
- location/district.

Returns:
- raw,
- corrected,
- observation,
- errors,
- regime state.

## `POST /api/v1/sandbox/predict`

Keep only for controlled technical exploration.

Must:
- validate units/ranges,
- mark manual-input predictions as sandbox,
- not label them operational.

---

# Required response metadata

Every scientific prediction should carry as applicable:
- model ID/version,
- data source,
- initialization,
- valid time,
- lead,
- accumulation period,
- grid/resolution,
- threshold definitions,
- regime-model version.

---

# Error semantics

Use clear errors:
- `400`: invalid scientific request.
- `404`: run/case not found.
- `409`: requested data not generated/available.
- `422`: validation.
- `503`: upstream forecast data unavailable.

Never silently substitute another run/time.

---

# Deprecations to address

- Normalize stale year-key naming in metrics endpoints.
- Remove hardcoded “audit” claims or make them actual executable checks.
- Ensure `/provenance` reports source manifests, not just one CSV checksum.
# Phase 2C append-only scientific API supersession

The legacy scientific routes described in this document remain historically
blocked; they are not revived. A distinct read-only `/api/science` historical
prototype API is now documented in `docs/66_PHASE2C_SCIENTIFIC_API.md`. Its
`prototype_scientific_ready` state applies only to frozen 2019 demonstration
artifacts and does not supersede legacy dataset readiness or imply operations.
