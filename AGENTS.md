# AGENTS.md — VarshaSetu / SIH26080

## 1. Purpose

This repository implements **VarshaSetu — Regime-Aware AI Post-Processing of Monsoon Rainfall Forecasts** for **SIH26080**, issued by the Ministry of Earth Sciences (MoES), National Centre for Medium Range Weather Forecasting (NCMRWF).

The software must become a scientifically defensible NWP post-processing system. It must **not** be developed as a generic weather dashboard or a standalone black-box rainfall predictor.

The target operational idea is:

> Real NWP forecast → forecast-time feature engineering → atmospheric regime probabilities → regime-conditioned post-processing → corrected rainfall grid → heavy/very-heavy rainfall probabilities → calibration → district product → verification → VarshaSetu dashboard.

## 2. Read these documents before changing architecture, ML, data, verification, or scientific UI

Mandatory reading order:

1. `docs/00_INDEX.md`
2. `docs/01_SIH26080_PROBLEM_STATEMENT.md`
3. `docs/02_PROJECT_AUDIT.md`
4. `docs/03_CURRENT_IMPLEMENTATION.md`
5. `docs/04_TARGET_ARCHITECTURE.md`
6. `docs/06_DATA_PROVENANCE.md`
7. `docs/08_REGIME_METHODOLOGY.md`
8. `docs/09_ML_METHODOLOGY.md`
9. `docs/10_VERIFICATION_PROTOCOL.md`
10. `docs/11_SCIENTIFIC_CONSTRAINTS.md`
11. `docs/14_ACCEPTANCE_CRITERIA.md`

For frontend work also read `docs/13_UI_DATA_CONTRACT.md`.
For API work also read `docs/12_API_CONTRACT.md`.
For deployment work also read `docs/18_DEPLOYMENT_AND_OPERATIONS.md`.

## 3. Highest-level engineering rules

### 3.1 Preserve working architecture unless evidence justifies change

Do **not** rewrite the project from scratch.

Preserve and incrementally improve:
- React/Vite frontend structure.
- FastAPI backend.
- Existing chronological evaluation concept.
- Linear MOS baseline.
- Existing global ML baselines.
- Regime classifier structure where reusable.
- Regime-specific specialist model idea.
- Verification module.
- Model comparison/ablation UI concept.
- Historical replay/sandbox concept.

### 3.2 Scientific correctness outranks UI polish

Priority order:

1. Reproducibility.
2. Dataset provenance.
3. Forecast-time causal validity.
4. Official SIH26080 mandatory requirements.
5. Correct verification.
6. Regime-aware technical differentiation.
7. Honest dashboard storytelling.
8. Deployment/production polish.

Do not spend development time on cosmetic features while a higher-priority scientific blocker remains unresolved.

### 3.3 Never fabricate scientific values

Never create or retain:
- Hardcoded “accuracy” percentages presented as live results.
- Fake confidence scores.
- Random or hand-written threshold probabilities.
- Multipliers that simulate rainfall trajectories.
- Static verification values masquerading as API-derived values.
- Synthetic “observations” presented as measured observations.
- “PASS” scientific audits that are not actually executed.
- Claims that a dataset is official, operational, real NWP, rain-gauge truth, calibrated, or leakage-free unless the repository can demonstrate it.

A UI placeholder may exist only when clearly labeled `DEMO PLACEHOLDER — NOT SCIENTIFIC OUTPUT`.

### 3.4 Never use future information during forecast inference

Dynamic predictors must be information available at forecast initialization or derived from the forecast itself.

Allowed examples:
- NWP precipitation at lead time.
- Forecast U/V wind.
- Forecast humidity.
- Forecast pressure.
- Forecast geopotential/vorticity.
- Forecast TCWV.
- Forecast ensemble statistics.
- Static elevation, latitude, longitude, coastline distance.
- Calendar fields known at forecast issue time.

Disallowed unless explicitly part of a retrospective diagnostic mode:
- Observed temperature at the forecast valid time.
- Observed humidity at valid time.
- Observed rainfall.
- Future reanalysis state.
- Targets or features calculated from targets.

A column name alone does not establish causal validity. Verify provenance.

### 3.5 Reanalysis is not raw NWP forecast

ERA5/IMDAA can support:
- regime-label research,
- atmospheric diagnostics,
- climatology,
- retrospective analysis.

Do not call reanalysis a raw NWP forecast in operational post-processing experiments.

### 3.6 Respect rainfall accumulation windows

The quarantined legacy CSV prototype targeted 6-hour rainfall. The canonical
Phase 1F–4J retrospective and operational-era experiments instead target
24-hour accumulation windows. Operational-era Day 1/2/3 windows are
+3→+27 h, +27→+51 h, and +51→+75 h, respectively. IMD heavy/very-heavy
categories used in these experiments are 24-hour cumulative categories.

Do not apply a 24-hour category threshold directly to a 6-hour target and call it equivalent.

### 3.7 Spatial metrics require spatial data

FSS requires aligned 2-D forecast/observation fields or another explicitly defined neighbourhood grid.

Never invent an FSS from station-only records.

## 4. Current known blockers

Scope note (2026-09-23): the blocker list below is the original Phase 0 audit
of the legacy `GOA_CLEAN.csv`/API path. It is not a status statement about the
separately governed canonical Phase 1F/2A/2B research corpora. Several listed
controls have since been repaired (including portable data paths and the
declared XGBoost dependency); Phase 2A added reproducible forecast-only
pseudo-label artifacts, and the bounded Phase 2B rainfall comparison is
reported in `docs/58`–`docs/62`. Those later artifacts do not rehabilitate the
legacy CSV/models, satisfy the broader Phase 0/1 release gate, or authorize
scientific API exposure. The legacy readiness gate and scientific endpoints
must remain blocked unless separately re-evaluated and approved.

Treat these as unresolved until code + tests + documentation prove otherwise:

- `backend/app/core/config.py` contains a machine-specific Windows CSV path.
- Checked-in `data/GOA_CLEAN.csv` differs from the dataset referenced by the saved report.
- Checked-in CSV does not contain `regime_id`.
- Current training cannot be reproduced from the checked-in dataset.
- Existing tests contain stale split assumptions.
- `xgboost` is used but not declared in the backend requirements observed in the audited ZIP.
- “XGBoost 2000” saved experiment is not a genuine distinct 2000-tree experiment.
- Current feature pipeline may use contemporaneous meteorological observations and therefore may leak valid-time information.
- Raw NWP provenance is unverified from the repository.
- Heavy/very-heavy thresholds are applied to the wrong accumulation period in the audited version.
- Heavy-rain test sample is extremely small.
- 2025 very-heavy test positives are zero in the saved report context.
- FSS is missing.
- Gridded forecast processing is missing.
- District polygon aggregation is missing.
- Several frontend values/charts are hardcoded or constructed.
- Authentication and notifications are simulated UI features.
- Some scientific audit/Jury Defense claims are stronger than the code evidence supports.

## 5. Development phases

Follow `docs/05_ROADMAP.md`.

The intended order is:

- **Phase 0 — Stabilize and make reproducible**
- **Phase 1 — Mandatory SIH26080 compliance**
- **Phase 2 — Scientific credibility**
- **Phase 3 — Technical differentiation**
- **Phase 4 — Demo excellence**
- **Phase 5 — Production readiness**

Do not jump to Phase 3/4 features when Phase 0/1 acceptance criteria are failing unless the user explicitly instructs otherwise.

## 6. Required baseline experiment ladder

The scientific benchmark should eventually compare:

1. Raw NWP.
2. Linear MOS or another strong transparent statistical baseline.
3. Global non-regime ML.
4. Hard regime-aware ML.
5. Soft probabilistic regime Mixture-of-Experts.
6. Optional EMOS/ensemble calibration when ensemble data are available.

Do not claim regime awareness adds skill unless a regime-aware method beats an appropriate non-regime post-processor on held-out data for relevant metrics.

## 7. Testing expectations

After meaningful backend/ML changes:
- run backend tests,
- run scientific unit tests,
- run reproducibility checks,
- validate no target/future leakage,
- validate nonnegative rainfall outputs,
- validate metric formulas,
- validate train/validation/test temporal separation.

After meaningful frontend changes:
- run TypeScript build,
- run lint if configured,
- verify scientific UI fields come from documented API fields,
- check no hardcoded scientific metrics were introduced.

After cross-stack changes:
- run API smoke tests,
- exercise at least one historical replay end-to-end,
- compare raw → corrected → observed outputs.

If a required check cannot run because of missing data/dependency, report that explicitly rather than silently passing.

## 8. Code-change protocol for Codex

For each nontrivial task:

1. State the current problem in one paragraph.
2. Identify files to inspect before editing.
3. Verify existing behavior.
4. Make the smallest coherent change.
5. Add or update tests.
6. Run relevant checks.
7. Update affected documentation.
8. Report:
   - files changed,
   - tests run,
   - test results,
   - unresolved risks,
   - scientific assumptions.

## 9. Change-scope discipline

Avoid:
- unnecessary framework migrations,
- new databases before required,
- splitting into microservices prematurely,
- frontend redesign without scientific purpose,
- replacing classical baselines just to appear more “AI-heavy,”
- deep-learning expansion before data validity and verification are correct.

Prefer:
- small reviewable commits,
- pure functions for scientific calculations,
- typed API contracts,
- explicit model/data metadata,
- versioned experiment reports,
- reproducible preprocessing.

## 10. Naming and semantics

Use terms precisely:

- **Raw NWP** only for actual forecast output with known source/cycle/lead.
- **Observation/reference** only for the documented truth source.
- **Calibration** only when probabilistic calibration is trained/evaluated.
- **Confidence** should not be used as a substitute for calibrated probability.
- **Regime probability** means model-estimated regime probability, not arbitrary softmax over handwritten scores unless explicitly labeled heuristic.
- **Historical replay** for retrospective rows containing known observations.
- **Operational forecast** only when inference can run without future observations.

## 11. AGENTS.md precedence

A more specific nested `AGENTS.md` may add local rules for a subtree, but must not weaken the scientific constraints in this file unless the user explicitly directs a change and the corresponding documentation is updated.

## 12. Definition of done

A task is not done because the UI renders or a function exists.

A task is done when:
- the implementation is connected end-to-end,
- tests cover the core behavior,
- output semantics are honest,
- inputs are scientifically valid,
- the relevant acceptance criteria are met,
- documentation matches the code.

## 13. Local Hardware and Compute Optimization Policy

The primary VarshaSetu development machine is an HP Victus 15-fa2309TX running
Windows 11, with an Intel Core i7-13620H (10 cores / 16 threads), 24 GB DDR5
RAM, an NVIDIA GeForce RTX 5050 Laptop GPU with 8 GB VRAM, and a 1 TB NVMe SSD.
Assume heavy computation runs on AC power with adequate cooling.

Future Codex work on this machine must follow these persistent rules:

- Maximize safe CPU and GPU utilization where doing so preserves scientific
  correctness, reproducibility, system stability, and interactive usability.
- Prefer process-based parallelism for CPU-bound ecCodes/GRIB decoding and
  transformation work. Prefer threads for I/O-bound acquisition work.
- Avoid nested thread oversubscription. Coordinate process counts with native
  library thread counts rather than multiplying both without a measured reason.
- Retain operating-system and UI headroom; do not force all 16 hardware threads
  to remain continuously saturated.
- Keep normal peak RAM use at approximately 18--20 GB maximum. Use chunked,
  Zarr-backed, streaming, or otherwise bounded processing instead of loading an
  entire corpus into memory.
- Use CUDA/GPU acceleration for XGBoost or future PyTorch workloads only when it
  is scientifically equivalent, deterministic to the required standard, and
  measurably faster for the actual workload.
- Do not assume scikit-learn automatically uses the GPU. Verify the execution
  backend and acceleration path explicitly before making performance claims.
- Aggressively reuse validated, hash-verified cache artifacts. Avoid duplicate
  decoding, redundant data copies, and unnecessary recomputation.
- Preserve deterministic scientific outputs, manifests, and hashes across
  hardware-aware optimizations. Performance changes must not silently alter
  numerical semantics, eligibility, lineage, or audit evidence.
- Benchmark concurrency on representative bounded workloads before permanently
  changing any frozen acquisition or processing worker settings. Record the
  benchmark, resource use, hardware/software context, and scientific-equivalence
  check that justify the change.

This policy does not override any scientific, provenance, validation, safety,
versioning, or governance rule above. Frozen concurrency settings remain frozen
until a separately authorized, documented benchmark justifies a versioned or
policy-approved change.
