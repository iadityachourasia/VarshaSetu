# Final PPT Facts — Phase 5B

Single source of numbers for slide decks and printed handouts. Every figure
here is copied from an already-audited canonical source (`docs/91` and the
frozen JSON artifacts it pins) or from this session's own direct reading of
the checked-in static presentation bundle
(`docs/presentation/OFFICIAL_DEMO_CASES.md`). Nothing here was computed,
estimated, or rounded beyond what the source itself states. Do not add a
number to a slide that is not in this file, `docs/91`, or the frozen JSON —
if a judge asks for something not listed, say so and offer to look it up
live rather than estimating on the spot.

## 1. One-line description

VarshaSetu is a research prototype that studies whether regime-aware,
forecast-time statistical post-processing can reduce systematic error in
raw NWP monsoon rainfall forecasts — evaluated on two separate, completed
historical benchmarks. It is not a live forecasting system.

## 2. The two experiment tracks (never pooled)

| | Track A — retrospective | Track B — operational-era |
|---|---|---|
| Forecast source | NOAA GEFSv12 **reforecast** | Historical NOAA **operational** GEFS |
| Truth | IMD gridded rainfall | IMD gridded rainfall |
| Train | 2017 | 2023 (cross-fit) |
| Validate / select | 2018 | 2024 |
| Final test (completed, consumed) | **2019** — 255 cases | **2025** — 232 cases / 301,832 paired cells |
| Grid | 49×49, 0.25° | Same target grid |
| District source | geoBoundaries IND ADM2 2021 | Not produced (see §7) |

Say explicitly, every time: *"different GEFS lineage, different
population — the two tracks are not pooled into one number."*

## 3. Track A (2019) headline

- Raw GEFS RMSE: **19.7735 mm**
- Global XGBoost (M2) RMSE: **17.8487 mm**
- Reduction: **9.73%**
- Population: 255 completed held-out cases, common valid-cell mask
- M2 had the best deterministic RMSE in the 2019 model ladder (M0 Raw, M1
  Linear Ridge MOS, M2 Global XGBoost, M3 Hard Regime, M4 Soft MoE)
- Soft routing (M4) improves on hard routing (M3) for RMSE, but **neither
  beats M2 Global XGBoost**
- In 2019 Raw GEFS remains **stronger than every corrected model (M1–M4)** on
  deterministic Heavy/Very-Heavy CSI/ETS **and on FSS at every scale**
  (`docs/64`, `docs/108`; bootstrap intervals exclude zero). This is a **Track A**
  result: the Track B heavy-rain pattern (regime-aware CSI/FSS above Raw in the
  Low/Depression pseudo-regime, `docs/106`) does **not** replicate on Track A,
  where M3/M4 forecast almost no heavy events.

## 4. Track B (2025) headline

Source: `FINAL_TEST_RESULT.json`, SHA-256
`04a7fc2a434d24449365e2cb9978cbc8584f5cc87ea4f132cfaf6e7fc7a4abca` (hash-pinned,
compared against every displayed value by an automated test).

- Raw GEFS RMSE: **16.1657 mm**
- Preselected **M1 Ridge MOS** RMSE: **15.5736 mm**
- Reduction: **3.66%**
- Population: 232 cases / 301,832 paired cells
- M1 was selected on 2024 data **before** the 2025 holdout was opened — not
  revised afterward
- M2 (secondary, predeclared comparator) reached **15.0022 mm** — lower than
  M1, but it does **not** replace M1 as the primary headline (M1 was the
  model committed to before outcome access)

## 5. The one fact every slide about Track B must carry

> Raw GEFS retained **stronger heavy and very-heavy spatial FSS** than the
> RMSE-selected model, at every one of the four frozen neighbourhood scales
> (1×1, 3×3, 5×5, 9×9). Lower overall rainfall RMSE did **not** translate
> into better extreme-rain spatial skill in 2025.

**Scope of that statement (Phase 4M, `docs/106`).** It is a statement about the
preselected M1 versus Raw — the frozen headline comparison — and must keep
being worded that way. It is not a statement about all corrected models:
post-hoc, for **heavy** rain the regime-aware M3/M4 scored higher than Raw on
FSS and CSI in 2025 (and 2024), mainly in the predicted Low/Depression
pseudo-regime; for **very-heavy** rain Raw stays best at coarse scales. Use the
post-hoc numbers only as labelled, descriptive, non-selecting diagnostics
(2025 is a consumed holdout), never as a replacement headline.

This is not a caveat to bury in small print — the app itself surfaces it on
Overview, Verification, and in Story Mode's dedicated "Extreme-Skill
Limitation" scene. State it in the same breath as the RMSE win, every time.

## 6. Probability / calibration (2025)

- Heavy rainfall Brier Skill Score vs. frozen 2023-prevalence reference:
  **+0.09483** (positive = skill over reference)
- Very-heavy BSS: **+0.02652** (positive, smaller)
- Heavy FAR at the frozen 0.10 decision threshold: **0.69576**
- Very-heavy FAR at the frozen 0.05 decision threshold: **0.85492**
- PR-AUC weakened from 2024 to 2025; upper reliability bins are sparse
- "Calibrated" means the fitted 2024 method — it does **not** mean the 2025
  probabilities were perfectly reliable. Say the FAR number in the same
  breath as the BSS number.

## 7. What is genuinely not built (say this plainly if asked)

- Track B district product (Phase 4N, `docs/107`): **2024 and 2025 only**, as
  a read-only area-weighted aggregation of the frozen grids (same Phase 2C
  overlap weights as 2019), historical replay. **2023 has none**, and there is
  It is not a frozen, hash-pinned artifact of its own. District-level
  verification exists for 2024/2025 under a frozen protocol (`docs/112`, `docs/113`):
  heavy-rain district-event CSI improves for M3/M4 but district-mean error does
  not, and very-heavy skill is not improved; it is post-hoc for 2025 and says
  nothing about warning skill.
- No five-member-ensemble-vs-ML comparison exists outside the 2025 matched
  subset (not for 2019, 2023, or 2024).
- (Updated 2026-10-01) Track A (2019) now has a regime page with evidence tables (`docs/109`); the regime classes remain forecast-only pseudo-labels.
- Regime classes are **forecast-only pseudo-labels**, not independently
  observed monsoon-regime truth. The 2023 out-of-fold balanced agreement
  with these pseudo-labels is 0.8806 — that is agreement with a pseudo-label,
  not meteorological ground truth.

### Added after the Phase 5B freeze (2026-10-01) — what to say, and what not to

- **Coastal and orographic.** The project defines rule-based geographic-forcing zones (distance to coast and local terrain relief, `docs/115`, `docs/116`) and verifies the frozen
  models inside them (`docs/117`, `docs/118`; page: Geographic Zones). There is **no coastal or orographic specialist model**, so the requirement is shown as *partial*, never implemented.
- **The main finding.** The Western Ghats coast (109 of the 1,301 land cells) holds roughly 35 to 43 % of all observed heavy-rain cell-case pairs in every population, and Raw GEFS forecasts
  only about 7 to 22 % as many heavy events as were observed there. No frozen model fixes it; the corrected models help on the operational-era track (differently in 2024 and 2025) and
  not on the 2019 reforecast track. This is the evidence-based target for the next model; it is a finding about frozen models, not a new skill claim.
- **Western disturbances** are not implemented. A feasibility study (`docs/122`) found no label source, no upper-tropospheric fields and an evaluation domain (10–22° N) that excludes the region where they act.
- **Independent regime validation** does not exist; a source probe (`docs/123`) lists candidate sources and obstacles. Do not call the 0.9424 (2018) or 0.8806 (2023 out-of-fold) figures accuracy.
- **Live or new-cycle forecasting** is not built; only a design exists (`docs/125`). The app is a historical replay.
- **Synoptic chart** (Forecast page, operational-era years): wind arrows, 500-hPa height contours and sea-level pressure lines from the frozen control-member forecast fields. It is not an analysis and not a causal explanation.
- **Requirement coverage** is one page, `/compliance`, resolved from hash-verified evidence: 12 of the 14 official requirement IDs are implemented and 2 are partial (regime classification, and improvement over raw because heavy-rain skill is mixed).
- **Not yet decided by the project owner:** the independent test period for any new model, IMD data-redistribution rights, and the label sources for western disturbances and regime validation.

## 8. Data quality (acquisition, cited in Story Mode's "Data Quality" scene)

- Scheduled forecast messages: **1,125**
- c00 (control member) QC-eligible: **615**
- Five-member-ensemble QC-eligible: **218**
- Every scheduled message was actually acquired; the eligible counts reflect
  canonical scientific QC attrition (packing precision, completeness
  checks), not missing data or a failed download.

## 9. Reproducibility and governance

- Frozen models: no retraining after any test was opened
- Hash-verified artifacts at every stage (manifest SHA-256s pinned in
  `docs/91` §19)
- Both the 2019 and 2025 evaluations are one-time, now-consumed final
  tests — neither was reopened for tuning after unsealing
- Two-track separation is structural (different lineages/populations), not
  a UI label choice

## 10. Official demo cases (Phase 5B, this session)

| | Track A anchor | Track B official | Track B backup |
|---|---|---|---|
| Case ID | `20190802T000000Z_day3_24h` | `20250714_day2_24h` | `20250903_day2_24h` |
| Init | 2019-08-02 | 2025-07-14 | 2025-09-03 |
| Lead | Day 3 (+72h) | Day 2 | Day 2 |
| Observed Heavy / Very-Heavy cells | 158 / 70 | 25 / 4 | 28 / 4 |
| Case RMSE, Raw vs. corrected | 41.7434 / 41.3304 mm | 12.617 / 12.663 mm (M1) | 12.796 / 12.623 mm (M1) |
| Case-level correction delta | −0.413 mm (modest improvement) | **+0.046 mm** (near-neutral) | −0.173 mm |
| Dominant pseudo-regime | Low/depression influenced | Active Monsoon (98.3%) | Break/Weak Monsoon (85.2%) |

The 2019 anchor case is one of six descriptive video-catalogue cases chosen
*after* the one-time held-out verification, deliberately including cases
where the correction helped and cases where it worsened (see
`docs/67_VIDEO_DEMO_CASE_CATALOGUE.md`) — it is not presented as the
best-performing case either.

The 2025 official case was chosen explicitly **because** its case-level
delta is near-neutral, not because it is the best-performing case — see
`docs/presentation/OFFICIAL_DEMO_CASES.md` for the full, non-cherry-picked
selection reasoning. If asked "why this case," that is the honest answer.

## 11. Sanctioned vocabulary (say this, not that)

| Say | Do not say |
|---|---|
| "historical case" | "representative result" / "typical case" |
| "forecast-only pseudo-regime" | "the detected weather regime" / "observed regime" |
| "completed held-out evaluation" / "consumed final test" | "live," "currently running," "still sealed" |
| "positive Brier Skill Score, with high FAR" | "calibrated" alone, without the FAR caveat |
| "regime-aware post-processing did not beat global ML on overall RMSE" | "regime awareness improves skill" (unqualified); also not "regime awareness never helps" |
| "post-hoc, regime-aware heavy-rain CSI/FSS exceeded Raw in the Low/Depression pseudo-regime (2024, 2025)" | presenting that as a tested or selected result, or as a headline |
| "Raw had better FSS than every corrected model in the 2019 reforecast benchmark, and than the selected M1 in 2025" | "Raw has better FSS than every corrected model" without naming the benchmark; "regime-aware models improve heavy-rain skill" as a general claim |
| "historical scientific prototype, not operational" | "operational," "production-ready," "live forecasting" |

## 12. Sources

- `docs/91_SCIENTIFIC_COMMUNICATION_ALIGNMENT.md` (canonical claim basis,
  Phase 4K/4L audited)
- `frontend-v2/src/lib/benchmarks/operational-2025.json` (frozen 2025
  numbers actually served by the app)
- `docs/presentation/OFFICIAL_DEMO_CASES.md` (this phase's demo-case
  selection)
- `docs/09_ML_METHODOLOGY.md`, `docs/08_REGIME_METHODOLOGY.md` (methodology
  detail beyond headline numbers)

This session could not re-fetch these numbers from a live backend (no Track
A or Track B backend is reachable in this sandboxed container — see
`docs/presentation/ROUTE_INVENTORY.md` §"What this session could not verify
directly"). Every number above is the last independently audited figure on
record, not a number this session re-derived.
