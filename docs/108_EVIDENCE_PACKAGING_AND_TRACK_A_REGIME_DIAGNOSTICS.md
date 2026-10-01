# Phase 6A (P0-1) — Served regime-aware verification evidence + Track A 2018/2019 M3/M4 diagnostics

## 1. Purpose and status

Closes two gaps found in the post-audit reconciliation: (1) the Phase 4M regime/lead FSS and categorical results (docs/106) existed only in the
gitignored `experiments/` tree and were unreachable from the API, the UI and the deployed image; (2) **Track A had no FSS or by-regime/by-lead
diagnostics for M1, M3 or M4**. This phase re-aggregates **frozen** artifacts only — no model was trained, tuned or selected — and packages all
four populations as tracked, hash-manifested evidence served by a read-only API. No UI change yet (P0-2/P0-3 consume this).

| Population | Role | Label served with every payload |
|---|---|---|
| Track A 2018 (251 cases) | validation year; used for early stopping and model selection | "development evidence … not a holdout" |
| Track A 2019 (255 cases) | consumed final test | **POST-HOC EXPLORATORY ANALYSIS OF THE COMPLETED 2019 FINAL TEST** |
| Track B 2024 (183 cases) | validation/selection year (M1 selected on it) | "development evidence … not a holdout" |
| Track B 2025 (232 cases) | consumed final test | **POST-HOC EXPLORATORY ANALYSIS OF THE COMPLETED 2025 FINAL TEST** |

## 2. What was built

- `backend/app/ml/verification_extra.py` — tracked home of the Phase 4M pure functions (FSS components, counts→POD/FAR/CSI/ETS, paired case bootstrap, `Population`, `analyse`). Phase 4M now imports it; a full re-run reproduced both Phase 4M outputs **byte-for-byte** (write-once guard), so the refactor changed no number.
- `scripts/build_phase6_evidence.py` — tracked, read-only builder. Track A: verifies the cache arrays (SHA-256), the freeze manifest and every frozen model hash, applies the **frozen** ridge/global/3 experts (M3 hard-routes on the classifier argmax; M4 blends by the classifier probabilities) to the cached 2018/2019 feature matrices, then analyses. Track B: copies the Phase 4M results unchanged.
- **Reproduction gate.** Before anything is written, every frozen per-model overall / per-lead / per-regime metric is recomputed: hit/miss/false-alarm counts must match **exactly** and continuous metrics to 1e-6 mm. Result: **175 checks per Track A year, counts exact, max abs diff 4.2e-9 (2018) / 5.8e-9 (2019) mm** (float32 accumulation noise). Builder also asserts finite, non-negative, aligned predictions and regime probabilities summing to 1.
- `backend/app/api/evidence.py` — `GET /api/science/evidence/manifest` and `GET /api/science/evidence/regime-verification?track=A|B&year=`. Verifies the manifest sidecar hash and each file's SHA-256 (failure → 503 `SCIENCE_INTEGRITY_FAILURE`), refuses any file whose evidence role has no registered display label, and adds a population summary (case count, event cells, defined/undefined FSS cases per model/scale/threshold) derived only from fields already in the file.
- Evidence files live in `backend/app/evidence_data/phase6/` (~0.67 MB, git-tracked). **Deviation from the plan** (`data/manifests/phase6/`): the Docker build context excludes `data/`, and the ignore-exception behaviour could not be verified here (no running Docker daemon); a wrong guess would break the Render build. Inside `backend/` the existing `COPY backend/ backend/` ships it with no Dockerfile change.
- `backend/tests/test_evidence.py` (22 tests, no untracked data needed): pure-function equivalence with frozen `fss_many`/`event_metrics`; partition/sum invariants for all four files; Track A evidence equals the **tracked** frozen `2019_final_results.json` and `model_selection_freeze.json` numbers; tamper (file, manifest) → 503; unregistered role never served; mandatory post-hoc labels.

## 3. Track A results (heavy ≥ 64.5 mm/24 h; all numbers from the served evidence)

| Metric | Year | M0 Raw | M1 | M2 | M3 | M4 |
|---|---|---|---|---|---|---|
| CSI | 2018 | .0757 | .0222 | .0386 | .0165 | .0163 |
| CSI | 2019 | .1204 | .0377 | .0485 | .0088 | .0077 |
| FSS 3×3 | 2018 | .2259 | .0654 | .1194 | .0522 | .0517 |
| FSS 3×3 | 2019 | .3310 | .1122 | .1454 | .0305 | .0267 |
| FSS 9×9 | 2019 | .4268 | .1474 | .1638 | .0328 | .0292 |
| Forecast/observed heavy-event frequency | 2019 | .506 | .104 | .088 | .021 | .019 |

- **Raw beats every corrected model on heavy-rain CSI and FSS at every scale, in both years.** Paired case-cluster bootstrap 2019: M3 − Raw ΔCSI −.112 [−.133, −.090], ΔFSS3×3 −.301 [−.348, −.249]; M3 − M2 ΔCSI −.040 [−.057, −.023]; M4 − M3 ≈ 0 (+.001 [0.000, +.003]).
- **Very heavy (≥ 115.6 mm):** M2, M3 and M4 forecast **no** very-heavy cell in 2018 or 2019 (FAR undefined, CSI/FSS 0); M1 CSI .0030 (2019); Raw CSI .0333, FSS 3×3 .1086.
- **By regime (2019 heavy CSI, Raw / M2 / M3):** Active .1237 / .0374 / 0; Break/Weak .0073 / .0016 / 0; Low/Depression .1320 / .0573 / .0132. The Active and Break/Weak specialists forecast **zero** heavy events; only the Low/Depression specialist forecasts any, far below Raw.
- **By lead (2019 heavy CSI, Raw / M3):** Day 1 .1277 / .0103; Day 2 .1233 / .0074; Day 3 .0997 / .0081.
- **RMSE by regime still favours correction** (2019 Raw / M2 / M3 / M4): Active 18.46 / 15.65 / 16.89 / 16.74; Break 15.40 / 12.70 / 13.01 / 12.98; Low 22.58 / 21.42 / 21.79 / 21.81 — M2 lowest in all three, consistent with docs/61.

## 4. Answers to the six questions (both tracks; no cherry-picking)

1. **Does M3/M4 improve event detection over Raw?** *Track B:* yes for heavy rain (2024 CSI .230/.227 vs .075; 2025 .094/.088 vs .048; intervals exclude 0), not for very heavy. *Track A:* **no** — worse than Raw in both years (intervals exclude 0), and no very-heavy forecasts.
2. **Spatial extreme skill?** *Track B:* heavy FSS above Raw (2025 3×3 .274/.263 vs .156; 9×9 interval includes 0); very-heavy Raw best at coarse scales. *Track A:* **no** — FSS far below Raw at all scales and thresholds.
3. **Regime dependence?** Yes on both tracks. *Track B:* the gain is confined to Low/Depression; Break→0. *Track A:* Active/Break specialists forecast no heavy cell; Low/Depression forecasts some but far below Raw.
4. **Lead dependence?** Modest. Raw skill falls with lead (Track A heavy CSI .128→.100); the corrected models' deficit is largest at Day 1 on Track A.
5. **M4 vs M3?** No material difference on either track for categorical/spatial skill (Track A ΔCSI ≈ +.001; Track B M3 nominally ahead, not significant); M4 is better on RMSE among the regime models.
6. **Where does M2 remain better?** RMSE/MAE/bias on both tracks; Track A heavy CSI/FSS over M3/M4; Track B Active regime (2025). M2 also collapses very-heavy forecasting on both tracks.

## 5. What this changes in earlier statements

- **The Track B heavy-rain regime-aware gain does not replicate on Track A.** It must never be presented as a general property of regime-aware post-processing. The supportable wording remains: regime-aware post-processing improves RMSE vs Raw on both tracks and does not beat the global model on RMSE/MAE/bias.
- **"Raw beats corrected on FSS" is now measured for Track A for all four corrected models** (M1–M4, both years). Earlier wording scoped to "Raw vs M2 only" (docs/60, 64, 72, 74, 77, 79, 05, 91, `FINAL_PPT_FACTS`) has been updated accordingly. For Track B the statement remains M1-specific (docs/89 frozen result) with the docs/106 caveat.

## 6. Limitations

- Post-hoc and exploratory; intervals are optimistic (serial correlation); regimes are forecast-only pseudo-labels.
- **Confounded cause (hypothesis, untested):** the Track A global/expert models used a Tweedie objective with early stopping (81 rounds, selected on 2018 RMSE) and experts trained on 62–99 cases, both of which shrink extreme predictions; Track B used squared error with 200–350 rounds. Track, objective and training size differ together, so the cause of the Track A/B difference is not established.
- Case-balanced weighting is a no-op on both tracks (every paired case has exactly 1,301 cells).
- The Track A builder needs the local, untracked 2018/2019 feature caches; the evidence it produced is tracked and served, and is validated in CI against the tracked frozen results.
- Docker/Render behaviour of the new files was not built locally (no Docker daemon); they sit under `backend/`, which the existing image already copies.

## 7. Reproduce

```bash
python scripts/build_phase6_evidence.py      # ~20 s, CPU; aborts if any output would change
python -m pytest backend/tests/test_evidence.py -q
```

Gate: `P0_1_EVIDENCE_PACKAGED_TRACK_A_DIAGNOSTICS_REPRODUCED` (not a performance claim).
