<div align="center">

# VarshaSetu

**Regime-Aware AI Post-Processing of Monsoon Rainfall Forecasts**

*Bridging raw NWP forecasts and actionable rainfall intelligence*

Built for **SIH26080** — Ministry of Earth Sciences (MoES), National Centre for Medium-Range Weather Forecasting (NCMRWF)

[![Python](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white)](backend/requirements.txt)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.116-009688?logo=fastapi&logoColor=white)](backend/requirements.txt)
[![Next.js](https://img.shields.io/badge/Next.js-16-000000?logo=next.js&logoColor=white)](frontend-v2/package.json)
[![React](https://img.shields.io/badge/React-19-61DAFB?logo=react&logoColor=white)](frontend-v2/package.json)
[![TypeScript](https://img.shields.io/badge/TypeScript-strict-3178C6?logo=typescript&logoColor=white)](frontend-v2/tsconfig.json)
[![Status](https://img.shields.io/badge/status-historical%20research%20prototype-orange)](docs/101_FINAL_FULL_STACK_QA_AND_STABILIZATION.md)

[Live Demo](#-live-deployment) · [Documentation](docs/00_INDEX.md) · [Architecture](#architecture) · [Getting Started](#getting-started) · [Deployment](docs/102_FREE_DEPLOYMENT.md)

</div>

---

## ⚠️ Read this first

VarshaSetu is a **historical scientific research prototype**, not a live forecasting
or operational warning system. It post-processes archived NWP model output
against archived observations, in two separate, non-pooled experiments. It
does not ingest current-date data and issues no live forecasts. Every number
in this README is a frozen, hash-verified result from a completed historical
test — re-derive any of them yourself with the commands in
[Verification](#-verification--reproducibility) below.

---

## Overview

Numerical Weather Prediction (NWP) models like NOAA's GEFS produce raw
rainfall forecasts with systematic, spatially-varying bias. VarshaSetu studies
whether a **regime-aware machine-learning correction layer** — one that
conditions its correction on the atmospheric state at forecast time — can
reduce that bias and produce better-calibrated extreme-rainfall probabilities
than a single global model, without ever seeing the future.

The project is deliberately split into two **independent, non-pooled**
historical experiments so that no result can be inflated by mixing
populations:

| | Track A — GEFSv12 Reforecast | Track B — Operational-Era GEFS |
|---|---|---|
| **Years** | 2017 (train) · 2018 (validate) · 2019 (test) | 2023 (cross-fit) · 2024 (validate) · 2025 (final test) |
| **Forecast source** | NOAA GEFSv12 reforecast archive | NOAA operational GEFS historical archive |
| **Observation** | IMD 0.25° gridded rainfall | IMD 0.25° gridded rainfall |
| **Test population** | 255 cases | 232 cases · 301,832 paired cells |
| **Status** | Final test completed, frozen | Final test completed, frozen |

Neither track's result is combined with the other. There is no "six-year"
or "combined" skill number anywhere in this project — a static test enforces
that (`science-copy-guard.test.ts`).

## Key Results

<table>
<tr><th align="left" colspan="2">Track A — 2019 GEFSv12 Reforecast (255 cases)</th></tr>
<tr><td>Raw GEFS RMSE</td><td><code>19.7735 mm</code></td></tr>
<tr><td>Global XGBoost (M2) RMSE</td><td><code>17.8487 mm</code></td></tr>
<tr><td><strong>Reduction vs. Raw</strong></td><td><strong>9.73%</strong></td></tr>
<tr><td>Selection basis</td><td>Lowest deterministic RMSE across the model ladder</td></tr>
</table>

<table>
<tr><th align="left" colspan="2">Track B — 2025 Historical Operational GEFS (232 cases · 301,832 cells)</th></tr>
<tr><td>Raw GEFS RMSE</td><td><code>16.1657 mm</code></td></tr>
<tr><td>M1 Ridge MOS RMSE <em>(preselected primary)</em></td><td><code>15.5736 mm</code></td></tr>
<tr><td>M2 Global XGBoost RMSE <em>(secondary, not eligible for reselection)</em></td><td><code>15.0022 mm</code></td></tr>
<tr><td><strong>Reduction vs. Raw (M1)</strong></td><td><strong>3.66%</strong></td></tr>
<tr><td>Selection basis</td><td>M1 was preselected under the frozen 2024 validation rule <em>before</em> the 2025 holdout was opened. M2's lower RMSE was discovered after the test and is reported honestly, but does not retroactively become the headline result — reselecting after seeing final-test results would invalidate the test.</td></tr>
</table>

**The honest caveat that matters most:** in 2025, Raw GEFS retained **stronger
Heavy and Very-Heavy spatial skill (FSS)** than the RMSE-selected M1 at every
tested neighborhood scale. Lower overall RMSE did not translate into better
extreme-rainfall spatial skill — this is stated as a first-class limitation
throughout the product, never buried in a footnote.

<details>
<summary><strong>Full model ladder (both tracks)</strong></summary>

| Model | Role | Description |
|---|---|---|
| **M0** | Reference | Raw NWP forecast, uncorrected |
| **M1** | Preselected primary (2025) | Linear Ridge MOS — transparent statistical baseline |
| **M2** | Secondary result | Global (non-regime) XGBoost |
| **M3** | Regime-aware | Hard regime-routed XGBoost (one specialist model per regime) |
| **M4** | Regime-aware | Soft probabilistic regime Mixture-of-Experts |

2025 regime-conditioned finding: **M4 (soft routing) beats M3 (hard routing)
in every one of the three paired pseudo-regime populations** (100 / 71 / 61
cases), but **neither regime-aware model beats global M2 overall** — regime
awareness did not add measurable skill on this final test.

</details>

<details>
<summary><strong>Data quality / eligibility (Track B)</strong></summary>

| | Scheduled | Atmosphere complete | c00 QC-eligible | Full 5-member eligible |
|---|---|---|---|---|
| **Total** | 1,125 | 1,125 | 615 | 218 |
| 2023 (cross-fit) | 375 | 375 | 200 | 76 |
| 2024 (validation) | 375 | 375 | 183 | 67 |
| 2025 (final test) | 375 | 375 | 232 | 75 |

All selected source messages were acquired; the gap between "scheduled" and
"eligible" reflects canonical QC attrition (e.g. packing/precision checks),
never a download failure.

</details>

## Architecture

```
                    ┌──────────────────────────────────────────────┐
                    │              Frozen Historical Corpus          │
                    │   NOAA GEFS (reforecast + operational archive) │
                    │         IMD 0.25° gridded rainfall (truth)      │
                    └────────────────────┬─────────────────────────┘
                                         │  forecast-time features only
                                         ▼
                    ┌──────────────────────────────────────────────┐
                    │       Regime Classifier (forecast-only)         │
                    │   Active Monsoon · Break/Weak · Low-Depression  │
                    └────────────────────┬─────────────────────────┘
                                         ▼
        ┌───────────┬───────────┬───────────────┬───────────────┐
        │  M0 Raw   │ M1 Ridge  │ M2 Global XGB  │ M3/M4 Regime  │
        └───────────┴───────────┴───────────────┴───────────────┘
                                         ▼
                    ┌──────────────────────────────────────────────┐
                    │   Calibration → Heavy/Very-Heavy Probability   │
                    └────────────────────┬─────────────────────────┘
                                         ▼
                    ┌──────────────────────────────────────────────┐
                    │       Verification (RMSE · FSS · Brier · PR)    │
                    └────────────────────┬─────────────────────────┘
                                         ▼
                    ┌──────────────────────────────────────────────┐
                    │   Read-only FastAPI presentation layer          │
                    │   /api/science/*  ·  /api/science/operational/*│
                    └────────────────────┬─────────────────────────┘
                                         ▼
                    ┌──────────────────────────────────────────────┐
                    │        Next.js scientific workstation           │
                    │  Forecast · Casebook · Extreme Rain · Ensemble  │
                    │  Regime · Districts · Verification · Audit      │
                    └──────────────────────────────────────────────┘
```

The backend **never trains, decodes GRIB, or computes a scientific result at
request time** — it serves only frozen, hash-verified artifacts. The frontend
never fabricates a value it cannot fetch: a genuine network failure falls
back to a checked-in static bundle (clearly labeled); a real scientific
integrity failure or unavailable product is always shown as a hard, honest
error, never silently masked. See
[`lib/data-source.ts`](frontend-v2/src/lib/data-source.ts).

### Repository layout

```
VarshaSetu/
├── backend/              FastAPI read-only science API (Python 3.12)
│   ├── app/api/          science.py (Track A) · operational.py (Track B)
│   ├── app/services/     legacy pipeline (blocked, quarantined — see below)
│   └── tests/            pytest suite (193+ tests)
├── frontend-v2/           Next.js 16 / React 19 presentation frontend (the demo app)
│   ├── src/app/           12 routes: forecast, casebook, extremes, ensemble,
│   │                      regimes, districts, verification, observations,
│   │                      quality, methodology, audit, and the overview
│   └── tests/e2e/         Playwright suite (35+ specs, real backend)
├── frontend/              legacy Vite app (blocked CSV path — not the demo app)
├── data/ · experiments/   frozen scientific artifacts (gitignored; see below)
├── scripts/demo/          one-command demo launcher + preflight + stop
├── docs/                  100+ numbered documents — docs/00_INDEX.md is the map
├── Dockerfile             backend container for free hosting (Render)
└── render.yaml            one-click Render Blueprint
```

## Tech Stack

| Layer | Technology |
|---|---|
| Backend API | FastAPI 0.116, Pydantic 2, Uvicorn |
| Scientific stack | NumPy, pandas, scikit-learn, XGBoost, SciPy, Zarr, Shapely |
| Frontend framework | Next.js 16 (App Router), React 19, TypeScript (strict) |
| Data & state | TanStack Query, Zod (runtime schema validation on every API response) |
| Mapping | MapLibre GL, with an offline district-geometry fallback |
| Charts | Recharts |
| Testing | pytest (backend), Vitest (frontend units), Playwright (E2E, real backend) |
| Deployment | Docker (Render, free tier) + Vercel (free tier) — see [docs/102](docs/102_FREE_DEPLOYMENT.md) |

## Getting Started

### Prerequisites

- Python 3.12
- Node.js (version pinned by `frontend-v2/package-lock.json`)

### Backend

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

Status endpoints: `GET /api/science/status` (Track A) ·
`GET /api/science/operational/status` (Track B) · `GET /api/health` ·
`GET /api/provenance` · `GET /api/dataset/audit` · `GET /api/audit`.

### Frontend (the demo app)

> **This repository has two frontends.** `frontend-v2/` is the actual
> historical-prototype presentation app used for the demo. `frontend/` is a
> legacy Vite app tied to the blocked CSV path — preserved, not developed.
> See [`docs/68_FRONTEND_ARCHITECTURE.md`](docs/68_FRONTEND_ARCHITECTURE.md).

```powershell
cd frontend-v2
npm ci
npm run dev        # http://127.0.0.1:3000
```

| Command | Purpose |
|---|---|
| `npm run build` | Production build |
| `npm run typecheck` | Strict TypeScript check |
| `npm run lint` | ESLint |
| `npm run test` | Vitest unit tests |
| `npm run e2e` | Playwright E2E (needs a live backend for most specs) |

### One-command demo

```powershell
& .\scripts\demo\start-demo.ps1
& .\scripts\demo\preflight-demo.ps1
```

Preflight reports `DEMO_PREFLIGHT_RESULT=READY` /
`READY_WITH_OFFLINE_MAP` / `BLOCKED` — see
[`docs/75_DEMO_LAUNCH_AND_RECOVERY.md`](docs/75_DEMO_LAUNCH_AND_RECOVERY.md).
Open `http://127.0.0.1:3200/forecast?demo=official` for the canonical,
non-cherry-picked demo case. Press **P** to toggle Presentation View. Stop
everything with:

```powershell
& .\scripts\demo\stop-demo.ps1
```

## 🚀 Live Deployment

The full system deploys for **$0/month**: backend on Render's free tier
(Docker, ~750MB of frozen artifacts baked in at build time), frontend on
Vercel's free tier. If the backend is asleep or briefly unreachable, the
frontend degrades gracefully to its checked-in static bundle rather than
erroring — no configuration needed for that, it's the existing fallback
architecture. Full walkthrough, exact env vars, and the verified local
Docker build log: **[docs/102_FREE_DEPLOYMENT.md](docs/102_FREE_DEPLOYMENT.md)**.

## Verification & Reproducibility

Every number in this README was re-derived live against the running backend
in this session, not taken on faith — see
[docs/101](docs/101_FINAL_FULL_STACK_QA_AND_STABILIZATION.md) section 6 for
the full comparison table. To reproduce any of it yourself:

```powershell
curl https://varshasetu.onrender.com/api/science/model-comparison        # Track A, all models
curl https://varshasetu.onrender.com/api/science/operational/2025/metrics/deterministic  # Track B, 2025
curl https://varshasetu.onrender.com/api/science/operational/quality      # data-quality counts
```

Test suite status as last verified locally against a real backend and the
real frozen corpus (not a CI badge — re-run these yourself, commands above):

| Suite | Result |
|---|---|
| Backend (`pytest backend/tests`) | 193 passed |
| Frontend unit (`npm run test`) | 76 passed |
| Frontend E2E (`npm run e2e`, single worker) | 35 passed |
| TypeScript / ESLint | clean |
| Production build | clean, all 12 routes |

## Scientific Constraints (non-negotiable)

This project is governed by [`AGENTS.md`](AGENTS.md), which no change may
weaken. In summary:

- No retraining, no altering predictions/observations/masks/thresholds/
  calibration/QC/model selection outside an explicitly authorized phase.
- No fabricated values, no invented PR/ROC curves. Track-B district
  aggregates are a read-only area-weighted view of the frozen grids for 2024/2025
  only (`docs/107`); 2023 has none. District-level verification exists for 2024/2025 under a frozen protocol (`docs/112`, `docs/113`).
- Forecast-time causal validity only: no feature that wouldn't exist at the
  moment a real forecast is issued.
- Reanalysis (ERA5/IMDAA) may inform regime-label research; it is never
  called a raw NWP forecast in a post-processing experiment.
- "Confidence" is never used as a substitute for a calibrated probability;
  "regime probability" means model-estimated, not an arbitrary heuristic
  score unless explicitly labeled as one.

A static test (`science-copy-guard.test.ts`) scans the entire frontend
source for banned phrases ("live forecast", "operationally proven",
"combined 2019-2025 skill", etc.) and fails the build if an unguarded
violation appears.

## Documentation

[`docs/00_INDEX.md`](docs/00_INDEX.md) is the entry point for all 100+
documents in this repository, in reading order. Start here depending on what
you need:

| I want to... | Read |
|---|---|
| Understand the problem statement | [`docs/01_SIH26080_PROBLEM_STATEMENT.md`](docs/01_SIH26080_PROBLEM_STATEMENT.md) |
| See the target architecture | [`docs/04_TARGET_ARCHITECTURE.md`](docs/04_TARGET_ARCHITECTURE.md) |
| Understand the regime methodology | [`docs/08_REGIME_METHODOLOGY.md`](docs/08_REGIME_METHODOLOGY.md) |
| Understand the ML methodology | [`docs/09_ML_METHODOLOGY.md`](docs/09_ML_METHODOLOGY.md) |
| See the verification protocol | [`docs/10_VERIFICATION_PROTOCOL.md`](docs/10_VERIFICATION_PROTOCOL.md) |
| Prepare for the judge demo | [`docs/presentation/FINAL_PPT_FACTS.md`](docs/presentation/FINAL_PPT_FACTS.md), [`FINAL_DEMO_NARRATION.md`](docs/presentation/FINAL_DEMO_NARRATION.md), [`JUDGE_QA.md`](docs/presentation/JUDGE_QA.md) |
| Deploy it myself | [`docs/102_FREE_DEPLOYMENT.md`](docs/102_FREE_DEPLOYMENT.md) |
| See the latest full QA pass | [`docs/101_FINAL_FULL_STACK_QA_AND_STABILIZATION.md`](docs/101_FINAL_FULL_STACK_QA_AND_STABILIZATION.md) |

## Data Configuration (legacy path)

The blocked legacy CSV path's default dataset and manifest are
repository-relative (`data/GOA_CLEAN.csv`,
`data/manifests/goa_clean.prototype.json`). To point it at another dataset,
set both `DIGIVARSHA_SOURCE_CSV` and `DIGIVARSHA_DATA_MANIFEST` — the
manifest must match the file checksum, row count, and ordered columns.
Passing that identity check does not by itself establish scientific
provenance or training eligibility; this path remains blocked regardless.

<details>
<summary><strong>Current scientific status (legacy CSV path)</strong></summary>

Phase 0 stabilization controls are implemented. The legacy CSV scientific
release gate is still open/not passed: the checked-in dataset is
structurally manifest-verified, but its scientific provenance is unverified,
it has no reproducible `regime_id`, and it lacks forecast
initialization/lead metadata. For scientific integrity, legacy CSV training,
inference, verification, probability, alert, and sandbox-prediction routes
remain blocked. See [the Phase 0 report](docs/30_PHASE0_STABILIZATION_REPORT.md)
and [the independent final audit](docs/90_INDEPENDENT_FINAL_SCIENTIFIC_AUDIT.md).

</details>

---

<div align="center">

Built for **Smart India Hackathon 2026** — problem statement SIH26080

</div>
