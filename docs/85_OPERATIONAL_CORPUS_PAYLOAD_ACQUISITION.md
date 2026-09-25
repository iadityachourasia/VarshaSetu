# Phase 4F — 2023–2025 operational GEFS selected-payload acquisition

Status: **`CORPUS_SOURCE_LAYER_PARTIAL`**. All selected payloads, decoded metadata and actual cross-year structural signatures are valid, and the 2025 forecast-only holdout remains sealed. Canonical rainfall QC admits only a documented subset; Phase 4F is not a feature, model, forecast-skill, or operational-readiness result.

## 1. Executive Summary

The frozen Phase 4E manifest contains 36,750 selected GRIB2 messages across 375 initializations and 1,125 date×lead cases. Acquisition was staged 2023, then 2024, then 2025 forecast inputs. **36,750/36,750** payloads are hash-verified and decoded metadata-valid; all actual structural signatures are compatible across years. Yet unchanged rainfall QC yields only **615/1,125** c00 source-eligible and **218/1,125** full-five-member source-eligible cases, so the decision is a **partial** source layer. Every scheduled case stays in the denominator, including rainfall-QC failures. No IMD observation, model inference or 2025 outcome was used.

## 2. Frozen Protocol

Dataset `operational_gefs_imd_2023_2025_v1`; unchanged [Phase 4D protocol](../experiments/recent_historical/operational_corpus_protocol_v1/protocol.json), SHA-256 `235f53a10a013de0e8a94eb07f7526f22ac0b624b1bbbb5473c872bf628c2c47`. The feature contract, lead schedule, source variables and source-level QC rule were not amended. This run does **not** open IMD observations.

## 3. Phase 4E Acquisition Manifest

The frozen [selected-range manifest](../experiments/recent_historical/phase4e_source_inventory_v1/planned_acquisition_manifest.jsonl), SHA-256 `4264225ad4845c26de320a05fbb14439a950dfffbdf3fd380964743c048f9e6a`, has 12,250 messages/year, 30,000 rainfall and 6,750 atmosphere overall. Planned lengths total 10,485,487,577 bytes: 2023 3,482,695,607; 2024 3,457,571,377; 2025 3,545,220,593. The Phase 4E 64,610-file closed-set manifest was verified before download. No extra date, member, field, cycle, lead, or range was admitted.

## 4. Acquisition Method

The [isolated Phase 4F pipeline](../experiments/recent_historical/phase4f_payload_acquisition_v1/README.md) fetches exact NOAA selected ranges via HTTP 206 only, validates `Content-Range`, length and GRIB envelope, computes SHA-256, then commits raw payload and receipt through a recoverable atomic transaction. Completed raw/receipt pairs are verified before reuse. Raw messages reside under `data/operational_gefs/v1/{year}`; metadata, QC arrays, ledgers, logs and manifests remain separately versioned. One date's 98 unique messages are decoded once and reused across its three lead products where applicable. No whole-object fallback exists.

## 5. Concurrency Selection

The Phase 4F I/O benchmark used fresh 2023 dates at four, six and eight workers. Four workers on June 1 achieved 2.02 MiB/s; six fresh workers on June 3 achieved 2.35 MiB/s; eight fresh workers on June 4 achieved 3.07 MiB/s. All 98 selected messages/date passed source and metadata validation and the pilot dates had no HTTP retries or throttling. Eight bounded I/O threads were chosen; Phase 1 frozen worker settings were not changed. Decode/QC remains sequential per date without nested oversubscription. Pilot results do not guarantee sustained network throughput.

## 6. Network Performance

The [year reports](../experiments/recent_historical/phase4f_payload_acquisition_v1/checkpoints/) record transferred bytes, measured download seconds, aggregate selected-byte MiB/s, retryable attempts, initial final failures, cache reuse and per-date logs. Retries are counted separately from distinct selected messages. Sustained HTTP keep-alive connections were sometimes closed remotely during the decode gap; recoverable attempts are retained in receipts. Measured selected-byte rates were 2.99 MiB/s (2023), 2.03 MiB/s (2024) and 1.50 MiB/s (2025), including transient network waits. Total network bytes were **10,402,238,894**, versus 10,485,487,577 final verified raw bytes; 288 exact/hash-matching messages were reused from protected caches. These are selected-payload rates, not whole-object or end-to-end season throughput.

## 7. 2023 Acquisition

125/125 dates were checkpointed. The year manifest verified 12,250/12,250 raw selected messages and 12,250/12,250 metadata records; its 28,335 listed artifacts passed a second SHA-256 verification. Source failure count was zero. Under unchanged QC, c00 passed 200/375, full five-member rainfall passed 76/375, and all 375/375 atmospheric case inputs passed. The year report remains the machine-readable source for exact lead/member counts and resource measurements.

## 8. 2024 Acquisition

125/125 dates were checkpointed. The year manifest verified 12,250/12,250 raw selected messages and 12,250/12,250 metadata records; its 28,351 listed artifacts passed a second SHA-256 verification. Source failure count was zero. Under unchanged QC, c00 passed 183/375, full five-member rainfall passed 67/375, and all 375/375 atmospheric case inputs passed. The 2023 and 2024 decoded structural-signature sets are identical. The protected Phase 4B July 18–24 Day-1 overlap reproduced **21/35** accepted member-products under the unchanged canonical QC; Phase 4F also includes Days 2–3 and therefore has a different full-week denominator. A total of 276 messages were copied from exact-object/range/hash-verified protected caches, without changing their originals.

## 9. 2025 Forecast Acquisition

125/125 forecast dates were checkpointed. The year manifest verified **12,250/12,250** selected raw messages and decoded metadata records; 28,383 listed artifacts passed a second SHA-256 verification. Two initially exhausted selected-range retries (June 3 `u850` f024 and August 6 c00 rainfall f042) were recovered individually from the same frozen manifest. Their partial metadata/checkpoints and failure histories remain in `recovery/` and `failures/`; 27 and 21 previously accepted array hashes respectively were preserved across those two-date re-QC runs. There are zero unrecovered source messages. Under unchanged QC, c00 passed **232/375**, full five-member rainfall passed **75/375**, and atmosphere passed **375/375**. No 2025 IMD value or model-performance outcome is part of this stage.

## 10. Payload Integrity

Each verified selected payload has source object, byte start/end, manifest index SHA-256, expected and actual length, local raw relative path, retrieval/reuse time, attempt history and SHA-256 receipt. Raw selected messages are never decoded scientifically before a matching verified receipt exists. The year manifest includes each raw file and receipt; verified raw evidence is not deleted on QC failure.

## 11. GRIB Metadata Validation

Every selected message is checked against its Phase 4E index row for parameter/level, cycle, forecast hour, member, family and accumulation/valid-time semantics. Decoded edition, product/grid/data-representation templates, native grid, units, scan direction, packing and missing-value keys are retained. A mismatch is `PAYLOAD_METADATA_MISMATCH` and stops affected scientific processing as `PROTOCOL_V1_PAYLOAD_INCOMPATIBILITY`.

## 12. Cross-Year Payload Compatibility

The actual decoded structural-signature sets are identical across 2023, 2024 and 2025: seven field signatures/year, with no first affected initialization or protocol-breaking grid/template/units/accumulation discontinuity. This is stronger than the Phase 4E `.idx`-text continuity claim. Rainfall uses GRIB2 product template 11; instant atmosphere uses template 1. All seven fields use regular-lat/lon grid template 0. Packing variability is reported descriptively and never silently relaxes canonical QC. The machine-readable [cross-year comparison](../experiments/recent_historical/phase4f_payload_acquisition_v1/cross_year_payload_compatibility.json) is finalized after the corpus gate.

## 13. Rainfall Grid Validation

Rainfall selected messages decode to the verified global **1440×721, 0.25°** regular-lat/lon grid, longitudes 0→359.75°, normalized latitudes −90→90°, and crop to the fixed 49×49 target. Source scan-direction keys are retained (`jScansPositively=0`, `iScansNegatively=0`). Unit `kg m**−2` is water-equivalent millimeters. The rainfall grid signature SHA-256 is `5b0577bc82e408d6d73d867c160c9f3dc71256c70e903743d778f386e23b8efe` in every year. No grid interpolation is used to invent rainfall resolution.

## 14. Atmospheric Grid Validation

UGRD 850 mb, VGRD 850 mb, HGT 500 mb and PWAT use `pgrb2ap5`; SPFH 700 mb and mean-sea-level PRES use `pgrb2bp5`. They decode to the verified global **720×361, 0.5°** regular-lat/lon grid, longitudes 0→359.5° and normalized latitudes −90→90°, then crop to finite 51×81 context arrays at f024/f048/f072. Their common grid-signature SHA-256 is `50611017acfa9976c06407208b4ef942d86b185be43e952ea5ea4403295bca1c`. Actual units are m/s (wind), gpm (500-mb height), kg/m² (PWAT), kg/kg (700-mb humidity), and Pa (MSLP). These arrays are source QC products, **not** interpolated model features.

## 15. Accumulation Semantics

The frozen 24-hour targets are Day 1 +3→+27 h, Day 2 +27→+51 h, Day 3 +51→+75 h. GRIB reference/valid time, forecast step, start/end interval, time-range unit and statistical-process keys are checked against the index and protocol. Atmosphere uses f024/f048/f072 respectively. Filename agreement alone is never sufficient. Documentation discrepancy: the legacy `AGENTS.md` §3.6 calls the then-current project target 6-hour rainfall; this Phase 4D-frozen operational corpus is explicitly a **24-hour** target. No 6-hour threshold is applied here, and this task does not rewrite earlier governance.

## 16. Rainfall Reconstruction

Phase 4F calls the unchanged canonical `reconstruct_minimal_accumulation_window`; it does not alter exact-cover, packing-bound, or negative-cell semantics. Shared source hours are decoded once/date. Only accepted 24-hour 49×49 arrays are saved. Rejected products retain their diagnostic/rejection evidence and remain in all scheduled denominators.

## 17. Packing-Precision Statistics

Year reports group actual packing quantum, data-representation template, binary/decimal scale and bits per value by member, lead and source hour. Across **33,750 lead-message incidences** (30,000 unique rainfall messages, with shared boundary hours counted in two lead windows), all use data-representation template 3, complex packing with spatial differencing. Quantum incidences are 28,691 at 0.1 mm, 5,048 at 0.01 mm, and 11 at 0.2 mm; bit widths span 8–14. There are 2,275 mixed-precision adjacent-pair member-products among 5,625 scheduled member-products, 416,774 negative intermediate cell occurrences and 9,447 beyond-bound cell occurrences; the most negative recorded intermediate residual is −0.2 mm. These diagnostic incidences are **not** counts of distinct raw messages or proof of a revised error tolerance. The canonical bound remains unchanged.

## 18. Rainfall QC

Each date×lead×member has explicit `PASS` or `FAIL`, source packing quanta, subtraction bound, negative and beyond-bound cell counts, minimum residual and reason. Failed rainfall is neither clipped nor zero-filled. Across 5,625 scheduled member-products, **3,680 passed and 1,945 failed** canonical QC; all 1,125 case source-message sets are complete. The source index and decoded-message set being complete do not imply rainfall-QC acceptance.

## 19. Member-Specific QC

All five members (`c00`, `p01`–`p04`) are counted separately by year and lead in each `year_report.json`. Each row below has **125 scheduled cases**; each entry is an accepted count, and its fail count is 125 minus that entry. A c00-valid case is not rejected just because a perturbed member fails; ensemble eligibility requires all five.

| Year | Lead | c00 | p01 | p02 | p03 | p04 | All five |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 2023 | Day 1 | 46 | 62 | 60 | 61 | 61 | 6 |
| 2023 | Day 2 | 78 | 101 | 83 | 90 | 96 | 31 |
| 2023 | Day 3 | 76 | 102 | 98 | 97 | 97 | 39 |
| 2024 | Day 1 | 51 | 64 | 72 | 61 | 65 | 6 |
| 2024 | Day 2 | 61 | 104 | 97 | 88 | 93 | 28 |
| 2024 | Day 3 | 71 | 106 | 99 | 92 | 100 | 33 |
| 2025 | Day 1 | 75 | 69 | 62 | 65 | 70 | 11 |
| 2025 | Day 2 | 75 | 95 | 90 | 88 | 91 | 32 |
| 2025 | Day 3 | 82 | 100 | 101 | 95 | 90 | 32 |
| **All** | **1,125/candidate member** | **615** | **803** | **762** | **737** | **763** | **218** |

## 20. Full-Ensemble Eligibility

`FULL_5_MEMBER_RAINFALL_QC_PASS` requires every frozen member's canonical 24-hour product; `ENSEMBLE_SOURCE_ELIGIBLE` additionally requires the atmospheric source inputs. Because atmosphere passed for every case, both are **218/1,125** overall: 76/375 in 2023, 67/375 in 2024, 75/375 in 2025. Day-1 ensemble acceptance is only 23/375 across the three years. These are source-only flags, not observation/model eligibility or probability output.

## 21. Atmospheric QC

All six forecast-only atmospheric messages at each lead must pass identity, units, native-grid, finite crop and physical-range checks. A case is `ATMOSPHERIC_QC_PASS` only if all six pass. After the two selected-range recoveries, atmosphere passed **1,125/1,125** cases (375/year, 125 per lead/year). No atmosphere value was substituted from another lead or year.

## 22. Deterministic Source Eligibility

`DETERMINISTIC_SOURCE_ELIGIBLE` means c00 rainfall canonical QC and all required atmospheric source fields pass. Because all atmosphere passed, this is **615/1,125**: 200/375 in 2023, 183/375 in 2024, 232/375 in 2025. By lead across years: Day 1 172/375, Day 2 214/375, Day 3 229/375. It is **not** a claim of observation alignment, complete feature extraction, model compatibility or forecast skill.

## 23. Probability Source Eligibility

`PROBABILITY_SOURCE_ELIGIBLE` has the same minimum c00-plus-atmosphere source prerequisites here, **615/1,125**; ensemble-baseline readiness is separately represented by `ENSEMBLE_SOURCE_ELIGIBLE` (**218/1,125**). This is not a calibrated-probability availability count. No probability model, calibrator or observed event label was run.

## 24. Regime Source Eligibility

`REGIME_SOURCE_ELIGIBLE` means the required forecast atmospheric source fields passed, **1,125/1,125**, not that a regime classifier was invoked or that its probabilities are available. No regime labels or scores were generated.

## 25. 2025 Holdout Protection

Only 2025 GEFS forecast bytes, metadata and source/QC flags were permitted. Phase 4F code imports no IMD reader or model-inference path. Even the two recovered dates were processed using source GRIB only. The final [holdout audit](../experiments/recent_historical/phase4f_payload_acquisition_v1/holdout_seal_audit.json) reports **`SEALED`**: no forbidden source markers, outcome-named files, 2025 observation access, model inference or outcome metrics. It does not unseal 2025 event counts or performance. This source-only audit cannot by itself assert future model generalization or authorize 2025 scoring.

## 26. Disk Usage

Preflight remeasured **282,193,772,544** free bytes before substantial transfer; a post-verification snapshot measured **265,168,162,816** free bytes. The hard stop is under 40 GB free or under remaining planned transfer plus 20 GB; preflight also requires room for all planned selected bytes, 35 GB staging allowance and 40 GB headroom. Final selected raw files occupy **10,485,487,577** logical bytes. A post-acquisition Phase 4F workspace snapshot occupied about **457,856,854** logical bytes, including receipts, metadata, checkpoints, logs and arrays; the validated 51×81 atmospheric `.npy` arrays account for 223,938,000 bytes and accepted 49×49 rainfall arrays for 71,156,480 bytes. No `.part` files remain in raw or Phase 4F staging. These are logical file-size measurements, not NTFS allocated-cluster usage; disk free space can also change because of unrelated local processes. Verified raw evidence is retained.

## 27. Processing Performance

Per-date network and decode/QC durations, selected-byte throughput, sampled process/system RAM and disk-write deltas are measured. The summed download duration is **4,943.91 s (82.4 min)** and summed decode/QC duration **3,409.52 s (56.8 min)**, including the two-date recovery work. Their sum is **about 139.2 min of measured stage work**, not an uninterrupted wall-clock duration: it excludes preflights, manifest rehashes, development, human pauses and time between runs. By year, download/decode sums are 1,110.14/907.22 s (2023), 1,582.78/975.57 s (2024), and 2,250.99/1,526.73 s (2025). Peak sampled Phase 4F acquisition-process RSS was about **215 MB** (2024); peak sampled system-wide used RAM during acquisition was about **17.97 GB** (2025). A later machine-wide memory snapshot exceeded that because of other processes, not this bounded Phase 4F worker. CPU/GPU acceleration is not claimed; eight I/O threads served acquisition, while per-date decode remained sequential.

## 28. Failures and Retries

Transient network errors got bounded exponential-backoff retries; 39,510 total download attempts are recorded across three years, with 3,048 `FAILED_RETRYABLE` entries within final verified receipts. Most observed retry reasons were remotely closed keep-alive connections after per-date decode gaps; 2024 also had isolated 90–231 s slow dates. There were **two initial `FAILED_FINAL` selected messages**, both in 2025; each kept its complete three-attempt failure record and was recovered individually with the same manifest range. Final unrecovered messages: **zero**. No wrong-length/hash/GRIB payload was admitted. An interrupted unverified `.part` is quarantined on resume; a fully verified pending transaction is recovered without re-download. Recovery also archived the original partial date metadata/checkpoint and checked previously accepted array hashes.

For a source-partial checkpoint only, the bounded recovery command is `.venv\Scripts\python.exe -m experiments.recent_historical.phase4f_payload_acquisition_v1.run recover-day --date YYYYMMDD`. It re-verifies frozen inputs, retries only missing manifest rows, preserves the original partial evidence, and reprocesses only that date; it does not unseal observations or run a model. The normal year runner now refuses to silently skip a source-partial checkpoint.

## 29. Artifact Manifest

The Phase 4F workspace has decoded-message metadata, accepted rainfall arrays, validated atmosphere arrays, date checkpoints, source-eligibility ledgers, receipts, network/recovery logs, year source manifests with SHA-256 sidecars, [cross-year compatibility](../experiments/recent_historical/phase4f_payload_acquisition_v1/cross_year_payload_compatibility.json) and the holdout audit. Raw selected GRIB2 files remain in the separate protocol-defined data layer. The independently verified year manifests list **28,335** (2023), **28,351** (2024) and **28,383** (2025) files. Their respective manifest SHA-256 values are `c35deea16c289de7cffeca502dd5409d7bdf0430b8a4b7bdd8556957083483e3`, `525e2316f470dbf731fbb73bfdcebd7878c3de9008a46980c93fe35c48048aa4`, and `97a66d7a3e8f111a5f4237535f3cdcaf87732820c4ba97a4db4b938b4c23f9d1`. Direct same-workspace re-finalization reproduced the exact 2023 and 2025 hashes, covering both the no-recovery and recovery report paths; 2024's verified manifest was not redundantly regenerated. The corpus-level [experiment manifest](../experiments/recent_historical/phase4f_payload_acquisition_v1/manifests/phase4f_experiment_manifest.json) lists 16 top-level files and verifies against SHA-256 `a2ad30e8cc1c8a90812a2cd5e6be20bc176006d6facc33b616d456fa271d1386`. A same-workspace rerun reuses verified receipts/checkpoints; an entirely new acquisition would have new timestamped receipts even if raw/scientific-content hashes match.

## 30. Decision Gate

**`CORPUS_SOURCE_LAYER_PARTIAL`**. All 36,750 frozen selected ranges are available, hash-verified and metadata-valid. The seven decoded field signatures/year match across all three years; no protocol-v1 structural blocker was found. However, canonical rainfall QC accepts c00 for only 615/1,125 cases and all five members for only 218/1,125; Day 1 is especially limited (c00 172/375; full ensemble 23/375). The source layer is usable **only for those documented source-eligible subsets**, subject to later feature availability and observation-alignment gates. Do not label all 1,125 cases eligible or revise packing bounds to inflate acceptance. The 2025 holdout remains sealed. This phase stops at source/decode/QC and does not authorize feature generation, training, inference, 2025 outcome analysis, frontend or scientific API changes. Exact next task, only under separate approval: design a versioned source-eligible feature-generation plan with explicit subset denominators, safe cached inputs and the still-sealed 2025 holdout; do not run it as part of Phase 4F.
