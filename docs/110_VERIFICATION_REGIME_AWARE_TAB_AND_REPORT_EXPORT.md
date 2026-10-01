# Phase 6E (P0-3) — Verification Lab regime-aware views and exportable verification report

## 1. Purpose and status

The PS lists a **verification report** as an expected output. The app had a Verification Lab but no regime-aware view and nothing downloadable. This phase adds,
on top of the hash-verified evidence (`docs/108`): (1) regime-aware verification views in the Verification Lab for both tracks, and (2) a generated
**verification report** in Markdown, CSV and JSON. No model, metric or number was computed or changed; every report value is read from the evidence file.

## 2. What was built

| Piece | Detail |
|---|---|
| `GET /api/science/evidence/report?track=A\|B&year=&format=md\|csv\|json` (`backend/app/api/evidence.py`) | Verifies the manifest and the evidence file SHA-256, refuses an unregistered evidence role, then renders the report **from the evidence JSON only**. Always an attachment (`Content-Disposition`), with `X-Evidence-SHA256`. Unknown track/year → 404 `SCIENCE_PRODUCT_UNAVAILABLE`; tamper → 503 `SCIENCE_INTEGRITY_FAILURE`; invalid format → 422. |
| Markdown report | title, **mandatory evidence label**, provenance (evidence SHA-256, reproduction status/checks, population, event cells, regime-assignment statement), an explicit list of covered PS metrics, then RMSE/MAE/bias, POD/FAR/CSI/ETS, FSS 1×1/3×3/5×5/9×9 (with defined-case counts) and observed/forecast event cells for all-cases, each pseudo-regime and each lead day, paired bootstrap contrasts (with "excludes/includes 0"), and the limitations list |
| CSV report | long format, one row per group × model × threshold × metric × scale: `track,year,evidence_role,group_type,group,case_count,model,threshold,metric,scale,value,defined_cases,note`. **Undefined values are empty cells with a note, never 0.** |
| JSON report | same rows plus bootstrap, caveats and metadata (`varshasetu-verification-report-v1`) |
| Verification Lab, Track B | new **Regime-aware** tab (2024 development year / 2025 consumed holdout) using the shared panel |
| Verification page, Track A | new section "Regime-aware verification · 2018 / 2019 reforecast" (population selector) using the same panel; independent of the server-side Track A fetches, so it stays available on its own |
| Shared panel | the verification report download links (Markdown · CSV · JSON) appear in the panel header on the Verification page and on the Regime page |

PS metric coverage of the report: **RMSE, ETS, CSI, POD, FAR and FSS** (plus MAE, bias, event counts), each by regime and by lead, for the two thresholds that define heavy and very-heavy rain.

## 3. Verification

| Check | Result |
|---|---|
| Backend `test_evidence.py` | 33/33 (11 new): every format carries the label, evidence SHA-256 and attachment headers for all four populations; CSV/JSON rows equal the evidence values exactly (POD/FAR/CSI/ETS, FSS with defined-case counts, RMSE, by regime and lead); undefined FAR stays undefined in MD/CSV/JSON (Track A 2019: `… very-heavy FAR \| 0.8412 \| 0.8800 \| undefined \| undefined \| undefined`); all PS metrics and groups present; invalid format, unavailable year and a tampered file are refused |
| `tsc`, `eslint src`, Vitest | clean, 98/98 |
| Playwright `verification-regime-aware.spec.ts` | 5/5: clicks the real download links and inspects the downloaded Markdown/CSV/JSON (filenames, label, metrics, CSV header, JSON schema and row count), the 2018 relabel, the Track B tab with 2024↔2025 switching, the report links on the Regime page, no horizontal overflow at 390/820 px |
| Browser check | Track A section and Track B tab render with labels and downloads; values equal `docs/108` |
| Full regression | see §5 |

## 4. Limitations

- The report reproduces the evidence tables; it is not a new analysis and does not include the older Track A ladder/probability/reliability pages (those remain on the Verification page above it). Probability skill (Brier, reliability) is **not** in this report.
- Reports exist only for the four published populations (Track A 2018/2019, Track B 2024/2025); 2017 and 2023 are training/cross-fit years and have none.
- Report generation is live-API only; there is no offline copy.
- Numbers are formatted to 3–4 decimals in Markdown; the CSV/JSON carry full precision.
- The panel inherits the docs/108–109 limitations (post-hoc consumed holdouts, pseudo-label regimes, optimistic bootstrap intervals, Track A does not show the Track B heavy-rain pattern).

## 5. Regression

Backend suite: 249 passed, 14 errors (all the known Windows `tmp_path` permission error, `docs/101`). Full Playwright, one worker, `next start` and the real backend: **70 passed, 1 failed** - the pre-existing `demo-flow.spec.ts:4` Overview strict-locator failure (`"9.73%"` in two elements since the Overview redesign; identical on the pre-Phase-4N code, `docs/107` §7).

Gate: `P0_3_VERIFICATION_REPORT_AND_REGIME_TAB_COMPLETE` (presentation and export only; no scientific claim added).
