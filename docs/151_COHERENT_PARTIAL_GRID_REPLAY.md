# Coherent partial-grid June 2024 replay and development score

Date: 2026-10-07. This research-only continuation of [the partial-grid
candidate](149_PARTIAL_GRID_INFERENCE_CANDIDATE.md) applies the sealed
symmetric probability projection in
`coherent_probability_projection_protocol_v1.json` to the **unchanged frozen
forecast models**. It does not change `data/live`, the scheduler, API,
dashboard, model weights or the strict live `P(very heavy) ≤ P(heavy)` gate.
The forecast replay uses the same 30 hash-verified June 2024 GEFS 00 UTC
cycles, 90 date/lead windows, 99% regional valid-cell gate and 95% district
weighted-area gate. The separate forecast protocol was hash-sealed before
running any cycle. The forecast-only year seal and per-cycle masks, fields,
district tables, source hashes and model hashes are immutable under
`data/processed/coherent_partial_grid_v1/2024/`.

## Forecast-only result

| Gate | Count |
|---|---:|
| Planned leads / coherent ready leads | 90 / 90 |
| Previously ready leads matched field by field | 55 |
| Newly ready versus the previous strict probability gate | 35 |
| Leads with at least one projected cell | 35 |
| Projected forecast cells | 3,094 |
| District-by-ready-lead values suppressed below 95% area | 218 |

For each of the 55 leads previously ready, the replay required bitwise
agreement for the valid mask and every retained M0/M2/M4 and event-probability
field. Invalid cells remain NaN. A district below 95% weighted coverage
remains null. Thus the projection fixes the **forecast-side ordering gate**
for this June population without manufacturing missing rainfall or district
values. It has not passed an independent-year check.

## Observation-paired development diagnostic

After the forecast-only year seal, a separate scoring protocol was frozen,
then all ready grids were paired with the hash-verified 2024 IMD 0.25-degree
03–03 UTC reference on the same valid cells. The original Phase 4I
probability cutoffs, 0.10 for heavy and 0.05 for very heavy, and 2023
climatologies were held fixed. June 2024 was previously used for development
and 2024 for calibrator selection; these are **descriptive development
scores**, not independent validation or proof of calibration.

| Stratum | Leads | Paired cells | Raw RMSE | Global M2 RMSE | Regime M4 RMSE | Heavy BSS | Very-heavy BSS |
|---|---:|---:|---:|---:|---:|---:|---:|
| All ready | 90 | 116,823 | 15.003 | **13.776** | 13.827 | +0.078 | **−0.030** |
| Previously ready | 55 | 71,376 | 15.344 | **13.983** | 14.213 | +0.080 | **−0.057** |
| Newly ready | 35 | 45,447 | 14.453 | 13.444 | **13.199** | +0.076 | +0.038 |

RMSE is mm per 24 h. BSS compares each projected-probability Brier score
with its frozen 2023 climatology reference on the same cells. On all ready
cells there were 1,576 observed heavy and 206 observed very-heavy events.
At the frozen probability cutoffs, heavy warnings were forecast 2.40 times
the observed frequency (658 hits, 918 misses, 3,132 false alarms; CSI
0.140). Very-heavy warnings were forecast **9.24 times** the observed
frequency (82 hits, 124 misses, 1,822 false alarms; CSI 0.040). The 3×3
heavy-rain FSS for M2 was 0.366. Full per-lead counts, ten-bin reliability
tables, ETS, POD, FAR, FSS, and date-block bootstrap intervals are in the
hash-sealed `coherent_partial_grid_score_v1.json`. The descriptive date-block
95% BSS interval over all ready leads is +0.016 to +0.127 for heavy and
−0.097 to +0.017 for very heavy; spatial and serial dependence remain.

## Decision and next gate

The ordering repair makes all 90 **research** leads forecast-ready, but the
very-heavy warning probabilities remain weak and strongly overforecast at
the frozen decision cutoff. Do **not** promote this bundle or call the
projected output calibrated. Keep the strict global product as default.
The next scientific task is a separately frozen, lead-aware extreme-event
calibration study on development years, followed by a genuinely independent
test year and fresh-cycle inference. The intended 2026 independent test
remains unscored until its IMD reference is available and its model-version
partition is resolved. Revisit district publication only after that evidence.

Reproduce the forecast seal with
`python scripts/run_coherent_partial_grid.py --all-june-2024` and the score
with `python scripts/score_coherent_partial_grid.py`. Both refuse changed
protocol, source or prior-artifact hashes and changed write-once results.
The scorer reproduced its sealed result byte for byte. Focused tests passed
(17), and the complete backend suite passed (759) on 7 October 2026.
