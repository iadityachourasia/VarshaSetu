# Independent-years corpus v2 (2021 and 2022): acquisition record

Status: **forecast-side acquisition complete and verified; nothing scored, trained or unsealed.** This implements the first step of option D1(a) of `docs/124`, after the source probe of `docs/127`. It adds years that no earlier protocol, selection, calibration or analysis has used, so a follow-up model can eventually be judged on data that were not seen when it was designed (risk R41). It authorises no training and no scoring.

## What was done

1. **Observation files.** The IMD annual 0.25 degree rainfall files for 2021 and 2022 (25,431,832 bytes each) were fetched from the same IMD endpoint used for 2023 to 2025 and stored under `experiments/recent_historical/imd_v2/`. Only the coordinate and time axes were read (`rainfall_values_read: false` in both manifests): the date axes are complete for 1 June to 3 October in both years. Their hashes are in the protocol. IMD redistribution rights remain unresolved (D2), so the files stay local and must not be uploaded anywhere.
2. **Protocol v2 frozen before any forecast byte.** `operational_corpus_protocol_v2` (sha256 `a3b1561618b1f41da2cb8fcd3cc7b6284c9c02773169d645a3f41c54612f0464`) is built from the frozen v1 protocol by script: source families, members, lead windows, fields, domains, QC policy, eligibility definitions and the feature contract are carried over unchanged. It changes only the years and schedule (250 initializations, 750 date-lead cases), the observation files and hashes, the split and sealing policy, and the storage layout. **Year roles: 2021 development, 2022 sealed independent test.** These roles were proposed in `docs/124` and `docs/127`; the project owner instructed "continue Acquire 2021-2022 data" on 2026-10-02 without changing them. They may be revised only before any 2022 observation value is read.
3. **Index inventory.** 250 dates, 86 sidecars per date; all 750 cases and 27,000 message occurrences are index-complete, the missing-message ledger is empty, the closed set of 43,260 files verifies, and the decision is `AUTHORIZED_FOR_PAYLOAD_ACQUISITION`.
4. **Payload acquisition.** The Phase 4F code was generated mechanically for 2021 and 2022 with every pinned constant computed from the verified inventory. All 24,500 selected byte ranges (7,110,741,985 bytes) were downloaded with exact `Content-Range`, length, GRIB header/trailer and SHA-256 checks, decoded for metadata, and put through the unchanged canonical rainfall reconstruction and the atmospheric finite checks. 2021 was completed and verified before 2022 started. Result: 24,500 of 24,500 hash-verified and metadata-valid, payload structure compatible across the two years, holdout-seal audit `SEALED`.

The governing records are tracked in `backend/app/evidence_data/phase10/` (manifest `corpus_v2_manifest.json`) and checked by `backend/tests/test_corpus_v2_evidence.py`. The raw messages, indexes and QC arrays are local and gitignored; the manifest records the hashes of the manifests that cover them.

## Source-side eligibility (forecast-only; no observation used)

| | 2021 | 2022 |
|---|---|---|
| scheduled cases | 375 | 375 |
| atmospheric inputs valid | 375 | 375 |
| control-run rainfall QC pass (deterministic source eligible) | 179 | 173 |
| all five members pass rainfall QC | 59 | 51 |

For context, the 2023, 2024 and 2025 corpus had 200, 183 and 232 control-run passes. The low pass rate is the same packing-bound failure mode documented in v1 (every failure carries the reason "negative difference exceeds packing bound"); it is a property of the NOAA accumulation encoding, not of this acquisition.

## Deviations and run record

- **Network.** Throughput varied from about 0.06 to 3.6 MiB/s, so 2021 took several hours and 2022 about an hour. The eight-worker setting was kept as v1 justified it and was not changed or re-benchmarked.
- **Transient failures, all recovered.** Six selected ranges on five dates in 2021 and two on two dates in 2022 failed all three attempts with timeouts or connection resets (never a missing source object). Each was re-fetched with the existing `recover-day` step, and every previously accepted array kept its hash. The pre-recovery 2021 year report and manifest are archived under `recovery/2021/_pre_recovery_year_finalization/`.
- **Finalization.** The corpus-level finalize first failed because the v2 directory had no `README.md` (it is a hashed manifest member); the README was written and finalize rerun. No scientific output was affected.

## A source change on 2021-07-21 (disclosed, not blocking)

From 2021-07-21 the NOAA 0.25 degree rainfall files carry 35 index messages instead of 34, which moves the rainfall message by one position. The selected fields' textual signatures are identical on all 250 dates, so what was fetched is unaffected. Whether the change matters for rainfall QC was checked on forecast-side flags only (`scripts/analyze_corpus2_layout_change.py`, `docs/artifacts/corpus2_layout_change_qc.json`): in 2021 the control-run pass rate is higher on or after 21 July (41 to 52 percent, p = 0.027), but the same calendar split in 2022, where there is no layout change, shows 46 and 46 percent (p = 1.0) and a significant shift for one perturbed member (55 to 72 percent, p = 0.001). Pass rates therefore vary with season, and there is no consistent evidence that the layout change affects QC. These are uncorrected tests on a single date, and cannot say why NOAA changed the file.

## Features (forecast-side) and context checks

The unchanged feature definitions were built for both years by `experiments/recent_historical/corpus2_features_v1/build.py` (arrays under `data/operational_derived/v2/features/`, local; JSON manifests tracked like v1). **2021 (development)** is paired with its IMD observations as v1 paired 2023 and 2024: 179 cases, 1,301 cells in every case (232,879 rows), which is exactly the terrain-derived land footprint of `docs/116`, an independent confirmation. **2022 (sealed)** keeps every finite forecast cell (173 cases of 2,401 cells, 415,373 rows) and has no target, label or observation date; the observation mask is applied only at unseal. The builder refuses to open 2022 observations (`assert_observation_year_allowed`), imports the IMD reader in one guarded function, and its input pins are read from the tracked evidence manifest. No model was loaded and no metric computed. Tests: `backend/tests/test_corpus_v2_features.py`.

Two descriptive checks (`scripts/analyze_corpus2_context.py`, `docs/artifacts/corpus2_context_check.json`; observations read only for development years 2021, 2023 and 2024):

- **The Ghats-coast deficiency is present in 2021 as well.** Raw GEFS on the coastal-and-orographic zone has a mean bias of about -7.5 mm and a heavy-rain frequency bias of about 0.11 in 2021, against about -6.7 mm and 0.11 in 2023 and -10.7 mm and 0.13 in 2024. The pattern the geography experiment (`docs/126`) targeted is therefore not specific to 2023 to 2025.
- **A multi-year offset in forecast 500 hPa height.** On land cells the area-mean forecast 500 hPa height of 2022 is about 1.5 standard deviations below the 2023 to 2024 mean (0.65 below 2021); 2021 and 2025 are also below 2023 to 2024 (0.95 and 0.73). A model that uses these features and is trained on other years will meet a real distribution shift in 2022, so any follow-up should test its sensitivity to them. This is forecast-side only and says nothing about skill.

Cases are not equally eligible across years (about half pass control rainfall QC), so these differences mix weather, eligibility and data effects.

## What this does not establish

- **No 2022 observation pairing.** Whether each 2022 case has a usable IMD target on a nonempty common mask is untested (it needs the values), and 2022 values stay unread.
- **No models.** No training, inference or probability features exist for 2021 or 2022.
- **Roughly half the cases are eligible.** About 47 percent of cases have a valid control-run rainfall field, so a follow-up has fewer cases than scheduled.
- **Retention.** The raw messages exist only locally; NOAA does not promise permanent retention of the archive.
- **Rights.** IMD terms for the new years are unresolved (D2), which limits publication and any third-party upload.

## Decisions that remain with the project owner

1. **Roles.** Confirm or revise 2021 development and 2022 sealed test, before any 2022 value is read.
2. **Follow-up protocol.** Whether to freeze a protocol v2 for a follow-up model (for example a bias-controlled geography-aware correction, `docs/126`), with its training years, selection rule and one-shot 2022 scoring, before building 2021/2022 features.
3. **First independent test of the frozen models.** Whether the unchanged M1 to M4 of the 2023 to 2025 corpus should also be scored once on 2022 under a pre-registered protocol. This is not authorised here.
4. **Rights (D2).**

## Addendum (2026-10-03): 2022 has since been opened

The 2022 observations were opened once, under the unseal record of `docs/132`, and the result is in `docs/133`. 2022 is now a consumed holdout; the sentences above that say 2022 values stay unread describe the state at the time of writing.
