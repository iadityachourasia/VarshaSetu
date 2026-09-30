# Final Architecture Diagram Spec — Phase 5B

Purpose: a single slide-ready diagram of what is **actually built and
demoed** today, clearly separated from the longer-term target architecture
in `docs/04_TARGET_ARCHITECTURE.md`. Do not draw the target architecture's
live-ingestion flow and label it as this project's current state — that
would misrepresent an operational research prototype as a production
system, which AGENTS.md §3.3 forbids.

## 1. Top-level shape: two parallel, non-pooled pipelines

Draw **two horizontal lanes**, clearly separated by a divider labeled
"Different GEFS lineages — not pooled," not two branches of one pipeline:

```
LANE A — Track A (retrospective)
  NOAA GEFSv12 reforecast ─▶ Forecast-time features ─▶ Pseudo-regime classifier ─▶
  Model ladder (M0 Raw / M1 Ridge / M2 XGBoost / M3 Hard-regime / M4 Soft-MoE) ─▶
  Extreme-event probability models ─▶ District aggregation ─▶ Verification ─▶
  Frozen artifacts (hash-pinned) ─▶ FastAPI (/api/science/*) ─▶ Frontend

LANE B — Track B (operational-era)
  Historical NOAA operational GEFS ─▶ Forecast-time features ─▶ Pseudo-regime classifier ─▶
  Model ladder (M0-M4, same family) ─▶ Extreme-event probability models ─▶
  [read-only district aggregation, 2024/2025 only; docs/107] ─▶ Verification ─▶ Frozen artifacts (hash-pinned) ─▶
  FastAPI (/api/science/operational/*) ─▶ Frontend
```

Both lanes terminate in the same frontend, but their frozen artifacts and
API namespaces are separate — draw two distinct database/artifact-store
icons, not one shared one, to avoid implying a pooled result.

## 2. Node styling (solid vs. dashed)

- **Solid boxes** — implemented, hash-verified, and actually shown in the
  live demo: forecast input, feature engineering, pseudo-regime classifier,
  the M0–M4 model ladder, extreme-event probability models, verification,
  frozen artifact store, FastAPI, frontend.
- **Solid box, Track A lane only** — district aggregation (real, but does
  not exist for Track B — do not draw it in Lane B at all, not even dashed,
  since it was never built for that track, not merely deferred).
- **Do not draw**: any box implying live/continuous ingestion, a
  scheduler polling a live NWP feed, or a production message queue. Nothing
  in this system ingests data at request time — every request the frontend
  makes reads a frozen, checked-in artifact.
- If the target architecture's aspirational layers (hierarchical regime
  engine, soft-MoE with three named experts, calibration/uncertainty layer)
  are wanted on the same slide for context, draw them in a **visually
  distinct dashed lane below**, labeled "Target architecture — not yet
  built (see docs/04)," never in the same solid styling as the shipped
  pipeline above it.

## 3. Color coding (reuse the app's own model palette)

Use the same semantic colors the live app already uses for model identity
(`frontend-v2/src/lib/model-colors.ts` / the CSS custom properties it
defines), so a judge who has just seen the app recognizes the same color
meaning the same model on the slide:

- M0 Raw GEFS — the app's neutral "raw" gray (`--raw`)
- M1 Linear Ridge MOS — teal (the app's primary accent color)
- M2 Global XGBoost — blue (`#3a6ea5` light / `#8ab4e0` dark)
- M3 Hard Regime — amber/brown (`#a8632e` light / `#e2a06b` dark)
- M4 Soft MoE — violet (`#9a4a86` light / `#d99bc7` dark)

These are the literal values in `frontend-v2/src/app/globals.css`
(`--model-m0` … `--model-m4`), not an approximation.

Do not invent a new color mapping for the slide deck; pulling the same
tokens keeps the deck and the live product visually consistent, which
matters when a judge flips between the slide and the screen.

## 4. Required annotations directly on the diagram

- A label on the Track B lane's output: "2025: RMSE improved, extreme
  spatial FSS did not" — the single most important caveat, placed where it
  cannot be missed, not in a footnote.
- A label on the district view: "Read-only aggregation of frozen grids, 2024/2025
  only; no district-level verification."
- A small hash-icon annotation on the frozen-artifact-store boxes:
  "SHA-256 pinned; a displayed-value test compares live output against this
  file" (this is literally true — see `docs/91` §3).
- A caption under the whole diagram: "Historical scientific prototype.
  Every box reads a frozen, already-computed artifact; nothing here ingests
  a live weather feed."

## 5. What this diagram must never imply

- That Track A and Track B feed a single combined score.
- That the pseudo-regime classifier output is an independently verified
  weather regime (it is a forecast-only pseudo-label — see `docs/08`).
- That the frontend calls out to a live NWP provider at request time.
- That district aggregation exists for both tracks.

## 6. Suggested slide placement

One diagram slide, placed immediately after the "Two Experiment Tracks"
narration beat (Story Mode scene 2) and before either benchmark's numbers
are shown — so the audience has the pipeline shape in mind before seeing
the 2019 and 2025 headline figures.

## 7. Source alignment

This spec intentionally diverges from `docs/04_TARGET_ARCHITECTURE.md`'s
single unified flow diagram, which describes the long-term target system
(a hierarchical regime engine, a three-expert soft mixture, live GRIB/Zarr
ingestion) rather than what is built and demoed today. Cite `docs/04`
explicitly on the dashed "target" lane if it is included, so nobody mistakes
the aspiration for the current state.
