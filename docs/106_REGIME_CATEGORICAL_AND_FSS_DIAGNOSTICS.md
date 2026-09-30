# Phase 4M — FSS and regime-stratified categorical diagnostics for M0–M4 (Track B)

## 1. Purpose and status

Closes a verification gap: FSS existed only for Raw vs M1 (2025) and Raw vs M2 (2019), and categorical
scores (POD/FAR/CSI/ETS) were never stratified by regime. This phase re-aggregates **already-frozen**
predictions; it fits, tunes and selects nothing. Code: `experiments/recent_historical/phase4m_regime_categorical_fss_v1/`
(`analysis.py` pure functions, `run.py`), tests: `backend/tests/test_phase4m_regime_diagnostics.py`,
outputs: `.../results/{2024,2025}_regime_categorical_fss.json`.

**Evidence roles — read before quoting anything**

| Year | Role | What it may be used for |
|---|---|---|
| 2024 | Phase 4I validation/selection year | Development-year evidence. M1 was selected on it, so it is not a holdout. |
| 2025 | Phase 4J holdout, **already consumed** | **Post-hoc descriptive only.** Must not select, tune or re-rank any model. The preselected primary model remains M1 (docs/89). |

Regime = argmax of the frozen forecast-only pseudo-regime classifier; these are pseudo-labels, not observed
meteorological truth (docs/54, 55, 91). M3 routes by exactly this argmax, so within a predicted regime M3 *is* that specialist.

## 2. Method and controls

- Same populations, 49×49 paired grids, valid masks, thresholds (≥64.5 and ≥115.6 mm/24 h) and FSS scales (1/3/5/9) as Phase 4I/4J; FSS arithmetic mirrors `phase2c.fss_many` (summed numerator/denominator across cases, edge clipping, ≥50 % valid-neighbourhood rule).
- **Reproduction gate (passed):** for both years the new code reproduces the frozen Raw and primary-model FSS (all 8 threshold×scale cells × 2 models) and the frozen M2/M3/M4 by-regime RMSE/MAE/bias, 43 checks per year, **max absolute difference 0**.
- Count-based POD/FAR/CSI/ETS are asserted equal to `phase2b.event_metrics` on the same cells.
- Uncertainty: paired case-cluster bootstrap (2 000 draws, seed 26080). Cases are resampled whole and every model is scored on the same draws. Caveat: consecutive dates/leads are serially correlated, so these intervals are **optimistic**.
- Frequency bias (forecast event cells / observed event cells) is reported because CSI/FSS can reward over-forecasting.

## 3. Results — heavy rain (≥64.5 mm/24 h)

Overall FSS (each model on its own defined cases; 2024 n=160, 2025 n=213–214):

| Year | Scale | M0 Raw | M1 | M2 | M3 | M4 |
|---|---|---|---|---|---|---|
| 2024 | 1×1 | .139 | .050 | .351 | .374 | .370 |
| 2024 | 9×9 | .259 | .092 | .545 | .570 | .565 |
| 2025 | 1×1 | .091 | .039 | .136 | .171 | .162 |
| 2025 | 3×3 | .156 | .067 | .221 | .274 | .263 |
| 2025 | 9×9 | .252 | .106 | .242 | .310 | .291 |

Overall CSI: 2024 Raw .075, M1 .026, M2 .213, M3 .230, M4 .227; 2025 Raw .048, M1 .020, M2 .073, M3 .094, M4 .088.
Heavy frequency bias is **below 1 for every model** overall (2025: Raw .22, M2 .15, M3 .24, M4 .20); regime-aware models are less suppressed, not over-forecasting.

Paired bootstrap, point [95 % CI]:

| Year | Contrast | ΔCSI | ΔFSS 3×3 |
|---|---|---|---|
| 2024 | M3 − Raw | +.155 [+.119,+.189] | +.300 [+.233,+.360] |
| 2024 | M3 − M2 | +.017 [+.004,+.031] | +.023 [−.000,+.048] |
| 2025 | M3 − Raw | +.046 [+.020,+.071] | +.118 [+.051,+.181] |
| 2025 | M3 − M2 | +.021 [−.005,+.046] | +.053 [−.014,+.117] |
| 2025 | M2 − Raw | +.025 [−.007,+.055] | +.065 [−.027,+.147] |

### By predicted regime (heavy CSI; FSS 3×3 in brackets), cases in parentheses

| Year | Regime | Raw | M2 | M3 | M4 |
|---|---|---|---|---|---|
| 2024 | Active (59) | .086 [.266] | .035 [.110] | .042 [.138] | .058 [.186] |
| 2024 | Break/Weak (46) | .043 [.222] | 0 [0] | 0 [0] | 0 [0] |
| 2024 | Low/Depression (78) | .074 [.206] | .254 [.547] | .270 [.564] | .264 [.556] |
| 2025 | Active (100) | .028 [.095] | .064 [.199] | .036 [.117] | .039 [.131] |
| 2025 | Break/Weak (71) | .020 [.081] | 0 [0] | 0 [0] | 0 [0] |
| 2025 | Low/Depression (61) | .081 [.237] | .103 [.288] | **.179 [.451]** | .165 [.425] |

Regime-level bootstrap (heavy): Low/Depression M3 − M2 ΔCSI **+.076 [+.042,+.119]** (2025), +.016 [+.001,+.032] (2024); Active M3 − M2 −.028 [−.062,+.006] (2025), M4 − M2 −.025 [−.054,−.000]; Break/Weak M3 − Raw −.020 [−.037,−.003] (2025), FSS 3×3 −.222 [−.408,−.017] (2024).

## 4. Results — very heavy (≥115.6 mm/24 h)

Sparse (2025: 1 430 event cells, 121 cases; 2024: 1 589 cells). 2025 overall CSI: Raw .020, M1 .010, M2 **.001**, M3 .022, M4 .009; FSS 3×3: Raw .086, M1 .038, M2 .002, M3 .093, M4 .038; at 9×9 the order is Raw .171 > M3 .125 > M1 .071 > M4 .050 > M2 .003 (Raw best). Bootstrap 2025: M3 − M2 ΔCSI +.022 [+.001,+.063]; M4 − Raw ΔCSI −.011 [−.021,−.002]; M3 − Raw ΔCSI +.003 [−.013,+.021] (no difference). 2024: M3 leads (CSI .053 vs Raw .015, M2 .044), all signal again sits in the Low/Depression class; Active and Break/Weak classes forecast no very-heavy cells in either year.

## 5. What this changes about earlier statements

1. "Raw GEFS beats corrected models on FSS at every scale" (docs/60, 64, 89, `FINAL_PPT_FACTS §3`) is true **only for the pairs that were measured**: M2 in 2019 and M1 in 2025. For **heavy rain, M3/M4 (and M2 at fine scales) exceed Raw on FSS and CSI in both 2024 and 2025**; for very-heavy rain in 2025 Raw still wins at coarse scales and M2 collapses.
2. "Regime-aware did not beat global" (`JUDGE_QA`) is correct for RMSE/MAE/bias only. For heavy-rain categorical/spatial skill in 2024 and 2025, hard-routed M3 is nominally best overall, with the M3 − M2 overall interval excluding zero in 2024 (CSI) but not in 2025.
3. The benefit is **entirely regime-specific**: it comes from the Low/Depression specialist. In the Active regime the global model is as good or better (2025) and corrected models are below Raw (2024). In Break/Weak M2/M3/M4 forecast essentially no heavy cell (frequency bias ≤ 0.001; zero CSI/FSS) and lose to Raw — the Break specialist has collapsed to "no extreme rain". (M1, not shown in the table, is also below Raw there.)
4. The regime-aware models have worse MAE, positive bias (2025 +0.17/+0.25 mm vs −0.93 M2) and do not improve RMSE, so the honest framing is a trade-off: better categorical/spatial extreme skill in one regime versus worse mean error.

Rewording applied after this phase: scope notes or narrowed sentences in `docs/05, 60, 61, 64, 72, 74, 76, 77, 79, 89 (§33), 91 (§7)` and `docs/presentation/FINAL_PPT_FACTS.md, JUDGE_QA.md, FINAL_DEMO_NARRATION.md`. Frozen measured values and decision labels (`RAW_BETTER`, `SELECTED_MODEL_IMPROVED_RMSE`) were not changed; docs/89's result hash covers `FINAL_TEST_RESULT.json`, not the markdown.

## 6. Limitations (do not remove when quoting)

- Post-hoc and exploratory: many contrasts, no multiplicity correction. 2025 cannot be used for model choice; 2024 is the selection year.
- Single year per result; three-class pseudo-regimes; Low/Depression is one class among three and dominates event counts (2025: 2 517 of 6 760 heavy cells; 2024: 4 798 of 6 366).
- Bootstrap intervals ignore temporal autocorrelation and are optimistic; very-heavy intervals rest on few event cases.
- Track A (2019) is not covered: per-case M3/M4 grids are not served or cached in a form used here.
- Frozen primary-model statements in docs/89 (M1, `RAW_BETTER`) remain correct and are not altered by this phase.

## 7. Reproduce

```bash
python -m experiments.recent_historical.phase4m_regime_categorical_fss_v1.run   # ~80 s, CPU only
python -m pytest backend/tests/test_phase4m_regime_diagnostics.py -q
```

Outputs are write-once-style: a rerun aborts if a result file would change.

Gate: `REGIME_DIAGNOSTICS_COMPLETE_REPRODUCTION_PASSED` (not an operational-performance claim).
