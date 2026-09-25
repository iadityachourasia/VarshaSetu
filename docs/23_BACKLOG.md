# Prioritized Backlog

## P0 — Do immediately

- [x] Replace absolute dataset path.
- [x] Identify the checked-in prototype file exactly; scientific authority remains unverified and training is blocked.
- [x] Create data manifest/checksum file.
- [ ] Restore/rebuild regime labels reproducibly.
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
- [ ] Create forecast-time-only feature registry.
- [x] Create repeated exact 24h raw-NWP pilot products; one archive inconsistency remains quarantined.
- [x] Build the bounded monthly aligned-grid pilot; production corpus pipeline remains pending.
- [ ] Implement FSS.
- [ ] Add district geometry.
- [ ] Aggregate grid to district.
- [ ] Add district map/table.
- [ ] Raw/corrected/observed/error maps.

Phase 1B checks off one source-backed timing/24-hour pairing only. It does not
check off a historical corpus, full predictor acquisition, repeated reliability,
training readiness, FSS, or district products.

Phase 1C validates one full calendar month but remains PARTIAL. Immediate P1
work is to resolve the July 22 `p01` accumulation exception and review/freeze the
historical acquisition/QC plan. It does not check off training readiness, FSS,
district products, regime labels, or the multi-year corpus.

## P2 — Scientific

- [ ] Validate regime label methodology.
- [ ] Evaluate event-aware extreme model.
- [ ] Reliability diagram.
- [ ] Brier Skill Score.
- [ ] Bootstrap uncertainty.
- [ ] Lead-time breakdown.
- [ ] Failure-case archive.
- [ ] Model/data/version metadata.

## P3 — USP

- [ ] Soft MoE.
- [ ] Multi-label/hierarchical regimes.
- [ ] Moisture/vorticity features.
- [ ] True orographic upslope feature.
- [ ] Extreme specialist.
- [ ] Explainable correction contributions.
- [ ] Multi-scale FSS dashboard.

## P4 — Demo

- [ ] polished replay selector,
- [ ] judge mode,
- [ ] aggregate evidence,
- [ ] offline cached demo,
- [ ] limitations panel.

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
