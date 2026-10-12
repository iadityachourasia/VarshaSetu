# Nested extreme-rain probability projection: development diagnostic

Date: 2026-10-07. The frozen Track B heavy (≥64.5 mm/24 h) and very-heavy
(≥115.6 mm/24 h) calibrators were fitted and selected separately. Some
forecast cells therefore violate `P(very heavy) ≤ P(heavy)`. The live worker
correctly refuses a whole lead when it encounters one. In the June 2024
partial-grid candidate this refused 35 of 90 leads.

**Follow-up:** `151_COHERENT_PARTIAL_GRID_REPLAY.md` now reports the completed
90-lead forecast replay and its later 2024 IMD-paired development score. The
"not yet replayed" decision below records the state of this earlier stage.

Before reading the 2024 labels for this analysis, we sealed
`coherent_probability_projection_protocol_v1.json` with a SHA-256 sidecar.
The only tested repair is the Euclidean projection: if the very-heavy
probability exceeds heavy, set both to their average; leave all other rows
unchanged. This is a deterministic adjustment of already frozen forecasts,
not refitting or probabilistic calibration. For a nested observed event pair,
the **sum** of the two squared probability errors cannot increase. Either
individual event's Brier score may still worsen.

The hash-verified Phase 4I selected 2024 probability arrays were paired with
the verified Phase 4G 2024 IMD labels in their original row order. The
protocol also prespecified separate reporting for the original calibration,
purged and model-selection blocks. The full reliability-bin counts and both
event Brier scores are in the immutable
`coherent_probability_projection_score_v1.json` and SHA-256 sidecar.

| 2024 block | Cells | Violating cells | Largest gap | Original joint Brier | Projected joint Brier |
|---|---:|---:|---:|---:|---:|
| All | 238,083 | 92 | 0.31068 | 0.02716502 | 0.02716417 |
| Original calibration | 140,508 | 82 | 0.01107 | 0.03580967 | 0.03580954 |
| Purged | 9,107 | 0 | 0 | 0.01034949 | 0.01034949 |
| Original model selection | 88,468 | 10 | 0.31068 | 0.01516628 | 0.01516422 |

The cell rate is low, but a single violating cell refuses a full live lead.
The 2024 model-selection block was previously used to select the frozen
calibrators, and 2024 is consumed development data. This result does **not**
establish independent reliability or that all 35 June lead refusals are
resolved. The projection has not been run on those 90 complete grids.

**Decision:** keep the strict live refusal gate and unchanged product. Next,
freeze a forecast-only projected-field replay on the same June case set,
check all 90 leads and district coverage, then assess probability reliability
on a genuinely independent year before any promotion. The 2026 IMD reference
is unavailable, so that independent check cannot yet be made.

Reproduce with `python scripts/score_coherent_probability_projection.py` and
`python -m pytest backend/tests/test_coherent_probability.py -q`. The scorer
verifies the protocol, selected forecast hashes and 2024 derived-year ledger
before loading labels. It refuses any change to its previously sealed score.
The scorer reproduced the existing sealed result byte for byte. Focused tests
passed (12), and the complete backend suite passed (754) on 7 October 2026.
