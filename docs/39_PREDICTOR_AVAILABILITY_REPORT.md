# Phase 1C Predictor Availability Report

Status: **PASS for July availability; not a regime-label or training artifact**

The pilot decoded control-member forecast fields for every July 2019 00 UTC
initialization at +24/+48/+72 h. Every value is available at forecast issue time
as a positive-lead model forecast. The source is not reanalysis and no future
observation enters these arrays.

## Contract result

| Variable | Official object family | GRIB identity | Level | Decoded unit | Native grid | Context grid | Valid / expected |
|---|---|---|---|---|---|---|---:|
| U850 | `ugrd_pres` | `u` / U component of wind | 850 hPa | m s**-1 | 0.25° | 0.5° bilinear | 93/93 |
| V850 | `vgrd_pres` | `v` / V component of wind | 850 hPa | m s**-1 | 0.25° | 0.5° bilinear | 93/93 |
| Q700 | `spfh_pres_abv700mb` | `q` / Specific humidity | 700 hPa | kg kg**-1 | 0.5° | 0.5° bilinear | 93/93 |
| Z500 | `hgt_pres_abv700mb` | `gh` / Geopotential height | 500 hPa | gpm | 0.5° | 0.5° bilinear | 93/93 |
| MSLP | `pres_msl` | `msl` / Mean sea level pressure | mean sea | Pa | 0.25° | 0.5° bilinear | 93/93 |
| PWAT | `pwat_eatm` | `pwat` / Precipitable water | entire atmosphere | kg m**-2 | 0.25° | 0.5° bilinear | 93/93 |

The Phase 1A contract named Q700's family as `spfh_pres`. Direct archive
inspection showed that family contains pressure levels only from 1000 to 800 hPa.
The official `spfh_pres_abv700mb` family contains the exact 700-hPa specific
humidity field. This is an archive-object correction, not a variable
substitution. Z500's decoded source unit is `gpm`, not the earlier table's `m`.

## Availability by variable and lead

| Variable | Lead | Expected | Valid | Missing | Failed | Completeness % | Retained message bytes |
|---|---:|---:|---:|---:|---:|---:|---:|
| U850 | 24 | 31 | 31 | 0 | 0 | 100 | 26,179,424 |
| U850 | 48 | 31 | 31 | 0 | 0 | 100 | 26,561,197 |
| U850 | 72 | 31 | 31 | 0 | 0 | 100 | 26,640,577 |
| V850 | 24 | 31 | 31 | 0 | 0 | 100 | 26,536,556 |
| V850 | 48 | 31 | 31 | 0 | 0 | 100 | 27,056,498 |
| V850 | 72 | 31 | 31 | 0 | 0 | 100 | 27,200,318 |
| Q700 | 24 | 31 | 31 | 0 | 0 | 100 | 6,216,448 |
| Q700 | 48 | 31 | 31 | 0 | 0 | 100 | 6,317,476 |
| Q700 | 72 | 31 | 31 | 0 | 0 | 100 | 6,348,545 |
| Z500 | 24 | 31 | 31 | 0 | 0 | 100 | 6,774,851 |
| Z500 | 48 | 31 | 31 | 0 | 0 | 100 | 6,907,586 |
| Z500 | 72 | 31 | 31 | 0 | 0 | 100 | 6,903,337 |
| MSLP | 24 | 31 | 31 | 0 | 0 | 100 | 28,021,623 |
| MSLP | 48 | 31 | 31 | 0 | 0 | 100 | 28,069,873 |
| MSLP | 72 | 31 | 31 | 0 | 0 | 100 | 28,225,734 |
| PWAT | 24 | 31 | 31 | 0 | 0 | 100 | 14,368,159 |
| PWAT | 48 | 31 | 31 | 0 | 0 | 100 | 14,540,956 |
| PWAT | 72 | 31 | 31 | 0 | 0 | 100 | 14,569,183 |

Complete predictor bundles: 93/93 initialization-lead bundles. Incomplete
bundles after independent retry: 0. A transient first-attempt Q700 index failure
on July 31 is retained in the initial execution history but is not an archive
availability gap.

## Monthly field sanity statistics

| Variable | Minimum | Maximum | Mean | Missing fraction | Initial-bound warning |
|---|---:|---:|---:|---:|---|
| U850 | -26.4889 | 29.5042 | 9.1462 | 0 | none |
| V850 | -25.6068 | 22.5500 | 2.0219 | 0 | none |
| Q700 | 0.000310 | 0.017380 | 0.007735 | 0 | none |
| Z500 | 5740.588 | 5920.111 | 5837.814 | 0 | none |
| MSLP | 98534.945 | 102077.539 | 100338.166 | 0 | none |
| PWAT | 2.200 | 82.300 | 49.719 | 0 | none |

Bounds are warnings only; no value was clipped. Detailed message metadata,
packing precision, valid time, member identity, and grid geometry remain in the
31 daily source manifests.

## Scientific conclusion

The minimum forecast-field contract is repeatedly obtainable for this month and
supports a future forecast-time regime-inference architecture. It does not
validate any regime definition, label generator, vorticity derivation, feature
skill, or model. Those remain forbidden until separately reviewed.

