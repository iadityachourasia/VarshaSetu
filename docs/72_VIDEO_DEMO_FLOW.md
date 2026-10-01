# Phase 3A Historical Video Demo Flow

All cases come from the official frozen Phase 2C video catalogue. The
default selected case is an illustrative historical case, not a “best model
case”; aggregate completed held-out 2019 metrics provide performance evidence.
All interactive maps in this flow are 2019 GEFSv12 reforecast artifacts. The
separate consumed 2025 operational-era benchmark is not visualized by these maps.

1. Open Overview. Identify the historical-prototype status and the
   API-derived 9.73% M2-versus-Raw RMSE reduction, 19.7735 to 17.8487 mm.
2. Enter Forecast Explorer through the primary action. Use the official
   demo selector or chronological case selector. State GEFS initialization,
   24-hour valid period and Day 1/2/3 lead.
3. Show synchronized Raw GEFS, frozen VarshaSetu M2 correction, and IMD
   observation maps with one rainfall legend. Inspect one cell by pointer or
   keyboard; show exact values and correction delta.
4. Read the forecast-only three-regime probability bars. Explain that
   these reproduce a deterministic pseudo-label methodology, not an
   independent meteorological ground-truth regime score.
5. Open Extreme Rain for the same case. Toggle Heavy ≥64.5 and Very Heavy
   ≥115.6 mm/24h calibrated probability maps. Show 2019 Brier, BSS,
   PR-AUC, ROC-AUC and reliability bins without calling probability rain.
6. Open District Intelligence for the same case. Select a real intersecting
   district; show area-weighted mean/max rainfall, event probabilities and
   affected fractions. Do not imply nationwide or unvalidated MP coverage.
7. Open Verification. Show the complete M0–M4 table and 1×1/3×3/5×5/9×9
   FSS. Say plainly: M2 wins overall RMSE; Raw remains stronger than every corrected model on
   the reported deterministic extreme-event spatial skill (`docs/108`).
8. End on Methodology: 2017 train, 2018 validate/calibrate, completed 2019
   final test; provenance and the non-operational readiness boundary. If the
   2025 result is included, show a separate sourced verification summary:
   preselected M1 Ridge reduced RMSE by 3.66% on 232 historical operational-era
   cases, while Raw retained better extreme spatial FSS than that selected M1
   (not a statement about every corrected model; see `docs/106`). Never merge it with
   the 2019 map story or pool the metrics.

The automated path is `frontend-v2/tests/e2e/demo-flow.spec.ts`. Its
screenshots are UI evidence only. No page triggers training, GRIB decoding,
or Phase 2B/2C artifact mutation.
