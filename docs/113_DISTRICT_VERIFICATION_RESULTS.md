# Phase 6C (P0-5) — District-level verification: execution and results (protocol v1)

## 1. Status

Executed under the approved, hash-frozen protocol (`docs/112`, SHA-256 `9b348063a6ac654e88a822694fd199d2f432d5d6b0bebafc19567f6be6e53365`).
No definition, threshold, support rule or grouping was changed after results existed. Read-only re-aggregation of frozen predictions with the pinned Phase 2C
district weights — nothing was trained, tuned or selected. 2024 is development evidence; 2025 is `POST-HOC EXPLORATORY ANALYSIS OF THE COMPLETED 2025 FINAL TEST`.

## 2. What was built

| Piece | Detail |
|---|---|
| `backend/app/ml/district_verification.py` | pure statistics: per-case district stats (means, area fractions, any-cell flags), pooled/lead/regime/region categorical and continuous scores for E1/E2/E3, paired whole-case bootstrap contrasts, per-district improvement with interval and status, support gating |
| `scripts/build_phase6_district_verification.py` | refuses any protocol hash other than the approved one; writes `district_verification_B_{2024,2025}.json` (~0.7 MB each) and a hash manifest under `backend/app/evidence_data/phase6/`, write-once |
| **Reproduction gate (14 checks per year, all passed)** | protocol's pre-registered support counts reproduced exactly (pairs, kept districts, E1/E2/E3 events at both thresholds); per-district observed events sum to the pooled count; district means for a sample of 8 cases × all districts × all models equal means recomputed from the already-served 49×49 grids (< 1e-3 mm); pooled Raw RMSE equals an independent per-pair loop |
| API | `GET /api/science/evidence/district-verification?year=` and `…/report?year=&format=md\|csv\|json`; manifest, protocol and file hashes verified (503 on tamper), evidence role must be registered, mandatory label |
| UI | Verification Lab → Track B → **District-level** tab: pooled error, paired contrasts, event tables (definition × threshold × metric × breakdown), improved/worsened counts with expected-by-chance, diverging improvement map, support-gated per-district table, exclusions, downloads; the Districts page links to it |
| Repo hygiene | `.gitattributes` marks `backend/app/evidence_data/**` as `-text` so checkout cannot alter hashed bytes (this machine has `core.autocrlf=true`) |

## 3. Results (169 of 188 districts; 2024: 183 cases, 30,927 pairs; 2025: 232 cases, 39,208 pairs)

### Pooled district-mean error (mm/24 h)

| Year | Metric | Raw | M1 | M2 | M3 | M4 |
|---|---|---|---|---|---|---|
| 2024 | RMSE | 14.72 | 14.59 | 14.64 | 15.17 | 15.03 |
| 2024 | MAE | **7.21** | 8.02 | 7.94 | 8.47 | 8.43 |
| 2024 | Bias | −1.29 | +0.85 | +1.91 | +2.87 | +2.91 |
| 2025 | RMSE | 13.50 | 13.10 | **12.62** | 13.03 | 12.81 |
| 2025 | MAE | 6.71 | 6.65 | **6.45** | 7.05 | 6.97 |
| 2025 | Bias | −1.59 | −1.57 | −1.10 | +0.09 | +0.18 |

### District events, E1 any valid cell (primary), pooled CSI [95 % interval of the paired difference]

| Threshold | Year | Raw | M1 | M2 | M3 | M4 | M3 − Raw | M3 − M2 |
|---|---|---|---|---|---|---|---|---|
| Heavy ≥ 64.5 mm | 2024 | .110 | .039 | .238 | .265 | .260 | +.155 [.116, .191] | +.027 [.008, .048] |
| Heavy ≥ 64.5 mm | 2025 | .067 | .026 | .067 | .102 | .095 | +.035 [.010, .058] | +.035 [.016, .055] |
| Very heavy ≥ 115.6 mm | 2024 | .027 | .010 | .059 | .077 | .067 | | |
| Very heavy ≥ 115.6 mm | 2025 | .021 | .009 | .001 | .016 | .010 | | |

(observed E1 events: heavy 3,227 / 3,845; very heavy 1,106 / 1,117.) M1 − Raw heavy CSI: −.071 (2024) and −.042 (2025), intervals exclude 0. M2 − Raw: +.128 (2024) but −.0001 [−.025, +.024] (2025).
E2 and E3 give the same broad ordering for heavy rain (M3 or M4 > M2 > Raw > M1 in both years; M3 is ahead of M4 in every case except E3 in 2024, where M4 is marginally ahead); very-heavy E2/E3 rest on 106–311 events, M2 forecasts essentially none in 2025.

### Where the heavy-rain gain sits (E1 heavy CSI, Raw / M2 / M3 / M4)

| Year | Active | Break/Weak | Low/Depression | 10–14 °N | 14–18 °N | 18–22 °N |
|---|---|---|---|---|---|---|
| 2024 | .090 / .046 / .059 / .059 | .083 / 0 / 0 / 0 | .122 / .332 / .364 / .358 | .086 / .163 / .183 / .177 | .117 / .345 / .367 / .358 | .120 / .216 / .252 / .248 |
| 2025 | .045 / .043 / .029 / .031 | .054 / 0 / 0 / 0 | .106 / .132 / .244 / .222 | .032 / .026 / .069 / .065 | .028 / .095 / .121 / .106 | **.108** / .069 / .105 / .101 |

### Districts improved / worsened versus Raw on the district mean (169 tested; ≈ 8.5 expected by chance in total, ≈ 4.2 per direction)

| Year | M1 improved / worsened | M2 | M3 | M4 |
|---|---|---|---|---|
| 2024 | 32 / 89 | 18 / 73 | 16 / 97 | 17 / 97 |
| 2025 | 69 / 38 | 52 / 22 | 19 / 52 | 24 / 50 |

Districts with per-district event scores (≥ 30 observed events): E1 heavy 34 (2024) / 38 (2025); E1 very heavy 10 / 11; E2 heavy 10 / 12; E2 very heavy 0 / 0.

## 4. What the district-level evidence says (and does not)

1. **Event detection and mean error disagree, as at grid level.** M3/M4 detect district heavy-rain events better than Raw in both years (intervals exclude 0), while their district-mean absolute error is **worse** than Raw in both years (continuous contrasts: M3 vs Raw −1.25 mm in 2024, −0.34 mm in 2025) and they carry a positive bias (up to +2.9 mm in 2024). The regime-aware gain is event-specific, not a general accuracy gain.
2. **The gain is regime- and region-specific.** It sits in the Low/Depression pseudo-regime and in the southern/central latitude bands; in the Active regime it is absent, in Break/Weak all corrected models score 0, and in the northernmost band in 2025 Raw is as good as M3.
3. **It does not extend to very heavy rain.** 2025 very-heavy E1 CSI: Raw .021 > M3 .016 > M4 .010 > M1 .009 > M2 .001.
4. **District improvement is mixed and year-dependent.** In 2024 most tested districts are *worsened* for every corrected model on the district mean (89–97 of 169); in 2025 M1 and M2 improve more districts than they worsen (69/38, 52/22) while M3/M4 worsen more than they improve (50–52 vs 19–24). Counts far exceed the ≈ 8.5 expected by chance, so these are not chance artefacts, but they remain optimistic-interval, single-season results.
5. **M1 (the pre-registered 2025 primary) improves 2025 district-mean error in 69 districts and worsens 38, yet loses to Raw on district event CSI in both years.** This repeats the grid-level finding that lower mean error does not imply better extreme-event detection.

## 5. Limitations

- Optimistic intervals (serial and spatial correlation); ~170 districts tested; per-district scores only where support rules are met; very-heavy results rest on ≈ 100–1,100 events.
- IMD land cells only; 19 coastal/border districts with fewer than 5 valid cells are excluded; geometry is simplified; this is aggregate verification of historical replay, not warning skill.
- 2025 is a consumed holdout (post-hoc, no selection); pseudo-regimes are forecast-only labels; one season per result; not pooled with Track A.
- Track A has no district verification (no per-case Track A district corpus exists for M3/M4).
- Numeric details above are quoted from the served evidence files; the files are the authority.

## 6. Regression

Backend suite: 272 passed, 14 errors (all the known Windows `tmp_path` permission error, `docs/101`). Full Playwright, one worker, `next start` and the real backend: **81 passed, 1 failed** - the pre-existing `demo-flow.spec.ts:4` Overview strict-locator failure (`"9.73%"` in two elements since the Overview redesign; identical on the pre-Phase-4N code, `docs/107` §7). New: 6 specs in `district-verification.spec.ts`, all passing; Vitest 105/105; `tsc` and `eslint` clean.

## 7. Reproduce

```bash
python scripts/build_phase6_district_verification.py   # ~15 s, CPU; aborts if the protocol hash differs or any output would change
python -m pytest backend/tests/test_district_verification.py backend/tests/test_evidence.py -q
```

Gate: `P0_5_DISTRICT_VERIFICATION_COMPLETE` (post-hoc/descriptive; no model selection).
