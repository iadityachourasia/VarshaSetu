# Official Demo Cases (Phase 5B)

Selected directly from the checked-in static presentation bundle
(`frontend-v2/public/science/operational-v1/index.json` and Track A's
`data/manifests/phase2c/`), not fabricated. All figures below were read
from those files in this session.

## FEATURED HISTORICAL DEMO CASE — Track B (2025)

**`20250714_day2_24h`**

| Field | Value |
|---|---|
| Initialization | 2025-07-14 00:00 UTC |
| Lead | Day 2 (+27 -> +51 h) |
| Valid observation date | 2025-07-16 |
| Role | 2025 final test (sealed-then-consumed population) |
| Observed Heavy cells | 25 |
| Observed Very Heavy cells | 4 |
| Max observed rainfall | 173.78 mm / 24 h |
| Raw RMSE (this case) | 12.617 mm |
| M1 RMSE (this case) | 12.663 mm |
| M1 minus Raw | **+0.046 mm** (essentially neutral) |
| Dominant pseudo-regime | Active Monsoon (98.3%) |
| Models available | M0, M1, M2, M3, M4, IMD observed |
| Ensemble | Five-member eligible (in the matched 75-case subset) |
| Probability | Heavy + Very Heavy calibrated grids available |
| Atmosphere | All six frozen fields available |

### Why this case

- **Not selected because it is the best-performing case.** Its case-level
  M1-minus-Raw delta (+0.046 mm) is close to zero -- essentially neutral,
  neither a flattering outlier nor a worst-case cherry-pick in the other
  direction. Choosing a near-neutral case is deliberate: it does not invite
  the (false) impression that the selected model always wins.
- Complete enough to demonstrate every major UI feature in one case: both
  Heavy and Very Heavy IMD cells are actually present (so Extreme Rain's
  two thresholds both show real detected events, not an empty grid),
  five-member ensemble eligible, full probability and regime data, full
  atmosphere fields, and a real M0-M4 model ladder (2025 is not
  out-of-fold like 2023).
- A Day 2 lead is a reasonable middle ground for a walkthrough -- long
  enough to be a genuine forecast, short enough that the atmosphere fields
  and rainfall target are close in valid time.
- No attribution ambiguity: `deterministic_source_eligible`,
  `probability_source_eligible`, `regime_source_eligible`, and
  `ensemble_source_eligible` are all true for this case in the live case
  index (confirmed via the same static bundle used here, which is
  generated from the same frozen artifacts the live API serves).

## BACKUP DEMO CASE — Track B (2025)

**`20250903_day2_24h`**

| Field | Value |
|---|---|
| Initialization | 2025-09-03 00:00 UTC |
| Lead | Day 2 |
| Valid observation date | 2025-09-05 |
| Observed Heavy cells | 28 |
| Observed Very Heavy cells | 4 |
| Max observed rainfall | 165.92 mm / 24 h |
| Raw RMSE (this case) | 12.796 mm |
| M1 RMSE (this case) | 12.623 mm |
| M1 minus Raw | -0.173 mm (small improvement) |
| Dominant pseudo-regime | Break / Weak Monsoon (85.2%) |
| Models / ensemble / probability / atmosphere | Same full availability as the primary case |

### When to use it

Use this case only if the primary case has a map/network/rendering problem
during a live demo, or if a judge specifically asks to see a second event.
It is a different month (September vs. July) and a different dominant
pseudo-regime (Break/Weak vs. Active Monsoon) from the primary case, so
switching to it during a live Q&A also incidentally demonstrates that the
regime classifier does not always return the same class.

## Track A anchor case (2019) — already established, unchanged

**`20190802T000000Z_day3_24h`** -- already the code-level
`PRIMARY_DEMO_CASE_ID` in `frontend-v2/src/lib/demo.ts` and the case
validated by `scripts/demo/preflight-demo.ps1`'s existing "Official primary
demo case" check. Nothing about this case selection changed this phase;
it is documented here only so the official judge path (section 5) has one
place that names all three cases together. Its metrics belong to the 2019
GEFSv12 reforecast track and must never be pooled or directly compared
number-for-number with the 2025 operational-era case above (different GEFS
lineage, different population).

## Frontend constants

`frontend-v2/src/lib/demo.ts` already exports `PRIMARY_DEMO_CASE_ID` for
Track A. This phase adds the Track-B equivalents in the same file:
`OFFICIAL_OPERATIONAL_CASE_ID = "20250714_day2_24h"` and
`BACKUP_OPERATIONAL_CASE_ID = "20250903_day2_24h"`, used by the
`?demo=official` preset (see docs/99 and the Forecast page).
