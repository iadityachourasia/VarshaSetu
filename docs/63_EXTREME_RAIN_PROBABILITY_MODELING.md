# Phase 2C Extreme-Rain Probability Modeling

## Frozen scientific roles and provenance

The Phase 2B M2 Global XGBoost (`global_xgboost.json`, SHA-256
`c0b4441071045bb9d1206a7c69645632efe2250adfc8a5464a6f69370d4c1797`)
is the unchanged primary deterministic forecast. Its 2019 RMSE is 17.8487 mm
versus 19.7735 mm for Raw GEFS. This phase did not retrain M0–M4.

2017 trains the two distinct binary event models. Within 2018, the first 60%
of chronologically ordered forecast initializations fit calibration and provide
XGBoost early stopping; the remaining 40% select model/calibration by Brier
score and a categorical decision cutoff by CSI. All leads of an initialization
remain together. The 2019 values were accessed only after writing the
probability-selection freeze, SHA-256
`a1fdbb2aa1bccfad8c7ee8691e06c67d8624055497a137390381907f332c9c4a`.
No post-2019 model/calibration/threshold tuning was done.
The 2018 split comprised 73 calibration and 49 selection initializations,
corresponding to 154 and 97 product cases. The original `2018_validation.json`
misnames those two case counts as `*_initialization_count`; the append-only
metric-semantic supersession records the true values. The split and all scores
were computed using initialization-grouped membership, so no product from an
initialization crossed folds.

The first post-freeze evaluation invocation loaded the 2019 cache but stopped
at a target-axis dimension assertion before computing/reporting any held-out
scores: valid cells did not cover every target latitude/longitude. The code
was corrected to read the authoritative 49×49 Zarr coordinate axes, and the
single completed held-out evaluation then ran. This was a shape-handling fix,
not a model or threshold change; no partial 2019 result artifact was kept.

The inclusive 24-hour IMD-reference labels are heavy `R >= 64.5 mm` and
very-heavy `R >= 115.6 mm`. There is no synthetic resampling. The 26 ordered
forecast-time inputs are the 22 frozen Phase 2B features, frozen M2 corrected
rainfall, and the three Phase 2A forecast-only regime probabilities. IMD
rainfall is used only as the target/reference. The Phase 2A regime probabilities
are prototype classifier outputs, not verified meteorological truth.

P1 is class-balanced logistic regression serialized as safe JSON. P2 is
class-weighted native-JSON XGBoost binary classification, with at most 180
histogram trees and 2018-only early stopping. Identity, sigmoid, and isotonic
calibration were compared on the held-out 2018 selection fold. Isotonic was
eligible only when the 2018 calibration fold had at least 100 positive cells;
this is a pragmatic minimum, not proof of stable tail calibration. P0 is the
fraction of all five valid GEFS members exceeding the same threshold, evaluated
only on the `FULL_ENSEMBLE_ELIGIBLE` subset, never imputed for control-only cases.
The 2017 event frequency is the frozen climatology for Brier Skill Score (BSS).

| Target | 2017 positive / cells | 2018 calibration positives | 2018 independent selection positives | Selected model/calibration | Frozen probability cutoff |
|---|---:|---:|---:|---|---:|
| Heavy | 4,750 / 335,658 | 5,012 | 1,417 | XGBoost + sigmoid | 0.30 |
| Very heavy | 865 / 335,658 | 1,289 | 351 | Logistic + isotonic | 0.05 |

The cutoff applies to probability, not rainfall. The original metric JSONs
inadvertently called that field `categorical.threshold_mm_24h`; the append-only
`metric_semantics_supersession.json` corrects the label without changing any
score, freeze, or 2019 evaluation. Current API responses use
`categorical.decision_threshold_probability`.

## Independent 2018 selection-fold verification

Both targets have 126,197 selection cells. The table is out-of-sample for
calibration and model selection, not an independent year from model tuning.

| Target | Events | Brier | BSS vs 2017 climatology | PR AUC | ROC AUC |
|---|---:|---:|---:|---:|---:|
| Heavy | 1,417 | 0.010665 | 0.04009 | 0.12886 | 0.91739 |
| Very heavy | 351 | 0.002746 | 0.01003 | 0.04286 | 0.94963 |

On the separate 2018 full-ensemble intersection (176 cases, 228,976 cells),
P0 Brier was 0.019002 heavy / 0.004904 very heavy; the selected models on
exactly those cells scored 0.015187 / 0.004103. P0 is not the control-only
comparison baseline and was not used to change the frozen selections.

## One-time 2019 held-out verification

The common Phase 2B control/model population contains 255 cases and 331,755
valid cells. BSS references 2017 training climatology, not a test-year fit.

| Target | Observed events | Brier | BSS | PR AUC | ROC AUC | POD | FAR | CSI | ETS |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Heavy | 9,633 | 0.022488 | 0.208570 | 0.337607 | 0.911075 | 0.353680 | 0.568952 | 0.241118 | 0.228589 |
| Very heavy | 2,918 | 0.007940 | 0.093259 | 0.154589 | 0.918279 | 0.582248 | 0.872332 | 0.116955 | 0.109782 |

For P0 on the 173 full-ensemble common cases (225,073 valid cells), heavy
Brier is 0.028850 versus 0.023405 for the selected classifier on those same
cells; very-heavy Brier is 0.009346 versus 0.008174. P0 is an uncalibrated,
coarse 0.2-step five-member fraction. Its log loss is particularly sensitive
to zero/one probabilities and is not a calibrated score.

The 2019 ten-bin reliability arrays (counts, predicted means, observed
frequencies), log loss, event counts, and explicit undefined reasons are in
`data/manifests/phase2c/2019_final_results.json`. Heavy's largest bin has
308,001 cells, mean p=0.01441, event rate=0.01153; the 0.3–0.4 bin has
3,854 cells, mean p=0.34731, event rate=0.34691. Very-heavy's 0–0.1 bin has
326,292 cells, mean p=0.00401, event rate=0.00533; its 0.1–0.2 bin has
5,266 cells, mean p=0.14610, event rate=0.21534. Thus reliability is mixed,
especially for very-heavy and small upper bins; calibration is evaluated,
not asserted perfect. The very-heavy 2019 FAR of 0.872 remains a major warning.

All reported probabilities lie in [0,1]. The implementation uses no
pickle/joblib authority and never loads the quarantined GOA CSV model path.
