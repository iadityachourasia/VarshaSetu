# Phase 7E: serving the zone evidence and the Geographic Zones page

Date: 2026-10-01. Follows `docs/115` to `docs/118`. No scientific computation, training or data acquisition was performed; this phase exposes frozen, hash-verified evidence.

## What was built

| Item | Location |
|---|---|
| Read-only router (overview, geography, verification, forcing) | `backend/app/api/zones.py`, mounted at `/api/science/evidence/zones/*` |
| Typed Zod client and schema tests | `frontend-v2/src/lib/api/zones.ts`, `zones.test.ts` |
| Page "Geographic Zones" (zone map with layers, skill by zone and score, zone-minus-all intervals, forcing strata, decision-rule panel) | `/zones`, `frontend-v2/src/components/zones/zone-evidence.tsx`, navigation entry in the SCIENCE group |
| Coverage resolver extended to zone evidence | `backend/app/api/evidence.py` (`zone:` and `zoneforcing:` sources) |
| Coverage row `REGIME-COASTAL-OROGRAPHIC` moved to PARTIAL with evidence-resolved facts | `backend/app/evidence_data/phase6/ps_coverage.json`, docs/22 regenerated |
| Tests | `backend/tests/test_zones_api.py` (15), updated `test_ps_coverage.py` and `test_coastal_orographic_protocol.py`, `zones.test.ts` (4), `tests/e2e/zones.spec.ts` (5), updated `compliance.spec.ts` |

## Integrity rules enforced

- Before any zone payload is served, the whole frozen chain is verified: protocol v3, geography artifact, Stage 2 spec, both manifests, their sidecars, and the hash references each file makes to the others. Any mismatch returns 503 `SCIENCE_INTEGRITY_FAILURE`; there is no fallback to cached data.
- Every file is hash-checked against its manifest entry; a role without a registered display label is refused, so Track A 2019 and Track B 2025 always appear as `POST-HOC EXPLORATORY ANALYSIS OF THE COMPLETED 20XX FINAL TEST`.
- The page states, on every view, that zones are a rule-based convention and not a validated regime, that bootstrap intervals are optimistic, that tracks are never pooled, and that Stage 3 is not authorised. Unsupported strata display `insufficient support`, never a number. No scientific figure is typed into the page; all come from the API.
- FSS is not shown (see `docs/117`).

## Coverage status change

Under the protocol's mapping (`docs/115`, `docs/118`), Stages 1 and 2 complete and served allow **PLANNED to PARTIAL**, never IMPLEMENTED. The row now links to `/zones`, states "no coastal or orographic specialist model" as its gap, and resolves nine figures from the evidence (the Ghats-coast cell count and Raw bias and heavy frequency bias for all four populations). The official PS-R03 status was already PARTIAL and is unchanged.

## Verification run (2026-10-01)

| Check | Result |
|---|---|
| Backend full suite (`--basetemp` in a writable folder) | 355 passed |
| Frontend `tsc --noEmit`, `eslint`, `next build` | clean |
| Vitest | 115 passed |
| Playwright full regression, one worker, against `next start` | 91 passed, 1 failed |

The single failure is `demo-flow.spec.ts:4`, which predates this work (duplicate Overview figure matched by a strict text locator); it is not fixed here.

## Limitations

The page reads only the four frozen populations; the map is an SVG of the 49 by 49 grid (no basemap), so it is independent of any tile service; the terrain attribution travels with the data. Zone-level evidence for 2023 and for other regions does not exist.

Gate: `P0_7_STAGES_0_2_SERVED`.

## Pre-push container verification (2026-10-01)

The committed Dockerfile was built and run as Render would (Linux, Debian 13, Python 3.12, 512 MB memory cap) with the real `serving-data-v1` bundle (200,680,777 bytes, gzip integrity verified).

| Check | Result |
|---|---|
| Image build from the committed Dockerfile | Every step before the bundle download succeeded. The download itself failed once from this machine with a connection reset (curl exit 56, slow network); the bundle was then fetched on the host with resume and retries and the image built with only that step replaced by a copy of the local file. The download step is therefore verified as far as the file and extraction go, not as a single uninterrupted network call. The Dockerfile has no retry flags, so a flaky network at deploy time can fail a Render build; adding `--retry` is a recommended, unmade change |
| Health check `/api/science/status` | healthy about 4 s after start; 135 MiB at start, 169 MiB after the smoke run, no errors in the logs |
| HTTP smoke test of 21 requests (all five new zone endpoints for all four populations, `ps-coverage`, regime and district verification, manifest, 2025 cases, district list, compare and history for 2024 and 2025, a structured 404) | 21 of 21 passed, each response under 0.15 s |
| Backend tests inside the container (zone, evidence, operational, phase 2C, district modules) | 175 passed, 3 failed: tests that read the raw boundary source file under `data/static`, which the image does not ship; the runtime never reads it, and one of the three also fails on the deployed commit |

Not covered: the free tier's actual CPU and build-time limits, and Render/Vercel auto-deploy behaviour.
