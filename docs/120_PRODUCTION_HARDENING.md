# Phase 7F: production hardening

Date: 2026-10-01. No scientific computation, model, protocol or evidence file was changed. Every item below was found by inspection, fixed with the smallest coherent change, tested, and verified in a clean checkout.

## What was fixed

| # | Problem found | Fix | Where |
|---|---|---|---|
| 1 | CORS allowed every origin with credentials enabled | Named origins only (production frontend and local development), credentials off (the API sets no cookies), read-only methods, `CORS_ALLOW_ORIGINS` override that refuses a wildcard. The production frontend reaches the API through a same-origin proxy, so browsers do not call it cross-origin in production | `backend/app/core/cors.py`, `backend/main.py` |
| 2 | Version was the string `0.1.0-phase0` in two places | One constant `API_VERSION`; the deployed commit is read from the environment (`RENDER_GIT_COMMIT`), never from git; both appear in `/api/health` and the OpenAPI document | `backend/app/version.py` |
| 3 | `/api/health` loaded the quarantined legacy dataset, which is not in the production image, so it could fail with an unhandled error | Health is now plain liveness with version, commit and the pointer to `/api/science/status`; the legacy gate is reported as quarantined | `backend/app/api/routes.py` |
| 4 | `/api/audit` and `/api/jury-defense` returned fixed hand-written PASS/FAIL statements not computed from the repository, which `AGENTS.md` section 3.3 forbids presenting as an executed audit | Both return HTTP 410 with the replacement named. A legacy dataset that cannot be loaded now gives a structured 410, not a 500. All legacy scientific endpoints stay fail-closed (409) | `backend/app/api/routes.py` |
| 5 | The Docker build downloaded the 200 MB data bundle with no integrity check and no retry; a connection reset failed the build | `curl --retry 8 --retry-all-errors -C -` and a pinned SHA-256 verified before extraction (the digest equals GitHub's published digest for the release asset); the malformed 63-character digest in `docs/102` is corrected | `Dockerfile`, `docs/102` |
| 6 | No CI | GitHub Actions: backend tests with the checksum-verified bundle, frontend lint, types, unit tests and build, and a Dockerfile lint. A test enforces that CI and the Dockerfile pin the same bundle | `.github/workflows/ci.yml` |
| 7 | The suite failed on any checkout without the gitignored bundle and experiment code | An explicit skip policy: those tests are skipped or not collected, with the reason printed in the report header and the skip summary; with the data present every one runs and must pass | `backend/tests/conftest.py` |
| 8 | Two Phase 1B governance tests only passed on Windows (hashes recorded over CRLF in one case, LF in another) | Hashes are computed over a canonical line-ending form for text and over exact bytes for binary files, so the result is the same on every checkout | `backend/tests/test_pilot_pair.py` |
| 9 | Changing `routes.py` broke the Phase 1B protected-artifact lock | Handled the governed way: an append-only supersession record v2 chained by hash to v1; v1 and the original lock are untouched | `data/manifests/phase1b/2019-07-15/protected_artifact_supersession_v2.json` |
| 10 | The `demo-flow` end-to-end test failed (strict locator matched a figure shown twice) | The locator accepts the first of several identical API-derived values | `tests/e2e/demo-flow.spec.ts` |
| 11 | Map specs failed offline because they need the public basemap host | They skip, with a stated reason, when that host is unreachable (`BASEMAP_PROBE_URL` overrides the probe) | `tests/e2e/helpers/online.ts` |
| 12 | Story Mode typed 2019 and 2025 RMSE, Brier skill and data-quality counts into the component (`AGENTS.md` section 3.3) | Every figure is derived in `lib/story-facts.ts` from the verified API (2019) and the generated frozen bundle (2025, data quality); a scene whose source is unavailable says so instead of showing a number. The derived values equal the previously typed ones, which is now a test | `frontend-v2/src/lib/story-facts.ts`, `story-mode.tsx` |
| 13 | The first visitor after a restart paid for hash verification of the evidence files | Best-effort background warm-up of the small evidence caches at startup; it never raises and never hides a later integrity failure | `backend/main.py` |

## Verification

| Check | Result |
|---|---|
| Backend suite on this machine | 379 passed |
| Backend suite on a bare clone (no bundle, no experiment code) | 234 passed, 68 skipped with printed reasons, 0 failed |
| Vitest | 122 passed |
| `tsc`, `eslint`, `next build` | clean |
| Playwright full suite, one worker, against `next start` | 94 of 94 passed (first fully green run) |
| `docker build --check` | no warnings |
| curl flags in the Linux base image | normal download, retry on a failing connection, and resume of a partial file all verified (`docs/119`) |

## Not done, and why

- **Playwright in CI:** it needs the full backend with data and a browser; it stays a local pre-push check.
- **Phase 4 freeze tests in CI:** they import the gitignored local experiment code; they run only where that code exists.
- **Free-tier build limits and Render/Vercel auto-deploy behaviour** are not simulated.
- **The first GitHub Actions run** can only be observed after the push.
- **Frozen-evidence tests that assert wording of limitations** were left unchanged.
- **`pytest` and `matplotlib` in the production requirements** add image size but are left alone to avoid an unverified runtime change.

Gate: `P3_HARDENING_COMPLETE_PENDING_FIRST_CI_RUN`.
