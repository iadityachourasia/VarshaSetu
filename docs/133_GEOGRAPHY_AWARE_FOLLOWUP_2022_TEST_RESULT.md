# Phase 10E: geography-aware follow-up, result of the single independent test on 2022

Date: 2026-10-03 (the machine clock is UTC; the test ran at 2026-10-02T20:18:24Z, after the unseal record). Result file: `backend/app/evidence_data/phase11/geoaware_followup_test_2022.json` (sha256 `fb2c0609b8359fa71836d0ee79d1bbba6f8e6df8c95f9d109499f75c596f500b`), labelled **"INDEPENDENT TEST: first use of this year"**. Design and guard: `docs/132`.

**2022 is now a consumed holdout.** It was opened once and must not be used for any further choice. Any later analysis of it must be labelled "POST-HOC EXPLORATORY ANALYSIS OF THE COMPLETED 2022 FINAL TEST", as for 2019 and 2025.

## Outcome in one paragraph

The pre-registered **primary** candidate set (protocol v3 selection) **satisfied P1 to P4 at the stated 97.5 percent level**: the geography model B1 (configuration 15) beat its control B0 (configuration 14) on Ghats-coast heavy-rain CSI, did not worsen overall error, and passed every guardrail. The pre-registered **secondary** candidate set (protocol v2 selection) **did not**: its geography model was significantly *worse* than the control on that quantity. So the geography-aware correction showed an independent gain, but only for the way the candidate was selected, and the gain over a strong control is modest.

## Numbers (stored values, 173 cases, 1,301 paired cells in every case)

Zone support: 109 cells, 1,928 observed heavy cell-case pairs and 452 very-heavy pairs, so every decision is evaluated, not unevaluable.

| Model (role) | RMSE (mm) | Bias (mm) | Heavy CSI, all cells | Very-heavy freq. bias | Ghats-coast heavy CSI | Ghats-coast heavy freq. bias |
|---|---|---|---|---|---|---|
| M0 Raw forecast | 17.00 | -0.57 | 0.073 | 0.249 | 0.078 | 0.12 |
| B0#14 (control) | 15.50 | +0.90 | 0.245 | 0.371 | 0.408 | 0.96 |
| B1#15 (primary candidate) | 14.94 | +0.21 | 0.272 | 0.311 | 0.450 | 1.24 |
| B1#8 (secondary candidate) | 14.90 | -0.67 | 0.205 | 0.015 | 0.354 | 0.69 |

Pre-registered decisions (paired whole-case bootstrap, 2,000 resamples, seed 26080, Bonferroni 97.5 percent intervals):

| Candidate set | P1 Ghats-coast heavy CSI, candidate minus control | P2 overall RMSE, candidate minus control | P3 | Adds value |
|---|---|---|---|---|
| Primary: B1#15 against B0#14 | +0.042 [+0.014, +0.073] passes | -0.55 mm [-0.83, -0.30] within tolerance | G1, G2, G4 pass; G3 met too (0.311) | **yes** |
| Secondary: B1#8 against B0#14 | -0.054 [-0.088, -0.023] does not pass | -0.59 mm [-0.92, -0.28] within tolerance | G1, G2, G4 pass; G3 not met (0.015) | **no** |

Against Raw, the primary candidate's Ghats-coast heavy CSI is +0.372 [+0.310, +0.428] and the control's is +0.330 [+0.263, +0.387]. The 95 percent intervals (descriptive) agree in sign with the 97.5 percent ones. By lead, the primary candidate has the higher Ghats-coast heavy CSI than the control on all three days (Day 1 0.488 against 0.468, Day 2 0.458 against 0.414, Day 3 0.409 against 0.352), with the smallest gap on Day 1.

## How to read it, including the unfavourable parts

1. **Most of the improvement over Raw comes from the non-geography ML correction.** The control alone lifts the Ghats-coast heavy CSI from 0.078 to 0.408. Geography adds a further +0.042, about a ninth of the total gain over Raw. That increment is statistically supported at 97.5 percent but modest in size.
2. **Part of the gain comes with mild over-forecasting.** The primary candidate's Ghats-coast heavy frequency bias is 1.24 against 0.96 for the control, and its zone bias is +3.4 mm against +0.7 mm. G4 (at most 1.5) is met, so the rule is satisfied, but a model that forecasts more heavy events will score more hits as well as more false alarms. The result should be quoted with that.
3. **The gain depends on how the candidate is selected.** The geography model chosen by lowest RMSE (secondary set) was worse than the control on the target quantity, exactly as `docs/131` warned. The aligned selection (change C2) is what made the difference, and it was introduced after earlier tables had been seen. The independent year is what makes the primary result informative, because nothing about 2022 was used for any choice; it does not remove the fact that two post-hoc changes preceded it.
4. **Two candidate sets were scored, so only the stricter 97.5 percent level supports the claim.** The primary result passes at that level.
5. **Very-heavy rain.** The primary candidate forecasts very-heavy rain at a frequency bias of 0.311 (G3 met), better than the earlier selection's near zero, but this is a reported diagnostic, not a decision criterion, and very-heavy skill was not tested.
6. **Sensitivity to the 500 hPa height offset** (descriptive, 97.5 percent intervals, models without the two height features minus the matching models with them): the primary pair is -0.014 [-0.043, +0.013], so there is no evidence the primary result depends on that field; the other three pairs are significantly lower without it (-0.083, -0.077 and -0.244, the last comparing different configurations), so the height features help in general.

## Limits

A single test year; one training window of three development years; about half the scheduled cases are forecast-eligible; bootstrap intervals are optimistic because cells within a case and consecutive days are correlated; historical replay, not warning skill; the frozen M1 to M4 were not scored on 2022 (decision 5 stayed no); IMD redistribution rights are unresolved, so the result file contains only aggregate scores.

## What this does and does not change

- **Claimed:** under a pre-registered, hash-frozen protocol, a geography-aware correction selected by the aligned rule improved Ghats-coast heavy-rain detection over the identical pipeline without geography on an independent year, within error and bias limits, for the operational-era track; a geography model selected by RMSE did not.
- **Not claimed:** that very-heavy rain is addressed, that geography alone explains the gain, that the result holds in other years or tracks, or that a validated coastal and orographic regime classifier or specialist exists. The PS requirement for a coastal and orographic regime therefore stays **PARTIAL** (the rule-based zones and a geography-aware correction exist, not a regime classifier).
- **Not changed:** the guardrails, the grid, the cap, any earlier result or any document's earlier outcome (the v1 outcome of no candidate and the v2 selection stay on record).

## Evidence and tests

`backend/tests/test_geoaware_followup_test_evidence.py` checks the hash chain, that the unseal record precedes the result and every tracked file it lists still matches, re-derives the v3 selection from the stored cross-validation table, and **re-derives every decision from the stored statistics with the same pure rule**. The API serves the verified chain at `/api/science/evidence/geoaware/followup` (503 on any tamper, on a freeze that claims 2022 was already open at freeze time, on a result not labelled as the first-use test, or on a record without the owner authorisation), and the Geography-Aware Experiment page shows it with computed text.
