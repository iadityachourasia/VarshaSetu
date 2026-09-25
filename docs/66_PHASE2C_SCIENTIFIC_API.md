# Phase 2C Read-Only Scientific API

All endpoints are under `/api/science` and serve only hash-verified, frozen
2019 historical artifacts. They never train, decode GRIB, query a network,
or perform scientific recomputation in an HTTP request. Case IDs are a strict
`YYYYMMDDT000000Z_day{1,2,3}_24h` allow-list matched against the frozen
manifest; unknown/path-traversal IDs return 404. All responses have Pydantic
schemas and science provenance. Internal absolute filesystem paths are never
included in responses. Invalid artifact hashes fail closed with 503.

| GET endpoint | Response purpose |
|---|---|
| `/status` | `prototype_scientific_ready`, counts and `operational_ready=false` |
| `/cases` | 255 historical case descriptors for a selector |
| `/cases/{case_id}` | historical init/valid period, lead, regime, RMSE, FSS and district summary |
| `/cases/{case_id}/rainfall` | 49×49 Raw GEFS, frozen M2 corrected and IMD observed arrays plus valid mask, mm/24h |
| `/cases/{case_id}/regime` | forecast-only Phase 2A pseudo-label probabilities and dominant regime |
| `/cases/{case_id}/probabilities` | calibrated heavy/very-heavy 49×49 probabilities in [0,1] |
| `/cases/{case_id}/fss` | per-case threshold/scale FSS with null/reasons |
| `/cases/{case_id}/districts` | area-overlap historical district product table |
| `/verification` | aggregate 2019 probability, P0 ensemble and FSS verification |
| `/geometry/districts` | frozen, hash-checked district GeoJSON with source/license metadata |
| `/demo-cases` | official historical example catalogue without internal artifact paths |
| `/model-comparison` | frozen Phase 2B M0–M4 held-out comparison, verified against its manifest hash |

Every per-case payload carries initialization UTC, product/lead, observation
valid period, corpus version, deterministic-model identity/hash, probability
selection freeze hash and API artifact-manifest hash. The 2019 observation map
is shown only in historical replay/verification, never presented as an
operational forecast input. The 2021 district geometry is served by the
versioned read-only `/geometry/districts` route for Phase 3A, with pinned
source, hash and ODbL attribution. The three Phase 3A contract extensions
serialize frozen artifacts only; they do not perform scientific computation.
Rainfall and probability payloads now expose target-cell centers, grid shape,
orientation, 0.25° cell size, extent, CRS and mask policy for lossless UI
rendering. These schema additions do not change any Phase 2B/2C arrays.

The original `/api/forecast`, `/api/metrics/*`, and `/api/sandbox/predict`
legacy scientific routes remain blocked with 409. Their historical Phase 0
readiness/lock is not revoked. New API readiness means only that validated
historical prototype artifacts are available for read-only demonstration; it
does **not** mean live forecast ingestion, current-date GEFS operations, or
production readiness. Model/corpus version are frozen to Phase 2B/1F/2A v2.

The original 2018/2019 metric JSONs contain a reporting-only categorical
cutoff field misnamed as rainfall millimeters. The versioned
`metric_semantics_supersession.json` preserves the original hashes and the
current API renders this as `decision_threshold_probability`. The numerical
metrics and frozen model choices are unchanged.
