# Phase 11A: district-level verification for the 2017-2019 reforecast track (Track A)

Date: 2026-10-03. Work package WP-A of `docs/134`. District-level verification existed only for the operational-era track (`docs/112`, `docs/113`); this adds Track A, so the `DISTRICT-VERIFICATION` requirement is now implemented for both tracks. The two tracks are never pooled.

## What was done

1. **Protocol frozen before any model value was read.** `district_verification_protocol_A_v1.json` (sha256 `a55569a1c3763a8618ef605ac27e4d57e79696bbd491c6339d7492553340cc2e`) carries every definition over **unchanged** from the approved Track B protocol v1: the event definitions E1 (any valid cell), E2 (at least 25 percent of valid area) and E3 (district mean), the thresholds (64.5 and 115.6 mm per 24 h), the coverage rule (at least 5 valid cells; 169 of 188 districts kept), the support thresholds (30 observed events per district, 30 cases), the contrasts, the latitude bands and the bootstrap (2,000 resamples, seed 26080). Only the populations (2018 and 2019), the frozen inputs and the observation-only support counts differ. A test compares the two protocols field by field. The support counts were computed from the cached IMD observations and the valid-cell mask only (`freeze` stage); the `run` stage refuses to start unless the protocol hash matches its sidecar.
2. **Populations and labels.** 2018 is the validation year (development evidence); 2019 is the consumed final test and is always labelled **POST-HOC EXPLORATORY ANALYSIS OF THE COMPLETED 2019 FINAL TEST**. Models M0 to M4 are the frozen Track A models, reconstructed from the frozen Phase 2B models and cached features with their hashes checked. Regimes are the forecast-only pseudo-regime (argmax of the frozen classifier), not observed truth.
3. **Reproduction gate (13 checks for 2018, 14 for 2019).** The observation-only support counts and the pooled observed-event counts are reproduced exactly; per-district observed events sum to the pooled count; pooled Raw district-mean RMSE equals an independent per-pair loop; and for 2019 (the only year the Track A API serves) the district means of Raw and IMD equal means recomputed from the already-served 49 by 49 grids.
4. **Served and shown.** `/api/science/evidence/district-verification?year=2018|2019` (and the report download in Markdown, CSV or JSON) now serve both tracks from per-track hash-verified manifests; tampering with one track returns 503 for that track and does not block the other. The Verification page has a new "District-level verification - 2018 / 2019 reforecast" section next to the regime section, with the same panel as the operational-era tab.

## Results (stored values; district-mean error in mm per 24 h, E1 any-cell heavy rain)

| | District-mean RMSE: M0 / M1 / M2 / M3 / M4 | E1 heavy CSI: M0 / M1 / M2 / M3 / M4 |
|---|---|---|
| 2018, 251 cases, 42,419 district-case pairs | 13.39 / 12.72 / 12.04 / 12.36 / 12.33 | 0.124 / 0.029 / 0.052 / 0.024 / 0.023 |
| 2019 (post-hoc), 255 cases, 43,095 pairs | 16.51 / 15.67 / 14.95 / 15.53 / 15.50 | 0.165 / 0.052 / 0.050 / 0.012 / 0.010 |

Districts classified improved or worsened against Raw (169 tested; about 8 in total and about 4 per direction are expected by chance alone): in 2019, M1 65 improved and 56 worsened; M2 108 and 3; M3 104 and 5; M4 106 and 5. In 2018, M1 44 and 88; M2 86 and 25; M3 86 and 19; M4 87 and 20.

## How to read it

- **District-mean error improves** for every corrected model in both Track A years, and most districts move closer to IMD under M2, M3 and M4. The Ridge model M1 is mixed: in 2018 it worsens more districts than it improves.
- **District heavy-rain event detection does not improve.** Every corrected model has a lower E1 heavy CSI than Raw in both years, and the regime-aware models are lowest. This agrees with the grid-level finding that the Track A corrected models suppress extremes, and it is reported plainly.
- **Context from the other track** (stored, `docs/113`): on the operational-era track district-mean error improves for every corrected model in 2025, but in 2024 it improves only slightly for M1 and M2 and is worse than Raw for M3 and M4 (15.17 and 15.03 against 14.72). The coverage manifest says so.

## Limits

Aggregate verification of historical replay, not warning skill; IMD land cells only, so border and coastal districts rest on few cells; bootstrap intervals resample whole cases and ignore serial and spatial correlation, so they are optimistic; with about 170 districts tested, a few classifications as improved or worsened occur by chance; 2019 is a consumed holdout and must not select, tune or re-rank a model. The approval of this protocol is an interpretation of the owner's general instruction (recorded in the protocol); the owner may withdraw it.

## Evidence and tests

`scripts/build_phase6_district_verification_track_a.py` (stages `freeze` and `run`, write-once), evidence `district_verification_A_2018.json`, `district_verification_A_2019.json` and manifest `district_verification_manifest_A.json` under `backend/app/evidence_data/phase6/`. Tests: `backend/tests/test_district_verification_track_a.py` (hash chain, derivation from protocol B, stored reproduction, API for both tracks, tamper isolation, labelled reports), the Track A cases of `frontend-v2/src/lib/api/evidence.test.ts`, and `frontend-v2/tests/e2e/district-verification-track-a.spec.ts` against the real backend.
