# Phase 2A Regime Validation Report

## Protocol

The validated prototype uses the forecast-only feature registry and the
deterministic three-class pseudo-label procedure in
[`54_PROTOTYPE_REGIME_METHODOLOGY.md`](54_PROTOTYPE_REGIME_METHODOLOGY.md).
Thresholds, standardization, pseudo-labeling, and classifier fitting use the
2017 JJAS training cases only. The unchanged rule is applied to 2018 for
validation. The 2019 held-out test year was not accessed. There is one case
per initialization and lead (+24, +48, +72 h); there is no random row split.

The labels (`ACTIVE_MONSOON`, `BREAK_WEAK_MONSOON`,
`LOW_DEPRESSION_INFLUENCED`) are project-defined pseudo-labels, not
independently observed or authoritative meteorological truth. The scores
below measure how well the logistic model reproduces its own deterministic
pseudo-label definition on held-out-year forecast fields. They must not be
reported as meteorological regime accuracy or rainfall skill.

## Results

| Validation subset | Cases | Balanced accuracy | Macro F1 | Multiclass log loss | Multiclass Brier |
|---|---:|---:|---:|---:|---:|
| All leads | 366 | 0.9424 | 0.9415 | 0.1546 | 0.0881 |
| +24 h | 122 | 0.9341 | 0.9333 | 0.1624 | 0.0945 |
| +48 h | 122 | 0.9186 | 0.9162 | 0.1677 | 0.0984 |
| +72 h | 122 | 0.9753 | 0.9753 | 0.1337 | 0.0714 |

2017 pseudo-label counts were 137 active, 137 break/weak, and 92 low-
depression influenced. 2018 counts were 116, 137, and 113 respectively.
Confusion-matrix order is true rows and predicted columns, in the class order
above:

```text
2018 all leads: [[107, 3, 6], [4, 130, 3], [5, 0, 108]]
```

The class probability values are outputs of an uncalibrated logistic model;
log loss and Brier score are descriptive proper scores against the prototype
pseudo-labels, not evidence of calibration against truth. The 2018 reliability
table is retained as a diagnostic only.

## Artifacts and integrity

The deterministic artifacts are under `data/manifests/phase2a/regimes-v1/`.
`artifact_manifest.json` records byte sizes and SHA-256 for each output.
Principal references:

- `regime_classifier.safe.json`: `0761ba62e1aafbf12228f604d43a7b288d5beb3a7e7f01536a5df62b51b6a204`
- `pseudo_label_definition.json`: `fab7ebfd231eb9187d376b6b8a1f2361c1bceabb5ac83122811f4a9f02d75cac`
- `validation_metrics.json`: `a2bf889eaf6dc2a45f3f34c51e1d4caf7736751c2c47585ed238b9a79c036c93`
- `feature_registry.json`: `dd341008bf7b425c3f65a915be381f45b21a5649b2d97475758b5003c32d20da`

The model is JSON coefficient data, not a pickle. It records fixed feature
order, training-only scaling, seed, year roles, and
`held_out_test_accessed: false`. Artifact hashes establish byte integrity,
not scientific validity.

## Decision

The bounded forecast-only regime prototype is reproducible and passes its
2018 pseudo-label consistency validation. It is suitable for controlled
prototype inspection and qualitative case review only. It does not satisfy
the evidence needed to claim that regime-aware processing improves rainfall
forecast skill, and it does not authorize 2019 model development, rainfall
model training, API exposure, probabilistic calibration claims, or operational
use.
