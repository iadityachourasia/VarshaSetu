# Experiment Record Template

Create one immutable record per meaningful experiment.

Suggested location:

```text
experiments/<experiment_id>/metadata.yaml
experiments/<experiment_id>/metrics.json
experiments/<experiment_id>/notes.md
```

## Metadata template

```yaml
experiment_id: EXP_YYYYMMDD_001
title:
created_at_utc:
git_commit:

objective:
hypothesis:

data:
  manifest_id:
  forecast_source:
  observation_source:
  region:
  train_period:
  validation_period:
  test_period:
  spatial_resolution:
  temporal_resolution:
  accumulation_hours:

features:
  registry_version:
  count:
  list_hash:

regime:
  methodology_version:
  classes_or_heads:

models:
  - name:
    estimator:
    hyperparameters:
    artifact:
    package_versions:

thresholds:
  heavy:
    value_mm:
    accumulation_hours:
  very_heavy:
    value_mm:
    accumulation_hours:

random_seed:

calibration:
  method:
  fit_period:

verification:
  metrics:
    - RMSE
    - ETS
    - CSI
    - POD
    - FAR
    - FSS

warnings:
  - ...

result_summary:
  raw_nwp_rmse:
  mos_rmse:
  global_ml_rmse:
  regime_ml_rmse:
  soft_moe_rmse:
```

## Notes template

### Question
What scientific question does this experiment test?

### Change from previous experiment
What single major variable changed?

### Result
Summarize without exaggeration.

### Failure cases
List important degradations.

### Decision
Keep / reject / investigate.

## Rule

Do not reuse an experiment ID after data/code changes.
