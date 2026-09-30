# 92 — Operational Science Presentation API (Phase 5A.1)

## 1. Purpose

Phase 5A.1 gives `frontend-v2` read-only, hash- or fingerprint-verified access
to the frozen operational-era (2023-2025) historical GEFS + IMD corpus that
lives under `experiments/recent_historical/` (phase4b-phase4l). Before this
phase, no API exposed any Track B artifact: the frontend's Track A (2019)
`/api/science/*` surface had no Track B counterpart. This is a presentation
adapter, not a new science phase — it never trains, recalibrates, reselects,
or re-runs inference. Every response is either a verbatim frozen JSON payload
or a lossless reshape (index/scatter) of an already-frozen flat array into the
same 49x49 grid Track A's `/api/science/*` already uses.

## 2. Scientific Freeze

Nothing in `backend/app/api/operational.py` writes to, retrains, or
recalculates any artifact under `experiments/recent_historical/`. It only
reads. `FINAL_TEST_RESULT.json`, `FINAL_TEST_READY` state, and every Phase
2/4G-4L artifact are unchanged by this work (verified: `git status` shows no
modification under `data/` or `experiments/`, and the phase4j integrity check
this module performs on every request recomputes and compares hashes against
the pre-existing `ARTIFACT_INTEGRITY.json`, which continues to pass).

## 3. Track B Sources

- Forecast: NOAA operational GEFS (historical archive), decoded and QC'd in
  phase4f.
- Observation: IMD 0.25 degree gridded rainfall (`experiments/recent_historical/imd/RF25_ind{year}_rfp25.nc`).
- Model artifacts (M1-M4, probability calibrators, regime classifier): phase4i
  (2024 validation/selection) and phase4j (2025 final test).

## 4. Year Roles

| Year | Role | API value |
|---|---|---|
| 2023 | Training / cross-fit | `TRAIN_CROSSFIT` |
| 2024 | Validation / calibration / model selection | `VALIDATION_SELECTION` |
| 2025 | One-time final historical test, holdout consumed | `FINAL_TEST_COMPLETED` |

2025 is never reported as sealed or untouched — `status()` and every year
capability response report `FINAL_TEST_COMPLETED`.

## 5. Artifact Availability

See the year capability matrix (section 6) and the underlying audit performed
before this implementation. The single governing rule applied throughout this
module: **a capability is only ever reported as available if a real frozen
file backs it**; nothing is synthesized to fill a gap.

## 6. API Architecture

New router: `backend/app/api/operational.py`, mounted at
`/api/science/operational` (added to `backend/main.py` alongside — not instead
of — the existing `/api/science/*` Track A router, which is byte-for-byte
unchanged). Follows `science.py`'s established conventions: Pydantic response
models for every route, `lru_cache`-backed loaders, `HTTPException(404/503)`
for unknown/failed-integrity artifacts, path-safety via
`Path.resolve().is_relative_to(base)`.

Routes implemented:

```
GET /api/science/operational/status
GET /api/science/operational/years
GET /api/science/operational/{year}/availability
GET /api/science/operational/{year}/cases
GET /api/science/operational/{year}/cases/{case_id}
GET /api/science/operational/{year}/cases/{case_id}/rainfall?field=
GET /api/science/operational/{year}/cases/{case_id}/atmosphere/{field}
GET /api/science/operational/{year}/cases/{case_id}/probability/{target}
GET /api/science/operational/{year}/cases/{case_id}/ensemble
GET /api/science/operational/{year}/metrics/deterministic
GET /api/science/operational/{year}/metrics/probability
GET /api/science/operational/{year}/metrics/fss
GET /api/science/operational/{year}/regimes
GET /api/science/operational/quality
GET /api/science/operational/provenance
```

Deliberately **not implemented** in this phase (see section 19): a per-case
regime endpoint, and district aggregation for Track B.

## 7. Integrity Verification

Two tiers, chosen to match what each part of the corpus actually has:

- **Tier 1 (cryptographic, cached for process lifetime):** the 2025 final-test
  corpus (`phase4j_operational_final_test_v1/`) has a dedicated
  `ARTIFACT_INTEGRITY.json` + `.sha256` sidecar covering every file
  (~25 files). `_phase4j_integrity()` verifies the sidecar hash, then every
  listed file's SHA-256, once per process (`lru_cache(maxsize=1)`), and raises
  `503` on any mismatch — this mirrors `science.py`'s `_store()` pattern
  exactly and does not rehash on every request.
- **Tier 2 (existence + fingerprint pin):** the eligibility JSONs, per-date
  `rainfall_qc`/`atmospheric_qc` `.npy` grids, and the 2024 `phase4i` JSON
  files have **no dedicated per-file hash manifest** in the frozen corpus (the
  top-level `experiments/recent_historical/artifact_manifest.json` covers only
  145 top-level files, not these). For these, `_guard_and_fingerprint()`
  records `(size, mtime)` on first access and raises `503` if either changes
  on a later access — the "verify size/mtime don't change" fallback layer
  AGENTS.md's hardware/optimization guidance anticipates for artifacts without
  a dedicated hash chain. This is a real, documented limitation, not silently
  claimed as cryptographic verification (see section 25).

All paths are additionally allowlist-guarded: every filesystem path is built
from a fixed base directory plus a value drawn from an explicit enum/regex
(case ID pattern, member name, field name), then checked with
`Path.resolve().is_relative_to(base)` before any file operation.

## 8. Case Index

`GET /{year}/cases` builds a paginated index directly from the frozen
`phase4f_payload_acquisition_v1/eligibility/{year}_source_eligibility.json`
(375 scheduled cases per year), enriched for 2025 with the frozen
`case_level.json` RMSE fields. No new scientific label is derived — every
field in `OperationalCaseSummary` is copied verbatim from a frozen record.
Supports `page`, `page_size`, and `lead_hours` filtering. Does not bulk-load
any array data.

## 9. Rainfall Products

`GET /{year}/cases/{case_id}/rainfall?field=`. Allowed fields:
`raw, p01, p02, p03, p04, m1, m2, m3, m4, imd`.

- `raw`/`p01`-`p04`: served directly from the already-gridded (49x49) frozen
  `rainfall_qc/{year}/{date}/{product}_{member}.npy` files, gated by that
  member's `*_RAINFALL_QC_PASS` eligibility flag. A QC-failed member returns
  `404`, never a value.
- `m1`-`m4`/`imd`: **2025 only.** These are frozen as flat, corpus-order
  vectors (`predictions/M1.npy`, etc., length 301,832). Reconstructed into the
  case's 49x49 grid using the frozen `population/2025_population_manifest.json`
  (`row_start`/`row_count` per case) and `pairing/pixel_index.npy` (the exact
  flat-to-grid-cell mapping) via a pure NumPy scatter — no interpolation, no
  recomputation. **Verified correct**: reconstructing case
  `20250601_day1_24h`'s M1 grid and computing RMSE against the reconstructed
  IMD grid over valid cells reproduces `case_level.json`'s frozen
  `M1_rmse_mm` (3.3959908646465267) to full float precision (see
  `test_2025_rainfall_grid_reconstructs_frozen_case_rmse`).
- 2023/2024: `m1`-`m4`/`imd` return `404` with an explicit message — 2023's
  models are fit-only (no frozen output grid exists by design), and 2024's
  flat arrays have no frozen per-case row-index manifest, so reshaping them
  would require assuming an ordering that isn't independently verified. This
  API refuses to guess.

## 10. Atmospheric Products

`GET /{year}/cases/{case_id}/atmosphere/{field}`, fields `u850, v850, q700,
z500, mslp, pwat`. Served directly from frozen
`atmospheric_qc/{year}/{date}/{field}_f0{hour}.npy` (shape confirmed `(51,
81)` for all three years), gated by `ATMOSPHERIC_QC_PASS`. The response
explicitly states there is no per-cell lat/lon sidecar in the frozen corpus
and that the source grid is an approximately 0.5 degree, 51x81 cropped
context — never claimed as native 0.25 degree.

## 11. Probability Products

`GET /{year}/cases/{case_id}/probability/{target}`, targets `heavy,
very_heavy`. **2025 only**, same pixel-index scatter as rainfall. 2023/2024
return `404` — no frozen probability model output exists for 2023 (fit-only),
and 2024's probability arrays are similarly flat/corpus-order without a
verified per-case index.

## 12. Regime Products

Per-case regime probability is **not exposed** in this phase (see section
19). Aggregate distribution (`GET /{year}/regimes`) is exposed for **2025
only**, serving `phase4j`'s `metrics/regime.json` verbatim — both the full
375-case classifier counts and the 232-case paired counts
(Active=100, Break/Weak=71, Low/Depression=61, confirmed exact match).

## 13. Ensemble Products

`GET /{year}/cases/{case_id}/ensemble` returns all five members
(`c00, p01-p04`) with an explicit `qc_eligible` flag per member; a grid value
is included only when that member passed canonical QC. Labeled `"AVAILABLE
FIVE-MEMBER SUBSET"`, never "full GEFS ensemble."

## 14. Deterministic Metrics

`GET /{year}/metrics/deterministic`. 2025 serves `phase4j`'s
`metrics/deterministic.json` verbatim (hash-verified), with `primary_model:
"M1"` and explicit notes reproducing the `PRESELECTED_PRIMARY_MODEL` /
`SECONDARY_FINAL_TEST_RESULT` distinction — M2's lower secondary RMSE is
reported but never promoted to primary. 2024 serves
`phase4i/deterministic_models/validation_manifest.json["metrics"]` verbatim,
with no `primary_model` (2024 has not had a primary designated). 2023 returns
`404` — no frozen final-test deterministic metrics exist for a train/cross-fit
year.

## 15. FSS

`GET /{year}/metrics/fss`. 2025 serves `phase4j/metrics/fss.json` verbatim
(1/3/5/9-cell neighborhoods, confirmed against the known Heavy/Very-Heavy
Raw/M1 figures). 2024 serves `phase4i/fss/2024.json` verbatim. 2023 returns
`404` (no frozen FSS exists for that year).

## 16. Reliability

Reliability bins are embedded inside the frozen `metrics/probability.json`
payload for 2025 and returned as-is via `/2025/metrics/probability` — never
reconstructed for a year that lacks them.

## 17. QC

`GET /quality` sums the frozen per-year eligibility records exactly:
1,125 scheduled date-lead cases, 1,125 atmosphere-complete, 615 c00-eligible
(200/183/232 by year), 218 five-member-eligible (76/67/75 by year) — all
verified to match the pasted brief's figures exactly in
`test_quality_headline_numbers`. The response explicitly distinguishes
acquisition (all selected messages were downloaded) from QC eligibility
(attrition), per the "do not describe QC attrition as download failure" rule.

## 18. Provenance

`GET /provenance` returns model-family labels, experiment version, and a
live `artifact_verification_status` string (derived from actually running the
Tier-1 integrity check, not a static claim) — never a local filesystem path,
credential, or bucket key.

## 19. Unavailable Products (explicit, by design)

- **PR/ROC curve point arrays**: not available anywhere in the audited
  corpus — only scalar `pr_auc`/`roc_auc` and, for some years, one
  fixed-threshold confusion table. This API exposes those scalars inside the
  probability metrics payload and nothing more; `pr_roc_curve_arrays:
  "unavailable"` is a literal field on every year capability response.
- **Track B district aggregates**: zero such artifacts exist anywhere under
  `experiments/recent_historical/` (confirmed by exhaustive search in the
  preceding audit). `district_aggregates: false` is a literal field on every
  year capability response. District Intelligence remains Track-A-only.
  **Superseded (Phase 4N, `docs/107`):** `district_aggregates` is now a boolean (`true` for 2024 and 2025, `false` for 2023) and
  `GET /{year}/cases/{case_id}/districts` serves a read-only area-weighted aggregation of the frozen grids (not a frozen artifact).
- **Per-case regime probability** (2023/2024/2025): `regime_375x3.npy` (2025),
  `2024_prospective_probability.npy`, and the 2023 OOF regime arrays have no
  verified case-id-to-row index discovered during this phase. Serving them
  positionally against the eligibility list's order would risk misattributing
  one case's regime to another — a genuine scientific-integrity bug, not a
  cosmetic one. This phase refuses to guess; see section 26 for the exact next
  step.
- **2023/2024 M1/M3/M4/probability case grids**: see section 9.

## 20. 2023 Leakage Safety

2023 M2 is exposed with capability value `"out_of_fold_case_grid"` (not
implemented as a per-case grid endpoint in this phase, since it is a flat
`prediction.npy` requiring the same row-index caution as 2024 — but the
capability flag correctly distinguishes it from an in-sample result at the
metadata level). `test_2023_m2_is_out_of_fold` and
`test_2023_m1_m3_m4_unavailable` assert the API can never present 2023 M1/M3/M4
as if they were independent predictions, and that 2023's role is reported
accurately everywhere.

## 21. Security

Every path-bearing endpoint parameter (`case_id`, `field`, `target`, `member`)
is constrained by a regex or an explicit enum before touching the filesystem,
and every resolved path is checked with `Path.resolve().is_relative_to(base)`.
`test_malformed_case_ids_are_rejected` exercises `../` traversal, encoded
traversal, out-of-range years embedded in the case ID, and malformed day/hour
suffixes — all return `404`, none reach the filesystem layer un-validated.

## 22. Performance

- Case index reads one JSON file per year (375 small records) — no bulk array
  loading.
- Grid/atmosphere/ensemble/probability fields are lazy-loaded only on their
  specific endpoint call.
- `lru_cache` bounds hold the phase4j integrity/array/population/case-level
  loaders (`maxsize=1` or `16`) — verified hashes and small manifests are
  cached for the process lifetime; the ~25-file phase4j corpus is the only one
  fully rehashed, and only once per process.

## 23. Backend Tests

`backend/tests/test_operational.py` — 29 tests, all passing:
- year-role and capability contract (status, availability per year, PR/ROC and
  district-aggregate unavailability)
- 2023 OOF safety, 2023/2024/2025 model-set exposure correctness
- 2025 M1-primary / M2-secondary designation
- QC-failed-member and five-member-eligibility enforcement
- path-safety (traversal, malformed case IDs, unknown years/fields)
- numerical regression against the exact known 2024/2025 deterministic RMSEs,
  quality counts, and 2025 regime case counts
- **array regression**: reconstructs a real 2025 case's M1/IMD grids through
  the API and proves the resulting RMSE matches the frozen `case_level.json`
  value bit-for-bit
- a source-inspection guard asserting the module never imports/calls model
  training or fitting code

Run: `python -m pytest backend/tests/test_operational.py -q` (from repo root,
so the `backend.*` import style resolves) — 29 passed. Full existing suite
(`python -m pytest backend/tests -q`) — 172 passed; the 14 pre-existing
errors are unrelated Windows `tmp_path`/temp-directory permission issues in
other test files (`test_monthly_pilot.py`, `test_phase4f_source.py`, etc.),
not caused by this change, and reproduce identically without it.

## 24. Frontend Contract

**Not implemented in this phase**, per the "no frontend redesign yet"
instruction. `frontend-v2/src/lib/api/science.ts` has not been touched. The
exact next step (section 26) is to extend it with a parallel set of
Zod-validated accessors for these routes, mirroring the existing pattern.

## 25. Known Limitations

- Tier-2 integrity (eligibility JSON, QC grids, 2024 JSON files) is
  existence+fingerprint, not cryptographic hash — documented above, not
  hidden.
- 2024 and 2023 model-output case grids are not reshaped, by design (section
  9/19) — only aggregate corpus/lead metrics are exposed for those years at
  the model-output level.
- Per-case regime probability is not exposed for any year pending a verified
  row-to-case index.
- `frontend-v2` has not been touched or smoke-tested against these new routes
  yet.

## 26. Exact Next Step

Before any frontend page work: (1) locate or reconstruct a verified
case-id-to-row index for the 2024 `phase4i` flat prediction arrays and the
375-row regime probability arrays (check for an as-yet-unexamined manifest
under `phase4i_operational_model_development_v1/oof_regime/manifest.json` or
`probability_features/`, which were not fully inspected in this phase); once
verified, extend `operational.py` to expose 2024 case grids and per-case
regime the same safe way 2025 is exposed now. (2) Extend
`frontend-v2/src/lib/api/science.ts` with Zod schemas/accessors for the routes
documented here. Do not proceed to frontend page redesign until both are
done.
