# Deployment and Operations

## MVP principle

Deployment should not become the project.

For SIH, prioritize a reliable single-service backend plus frontend.

## Recommended MVP deployment

### Frontend
- static/Vite hosting.

### Backend
- one Python FastAPI service.

### Scientific files
- local persistent volume or object storage depending platform limits.

### Artifacts
- immutable model/report files with version IDs.

## Environment configuration

Move all environment-specific values out of source:
- data root,
- model root,
- allowed origins,
- object storage credentials,
- runtime mode.

Use `.env.example`, never commit secrets.

## Runtime modes

Recommended:
- `development`
- `demo`
- `production`

### Demo mode
May use cached historical cases.
Must not generate fake scientific values.

## Health endpoints

Expose:
- `/health/live`
- `/health/ready`

Readiness may verify:
- model artifacts loaded,
- metadata available,
- required data mount exists.

Do not require external NWP network access for liveness.

## Logging

Log:
- request ID,
- run ID,
- model version,
- forecast lead,
- processing errors,
- data source/version.

Avoid logging secrets.

## Model artifact governance

Store:
- model ID,
- code commit,
- data manifest,
- package versions,
- training timestamps,
- metrics.

## Large scientific data

Do not put NetCDF/GRIB blobs in PostgreSQL.

Use:
- object/file storage for arrays,
- Postgres/PostGIS for metadata/geometry when needed.

## Production extensions

Later:
- scheduled ingestion,
- retries,
- data-quality alerts,
- workflow queue,
- model registry,
- drift reports,
- observation-arrival verification jobs.

## Security

For SIH MVP:
- basic API hardening,
- strict CORS rather than `*` when deployed,
- input validation,
- no credentials in client,
- dependency pinning.

Full RBAC/auth can wait unless the official workflow requires it.
