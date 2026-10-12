# Probability v4 lineage corrigendum — 9 October 2026

## Correction to the frozen metadata interpretation

The v4 protocol's frozen field `observation_values_read_before_freeze: false`
is **too broad if read as a project-wide statement**. The v4 `prepare` call
itself opened no reference values. Before that freeze, however, the failed v3
run had already opened **2023** IMD reference values to train the same heads,
and the earlier national v1/v2 experiments had already consumed **2024** IMD
reference values. Their score hashes were dependencies of the v4 protocol.
Likewise, the v4 fit seal's `2024_reference_values_read: false` means that
**the v4 fit/prediction step** did not open the 2024 reference; it must not be
read as a claim that the project had never inspected 2024 rainfall.
The v4 `2025_2026_values_read: false` fields are likewise scoped to that
experiment: 2025 was consumed in earlier studies, while 2026 remains sealed.

The original protocol, fit seal and score are hash-frozen and were **not
edited**. This addendum corrects their interpretation. References in
`docs/176` to a freeze "before 2024 pairing" mean before **v4's own 2024
pairing**, not before all prior 2024 analyses. V4 is an adaptive,
already-consumed-2024 development comparison. Its reported date-bootstrap
intervals are descriptive for that population; they are not independent-year
confirmation or grounds for product promotion.

## Technical repair provenance

The v3 protocol (SHA-256
`94b413b11d5e6cce5588708098aeefd53f47016e8828c43cf10a57c4a01bfa3f`)
was frozen before the **v3** 2023 fit. Its execution failed at the Windows
XGBoost model-path reload, before any v3 2024 prediction or score. It left
two head models, `nested_oof_float32.npz` and `models.json` in the preserved
partial directory. No v3 fit seal or score exists.

An independent read-only audit compared the frozen v3 and v4 scientific
contracts and all four fitted artifacts. The model specifications, date-block
folds, calibration, coherence, cutoff rule, comparators and decision gate are
the same apart from arm naming. The heavy head, very-heavy head, nested OOF
array and `models.json` have **byte-identical SHA-256 hashes** in v3 partial
and v4 final. V4 used the XGBoost bytearray load path, then sealed 156 2024
forecasts before its separate 2024 score step. This supports a technical
rerun of the same predeclared scientific recipe. It does **not** make 2024
independent: v1/v2 outcomes motivated the nonlinear candidate.

The write-once audit is
`data/manifests/research_pilot/nationwide_probability_v4_lineage_audit_v1.json`,
SHA-256 `c9a1ef961bf85bc2528e4701ce09af34a3eb476df4cf4ae6989790ca6e97cbcc`.
`scripts/audit_nationwide_probability_v4_lineage.py check` reproduces the
protocol/score receipts, v3 failed state, equal scientific contracts and
identical fitted bytes without fitting or observation pairing. It explicitly
marks the global interpretation of the frozen flag **invalid**. Its own
`2026_observation_values_read_by_audit` is false.

## Scientific decision and prevention

The v4 consumed-2024 very-heavy Brier gate remains **failed** (`docs/176`).
Heavy-rain development improvement is not cherry-picked into the product.
The default remains regional M2; no national probability, district or public
warning promotion follows. Future protocols should use scoped fields such as
`reference_years_previously_consumed`, `reference_values_read_in_this_step`
and `predictions_sealed_before_this_step_score`, rather than an unqualified
`observation_values_read_before_freeze` boolean. This correction changes no
2026 source gate or independent-test seal.

## Verification and files

- The read-only source inspection found zero v3 2024 prediction files and no
  v3 fit/score seal; four v3/v4 fitted artifact hashes matched exactly.
- Focused contract tests: **2 passed**. The first direct audit invocation
  failed with a script import-path error; it wrote no artifact. The import
  path was fixed, then the audit write completed and its receipt checked.
- Full backend `python -m pytest backend/tests -q
  --basetemp=data/pytest-probability-lineage-full-20261009
  -p no:cacheprovider --durations=5` with the known Windows socket-enabled
  setup: **870 passed**, exit 0, 106.88 s.
- `python scripts/audit_nationwide_probability_v4_lineage.py check`:
  exit 0, corrigendum audit SHA-256 reproduced. The existing v4 integrity
  check also passed with 156 sealed predictions and the unchanged score hash.
- `python scripts/score_2026_with_clearance_gate_v2.py --preflight`:
  exit 0, `BLOCKED_BEFORE_OBSERVATION_READ`, 213 forecast cases, no score.
- `git diff --check`: exit 0, existing Windows line-ending notices only.
  Free C: space was 178.21 GiB, above the 50 GiB floor.

This increment adds `scripts/audit_nationwide_probability_v4_lineage.py`,
`backend/tests/test_nationwide_probability_v4_lineage.py`, the write-once
audit and this corrigendum. `docs/176` and `docs/00_INDEX.md` get prominent
correction pointers. No frozen scientific artifact was overwritten.
