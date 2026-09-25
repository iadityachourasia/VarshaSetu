# Environment & Local Setup Specification

## Current audited stack

### Backend
- Python
- FastAPI
- Uvicorn
- Pandas
- NumPy
- scikit-learn
- SciPy
- Pydantic
- Pytest
- XGBoost used by code but absent from the audited requirements file

### Frontend
- React 18
- TypeScript
- Vite
- Tailwind CSS
- Recharts
- Lucide React

## Target development environment

Use one documented Python version across team members and CI.

Recommended/smoke-tested for Phase 0:
- Python 3.12.
- Node.js LTS compatible with Vite version in use.

Do not change runtime versions casually after model artifacts are produced.

## Backend setup target

From repository root or `backend/` according to final project convention:

```bash
python -m venv .venv
# activate venv (PowerShell: .venv\Scripts\Activate.ps1)
python -m pip install --upgrade pip
pip install -r backend/requirements.txt
python -m pytest -q
```

The exact command should be standardized after Phase 0 fixes.

## Frontend setup

```bash
cd frontend
npm ci
npm run build
npm run lint
npm run dev
```

If lint configuration is missing/broken, either repair it or remove the script; do not keep a fake quality command.

Phase 0 removed the stale `lint` script because no ESLint dependency or
configuration was present. `npm run build` is the enforced frontend check until
a real lint configuration is added.

## Required environment variables

Create `.env.example` when configuration becomes environment-based.

Potential keys:

```text
APP_ENV=development
DATA_ROOT=./data
MODEL_ROOT=./backend/models
REPORT_ROOT=./backend/reports
CORS_ALLOWED_ORIGINS=http://localhost:5173
```

Future data-source credentials must be backend-only.

## Dependency pinning

Before competition demo:
- export exact Python package versions,
- preserve `package-lock.json`,
- record XGBoost/sklearn versions used for serialized models.

## Scientific-data dependencies planned

When the grid pipeline is introduced, likely additions include:
- xarray,
- cfgrib,
- xesmf or another validated regridder,
- geopandas,
- rasterio,
- zarr where useful.

Do not add all dependencies in advance; add them with the feature requiring them.

Phase 1A added and pinned `eccodes==2.48.0` because the official one-message
GEFS sample probe required actual GRIB2 decoding. The other grid/geospatial
dependencies remain deferred until their specific adapters are implemented.

## Clean-clone definition

A clean-clone success means:
1. source checkout,
2. environment creation,
3. dependency install,
4. tests collect,
5. frontend builds,
6. documented demo/replay can run using files actually included or reproducibly downloaded.

A machine-local file outside the repository cannot be a mandatory hidden dependency.
