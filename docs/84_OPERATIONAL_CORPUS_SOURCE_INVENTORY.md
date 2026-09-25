# Phase 4E — 2023–2025 operational GEFS source inventory

Status: **index-only inventory complete; `AUTHORIZED_FOR_PAYLOAD_ACQUISITION` for a separately approved, exact selected-range Phase 4F**. This is not payload validation, rainfall QC, an eligible scientific corpus, training authorization, or operational readiness.

## 1. Executive Summary

All 375 predeclared 00 UTC initializations and 1,125 date×lead cases (2023–2025, June 1–October 3 inclusive) were retained. NOAA sidecars listed all 32,250 required source objects and all 40,500 case-field message occurrences. There were zero missing or anomalous occurrences. The planned transfer deduplicates shared window-boundary messages to 36,750 exact selected ranges (10,485,487,577 bytes). Selected textual parameter/level/forecast/member/interval signatures agree across all three years. Every case still requires decoded GRIB metadata and rainfall-QC validation before scientific admission.

## 2. Frozen Protocol Reference

The sole schedule and field contract are [`protocol.json`](../experiments/recent_historical/operational_corpus_protocol_v1/protocol.json) and its [`feature_contract.json`](../experiments/recent_historical/operational_corpus_protocol_v1/feature_contract.json), version `operational_gefs_imd_2023_2025_v1`. Phase 4E did not modify them or the 2017–2019 retrospective corpus. The companion [Phase 4E README](../experiments/recent_historical/phase4e_source_inventory_v1/README.md) gives the exact reproducible commands.

## 3. Protocol Hash

The protocol SHA-256, checked before retrieval and on every run/finalize/verify invocation, is `235f53a10a013de0e8a94eb07f7526f22ac0b624b1bbbb5473c872bf628c2c47`. The feature-contract SHA-256 is `100894f11b677b1de20869d7a741ed16d770d2f4dbff415084fe9888a393842f`. Both match the frozen references.

## 4. Inventory Method

For each date, code enumerated the frozen 16 rainfall forecast hours × five members plus `pgrb2ap5` and `pgrb2bp5` at f024/f048/f072: **86 `.idx` objects/date**. Six bounded concurrent I/O threads fetched only sidecars from `noaa-gefs-pds.s3.amazonaws.com`, with a 500 KB/object cap and at most two retries. Phase 4A/4B sidecars were reused by verified hash where present. Receipts retain object key, source URL, retrieval/reuse time, byte count, SHA-256, HTTP result, retry count, and Last-Modified/ETag when captured. Per-date atomic checkpoints make the run resumable. No GRIB payload, selected byte range, IMD observation value, model, or scientific metric was accessed.

## 5. NOAA Source Families

`pgrb2sp25`: `APCP:surface`, c00 and p01–p04, the frozen 16 forecast hours through f075. `pgrb2ap5`: `UGRD:850 mb`, `VGRD:850 mb`, `HGT:500 mb`, `PWAT:entire atmosphere (considered as a single layer)`. `pgrb2bp5`: `SPFH:700 mb`, `PRES:mean sea level`. Atmospheric fields use c00 at f024/f048/f072. The inventory used exact key forms `gefs.YYYYMMDD/00/atmos/{family}/{member}.t00z.{grid}.fHHH.idx`; it did not substitute aliases, members, cycles, or grids. The provider is [NOAA/NCEP GEFS public data](https://registry.opendata.aws/noaa-gefs/).

## 6. 2023 Availability

125/125 initializations had indexes; 10,750/10,750 required index objects and 375/375 date×lead cases were index-complete. Control-rainfall, atmospheric, deterministic-input, and full-five-member index completeness were each 375/375. Source-unavailable and structurally anomalous cases: zero.

## 7. 2024 Availability

125/125 initializations had indexes; 10,750/10,750 required index objects and 375/375 date×lead cases were index-complete. Control-rainfall, atmospheric, deterministic-input, and full-five-member index completeness were each 375/375. Source-unavailable and structurally anomalous cases: zero. This does **not** overturn the Phase 4B finding that only 21/35 rainfall member-products passed decoded rainfall QC in its seven-day sample.

## 8. 2025 Availability

125/125 initializations had indexes; 10,750/10,750 required index objects and 375/375 date×lead cases were index-complete. Control-rainfall, atmospheric, deterministic-input, and full-five-member index completeness were each 375/375. Source-unavailable and structurally anomalous cases: zero. Observation values and performance remained sealed.

## 9. Day-1 Completeness

375/375 scheduled Day-1 (+3→+27 h) cases were index-complete: 125/125 in each year. The six required rainfall source hours/member and six f024 atmospheric fields were listed.

## 10. Day-2 Completeness

375/375 scheduled Day-2 (+27→+51 h) cases were index-complete: 125/125 in each year. The six required rainfall source hours/member and six f048 atmospheric fields were listed.

## 11. Day-3 Completeness

375/375 scheduled Day-3 (+51→+75 h) cases were index-complete: 125/125 in each year. The six required rainfall source hours/member and six f072 atmospheric fields were listed.

## 12. Rainfall Message Completeness

All 1,125 cases have c00 and each of p01–p04 **message availability** for the exact-cover source hours. All 30,000 unique rainfall APCP messages (375 dates × 16 hours × five members) appear once in the acquisition plan. The case-field inventory also records repeated f027/f051 boundary references. `RAINFALL_REQUIRES_DECODED_QC` applies to every case/member: index presence is not a reconstructed, packing-safe 24-hour value.

## 13. Atmospheric Message Completeness

All 1,125 cases have all six required atmospheric messages at the corresponding frozen f024/f048/f072 time, for 6,750 unique selected atmospheric messages. Native-grid shape, template, units, finite context-grid coverage, and interpolation readiness require payload validation.

## 14. Ensemble Completeness

Every case is full-five-member **index** complete (1,125/1,125). Member-specific flags are preserved in [`source_inventory.json`](../experiments/recent_historical/phase4e_source_inventory_v1/source_inventory.json); a future c00-valid case is not made ineligible merely because a perturbed member later fails decoded QC. No probability or ensemble forecast was computed.

## 15. Missing-Message Ledger Summary

The complete [`missing_message_ledger.jsonl`](../experiments/recent_historical/phase4e_source_inventory_v1/missing_message_ledger.jsonl) is empty (zero bytes, zero missing/anomalous occurrences); it is intentionally retained as hashed evidence. All 40,500 expected case-field rows, including boundary-hour reuse, are in [`message_inventory.jsonl`](../experiments/recent_historical/phase4e_source_inventory_v1/message_inventory.jsonl). No failed date was silently dropped.

## 16. Cross-Year Structural Comparison

The selected index signatures—exact parameter, level, forecast description/accumulation interval and ensemble identity—match across 2023, 2024 and 2025. No field disappeared, changed family, changed selected forecast-hour naming, or gained duplicate exact matches. Message-number/index-size ordering comparisons found zero cross-year differences for the selected field keys. The index parser found no format-change or metadata-inconsistency status. This is **text-index** continuity, not proof of equal GRIB templates or source executables.

## 17. Product-Family Continuity

The `gefs.YYYYMMDD/00/atmos/` key convention, c00/p01–p04 names, `pgrb2sp25` 0.25° product label, `pgrb2ap5`/`pgrb2bp5` 0.5° product labels, fHHH naming and `.idx` convention remained available on all scheduled dates. The label is not a decoded native-grid verification.

## 18. Metadata Compatibility

The `.idx` text supports provisional parameter, level, initialization, forecast-hour, accumulation-window and member checks. It does **not** expose GRIB grid/product/data-representation templates, native grid shape, packing quanta or decoded physical units. The machine-readable inventory includes those frozen-contract fields as explicit `null` values, not inferred data. Phase 4E's expanded evidence statuses (`INDEX_AVAILABLE`, `MESSAGE_AVAILABLE`, and specific failure codes) differ in spelling/granularity from the protocol's conceptual `INDEX_PRESENT`/`MESSAGE_PRESENT`/`SOURCE_UNAVAILABLE` status list; `MESSAGE_AVAILABLE` means `MESSAGE_PRESENT`, but neither is a decoded-valid claim. Phase 4D's prose asks for template comparison *before* payload acquisition, whereas an index-only inventory cannot perform it. Phase 4F must make template/metadata validation the first gate on selected payload bytes; until then compatibility is provisional. Likewise, an HTTP 200 index does not prove the corresponding GRIB object is intact.

## 19. Cases Requiring Payload Validation

**1,125/1,125** cases, 375 per year, are marked `REQUIRES_PAYLOAD_METADATA_VALIDATION`. Each selected range needs byte/hash identity, GRIB template/grid/level/units/interval checks, followed by unchanged canonical packing-aware rainfall reconstruction and member-specific QC in a later phase. There are zero cases certified scientifically eligible by Phase 4E.

## 20. Planned Acquisition Manifest

[`planned_acquisition_manifest.jsonl`](../experiments/recent_historical/phase4e_source_inventory_v1/planned_acquisition_manifest.jsonl) lists **36,750 unique messages**: 30,000 rainfall and 6,750 atmosphere. Each row records year, initialization, 00 UTC cycle, member, lead(s), forecast hour, family, parameter/level, NOAA key, index key/hash, GRIB message number, exact byte start/end/length, and intended relative local path. Day-boundary reuse is deduplicated. This is a proposal only; no listed payload was fetched. All selected lengths were derivable from the next index offset; unknown lengths: zero.

## 21. Exact Estimated Download Volume

Selected byte-range sums from index offsets (decimal bytes):

| Year | Rainfall | Atmosphere | Combined |
| --- | ---: | ---: | ---: |
| 2023 | 2,964,234,562 | 518,461,045 | 3,482,695,607 |
| 2024 | 2,930,180,860 | 527,390,517 | 3,457,571,377 |
| 2025 | 3,021,334,420 | 523,886,173 | 3,545,220,593 |
| **Total** | **8,915,749,842** | **1,569,737,735** | **10,485,487,577** |

This is a planned selected-message volume, not a measured transfer, and excludes request/protocol overhead or retransmission. Cached index contents total 125,240,665 bytes. Inventory inputs occupy 204,753,999 logical bytes across 64,599 files; a 4 KiB cluster-slack planning approximation adds 164,803,505 bytes, not a measured NTFS allocation audit.

## 22. Disk Requirement

Free disk measured during finalization: **282,537,918,464 bytes** (282.54 GB, about 263.13 GiB); after manifest verification it was **282,193,772,544 bytes**. Subtracting only planned selected bytes from the finalization snapshot leaves 272,052,430,887 bytes; a conservative additional 35 GB staging allowance would leave about 247.05 GB. No space was reserved. Phase 4F must stop if free space drops below 40 GB **or** below remaining planned transfer plus 20 GB, and must remeasure immediately before transfer; these snapshots can change independently of this project.

## 23. Estimated Acquisition Time

Phase 4B actually transferred 73,300,764 selected bytes in about 8.8 minutes serially. At that observed seven-day rate, 10,485,487,577 planned bytes imply **1,258.8 minutes (~21.0 h) serial-equivalent**. At one-third that rate, allow **3,776.5 minutes (~62.9 h)**, excluding decode/QC and unpredictable service delays. A bounded-concurrency speedup is **unmeasured**; benchmark a representative selected-range workload before projecting one or changing frozen workers. The Phase 4D report's “~55 h serial” does not follow its cited 8.8-minute/73,300,764-byte Phase 4B rate and should not be used as a measured estimate. Its suggestion to benchmark a staged selected-range week in *Phase 4E* conflicts with this phase's explicit index-only/no-payload scope; defer such a benchmark to a separately authorized Phase 4F. Phase 4E checkpoint span included interruptions/development and is not an acquisition benchmark.

## 24. Resumability Strategy

Index receipts and SHA-256-checked cached sidecars were reused; completed dates were atomic checkpoints. An interrupted run resumed without re-fetching verified source data. There are **zero `.part` files** after completion. Of 32,250 index objects, 31,974 new index files reside under Phase 4E; 369 object resolutions were cache hits at checkpoint time (including earlier Phase 4E resumptions), so the two counts need not be arithmetic complements. Last-Modified is captured for 28,774 objects; earlier responses and protected-cache reuse without it retain `null`. Phase 4F should use the same hash-before-reuse rule for selected payload ranges.

## 25. 2025 Holdout Protection

Only 2025 **forecast** index metadata, source availability and planned ranges were inspected. No 2025 IMD file was opened by Phase 4E code, no model loaded, no inference/scoring/event counts generated, and no 2025 performance reported. The 2023/2024/2025 training/validation/test policy remains conditional and unchanged; 2025 observation outcomes remain sealed.

## 26. Risks

Index availability does not establish GRIB object accessibility or integrity, true source grid/template/packing/units, decoded finite coverage, canonical rainfall acceptance, IMD alignment, licensing, model compatibility, or usable case counts. Phase 4B already showed substantial decoded rainfall rejection despite index availability. Source headers were not recorded for every index. Network/storage/remote-object behavior may change after this snapshot. No current scientific API or frontend claim should be revised from this inventory alone.

## 27. Stop Conditions

Stop Phase 4F on source hash/byte-range mismatch, changed GRIB parameter/level/member/interval/grid/template/units, canonical-QC or feature-contract pressure, persistent corruption, missing mandatory predictors, licensing/access concern, free disk below the frozen threshold, or any loss of the 2025 holdout seal. Preserve failed records and denominators. A material source discontinuity requires a versioned protocol decision, never silent v1 mutation.

## 28. Reproducibility

From repository root: `.venv\Scripts\python.exe -m experiments.recent_historical.phase4e_source_inventory_v1.inventory run --workers 6`, then `finalize`, then `verify`; reruns use verified checkpoints/receipts and do not need to repeat completed downloads. The 9 focused Phase 4E tests cover frozen hashes/calendar, object/message enumeration, parser/matching, exact-cover availability, member-specific completeness, deduplication, cross-year signature changes, missing-object classification and the holdout seal. Final regression and hash-verification results are recorded in the task handoff; no scientific payload was decoded here.

## 29. Artifact Manifest

[`artifact_manifest.json`](../experiments/recent_historical/phase4e_source_inventory_v1/artifact_manifest.json) and [`artifact_manifest.sha256`](../experiments/recent_historical/phase4e_source_inventory_v1/artifact_manifest.sha256) form a closed-set SHA-256 manifest of **64,610 files** of code, receipts, cached indexes, date checkpoints and derived evidence. Manifest SHA-256: `3c68d211aa487abe1e34b1a016932e819c522e9dca4013a8ab5287a9224950ef` (verified against all listed files). Principal outputs: `protocol_reference.json`, `source_inventory.json`, `message_inventory.jsonl`, `missing_message_ledger.jsonl`, `cross_year_compatibility.json`, `planned_acquisition_manifest.jsonl`, `size_estimates.json`, and `network_statistics.json`. The prior Phase 4A/B/C evidence and frozen Phase 4D protocol are outside this new versioned directory and remain protected.

## 30. Decision Gate

**`AUTHORIZED_FOR_PAYLOAD_ACQUISITION`**: the all-year index inventory supports the frozen v1 key/message plan sufficiently to begin a separately authorized acquisition of **only** the listed selected ranges. This is not a declaration that payload metadata, decoded rainfall, atmospheric inputs, scientific eligibility, or 2025 performance are valid. Phase 4E stops here; no payload acquisition, model work, API/frontend change, or 2025 outcome inspection follows automatically.
