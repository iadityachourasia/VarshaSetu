# 2018 Model Selection Report

## Frozen validation protocol

Validation population is the actual common intersection: 251 cases and 326,551 identical valid cells for every M0–M4 method. 251 is only the current control-eligible upper bound. 2017 was training-only; 2019 was not accessed before freeze `b9f0634e4db9de606406f7bfd77d23036740513047be557349aefefdd9ecf08d`. No 2018 fitting was performed.

## Selected candidates

- Ridge alpha: 100.0
- XGBoost target strategy: tweedie
- XGBoost rounds: 81
- Execution device: cpu

## Validation metrics

### M0_RAW_GEFS

326,551 cells; RMSE 15.5749, MAE 6.7349, bias +0.4208 mm. Heavy events 6,429; POD/FAR/CSI/ETS 0.0991/0.7575/0.0757/0.0699. Very-heavy events 1,640; POD/FAR/CSI/ETS 0.0299/0.8345/0.0260/0.0252.


Per lead and forecast-only classifier regime metrics are retained in `data/manifests/phase2b/model_selection_freeze.json`.

### M1_LINEAR_RIDGE_MOS

326,551 cells; RMSE 14.7470, MAE 7.3107, bias +1.1207 mm. Heavy events 6,429; POD/FAR/CSI/ETS 0.0230/0.6263/0.0222/0.0210. Very-heavy events 1,640; POD/FAR/CSI/ETS 0.0055/0.7097/0.0054/0.0053.


Per lead and forecast-only classifier regime metrics are retained in `data/manifests/phase2b/model_selection_freeze.json`.

### M2_GLOBAL_XGBOOST

326,551 cells; RMSE 14.0296, MAE 6.0366, bias -0.6485 mm. Heavy events 6,429; POD/FAR/CSI/ETS 0.0414/0.6371/0.0386/0.0366. Very-heavy events 1,640; POD/FAR/CSI/ETS 0.0000/null/0.0000/0.0000.


FAR at 115.6 mm/24 h is null (no forecast events; 326,551 valid cells, 1,640 observed events, 0 forecast events).

Per lead and forecast-only classifier regime metrics are retained in `data/manifests/phase2b/model_selection_freeze.json`.

### M3_HARD_REGIME_XGBOOST

326,551 cells; RMSE 14.2744, MAE 5.9781, bias -1.0687 mm. Heavy events 6,429; POD/FAR/CSI/ETS 0.0168/0.5556/0.0165/0.0157. Very-heavy events 1,640; POD/FAR/CSI/ETS 0.0000/null/0.0000/0.0000.


FAR at 115.6 mm/24 h is null (no forecast events; 326,551 valid cells, 1,640 observed events, 0 forecast events).

Per lead and forecast-only classifier regime metrics are retained in `data/manifests/phase2b/model_selection_freeze.json`.

### M4_SOFT_REGIME_MOE

326,551 cells; RMSE 14.2396, MAE 5.9615, bias -1.0582 mm. Heavy events 6,429; POD/FAR/CSI/ETS 0.0166/0.5597/0.0163/0.0156. Very-heavy events 1,640; POD/FAR/CSI/ETS 0.0000/null/0.0000/0.0000.


FAR at 115.6 mm/24 h is null (no forecast events; 326,551 valid cells, 1,640 observed events, 0 forecast events).

Per lead and forecast-only classifier regime metrics are retained in `data/manifests/phase2b/model_selection_freeze.json`.

## Target-transform candidates

- `direct`: 326,551 cells; RMSE 14.0411, MAE 6.7467, bias +0.7830 mm. Heavy events 6,429; POD/FAR/CSI/ETS 0.0709/0.6187/0.0636/0.0605. Very-heavy events 1,640; POD/FAR/CSI/ETS 0.0000/null/0.0000/0.0000.; selected best iteration 55.
- `log1p`: 326,551 cells; RMSE 14.9148, MAE 5.4796, bias -3.1271 mm. Heavy events 6,429; POD/FAR/CSI/ETS 0.0000/null/0.0000/0.0000. Very-heavy events 1,640; POD/FAR/CSI/ETS 0.0000/null/0.0000/0.0000.; selected best iteration 71.
- `tweedie`: 326,551 cells; RMSE 14.0296, MAE 6.0366, bias -0.6485 mm. Heavy events 6,429; POD/FAR/CSI/ETS 0.0414/0.6371/0.0386/0.0366. Very-heavy events 1,640; POD/FAR/CSI/ETS 0.0000/null/0.0000/0.0000.; selected best iteration 80.

## CPU/GPU check

The representative 50,000-row / 20,000-row validation benchmark selected `cpu`. CPU elapsed 0.22963100000015402 s; CUDA first-run elapsed 28.589846899999884 s; the repeat CUDA pass elapsed 0.32721489999994446 s. The first CUDA run includes device/context initialization, so the warmed repeat is also reported. CUDA fit and repeat completed without a CUDA exception or allocation failure; repeated CUDA predictions were stable=True with maximum absolute delta 0.0 mm. The sampled GPU memory snapshot was `NVIDIA GeForce RTX 5050 Laptop GPU, 309, 8151, 61`; peak VRAM telemetry was not recorded, so this is not a peak-memory claim.

The pre-agreed scientific-equivalence gate was correlation >=0.999, relative RMSE drift <=0.001, and absolute heavy-CSI drift <=0.005. Observed correlation 0.9882553531888851, RMSE drift 0.000895546210386857, CSI drift 0.012312231129081558; overall equivalence passed=False. CUDA was therefore not selected even though no 20% speed threshold was imposed.

Undefined rare-event scores remain null with counts/reasons in machine-readable metrics. Validation is for selection only, not final performance claims.
