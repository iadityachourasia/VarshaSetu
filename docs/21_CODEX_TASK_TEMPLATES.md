# Codex Task Templates

Use these as issue-style prompts.

---

# Template A — Phase 0 task

```text
Read AGENTS.md and docs/00_INDEX.md first.

Task: <specific task>

Problem:
<what is broken and why it matters scientifically/technically>

Evidence:
<file paths / current behavior>

Required behavior:
<precise desired state>

Constraints:
- Do not redesign unrelated components.
- Do not add fake/demo scientific outputs.
- Preserve existing working baselines.
- Update tests.
- Update relevant docs if semantics change.

Acceptance criteria:
- <check 1>
- <check 2>

Verification:
Run:
<commands>

At the end report:
- files changed
- tests run/results
- unresolved risks
```

---

# Template B — Data provenance task

```text
Read:
- AGENTS.md
- docs/06_DATA_PROVENANCE.md
- docs/07_DATA_SCHEMA.md
- docs/11_SCIENTIFIC_CONSTRAINTS.md

Audit <dataset/fields>.

For every field identify:
- source
- forecast/observation/reanalysis/static
- initialization/valid time
- lead
- units
- accumulation
- whether available at forecast issue time

Do not change the model until unsafe/unverified dynamic predictors are identified.

Output:
1. machine-readable manifest
2. human-readable provenance update
3. proposed code changes
4. tests
```

---

# Template C — Soft Mixture-of-Experts

```text
Read:
AGENTS.md,
docs/08_REGIME_METHODOLOGY.md,
docs/09_ML_METHODOLOGY.md,
docs/10_VERIFICATION_PROTOCOL.md.

The existing regime-aware model uses hard argmax routing.

Implement a soft MoE baseline that:
- retains the same expert models initially,
- uses classifier probabilities as expert weights,
- produces nonnegative rainfall,
- is evaluated on the identical frozen split,
- does not alter the final test set,
- is compared with raw NWP, MOS, global ML, and hard routing.

Add tests for:
- expert weights sum to 1,
- deterministic inference,
- no negative rainfall,
- output shape.

Do not claim improvement until report metrics prove it.
```

---

# Template D — 24-hour heavy rainfall

Historical note: this template describes the legacy 6-hour-target transition.
The canonical Phase 1F–4J corpora already use 24-hour rainfall. Do not rerun
this template against frozen artifacts or treat its opening sentence as the
current scientific target; see `51_CANONICAL_PRECIPITATION_RECONSTRUCTION.md`
and `89_OPERATIONAL_FINAL_TEST_2025.md`.

```text
Read:
docs/07_DATA_SCHEMA.md,
docs/10_VERIFICATION_PROTOCOL.md,
docs/11_SCIENTIFIC_CONSTRAINTS.md.

Current target is 6-hour rainfall while heavy-rain categories are 24-hour categories.

Implement a scientifically explicit 24-hour accumulation product:
- define accumulation boundary/timezone,
- require complete constituent periods,
- document missing-period handling,
- preserve 6-hour product separately,
- train/evaluate heavy and very-heavy probabilities on the 24-hour target,
- report positive-event counts,
- never treat zero-event Brier score as evidence of strong calibration.

Add unit tests for accumulation windows and threshold labels.
```

---

# Template E — FSS

```text
Read:
docs/10_VERIFICATION_PROTOCOL.md
and the ECMWF FSS source in docs/20_SOURCE_REGISTER.md.

Implement FSS only after a genuine aligned 2-D forecast/observation grid exists.

Requirements:
- binary exceedance by threshold,
- neighbourhood fractions,
- configurable window sizes,
- correct edge handling documented,
- perfect-match test,
- mismatch test,
- displaced-event test,
- output by threshold and spatial scale.

Do not create a station-only pseudo-FSS.
```

---

# Template F — Frontend scientific cleanup

```text
Read:
docs/13_UI_DATA_CONTRACT.md.

Audit the requested page.

Remove:
- hardcoded scientific metrics,
- hand-authored probabilities,
- synthetic time series,
- unconnected scientific controls.

Every remaining scientific value must have a documented API field.

If backend value is unavailable, show:
"Not yet implemented"
instead of fake numbers.

Run npm build/lint and list every changed data source.
```

---

# Template G — Judge demo feature

```text
Read:
docs/17_DEMO_PROTOCOL.md,
docs/13_UI_DATA_CONTRACT.md,
docs/14_ACCEPTANCE_CRITERIA.md.

Implement only the requested demo slice.

It must show an actual held-out case and preserve:
forecast source,
init,
lead,
valid time,
accumulation,
raw forecast,
corrected forecast,
observation,
metric source.

No demo-only scientific fabrication.
```
