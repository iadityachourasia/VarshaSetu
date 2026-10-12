# 2026 JJAS frozen-model forecast seal

Date: 2026-10-07. The complete sealed 2026 JJAS forecast-side corpus has now been passed through the **unchanged frozen Track B models** before any 2026 IMD observation pairing. This is a research forecast archive, not a verification, operational warning or claim of improved 2026 skill. The existing strict live worker, product default and scheduler were not changed.

The write-once protocol is `data/manifests/research_pilot/2026_frozen_inference_protocol_v1.json` (SHA-256 `5319253ab7da2a4a19034a80ddbc2e06dbbd9b7c1a7474bfca42bf75de56a4bf`). It pins the 2026 forecast-year seal, the previously frozen 2026 comparison protocol, the 2023-trained model readiness and selection records, the runner hash, the 50 GiB disk floor and the handling of incoherent probabilities. A single 2026-06-01 Day 1 forecast-only smoke run preceded this protocol and is disclosed in it; no observation or model selection was involved. The full prediction archive was generated only after the protocol was sealed.

`scripts/run_2026_frozen_inference.py` reverified each forecast-side case manifest, its feature arrays and all selected-message source receipts before inference. It generated immutable, hash-receipted local case directories under `data/processed/gefs_2026_frozen_inference_v1/`. For every strict-QC lead it stored Raw M0, linear MOS M1, global M2, hard-regime M3 and soft-regime M4 rainfall, plus the frozen 2024-fitted heavy/very-heavy probability outputs and three-class regime output. It did not fit, recalibrate, threshold-select, pair IMD, score skill or publish a live forecast.

The year seal is `data/manifests/research_pilot/2026_frozen_inference_year_v1.json` (SHA-256 `ef557185447aa4cc57770b2aa32e3ebb20b070eea0745a3f77eb72f546cf9b10`). It verifies all 122 source cycles and all prediction artifacts against the source-year population:

| Lead | Strict-QC predictions | Cases with P(very heavy) > P(heavy) | Affected cells |
|---|---:|---:|---:|
| Day 1 | 64 | 6 | 47 |
| Day 2 | 69 | 2 | 15 |
| Day 3 | 80 | 14 | 97 |
| **Total** | **213** | **22** | **159** |

The original unprojected probabilities are retained for audit. The 22 incoherent leads are explicitly marked **research-only, no warning use**; no cell was silently projected or masked, and no live publication gate was weakened. Even a lead with coherent ordering does not have established 2026 reliability. All five rainfall outputs were finite and nonnegative, and Raw M0 matched the sealed forecast input. A separate read-only recomputation compared all **1,704 output arrays** across all 213 leads bitwise with fresh frozen-model inference: all matched.

This locks predictions for a later same-case 2026 comparison. M2 remains the product default; M4 cannot be promoted without the prespecified heavy-CSI interval, RMSE and bias gates against M2. The 2026 IMD 03–03 UTC reference is not yet available locally, and the actual GEFS version transition plus comparability with the 2023 training version remain unresolved. No 2026 skill or reliability metric can be computed or claimed from this seal.
