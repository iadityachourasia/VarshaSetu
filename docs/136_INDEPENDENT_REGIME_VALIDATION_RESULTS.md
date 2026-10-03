# Phase 11B: independent validation of the regime classifier against observed active and break spells

Date: 2026-10-03. Work package WP-B of `docs/134`, following the source probe of `docs/123`. Until now every regime score measured agreement with a deterministic pseudo-labelling rule. This is the first check against something independent of that rule: rainfall observations. It is **partial by construction** and its finding is unfavourable to the classifier; both are stated up front.

## What was done

1. **Climatology download (stated before it ran).** IMD annual 0.25 degree RF25 files for 1981 to 2016: 36 files of about 25 MB (874 MB in total) from the same IMD endpoint used for the project's observation files, stored under `experiments/recent_historical/imd_climatology/`, headers validated (365 or 366 daily records, the same 129 by 135 grid), hashes recorded in the protocol. The period shares no year with any evaluated population (2018, 2019, 2024, 2025). The files are local only and must not be uploaded or republished (IMD rights unresolved, D2).
2. **Labels (the style of Rajeevan, Gadgil and Bhate 2010, as described in `docs/123`).** The cosine-latitude weighted mean rainfall over valid IMD cells in a core-zone box (18 to 28 N, 65 to 88 E) is normalised against a smoothed daily climatology; a run of at least three consecutive days at or above +1 standard deviation is an **active** spell and at or below -1 a **break** spell; only July and August days carry a label. **This is not the published classification.** The documented deviations: a box instead of the core-zone polygon, the IMD grid starting at 66.5 E, a 15-day moving-average climatology and one pooled sigma (3.93 mm per day), a 36-year record, and the criteria were read from summaries and not verified against the paper's text.
3. **Protocol frozen before any prediction was read** (`regime_validation_protocol_v1.json`, sha256 `f10aee6fb10db828141dd9ca3f3f7df8eceb87c3dada03185bcf296c49fa9261`): the criteria, the climatology (mean, sigma and file hashes), the populations, the mapping of tasks, the metrics, the 30-case support gate and the observation-only counts below. The `score` stage recomputes the labels and refuses to run unless they reproduce the frozen counts exactly.
4. **Populations and labels.** Track A 2018 (development) and 2019 (**POST-HOC EXPLORATORY ANALYSIS OF THE COMPLETED 2019 FINAL TEST**), Track B 2024 (development) and 2025 (**POST-HOC EXPLORATORY ANALYSIS OF THE COMPLETED 2025 FINAL TEST**). A case is paired with the IMD day initialization date plus its lead day (as in `docs/84`); only cases paired with a July or August day are scored. Track A has the classifier output only for its paired cases (141 and 129 are labelled), Track B for all 375 cases per year (186 labelled).
5. **Two pre-registered tasks.** Predicted ACTIVE_MONSOON versus observed active, and predicted BREAK_WEAK_MONSOON versus observed break. The low/depression class is not scored: **depression is not validated**, because no observation-based depression label exists in this protocol (the IMD best-track terms remain unverified), and the weak part of "Break / Weak" has no published criterion.

## Counts (observation-only, frozen before scoring) and what the gate allowed

| Population | Labelled cases | Observed active / break / neutral | Active task | Break task |
|---|---|---|---|---|
| Track A 2018 (development) | 141 | 0 / 13 / 128 | insufficient support | insufficient support |
| Track A 2019 (post-hoc) | 129 | 30 / 15 / 84 | scored (exactly at the gate) | insufficient support |
| Track B 2024 (development) | 186 | 48 / 0 / 138 | scored | insufficient support |
| Track B 2025 (post-hoc) | 186 | 9 / 18 / 159 | insufficient support | insufficient support |

The support gate (at least 30 cases on both sides of a task) was fixed before the counts existed and was **not relaxed**. Consequently the break task could not be validated in any population: four seasons contain too few break days (the largest is 18 cases). Pooling the populations was not done: the two tracks have different classifiers and are never pooled.

## Result (stored values; balanced accuracy, where 0.5 is no skill)

| | Balanced accuracy [95 % interval] | Recall | Precision | Observed active cases |
|---|---|---|---|---|
| 2019 (post-hoc) | 0.316 [0.237, 0.395] | 0.07 (2 of 30) | 0.04 | 30 |
| 2024 (development) | 0.386 [0.283, 0.486] | 0.25 (12 of 48) | 0.15 | 48 |

Predicted class by observed state:

| | 2019: observed active / break / neutral | 2024: observed active / break / neutral |
|---|---|---|
| Active Monsoon | 2 / 10 / 33 | 12 / 0 / 66 |
| Break / Weak | 0 / 0 / 5 | 0 / 0 / 0 |
| Low / Depression | **28** / 5 / 46 | **36** / 0 / 72 |

## How to read it

- **The pseudo-class named Active does not correspond to observed active spells.** The balanced accuracy is below the chance level in both scored populations, with the whole 95 percent interval below 0.5 in both (the 2024 upper bound is 0.486). Most observed active-spell days (28 of 30 and 36 of 48) are classified as **Low / Depression**, not Active. That is physically plausible, since active spells often coincide with monsoon low-pressure systems, but it means the class name is misleading and any claim that the classifier identifies "active monsoon" is **not supported** by this evidence.
- **The break and depression classes could not be validated** at all.
- **This does not invalidate the correction models.** The regime-aware models route on the classifier's classes whatever they are called, and their verification (`docs/106`, `docs/113`) is unchanged; what this shows is that the labels should not be read as observed meteorological regimes.
- **Why the mapping was not redefined.** Mapping predicted Low/Depression to observed active would fit the result after seeing it. It is reported descriptively in the confusion table; a different mapping would need its own frozen protocol and new data.

## Limits

Two scored populations, one of them exactly at the support gate; labels are rainfall-based and approximate, not the published classification and not an expert review; only July and August are labelled; the intervals resample initialization dates and are optimistic; the approval of this protocol is an interpretation of the owner's general instruction (recorded in the protocol), and the owner may withdraw it.

## Evidence, API, tests

`scripts/fetch_imd_climatology.py`, `scripts/build_regime_validation.py` (stages `freeze` and `score`, write-once), pure code in `backend/app/ml/regime_validation.py`, evidence `regime_validation_protocol_v1.json`, `regime_validation_{A_2018,A_2019,B_2024,B_2025}.json` and `regime_validation_manifest.json` under `backend/app/evidence_data/phase6/`. The API is `/api/science/evidence/regime-validation/{overview,result?year=}` (hash-verified, 503 on tamper) and the panel is on the Regime Intelligence page for both views. Tests: `backend/tests/test_regime_validation.py` (pure functions), `backend/tests/test_regime_validation_evidence.py` (chain, gate, scores re-derived from the stored confusion tables, API, tamper), `frontend-v2/src/lib/api/regime-validation.test.ts` and `frontend-v2/tests/e2e/regime-validation.spec.ts`.
