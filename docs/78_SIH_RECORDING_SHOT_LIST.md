# Phase 3C — Recording shot list

Capture the production app at 1920×1080, browser zoom 100%, dark theme.
Close unrelated windows and notifications. Move the cursor out of metrics
after interaction; do not show secrets, terminals or developer-console logs.
Keep OpenFreeMap/OpenMapTiles/OSM and geoBoundaries attribution visible. Use
slow, deliberate scrolls; pause after map navigation for labels/vector tiles
to render. No fake animation or scientific image is permitted.

| Shot / approx. duration | Page, official case | Style / display | Interaction and expected result | Narration |
|---|---|---|---|---|
| 1 / 20s | Overview, none | N/A | Show title, historical label | Problem |
| 2 / 20s | Overview, A entry | N/A | Show 9.73% with Raw 19.7735 and M2 17.8487 mm; click primary CTA | Evidence |
| 3 / 30s | Forecast, A `20190802T000000Z_day3_24h` | Dark Geographic / Weather Visualization | Three maps and online labels; modest case RMSE improvement clearly separate from aggregate | Forecast comparison |
| 4 / 15s | Forecast, A | Dark Geographic / Scientific Grid | Toggle display, inspect preselected nearest-valid-center cell; show exact Raw/corrected/IMD values and synchronized cameras | Grid integrity |
| 5 / 20s | Forecast, A then C `20190802T000000Z_day2_24h` | Dark Geographic / Weather Visualization | Read forecast-only regime probabilities; C shows Active and case-level worsening | Regime caveat |
| 6 / 30s | Extreme Rain, B `20190807T000000Z_day2_24h` | Dark Geographic / Weather Visualization | Toggle Heavy ≥64.5 and Very Heavy ≥115.6 mm/24h; inspect probability cell | Extreme probabilities |
| 7 / 15s | Extreme Rain, B | same | Scroll to 2019 reliability and counts; do not conflate probability with amount | Calibration limits |
| 8 / 25s | Districts, B | Dark Geographic / fixed district choropleth | Select a case-valid district, show mean/max/probability/area fractions and attribution | District intelligence |
| 9 / 35s | Verification, none | N/A | M0–M4 table, 9.73% aggregate, Heavy/VH metrics; scroll to FSS and observe Raw lead | Honest evaluation |
| 10 / 25s | Methodology, none | N/A | Show parallel correction/regime wording, 2017/2018/2019, provenance and historical-only boundary | Close |

For a Light Geographic B-roll shot, select Light Geographic and wait for
Positron vector tiles/labels; restore Dark before continuing. For offline
rehearsal, block the OpenFreeMap host in a test context only and verify the
clearly labeled district-geometry fallback. Do not present offline fallback
as the full online map. Full-page charts need planned scrolls rather than
shrinking the browser below legible zoom.

The numbered shots above use **2019 GEFSv12 reforecast** APIs only. If adding
the completed 2025 operational-era benchmark, add a separate sourced
Verification/report slide after shot 9, never 2025 values on 2019 maps. It
must identify the preselected Ridge MOS, 232-case population, 3.66% RMSE
reduction, Raw's stronger extreme spatial FSS, and historical/non-live scope.
