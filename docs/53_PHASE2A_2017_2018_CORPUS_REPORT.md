# Phase 2A 2017–2018 Prototype Corpus Report

## Decision and scope

The bounded training/validation corpus for the forecast-only regime prototype
was acquired and assembled from GEFS v12 retrospective forecasts and the IMD
0.25-degree daily rainfall archive. 2017 is the prototype fitting year and
2018 is validation only. The 2019 test/demo artifacts were not read by the
acquisition, seasonal-build, or regime-training scripts. This corpus does not
authorize rainfall-model training, production inference, or API unblocking.

Rainfall uses the canonical v2 minimal native-interval decomposition and
representation-aware packing bound specified in
[`51_CANONICAL_PRECIPITATION_RECONSTRUCTION.md`](51_CANONICAL_PRECIPITATION_RECONSTRUCTION.md).
Failed products remain quarantined; reconstruction semantics and bounds were
not relaxed to increase sample counts.

## Provenance and reproducibility

Official IMD annual source files and SHA-256 receipts are recorded in
`data/manifests/phase2a/sources/imd_rf25_2017.json` and
`data/manifests/phase2a/sources/imd_rf25_2018.json`. Monthly GEFS source and
QC manifests are under `data/manifests/phase2a/{year}-{month}/`; each seasonal
manifest records the exact monthly collection-manifest hashes. Seasonal Zarr
tree hashes are recorded both in `season_manifest.json` and below. The data
version string retains the parent v2 lineage; the seasonal subsets are
explicitly identified by year and role and do not replace the frozen 2019
evidence.

| Season | Role | Rainfall products valid / expected | Atmosphere valid / expected | Paired observation cases | Control eligible | Full ensemble eligible | Regime eligible | Zarr tree SHA-256 |
|---|---|---:|---:|---:|---:|---:|---:|---|
| 2017 JJAS | TRAIN | 1,489 / 1,830 | 2,196 / 2,196 | 366 / 366 | 258 / 366 | 187 / 366 | 366 / 366 | `6e742e4f148cf0bca435293116785015379614eae17645968ee0106f29c88475` |
| 2018 JJAS | VALIDATION | 1,476 / 1,830 | 2,196 / 2,196 | 366 / 366 | 251 / 366 | 176 / 366 | 366 / 366 | `5d1e09b7e90e98b081965409a36b714fc1d578f21dbe45fcb680ab266a642c3f` |

All 366 cases per season are regime eligible because their required six-field
forecast-time atmospheric bundles are complete. Rainfall eligibility is
case/product tiered: the control-model eligible case counts are 258/366 in
2017 and 251/366 in 2018, while some additional ensemble-member products are
individually valid outside fully eligible cases. Thus control eligibility is
not the same as full-ensemble eligibility. All four months per year were
accepted with quarantined samples; no whole month was silently discarded.

The v2 rainfall admission totals are 1,489 valid / 341 quarantined products in
2017 and 1,476 valid / 354 quarantined in 2018. Each seasonal manifest and
the per-product rainfall completeness tables provide the detailed lineage.
All 2,196 atmospheric variable/lead samples per season passed the recorded
availability and plausibility QC. Observation event inventory covers 124
valid dates per season because each forecast product window has its own valid
date, including dates in early October. The full event inventory and monthly
summaries are emitted under each season's manifest directory.

## Observation event inventory (descriptive only)

| Season | Days with ≥1 heavy grid cell | Heavy cell events | Days with ≥1 very-heavy grid cell | Very-heavy cell events | Maximum observed daily grid value (mm) |
|---|---:|---:|---:|---:|---:|
| 2017 JJAS | 101 | 2,290 | 54 | 430 | 358.34 |
| 2018 JJAS | 93 | 2,979 | 50 | 747 | 403.14 |

These are IMD-grid event counts under the current documented thresholds; they
are not independent storm counts, district counts, or model verification.
District geometry remains unavailable and district-level counts are not
computed.

## Limitations and use decision

- The reconstruction quarantine rate remains substantial; do not describe
  1,489/1,476 product acceptance as full ensemble availability.
- The retrospective dataset is not an operational forecast-feed validation.
- The seasonal event inventory is descriptive and does not demonstrate
  rainfall post-processing skill.
- FSS eligibility is currently an alias of valid aligned gridded pairs, not a
  reported FSS score.
- Seasonal Zarrs are isolated prototypes; they do not alter v1 or the protected
  2019 v2 test corpus.
- No rainfall model was trained.

Phase 2A corpus assembly is complete for its authorized 2017/2018 scope. Any
later scientific phase requires a separate authorization and must preserve
the frozen test-year boundary.
