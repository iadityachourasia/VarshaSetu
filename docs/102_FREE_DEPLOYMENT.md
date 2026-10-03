# 102 — Free Deployment (Backend on Render + Frontend on Vercel)

## 1. What this deploys

The real, live VarshaSetu system for $0/month:

- **Backend** (`backend/`): the read-only FastAPI science API, containerized
  and deployed to Render's free web-service tier. Serves both Track A
  (2019 GEFSv12 reforecast) and Track B (2023-2025 historical operational
  GEFS) from frozen, hash-verified artifacts. Never retrains, never decodes
  GRIB, never writes to `data/`/`experiments/` at request time.
- **Frontend** (`frontend-v2/`): the Next.js presentation app, deployed to
  Vercel's free Hobby tier, configured to call the Render backend as its
  live-API primary source, with the already-committed static bundle as a
  genuine-network-failure fallback (`lib/data-source.ts`'s existing,
  unmodified `withStaticFallback` architecture).

No code in `backend/app` or `frontend-v2/src` was changed to make this
deployment work — only three new files (`Dockerfile`, `.dockerignore`,
`render.yaml`) at the repository root, none of which touch application
logic.

## 2. Why the repo needed to become public

Render's free Docker build downloads the ~200MB frozen-data bundle (below)
from a plain `https://github.com/.../releases/download/...` URL. GitHub
returns `404` for release assets on a **private** repo when the requester
isn't authenticated, so a private repo would have required a GitHub
Personal Access Token stored as a Render secret. The repository was made
public instead (`gh repo edit ... --visibility public`), which is also
consistent with the project's own reproducibility/audit framing — no
secrets were ever present in the repo (verified in docs/101 section 39).

## 3. The frozen-data bundle

The backend's actual runtime footprint is **~750MB uncompressed / ~200MB
compressed** — not the full ~19GB acquisition corpus. It is exactly the six
directories `backend/app/api/science.py` and `operational.py` read at
request time:

```
data/manifests/phase2b
data/manifests/phase2c
data/operational_derived/operational_features_2023_2025_v1
experiments/recent_historical/phase4f_payload_acquisition_v1
experiments/recent_historical/phase4i_operational_model_development_v1
experiments/recent_historical/phase4j_operational_final_test_v1
```

These are `.gitignore`d (too large for a normal git push) and are instead
published as an immutable GitHub Release asset:

```
https://github.com/iadityachourasia/VarshaSetu/releases/download/serving-data-v1/varshasetu-serving-data-v1.tar.gz
```

sha256: `f5904aa9c8b1b96fb124b96396e854e3df840daa85efe05c20031e55fa22b262`
(recorded in the release notes; re-derive with `sha256sum` on the six
directories' tarball to confirm nothing was altered before re-publishing).
The `Dockerfile` downloads and extracts this at **build time** (baked into
the image), not at container start, so a free-tier cold start after
inactivity never depends on GitHub's availability or adds download latency.

**If the frozen artifacts are ever legitimately regenerated** (a new
research phase, never a retraining of existing results), a new release tag
must be cut and `Dockerfile`'s `DATA_BUNDLE_URL` default updated to match —
never overwrite the `serving-data-v1` asset in place, to keep old deploys
reproducible.

## 4. Backend deploy (Render)

1. Verified locally first (this session): `docker build -t
   varshasetu-backend-test -f Dockerfile .` completed in ~150s, producing a
   903MB image; the container started cleanly and served correct live
   values for both tracks (`/api/science/status`,
   `/api/science/operational/status`,
   `/api/science/operational/2025/metrics/deterministic` — RMSE values
   matched the canonical numbers exactly).
2. In the Render dashboard: **New +** → **Blueprint** → connect the
   `iadityachourasia/VarshaSetu` GitHub repo → Render reads `render.yaml`
   from the repo root automatically and proposes the `varshasetu-backend`
   free web service. Confirm and deploy.
   - Alternative without Blueprint: **New +** → **Web Service** → connect
     the repo → Runtime: **Docker** → Dockerfile path `./Dockerfile` →
     Plan: **Free**.
3. First build takes several minutes (pip install of the full scientific
   stack + the data-bundle download). Render's free plan spins the service
   down after ~15 minutes of inactivity; the next request triggers a cold
   start (image is already built, so this is just container start time —
   seconds, not a rebuild).
4. Once live, note the public URL Render assigns, e.g.
   `https://varshasetu-backend.onrender.com`. Confirm health:
   `curl https://<your-render-url>/api/science/status` and
   `curl https://<your-render-url>/api/science/operational/status` should
   both return 200 with real data, matching section 4 above.

## 5. Frontend deploy (Vercel)

1. In the Vercel dashboard: **Add New** → **Project** → import the same
   GitHub repo.
2. **Root Directory**: set to `frontend-v2` (this repo has two frontends;
   Vercel must build the Next.js one, not the legacy Vite `frontend/`).
   Framework preset should auto-detect as Next.js.
<!-- Optional switches, both off by default: NEXT_PUBLIC_SHOW_COMPLIANCE_PAGE=1 (frontend build) shows the requirement-coverage page (/compliance); SHOW_COVERAGE_API=1 (backend environment) opens its endpoint. -->
3. **Environment Variable**: add `SCIENCE_API_URL` =
   `https://<your-render-url>` (no trailing slash, no `/api` suffix —
   `next.config.ts`'s existing `rewrites()` appends `/api/science/:path*`
   itself). This single env var is read both by the server-side `getScience`/
   `getOperational` calls (`server=true` fetches use it directly) and by
   the Next.js rewrite that proxies same-origin client-side calls to it.
4. Deploy. No other configuration is needed — `npm run build` is Vercel's
   default for a detected Next.js project and matches what this session
   already verified builds cleanly.
5. Confirm: open the deployed URL, check a Track B page (e.g.
   `/forecast?experiment=operational&year=2025`) and look for the
   `DataSourceIndicator` chip reading **"Verified frozen API"** — that
   confirms the frontend is really reaching the live Render backend, not
   silently running on the static fallback the whole time.

## 6. What happens if the free backend is asleep or unreachable

This is not a special case to configure — it is the existing, already-
tested `withStaticFallback` behavior (docs/95-97): a genuine network
failure (Render cold-starting, or temporarily down) shows the "Cached
frozen presentation data" indicator and serves the checked-in static
bundle instead of an error. A real `SCIENCE_INTEGRITY_FAILURE` or a
genuine "this product doesn't exist" answer is never masked this way — see
`frontend-v2/src/lib/data-source.ts`.

## 7. Cost

$0. Render's free web-service tier and Vercel's free Hobby tier. No credit
card required for either at the plans used here. The only ongoing
resource: Render's free tier spins the service down after inactivity, so
the very first request after a quiet period takes longer (container start,
not a rebuild) — cosmetic for a demo, not a cost.

## 8. Rollback / re-deploy

Both platforms redeploy automatically on push to `master` by default
(configurable in each dashboard). To roll back the data bundle without
touching frozen science, revert only `Dockerfile`'s `DATA_BUNDLE_URL` to an
older release tag — the tarball itself is immutable once published.

## Runtime configuration added in Phase 7F (`docs/120`)

| Variable | Purpose | Default |
|---|---|---|
| `CORS_ALLOW_ORIGINS` | Comma-separated browser origins allowed to call the API directly. A wildcard is refused. Not needed when the frontend proxies `/api/science/*` (the Vercel setup in this document) | the production frontend origin and local development origins |
| `RENDER_GIT_COMMIT` | Set by Render itself; reported by `/api/health` as `commit` | `unknown` outside Render |

`GET /api/health` is liveness only and reports `version` and `commit`; scientific status is `GET /api/science/status` (the Render health check). If you change the bundle, update `DATA_BUNDLE_URL` and `DATA_BUNDLE_SHA256` in both the `Dockerfile` and `.github/workflows/ci.yml` together (a backend test enforces that they match).
