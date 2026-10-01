# Phase 6F (P0-6): SIH26080 Requirement Coverage and Governance Refresh

Date: 2026-10-01. Status: implemented. No scientific computation, training or data acquisition was performed.

## Problem

Judges and maintainers had no single place showing which SIH26080 requirements exist, which are partial, and which do not exist yet. Governance
documents (`docs/22`, `23`, `14`, `16`, `08`, `03`, `PRODUCT.md`, `00_INDEX`, `JUDGE_QA`) still described the Phase 0-1 state of the quarantined
legacy CSV prototype.

## What was built

| Item | Location |
|---|---|
| Machine-readable coverage manifest (30 rows; status vocabulary IMPLEMENTED / PARTIAL / PLANNED) | `backend/app/evidence_data/phase6/ps_coverage.json` |
| Read-only endpoint; every figure is resolved server-side from hash-verified evidence by JSON pointer, never typed | `GET /api/science/evidence/ps-coverage` |
| Frontend page and navigation entry "SIH26080 Compliance" | `/compliance`, `frontend-v2/src/components/compliance/ps-coverage.tsx` |
| Generated status block in `docs/22` (no hand-typed status) | `scripts/build_ps_traceability_doc.py` |
| Backend tests (12) | `backend/tests/test_ps_coverage.py` |
| Frontend schema test and Playwright spec (5) | `frontend-v2/src/lib/api/evidence.test.ts`, `frontend-v2/tests/e2e/compliance.spec.ts` |

## Honesty rules enforced by tests

- Every official requirement PS-R01 to PS-R14 is covered by at least one row.
- Coastal/orographic, western-disturbance, independent regime validation, live inference, synoptic overlays and all-India domain are PLANNED, carry no
  evidence facts, and state their gap. The regime-classifier and improvement-versus-Raw rows are PARTIAL.
- IMPLEMENTED rows must link to a real page route and a real evidence document; PARTIAL/PLANNED rows must state the gap.
- No number may be typed into status text; figures exist only as evidence-resolved facts. Facts from the consumed 2019 and 2025 years carry the
  post-hoc evidence label.
- An unresolvable pointer, a planned row with a fact, or a tampered underlying evidence file makes the endpoint return 503 `SCIENCE_INTEGRITY_FAILURE`.
- `docs/22` fails its test if it drifts from the manifest.

Resulting official-requirement status (generated in `docs/22`): PS-R03 (regime classification) and PS-R05 (improvement versus Raw) are PARTIAL;
the other twelve are IMPLEMENTED. IMPLEMENTED means the capability exists and is evidence-backed, not that every forecast result is better than Raw.

## Governance documents refreshed

| Document | Change |
|---|---|
| `docs/22` | Generated current-status block; Phase 0-1 audit kept as a labelled historical section |
| `docs/23` | Checkboxes re-checked against the repository; ticked items cite evidence; unticked items annotated |
| `docs/14` | Banner: the original gates concern the legacy CSV path and stay open; not a status of the canonical track |
| `docs/16` | R03, R05, R06, R07, R09, R10 updated; R30-R34 added (IMD redistribution, 2024 validation reuse, non-replicating regime-aware gain, evidence line endings, many-district chance) |
| `docs/08`, `docs/03` | Banners pointing to the canonical regime method and current implementation documents |
| `docs/00_INDEX.md` | Phase 0-1 blocker chain replaced by current priorities |
| `PRODUCT.md` | Removed the "untouched 2019 test" wording; describes both tracks and the new pages |
| `docs/presentation/JUDGE_QA.md` | Removed the claim that elevation/coastline distance are current predictors; no current model uses static geography |

## Verification run (2026-10-01)

| Check | Result |
|---|---|
| Backend full suite (`pytest backend/tests`, `--basetemp` in a writable directory) | 298 passed |
| Frontend `tsc --noEmit`, `eslint`, `next build` | clean |
| Vitest | 108 passed |
| Playwright full regression, one worker, against `next start` | 86 passed, 1 failed |

The single failure is `demo-flow.spec.ts:4`. It is the known failure that predates this work (confirmed earlier on the original code: the Overview page
shows the same figure twice and the strict text locator matches both). It is not fixed here.

Environment note: on this Windows machine the default pytest temp directory raises a permission error for a few tests; passing `--basetemp` to a
writable folder makes them run, and the full suite passes.

## Limitations

- The coverage manifest is hand-authored for statuses and links; only the numbers and the docs/22 table are generated. A reviewer must change a status
  deliberately, and the tests only catch structural dishonesty (planned rows with facts, missing links), not a wrongly chosen status.
- The page reads hash-verified evidence for Track B 2024/2025 and Track A 2018/2019 only.

## Next

P0-7: coastal/orographic regime protocol (documentation only), then stop for approval before any data acquisition or training.
