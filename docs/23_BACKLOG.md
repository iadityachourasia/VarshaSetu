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

- [ ] Validate regime label methodology. (Only pseudo-label agreement exists; independent validation is PLANNED, see `/compliance`.)
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
