# Phase 2A Accelerated Readiness Decision

## Decision

The authorized Phase 2A accelerated prototype work is complete for its narrow
scope: canonical-v2 2017/2018 JJAS corpus assembly, observation pairing and
case-tiered QC; a forecast-time-only three-regime pseudo-label definition;
2017 fitting; and 2018 validation. The outcome is a reproducible research
prototype, **not** a scientifically validated rainfall post-processing
system. No rainfall model was trained, no 2019 artifact was used for
development, and no scientific API was unblocked.

## Accepted evidence

- Both seasons have 122/122 expected initializations, all 2,196/2,196
  atmospheric variable/lead samples valid, and 366/366 observation pairings.
- Rainfall products are accepted case-by-case: 2017 has 1,489/1,830 valid
  member-products; 2018 has 1,476/1,830. The control-eligible case counts are
  258/366 and 251/366; full-ensemble-eligible counts are 187/366 and 176/366.
- The seasonal Zarr trees, source receipts, monthly lineage, regime artifacts,
  and validation metrics are hash-recorded in their manifests.
- The regime model has 366 eligible training cases and 366 validation cases.
  Its 2018 balanced accuracy of 0.9424 is only agreement with the generated
  pseudo-labels and is explicitly not objective regime skill.
- Feature availability, temporal role order, deterministic outputs, safe JSON
  model serialization, normalized probabilities, vorticity and forecast-only
  feature calculations are covered by tests.
- The 2019 test/demo corpus was not read by the Phase 2A acquisition, build,
  or fit/validation command. Its existing Phase 1F hashes remain protected.

## Remaining blockers to broader scientific work

1. Pseudo-labels have not been independently validated by expert or
   authoritative regime annotations.
2. High rainfall-product quarantine and incomplete full-ensemble availability
   constrain any ensemble-based experiment.
3. No rainfall post-processor has been trained or compared with raw GEFS and a
   strong non-regime baseline on a common held-out sample.
4. The prototype probability outputs are not calibrated against independent
   truth. No event-probability product is approved.
5. FSS is not computed; its current eligibility tier denotes valid aligned
   grids only. Authoritative district geometry and district aggregation remain
   absent.
6. The Phase 2A prototype artifacts are not wired to the legacy API or
   frontend. Existing CSV/API outputs retain their previously documented
   limitations; Phase 2A does not silently supersede them.
7. The exact repository-wide and frontend scientific-integrity blockers
   listed in the stabilization, audit, and roadmap documents remain governed
   by those documents; this prototype does not resolve them by implication.

## Authorization boundary

This readiness report closes only the bounded Phase 2A tasks. It does not
authorize a new scientific phase, acquisition of other years, access to 2019
for model fitting, changes to v1, relaxed reconstruction rules, new regime
classes, rainfall-model training, performance tuning of frozen acquisition
settings, or API/UI integration. Such work requires separate review against
the roadmap, training-index roles, provenance rules, and applicable
acceptance criteria.
