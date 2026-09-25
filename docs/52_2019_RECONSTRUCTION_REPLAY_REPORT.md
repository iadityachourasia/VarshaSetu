# 2019 Canonical Reconstruction Replay Report

Status: completed Phase 1F cache-only evidence. No model was trained.

## Recovery and artifact integrity

The full scientific replay completed twice before a later diagnostic-only run
was interrupted. On recovery, the season manifest, replay table, interval
inventory, independent verification file, and independently recomputed v2 Zarr
tree all matched their recorded deterministic SHA-256 references. No partial or
temporary artifact existed. The missing counters were generated separately
from hash-verified cached GRIB objects; no scientific replay output was
rewritten and no network request was made.

Key machine artifacts are under `data/manifests/phase1f/2019-JJAS/`:

- `season_manifest.json`;
- `reconstruction_replay.csv` (1,830 case rows);
- `interval_inventory.csv` (15,250 message rows);
- `independent_verification.csv` (five dates × three c00 products);
- `reconstruction_diagnostics.csv` (3,660 method rows), SHA-256
  `46549090541804ff466572496d21e7b09d865591f12dd6aac6428f8ca23e9190`;
- `deterministic_replay_verification.json`.

The v2 Zarr tree SHA-256 is
`13fc4ea03f0724fc6a3c0506de1a30b1acb5be4f8dc803c9ea46bb2b5377cb9e`.
The v1 manifest and Zarr hashes remain
`c68af39654a6449ab7a1d81a5259888dfa1c31568bc83100228ae2e62e6f20ce`
and `895cecb614a8d39b5e251b8608bb613f5695202c4fdc4b8752e71fd8d1fcc18d`.

## Rainfall acceptance

| Reconstruction | Accepted | Quarantined | Acceptance |
|---|---:|---:|---:|
| v1 method A | 614 / 1,830 | 1,216 | 33.55% |
| v2 method B | 1,468 / 1,830 | 362 | 80.22% |

### Coverage by month

| Month | Accepted / expected | Acceptance |
|---|---:|---:|
| June | 355 / 450 | 78.89% |
| July | 374 / 465 | 80.43% |
| August | 375 / 465 | 80.65% |
| September | 364 / 450 | 80.89% |

### Coverage by product

| Product | Accepted / expected | Acceptance |
|---|---:|---:|
| Day 1 | 595 / 610 | 97.54% |
| Day 2 | 440 / 610 | 72.13% |
| Day 3 | 433 / 610 | 70.98% |

Every month and product has broad coverage. The 362 failures remain
case-scoped quarantines where the one necessary boundary difference exceeds its
actual packing bound; they were not clipped, substituted, or tolerance-relaxed.

## Eligibility

| Tier | v1 | v2 |
|---|---:|---:|
| `CONTROL_MODEL_ELIGIBLE` | 52 / 366 | 255 / 366 |
| `FULL_ENSEMBLE_ELIGIBLE` | 9 / 366 | 173 / 366 |
| `EXTREME_EVENT_ELIGIBLE` | 52 / 366 | 255 / 366 |
| `FSS_ELIGIBLE` | 52 / 366 | 255 / 366 |
| `REGIME_ELIGIBLE` | 366 / 366 | 366 / 366 |

The control set is sufficiently broad across season and lead products for the
next limited chronological prototype stages. The full-ensemble set is usable
for optional experiments but remains incomplete and must use its own frozen
index. This is not permission to compare models on different case sets.

## Independent verification

The deterministic sample covers 2019-06-01, dry 2019-06-15, 2019-07-22, wet
2019-08-06, and 2019-09-30, with all three c00 products (15 cases). An
independently written explicit formula agreed with all canonical accept/reject
statuses; all accepted arrays matched exactly and were nonnegative.

## July 22

p01 Day 2 changes from method-A failure to method-B pass because `+39→+42` is
not used. p04 Day 2 also passes. c00 Day 2 remains quarantined because the
required `+27→+30` subtraction violates its packing bound. Consequently that
initialization/product is not control or full-ensemble eligible, while its
atmosphere remains regime-eligible.

## Raw GEFS v2 baseline

This is raw c00 verification on the new eligible set, not an improvement claim:

| Product | Cells | RMSE mm | MAE mm | Bias mm |
|---|---:|---:|---:|---:|
| Day 1 | 158,722 | 19.2297 | 9.4249 | +1.9673 |
| Day 2 | 93,672 | 21.1652 | 9.6315 | -0.1752 |
| Day 3 | 79,361 | 19.1352 | 8.7744 | -1.2453 |

At 64.5 mm/24 h, Day 1/2/3 POD is 0.1831/0.1687/0.1150, FAR is
0.7031/0.6858/0.5719, CSI is 0.1277/0.1233/0.0997, and ETS is
0.1178/0.1114/0.0935. Complete 115.6 and 204.5 mm contingency records remain
in `raw_gefs_control_baseline.json` and the updated baseline report.

## Scientific decision

V2 is a provenance-complete, scientifically usable prototype corpus with
explicit case exclusions. It remains `training_eligible=false` until the next
task constructs the documented methodology and chronological experiment views.
No regime label, model, FSS result, or scientific API was created here.

## Documentation and implementation discrepancies resolved

1. The completed replay table lacked explicit method-A subtraction, negative
   intermediate, packing-bound violation, and final-negative counters. Recovery
   added a separate 3,660-row diagnostic ledger without rewriting the
   deterministic replay evidence.
2. The first independent-verification draft retained only accepted products,
   yielding eight rather than the required 15 rows. The corrected deterministic
   artifact contains all five dates and all three c00 products, including
   independently confirmed rejections.
3. Historical text treated the July 22 p01 diagnostic `+39→+42` failure as a
   Day-2 target failure. Append-only updates now distinguish the real diagnostic
   anomaly from the v2 canonical target while preserving v1 conclusions.
4. The system Python lacks pytest; all successful tests use the repository
   `.venv`, which is the actual reproducible backend environment.
5. The manually interrupted diagnostic regeneration left no partial file and
   did not modify any completed reference hash. Process inspection through WMI
   was permission-denied, but no command session remained active and filesystem
   inspection found no partial/temp artifact.

`CANONICAL_RECONSTRUCTION_APPROVED`

`PROTOTYPE_CORPUS_USABLE`
