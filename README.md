# VarshaSetu

### Regime-Aware AI Post-Processing of Monsoon Rainfall Forecasts

**Bridging Raw NWP Forecasts and Actionable Rainfall Intelligence**

VarshaSetu is being developed for Smart India Hackathon problem statement
SIH26080, issued by the Ministry of Earth Sciences (MoES), National Centre for
Medium Range Weather Forecasting (NCMRWF). The intended system post-processes
genuine NWP forecasts; it is not a standalone weather predictor or a generic
dashboard. VarshaSetu is a research prototype evaluated in separate historical
GEFSv12 reforecast (2017–2019) and operational-era GEFS (2023–2025)
experiments; it does not issue live forecasts.

> **Release boundary:** the legacy `GOA_CLEAN.csv` training/inference path remains
> blocked. Frozen historical research artifacts and read-only Phase 2B/2C
> scientific APIs exist separately. Neither benchmark establishes live or
> production readiness.

## Current scientific status

Phase 0 stabilization controls are implemented. The **legacy CSV scientific
release gate** is still open/not passed: the checked-in dataset is structurally manifest-verified,
but its scientific provenance is unverified, it has no reproducible `regime_id`,
and it lacks forecast initialization/lead metadata. The saved model/report
artifacts were trained on a different absent dataset.

For scientific integrity, legacy CSV training, inference, verification,
probability, alert, and sandbox-prediction routes remain blocked. Separately,
the `frontend-v2` historical prototype serves frozen 2019 Phase 2B/2C science
through read-only `/api/science` endpoints. The completed 2025 operational-era
benchmark is a separate, consumed historical final test, not a live API layer.

The distinct results are: on 255 frozen 2019 GEFSv12 reforecast cases, Global
XGBoost reduced RMSE from **19.7735 to 17.8487 mm (9.73%)** versus Raw. On 232
frozen 2025 historical operational-GEFS cases, the model **preselected in 2024**
(M1 Ridge MOS) reduced RMSE from **16.1657 to 15.5736 mm (3.66%)**. These
populations are not pooled. Raw GEFS retained better heavy and very-heavy
spatial FSS than selected M1 in 2025. See [the independent final audit](docs/90_INDEPENDENT_FINAL_SCIENTIFIC_AUDIT.md).

See [the Phase 0 report](docs/30_PHASE0_STABILIZATION_REPORT.md) for the full
discrepancy list and unresolved blockers.

## Two frontends — read this before running anything

This repository contains **two separate frontend applications**. Confusing
them is the most common way to misunderstand what actually works:

- **`frontend/`** — the original Vite application, tied to the blocked
  legacy `GOA_CLEAN.csv` path described above. Preserved and recoverable,
  not actively developed.
- **`frontend-v2/`** — the independent Next.js 16 application that is the
  actual historical-prototype presentation frontend, and the one used for
  the SIH demo. It reads only frozen, hash-verified `/api/science` (2019
  GEFSv12 reforecast) and `/api/science/operational` (2023-2025 historical
  operational GEFS) artifacts — it never trains, decodes GRIB, or computes
  a scientific result at request time. See
  [`docs/68_FRONTEND_ARCHITECTURE.md`](docs/68_FRONTEND_ARCHITECTURE.md)
  for its route ownership and data boundary.

Everything below the setup section — the demo launcher, the judge-facing
docs, the presentation deck material — is about `frontend-v2/`.

## Setup

Use Python 3.12 and Node.js compatible with the lockfile.

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r backend\requirements.txt
python -m pytest -q backend\tests
```

Run the API from the repository root:

```powershell
.venv\Scripts\python.exe -m uvicorn backend.main:app --reload
```

Useful status endpoints:

- `GET /api/health`
- `GET /api/status`
- `GET /api/provenance`
- `GET /api/dataset/audit`
- `GET /api/audit`

### frontend-v2 (the demo-facing app)

```powershell
cd frontend-v2
npm ci
npm run dev        # local development, http://127.0.0.1:3000
```

Other useful commands from `frontend-v2/`: `npm run build` (production
build), `npm run typecheck`, `npm run lint`, `npm run test` (Vitest unit
tests), `npm run e2e` (Playwright, needs a live backend for most specs — see
[`docs/presentation/ROUTE_INVENTORY.md`](docs/presentation/ROUTE_INVENTORY.md)
for exactly which specs need one).

### Running the official demo

On the Windows development machine, from the repository root:

```powershell
& .\scripts\demo\start-demo.ps1
& .\scripts\demo\preflight-demo.ps1
```

Preflight reports one of three results:
`DEMO_PREFLIGHT_RESULT=READY` / `READY_WITH_OFFLINE_MAP` / `BLOCKED` — see
[`docs/75_DEMO_LAUNCH_AND_RECOVERY.md`](docs/75_DEMO_LAUNCH_AND_RECOVERY.md).
Open `http://127.0.0.1:3200` and navigate to `/forecast?demo=official` for
the canonical, non-cherry-picked demo case (Track B / 2025) — see
[`docs/presentation/OFFICIAL_DEMO_CASES.md`](docs/presentation/OFFICIAL_DEMO_CASES.md)
for why that case was chosen and what to do if it has a problem live. Press
`P` to toggle Presentation View (collapsed chrome, judge-facing layout).
Stop everything the launcher started with:

```powershell
& .\scripts\demo\stop-demo.ps1
```

### Documentation map

[`docs/00_INDEX.md`](docs/00_INDEX.md) is the entry point for every
document in this repository, in reading order. For the SIH demo
specifically, start with
[`docs/presentation/FINAL_PPT_FACTS.md`](docs/presentation/FINAL_PPT_FACTS.md)
(sourced numbers for slides),
[`docs/presentation/FINAL_DEMO_NARRATION.md`](docs/presentation/FINAL_DEMO_NARRATION.md)
(90s/2min/30s scripts), and
[`docs/presentation/JUDGE_QA.md`](docs/presentation/JUDGE_QA.md) (anticipated
questions with honest, sourced answers).

## Data configuration

The default dataset and manifest are repository-relative:

- `data/GOA_CLEAN.csv`
- `data/manifests/goa_clean.prototype.json`

To use another dataset, set both `DIGIVARSHA_SOURCE_CSV` and
`DIGIVARSHA_DATA_MANIFEST`. These legacy-named environment variables are retained
as stable compatibility contracts during the identity migration. The manifest
must match the file checksum, row count, and ordered columns. Passing identity
checks does not by itself establish scientific provenance or training eligibility.
