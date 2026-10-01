# Phase 7B (Stage 0): static geography artifact for the coastal/orographic protocol

Date: 2026-10-01. Protocol: `docs/115`, frozen v3 (SHA-256 `a9ff78173ddb6026e6b297c2da2128dde2fdcf825ae8b0c368c5f5fa79d199fd`). No rainfall value, model output or skill result was read. No model was trained.

## Source

| Item | Value |
|---|---|
| File | `GMTED2010_mean_30arcsec.nc4`, 249,216,253 bytes, md5 `5b6c47502ae8d03b8718349655d5cd95`, SHA-256 `5aef5bbaa5373d530752ad648c63aa2cc2b14d5a854fe5acf0a61fb8bacca7f8` |
| Distribution | Zenodo record 14537811, third-party NetCDF conversion of the USGS GMTED2010 mean 30 arc-second ArcGrid, CC BY 4.0 (attribution kept in the artifact) |
| Local copy | `data/static_geography_raw/` (gitignored; not redistributed; the build verifies size and hash and refuses otherwise) |
| Vertical reference | EGM96 geoid, used as relative elevation only |
| Download | Confirmed by the project owner with file name, source and size stated beforehand; size and md5 matched |

## What was built

`backend/app/evidence_data/phase7/static_geography_v1.json` (SHA-256 `cb546e192fe24a53b991653acf0a7960393a234e9a6eddcd34b56c6b0b8151d0`, sidecar `.sha256`, LF bytes, `-text`), produced by
`scripts/build_static_geography.py` (`--check` reproduces it byte for byte; needs `h5py`, a build-time dependency of the script only, not added to the backend requirements).
It holds, on the 49×49, 0.25° grid: IMD footprint (1,301 cells), land fraction, mean elevation, local relief (3×3), distance to coast, slope, terrain uphill unit vector,
landward coast-normal unit vector and the zone label per cell. The footprint is the set of cells only. QA maps: `docs/artifacts/static_geography_v1_qa.png` (`scripts/plot_static_geography_qa.py`).

## Findings

- Footprint versus terrain: 1,253 of 1,301 footprint cells (96.3 %) are majority-land in the terrain file; 11 contain no land pixel above 0 m and 37 more are less than half land (all coastal); 2 terrain-land cells lie outside the footprint. The v2 union rule handles this.
- Zone cells (v3 rules): **COASTAL 210, OROGRAPHIC 245, COASTAL_AND_OROGRAPHIC 109, OTHER 737** (total 1,301); every zone exceeds the 20-cell gate. Coastal ≤ 100 km: 319 cells; orographic (relief ≥ 300 m): 354.
- Sensitivity-only counts: coastal 113 / 202 / 480 cells at 50 / 75 / 150 km; orographic 626 / 466 / 229 cells at relief ≥ 200 / 250 / 400 m; the superseded v2 rule would have marked 825 cells.
- The maps are physically plausible: the Western Ghats escarpment and the Nilgiris stand out in relief, the interior plateau has low relief, and distance to coast grows toward the north-east interior.

## Notes and limitations

- The v3 amendment text quotes the diagnostics from the first v2 build (824 and 354 cells); after rounding the stored values to two decimals the final artifact gives 825 and 354. The orographic count under the approved rule is unchanged.
- Zones are decided on the stored (two-decimal) values so the artifact is self-consistent at the thresholds.
- 0.25° smooths the Ghats; true land at exactly 0 m is read as sea by the terrain file (the footprint union covers every coastal footprint cell); GMTED2010 is a 1 km product aggregated here.
- The zones are a transparent rule-based convention and are not a validated regime. Nothing here changes the PLANNED status on `/compliance`.

## Tests

`backend/tests/test_static_geography.py` (6): protocol hash chain v1→v2→v3 with earlier versions byte-unchanged; artifact hash, source pin and attribution; footprint and QA criteria; independent recomputation of every zone from the stored fields; physical sanity and no rainfall/target fields; known places (Mumbai coast, Deccan interior, Nilgiris).

## Next

Stage 1: zone-stratified verification of the frozen M0–M4 on both tracks with the paired whole-case bootstrap, under the support gate and decision rule in `docs/115`. This reads rainfall and model grids, so it is the first step that touches results; the protocol is frozen and the zones are fixed.

Gate: `P0_7_STAGE0_COMPLETE`.
