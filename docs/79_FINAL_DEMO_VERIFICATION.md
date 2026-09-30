# Phase 3C — Final demo verification

Verified on the HP Victus Windows 11 development machine against the frozen
local Phase 2B/2C API and the actual Next.js 16.3.6 production build. No
scientific artifact, backend route, legacy frontend or model was changed.
The repository has no accessible Git metadata, so this report relies on
hash verification and explicit file scope, not a Git diff.

## Frozen scientific claim and case population

The read-only model-comparison endpoint returned Raw RMSE
19.773472597952658 mm and M2 Global XGBoost RMSE 17.84869823727102 mm
on the common 2019 test population. The UI computes
`(Raw - M2) / Raw × 100` = 9.73% at display precision. This is not a
selected-case result. M2 has the lowest deterministic RMSE, but M3/M4 do
not beat it on RMSE. Raw retains stronger deterministic Heavy/Very Heavy
CSI/ETS than every corrected model, and stronger FSS than M2 at every
reported scale (FSS exists only for Raw vs M2 in 2019). The 2019 Very Heavy categorical FAR is
0.8723324316200781. The UI displays the historical/non-operational
boundary, rare-event reliability caveat, and pseudo-label regime caveat.
The Methodology path explicitly identifies the primary M2 and regime
classifier as **parallel** forecast-only models.

The primary entry case is official
`20190802T000000Z_day3_24h`: Day 3, 158 Heavy and 70 Very Heavy
observed cells; Raw/corrected case RMSE 41.7434/41.3304 mm. Heavy case
`20190807T000000Z_day2_24h` has 200/106 Heavy/Very Heavy cells and
49.4892/50.1636 mm case RMSE. Transparency case
`20190802T000000Z_day2_24h` has an Active pseudo-label, 147/77
Heavy/Very Heavy cells and 40.9116/42.8856 mm case RMSE. All three have
rainfall, probability, FSS, regime and 187 case-valid district outputs.
Their selection is illustrative, not test-set cherry-picking.

The rainfall/probability inspector defaults to the valid cell nearest the
49×49 grid center, with deterministic row-major tie order; for the
primary case the selected coordinate is 16.00° N, 74.00° E. Districts
default to the case-valid district with highest **forecast corrected
mean** and ID tie-break, with no observation-based selection.

## Production checks

| Check | Observed result |
|---|---|
| TypeScript strict, ESLint | passed |
| Vitest | 3 files, 12 tests passed |
| Next production build | passed; six routes generated |
| Production Playwright | Final two-worker run 10/10 passed in 1.8 minutes, including complete path, 1920×1080/1440×900/1366×768 screenshots, online vector tile, offline failure, API-display consistency |
| Accessibility smoke | no critical/serious axe WCAG 2A/AA/2.1 A/AA violations on Verification |
| Backend pytest | 86 passed, 1 upstream Starlette/AnyIO deprecation warning |
| Python compileall | passed |
| Phase 2C manifest | SHA-256 sidecar matched; 525 listed files, 0 digest mismatches |
| API readiness/proxy | `prototype_scientific_ready`, `operational_ready=false`; local and same-origin proxy passed |
| API safety | Unknown science case returned 404; legacy `/api/forecast` with required query returned historical 409 lock |
| Online geography | official Dark style, OSM-derived vector `.pbf` tiles, sprites/fonts HTTP 200 in browser; visible place labels and attribution |
| Cartographic warning | public Dark style omitted its referenced `circle-11` sprite; a narrow local marker resolver removed the warning without touching science |
| Offline geography | simulated provider failure, local district fallback and scientific maps/inspection/district interaction passed |

Browser screenshot review found no horizontal overflow at the three desktop
widths. Large Verification and District tables require deliberate scrolling
during recording. Online geography can take a few seconds after scientific
layers are ready; wait for labels before capturing. The public provider
has no availability guarantee and preflight must be repeated on recording
day. The fallback is not a full street/city map.

Representative warm production browser timings after final rebuild, with
one browser worker: Overview 194 ms, Overview→three scientific map layers
1,211 ms, official case switch 711 ms, Verification navigation 206 ms.
Under four simultaneous browser workers the same test saw 944, 5,208,
10,500 and 14,068 ms, respectively; the full 10-test run still passed.
This contention is a reason to close other browser/test workloads during
recording. These are browser/test-environment samples, not latency SLAs or
controlled performance benchmarks. The launcher preflight
completed with local API/proxy and online style available when run with
network permission. The observed warm production launcher elapsed time was
8.26 seconds with an already healthy external API. Its shutdown stopped
only its owned Next process while that API remained healthy. Neither
training nor GRIB decoding occurred.

## Documentation discrepancies resolved or retained

- `docs/68` described the old polygon renderer and no external tiles;
  it now has an append-only Phase 3B/3C supersession pointing to `docs/73`.
- `docs/73` described the old alphabetically-first district default; it
  now records the forecast-based presentation selection.
- The Next scaffold README claimed a development port and template setup;
  it is replaced with the actual production launch contract.
- Historical `docs/60` uses “255 final common” and “255 upper bound” in
  nearby passages. API/model manifest agree on 255 test cases and 331,755
  paired cells; the historical scientific report was not rewritten here.

## Recording and remaining limits

OBS Studio 32.1.2 is installed. Configure a 1920×1080 canvas/output,
30 fps, window capture of the browser, hardware encoder if stable, and
record a short local test with microphone check. Keep audio, notifications
and private desktop content controlled. Playwright screenshots/trace are
QA evidence, **not** a completed narrated video. No finished video file
was created in this phase.

Release status: **READY_FOR_RECORDING**, conditional on repeating the
online-basemap and local preflight at the actual recording time. This does
not mean operational readiness or public deployment.
