# Phase 7A (P0-7): Coastal / orographic geographic-forcing protocol v1 — APPROVED for Stages 0–2 and frozen

Date: 2026-10-01. **Status: APPROVED (Stages 0–2 only) and frozen before any zone-level result was computed.** The machine-readable protocol is
`backend/app/evidence_data/phase6/coastal_orographic_protocol_v1.json`, SHA-256 **`76dbf44eddee318cef5975a46b1f8046434f1a61e1e738d91fbc12909de80714`** (LF bytes; `.gitattributes` marks `backend/app/evidence_data/**` as
`-text`). It is immutable: any changed rule needs a v2. Nothing has been acquired, computed from model output, or trained. The only data read while writing it were the
time-invariant IMD valid-cell footprint and the grid coordinates (§5). Values labelled *proposed* below were approved unchanged (§14).

## 1. Problem

SIH26080 lists a coastal / orographic rainfall regime next to active monsoon, break and low/depression. The project's three pseudo-regimes (`docs/54`) cover the
synoptic state only. No static terrain, land-mask or coastline field exists in the frozen feature schema (`FEATURE_REGISTRY` marks `elevation`,
`terrain_gradient`, `distance_to_coast` as `future_source_required`). The compliance page therefore shows the requirement as **PLANNED**, and it must stay
PLANNED until the evidence in §9 exists.

## 2. Design principle: geography is per cell, the synoptic regime is per case

An active monsoon day can also be an orographic day. The existing classifier assigns one label to a whole 49×49 case. A coastal or orographic influence differs
from cell to cell (a cell on the Ghats and a cell in the interior share the same synoptic state). Therefore geographic forcing is **not** added as a fourth class of
the flat taxonomy (that would mix two different things). It is a second, per-cell dimension, consistent with the hierarchical design in `docs/08` and `docs/34`:

```text
Head A  synoptic state        per case   Active | Break/Weak | Low/Depression      (existing, unchanged)
Head C  geographic forcing    per cell   static zone  x  forecast-time forcing strength   (this protocol)
```

Head A and the frozen models M0–M4 are **not modified** by this protocol.

## 3. Staged plan, with a decision gate after each stage

| Stage | What | Training? | New model? | Authorised by approving this document? |
|---|---|---|---|---|
| 0 | Acquire static geography into a versioned, hashed artifact (§6) | No | No | **Yes** (needs one small public download) |
| 1 | Static zones + verification of the **frozen** M0–M4 stratified by zone | No | No | **Yes** |
| 2 | Forecast-time forcing-strength strata from U850/V850/PWAT/Q700 and static geometry; same verification stratified | No (thresholds are tercile cut-points of the training year only) | No | **Yes** |
| 3 | A geography-aware correction (regime head fed into a model) | Yes | Yes (M5 lineage) | **No** — only after Stage 1–2 results, under its own protocol and approval |

The reason for staging: whether coastal and orographic cells are actually mishandled by the existing models is an empirical question that needs no new model to
answer. If Raw and M1–M4 behave the same in those zones, a geography-specific model is unjustified; if they do not, Stage 3 is justified and its design is informed by
real evidence rather than assumption.

## 4. Populations, labels and roles (no pooling across tracks)

| Track | Zone / threshold fitting | Development | Consumed final test (post-hoc only) |
|---|---|---|---|
| A (GEFSv12 reforecast) | 2017 | 2018 | 2019 — `POST-HOC EXPLORATORY ANALYSIS OF THE COMPLETED 2019 FINAL TEST` |
| B (operational GEFS) | 2023 | 2024 (already used for selection and calibration; development evidence only) | 2025 — `POST-HOC EXPLORATORY ANALYSIS OF THE COMPLETED 2025 FINAL TEST` |

Static zones depend on no year. Forcing-strength cut-points (Stage 2) are fitted on the training year only. No frozen model, threshold or selection is changed using
any result of this protocol; 2019 and 2025 are never used for selection or tuning and are never called untouched.

## 5. Observation-free feasibility counts (the only data inspected so far)

The valid-cell footprint is identical in every paired 2023 and 2024 case (checked on a sample of 25 cases per year): **1,301** land cells of the 49×49, 0.25° grid
(10–22°N, 68–80°E); 96 of them lie on the domain edge. Distance to the nearest non-footprint cell centre (a proxy for distance to the coast, to be replaced by the
frozen land mask in Stage 0) gives the following cell counts. They contain no rainfall value and no model output.

| Candidate coastal width | ≤ 30 km | ≤ 50 km | ≤ 75 km | ≤ 100 km | ≤ 150 km |
|---|---:|---:|---:|---:|---:|
| Valid cells (of 1,301) | 74 | 102 | 178 | 274 | 413 |

Caveats: the proxy is the IMD land footprint, not a land-sea mask; a footprint hole inside the domain would be counted as coast; cells next to the domain edge are not
coastal merely because the domain ends there. Orographic zone support cannot be counted until elevation exists (Stage 0).

## 6. Static sources (decision D4)

| Source | Resolution | Provenance | Strength | Weakness |
|---|---|---|---|---|
| **S1** surface orography and land fraction already inside the GEFS pgrb2 products used by the project | 0.5° (≈ 55 km) | Same lineage as the forecasts | Provenance-clean, tiny range fetch | Whether these fields exist in the exact products and are decodable is **unverified**; 0.5° smooths the Western Ghats (a narrow escarpment) |
| **S2** a public-domain global DEM (for example GMTED2010 or SRTM) aggregated to 0.25° | 0.25° target from ≈ 250 m–1 km | External, versioned | Resolves the Ghats much better; the grid used for verification | New external source; licence must be recorded at download; area-mean aggregation still smooths a narrow barrier |

**Recommendation:** S2 as the primary source (it matches the verification grid and resolves the barrier better), with S1 used only as a cross-check if a probe confirms
it is present. Whichever is approved, Stage 0 records the exact file, version, licence text, SHA-256 and the aggregation method (area-mean for elevation, majority for
the land mask). If the licence is not clearly permissive for redistribution of derived 0.25° values, **stop** and ask rather than proceeding.

Derived static fields (all frozen formulas): mean elevation; local relief (maximum minus minimum elevation in the 3×3 neighbourhood); terrain-gradient vector from the
elevation smoothed once with a 3×3 mean (declared); coast normal (gradient of the smoothed land fraction); distance to coast (great-circle distance from the cell centre
to the nearest ocean cell centre of the frozen land-sea mask).

## 7. Zone definitions (proposed values, freeze on approval)

Zones are static, rule-based and **not mutually exclusive**; every cell receives one of four labels, which the report keeps visible:

| Label | Proposed rule |
|---|---|
| `COASTAL` | valid cell with distance to coast ≤ **100 km** |
| `OROGRAPHIC` | valid cell with mean elevation ≥ **400 m** or local relief ≥ **300 m** |
| `COASTAL_AND_OROGRAPHIC` | both rules (the Western Ghats coast is expected to appear here) |
| `OTHER` | neither |

The widths and thresholds are meteorological judgement, not fitted: alternatives (50/75/150 km; 300/500 m) are listed with their counts in the frozen artifact as a
**sensitivity analysis only**; the primary zones are the proposed values above and are not reselected after seeing results. They need expert review; the project
should state plainly that they are a transparent rule-based convention, not a validated physical regime classification.

**Support gate (proposed):** a zone is reported with a metric only if it has ≥ 20 cells, ≥ 30 cases and ≥ 30 observed event cell-case pairs for that metric's
threshold; otherwise the report shows `insufficient_support` with the counts, never a number.

## 8. Stage 2: forecast-time forcing strength

For each cell and case, from forecast fields only (U850, V850, PWAT, Q700 and the static geometry):

- `onshore` = max(0, wind · coast-normal) for `COASTAL` cells; `cross_barrier` = max(0, wind · terrain-gradient direction) for `OROGRAPHIC` cells, using U850/V850
  bilinearly resampled from the 0.5° context grid to 0.25° (resampling method declared and frozen);
- `forcing = component × PWAT` (a moisture-flux proxy, declared as a proxy, not a measured moisture flux).

Strength strata are the lower, middle and upper terciles of `forcing` over the **training year's** cell-case pairs in that zone (cut-points saved in the artifact). No
rainfall, observation or target-derived value enters. A leakage test asserts that only static fields and forecast fields can reach the computation.

## 9. Pre-registered questions and decision rules

Models: the frozen M0 Raw, M1 Ridge MOS, M2 global XGBoost, M3 hard-regime, M4 soft-regime (Track B), and M0/M2/M3/M4 where Track A has frozen outputs. Metrics: RMSE, MAE,
bias, POD, FAR, CSI, ETS and 2-D FSS where the zone is spatially contiguous enough (otherwise FSS is not reported). Heavy and very-heavy IMD 24-hour categories. Uncertainty:
the paired whole-case bootstrap used throughout (seed 26080, optimistic because cells in a case are correlated), with the expected-by-chance share stated beside any count of
significant strata.

- **Q1** Do Raw and each model differ in bias or RMSE inside a zone compared with all cells?
- **Q2** Does the improvement over Raw (M1–M4) differ in a zone compared with all cells?
- **Q3** Within a zone, is Raw's heavy-rain frequency bias or the corrected model's skill different in the strong-forcing tercile than in the weak-forcing tercile?

**Decision rule (proposed):** a zone shows a *geographic gap* for a metric when the paired interval of (zone value − all-cell value) excludes zero in the development
year **and** the sign is the same in the consumed final-test year (post-hoc). Stage 3 is recommended only if at least one zone shows a gap for a metric that matters to the
PS (RMSE, heavy-event CSI or bias) on at least one track. If no gap is found, the honest result is "no evidence of a geography-specific deficiency in these models at
this resolution", and the requirement stays PARTIAL.

## 10. Effect on the PS coverage status

| Evidence available | Coverage status shown on `/compliance` |
|---|---|
| Today | PLANNED |
| Stage 1–2 complete (zones, stratified verification, no regime-aware model) | **PARTIAL**, described as "rule-based geographic zones with stratified verification; no coastal/orographic specialist model" |
| Stage 3 complete and the geography-aware model beats the appropriate non-regime baseline on held-out data under its own protocol | IMPLEMENTED (only then) |

Zones are always named "rule-based geographic-forcing zone"; they are never called a learned, validated or official regime.

## 11. Leakage and registry policy

Static geography is allowed at forecast time (`AGENTS.md` §3.4). The existing `FEATURE_REGISTRY` v1 is not edited: acquired static fields enter a **new versioned
registry** and, in Stages 0–2, are used only for stratification and forcing diagnostics, not as model inputs. Nothing derived from rainfall or IMD values defines a zone
or a stratum. The one observation-derived input is the time-invariant IMD footprint (the set of cells), and only until the frozen land-sea mask replaces it.

## 12. Stage 0 deliverables and stop conditions

Deliverable: `static_geography_v1` (NPY arrays, manifest and SHA-256 sidecar, a few MB), the licence text, QA maps of elevation, land-sea mask, distance to coast and zones,
and observation-free zone cell counts. Hash-pinned and tracked under `backend/app/evidence_data/` only if small and the licence allows redistribution.

Stop if: the licence does not permit the intended use; the aggregated field misaligns with the 49×49 grid (a registration check against the footprint is part of the QA);
the land-sea mask disagrees materially with the IMD footprint over the coast; any zone has fewer than 20 cells; or any step would need a frozen model or threshold to change.

## 13. Limitations (to be repeated in every report)

- 0.25° (≈ 28 km) cannot resolve a narrow escarpment or a coastal convergence band; a null result is a statement about this resolution, not about the physics.
- Coastal and orographic zones overlap with the Low/Depression synoptic state; stratified results are therefore also reported jointly by synoptic regime where support allows,
  and a gap attributed to geography may partly be synoptic.
- Many strata × models × thresholds invite false positives; expected-by-chance counts accompany every claim.
- Track A and Track B are never pooled; 2024 is development evidence only; 2019 and 2025 results are post-hoc analyses of consumed holdouts.
- Historical replay only; no operational claim follows.

## 14. Decisions taken (2026-10-01)

1. **D4** static source: **S2 public-domain DEM aggregated to 0.25°** as primary; GEFS ancillary fields only as an optional cross-check if a probe confirms them.
2. Zone rules: **as proposed** (coastal ≤ 100 km; orographic mean elevation ≥ 400 m or local relief ≥ 300 m); alternatives are sensitivity analysis only.
3. Scope: **Stages 0–2 only**; Stage 3 needs its own protocol and approval.
4. Download: approved in principle for Stage 0; the exact DEM file, source, size and licence will be stated and confirmed before any download.
5. Commit policy: local commits, no push.

## 15. Amendments during Stage 0 (v1 stays on file unchanged)

Both amendments were triggered by quality checks on the static geography, before any rainfall value, model output or skill result had been looked at, and both were approved by the project owner.

| Version | SHA-256 | Change | Why |
|---|---|---|---|
| v1 | `76dbf44e…0714` | original | — |
| v2 | `650e5c75d1d07b286a08c27d32596d189cdae7ae04e03398f5ac05e65fae8204` | Land cell = terrain land majority **or** IMD footprint cell; elevation of a footprint cell with no land pixel is undefined, never 0 m | The terrain file stores ocean as 0 m; 48 coastal footprint cells (11 with no land pixel above 0 m) would have been classed as ocean and mis-zoned as OTHER |
| v3 | `a9ff78173ddb6026e6b297c2da2128dde2fdcf825ae8b0c368c5f5fa79d199fd` | Orographic = local relief ≥ 300 m only (the mean-elevation ≥ 400 m test is dropped from the primary rule and kept as a superseded sensitivity count) | The v2 rule marked 824 of 1,301 land cells as orographic; 471 of them satisfied only the elevation test and were mostly plateau (the Deccan), not a barrier |

Coastal rule, support gate, scope, forcing-strength definition, populations, metrics and the decision rule are unchanged. The Stage 0 record is `docs/116`.

Gate: `P0_7_PROTOCOL_APPROVED_FROZEN` (v1), amended to v3; see `docs/116` for Stage 0 completion.
