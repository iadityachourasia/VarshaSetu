# API Contract

## Principles

- Scientific values originate in backend services.
- Responses must carry metadata needed to interpret forecasts.
- Frontend must not reconstruct scientific values by multiplying or guessing.
- Pydantic response models are recommended for all production endpoints.

## Experimental live-cycle status fields (October 2026)

`GET /api/science/live/field` returns `probability_status: null` for rainfall fields and `RESEARCH_ONLY_RELIABILITY_UNVERIFIED` for heavy/very-heavy probability fields. `GET /api/science/live/districts` returns the same research-only status for its probability columns. These fields describe verification status, not a computed probability. The read-only API continues to serve the frozen bundle values; no model or threshold is changed by the status label. The live UI defaults to M2 global correction, matching the district endpoint's M2 default.

The live field uses `schema_version: live_field_v2` and also returns
`source_track`, `model_id`, initialization UTC, lead hour, the exact +hour
accumulation window, an explicit finite-cell `valid_mask` and `valid_cells`,
`mask_policy`, and the verified bundle-manifest SHA-256. The district response
uses `schema_version: live_district_v2` and carries the same cycle/lead/window,
source/model, initialization, common finite-cell mask and manifest hash,
plus geometry and weight hashes. It returns a `weighted_grid_coverage_fraction` per
included row, `coverage_threshold_fraction: 0.95`, and a withheld-row count.
Coverage is relative to each research polygon's **represented regional grid
weight**, not to its full geographic area. A row below the threshold is omitted;
missing forecast cells are never treated as zero.

## Historical India-wide Raw map (October 2026)

`GET /api/science/evidence/all-india-raw/cases?year=2023|2024|2025` lists the frozen included control-member cases and local availability. `GET /api/science/evidence/all-india-raw/grid?year=&case_id=` returns one hash-verified 129×135 Raw GEFS 24-hour grid, a separate research-boundary display mask, frozen ledger/geometry hashes and the accumulation window. It never returns observed, corrected or probability values. A missing cache/bundle is unavailable; a hash mismatch is an integrity failure. See `docs/166` for the exact display and fallback contract.

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

## Local nationwide development research API (8 October 2026)

The original v1 probability arrays remain inspectable research fields, but
their head-fold and cutoff methodology failed a subsequent audit (`docs/168`).
`/overview` and probability `/grid` responses report
`RESEARCH_METHOD_AUDIT_FAILED_RELIABILITY_UNVALIDATED`; rainfall grid fields
have `probability_status: null`. This is a verification-status correction only:
the frozen arrays and scores remain unchanged. The separate v2 probability
repair candidate failed consumed-2024 development Brier comparisons and is not
served by this API.

`/api/science/research/nationwide` is disabled unless the local backend is
started with `VARSHASETU_LOCAL_NATIONWIDE_RESEARCH=1`. It reads hash-checked,
sealed 2024 development artifacts and exposes only these GET routes:

- `/overview`: model ladder, same-case national scores, regional guardrails,
  evidence hashes and explicit no-promotion status.
- `/cases`: 156 locally sealed 2024 historical cases and leads.
- `/verification?region=ALL_INDIA|INSIDE_MODEL_DOMAIN|EAST_AND_NORTH_EAST|EAST_COAST_PENINSULA|NORTH_OF_DOMAIN|SOUTH_OF_DOMAIN&lead_hours=0|24|48|72`:
  all five sealed same-case Raw/MOS/global/hard/soft arms, continuous RMSE and
  bias, heavy and very-heavy contingency counts and CSI/ETS/POD/FAR, aligned
  2-D FSS at 1/3/5-cell neighbourhoods, and date-block uncertainty/support.
  The typed response contains source/reference labels, protocol/score/
  uncertainty hashes and `independent_skill_claim: false`. It rejects a
  missing arm, mismatched paired-cell count, unsupported region or lead.
- `/grid?case_id=...&field=M0|M1|M2|M3|M4|heavy_p|very_heavy_p`:
  129 × 135 forecast field and explicit research land mask. Missing cells are
  JSON `null`, not zero. Probabilities are research-only.
- `/districts?case_id=...`: sampled-grid, research-geometry district means and
  coverage for the same sealed forecast case.

These routes do not read observations during request handling, do not expose
2026 cases, and do not replace the live regional product. Missing local
artifacts or a disabled flag return 404; a failed evidence hash/chain returns
503. `docs/167_NATIONWIDE_RESEARCH_PILOT_20261008.md` records the protocol,
results and unresolved promotion gates.
