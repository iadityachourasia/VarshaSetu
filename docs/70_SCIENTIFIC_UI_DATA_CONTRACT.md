# Phase 3A Scientific UI Data Contract

The 2019 UI consumes frozen Phase 2B/2C `GET /api/science` endpoints.
The Overview separately reads the historical operational-era 2025 case
index and a hash-pinned 2025 final-test summary. It never invokes legacy
`/api/forecast`, `/api/metrics/*` or prediction routes.
The browser calls same-origin paths through the Next rewrite; runtime JSON
is checked with Zod in `frontend-v2/src/lib/api/science.ts`.

| UI | Endpoints | Required meaning |
|---|---|---|
| Overview | `/status`, `/model-comparison`, `/verification`, `/demo-cases` | 2019 9.73% is computed from M0 and M2 RMSE returned by API |
| Forecast Explorer | `/cases`, `/demo-cases`, `/cases/{id}`, `/rainfall`, `/regime`, `/fss`, `/geometry/districts` | three paired fields use one mask, grid and rainfall legend |
| Extreme Rain | `/cases`, `/demo-cases`, `/probabilities`, `/rainfall`, `/geometry/districts`, `/verification` | event probability is not deterministic rainfall; IMD used only in historical verification |
| District Intelligence | `/cases`, `/demo-cases`, `/districts`, `/geometry/districts` | actual area-overlap product; polygon source and license shown |
| Verification | `/model-comparison`, `/verification` | M0–M4 same paired deterministic population; FSS raw/corrected denominator case counts are shown separately |
| Methodology | `/status` | source, split, limitations and hashes |

The rainfall API includes `raw`, `corrected`, `observed`, `valid_mask`,
`unit=mm/24h`, and `grid`. The probability API includes separate Heavy and
Very Heavy matrices, thresholds, and the same grid orientation. Null/masked
values remain absent on maps; they are not converted to zeros. Selection
uses manifest-allow-listed case IDs. Links preserve a valid case query
parameter between exploration views. Advanced provenance shows corpus,
model and manifest identity, never a local absolute path.

The Overview also reads the existing 2019 `/cases` response and the
complete 2025 `/operational/2025/cases?page_size=400` index for its charts.
The latter contains 375 scheduled cases, of which exactly 232 are
deterministic-source eligible for the frozen final test. Each series
requires the correct year, complete population, unique case IDs, valid
dates, nonnegative paired RMSE, and matching lineage or final-test role.
Because all frozen 2025 cases have 1,301 paired cells, the root mean of
their squared case RMSE must also reproduce both pinned aggregate RMSE
values within numerical tolerance. Optional 2019 verification and demo
counts render only when their manifest identity matches the 2019 status.
The plotted values are unsmoothed and ordered by forecast initialization
date. A line segment joins separate case points only; it is not a
continuous rainfall trend. If validation fails, only sourced aggregate
RMSE bars appear with an unavailable-series label.

The 2019 headline is calculated from M0/M2 API RMSE when the read-only API
responds. If a required 2019 request fails at the transport layer, Overview
uses `frontend-v2/src/lib/benchmarks/reforecast-2019-overview.json`, generated
by `frontend-v2/scripts/build-overview-2019-snapshot.py` from the same frozen
Phase 2B/2C result artifacts. The generator checks the Phase 2C manifest and
both result-file hashes; frontend tests recompute the hashes and compare every
snapshot case to the source. The page labels this as a verified frozen snapshot.
HTTP errors, schema failures, source-manifest conflicts, and invalid series
do not activate or silently change this fallback. The snapshot supplies only
the homepage benchmark and case RMSE chart; other 2019 evidence remains
unavailable if its API response is missing.

The 2025 primary
headline is the frozen preselected M1 Ridge result from
`FINAL_TEST_RESULT.json` (SHA-256
`04a7fc2a434d24449365e2cb9978cbc8584f5cc87ea4f132cfaf6e7fc7a4abca`).
The 2025 Heavy and Very Heavy BSS and FAR shown on Overview come from that
same pinned source, with the frozen probability cutoffs, 2023 prevalence
reference, and displayed high false-alarm ratios. Detailed reliability
limitations remain on the linked Verification view. The two experiments are not
pooled. Missing 2019 API evidence renders unavailable without hiding the
independent 2025 frozen result. The hero and three image-backed navigation
cards use decorative artwork and do not encode forecast or verification data.

The compact six-card 2025 evidence row preserves source scope: the pinned
M1 RMSE reduction, Raw-better extreme FSS, pinned Heavy/Very Heavy BSS and
cutoff FAR, the frozen M4/M3/M2 RMSE ordering, and NOAA/IMD provenance.
The slim linked caveat keeps the two GEFS lineages separate and points to
Verification. Tile icons are decorative and do not encode scientific values.

M2 Global XGBoost is the frozen primary deterministic product. Regime
probabilities are forecast-only pseudo-label classifier outputs, not
independently verified meteorological accuracy. The UI must not imply
that M3 or M4 beat M2, or that M2 improves heavy-event CSI/ETS/FSS.
Reliability upper bins with no samples are explicitly undefined.
