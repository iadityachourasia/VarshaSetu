# Development Roadmap

## Priority philosophy

Do the highest-dependency scientific work first.

A visually complete feature that rests on invalid data is lower value than an incomplete UI backed by a correct forecast pipeline.

---

# Phase 0 — Stabilize and Reproduce

## Goal

A clean clone can install, test, train or load documented artifacts, and produce an honest baseline report.

### P0.1 Remove machine-specific dataset path
- **Files:** `backend/app/core/config.py`, loader.
- **Dependency:** none.
- **Difficulty:** low.
- **Acceptance:** project resolves data path from repo/config/environment.

### P0.2 Resolve dataset identity
- establish whether `GOA_DATA (1).csv` is available and legitimate;
- if not, create a reproducible preparation pipeline from authoritative sources;
- document checksums.
- **Difficulty:** medium-high.
- **Impact:** critical.

### P0.3 Reproduce `regime_id`
- create a documented generation/ingestion mechanism;
- never depend on an undocumented external column.
- **Difficulty:** medium-high.

### P0.4 Synchronize tests with actual split
- fix import path;
- fix row/split expectations;
- add configuration-driven assertions.
- **Difficulty:** low.

### P0.5 Complete dependencies
- add/pin XGBoost and other scientific dependencies actually used.
- **Difficulty:** low.

### P0.6 Fix mislabeled model experiment
- remove fake “XGBoost 2000” label or implement a truly distinct configuration.
- **Difficulty:** low.

### P0.7 Remove unsupported scientific UI claims
- synthetic trajectories,
- static threshold probabilities,
- hardcoded mean values,
- hardcoded PASS audit.
- **Difficulty:** low-medium.

### P0.8 Add experiment metadata
Every report must include:
- git commit,
- data hashes,
- split,
- model hyperparameters,
- feature list,
- thresholds,
- accumulation period,
- timestamp,
- seed.

---

# Phase 1 — Mandatory SIH26080 Compliance

## Goal

Meet PS-R01 through PS-R14 with a minimal but genuine scientific pipeline.

### P1.1 Real forecast source
Add archived NWP with:
- initialization,
- valid time,
- lead,
- variable metadata.

### P1.2 Forecast-time-only feature contract
Eliminate future-valid-time observations from model inputs.

### P1.3 Correct 24-hour rainfall product
Aggregate or obtain 24-hour target consistently before applying 24-hour heavy categories.

### P1.4 Gridded verification domain
Build aligned NWP/observation 2-D fields.

### P1.5 FSS
Implement and unit-test FSS for:
- multiple thresholds,
- multiple neighbourhood scales.

### P1.6 District geometry
Add district boundary source and grid-to-polygon aggregation.

### P1.7 District product API/UI
Return/render:
- corrected rain,
- probability,
- summary statistics.

### P1.8 Raw → corrected → observed comparison
One synchronized historical replay must display all three.

---

# Phase 2 — Scientific Credibility

## Goal

Make results defensible under technical questioning.

### P2.1 Dataset provenance completeness
No undocumented scientific input.

### P2.2 Strong baseline ladder
Raw, MOS, global ML, regime-aware.

### P2.3 Regime-label validation
Regime labels must have reproducible methodology.

### P2.4 Rare-event handling
Evaluate:
- class weighting,
- balanced sampling,
- event-aware training,
- longer history.

### P2.5 Probability calibration
Add:
- reliability curves,
- Brier skill,
- insufficient-event handling.

### P2.6 Lead-time stratification
Evaluate by +24/+48/+72 etc. where data permit.

### P2.7 Confidence intervals
Use bootstrap/event bootstrap where appropriate.

### P2.8 Failure-case analysis
Store examples where correction worsens raw NWP.

## Phase 2A bounded prototype outcome (2026-09-23)

The authorized bounded successor implemented a forecast-only three-class
regime pseudo-labeler and safe JSON classifier, fitted only on 2017 JJAS and
validated on 2018 JJAS. Its held-out consistency metrics do not represent
objective meteorological regime skill. The season corpus and tier counts are
in `docs/53_PHASE2A_2017_2018_CORPUS_REPORT.md`; validation interpretation is
in `docs/55_PHASE2A_REGIME_VALIDATION_REPORT.md`; the readiness boundary is
in `docs/57_PHASE2A_ACCELERATED_READINESS.md`. This does not complete the
Phase 2 baseline ladder, rare-event validation, independent regime-label
validation, calibration, confidence intervals, or failure-case analysis.

---

# Phase 3 — Differentiation

## Goal

Add technically meaningful USPs only after core validity.

### P3.1 Soft Regime Mixture-of-Experts
Use regime probabilities to blend experts.

### P3.2 Hierarchical/multi-label regime representation
Separate:
- broad monsoon state,
- synoptic driver,
- terrain/coastal forcing.

### P3.3 Physics-guided features
Examples:
- moisture flux convergence,
- low-level vorticity,
- pressure tendency where valid,
- wind × terrain gradient / upslope flow,
- coast distance,
- NWP neighbourhood features.

### P3.4 ExtremeRain specialist
Dedicated extreme module with calibrated outputs.

### P3.5 Explainable corrections
Show:
- expert weights,
- feature contributions,
- correction magnitude,
- reason codes based on actual model state.

### P3.6 Multi-scale spatial skill
FSS curves/heatmaps by:
- threshold,
- scale,
- lead,
- regime.

---

# Phase 4 — Demo Excellence

## Goal

Make the scientific proof understandable in under two minutes.

- historical held-out case selector,
- initialization and lead clearly shown,
- raw map,
- regime state,
- corrected map,
- observed map,
- error-reduction map,
- heavy-rain probability map,
- district table,
- mandated metrics,
- ablation,
- aggregate test-set results,
- known limitations.

No fake animation/data.

---

# Phase 5 — Production Readiness

Only when needed:
- scheduled forecast ingestion,
- data quality monitoring,
- object storage,
- PostGIS,
- model registry,
- background jobs,
- observability,
- auth/RBAC,
- audit logs,
- drift monitoring,
- automated retraining gates.

---

# Do Not Waste Time On

Until Phase 1/2 are complete:
- chatbot,
- LLM explanation layer,
- voice,
- native mobile app,
- blockchain,
- 3-D globe,
- social media monitoring,
- elaborate authentication,
- full microservices migration,
- Kubernetes,
- nationwide radar dependency,
- huge transformer architecture,
- cosmetic redesign unrelated to scientific proof.


## Phase 2B bounded rainfall model comparison outcome (2026-09-23)

The authorized retrospective comparison is complete for the frozen 2017/2018/2019 roles. See `docs/58`–`docs/62` and `data/manifests/phase2b/`. This closes only the bounded raw/MOS/global/hard/soft model comparison; it does not complete the broader Phase 2 credibility gate, FSS, calibration, district products, API integration, or operational readiness.

## Phase 2C bounded scientific-product outcome (2026-09-23)

The separately authorized Phase 2C built distinct 2017-trained heavy and
very-heavy classifiers, used 2018 initialization-grouped calibration/selection,
then made a one-time 2019 probability/FSS/district evaluation only after a
hash-written selection freeze. The frozen Phase 2B M2 deterministic model was
not retrained or reselected. See `docs/63`–`docs/67` and
`data/manifests/phase2c/`. In 2019 Raw GEFS remains stronger than every
corrected model (M1-M4; `docs/64` for M2, `docs/108` for all) on deterministic FSS and on CSI/ETS
at the extreme thresholds; the dedicated probability products
have positive 2019 BSS relative to 2017 climatology but imperfect reliability.
The new read-only `/api/science` serves historical prototype artifacts only.
Legacy API blocks, live-ingestion limitations and operational readiness remain
unchanged. Frontend integration is a subsequent, separately authorized task.

## Phase 3A independent scientific frontend (2026-09-23)

The separately authorized `frontend-v2/` rebuild is a Next.js read-only
historical interface over frozen Phase 2B/2C APIs. The legacy Vite
`frontend/` remains intact until a routing cutover is explicitly chosen.
Phase 3A adds no scientific training or metric changes. Architecture,
scientific UI semantics, design system, tests and demo path are in
`docs/68`–`docs/72`. This is demonstration readiness only, not live
operational forecast readiness; the broader Phase 0/1/2 caveats above
remain historically preserved.

## Phase 3B focused cartography upgrade (2026-09-23)

The separately authorized `frontend-v2/` map upgrade adds OpenFreeMap
geographic styles, shared MapLibre controls/lifecycle, mask-aware display-only
weather interpolation, exact grid mode, and a pinned-geometry offline fallback.
It does not alter scientific artifacts or introduce operational forecasting.
See `docs/73_PROFESSIONAL_MAPPING_SYSTEM.md` for scope, provenance and QA.
