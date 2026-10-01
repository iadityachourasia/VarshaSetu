# Phase 6C (P0-5) — District-level verification protocol v1 (APPROVED, frozen before any result)

## 1. Status

Approved by the project owner on the decisions in §6, **before any district-level skill score was computed**. The machine-readable protocol is
`backend/app/evidence_data/phase6/district_verification_protocol_v1.json`, SHA-256 **`9b348063a6ac654e88a822694fd199d2f432d5d6b0bebafc19567f6be6e53365`**
(LF bytes; `.gitattributes` marks `backend/app/evidence_data/**` as `-text` so no checkout can alter the hashed bytes). It is immutable: any changed rule needs a new version.
The only data read to inform it were **IMD observations and the valid-cell mask** (no model value).

## 2. Why a protocol first

A district "event" needs a definition and enough support to report a number. Different definitions give very different answers and sample sizes, so the choice
had to be made blind to model performance.

## 3. Observation-only support counts (after the approved ≥ 5 valid-cell rule)

188 districts; **169 kept, 19 excluded** (median < 5 valid IMD land cells in both years). Every paired case has the same 1,301 valid cells, so a district's valid-cell
count is constant across cases and the pair rule equals the district rule. Median valid cells per kept district: 14.

| Year | Cases | District-case pairs | Heavy ≥ 64.5 mm: E1 any cell / E2 ≥ 25 % area / E3 district mean — event pairs (districts with ≥ 30 events) | Very heavy ≥ 115.6 mm: E1 / E2 / E3 |
|---|---|---|---|---|
| 2024 | 183 | 30,927 | 3,227 (34) / 1,132 (10) / 738 (6) | 1,106 (10) / 311 (0) / 155 (0) |
| 2025 | 232 | 39,208 | 3,845 (38) / 1,229 (12) / 678 (5) | 1,117 (11) / 239 (0) / 106 (0) |

Pooled skill is estimable for every definition; per-district skill is estimable for about 34–38 districts (heavy, E1), 10–12 (heavy, E2) and 10–11 (very heavy, E1 only).

## 4. The protocol

- **Unit:** district-case pair. **Fields:** frozen Raw/M1–M4 and IMD on paired valid cells with the Phase 2C weights (docs/107, 111). Included pair: ≥ 5 valid cells.
- **Continuous:** area-weighted district mean; RMSE, MAE, bias pooled; per district only with ≥ 30 included cases.
- **Events (64.5 / 115.6 mm per 24 h, inclusive, the identical rule applied to the model and to IMD on the same cells):** **E1 any valid cell ≥ threshold (primary)**; E2 ≥ 25 % of the district's valid area ≥ threshold (secondary); E3 district mean ≥ threshold (sensitivity; pooled only).
- **Categorical:** POD, FAR, CSI, ETS, counts and the forecast/observed ratio, pooled; undefined stays undefined. Per district (E1 and E2) only where the district has ≥ 30 **observed** events under that definition and threshold; otherwise `insufficient_support`.
- **Paired comparisons:** M1–M4 vs Raw, M3 vs M2, M4 vs M2, M3 vs M4. Improvement per district-case = |Raw err| − |model err| of the district mean; a district is *improved / worsened* when its mean improvement is > 0 / < 0 **and** the 95 % paired whole-case bootstrap interval excludes 0, else *indeterminate*. With a two-sided 95 % interval about 5 % of tested districts in total (≈ 2.5 % per direction) are classified improved or worsened by chance, so counts are reported beside that expected number.
- **Breakdowns:** lead day; forecast-only pseudo-regime; latitude band (10–14, 14–18, 18–22 °N of the district centroid clipped to the domain).
- **Labels:** 2024 = development evidence; 2025 = `POST-HOC EXPLORATORY ANALYSIS OF THE COMPLETED 2025 FINAL TEST`. Never pooled with Track A.
- **Reproduction gate:** the builder must reproduce the support counts above exactly, district means must equal means recomputed from the already-served grids, pooled Raw district RMSE must equal an independent loop, and per-district observed events must sum to the pooled count.

## 5. Why E1 is primary

E1 retains the most events and is closest to point-event warning language; its dependence on the number of valid cells is limited by the 5-cell rule and by comparing every model with Raw within the same district-case pair. E2 is more spatially meaningful but thin (10–12 supported districts for heavy rain, none for very heavy), so it is reported as secondary rather than hidden.

## 6. Decisions taken

1. Primary event definition: **E1 any cell** (as proposed).
2. Minimum observed events per district for a per-district score: **30** (as proposed).
3. Coverage rule: **≥ 5 valid cells** (stricter than the proposed 3).
4. Regional grouping: **three latitude bands** (as proposed).
5. Commit policy: keep working; nothing committed yet.

## 7. Known limitations

- District-case pairs inside one case are spatially correlated and consecutive days are serially correlated; bootstrap intervals are optimistic; testing ~170 districts invites false positives (hence the expected-by-chance counts).
- IMD land cells only; coastal and border districts have few cells; geometry is simplified (docs/65, 107).
- Pseudo-regime breakdowns inherit docs/108–110 caveats. 2025 is a consumed holdout. District verification of historical replay is not an assessment of warning skill.

Gate: `P0_5_PROTOCOL_APPROVED_FROZEN`. Execution and results: `docs/113`.
