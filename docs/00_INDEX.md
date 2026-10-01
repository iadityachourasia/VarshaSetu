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
| `98_ADVANCED_METEOROLOGICAL_PRODUCTION_FRONTEND.md` | Phase 5A.3: Verification Skill Cube, Six-Season month×year matrix, Provenance DAG + Holdout Governance + finalized Audit page, Judge Story Mode, a canonical model/semantic color system and metric-definition module, a real (self-verified) science-copy-guard test -- and an honest BLOCKED verdict on synoptic meteorology (wind vectors/contours/isobars), confirmed blocked by absent wide-domain atmosphere data plus a newly-found real hash-integrity failure on Track A's own checked-out manifest | Before attempting synoptic meteorology, before trusting any "verified" claim about the Skill Cube or `/verification` without a live backend, and before assuming Track A's backend is runnable in a sandboxed checkout without first checking its manifest hash |
| `presentation/OFFICIAL_DEMO_CASES.md` | Phase 5B: the official/backup 2025 (Track B) demo cases and the preserved 2019 (Track A) anchor case, with full non-cherry-picked selection reasoning, backing the `?demo=official` preset and `scripts/demo/preflight-demo.ps1` | Before changing the official demo case, the `?demo=official` preset, or the preflight script's Track B checks |
| `presentation/ROUTE_INVENTORY.md` | Phase 5B: honest WORKING / WORKING_WITH_LIMITATION classification of all 12 routes, two real page-level reliability bugs found and fixed this phase (`/verification`, `/methodology` each blanked entirely on a Track A outage despite mostly/partly not needing it), and the exact boundary of what could be verified in this sandbox | Before the judge walkthrough, before claiming any route is "fully working," and before touching `/verification` or `/methodology`'s data-fetching structure again |
| `presentation/FINAL_PPT_FACTS.md` | Phase 5B: single sourced fact sheet for slide decks -- every canonical number, the sanctioned-vocabulary table, and what is genuinely not built | Before writing or updating any slide deck, handout, or spoken narration |
| `presentation/FINAL_ARCHITECTURE_DIAGRAM_SPEC.md` | Phase 5B: spec for one architecture slide showing what is actually built and demoed (two non-pooled lanes), explicitly distinct from `docs/04`'s aspirational target flow | Before drawing or commissioning an architecture diagram for the deck |
| `presentation/FINAL_DEMO_NARRATION.md` | Phase 5B: 90-second / 2-minute / 30-second narration scripts aligned scene-for-scene with Story Mode, plus delivery notes and the backup-case switch procedure | Before rehearsing or delivering the live demo |
| `presentation/JUDGE_QA.md` | Phase 5B: anticipated judge questions by theme (provenance, regime awareness, extreme-skill limitation, scope gaps, reproducibility) with honest, sourced answers | Before the judge Q&A session |
| `presentation/FINAL_SUBMISSION_CHECKLIST.md` | Phase 5B: this repo's own UI/Demo acceptance gates checked off with evidence, full regression results (73/74 Vitest, 13/35 Playwright -- every failure traced to the sandbox's missing backend/corpus, zero regressions from this phase), and an honest list of what needs the real dev machine (screenshot pack, PowerShell preflight execution) before demo day | Before declaring the submission ready, and as the direct input to `docs/99`'s decision gate |
| `99_FINAL_SIH_DEMO_FREEZE.md` | Phase 5B release-candidate record: what was built and fixed this freeze phase, full regression evidence, honest real-dev-machine gap list, and the `SIH_DEMO_READY_WITH_MINOR_NOTES` decision gate | Before demo day, and before starting any further product-development cycle on this branch |
| `100_REAL_MACHINE_VERIFICATION_OF_CLOUD_SESSION.md` | Closed out every "not run here, needs a live backend" limitation the 5A.2D/5A.3/5B cloud session flagged: ran the full backend+frontend test/E2E suites for real (193 backend, 76 Vitest, 35/35 Playwright), confirmed the Track A manifest hash was a sandbox-checkout artifact (not real), and found+fixed 4 real defects only reachable with live data (mobile header overflow, a stale route guard blocking year-adaptive Extreme Rain, a wrong 2024 probability-metrics shape assumption, a dropped false-alarm-ratio caveat) plus 5 real-backend-only test-locator bugs in the cloud session's own new specs | Before merging `master-3xhx5v`, and as the evidence trail for exactly what changed since `docs/99`'s freeze |
| `101_FINAL_FULL_STACK_QA_AND_STABILIZATION.md` | Full-stack QA/stabilization pass (no new features, no retraining): re-verified every canonical scientific number live against the real backend, audited the error contract/security/copy/accessibility/responsive surface, found and fixed a real header-overlap bug and its downstream 834px responsive-overflow consequence, verified the demo launcher end-to-end (`DEMO_PREFLIGHT_RESULT=READY`, clean restart, no zombies), and reached `FULL_STACK_QA_PASSED` with 35/35 Playwright and 76/76 Vitest | Before the SIH demo, as the final release-readiness record |
| `102_FREE_DEPLOYMENT.md` | Full $0 deployment: backend (Docker, ~750MB real frozen-data footprint published as a GitHub Release asset) on Render's free tier, frontend on Vercel's free tier via `SCIENCE_API_URL` + the existing `next.config.ts` rewrite, verified end-to-end with a real local Docker build serving correct live values on both tracks; explains why the repo was made public | Before deploying, redeploying, or rotating the published data-bundle release |
| `103_LIVE_FRONTEND_UI_UX_AUDIT_AND_POLISH.md` | Live 12-route visual audit, local responsive/sidebar and overview benchmark repairs, production-build screenshot matrix, browser regressions, and deployment handoff | Before publishing frontend polish or presenting the deployed UI |
| `104_FRONTEND_HARDENING_AND_POLISH.md` | Forecast timeout and fallback hardening, shared charts, responsive visual polish, full browser regression and deployment verification | Before presenting or extending the polished frontend |
| `105_VISUAL_DESIGN_AND_AI_SLOP_AUDIT.md` | Read-only local/live design critique, effective token inventory, 66-screen baseline, Story Mode clipping defect, route reviews, scorecard, and ranked design priorities | Before choosing a visual redesign direction; no UI change is authorized by the audit |
| `106_REGIME_CATEGORICAL_AND_FSS_DIAGNOSTICS.md` | Phase 4M: FSS for M0–M4 and regime/lead-stratified POD/FAR/CSI/ETS on frozen 2024 (development) and 2025 (consumed, post-hoc descriptive) grids; reproduction gate vs docs/88–89; finding that the regime-aware heavy-rain gain is confined to the Low/Depression regime and that "Raw beats corrected on FSS" holds only for the M1/M2 pairs previously measured | Before quoting any regime-aware or FSS statement; before rewording docs/60, 64, 89 or `JUDGE_QA` |
| `107_TRACK_B_DISTRICT_PRODUCT.md` | Phase 4N: Track B (2024/2025) district table/map as a read-only area-weighted aggregation of frozen grids with the Phase 2C weights shared with Track A; verification of the implementation; limits (no 2023, no district-level verification, not a frozen artifact); supersedes the "no Track B district product" statements | Before any district claim for the operational-era track, and before proposing district-level verification |
| `108_EVIDENCE_PACKAGING_AND_TRACK_A_REGIME_DIAGNOSTICS.md` | Phase 6A (P0-1): regime/lead-stratified FSS + categorical evidence for M0–M4 packaged as tracked, hash-manifested files and served read-only at `/api/science/evidence/*`; new Track A 2018/2019 M3/M4 diagnostics (frozen models, exact reproduction); finding that the Track B heavy-rain regime-aware gain does **not** replicate on Track A | Before quoting any FSS or regime-aware statement, and before building the regime/verification UI (P0-2/P0-3) |
| `109_REGIME_INTELLIGENCE_UI_COMPLETION.md` | Phase 6D (P0-2): removes the Regime "Feature in Development" state; Track A workbench and a shared regime-aware verification panel (by pseudo-regime and lead; RMSE, POD, FAR, CSI, ETS, FSS; paired differences) for both tracks, with mandatory post-hoc labels and undefined-value handling | Before changing the Regime page or quoting what it shows |
| `110_VERIFICATION_REGIME_AWARE_TAB_AND_REPORT_EXPORT.md` | Phase 6E (P0-3): Regime-aware tab/section in the Verification Lab (both tracks) and a hash-verified, downloadable verification report (Markdown/CSV/JSON) covering RMSE, ETS, CSI, POD, FAR, FSS by regime and lead, with undefined values preserved | Before changing the verification report or quoting its contents |
| `111_DISTRICT_PRODUCT_COMPLETION.md` | Phase 6B (P0-4): Track B district compare-all-models endpoint and view, per-district error and improvement vs Raw (single-case, district-mean; not a skill score), diverging error map, descriptive district history (no skill statistic), and the Historical District Decision-Support Prototype label | Before changing the district product or quoting any district-level figure |
| `112_DISTRICT_VERIFICATION_PROTOCOL.md` | Phase 6C (P0-5): APPROVED and hash-frozen district-level verification protocol v1 (E1 primary, 30 observed events, >= 5 valid cells, latitude bands) with observation-only support counts; written before any result | Before changing or quoting district-level verification rules |
| `113_DISTRICT_VERIFICATION_RESULTS.md` | Phase 6C (P0-5): execution of protocol v1 for Track B 2024/2025 - hash-manifested evidence, `/api/science/evidence/district-verification` + reports, Verification Lab District-level tab; findings: district event CSI improves for M3/M4 while district-mean error worsens, no very-heavy gain, improved/worsened counts vs chance | Before quoting any district-level skill figure |
| `114_PS_COVERAGE_AND_GOVERNANCE_REFRESH.md` | Phase 6F (P0-6): `/compliance` SIH26080 requirement-coverage page, evidence-resolved coverage manifest and endpoint, generated `docs/22` status block, and refresh of stale governance documents; planned items are never shown as implemented | Before changing requirement status, the coverage manifest, or governance documents |
| `115_COASTAL_OROGRAPHIC_REGIME_PROTOCOL.md` | Phase 7A (P0-7): APPROVED and hash-frozen v1, amended to v3 (Stages 0–2 only) — staged protocol for a per-cell geographic-forcing dimension (static sources, rule-based coastal/orographic zones, forecast-time forcing strata, pre-registered questions); no acquisition or training done yet | Before acquiring static geography or claiming any coastal/orographic result |
| `116_STATIC_GEOGRAPHY_STAGE0.md` | Phase 7B (Stage 0): `static_geography_v1` built from GMTED2010 under protocol v3 (land-mask and orographic-rule amendments recorded in docs/115 section 15), QA maps, zone counts; no results touched | Before using static geography, zones or quoting zone sizes |
| `117_ZONE_VERIFICATION_STAGE1.md` | Phase 7C (Stage 1): zone-stratified verification of frozen M0–M4 on both tracks under protocol v3; the Western Ghats coast concentrates heavy rain and is underforecast by every frozen model; the literal decision rule recommends Stage 3 but with stated confounds; Stage 3 not authorised | Before quoting any zone-level result or starting Stage 2 or 3 |
| `118_ZONE_FORCING_STAGE2.md` | Phase 7D (Stage 2): forecast-time forcing-strength strata inside the zones (training-year cut-points, frozen spec), heavy rain concentrates in the strong stratum and every frozen model underforecasts it on the Ghats coast; Stage 3 not authorised | Before quoting forcing-stratum results |
| `119_ZONE_EVIDENCE_API_AND_PAGE.md` | Phase 7E: read-only hash-chain-verified zone evidence API, Geographic Zones page, coverage row moved to PARTIAL (never implemented), verification results | Before changing the zone API, the page or the coastal/orographic coverage status |
| `120_PRODUCTION_HARDENING.md` | Phase 7F: explicit CORS, single version source, honest health, retired static audit routes, checksum-verified and retried bundle download, CI, explicit skip policy, line-ending independent governance hashes, Story Mode figures derived from evidence | Before changing CORS, health, the Dockerfile, CI or Story Mode figures |
| `121_SYNOPTIC_CHART_AND_CONTEXT_GRID.md` | Phase 8A: synoptic chart (wind, height, pressure, shading) built from the frozen 51x81 fields; the grid's georeferencing verified against Track A's stored coordinates | Before changing the atmosphere API, the synoptic chart or its coordinates |
| `122_WESTERN_DISTURBANCE_FEASIBILITY.md` | Phase 8B: western-disturbance feasibility study (investigation only): domains, verified data inventory, label sources, staged path, owner decisions; requirement stays planned | Before any western-disturbance label, download or model |
| `123_INDEPENDENT_REGIME_VALIDATION_PROBE.md` | Phase 8C: independent regime validation, source and licence probe (no labelling): objective active/break criteria, IMD best tracks, obstacles, staged path, owner decisions; requirement stays planned | Before creating any independent regime label or downloading a regime data source |
| `124_GEOGRAPHY_AWARE_MODEL_PROTOCOL_PROPOSAL.md` | Phase 9A: PROPOSED, not frozen — protocol for a geography-aware correction (M5) aimed at the Ghats-coast heavy-rain deficiency; training-year support, the independent-test blocker and its options, design, decision rule and risks; awaiting owner approval; nothing trained | Before any M5 or Stage 3 training |
| `125_LIVE_INFERENCE_DESIGN.md` | Phase 9B: live and new-cycle inference, design only: what exists, what is missing, worker architecture, phases with acceptance criteria, risks, owner decisions; requirement stays planned | Before building any live inference |
| `126_GEOGRAPHY_AWARE_MODEL_RESULTS.md` | Phase 9B: frozen-protocol results of the geography-aware correction (M5a): large replicated heavy-rain gain on the Ghats coast but over-forecasting in 2024, pre-registered rule not met, attribution undetermined, contamination notice; development-only | Before quoting any geography-aware model result or designing a follow-up |
| `127_INDEPENDENT_YEARS_SOURCE_PROBE.md` | Phase 9C: HEAD-only probe showing the NOAA GEFS objects for 2021 and 2022 (candidate independent years) exist in a 19-date sample; no download, existence is not validity | Before deciding whether to acquire independent years |
| `HARDWARE_OPTIMIZATION.md` | Local bounded-compute benchmark and hardware-aware implementation notes | Before changing concurrency or compute strategy |

## Golden rule

No document can override the official SIH problem statement.

If documentation and code disagree:
1. verify the actual code,
2. verify the official requirement,
3. update the documentation,
4. do not pretend the conflict does not exist.

## Current priorities (replaces the Phase 0-1 blocker chain)

The Phase 0-1 chain (reproducibility, provenance, causality, accumulation, pairing, FSS, districts, calibration) is resolved for the canonical research track.
What remains, in order (see `docs/22` and the app's `/compliance` page for the evidence-linked status):

```text
1. Coastal / orographic regime protocol (write, approve, then train)   - mandatory PS regime still PLANNED
2. Western-disturbance feasibility (domain, upper-air fields, labels)  - mandatory PS regime still PLANNED
3. Independent regime validation set                                   - labels are pseudo-label agreement only
4. Next-generation model (M5) after protocol approval                  - data and independent-test question first
5. Live / new-cycle inference                                          - currently historical replay only
6. Engineering hardening (CORS, versions, checksums, CI)               - see the plan's P3 list
```
