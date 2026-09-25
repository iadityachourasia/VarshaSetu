# Phase 3C — SIH prototype video storyboard

Target 3:40, captured from the actual production app at 1920×1080. All
forecast scenes are **historical 2019**, not live forecasts. The three cases
are from the frozen Phase 2C catalogue:

- A, complete workflow: `20190802T000000Z_day3_24h`, Day 3, 158
  observed Heavy and 70 Very Heavy cells; case RMSE 41.74 Raw / 41.33
  corrected mm. This modest case-specific improvement is illustrative only.
- B, extreme rainfall: `20190807T000000Z_day2_24h`, Day 2, 200 Heavy and
  106 Very Heavy cells. Case RMSE worsens 49.49 → 50.16 mm.
- C, transparency/regime contrast: `20190802T000000Z_day2_24h`, Day 2,
  Active forecast-only regime, 147 Heavy cells; case RMSE worsens
  40.91 → 42.89 mm.

| Time | Scene | Evidence |
|---|---|---|
| 00:00–00:20 | Problem and title | NWP rainfall needs verified post-processing, not invented forecast values |
| 00:20–00:40 | Overview | Historical label and API-derived 9.73% lower 2019 RMSE |
| 00:40–01:25 | Forecast Explorer, A | Three aligned maps; raw → corrected → IMD, inspect a valid original grid cell |
| 01:25–01:45 | Forecast-only regime, A then C | Probabilities reproduce pseudo-label methodology; do not call them observed truth |
| 01:45–02:15 | Extreme Rain, B | Heavy and Very Heavy probability maps; threshold units, reliability and sparse-bin caveat |
| 02:15–02:40 | District Intelligence, B | Select a real case-valid district; area-weighted summary and limited geographic scope |
| 02:40–03:15 | Verification | M0–M4, true held-out season, FSS, and high Very Heavy FAR |
| 03:15–03:40 | Methodology and close | Parallel primary correction/regime branches, 2017/2018/2019 split, historical-only limitation |

Avoid rapid cuts before map labels load. The first viewport is a chapter
opening, not every lower chart; scroll deliberately for FSS and reliability.
Case examples never establish aggregate superiority—the full common 2019
test population does.

## Separate 2025 evidence, if included in the recording

The timed scenes above are **2019-only** and remain valid as historical UI
demonstration. The completed 2025 operational-era final test is a different
GEFS lineage and population; do not overlay its figures on any 2019 map. A
separate sourced Verification/report slide may state that the preselected M1
Ridge reduced 2025 RMSE from 16.1657 to 15.5736 mm (3.66%) on 232 cases,
while Raw GEFS retained better heavy/very-heavy spatial FSS. Cite
`89_OPERATIONAL_FINAL_TEST_2025.md` and the Phase 4K audit. Re-time the video
explicitly if this segment is added; do not silently squeeze away limitations.
