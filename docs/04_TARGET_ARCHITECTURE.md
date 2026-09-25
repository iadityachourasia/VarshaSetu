# Target Architecture

## Design objective

Transform the current point-record historical prototype into a scientifically traceable, regime-aware NWP post-processing system without unnecessary rewrites.

## Target end-to-end flow

```text
Authoritative Forecast Source
(GEFS/GFS fallback; NCMRWF data when provided)
                │
                ▼
       Forecast Data Adapter
 GRIB2/NetCDF/Zarr + metadata
                │
        ┌───────┴────────┐
        │                │
        ▼                ▼
 Dynamic NWP fields   Static geospatial
 rain, U/V, RH,       DEM, slope/aspect,
 MSLP, TCWV,          coastline distance,
 geopotential,        district polygons
 ensemble stats
        │                │
        └───────┬────────┘
                ▼
        Temporal/Spatial Alignment
 forecast init / lead / valid time
 common observation grid
                │
                ▼
       Forecast-Time Feature Engine
        │        │        │
        ▼        ▼        ▼
 moisture    vorticity   terrain/upslope
 forcing     proxies     forcing
                │
                ▼
      Hierarchical Regime Engine
                │
      probabilistic regime state
                │
                ▼
       Soft Mixture-of-Experts
        ┌────────┼────────┐
        ▼        ▼        ▼
      active    break   synoptic/
      expert    expert  terrain expert
        └────────┼────────┘
                ▼
       Corrected rainfall grid
                │
      ┌─────────┴─────────┐
      ▼                   ▼
24h accumulation      probabilistic/
& point estimate      extreme-rain head
      │                   │
      └─────────┬─────────┘
                ▼
       Calibration / Uncertainty
                │
                ▼
        District Aggregation
 mean / max / p90 / affected area
                │
                ▼
        Verification Engine
 RMSE, ETS, CSI, POD, FAR, FSS
 + reliability/Brier recommended
                │
                ▼
              FastAPI
                │
                ▼
        VarshaSetu Dashboard
```

## Architectural layers

### Layer 1 — Forecast source abstraction

A forecast record/grid must carry:
- model source,
- model/version,
- initialization time,
- valid time,
- lead hours,
- accumulation interval,
- variable,
- level,
- units,
- grid definition.

The ML pipeline must not depend on one specific provider.

### Layer 2 — Scientific data processing

Use scientific array tooling for:
- GRIB/NetCDF ingest,
- unit normalization,
- temporal accumulation,
- regridding,
- masking,
- static field joining,
- observation pairing.

Recommended:
- xarray,
- cfgrib/eccodes,
- xESMF or a validated alternative,
- NumPy,
- Pandas,
- GeoPandas,
- Rasterio,
- optional Zarr.

### Layer 3 — Regime inference

Target design:
- probabilistic,
- hierarchical/multi-label where appropriate,
- trained/validated against reproducible labels,
- driven by forecast-time atmospheric state.

Possible heads:
- monsoon state: active / break / neutral,
- synoptic driver: low/depression / other / WD where domain supports it,
- spatial forcing: coastal/orographic influence.

Do not force overlapping physical concepts into one exclusive class merely for convenience.

### Layer 4 — Post-processing models

Required baselines:
- raw NWP,
- MOS,
- global ML.

Target:
- probabilistic soft regime Mixture-of-Experts.

The MoE should be justified by held-out improvement, not by architecture novelty alone.

### Layer 5 — Extreme rainfall

Produce:
- heavy exceedance probability,
- very-heavy exceedance probability,
- correct accumulation period,
- calibrated reliability assessment,
- explicit insufficient-sample state.

### Layer 6 — Spatial/district product

Generate:
- gridded corrected rainfall,
- probability grids,
- district polygons,
- area-weighted aggregation,
- district-level decision variables.

Recommended district fields:
- mean rainfall,
- maximum grid rainfall,
- p90/p95,
- area fraction above heavy threshold,
- area fraction above very-heavy threshold,
- dominant/mixture regime,
- forecast uncertainty,
- lead time.

### Layer 7 — Verification

Mandatory:
- RMSE,
- ETS,
- CSI,
- POD,
- FAR,
- FSS.

Recommended:
- MAE,
- bias,
- frequency bias,
- Brier score,
- Brier skill score,
- reliability diagram,
- confidence intervals.

### Layer 8 — API/UI

The dashboard should render scientific outputs from typed API contracts.

The frontend must not generate scientific results itself.

## Storage architecture

### MVP
Prefer simple, inspectable formats:
- source GRIB/NetCDF,
- normalized NetCDF/Zarr,
- Parquet metadata/tabular evaluation,
- GeoJSON boundaries,
- JSON versioned experiment reports.

### Production
Add when justified:
- object storage for arrays,
- PostgreSQL/PostGIS for metadata/geospatial entities,
- model registry,
- workflow/job orchestration.

## Non-goals for early stages

Do not introduce:
- microservice sprawl,
- Kubernetes,
- distributed feature stores,
- unnecessary vector databases,
- LLM components,
until core PS compliance and scientific validity are proven.
