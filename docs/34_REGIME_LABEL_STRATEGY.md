# Regime-Label Strategy

Status: Phase 1A design record. No `regime_id` was created by Phase 1A.

Phase 2A now implements a separate, explicitly provisional three-class
pseudo-label method. See `54_PROTOTYPE_REGIME_METHODOLOGY.md` for the exact
forecast-only diagnostics, 2017-only thresholds, limitations, and classifier.
Nothing in that successor retroactively validates legacy `regime_id` values or
makes the prototype classes official NCMRWF labels.

Phase 1C availability evidence (2026-09-19): the control-member U850, V850,
Q700, Z500, MSLP, and PWAT forecast fields were valid for all 31 July 2019
initializations at +24/+48/+72 (558/558 snapshots; 93/93 complete bundles) on
the planned 5–30°N, 55–95°E context domain. This supports feasibility of the
forecast-time predictor side only. It does not create or validate regime labels,
vorticity, thresholds, clustering, or regime skill. See
`39_PREDICTOR_AVAILABILITY_REPORT.md`.

## Principle

Monsoon state, synoptic driver, and spatial forcing overlap. The long-term target
is therefore a hierarchical/multi-label description, not an unexplained single
six-class target:

```text
Monsoon state:    active | break | neutral
Synoptic driver:  low/depression | western disturbance | other
Spatial forcing:  orographic (score/flag) | coastal (score/flag)
```

Every label must have a reproducible formula or reviewed annotation source,
input-manifest IDs, analysis time/window, version, and uncertainty. Target
rainfall must not be used to define a predictor-side regime that is then claimed
to improve that same target without an explicit diagnostic-only designation.

## Strategy comparison

### A. Documented rule-derived labels

Use circulation/moisture indices with published meteorological definitions: for
example large-scale monsoon wind/shear and pressure/circulation criteria. This is
interpretable and feasible for an MVP, but thresholds need literature support,
sensitivity analysis, and expert review. Rules should emit component labels and
uncertainty/unknown status, not force every day into a confident class.

### B. Circulation-pattern learning

Cluster or classify standardized multi-level circulation fields over the context
domain. Fit transformations and clusters on training years only, select cluster
count/stability without test rainfall, and attach meteorological interpretations
after composite analysis. This can capture continuous/overlapping patterns but
is sensitive to preprocessing and label permutation.

### C. NCMRWF weather-pattern adaptation

NCMRWF publicly demonstrates probabilistic weather-pattern concepts including
active/break monsoon and western disturbances. Direct adoption requires the
actual method, definitions, and sufficient data—not screenshots or pattern names.
If NCMRWF supplies its labels/method, map them through a versioned crosswalk and
validate against independent periods.

## MVP recommendation

1. Create a reviewed, versioned rule-based **diagnostic label generator** for
   broad monsoon state and synoptic-driver flags using separately identified
   reanalysis fields over the 5–30°N, 55–95°E context domain.
2. Keep reanalysis data and labels separate from raw forecast predictors.
3. Define equivalent forecast-field features so operational inference uses only
   fields available from the forecast initialization, never future reanalysis.
4. Preserve probabilities/scores and component flags; allow `unknown` and
   overlapping drivers.
5. Compare against a circulation-clustering sensitivity experiment after the
   source data exist. Split chronologically before fitting scalers/clusters.
6. Seek NCMRWF/meteorologist review and adapt official pattern information only
   when its methodology and access rights are clear.

## Leakage and reproducibility controls

- Label timestamps cannot exceed the target forecast initialization for an
  operational predictor. Retrospective labels derived from later analysis are
  targets for a regime classifier, not inference features.
- No observed rainfall, future humidity/temperature, or corrected rainfall may
  define an operational regime feature.
- All thresholds, spatial averages, seasons, pressure levels, anomaly baselines,
  and tie/unknown rules are configuration with version/hash.
- Climatologies and normalizers are fitted on training years only.
- Report per-component prevalence, overlap matrix, temporal persistence,
  stability, and expert/composite plausibility.
- `regime_id` remains absent until generator code, tests, source manifests, and
  methodology review exist. A missing label is not filled heuristically.

## Acceptance before model training

A regime label is eligible only when the label pipeline can regenerate an
identical artifact from clean inputs; source hashes, code/config version, and
chronological split are recorded; leakage tests pass; and documentation states
whether the label is reanalysis-derived, forecast-derived, or human-reviewed.
