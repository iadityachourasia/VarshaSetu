# Dataset Version and Freeze Specification

## Version identity

The stable identifier is:

`varshasetu-gefs12r-imd025-jjas-2000-2019-v1`

The authoritative machine-readable plan is
`data/manifests/corpus/varshasetu-gefs12r-imd025-jjas-2000-2019-v1.plan.json`.
It validates through `DatasetFreezeManifest`, is immutable in memory, declares
`acquisition_status="NOT_STARTED"`, and declares `training_eligible=false`.
It is a specification, not evidence that the corpus exists.

## Frozen semantics

V1 freezes NOAA GEFSv12 Reforecast and official IMD 0.25° daily gridded
rainfall; years 2000-2019; JJAS 00Z initialization dates; three 24-hour windows;
c00/p01-p04 rainfall; c00 U850/V850/Q700/Z500/MSLP/PWAT at +24/+48/+72; target
and context domains/grids; units/native identities; accumulation reconstruction;
IMD mask; conservative rainfall and bilinear atmospheric mapping; packing
negative policy; eligibility/month gates; storage schema/chunks; retry rules;
and comparison fairness.

Any change to a scientific meaning—including provider/version, temporal window,
member set, variable/level/unit, grid, mask, regridding, negative policy,
eligibility, or observation convention—requires a new dataset version. Existing
v1 manifests and bytes remain immutable. Operational GFS/GEFS, IMERG, ERA5, or
IMDAA cannot be silently merged into v1.

## Provenance hierarchy

Every accepted normalized chunk must resolve to the dataset version, monthly
manifest, initialization manifest, child receipt, source URL/range/hash, decoded
message metadata, transformation/software version, and QC result. Native names
remain alongside canonical names. Training views store case IDs and eligibility
masks and are regenerable; they do not become a second undocumented dataset.

## Prototype subset status

The full 2000-2019 corpus plan remains unacquired and its plan-level status is
still `NOT_STARTED`. A provenance-complete 2019 JJAS subset now exists under the
same frozen semantics and is admitted
`SEASON_ACCEPTED_WITH_QUARANTINED_SAMPLES`. This does not make the full plan
complete and does not change `training_eligible=false`. See
`47_2019_JJAS_CORPUS_REPORT.md` for the subset manifest and quarantine counts.

## Phase 1F semantic successor

The approved successor is
`varshasetu-gefs12r-imd025-jjas-2000-2019-v2`. It changes only precipitation
reconstruction and its negative-residue policy: metadata-derived exact cover
minimizes subtractions, and the unavoidable difference uses its mathematical
packing bound without the v1 0.1 mm cap. Timing, IMD pairing, providers,
members, grids, masks, atmospheric predictors, and eligibility meanings do not
change. V1 artifacts remain immutable historical evidence; future acquisition
and experiment construction must identify v2 explicitly.

The executed 2019 v2 subset is at
`data/processed/phase1f/2019-JJAS/varshasetu-gefs12r-imd025-2019-jjas-v2.zarr`.
The full multi-year v2 corpus is not acquired and remains non-training-ready.

## Phase 2A prototype subsets

The authorized 2017 and 2018 JJAS subsets use the same v2 provider, products,
members, predictors, grids, timing, IMD pairing, canonical reconstruction, and
eligibility meanings as the executed 2019 v2 subset. Their temporal roles are
frozen as training and validation respectively; 2019 is the untouched final
test/demo period. This bounded acquisition does not imply that the named
2000–2019 corpus is complete. Season manifests and training indices remain the
evidence for which cases are usable; source presence alone is not admission.
The 2017/2018 subset manifests now report 1,489/1,830 and 1,476/1,830 valid
rainfall member-products and preserve the same case-tiered semantics; the full
corpus plan remains incomplete and non-training-ready for rainfall modeling.
See `53_PHASE2A_2017_2018_CORPUS_REPORT.md` for the executed evidence.
