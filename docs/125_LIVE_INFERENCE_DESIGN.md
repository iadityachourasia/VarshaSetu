# Phase 9B: live and new-cycle inference, design (no code)

Date: 2026-10-01. **Design only; nothing was built, downloaded or run.** The goal is a plan that is true to what the repository contains, so that the largest remaining
"production" item can be started, costed and approved with its risks in view. The coverage row `LIVE-INFERENCE` stays **PLANNED** and is not a mandatory requirement.

## 1. What "live" means here, and what it must not claim

Today the app is a **historical replay**: every number shown comes from a frozen case with a known observation (`AGENTS.md` section 10, "Historical replay"). An *operational* or *live* forecast
is defined there as one whose inference runs without any future observation. The target product is therefore:

> take a published GEFS cycle, apply the **frozen** Track B models with no retraining, and publish corrected rainfall, heavy-rain probabilities and district tables for that cycle, each clearly
> labelled as an experimental forecast, with provenance and quality status.

It must **not** claim verified skill for the new cycle (no observation exists yet), must not present itself as an official warning, and must not change any frozen artifact.

## 2. What already exists and can be reused (inventory)

| Step | Existing piece | State |
|---|---|---|
| Find and fetch the needed GEFS messages | `scripts/data/acquire_monthly_pilot.py` (index lookup, parallel byte-range fetch, per-message decode and crop, daily writers) | Works, but tied to the frozen corpus dates and monthly batch layout; needs a single-cycle entry point |
| Rainfall window reconstruction | `backend/app/data/accumulation.py` (`reconstruct_accumulation_window`, segment coverage checks) | Reusable as is |
| Regridding and masks | `backend/app/data/regridding.py`, `monthly_qc.py` (`context_coordinates`, `bilinear_to_context`) | Reusable as is |
| The 22 forecast-time features | `backend/app/ml/phase2b.py`, `features.py` | Reusable; Track B feature construction lives in the Phase 4G code under the gitignored `experiments/` tree |
| Forecast-only regime features and classifier | `backend/app/ml/forecast_regimes.py` and the frozen 2023 classifier (`regime_models/full_2023_classifier.json`) | Reusable |
| Frozen models M1 to M4 and the probability models and calibrators | `experiments/.../phase4i_operational_model_development_v1/{deterministic_models,regime_models,probability_models}` (frozen at `final_freeze/`) | Present locally; **not in the production image** (the image holds predictions and manifests, not the model files) |
| District aggregation | `backend/app/ml/district_product.py` with the pinned Phase 2C weights | Reusable |
| Precedent for inference on a case no observation touched | `experiments/recent_historical/infer_2024_case.py` (a frozen-model transfer probe that never reads IMD, hash-checks every input) | Uses the Track A models and one case; the pattern, not the code, carries over |

## 3. What is missing

1. A cycle-parameterised acquisition: one initialization date and cycle, all three leads, with source existence and completeness checks and a clear "not yet published" state.
2. A runtime loader for the **Track B** frozen models, with hash verification against `final_freeze/model_selection_freeze.json`, and a decision on how the model files reach the worker (the web image must stay read-only and small).
3. Online versions of the corpus quality gates: canonical rainfall reconstruction, the 0.5-degree atmospheric completeness check, finite-value and non-negative checks, and an applicability check against the frozen training ranges.
4. Lead handling for Day 1, Day 2 and Day 3 (+3 to +27, +27 to +51, +51 to +75 hours) end to end.
5. Publication: where the result is stored, how the read-only API serves it, and how it is labelled.
6. Scheduling, retries, alerts and an operator runbook.
7. Ensemble members are optional and out of scope for a first version (the frozen models use the control member).

## 4. Proposed architecture

```text
 scheduler (daily, after the NOAA cycle is published)
        |
        v
 worker (separate service, NOT the web API)
   1. check cycle published; fetch only the needed byte ranges
   2. canonical reconstruction + QC gates (fail closed)
   3. features + forecast-only regime probabilities
   4. frozen M1..M4 + calibrated heavy / very-heavy probabilities
   5. district aggregation with the pinned weights
   6. write an immutable, hash-manifested result bundle
        |
        v
 object storage (versioned: cycle / lead / model / manifest)
        |
        v
 read-only science API  --->  frontend "Latest experimental cycle" view
```

Principles carried over from the rest of the project:

- The existing API stays **read-only and fail-closed**; it only serves a finished, hash-verified bundle. All heavy dependencies (GRIB decoding, model libraries) stay in the worker, so the web image does not grow.
- Every published bundle records the source cycle and its message hashes, the frozen model hashes, the code version, the QC verdicts and the status. A bundle that failed any gate is **not published**; the previous good cycle remains visible with its age shown.
- Labels, always visible: "EXPERIMENTAL FORECAST — frozen models, no verification yet — not an official warning". No skill number is shown for a cycle without observations.
- No observation is read at inference time; a test asserts the worker has no access path to IMD data.
- Frozen models are never retrained or recalibrated by the worker.

## 5. Phases with acceptance criteria

| Phase | Work | Acceptance |
|---|---|---|
| L0 | Owner decisions in section 7; confirm the NOAA archive retention and the cycle publication time from official documentation | decisions recorded |
| L1 | Single-cycle replay: run the worker path on an already-known **historical** cycle and reproduce the frozen Track B outputs exactly (rainfall, features, regime probabilities, M1 to M4, probabilities) | bit-identical or within the project's float tolerance for every case in a chosen sample; this is the scientific gate |
| L2 | QC gates online, each tested with a deliberately broken input (missing message, fill values, wrong units, truncated range) | every broken input is refused and nothing is published |
| L3 | Result bundle format, storage and the read-only API endpoint, with tamper tests like the existing evidence endpoints | served equals stored; a modified file returns an integrity failure |
| L4 | Scheduling, retries, alerting, runbook and a dry run of several consecutive new cycles | a missed or late cycle is shown as such, never silently reused |
| L5 | Frontend "Latest experimental cycle" view with the labels above and the age of the data | labels cannot be hidden; a stale cycle is visibly stale |

L1 is the key proof: if the worker cannot reproduce the frozen historical outputs exactly, nothing about a new cycle can be trusted.

## 6. Risks

- **Source availability.** Public NOAA operational data have no stated long-term retention; the archive used for 2023 to 2025 may not remain; a live service depends on NOAA's publication timing.
- **Model drift.** The GEFS configuration can change after the training years (the project already documented that operational-era 700-hPa humidity sits above the reforecast training distribution, `docs/82` section 14); the frozen models would then be extrapolating. The applicability check and a visible warning are required, and a skill claim is impossible until observations arrive.
- **Free-tier hosting.** A scheduled worker with GRIB decoding, plus storage, is a different class of service from the current web API; a free tier may not suffice (unverified).
- **Observation delay.** IMD gridded observations arrive months later, so the live view can never show verification promptly.
- **Scientific freeze.** Any model change (for example the geography-aware candidate in `docs/124`) would need its own protocol and a new freeze before it could be served.

## 7. Decisions needed from the project owner

1. Is a live view wanted, given it cannot show verified skill? If yes, is "experimental, unverified" labelling acceptable for judges and users?
2. Where may the worker run and be stored (local machine, a free service, a paid service)? This changes the cost and reliability sections above.
3. Which models would be served first: the frozen M1 (the preselected primary) alone, or M1 to M4 and the probabilities?
4. Is the worker allowed to download from NOAA on a schedule (the existing, approved source; the volume per cycle has not been measured)?

Gate: `P2_4_LIVE_INFERENCE_DESIGN_DOCUMENTED_AWAITING_OWNER_DECISIONS`.
