# 2026 verification scorer and research-pilot closeout

Date: 2026-10-07. Scope: local evaluator-ready **research pilot**, not a public warning service. This note closes the implementation that can be completed without a 2026 observation file, an authoritative GEFS transition review, or outside expert annotations. It does not turn those missing inputs into scientific passes.

## Frozen one-shot 2026 verification

The 122-cycle 2026 JJAS forecast archive contains 213 strict-QC Day 1–3 leads and was sealed before any 2026 IMD observation pairing (`156_GEFS_2026_FROZEN_INFERENCE_SEAL.md`). The score protocol is `data/manifests/research_pilot/2026_track_b_score_protocol_v1.json`, SHA-256 `e3ce114a91036bb5ffbe937c49b2dbf347a6594840735a13f6564f7f3b987d84`. It pins the forecast archive, model selection, comparison rule, bootstrap, scorer code and observation requirements. Changes to a pinned input require a new version and disclosure before pairing; editing this protocol in place would invalidate its seal.

`scripts/score_2026_frozen_inference.py --preflight` reads manifests and file metadata only. Its 7 October result was:

```json
{"forecast_cases":213,"observation_read":false,"reasons":["IMD_2026_REFERENCE_CLEARANCE_MISSING","GEFS_2026_VERSION_REVIEW_MISSING"],"status":"BLOCKED_BEFORE_OBSERVATION_READ"}
```

An attempted `--score` refused at that preflight gate, before constructing the IMD reader or writing a result. **No 2026 IMD values were read or scored.** The earlier team attestation and local prior-use audit remain a provisional independence check, not a substitute for a source file or scientific review.

When both external reviews are recorded in sealed clearance manifests, the one-shot runner will hash-check the IMD file, verify every frozen forecast case, pair the 03–03 UTC daily grids on a shared valid-cell mask, and write one immutable score. It compares Raw M0, MOS M1, global M2, hard-regime M3 and soft-regime M4 on identical cells. It reports RMSE, bias, heavy and very-heavy contingency scores, FSS at four neighbourhood scales, lead and announced-boundary strata, and a date-block bootstrap for the frozen M4-versus-M2 heavy-rain CSI comparison. Frozen promotion gates also require event support, RMSE and bias. The runner never promotes a model automatically. The boundary strata are based on an **announced** change and cannot establish actual model equivalence.

The frozen 2026 probability pair violates P(very heavy) ≤ P(heavy) on 22 leads (159 cells). The scorer retains these leads for deterministic M0–M4 comparison and excludes the **entire lead** from probability reliability/Brier reporting. Coherent leads are still research-only until independently checked for reliability. This exclusion is a disclosed probability-quality rule, not outcome-based filtering.

## Status of the five requested advances

| Advance | Evidence now available | Open scientific or release gate |
|---|---|---|
| Regime evidence | Forecast-time detectors, objective active/break checks, and a blinded 72-case review packet | Independent expert/bulletin labels; a winter corpus for western disturbances. Forecast-regime labels must not be called expert truth. |
| Regime-conditioned correction | Fair development comparison completed; the new residual arm did not beat the strongest matched global control; frozen M2 remains default | A future independent-year result may test the prespecified M3/M4 comparison, but cannot retroactively validate the failed residual arm. |
| Heavy/very-heavy probabilities | Frozen probability bundle, order diagnostic, coherent research-only projection, lead-aware calibration and no-refit transport tests | 2026 reliability is unmeasured; 22 frozen leads are incoherent; June 2024 very-heavy Brier skill and warning frequency failed promotion. No warning-use claim. |
| New-cycle operation | Forecast-only 2026 archive, hash-verified live worker, local scheduler, read-only API and district output | New-cycle inference is not measured skill. October–May is outside the declared JJAS scope. Public operation needs governance and later reference-based verification. |
| India-wide product | Whole-India Raw GEFS reference verification by region; corrected regional pipeline and partial-grid development diagnostics | No India-wide corrected-model skill or official district-boundary claim. Extend in stages with same-case support, geometry and rights review. |

## What would close the remaining gates

1. Obtain the complete 2026 IMD 0.25° daily file through an authorized route; record source receipt, local-use/redistribution decision, 03–03 UTC semantics and SHA-256 in `2026_imd_reference_clearance_v1.json`. A 200 response with zero bytes is **not** a reference file.
2. Obtain authoritative evidence of the actual 2026 GEFS implementation transition and review comparability to the 2023 training version. Seal `2026_gefs_version_clearance_v1.json`; the announced-calendar partition alone is insufficient.
3. Run the frozen scorer **once** after both clearances, then review all promotion gates, lead/regime/region evidence, event support and reliability. Any score remains an experimental research result until forecaster governance approves use.
4. Get blinded expert/bulletin regime annotations and a separate winter corpus. Develop an India-wide corrected model only after regional same-case coverage and event support pass. NCMRWF adapter evaluation remains contingent on authorized grids and terms.

## Verification completed on 7 October

- Backend suite: **780 passed**, with a repository-local pytest temporary directory and local socket access on Windows.
- Dedicated scorer tests: **4 passed**, covering same-cell metrics and probability exclusion, duplicate/order refusal, NetCDF date/missing handling, and blocked scoring before observation access.
- Frontend: TypeScript, ESLint, **212 Vitest tests in 31 files**, and optimized production build passed. The first Vitest attempt had sandbox temporary-file failures; a workspace-local temp directory resolved them. The first build attempt hit a Windows sandbox path-canonicalization denial; the filesystem-enabled retry passed.
- `git diff --check` returned no whitespace errors. Earlier sealed-forecast verification bitwise reproduced all **1,704** stored output arrays; this is an inference reproducibility check, not a 2026 skill score.

The code and evidence have not been committed. Existing working-tree changes from the wider research-pilot implementation are preserved for review.
