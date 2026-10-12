# Supplemental 2026 clearance-readiness audit — 9 October 2026

The frozen `2026_track_b_score_protocol_v1.json` correctly requires an
authorized annual IMD reference and GEFS version review, and its pinned
scorer still blocks because both clearance manifests are absent. A code
inspection found that the scorer's future preflight checks only a few manifest
fields: reference status, window, receipt and file hash; version status,
an evidence reference and transition time. By itself it does **not** test a
365-day annual axis, explicit rights decision, exact 2023 cycle versions,
the 2026 cycle-version map or the seven predictor reviews. A superficially
complete, hash-receipted clearance JSON could therefore make the v1 preflight
say `READY_TO_PAIR` without all four `docs/159` gates actually being proved.

The frozen scorer and protocol were **not edited**; its code hash still matches
the pinned SHA-256. The new
`scripts/audit_2026_clearance_readiness.py` is a supplemental, read-only
review gate. It checks:

1. Declared annual coverage from 1 January through 31 December 2026,
   365 daily records, the 03–03 UTC accumulation window, source receipt,
   SHA-256 and explicit local-use/redistribution decision.
2. The NetCDF `TIME` axis and rainfall *shape* (365×129×135), without
   opening rainfall values, plus a streamed file hash when a file exists.
3. Actual 2026 transition time with authoritative evidence, a version for
   **every** frozen 2026 cycle, a version for every admitted 2023 training
   cycle, and source evidence for the 2023 patch.
4. A separate documented accept/reject decision with evidence and rationale
   for rainfall, U850, V850, Q700, Z500, MSLP and PWAT.

The validator checks **structure and consistency**. It cannot authenticate
that a URL describes the deployed executable, establish rights from an
unsupported checkbox, or make a scientific comparability decision. A
qualified human source review remains necessary. A future actual scoring run
must use a **new, disclosed, hash-pinned score protocol/entrypoint** that
enforces this supplemental review; merely running the v1 scorer after adding
two minimally shaped files would be inadequate. Do not rewrite the frozen v1
protocol or treat this audit as a clearance manifest.

**9 October follow-up:** `174_2026_VERSIONED_SCORE_GATE_V2_20261009.md`
records that the required versioned entrypoint and sealed protocol now exist.
They are blocked by the same external source evidence and missing human
review. The statement above records the requirement at the time this audit
was written; the v1 scorer remains unchanged.

On 9 October the new audit and the frozen v1 preflight both return
`BLOCKED_BEFORE_OBSERVATION_READ` because the two clearance manifests remain
absent. No 2026 rainfall value was opened, no score ran, and neither
clearance file was created. The available metadata diagnostic in `docs/172`
does not remove the external source requirements.

## Verification

- `python -m pytest backend/tests/test_2026_clearance_readiness.py -q
  --basetemp=data/pytest-clearance-readiness-20261009 -p no:cacheprovider`:
  **4 passed**, exit 0. Tests include incomplete terms/cycle/predictor
  refusal and a NetCDF stub that raises if rainfall values are accessed.
- `python scripts/audit_2026_clearance_readiness.py`: exit 0, blocked,
  observation values read false, score run false.
- `python scripts/score_2026_frozen_inference.py --preflight`: exit 0,
  blocked, 213 sealed cases, observation read false.
- A metadata-only look at the already-consumed local 2025 annual IMD file
  confirmed the expected `(365, 129, 135)` rainfall variable shape and
  129×135 axes; no 2026 file or rainfall value was opened.
- Frozen scorer SHA-256 still matches its v1 score protocol.
- First full backend run: **851 passed, 1 failed** in 110.66 s. The failure
  was `test_live_api.py::test_a_live_bundle_is_served_with_its_experimental_label_and_stale_flag`,
  outside the changed files; it passed immediately as an isolated test and
  in its 11-test file. This interrupted the first full-suite pass claim.
- Second full backend run with a fresh basetemp and retained local log:
  **852 passed**, exit 0 in 102.65 s. No live API code was changed during
  this investigation. The single first-run failure is recorded as an
  intermittent test result, not silently erased.
