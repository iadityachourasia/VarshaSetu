# Authoritative Phase 2B Rainfall Modeling

## Scope and status

Executed bounded retrospective model comparison using only canonical v2 Phase 1F/2A Zarr and frozen manifests. This does not authorize API exposure, operational forecasts, FSS, district aggregation, new acquisition, or further scientific phases. Model-selection freeze SHA-256: `b9f0634e4db9de606406f7bfd77d23036740513047be557349aefefdd9ecf08d`.

## Frozen roles and populations

- 2017 JJAS: training only; common control + complete feature + valid reference set has 258 cases / 335,658 cells.
- 2018 JJAS: validation/model selection only; actual intersection has 251 cases / 326,551 cells. The published 251 control-eligible count is an upper-bound reference, not the final comparison population.
- 2019 JJAS: final untouched test; accessed only after the hash-verified model-selection freeze. Its exact intersection is in the final report.

Cases are selected by the actual intersection of `CONTROL_MODEL_ELIGIBLE`, `REGIME_ELIGIBLE` (all complete atmosphere bundle inputs), paired observation availability, valid c00 inputs, and complete finite feature rows. All M0–M4 use the exact same case IDs and cell mask per year.

## Feature contract

Features, in fixed order: `raw_c00_rain_mm, forecast_u850, forecast_v850, forecast_q700, forecast_z500, forecast_mslp, forecast_pwat, pwat_area_mean, q700_area_mean, u850_area_mean, v850_area_mean, wind_speed_area_mean, moisture_transport_area_mean, mslp_area_mean, mslp_minimum, mslp_range, z500_area_mean, relative_vorticity_area_mean, relative_vorticity_p90, latitude_deg, longitude_deg, lead_hours`. M0 is raw c00 rainfall; M1 Ridge MOS and M2 global XGBoost use this non-regime feature set. M2 explicitly excludes predicted regime class, probabilities, and pseudo-label identifiers. M3/M4 use the same selected global model and the same three 2017 pseudo-label specialists; M3 routes by forecast-only classifier argmax, M4 blends experts by forecast-only probabilities. A specialist requires at least 30 independent training cases and at least 20,000 valid cells; otherwise its gate uses the frozen global fallback.

The six atmospheric fields are bilinearly interpolated from the validated 0.5-degree context grid to 0.25-degree target-cell centers. This aligns grids and does not create meteorological source resolution. The interpolation semantics are identical across all years. Derived 12-feature regime vectors are recomputed and verified against Phase 2A case artifacts for 2017/2018; 2019 uses the frozen classifier after the holdout gate.

## Bounded model selection

Ridge alpha candidates: `(0.1, 1.0, 10.0, 100.0)`. XGBoost target candidates: `('direct', 'tweedie', 'log1p')`; fixed histogram tree settings, depth 6, learning rate .05, 350-round cap, 35-round early stopping, seed 26080, and 12 CPU worker threads. Minimum 2018 common-population RMSE selects within each model family. No exhaustive search was performed. The 2019 set was never used to choose features, preprocessing, target transform, hyperparameters, model families, or model artifact.

CPU/CUDA benchmark selected `cpu`. Benchmark equivalence: `{"cuda_repeatability": {"maximum_absolute_prediction_delta": 0.0, "prediction_correlation": 0.9999999999999998, "seconds": 0.32721489999994446, "stable": true, "status": "ok"}, "maximum_absolute_csi_drift": 0.012312231129081558, "passed": false, "prediction_correlation": 0.9882553531888851, "relative_rmse_drift": 0.000895546210386857}`; details and resource context: `data/manifests/phase2b/cpu_gpu_benchmark.json`.

## Artifact safety and limitations

Feature matrices are cached as hash-addressed safe NumPy arrays with per-array SHA-256 and source-tree/code/feature-schema lineage. Ridge is safe JSON; XGBoost uses native JSON. `allow_pickle=False`; no joblib/pickle is authoritative. These are retrospective prototype results against IMD gridded reference, not calibrated event probabilities or operational NWP readiness. FSS is not computed in this phase.
