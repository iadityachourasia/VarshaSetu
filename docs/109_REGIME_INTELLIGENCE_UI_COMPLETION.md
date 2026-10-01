# Phase 6D (P0-2) — Regime Intelligence UI completion

## 1. Purpose and status

Removes the last "Feature in Development" state from the core Regime page and gives **both tracks** a real workbench built only on frozen, hash-verified
evidence (`docs/108`). No backend, model or number changed in this phase; it is a presentation layer over `/api/science/evidence/regime-verification`
and the existing case APIs.

## 2. What changed

| Area | Before | After |
|---|---|---|
| `/regimes` (Track A, any non-operational experiment) | full-page "Feature in Development" placeholder | `RegimeTrackA`: per-case forecast-only probabilities (2019; from the published case catalogue), 2019 case distribution by dominant pseudo-regime, routing pathway, and the verification evidence panel |
| `/regimes?experiment=operational` (Track B) | per-case probabilities, distribution, 2025 M2–M4 RMSE strip; fell back to the WIP placeholder if the case list failed | unchanged content **plus** the verification evidence panel; a failed case list now shows an honest data-unavailable error, never a placeholder |
| Regime-aware verification | none in any route | `RegimeEvidencePanel` (shared): RMSE/MAE/bias, POD, FAR, CSI, ETS, FSS (1/3/5/9) and forecast/observed event ratio for M0–M4, each by pseudo-regime and by lead day; heavy ≥ 64.5 and very heavy ≥ 115.6 mm/24 h; paired-bootstrap contrasts |
| Removed | `regime-work-in-progress.tsx`, its Playwright spec, ~22 lines of `.regime-development*` CSS | — |

Files: `frontend-v2/src/app/regimes/page.tsx`, `components/regimes/{regime-track-a,regime-evidence-panel,regime-intelligence}.tsx`, `lib/api/evidence.ts` (+ test), `tests/e2e/regimes.spec.ts`, `app/globals.css`.

## 3. Honesty controls built into the panel

- **Mandatory label.** The banner shows the API's `evidence_label`: "POST-HOC EXPLORATORY ANALYSIS OF THE COMPLETED 2019/2025 FINAL TEST" for consumed holdouts, "development evidence … not a holdout" for 2018/2024. The label comes from the backend and cannot be omitted.
- **No typed science numbers.** Every value is read from the API; the RMSE-versus-Raw percentages are computed in the component from the served RMSEs.
- **Undefined stays undefined.** Null FAR/CSI/FSS render as "undefined" (never 0); FSS cells show the number of defined cases and the note lists undefined cases per model; very-heavy event suppression is visible through the forecast/observed event ratio.
- **Uncertainty.** Paired differences show the interval and state "excludes 0"/"includes 0" in words, not colour; the optimistic-bootstrap caveat is shown.
- **Training years.** 2017 (Track A) and 2023 (Track B) state that models were fitted on them, so no verification is published; 2018 has no per-case probabilities (only 2019 cases are published).
- **Taxonomy.** The page states that coastal, orographic and western-disturbance regimes are not yet part of the classifier, that classifier agreement is with pseudo-labels (not meteorological accuracy), and that no independent expert validation exists.
- **Data source.** Live API only — the evidence is not in the static presentation bundle, so on an unreachable API the panel shows an error rather than cached numbers.

## 4. Verification

| Check | Result |
|---|---|
| `tsc --noEmit`, `eslint .` | clean |
| Vitest | 98/98 (8 new: schema parsed against the **real tracked evidence files** for all four populations, null preservation, hash/model/regime validation, structured errors) |
| Production build (`next build`) | OK |
| Playwright `regimes.spec.ts` | 6/6: no WIP text; mandatory post-hoc label; table values equal the evidence API (CSI by regime/lead, FSS 5×5 with defined-case counts); 2018/2017 and 2023 states; Track B toggles; paired-difference wording; no horizontal overflow at 390/820 px |
| Browser check (Track A 2018/2019, Track B 2023/2025) | all states render; values equal `docs/106`/`docs/108` (e.g. 2025 heavy CSI Low/Depression: Raw .081, M2 .103, M3 .179, M4 .165) |
| Full Playwright regression | see §6 |

## 5. Limitations

- Track A per-case probabilities exist for 2019 only; there is no Track A regime-by-case view for 2018.
- The panel is a verification table view, not yet the judge-facing "regime-aware correction" story page; the Verification Lab tab and report export are P0-3.
- Metric names are shown in full in the panel but the shared metric-definition tooltips (`lib/metric-definitions.ts`) are not yet wired into these tables.
- Accessibility was checked structurally (table captions, scope headers, `aria-pressed` groups, words not colour); the repo's axe audit script was not re-run for the new page.

## 6. Regression

Full Playwright suite, one worker, against `next start` and the real backend: **65 passed, 1 failed**. The single failure is `demo-flow.spec.ts:4`, the pre-existing Overview strict-locator failure (`"9.73%"` appears in two elements since the Overview redesign; it fails identically on the code before Phase 4N, see `docs/107` §7). The removed WIP spec is replaced by `regimes.spec.ts`. Backend suite unchanged by this phase (238 passed, 14 known Windows `tmp_path` errors).

Gate: `P0_2_REGIME_UI_COMPLETE` (presentation only; no scientific claim added).
