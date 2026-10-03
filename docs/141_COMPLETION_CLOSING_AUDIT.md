# Closing audit of the completion work packages (WP-A to WP-G)

Date: 2026-10-03. This closes the plan of `docs/134`. For each problem-statement item it states what was built, the final coverage status, the evidence, and the gap that remains and why. The live status of every row is the `/compliance` page and `docs/22` (generated from `backend/app/evidence_data/phase6/ps_coverage.json`); this document explains it.

## Final coverage

**Update after the reforecast study (`docs/142`):** of the 14 official requirement IDs, **all 14 are implemented**: PS-R03 through validated sealed-year regime detection and PS-R05 through a pre-registered confirmatory test after round 1 failed its bias guardrail. Of the 30 coverage rows, **27 are implemented, 3 partial and none planned**; the partial rows are the non-mandatory extras independent expert validation, live inference and the all-India domain. The table below is the state before that study and is kept as the record of the first closing.

Original first-closing statement: of the 14 official requirement IDs, 12 were implemented and 2 partial (PS-R03, PS-R05); of the 30 coverage rows, 23 implemented, 7 partial and none planned.

## Item by item

| Item | Work package | Final status | What exists | What remains and why |
|---|---|---|---|---|
| District verification, Track A | WP-A, `docs/135` | IMPLEMENTED (both tracks) | Frozen protocol carried over unchanged from Track B; 2018 development and 2019 post-hoc evidence; per-track manifests served and shown. District-mean error improves; district heavy-rain CSI is below Raw for every corrected model. | Nothing further. The result is unfavourable on heavy-rain detection and is reported as such. |
| Independent regime validation | WP-B, `docs/136` | PARTIAL | Observation-based active and break labels (Rajeevan et al. 2010 style, 1981-2016 climatology), frozen protocol, four populations, support gate. The pseudo-class named Active does not match observed active spells. | Break and depression could not be validated (too few cases, no depression label). Not the published classification. A real validation needs expert or bulletin labels. |
| Coastal and orographic regime | WP-C, `docs/137` | PARTIAL | A forecast-time forcing regime (weak, moderate, strong), terciles from the training year, discriminating observed Ghats-coast heavy rain on the development years; served and shown. | It is a heuristic, not a learned or validated regime; there is no specialist model, and a standing rule forbids IMPLEMENTED without one. |
| Western-disturbance regime | WP-D, `docs/138` | PARTIAL | A forecast-time 500 hPa trough indicator from stored global fields, served and shown. | The pre-registered association with north-west India rainfall was **not met**; no label source exists; the corpus is the monsoon season. A validated regime needs labels and a winter or pre-monsoon corpus. |
| All-India domain | WP-D, `docs/140` | PARTIAL | Raw GEFS verified against IMD over the whole IMD grid, by region, with intervals and a support gate; reproduced by an independent per-cell loop. | Raw only: no model was applied or trained outside the 10-22 N, 68-80 E box; the wider reconstruction excluded more cases. A corrected all-India forecast needs a new corpus, protocol and independent test. |
| Heavy-rain models in the product | WP-E | PARTIAL (improvement row) | The 2022 independent-test figures for the event-weighted and geography-aware corrections are facts on the improvement row, with their first-use label, and are shown on the Geography-Aware page. | Very-heavy improvement is not shown (the primary candidate's interval includes zero). The corrections are not applied to other years. |
| Live new-cycle pipeline | WP-F, `docs/139` | PARTIAL | Worker, immutable hash-checked bundle, read-only API and page. The replay of stored 2025 cycles through the same code reproduces features, regime probabilities, M0-M4 and probabilities exactly, and refuses what the corpus refused. | No live NOAA cycle had been fetched (a download needs owner confirmation); no scheduler, alerting or hosted worker; no skill claim is possible for a new cycle. |

## What cannot be demonstrated on data that exist today

- **Very-heavy rain improvement.** Every corrected model has low very-heavy skill; the only candidate whose interval excludes zero does so by a hair on one year, and it was not a decision criterion.
- **Skill on a new cycle.** Observations arrive months later.
- **A validated regime classifier.** The classes are forecast-only pseudo-labels; the one independent check is unfavourable for Active and silent on Break and depression.
- **An NCMRWF model.** The forecast being corrected is NOAA GEFS.

## Checks run for this closing

Final state after the reforecast study, the decision to keep the maps on the validated model box, and a visual quality pass over every page:

- Backend `pytest backend/tests` (writable `--basetemp`): 670 passed. The replay gate, the broken-input cases and the independent all-India recomputation need the local frozen tree and IMD files and are skipped (not passed) on a bare clone.
- Frontend: TypeScript and ESLint clean; Vitest 183 passed; production build clean.
- Playwright against the real backend (single worker): 131 passed. Four of these are new and cover the in-page navigation of the two long evidence pages (every link resolves to a section), the absence of nested scroll boxes around evidence tables, and the single caveat list of the live page.
- Visual review of all 16 routes at desktop and phone width and in dark mode, with console errors and horizontal overflow measured: no console error and no horizontal overflow on any route.
- Defects found and fixed in that pass: evidence tables were trapped in a 550 px scroll box (the Compliance rows were cut off); the live page printed its caveats twice and drew a small map without a scale; the Verification page had a stale "charts below" boundary note at its very end and no way to jump between its six sections; the reforecast panel had no spacing between its tables and verdicts; two synoptic label styles keyed on a `data-theme` attribute the app never sets, so they never switched in dark mode.
- Stale assertions from earlier work packages were corrected (a coastal protocol test that expected only zone facts, a Vitest test that expected two planned rows); a copy-guard test that pins the Verification subtitle was respected, not edited.
- Standing rules held: IMD files stayed local with only aggregates tracked (the IMD-derived pair caches and the 1.6 GB reforecast cache are gitignored); consumed holdouts (2019, 2022, 2025) carry their post-hoc labels; Track A and Track B were never pooled; no manifest text contains a typed number.

## Open owner items

IMD redistribution rights (D2); whether the frozen M1-M4 may be run on 2022 (default no); confirmation to fetch a current NOAA cycle for the live worker (about 9 MB; `plan` shows the exact ranges first); push.
