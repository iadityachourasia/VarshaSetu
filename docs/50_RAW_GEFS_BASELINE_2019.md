# Raw GEFS Control Baseline — 2019 JJAS

Status: raw NWP verification only. This is not AI evaluation and contains no
VarshaSetu improvement claim.

Only `CONTROL_MODEL_ELIGIBLE` c00 cases are verified against aligned IMD fields.
The denominator therefore differs by product according to valid cases and masks.
Machine-readable results are in
`data/manifests/phase1e/2019-JJAS/raw_gefs_control_baseline.json`.

## Continuous metrics

| Product | Valid grid cells | RMSE (mm) | MAE (mm) | Bias (mm) |
|---|---:|---:|---:|---:|
| Day 1 | 31,224 | 20.2392 | 9.6067 | +0.3110 |
| Day 2 | 20,816 | 26.6491 | 13.2176 | -2.0524 |
| Day 3 | 15,612 | 25.6063 | 12.0188 | -2.9191 |

## Heavy-rain contingency metrics

### >=64.5 mm/24 h

| Product | POD | FAR | CSI | ETS |
|---|---:|---:|---:|---:|
| Day 1 | 0.1724 | 0.6107 | 0.1357 | 0.1245 |
| Day 2 | 0.1971 | 0.5397 | 0.1601 | 0.1433 |
| Day 3 | 0.1618 | 0.4462 | 0.1431 | 0.1303 |

### >=115.6 mm/24 h

| Product | POD | FAR | CSI | ETS |
|---|---:|---:|---:|---:|
| Day 1 | 0.0382 | 0.4000 | 0.0372 | 0.0365 |
| Day 2 | 0.0244 | 0.8706 | 0.0210 | 0.0175 |
| Day 3 | 0.0329 | 0.8070 | 0.0289 | 0.0258 |

### >=204.5 mm/24 h (descriptive)

| Product | POD | FAR | CSI | ETS |
|---|---:|---:|---:|---:|
| Day 1 | 0.0000 | N/A | 0.0000 | 0.0000 |
| Day 2 | 0.0000 | 1.0000 | 0.0000 | -0.0004 |
| Day 3 | 0.0000 | 1.0000 | 0.0000 | -0.0004 |

Day 1 has no forecast-positive extremely-heavy cells, so FAR is mathematically
undefined and is reported as `N/A`, not zero. These metrics are an honest raw
baseline on the narrow eligible subset. They must not be compared with a future
post-processor unless the exact same case intersection is used.

## V2 canonical-reconstruction baseline

Phase 1F recomputed raw c00 verification on the expanded v2 eligible set. This
is a data-processing correction, not evidence of forecast improvement.

| Product | Cells | RMSE mm | MAE mm | Bias mm |
|---|---:|---:|---:|---:|
| Day 1 | 158,722 | 19.2297 | 9.4249 | +1.9673 |
| Day 2 | 93,672 | 21.1652 | 9.6315 | -0.1752 |
| Day 3 | 79,361 | 19.1352 | 8.7744 | -1.2453 |

| Threshold | Product | POD | FAR | CSI | ETS |
|---:|---|---:|---:|---:|---:|
| 64.5 | Day 1 | 0.1831 | 0.7031 | 0.1277 | 0.1178 |
| 64.5 | Day 2 | 0.1687 | 0.6858 | 0.1233 | 0.1114 |
| 64.5 | Day 3 | 0.1150 | 0.5719 | 0.0997 | 0.0935 |
| 115.6 | Day 1 | 0.0534 | 0.8413 | 0.0416 | 0.0398 |
| 115.6 | Day 2 | 0.0409 | 0.8264 | 0.0342 | 0.0321 |
| 115.6 | Day 3 | 0.0183 | 0.8750 | 0.0162 | 0.0150 |
| 204.5 | Day 1 | 0.0000 | 1.0000 | 0.0000 | -0.0002 |
| 204.5 | Day 2 | 0.0000 | 1.0000 | 0.0000 | -0.0002 |
| 204.5 | Day 3 | 0.0000 | 1.0000 | 0.0000 | -0.0001 |

Machine-readable results are in
`data/manifests/phase1f/2019-JJAS/raw_gefs_control_baseline.json`. Any future
model comparison must recompute raw and post-processed results on the same
declared held-out case intersection rather than comparing this table to v1.

## Phase 2B common-population replay

The raw c00 baseline was recomputed once in the Phase 2B test evaluation on
the exact dynamically constructed common population and identical valid-cell
mask used by M1–M4. See `docs/60_2019_FINAL_TEST_REPORT.md` and
`data/manifests/phase2b/2019_final_results.json`. Its overall result is the
M0 row there; it is not a post-hoc comparison to a different eligibility
denominator. The historical product-level tables above are retained unchanged.
