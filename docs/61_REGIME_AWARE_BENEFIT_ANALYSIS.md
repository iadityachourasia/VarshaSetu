# Regime-Aware Benefit Analysis

## Held-out answers

- VarshaSetu vs raw GEFS: improved overall RMSE from 19.7735 to 17.8487 mm (9.73% reduction), but did not improve heavy-rain CSI/ETS; raw CSI/ETS are 0.1204/0.1107, with M0_RAW_GEFS/M0_RAW_GEFS best for CSI/ETS.
- Global ML vs MOS (RMSE): improved; M2 17.8487, M1 18.8020 mm.
- Hard regime vs global ML (RMSE): did not improve; M3 18.4858, M2 17.8487 mm.
- Soft MoE vs hard/global: M4 reduced RMSE slightly versus M3 (0.0459 mm) but remained worse than M2 by 0.5911 mm; heavy CSI/ETS were M4 0.0077/0.0072, M3 0.0088/0.0082, and M2 0.0485/0.0462.
- Best RMSE model: M2_GLOBAL_XGBOOST.
- heavy_64_5 best: CSI M0_RAW_GEFS; ETS M0_RAW_GEFS.
- very_heavy_115_6 best: CSI M0_RAW_GEFS; ETS M0_RAW_GEFS.

## Expert support and fallback

- ACTIVE_MONSOON: 99 training cases, 128,799 cells; trained
- BREAK_WEAK_MONSOON: 97 training cases, 126,197 cells; trained
- LOW_DEPRESSION_INFLUENCED: 62 training cases, 80,662 cells; trained

## Interpretation boundary

Regime-aware superiority is not presumed. The statements above are based only on the one-time 2019 held-out results after the prewritten model-choice freeze. This analysis uses prototype pseudo-labels and uncalibrated classifier probabilities; they are not authoritative meteorological labels or calibrated event probabilities. Event counts and uncertainty intervals must be considered alongside point scores. The 2019 result is not used for retuning.
