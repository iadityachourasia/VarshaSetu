# Phase 4N — Track B (operational-era) district product

## 1. Purpose and status

Closes the largest remaining PS-R08 gap: a district table/map for the operational-era track (2023–2025),
which previously answered "not available". Track B now serves an **area-weighted district aggregation of the
already-frozen per-case grids**, for **2024** (validation/selection year) and **2025** (consumed holdout,
historical replay). **2023 has no district product** (see §5).

This supersedes the "no Track B district product / `district_aggregates: false`" statements in `docs/92`
(§ Track B district aggregates), `docs/93` (§ recommended next steps, item 3), `docs/presentation/FINAL_PPT_FACTS.md` §7,
`docs/presentation/JUDGE_QA.md`, `docs/presentation/ROUTE_INVENTORY.md`, `docs/presentation/FINAL_ARCHITECTURE_DIAGRAM_SPEC.md`
and `README.md`. Those documents carry a pointer to this one. Earlier phase records (`docs/94`, `101`, `103`–`105`)
describe the state at their own dates and were intentionally left unchanged.

## 2. What it is — and what it is not

- It **is** a read-only aggregation computed at request time from frozen arrays (Raw M0, M1–M4, calibrated heavy/very-heavy
  probability, IMD observation) using the **same pinned, hash-verified Phase 2C overlap-weight matrix as Track A** (`docs/65`).
  Both tracks therefore share one spatial definition (188 domain districts, geoBoundaries ADM2 2021, ODbL).
- It **is not** a new model output, retraining, recalibration or re-selection, and **not** a frozen, hash-pinned artifact
  of its own: the inputs are hash/fingerprint-verified under the existing Track B integrity model (`docs/92`), the weights and
  geometry are verified against the Phase 2C manifest, and the endpoint embeds the weights/geometry SHA-256 in every response.
- It is a **historical replay**, not a live district forecast or advisory. Observed IMD district statistics are shown only because the
  cases are retrospective.
- It is **not** district-level *verification*. No district-level skill score exists yet (see §6).

## 3. Method

Code: `backend/app/ml/district_product.py` (pure functions), `backend/app/api/operational.py`
(`GET /api/science/operational/{year}/cases/{case_id}/districts?model=m1|m2|m3|m4`), frontend
`frontend-v2/src/components/districts/operational-districts.tsx`.

1. Scatter the case's valid paired cells onto the 49×49 (2401-cell, south-to-north) grid via the frozen pixel index; unpaired cells are NaN.
2. A cell contributes to a district only if its overlap weight is > 0 **and** every required field (raw, corrected, observed, and the probabilities when present) is finite.
3. District mean = weights normalised over those cells (cos-latitude-corrected planar overlap, as in `docs/65`). Districts with no valid cell in the case are omitted (typically 187 of 188).
4. Returned per district: raw mean/max, corrected mean/max (chosen model), area-weighted heavy/very-heavy probability, corrected heavy/very-heavy **area fraction** (share of cells ≥ 64.5 / ≥ 115.6 mm/24 h, inclusive), and the IMD replay counterparts (mean, max, heavy/very-heavy area fraction), plus the case's forecast-only pseudo-regime.
5. Default model is **M1** (pre-registered primary for 2025; the RMSE-selected model for 2024). M2–M4 are selectable and labelled with their true role; M2 is never labelled primary.

## 4. Verification of the implementation

| Check | Result |
|---|---|
| Stored Phase 2C weights vs independent recomputation from the pinned GeoJSON (`district_weights`) | identical (max abs diff 0); district order equals `districts.geojson` |
| New aggregation vs the frozen Track A `aggregate_districts` on identical inputs | equal to 1e-9 on every shared statistic |
| Endpoint vs an independent recomputation from the already-served rainfall/probability grids, 2024 and 2025, M1 and M3 | equal (means ±1e-3 mm, probabilities ±1e-6) — this also confirms the flat M0 array equals the served raw QC grid on all 1 301 valid cells |
| Threshold inclusivity (64.5 / 115.6), missing-field cells get no weight, empty districts omitted, shape errors raise | unit-tested |
| Backend suite | 216 passed; 14 errors, all the known Windows `tmp_path` permission error (`docs/101`) |
| Frontend | `tsc` clean, production build OK, 90/90 Vitest, 4 new Playwright specs pass (2025 table/labels, sort + inspector, model/map-variable switch, 2024 label + 2023 honest state) |
| Wider Playwright run | 56/61 in one parallel run; 4 of the 5 failures (`mapping:35`, `demo-flow:64`, `forecast-chart-hardening:19`, `live-polish-regression:43`) pass when re-run in isolation (load-related); the fifth, `demo-flow:4`, fails identically on the pristine pre-change code (see §7) |

## 5. Why 2023 has none

2023 is the train/cross-fit year: only leakage-safe out-of-fold M2 exists there, and there are no probability or M1/M3/M4
output grids. The endpoint returns `SCIENCE_PRODUCT_UNAVAILABLE` and the page says so; nothing is fabricated from training data.

## 6. Limitations (keep when quoting)

- District-level verification was not part of this phase and has since been done under a frozen protocol (Phase 6C, `docs/112`, `docs/113`); the district product itself is not a skill claim.
- Area-weighted district *means* smooth extremes; heavy/very-heavy cells are better read from the area fractions, probabilities and cell maximum (which is a single-cell maximum, not an area-weighted extreme).
- Domain-limited (10–22°N, 68–80°E); geometry is simplified, 735 of 736 advertised ADM2 features, not an official current boundary; ODbL share-alike review is still required before redistributing derived geometry.
- Only IMD land cells that passed pairing have values, so coastal/partly-covered districts are aggregated over fewer cells (`valid_grid_cells` is shown).
- Live-API only: there is **no** static-bundle fallback for this view (unlike the Track B grid pages). On a cold Render instance the first request pays the one-time Phase 2C manifest verification (hashing every frozen file).
- 2025 is a consumed holdout; district views of it are descriptive replay and must not be used to select or re-rank a model. The M1 primary result is unchanged.
- The regime shown is a forecast-only pseudo-label, not observed meteorological truth.

Update (Phase 6B, `docs/111`): the single-model limitation above has since been lifted (compare-all-models view, per-district error/improvement, error map, descriptive history). The absence of district-level verification and the other limitations stand.

## 7. Incidental findings

- `frontend-v2/tests/e2e/demo-flow.spec.ts:4` (Overview `/`) fails on the **original** code with a strict-mode violation: `"9.73%"` now appears in two Overview elements since the Overview redesign (`879b940f`). Pre-existing and unrelated to this phase; not fixed here.
- Playwright specs must run against `next start` (the specs use `127.0.0.1`); under `next dev` that origin is blocked from hydrating and pages stay on their loading skeleton.

Gate: `TRACK_B_DISTRICT_PRODUCT_COMPLETE_VERIFICATION_NOT_STARTED`.

## Addendum: downloading a case (2026-10-01)

`GET /api/science/operational/{year}/cases/{case_id}/districts/export?format=csv|json` returns the same district comparison the page shows (it calls the comparison code path directly, so nothing is recomputed or rounded): Raw, M1 to M4 and IMD for every district, the errors and the improvement-versus-Raw values, and the provenance as columns (`label`, `year_role`, `case_id`, `predicted_regime`, `units`, `method`, `weights_sha256`, `geometry_sha256`) so a downloaded file cannot lose its label. The 2025 file therefore says `FINAL_TEST_COMPLETED` in every row, and every row says the product is a historical decision-support prototype, not an operational warning. The JSON form also carries the caveats. The district page links both formats for the selected case. Tests: `backend/tests/test_district_export.py` and the last case of `frontend-v2/tests/e2e/operational-districts.spec.ts`.

