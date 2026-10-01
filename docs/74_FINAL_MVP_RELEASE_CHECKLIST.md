# Phase 3C — Final MVP recording gate

This checklist governs a **historical scientific prototype**, not an
operational forecast service. The scientific backend and Phase 2B/2C artifacts
are frozen and read-only.

| Gate | Evidence required |
|---|---|
| Production service | `next build`, `next start`, FastAPI readiness and same-origin science proxy respond |
| Six screens | Overview, Forecast, Extreme Rain, Districts, Verification and Methodology load in production |
| Primary case | Official `20190802T000000Z_day3_24h` opens from Overview; ordinary case browsing remains |
| Maps | Three shared-scale rainfall maps, synchronized cameras, exact valid-cell inspection, online vector geography, visible attribution |
| Offline | Style/tile failure activates clearly limited local district geography without losing scientific fields |
| Science | 2019 common-case RMSE is API-derived; limitations remain visible; no model retraining or future data |
| District | Case-valid area-weighted outputs and selectable real geometry |
| Tests | TypeScript, lint, production build, unit, production Playwright, backend pytest, compileall, API and manifest SHA-256 |
| Recording | Launcher, preflight, shutdown, three cases, storyboard, narration and shot list documented |

Release decision is recorded in `docs/79_FINAL_DEMO_VERIFICATION.md`.
The online vector basemap is a public external service and must be rechecked
immediately before recording. A transient tile failure does **not** invalidate
the local scientific artifacts, but recording the full geographic sequence
requires online tiles. Do not describe the sparse offline district fallback as
equivalent to an online city/road basemap.

Non-negotiable claims: M2 Global XGBoost is the best tested deterministic RMSE
model; M3/M4 do not beat it on RMSE; in 2019 Raw GEFS has stronger reported
deterministic Heavy/Very Heavy CSI/ETS than every corrected model and stronger
FSS than every corrected model M1-M4 (`docs/64`, `docs/108`). The regime classifier reproduces
forecast-only pseudo-labels, not independent meteorological truth.
