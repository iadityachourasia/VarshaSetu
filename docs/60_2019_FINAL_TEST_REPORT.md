# 2019 Final Held-Out Test Report

## One-time evaluation gate

Model-choice manifest SHA-256 `b9f0634e4db9de606406f7bfd77d23036740513047be557349aefefdd9ecf08d` was written before the first 2019 Zarr value was read. It freezes feature order, preprocessing, model families, target transform, Ridge alpha, XGBoost settings, shared expert definition, specialist gates, and model artifact hashes. No post-test tuning was performed.

Phase 1F source Zarr tree SHA-256: `13fc4ea03f0724fc6a3c0506de1a30b1acb5be4f8dc803c9ea46bb2b5377cb9e`. Final common set is the exact intersection of `CONTROL_MODEL_ELIGIBLE`, `REGIME_ELIGIBLE`, complete forecast feature availability, and valid paired observation cells: 255 cases / 331,755 identical valid cells for each model. 255 is an upper bound, not the final comparison denominator.

## Results

### M0_RAW_GEFS

331,755 cells; RMSE 19.7735, MAE 9.3276, bias +0.5938 mm. Heavy events 9,633; POD/FAR/CSI/ETS 0.1618/0.6802/0.1204/0.1107. Very-heavy events 2,918; POD/FAR/CSI/ETS 0.0404/0.8412/0.0333/0.0315.


Per-lead, forecast-only predicted-regime and case-cluster bootstrap results are in `data/manifests/phase2b/2019_final_results.json`.

### M1_LINEAR_RIDGE_MOS

331,755 cells; RMSE 18.8020, MAE 9.3611, bias +0.3454 mm. Heavy events 9,633; POD/FAR/CSI/ETS 0.0401/0.6159/0.0377/0.0349. Very-heavy events 2,918; POD/FAR/CSI/ETS 0.0031/0.8800/0.0030/0.0028.


Per-lead, forecast-only predicted-regime and case-cluster bootstrap results are in `data/manifests/phase2b/2019_final_results.json`.

### M2_GLOBAL_XGBOOST

331,755 cells; RMSE 17.8487, MAE 8.0730, bias -1.5960 mm. Heavy events 9,633; POD/FAR/CSI/ETS 0.0503/0.4281/0.0485/0.0462. Very-heavy events 2,918; POD/FAR/CSI/ETS 0.0000/null/0.0000/0.0000.


FAR at 115.6 mm/24 h is null (no forecast events; 331,755 valid cells, 2,918 observed events, 0 forecast events).

Per-lead, forecast-only predicted-regime and case-cluster bootstrap results are in `data/manifests/phase2b/2019_final_results.json`.

### M3_HARD_REGIME_XGBOOST

331,755 cells; RMSE 18.4858, MAE 8.1121, bias -2.2960 mm. Heavy events 9,633; POD/FAR/CSI/ETS 0.0089/0.5825/0.0088/0.0082. Very-heavy events 2,918; POD/FAR/CSI/ETS 0.0000/null/0.0000/0.0000.


FAR at 115.6 mm/24 h is null (no forecast events; 331,755 valid cells, 2,918 observed events, 0 forecast events).

Per-lead, forecast-only predicted-regime and case-cluster bootstrap results are in `data/manifests/phase2b/2019_final_results.json`.

### M4_SOFT_REGIME_MOE

331,755 cells; RMSE 18.4398, MAE 8.0973, bias -2.2879 mm. Heavy events 9,633; POD/FAR/CSI/ETS 0.0078/0.5924/0.0077/0.0072. Very-heavy events 2,918; POD/FAR/CSI/ETS 0.0000/null/0.0000/0.0000.


FAR at 115.6 mm/24 h is null (no forecast events; 331,755 valid cells, 2,918 observed events, 0 forecast events).

Per-lead, forecast-only predicted-regime and case-cluster bootstrap results are in `data/manifests/phase2b/2019_final_results.json`.

## Interpretation

All claims below compare methods on the same exact final cases and per-cell masks. Heavy and very-heavy metrics use 64.5 and 115.6 mm/24 h. Any undefined metric is null, with sample and event counts and an explicit reason. This is a held-out retrospective prototype evaluation; the IMD gridded reference has the provenance and limitations documented in Phase 1F. No FSS is reported in this Phase 2B report because it was outside Phase 2B scope. FSS was added afterwards: `docs/64` covers Raw vs M2, and `docs/108` covers all five models with regime- and lead-stratified categorical scores (post-hoc; it reproduces this report's frozen numbers exactly). Track B equivalents are in `docs/106`.
