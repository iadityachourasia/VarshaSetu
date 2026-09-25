# Regridding and Alignment Specification

Status: validated for the single Phase 1B rainfall pair only. This is not yet a
multi-date production specification.

## Scope and invariant

The source is NOAA GEFSv12 Reforecast control-member precipitation and the
target is the native IMD 0.25° daily-rainfall grid. The validated correction/FSS
domain is 10–22°N, 68–80°E. Rainfall remains in millimetres and IMD missing or
ocean cells remain invalid; fill values are never converted to zero.

The paired interval is half-open:

```text
[2019-07-14 03:00 UTC, 2019-07-15 03:00 UTC)
```

This corresponds to GEFS initialization 2019-07-14 00 UTC, leads +3 through
+27, and IMD target date 2019-07-15 under the externally verified 08:30 IST to
08:30 IST daily convention. The IMD NetCDF time coordinate labels the date at
00:00 and does not provide accumulation bounds, so the interval convention is
external metadata and must continue to be recorded explicitly.

## Source grid inspection

The decoded GEFS GRIB messages are `regular_ll`, 1440 × 721 globally, with
0.25° cell centres, longitudes 0–359.75°, and native latitude storage north to
south. The adapter canonicalizes latitude to ascending order before any crop.
The target-domain crop has 49 × 49 centres from 10.0 to 22.0°N and 68.0 to
80.0°E, inclusive.

The IMD file has 135 longitudes from 66.5 to 100.0°E and 129 latitudes from 6.5
to 38.5°N, both ascending at 0.25°. Its target-domain crop is also 49 × 49. No
coordinate-bound variables are present. In this pilot the GEFS and IMD target
cell centres are exactly equal after GEFS latitude canonicalization.

## Cell-bound construction

For every strictly ascending one-dimensional centre coordinate, interior bounds
are adjacent-centre midpoints. Each exterior bound is obtained by reflecting the
nearest midpoint about the exterior centre. For a uniform 0.25° grid this gives
half-cell extensions of 0.125°. The procedure fails closed for non-1-D,
non-monotonic, or single-point coordinates.

Spherical cell area uses:

```text
A = R² × [sin(phi_north) - sin(phi_south)] × [lambda_east - lambda_west]
R = 6,371,000 m
```

## First-order conservative weights

`backend/app/data/regridding.py` constructs a target-area-normalized overlap
matrix. Each weight is the spherical source/target cell-intersection area divided
by target-cell area. Every target row must sum to 1 within absolute tolerance
`1e-10`; incomplete source coverage is an error.

For this one pair, the grids are co-located and the resulting conservative
mapping is an identity mapping. The method is still derived from validated cell
bounds rather than assuming identity. The deterministic NumPy weight artifact
has SHA-256:

```text
37a3fc3244c0ce6c41bf6c580de8748194e7e1dc839e73e0e17285530e245523
```

The implementation is repository-local NumPy spherical overlap code, executed
with NumPy 2.2.6 and SciPy 1.16.1. GRIB decoding used ecCodes 2.48.0.

## Mask semantics

The IMD `RAINFALL` variable declares both `_FillValue=-999.0` and
`missing_value=-999.0`. The valid mask is:

```text
isfinite(observation) AND observation != fill_value
```

The derived NetCDF stores `valid_mask[y,x]` separately and writes invalid
observation cells as `-999.0`. Forecast values remain defined across the
rectangular target domain, but any comparison or future FSS calculation must use
only cells where `valid_mask` is true.

For this pilot there are 1,301 valid and 1,100 masked cells. The comparable
valid area is 960,237,217,681.0657 m²; the full rectangular target area is
1,780,148,630,578.9324 m².

## Conservation QC

The diagnostic is the sum of rainfall depth multiplied by spherical cell area
over the identical IMD valid-cell mask before and after mapping. The preliminary
relative tolerance is `1e-10`, justified here because source and target grids are
exactly co-located and the generated weights should reduce to identity.

```text
source integral = 6,818,087,525,825.749 mm m²
target integral = 6,818,087,525,825.749 mm m²
relative difference = 0.0
status = PASS
```

A later non-coincident source/target grid needs a tolerance justified from that
grid geometry and numerical implementation; this pilot's zero difference must
not be generalized.

## Fail-closed conditions

Alignment fails if coordinates are non-monotonic, source coverage is incomplete,
source and target identity unexpectedly differs in this fixed pilot, weight rows
do not sum to one, rainfall contains material negative values, the observation
mask cannot be recovered, or the conservation tolerance is exceeded.

## Reproduction

From the repository root, with the official IMD annual file already available:

```powershell
.venv\Scripts\python.exe scripts/data/acquire_pilot_pair.py `
  --imd-file data/raw/observations/imd/2019/RF25_ind2019_rfp25.nc `
  --pilot-date 2019-07-15 `
  --output-root data
```

The command does not train, label, or change scientific readiness.
