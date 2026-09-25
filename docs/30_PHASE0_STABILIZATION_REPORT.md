# Phase 0 Stabilization Report

Date: 2026-09-19

## Post-Phase 0 identity note

On 2026-09-19, the project adopted **VarshaSetu** as its canonical product name.
Historical identity references in this report are preserved as audit evidence and
describe the repository as it existed during Phase 0. The rename did not alter
the scientific controls, blockers, data, models, or verification evidence below.

## Outcome

The repository is safer and structurally reproducible, but Phase 0 is **not
scientifically complete**. The checked-in dataset can now be located and verified
byte-for-byte from a clean checkout. Scientific training and inference are
deliberately blocked because the evidence needed to establish dataset lineage,
forecast-time causality, regime labels, and correct accumulation semantics is not
present.

No new forecasting feature was added.

## Controls implemented

- Portable repository-relative data path, with paired environment overrides.
- Checked-in JSON manifest validating SHA-256, row count, and ordered schema.
- Exact separation between 26 source columns and the derived `datetime` column.
- Configuration-driven split tests for train 2020–2023, validation 2024, test 2025.
- Semantic feature registry; unknown contemporaneous atmospheric fields are no
  longer used by `prepare_features`.
- Operational feature validation rejects unverified forecast provenance.
- Readiness gate blocks training, artifact loading, verification endpoints,
  replay, probabilities, and sandbox inference.
- Legacy reports/models retained but quarantined and labeled.
- Fake XGBoost-2000 run removed from executable experiment generation.
- Missing XGBoost dependency added; backend dependencies pinned.
- Reachable frontend reduced to API-derived readiness/provenance status with no
  forecast, metric, probability, authentication, notification, or alert claims.
- Future experiment reports now have code-version state, data hash, split,
  hyperparameters, feature registry, thresholds/accumulation, seed, timestamp,
  and package-version fields.

## Documentation–code discrepancies found

The following list records every discrepancy found during this pass, including
items already named in the audit and additional live-code findings.

1. The workspace is not a Git checkout, although experiment metadata requires a
   git commit. Future reports record `unavailable:not-a-git-checkout` until fixed.
2. `SOURCE_CSV_PATH` was a developer-specific Windows Downloads path.
3. The checked-in CSV hash is `7b01…b241`; the report claims `30e4…d1b6`.
4. The checked-in CSV has 26 source columns; the report source had 27, including
   `regime_id`, and then counted generated `datetime` as column 28.
5. The report path and filename identify absent `GOA_DATA (1).csv`.
6. `regime_id` and its generation methodology are absent, so regime training and
   classifier accuracy cannot be reproduced.
7. The tests expected the obsolete 2020–2022/2023/2024/2025 split while config
   uses 2020–2023/2024/2025/no unseen split.
8. Test data hashes and column counts referred to the absent report dataset.
9. XGBoost was imported but not declared in backend requirements.
10. The “XGBoost 2000” path instantiated the same 1000-tree configuration as the
    1000-tree run, producing identical saved metrics.
11. The probability model's non-DataFrame path referenced `X_vals` before it was
    assigned.
12. The old evaluation script looked for a nonexistent `split_metadata.counts`
    shape and could still print the quarantined report directly.
13. Metrics API response keys were named `validation_2023` and `test_2024` while
    returning 2024 and 2025 content.
14. `/provenance` reported the legacy dataset rather than the configured file.
15. `/audit` returned handwritten PASS values instead of executed readiness
    results.
16. `/jury-defense` called the dataset official, claimed 100% source integrity,
    and overstated leakage prevention.
17. Forecast lookup silently substituted another station or the first time when
    the requested record was unavailable, contrary to API error semantics.
18. Training features included unknown-source valid-time temperature, dew point,
    humidity, pressure, cloud, wind, boundary-layer height, and TCWV.
19. Derived NWP-minus-unknown-field differences and terrain × unknown wind could
    therefore leak future/reference information.
20. Raw-NWP-prefixed columns still lack model, cycle, initialization, lead, and
    acquisition provenance; names alone do not validate them.
21. Dataset unit headers contain mojibake (`?C`, `kg/m?`, direction `?`) and are
    not authoritative unit metadata.
22. The 6-hour target was compared with 24-hour rainfall-category thresholds.
23. Alerts and rainfall categories applied those same incompatible thresholds.
24. Probability calibration was claimed as validated even though only a fitted
    calibrator and Brier values were shown; reliability was not assessed.
25. The test set had one legacy heavy event and zero very-heavy events, yet the UI
    presented calibration positively.
26. Regime probabilities were manually temperature-smoothed after classifier
    output and described as realistic calibration without evaluation.
27. Five-regime heuristic softmax scores were exposed as probability/confidence
    despite being handwritten and unvalidated.
28. The frontend synthesized a four-period trajectory by multiplying one record.
29. The frontend supplied realistic fallback rainfall and metric numbers when API
    values were missing.
30. The frontend supplied fallback regime probabilities (0.68/0.22/0.10).
31. A 97.63% classifier accuracy was hardcoded into UI text.
32. Mean-rainfall and meteorology cards used hardcoded values.
33. Analysis configuration, confidence interval, threshold, geography, and split
    controls changed local UI state but did not change scientific computation.
34. The model table labeled the regime model “PRIMARY OPERATIONAL” although the
    system has no operational forecast ingestion.
35. Historical-row lookup was labeled operational/live forecast.
36. Simulated authentication initialized the UI with a named user and role.
37. Notifications and alert logs were hardcoded.
38. Settings implied unit conversion and alert thresholds without connecting
    them to scientific outputs.
39. The footer displayed a fallback hash different from both the legacy report
    hash and current dataset hash.
40. The frontend claimed the calibrator used training/validation data, while the
    code calibrated by cross-validation within training data.
41. The ablation UI said models were trained on TRAIN & VALIDATION, while model
    fitting occurred on TRAIN and selection on VALIDATION.
42. The runtime branding alternated among DigiVarsha, Vrishti AI, and NEPHOS AI.
43. The root README was a documentation-pack README rather than runnable project
    setup and scientific status.
44. The frontend declared a lint command without ESLint dependencies or config.
45. Serialized artifacts lacked a package/version compatibility record.
46. Experiment reports omitted required code version, full hyperparameters,
    feature registry/list, accumulation metadata, seed, and package versions.
47. The saved regime-aware RMSE beat raw/global HGB but remained worse than MOS;
    some UI emphasis implied it was the preferred operational model.
48. Dataset audit date bounds used lexicographic `DD-MM-YYYY` string min/max
    rather than parsed timestamps; live audit now reports ISO chronological bounds.
49. Only one parsed local datetime existed and no canonical UTC timestamp was
    retained; the loader now derives both offset-aware local time and UTC time.
50. `npm ci` reports two locked transitive dependency vulnerabilities (one
    moderate in `esbuild`, one high aggregate entry in Vite including a Windows
    `server.fs.deny` bypass). The available remediation is Vite 8, a major
    upgrade, so it was not force-applied during this stabilization pass.
51. `MANIFEST.md` counted only the originally supplied documentation pack but
    could be mistaken for a live repository manifest; it is now labeled as an
    original-pack inventory.
52. `LAST_MODIFIED.txt` claimed “100% VERIFIED REAL DATA” despite the unresolved
    provenance and dataset mismatch. The original non-UTF-8 file is retained as
    `LAST_MODIFIED.LEGACY_UNTRUSTED.txt`; the current status file is explicit.
53. The FastAPI service still allows wildcard CORS with credentials instead of
    using an environment-scoped origin list. This is a production-security debt,
    not a scientific Phase 0 release blocker.
54. Most API endpoints still lack explicit Pydantic response models, despite the
    API contract recommending typed production responses. The live Phase 0
    status shape is typed on the frontend, but backend response-model work remains.

## Remaining blockers

1. Obtain and document the actual forecast and observation source lineage,
   licenses/terms, units, acquisition procedure, and immutable raw hashes.
2. Obtain or reproducibly generate scientifically defensible `regime_id` labels.
3. Add forecast initialization, valid time, lead, model/version, grid, and
   accumulation metadata.
4. Establish which forecast-like fields truly existed at issue time.
5. Build a correct 24-hour target before restoring heavy/very-heavy categories.
6. Re-train every artifact from the verified manifest and generate a new report.
7. Restore scientific frontend pages only after their API fields come from that
   reproducible report.

## Phase 0 gate status

- Passed: portable path, manifest/checksum identity, dependency declaration,
  split synchronization, fake experiment removal from executable code,
  frontend fail-closed integrity, and explicit training block.
- Pending: authoritative data identity, scientific provenance, reproducible
  regime labels, clean reproducible training, and a matching current report.

The Phase 0 release gate therefore remains **open/not passed**.

## Later canonical-corpus modeling status (2026-09-23)

The preceding findings and “next task” describe the legacy GOA CSV/API
stabilization snapshot and remain valid for that legacy path. Subsequent work
established separate Phase 1F/2A canonical-v2 GEFS/IMD corpora and an authorized
bounded Phase 2B 24-hour rainfall-model comparison; the selection, held-out
results, and artifacts are documented in `docs/58`–`docs/62`. Therefore the
older statement that no rainfall model/report can be regenerated is superseded
for that isolated canonical retrospective experiment only. Phase 2B does not
resolve the legacy dataset identity/feature timing blockers, independently
validate the prototype pseudo-regimes, provide calibrated event probabilities,
or complete FSS/district/operational requirements. The legacy readiness gate
still reports not-ready, and the scientific API remains fail-closed.

## Verification run on 2026-09-19

- Backend clean install into repository-local Python 3.12 `.venv`: succeeded.
- `python -m pip check`: passed; no broken requirements.
- `python -m pytest -q backend/tests`: **8 passed** in 3.60 seconds; one
  third-party Starlette/AnyIO deprecation warning.
- Python `compileall` over `backend/`: passed.
- Training readiness execution: correctly blocked with five scientific blockers;
  no model fitting or artifact overwrite occurred.
- Evaluation execution: correctly refused the mismatched legacy report.
- API smoke: `/api/health` returned degraded/stabilization mode,
  `/api/status` returned five blockers, and `/api/metrics/overall` returned 409.
- `npm ci`: succeeded (174 packages added; 175 audited in that run).
- `npm run build`: succeeded; TypeScript compiled, 1,471 modules transformed,
  production bundle generated in 1.54 seconds.
- Frontend source scan for removed hardcoded values/claims: no matches.
- `npm audit`: 2 vulnerabilities remain (1 moderate, 1 high); remediation
  requires a semver-major Vite upgrade and is deferred as an explicit risk.

## Next single highest-priority task

Acquire and register one legitimate paired forecast/reference dataset with an
authoritative source record, immutable raw hashes, units, initialization time,
valid time, lead, and accumulation window. Do not restore training or model UI
until that manifest passes the readiness gate; then define reproducible regime
labels without using target rainfall.
