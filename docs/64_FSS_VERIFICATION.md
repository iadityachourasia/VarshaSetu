# Phase 2C Fractions Skill Score Verification

## Definition and validity

FSS is computed from actual aligned 49×49 two-dimensional 24-hour rainfall
fields on the 10–22° N, 68–80° E, 0.25° target grid, not flattened stations.
For threshold T and an odd square neighborhood, the observed/forecast event
fractions are the count of cells at or above T divided by the count of valid
cells in that neighborhood. Then `FSS = 1 - sum((f-o)^2)/sum(f^2+o^2)` over
eligible centers, with the numerator/denominator summed across cases before
division. Validity uses the exact Phase 2B paired observation/forecast mask.

Domain edges use only in-domain cells (no wrap or reflected rainfall). Masked
IMD cells are excluded from both fractions. A center must itself be valid and
at least 50% of its in-domain neighborhood must be valid. Cases/neighborhoods
where both forecast and observed event fractions are everywhere zero add zero
to numerator and denominator; an individual case FSS is `null` with a reason.
If the total denominator is zero, aggregate FSS is also `null`. Defined FSS is
bounded to [0,1]. Synthetic perfect, mismatch, edge, mask, and no-event tests
exercise this policy.

The scales are 1×1, 3×3, 5×5 and 9×9 cells. One 0.25° latitude cell is about
28 km; longitude-cell width varies with latitude (~26–27 km in this domain),
so these are approximate scales, not exact kilometer distances.

## Frozen 2019 comparison

All rows use the same 255 Phase 2B cases and paired valid-cell masks. The
`case_count` in the machine-readable per-method FSS record is the number of
cases contributing a nonzero FSS denominator, which can differ by model when
one forecast has no threshold events. This does not change the paired source
population. Raw/Corrected denominator-contributor counts are shown below.

| Threshold | Window | Raw FSS | Corrected M2 FSS | Raw/Corrected contributing cases |
|---|---:|---:|---:|---:|
| 64.5 mm/24h | 1×1 | 0.214916 | 0.092548 | 236 / 228 |
| 64.5 mm/24h | 3×3 | 0.331008 | 0.145397 | 236 / 228 |
| 64.5 mm/24h | 5×5 | 0.378822 | 0.162803 | 236 / 228 |
| 64.5 mm/24h | 9×9 | 0.426756 | 0.163781 | 236 / 228 |
| 115.6 mm/24h | 1×1 | 0.064481 | 0.000000 | 165 / 152 |
| 115.6 mm/24h | 3×3 | 0.108631 | 0.000000 | 165 / 152 |
| 115.6 mm/24h | 5×5 | 0.129916 | 0.000000 | 165 / 152 |
| 115.6 mm/24h | 9×9 | 0.160384 | 0.000000 | 165 / 152 |

For the pair evaluated here — **Raw GEFS vs the M2 global model on the 2019
Track A population** — Raw GEFS is stronger at every evaluated FSS threshold and
spatial scale. FSS was not computed for M1, M3 or M4 in 2019, so this result
must not be read as "Raw beats every corrected model on FSS". The Track B
diagnostics in `docs/106` show that this does not generalise: for heavy rain
the regime-aware M3/M4 exceed Raw on FSS in 2024 and 2025.
The M2 corrected forecast improves aggregate RMSE but suppresses very-heavy
deterministic events. The calibrated binary probability outputs are a separate
product; they do not retroactively improve deterministic FSS. No FSS-based
retuning of M2 or the probability selection was performed.
