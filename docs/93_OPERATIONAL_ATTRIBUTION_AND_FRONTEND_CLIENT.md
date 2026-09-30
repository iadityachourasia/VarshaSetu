# 93 — Operational Attribution Completion + Frontend Science Client (Phase 5A.1B)

## 1. 2024 Attribution Investigation

Phase 5A.1 left 2024's M1-M4/probability model outputs as `aggregate_metric_only`
because `phase4i_operational_model_development_v1/deterministic_models/validation_manifest.json`
gave no per-case row index for its flat 238,083-cell arrays. Investigating
`phase4g_features_v1/build.py` and `finalize.py` (the actual Phase 4G feature
build code, not previously read in Phase 5A.1) showed they write
`row_start`/`row_count`/`pixel_index` outputs to a directory whose base was not
inspected before. Searching the filesystem for `pixel_index.npy` outside
`phase4j` found it: a whole previously-unexamined tree at
`data/operational_derived/operational_features_2023_2025_v1/{year}/{split}/deterministic/`,
containing `cases.json`, `pixel_index.npy`, `X.npy`, `y_mm.npy` (paired IMD),
`heavy_label.npy`, `very_heavy_label.npy` for `2023/train`, `2024/validation`,
and `2025/test_sealed` (that last directory name is a pipeline-stage label from
before the 2025 holdout was unsealed; it is never surfaced in any API response).

## 2. 2024 Mapping Evidence

Evidence type used: **C and D** (frozen row_start/row_count/pixel_index array,
independently validated against pre-existing frozen aggregate metrics).

- `2024/validation/deterministic/cases.json`: 183 records, each with
  `case_id`, `row_start`, `row_count` (summing to 238,083, matching
  `M1_2024.npy`'s length exactly).
- `2024/validation/deterministic/pixel_index.npy`: 238,083 flat-to-grid-cell
  indices into the same 49x49 grid Track A and 2025's Track B already use.
- `2024/validation/year_manifest.json` declares `outputs_sha256.deterministic`
  hashes for `cases`, `pixel_index`, `target_mm` (=`y_mm.npy`), etc.; its own
  SHA-256 matches `dataset_catalog_manifest.json["years"]["2024"]["year_manifest_sha256"]`,
  which itself is cross-checked against `phase4g_experiment_manifest.json`'s
  independent copy of the same hash. This is a real, closed hash chain, not an
  assumption.
- `phase4i/probability_features/2024/manifest.json` independently states
  `"row_order": "identical to Phase4G deterministic cases/row_start/pixel_index"`
  — the two pipeline stages document the same ordering contract in their own
  words.

## 3. 2024 Reconstruction Proof

Reconstructing all four models (M1/M2/M3/M4) plus the raw c00 baseline through
this index and computing RMSE against the reshaped IMD grid over the full
183-case population reproduced `validation_manifest.json`'s frozen aggregate
RMSE to float32 precision:

| Model | Reconstructed RMSE | Frozen RMSE |
|---|---|---|
| M0 (raw) | 17.129675 | 17.129672877498237 |
| M1 | 16.79747 | 16.797471743133617 |
| M2 | 16.845932 | 16.84593181465105 |
| M3 | 17.413378 | 17.41337838391456 |
| M4 | 17.262783 | 17.262784825888428 |

The 2024 heavy-probability array was checked the same way: reconstructed
Brier score (0.02107000818860998) matched
`validation/probability_heavy_2024.json`'s frozen
`full_2024_descriptive_metrics.brier` to full double precision. This proves
the row order — it is not assumed from matching array lengths. Backed by
`test_2024_m1_m2_m3_m4_grid_reconstruction_reproduces_frozen_aggregate_rmse`
and `test_2024_raw_reconstruction_via_rainfall_qc_matches_frozen_aggregate` in
`backend/tests/test_operational.py`.

## 4. Unresolved Mappings

None remain for 2024's deterministic/probability model outputs. What stays
genuinely unavailable, by design (not by unresolved attribution):
2023's M1/M3/M4 and probability models were fit on 2023, never scored against
it, so no frozen 2023 output array exists for them at all — there is nothing
to attribute.

## 5. Regime Attribution

Evidence type used: **A** (explicit frozen case_ids arrays) for 2023/2024,
**D** (independent double cross-check against two frozen aggregates) for 2025.

- **2023**: `oof_regime/manifest.json["case_ids"]` (375 entries) maps
  directly onto `oof_regime/probability.npy` (shape `(375, 3)`); the
  manifest's own `probability_sha256` matches the actual file hash.
- **2024**: `regime_models/manifest.json["validation_case_ids"]` (375
  entries, all `2024-*`) maps directly onto
  `regime_models/2024_prospective_probability.npy` (shape `(375, 3)`); the
  manifest's own `2024_probability_sha256` matches the actual file hash.
- **2025**: `predictions/regime_375x3.npy` has no dedicated case_ids array.
  Indexing it by the frozen `2025_source_eligibility.json` file's own row
  order and computing `argmax` per row reproduces **both**
  `metrics/regime.json`'s full-375 classifier counts
  (Active=150, Break/Weak=130, Low/Depression=95) **and** its 232-case paired
  counts (Active=100, Break/Weak=71, Low/Depression=61) exactly. Two
  independent aggregate matches under one ordering hypothesis is not
  plausible by chance under a wrong row order.

## 6. 2023 OOF Protection

`GET /2023/cases/{case_id}/regime` returns `prediction_role: "OUT_OF_FOLD"`
and `year_role: "TRAIN_CROSSFIT"` unconditionally — there is no code path that
can substitute an in-sample or full-training regime assignment for 2023.

## 7. 2024 Prospective Regime

`GET /2024/cases/{case_id}/regime` returns
`prediction_role: "PROSPECTIVE_VALIDATION"` — the classifier was trained on
2023 and applied prospectively to 2024, never retrained on 2024 itself.

## 8. 2025 Final Regime

`GET /2025/cases/{case_id}/regime` returns
`prediction_role: "FINAL_TEST_PREDICTION"`. Every regime response (all three
years) carries `semantic_note: "forecast-only pseudo-regime; not
independently observed meteorological truth"`.

## 9. Operational API Extensions

`backend/app/api/operational.py` gained, without changing any Phase 5A.1
route's existing contract:

- `rainfall()`: now supports `m1-m4`/`imd` for **2024** (via the Phase 4G
  index) and `m2`/`imd` for **2023** (via the OOF M2 array + Phase 4G index);
  `m1`/`m3`/`m4` for 2023 remain a `404` with an explicit "fit on 2023, not
  scored against it" message.
- `probability()`: now supports `heavy`/`very_heavy` for **2024**; 2023
  remains `404` (no probability model was fit for 2023 to score against
  itself).
- **New** `GET /{year}/cases/{case_id}/regime` for all three years, gated by
  `REGIME_SOURCE_ELIGIBLE`.
- `regimes()` (aggregate): now computes a real predicted-class-count
  distribution for 2023/2024 from the per-case lookups, instead of `404`;
  2025 still serves `phase4j`'s own frozen `metrics/regime.json` verbatim.
- Two new hash-verified loader families: `_phase4g_deterministic(year)`
  (cases.json + pixel_index + IMD, Tier-1 hash chain rooted at
  `dataset_catalog_manifest.json`) and `_oof_m2_2023()` /
  `_regime_2023()` / `_regime_2024()` / `_regime_2025()` (each verified
  against a manifest-declared hash or an independent aggregate reproduction).

## 10. Updated Capability Matrix

```
                       2023              2024        2025
raw_rainfall            Y                 Y           Y
imd_observation         Y                 Y           Y
m1                 unavailable        case_grid    case_grid
m2              out_of_fold_case_grid case_grid    case_grid
m3                 unavailable        case_grid    case_grid
m4                 unavailable        case_grid    case_grid
heavy_probability   unavailable        case_grid    case_grid
very_heavy_prob.    unavailable        case_grid    case_grid
regime_probability    per_case          per_case    per_case
atmosphere_fields       Y                 Y           Y
ensemble_members  eligible_subset   eligible_subset eligible_subset
case_level_metrics     false             false        true
per_cell_metrics       false             false        true
fss                    false             true         true
reliability_bins       false             true         true
pr_roc_curve_arrays  unavailable      unavailable  unavailable
district_aggregates    false             false        false
```

2025's M1 remains `primary_selection_status = "PRESELECTED_PRIMARY_MODEL"`
and M2 remains `"SECONDARY_FINAL_TEST_RESULT"` — unchanged from Phase 5A.1;
no code path in this phase touches that designation.

## 11. Frontend Client Architecture

New file `frontend-v2/src/lib/api/operational.ts`. Deliberately a **separate
file** from `science.ts` rather than appended inline — `science.ts` covers
Track A's ~10 schemas at 165 lines; adding ~15 more operational schemas
in-place would roughly triple it. The file still follows `science.ts`'s exact
conventions: same Zod-first validation style, same same-origin/server-origin
base-URL logic, no Redux/Zustand/TanStack Query (confirmed still unused in
the actual fetch code, matching the Phase 5A.1 audit finding).

## 12. Zod Contracts

All 16 response shapes from `docs/92` are covered: `operationalStatusSchema`,
`operationalAvailabilitySchema` (+ `operationalYearsSchema` for the list
form), `operationalCaseSummarySchema`/`operationalCasesResponseSchema`/
`operationalCaseDetailSchema`, `operationalGridFieldSchema`,
`operationalAtmosphericFieldSchema`, `operationalProbabilityFieldSchema`,
`operationalRegimeSchema`/`operationalRegimeSummarySchema`,
`operationalEnsembleSchema`, `operationalDeterministicMetricsSchema`,
`operationalProbabilityMetricsSchema`, `operationalFssSchema`,
`operationalQualitySchema`, `operationalProvenanceSchema`.

## 13. Error Contract

The existing `/api/science/*` client (`getScience` in `science.ts`) collapses
every non-2xx response to one of two fixed strings by status code, discarding
FastAPI's actual `{"detail": "..."}` body — sufficient for Track A's UI, but
not enough to distinguish `NOT_ELIGIBLE_FOR_CASE` from `NOT_AVAILABLE`, which
both surface as `404` with different detail text. `operational.ts` therefore
fetches directly (same base-URL logic, not delegating to `getScience`) and
classifies using the real `detail` text into a typed `OperationalApiError`
with `.kind`: `NOT_AVAILABLE | NOT_ELIGIBLE_FOR_CASE | INTEGRITY_FAILURE |
NETWORK_FAILURE`. This is a pattern-matched approximation over free text, not
a backend-declared error code — documented as a limitation in the source
comment and in section 17 below, not silently presented as exact.

## 14. Grid Safety

`operationalGridFieldSchema` uses a Zod `superRefine` to reject a payload
whose `values` row/column counts, or `latitude_centers`/`longitude_centers`
lengths, disagree with its own declared `shape` — proven by
`operational.test.ts`'s two malformed-grid rejection tests. U850/V850 are
never collapsed into a magnitude in the client; both components pass through
independently for a later Phase 5A.2 vector-rendering step.

## 15. Unsupported Products

`district_aggregates: z.literal(false)` and `pr_roc_curve_arrays:
z.literal("unavailable")` are typed as Zod literals, not plain booleans/strings
— a payload that ever claims otherwise fails validation immediately rather
than silently rendering. No PR/ROC curve-point Zod type exists anywhere in
this client.

## 16. Tests

- Backend: `backend/tests/test_operational.py` grew from 29 to 38 tests
  (all passing) — the 9 new tests are the 2024 reconstruction proof, the 2023
  OOF M2 case-order check, the three regime prediction-role tests, the
  finite/sums-to-one/no-duplicate regime validation sweep, the double
  full-375/paired-232 regime count reproduction, and the "2023 unproven
  fields stay unavailable" guard.
- Frontend: `frontend-v2/src/lib/api/operational.test.ts`, 19 new Vitest
  tests covering every schema, the two grid-malformation rejections, and all
  four error-kind classifications (including the corrected QC-vs-not-fit
  distinction using real backend detail text).

## 17. Scientific Integrity

No artifact under `data/` or `experiments/` was modified (`git status` clean
there throughout). `_phase4g_deterministic()`, `_oof_m2_2023()`,
`_regime_2023()`, and `_regime_2024()` each verify a cryptographic hash
declared by a pre-existing frozen manifest before serving anything; `_regime_2025()`
is validated by exact reproduction of two independent frozen aggregates rather
than a manifest hash (none exists for that specific array), which is
documented as evidence type D, not asserted as type A.

## Exact Next Task

1. Backend: consider adding a structured `{code, detail}` error body to
   `/api/science/operational/*` (e.g. via a shared `HTTPException` subclass)
   so the frontend's `OperationalApiError` classification in section 13
   becomes exact rather than pattern-matched over free text.
2. Frontend: begin wiring `operational.ts`'s accessors into the actual
   Forecast/Ensemble/Regime Intelligence page components for 2023-2025 case
   exploration — this is the first real Phase 5A.2 visual-integration step,
   deliberately not started in this phase.
3. Do not attempt Track B district aggregation or PR/ROC curve reconstruction
   in either step above — both remain genuinely absent from the frozen corpus.
   (Update, Phase 4N, `docs/107`: district aggregation was later added as a read-only derived view over the frozen grids for 2024/2025.
   PR/ROC curve reconstruction remains unavailable.)
