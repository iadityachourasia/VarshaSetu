# Prioritized Backlog

> Status update (Phase 6, 2026-10-01): boxes were re-checked against the repository. Ticked items cite their evidence; unticked items are open. The live, evidence-linked view of PS coverage is the app's `/compliance` page (`docs/22`).

## P0 — Do immediately

- [x] Replace absolute dataset path.
- [x] Identify the checked-in prototype file exactly; scientific authority remains unverified and training is blocked.
- [x] Create data manifest/checksum file.
- [x] Restore/rebuild regime labels reproducibly. (Canonical research track: forecast-only pseudo-labels reproduce exactly, `docs/55`; the legacy-CSV labels remain unrecoverable and quarantined.)
- [x] Fix backend import/test setup.
- [x] Synchronize split tests.
- [x] Add XGBoost to requirements and pin environment.
- [x] Remove fake XGBoost-2000 from executable training/report generation; legacy file remains quarantined.
- [x] Remove stale metrics endpoint aliases by blocking unverified metrics entirely.
- [x] Fix report record-count semantics for future reports.
- [x] Fix non-DataFrame probability inference bug.
- [x] Remove hardcoded scientific values from the reachable frontend; legacy pages are unreachable during stabilization.
- [x] Replace operational UI with explicit Phase 0 scientific-readiness status.
- [x] Replace unsupported provenance/audit statements with executable fail-closed status.

## P1 — Mandatory PS

- [x] Select a source-backed primary/fallback forecast-reference architecture.
- [x] Define forecast/observation schemas, exact 24h windows, target/context grids, and staged storage plan.
- [x] Add strict metadata/checksum/GEFS step-range validators and unit tests.
- [x] Validate public NOAA GEFS index access and record checksum/limitations; Phase 1A also decoded one probe field.
- [x] Obtain one official IMD NetCDF with visible terms/disclaimer, native metadata, fill value, and checksum; no explicit version attribute exists.
- [x] Decode one official GEFS precipitation message and validate target-domain geographic subsetting (in-memory probe only).
- [x] Produce one exact +3..+27 h / 03–03 UTC paired grid with source and derived manifests; remains training-ineligible.
- [x] Measure one-month transfer, disk, RAM, event coverage, and failure rate; result PARTIAL, so bulk is not approved.
- [x] Acquire a bounded July 2019 genuine archived forecast pilot; full historical corpus remains unauthorized.
- [x] Add init/valid/lead metadata to Phase 1C source lineage.
- [x] Create forecast-time-only feature registry. (`docs/56`)
- [x] Create repeated exact 24h raw-NWP pilot products; one archive inconsistency remains quarantined.
- [x] Build the bounded monthly aligned-grid pilot; production corpus pipeline remains pending.
- [x] Implement FSS. (`docs/64`, `docs/108`: all five models, both tracks)
- [x] Add district geometry. (`docs/65`)
- [x] Aggregate grid to district. (`docs/65`, `docs/107`)
- [x] Add district map/table. (`docs/107`, `docs/111`)
- [x] Raw/corrected/observed/error maps. (Forecast & Atmosphere; district error map `docs/111`)

Phase 1B checks off one source-backed timing/24-hour pairing only. It does not
check off a historical corpus, full predictor acquisition, repeated reliability,
training readiness, FSS, or district products.

Phase 1C validates one full calendar month but remains PARTIAL. Immediate P1
work is to resolve the July 22 `p01` accumulation exception and review/freeze the
historical acquisition/QC plan. It does not check off training readiness, FSS,
district products, regime labels, or the multi-year corpus.

## P2 — Scientific

- [ ] Validate regime label methodology. (Only pseudo-label agreement exists; independent validation is PLANNED, see `/compliance`. Source probe done in `docs/123`; waiting on owner decisions on the rainfall climatology and the depression-record terms.)
- [x] Evaluate event-aware extreme model. (`docs/63`, `docs/89`)
- [x] Reliability diagram.
- [x] Brier Skill Score.
- [x] Bootstrap uncertainty. (`docs/108`, `docs/113`; optimistic intervals)
- [x] Lead-time breakdown.
- [x] Failure-case archive. (Event Casebook)
- [x] Model/data/version metadata. (`docs/62`)

## P3 — USP

- [x] Soft MoE. (M4)
- [ ] Multi-label/hierarchical regimes. (Design in `docs/08`, `docs/34`; protocol not yet approved.)
- [x] Moisture/vorticity features. (regime diagnostics, `docs/54`)
- [ ] True orographic upslope feature. (No static terrain data in the frozen schema yet.)
- [ ] Extreme specialist.
- [ ] Explainable correction contributions.
- [x] Multi-scale FSS dashboard. (Verification Lab)

## P4 — Demo

- [x] polished replay selector,
- [x] judge mode, (Story Mode)
- [x] aggregate evidence,
- [x] offline cached demo, (Track B static fallback and offline map style; Track A is live-API only)
- [x] limitations panel.

## P5 — Production

- [ ] scheduled forecast ingestion,
- [ ] object storage,
- [ ] PostGIS if needed,
- [ ] observability,
- [ ] auth/RBAC if required,
- [ ] drift/model upgrade monitoring.
# Phase 1D backlog update (2026-09-19)

Completed: July 22 forensic classification, packing-aware fail-closed policy,
eligibility tiers, monthly gate, comparison intersection, immutable v1 plan,
and production storage/chunk/retry design. Next: acquire exactly one complete
JJAS season under v1 in reviewed monthly batches, run monthly plus seasonal QC,
and stop for review. Multi-year acquisition beyond that season, ML training,
regime labels, and scientific endpoint activation remain blocked.

## Status after Phase 7F / 8A–8C (2026-10-01)

- [x] Production hardening: explicit CORS, single version source, honest health, retired static audit routes, checksum-verified and retried bundle download, CI, explicit skip policy (`docs/120`).
- [x] Synoptic chart (wind, height, pressure, shading) on the Forecast page, with the context grid's georeferencing verified (`docs/121`).
- [x] Western-disturbance feasibility study, investigation only (`docs/122`). The requirement stays planned.
- [x] Independent regime validation source probe, no labelling (`docs/123`). The requirement stays planned.
- [ ] Western-disturbance work: owner decisions needed (label source, northward domain extension, downloads, season scope), `docs/122` section 9.
- [ ] Independent regime validation: owner decisions needed (climatology, depression record terms, partial validation, expert review), `docs/123` section 5.
- [ ] A new model (M5) and a geography-aware model (Stage 3): need an independent test period and the IMD redistribution decision.
- [ ] Live or new-cycle inference: separate worker; not started.
- [ ] Story Mode 2.0 and demo polish.

## Status after Phase 9 (2026-10-01)

- [x] Geography-aware correction (M5a) protocol frozen before training, trained on 2023, selection frozen, evaluated on 2024 and the post-hoc 2025 (`docs/124`, `docs/126`). Result: pre-registered rule **not met** (heavy-rain gain on the Ghats coast replicated, but 2024 over-forecasting).
- [x] Independent years acquired (forecast side): corpus v2 for 2021 (development) and 2022 (sealed test), protocol frozen, 24,500 hash-verified messages, nothing scored (`docs/127`, `docs/128`).
- [x] Forecast-side features built for 2021 (paired with IMD, development) and 2022 (no targets, sealed): `docs/128`.
- [x] Follow-up protocol drafted (`docs/129`), frozen as approved for development selection only, and run: **no candidate in any arm**, sealed 2022 not opened (`docs/130`).
- [x] Protocol v2 (G3 reported, not gating; post-hoc, disclosed) frozen and run: each arm has a candidate; 2022 still unopened (`docs/131`).
- [x] All three options done in the only coherent order (`docs/132`, `docs/133`): protocol v3 frozen, 2022 opened once under a signed 29-hash record, both candidate sets scored; primary passes, secondary does not; reported.
- [ ] Open after `docs/133`: decision 5 (frozen M1 to M4 on 2022, still no); IMD rights (D2); 2022 is consumed, so further tests need new data (2026 season).
- [ ] The follow-up (protocol for a model, for example a bias-controlled recipe) still needs: owner confirmation of the year roles, a frozen follow-up protocol (including sensitivity to the forecast 500 hPa height offset), the 2022 IMD pairing done only at unseal, and the IMD rights decision (D2). Not started.
- [x] First green CI run on GitHub Actions (backend with the checksum-verified bundle, frontend, Dockerfile lint) after fixing line-ending and missing-local-code issues that only a clean Linux checkout exposes.

## Status after the completion work packages (2026-10-03, `docs/134`)

- [x] WP-A: district verification for Track A (`docs/135`).
- [x] WP-B: partial independent regime validation; the pseudo-Active class does not match observed active spells (`docs/136`).
- [x] WP-C: forecast-time coastal/orographic forcing regime, a labelled heuristic (`docs/137`).
- [x] WP-D: western-disturbance trough indicator, association not met (`docs/138`); Raw all-India verification (`docs/140`).
- [x] WP-E: the 2022 independent-test figures are served on the improvement row and the Geography-Aware page (very-heavy improvement not shown).
- [x] WP-F: experimental live-cycle worker, API and page; replay is bit-identical (`docs/139`).
- [ ] Run the live worker on a current NOAA cycle (needs owner confirmation of the download; `plan` first).
- [ ] Scheduler, retries, alerting and a hosted worker for the live view.
- [ ] A validated western-disturbance regime (needs a label source and a winter or pre-monsoon corpus).
- [ ] A corrected (post-processed) forecast outside the 10-22 N, 68-80 E box (a new corpus, protocol and independent test).
- [ ] Very-heavy rain improvement and skill on a new cycle cannot be shown on data that exist today.
- [ ] Owner decisions: IMD redistribution rights (D2), the frozen M1-M4 on 2022 (default no), commit and push.

## Status after the reforecast study (2026-10-03, `docs/142`)

- [x] Independent data acquired: GEFSv12 reforecast control 2000-2016 (about 40 GB) and ERA5 geopotential 2000-2022 (about 11 GB); 2014-2016 sealed and opened once.
- [x] Regime detection (active, break, low/depression, western disturbance, coastal rain day) validated against objective labels: PS-R03 implemented.
- [x] Heavy-rain correction and exceedance classifiers: RMSE, heavy and very-heavy CSI improve; regime-awareness adds nothing.
- [x] PS-R05: round 1 failed the frozen mean-error guardrail; a pre-registered confirmatory round 2 on 2017-2019 (frozen models, one mean-error shift) met every criterion (`docs/142`).
- [ ] A model whose mean error stays inside the guardrail without a shift taken from earlier years (2019 alone stays above it after the shift).
- [ ] Expert- or bulletin-assigned regime labels (the labels used are objective rules).
- [ ] Reliability analysis of the exceedance probabilities before they are called calibrated.
- [ ] The live worker run on a current NOAA cycle (needs owner confirmation of the download).

