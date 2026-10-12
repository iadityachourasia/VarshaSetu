# Versioned 2026 one-shot score gate — 9 October 2026

## Decision

The frozen v1 scorer and its score protocol remain byte-for-byte unchanged.
The sealed `2026_track_b_score_gate_protocol_v2.json` (SHA-256
`b7fd05760ff5c2e5c8289235613318dad23a7438745335b60e87e59765bbff8a`)
pins the v1 protocol/scorer, the supplemental annual/version auditor, and a
new entrypoint, `scripts/score_2026_with_clearance_gate_v2.py`. The v2
entrypoint is the governed path for a future one-shot score. Directly running
the v1 `--score` entrypoint would bypass this stronger source review and must
not be used for a future independent-test claim.

Before delegating to the unchanged v1 algorithm, v2 requires the
supplemental source audit to report `READY_FOR_MANUAL_SOURCE_REVIEW` and a
separately sealed, named, dated human approval tied to the exact hashes of
both source clearances and the annual IMD file. It also refuses a second
score or an existing v2 companion receipt. After a successful future score,
it writes a one-shot companion receipt binding the source review to the v1
score hash. A crash after v1 writes its score but before the companion is
complete leaves **no evidenced v2-gated result** and requires manual audit;
automatic rerun is prohibited.

The code validates structure, hashes and declared decisions. It cannot
authenticate a provider statement, establish a licence from a checkbox, or
decide predictor comparability. The named reviewer must inspect the actual
IMD rights/source evidence, actual GEFS deployment and 2023 patch evidence,
and the seven selected predictor reviews. They must also confirm that the
actual cycle transition is compatible with the v1 scorer's frozen
15 June 2026 12 UTC version partition; if it differs, the v1 score
stratification needs a new prespecified version before pairing. A reviewer
must not create approval merely because the structural checks pass.

## Executed checks

- Focused clearance/gate tests: **9 passed**, exit 0.
- Full backend suite using the socket-enabled Windows setup:
  `python -m pytest backend/tests -q
  --basetemp=data/pytest-score-gate-v2-final-20261009 -p no:cacheprovider
  --durations=5`: **857 passed**, exit 0, 282.37 s. The longest source-ledger
  test took 155.65 s; the run was allowed to finish.
- `scripts/probe_2026_source_clearance.py --check`: exit 0,
  `OPEN_NO_CLEARANCE`, the same four external blockers.
- Supplemental audit and both v1/v2 `--preflight` calls: exit 0 and
  `BLOCKED_BEFORE_OBSERVATION_READ`. V2 lists missing IMD clearance, GEFS
  clearance and human approval. Its 213 forecast leads remain sealed.
- Sealed protocol and pinned v1/v2 code hashes rechecked. The complete
  annual IMD file, both clearance manifests, review approval and score
  artifacts are absent. No 2026 rainfall values were opened and no score ran.
- Approximately 178.8 GiB was free on `C:` at closeout, above the 50 GiB
  project floor. No decode or training job was started.

## External dependency and next action

The four `docs/159` source issues remain **BLOCKED**: complete authorized
annual RF25 2026, actual cycle-specific 2026 GEFS deployment identity, exact
2023 training patch, and selected-predictor comparability. A qualified
reviewer must then inspect the source evidence and the frozen partition
before creating the approval receipt. The calendar year was still in
progress on 9 October 2026; the 125 provisional daily grids are not the
annual reference. The current product default remains regional M2. No
independent 2026 skill, public warning, or national correction promotion is
claimed.
