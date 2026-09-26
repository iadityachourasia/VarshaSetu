# Documentation Index

## Purpose

This directory is the working technical specification, scientific governance system, and Codex context for VarshaSetu.

### Core project/control documents

| File | Purpose | Read when |
|---|---|---|
| `01_SIH26080_PROBLEM_STATEMENT.md` | Authoritative mandatory PS baseline | Before deciding scope |
| `02_PROJECT_AUDIT.md` | Verified current weaknesses/strengths | Before modifying current code |
| `03_CURRENT_IMPLEMENTATION.md` | What genuinely exists now | Before reusing/replacing components |
| `04_TARGET_ARCHITECTURE.md` | Intended end-state architecture | Before architectural changes |
| `05_ROADMAP.md` | Ordered implementation phases | Before starting work |
| `06_DATA_PROVENANCE.md` | Dataset lineage requirements | Before any data/ML work |
| `07_DATA_SCHEMA.md` | Current and target field contracts | Before preprocessing/API changes |
| `08_REGIME_METHODOLOGY.md` | Regime definition/modeling rules | Before regime ML work |
| `09_ML_METHODOLOGY.md` | Baselines, models, training protocol | Before model changes |
| `10_VERIFICATION_PROTOCOL.md` | Metric formulas and evaluation rules | Before reporting results |
| `11_SCIENTIFIC_CONSTRAINTS.md` | Non-negotiable scientific guardrails | Always |
| `12_API_CONTRACT.md` | Current/target API semantics | Backend/frontend integration |
| `13_UI_DATA_CONTRACT.md` | Prevents fake scientific UI | Frontend changes |
| `14_ACCEPTANCE_CRITERIA.md` | Objective definition of done | Before closing tasks |
| `15_TESTING_STRATEGY.md` | Required automated checks | While implementing |
| `16_RISK_REGISTER.md` | Known failure modes/mitigations | Planning/review |
| `17_DEMO_PROTOCOL.md` | Judge-facing scientific demo flow | Demo work |
| `18_DEPLOYMENT_AND_OPERATIONS.md` | MVP and production deployment | Deployment stage |
| `19_DECISION_LOG.md` | Architecture/science decisions | Update after major choices |
| `20_SOURCE_REGISTER.md` | External authoritative sources | Scientific claims |
| `21_CODEX_TASK_TEMPLATES.md` | Ready-to-use Codex prompts | Daily development |
| `30_PHASE0_STABILIZATION_REPORT.md` | Live Phase 0 evidence, discrepancies, and blockers | Before trusting current outputs |
| `31_AUTHORITATIVE_DATA_ARCHITECTURE.md` | Source-backed Phase 1A forecast/reference decision | Before acquiring scientific data |
| `32_FORECAST_DATA_CONTRACT.md` | Exact forecast identity, timing, units, and grid rules | Forecast ingestion work |
| `33_OBSERVATION_DATA_CONTRACT.md` | Exact rainfall-reference timing, QC, and grid rules | Observation ingestion work |
| `34_REGIME_LABEL_STRATEGY.md` | Reproducible hierarchical label design; no labels generated | Before regime-label work |
| `35_DATA_ACQUISITION_PLAN.md` | Staged, storage-bounded official-data acquisition | Before any download beyond a pilot |
| `36_ONE_WINDOW_PILOT_REPORT.md` | Executed Phase 1B forecast/observation pairing evidence | Before authorizing a larger acquisition |
| `37_REGRIDDING_AND_ALIGNMENT_SPEC.md` | Validated rainfall grid/mask/conservation procedure | Before spatial preprocessing changes |
| `38_ONE_MONTH_ACQUISITION_PILOT.md` | Executed July acquisition pilot and its historical interpretation | Before reading strict Phase 1E replay results |
| `39_PREDICTOR_AVAILABILITY_REPORT.md` | Atmospheric predictor archive evidence | Before regime-input work |
| `40_DATA_VOLUME_AND_STORAGE_PLAN.md` | Measured pilot storage/network evidence | Before scaling acquisition |
| `41_MONTHLY_QC_SPEC.md` | Monthly QC and admission contract | Before monthly processing |
| `42_GEFS_ACCUMULATION_ANOMALY_REPORT.md` | Packing-aware reconstruction evidence and anomaly policy | Before rainfall reconstruction |
| `43_CORPUS_ADMISSION_POLICY.md` | Independent eligibility tiers and quarantine rules | Before creating experiment views |
| `44_PRODUCTION_ACQUISITION_PLAN.md` | Frozen retry, concurrency, and resume plan | Before production downloads |
| `45_DATASET_VERSION_AND_FREEZE_SPEC.md` | Dataset version and semantic freeze | Before changing corpus meaning |
| `46_PRODUCTION_STORAGE_AND_CHUNKING.md` | Frozen Zarr schema and retention plan | Before normalized storage changes |
| `47_2019_JJAS_CORPUS_REPORT.md` | Executed 2019 seasonal acquisition, QC, discrepancies, and admission | Before any prototype training proposal |
| `48_2019_EVENT_INVENTORY.md` | Observation-only 2019 heavy-event inventory | Prototype case review |
| `49_PROTOTYPE_TRAINING_INDEX_SPEC.md` | Eligibility-filtered future experiment indices | Before constructing splits |
| `50_RAW_GEFS_BASELINE_2019.md` | Raw c00 2019 verification; no AI claim | Baseline review |
| `51_CANONICAL_PRECIPITATION_RECONSTRUCTION.md` | Approved metadata-derived minimal-decomposition v2 method | Before rainfall reconstruction or expansion |
| `52_2019_RECONSTRUCTION_REPLAY_REPORT.md` | Executed 1,830-case v2 replay, recovery, eligibility, and baseline evidence | Before prototype methodology or acquisition expansion |
| `53_PHASE2A_2017_2018_CORPUS_REPORT.md` | Executed 2017–2018 prototype acquisition, observation pairing, QC, and tiered eligibility | Before using the train/validation corpus |
| `54_PROTOTYPE_REGIME_METHODOLOGY.md` | Forecast-only three-regime pseudo-label and classifier design | Before regime-label work |
| `55_PHASE2A_REGIME_VALIDATION_REPORT.md` | Executed deterministic 2017 fit / 2018 pseudo-label reproduction validation | Before interpreting prototype regime outputs |
| `56_FEATURE_REGISTRY_AND_LEAKAGE_GATE.md` | Executable feature availability registry and temporal leakage controls | Before adding predictors |
| `57_PHASE2A_ACCELERATED_READINESS.md` | Phase 2A readiness decision and explicit limits on downstream use | Before any accelerated scientific phase |
| `58_AUTHORITATIVE_RAINFALL_MODELING.md` | Phase 2B frozen model ladder, features, and train/validation/test protocol | Before using rainfall model artifacts |
| `59_2018_MODEL_SELECTION_REPORT.md` | Common-case validation selection and CPU/GPU check | Model selection evidence |
| `60_2019_FINAL_TEST_REPORT.md` | One-time frozen 2019 held-out model evaluation | Final prototype skill review |
| `61_REGIME_AWARE_BENEFIT_ANALYSIS.md` | Honest regime-aware vs global/raw benefit analysis | Before making skill claims |
| `62_MODEL_ARTIFACT_MANIFEST.md` | Safe artifact/cache hashes and lineage | Before loading Phase 2B artifacts |
| `63_EXTREME_RAIN_PROBABILITY_MODELING.md` | Frozen binary probability training, calibration and held-out scores | Before probability claims |
| `64_FSS_VERIFICATION.md` | Genuine 2-D threshold/scale FSS and edge/mask policy | Before spatial skill claims |
| `65_DISTRICT_PRODUCT_METHODOLOGY.md` | Pinned district geometry, license and overlap aggregation | Before district output use |
| `66_PHASE2C_SCIENTIFIC_API.md` | Read-only historical API schemas, provenance and readiness boundary | Before API/frontend integration |
| `67_VIDEO_DEMO_CASE_CATALOGUE.md` | Transparent held-out historical example selection | Before video/demo work |
| `68_FRONTEND_ARCHITECTURE.md` | Independent Next.js Phase 3A architecture and safe legacy rollback | Before frontend integration/cutover |
| `69_DESIGN_SYSTEM.md` | Dark/light tokens, scientific palette, typography and primitives | Before visual changes |
| `70_SCIENTIFIC_UI_DATA_CONTRACT.md` | Read-only API-to-view mapping and honest scientific semantics | Before frontend data changes |
| `71_FRONTEND_TESTING_AND_QA.md` | Build, unit, browser and accessibility verification protocol | Before declaring frontend done |
| `72_VIDEO_DEMO_FLOW.md` | Exact historical-video route and scientific narration | Before recording demo |
| `73_PROFESSIONAL_MAPPING_SYSTEM.md` | Phase 3B cartography, raster alignment, offline fallback and map QA | Before map changes or demo recording |
| `74_FINAL_MVP_RELEASE_CHECKLIST.md` | Phase 3C recording gate and protected-artifact checks | Before declaring recording readiness |
| `75_DEMO_LAUNCH_AND_RECOVERY.md` | Windows production launcher, preflight, shutdown and legacy rollback | Before operating the demo |
| `76_SIH_VIDEO_STORYBOARD.md` | Timed 3–4 minute sequence using three official cases | Before recording |
| `77_SIH_VIDEO_NARRATION.md` | Scientifically bounded spoken script | During recording |
| `78_SIH_RECORDING_SHOT_LIST.md` | Exact pages, case IDs, map modes, interactions and capture settings | During recording |
| `79_FINAL_DEMO_VERIFICATION.md` | Production tests, API/hash audit, screenshots, performance and remaining risks | Release handoff |
| `80_RECENT_HISTORICAL_FEASIBILITY.md` | Phase 4A actual 2023–2025 IMD/NOAA access, 2024 operational transfer probe, QC and decision gate | Before any recent-historical expansion |
| `81_SEVEN_DAY_OPERATIONAL_EVALUATION_2024.md` | Phase 4B predeclared seven-day 2024 operational GEFS source/QC/frozen-model external evaluation and limitations | Before any operational-transfer claim or expansion |
| `82_OPERATIONAL_REFORECAST_COMPARABILITY_AUDIT.md` | Phase 4C cached-source GEFS reforecast/operational packing, accumulation, feature-shift and applicability audit | Before operational-corpus/QC/OOD proposals |
| `83_OPERATIONAL_CORPUS_PROTOCOL_2023_2025.md` | Phase 4D frozen 2023–2025 operational GEFS/IMD corpus design, source-continuity gates, split, holdout, acquisition and resource plan | Before Phase 4E inventory/acquisition |
| `84_OPERATIONAL_CORPUS_SOURCE_INVENTORY.md` | Phase 4E index-only NOAA source inventory, cross-year compatibility, selected-range plan, and payload-acquisition decision gate | Before any Phase 4F selected-byte acquisition |
| `85_OPERATIONAL_CORPUS_PAYLOAD_ACQUISITION.md` | Phase 4F exact selected-range acquisition, decoded metadata compatibility, unchanged source QC, and year-level source eligibility | Before operational feature generation or model work |
| `86_OPERATIONAL_FEATURE_DATASET_2023_2025.md` | Phase 4G source-only operational feature construction, paired 2023/2024 targets, sealed 2025 inputs, and incomplete probability-schema gate | Before operational-era model-development planning |
| `87_OPERATIONAL_MODEL_DEVELOPMENT_PROTOCOL.md` | Phase 4H leakage-safe, protocol-only 2023 cross-fit / 2024 selection design and 2025 sealed-test gate | Before Phase 4I model execution |
| `88_OPERATIONAL_MODEL_DEVELOPMENT_2023_2024.md` | Historical Phase 4I record of 2023 OOF training, 2024 selection and the then-sealed 2025 readiness state | For pre-unseal selection chronology; 2025 has since been consumed |
| `89_OPERATIONAL_FINAL_TEST_2025.md` | Phase 4J one-time authorized 2025 operational-era final test, frozen primary result, extremes, FSS, probabilities and holdout-consumption audit | Before any operational-era performance claim |
| `90_INDEPENDENT_FINAL_SCIENTIFIC_AUDIT.md` | Phase 4K independent recalculation, claim audit and documentation/frontend discrepancy ledger | Before public scientific claims |
| `91_SCIENTIFIC_COMMUNICATION_ALIGNMENT.md` | Phase 4L canonical claims, 2019/2025 communication boundary and correction verification | Before presentation, frontend copy or demo narration |
| `92_OPERATIONAL_SCIENCE_PRESENTATION_API.md` | Phase 5A.1 read-only presentation API over the frozen 2023-2025 corpus: routes, integrity model, year capability matrix, known limitations | Before any frontend integration of Track B (2023-2025) data |
| `93_OPERATIONAL_ATTRIBUTION_AND_FRONTEND_CLIENT.md` | Phase 5A.1B proof of the 2024 model-output and 2023-2025 regime row/pixel attribution, the upgraded capability matrix, and the frontend-v2 Zod client for the operational API | Before exposing or consuming any Track B per-case model/regime grid |
| `94_SIX_YEAR_EXPLORER_AND_SYNOPTIC_FRONTEND.md` | Phase 5A.2 status: the already-substantial existing six-year frontend, the structured `{code, detail}` error contract, the District Track-B capability fix, and the honestly-scoped remaining gaps | Before further /forecast, /casebook, /ensemble, /regimes, or /districts frontend work |
| `95_LIVE_OPERATIONAL_FRONTEND_DATA_MIGRATION.md` | Phase 5A.2B: migrates Forecast (Track B) and Data Quality to the live operational API with a verified static fallback layer; a real Zod-validation-bypass bug found and fixed in the fallback logic; honest list of pages not yet migrated | Before migrating Casebook/Ensemble/Regimes/Extremes/Verification, or touching the fallback/data-source model |
| `96_COMPLETE_LIVE_SCIENCE_PAGE_MIGRATION.md` | Phase 5A.2C: extended live case index (selector/casebook metadata), live-API-primary Casebook/Ensemble/Regime Intelligence pages, new `/metrics/ensemble` endpoint; honest scope note that Extreme Rain/Verification remain static | Before migrating Extreme Rain or Verification, or extending the case-index schema again |
| `97_EXTREME_RAIN_AND_VERIFICATION_LIVE_MIGRATION.md` | Phase 5A.2D: year-adaptive live-API-primary Extreme Rain (4 modes) and a 7-tab Verification, a shared `operational-charts.tsx` component library, 4 new Playwright specs (2 actually run/passing, 2 needing a live backend not present in that session), and the exact honest boundary of what was/wasn't verified | Before further Extreme Rain/Verification work, before adding a cross-year Skill Cube, or before trusting any "verified live" claim about Track B without re-checking against a real backend |
| `HARDWARE_OPTIMIZATION.md` | Local bounded-compute benchmark and hardware-aware implementation notes | Before changing concurrency or compute strategy |

## Golden rule

No document can override the official SIH problem statement.

If documentation and code disagree:
1. verify the actual code,
2. verify the official requirement,
3. update the documentation,
4. do not pretend the conflict does not exist.

## Current highest-priority blocker chain

```text
Repository reproducibility
        ↓
Data provenance
        ↓
Forecast-time causality
        ↓
Correct rainfall accumulation
        ↓
Real gridded NWP/observation pairing
        ↓
FSS + district product
        ↓
Regime-model improvement
        ↓
Probability calibration
        ↓
Demo polish
```
