# Phase 10D: geography-aware follow-up, protocol v3 and the unseal record

Date: 2026-10-03. Protocol v3: `backend/app/evidence_data/phase11/geoaware_followup_protocol_v3.json` (sha256 `252cbf4b3fafdbe52e9c8ee9a9c6b4a3c1d6f9a57e0d22485569d935cd366191`). Selection freeze v3 sha256 `ce9b5addab9e6be5eca8baa34a339271fa6808ddb5c96cb9e50ce093991748a6`. Unseal record sha256 `982aae51a128279ad19bab301cb30c312f35b347398af97079b5f685cbe35808`. Result and its interpretation: `docs/133`.

## The instruction, and why the order matters

After `docs/131` listed three options (run the one-shot 2022 test as frozen, draft protocol v3, or stop and report), the project owner replied **"do all of three perfectly"**. The three are not independent, because 2022 can be opened only once: testing the v2 candidate and then drafting v3 would spend the year twice. The only coherent order was therefore: (a) freeze v3 including its selection, (b) open 2022 **once** and score the frozen v2 candidate set and the frozen v3 candidate set together under a pre-registered multiplicity rule, (c) report every result. The message does not name these steps; it was treated as authorising all three in that order, and the unseal record (below) is the signed form of step (b). It authorises nothing else: the frozen M1 to M4 were not scored (decision 5 stays no), and IMD values remain unpublishable (D2).

## Change C2 (post hoc, disclosed)

v2 selected each arm by lowest pooled RMSE, while the primary test asks about Ghats-coast heavy-rain CSI, and `docs/131` showed the two pulling apart. **C2** aligns them: among configurations eligible under G1, G2 and G4 in every held-out year and within 0.2 mm of the lowest eligible pooled out-of-fold RMSE, select the one with the highest mean (over the three held-out years) Ghats-coast zone heavy CSI; ties go to the lower RMSE, then the earlier grid position. The same rule is applied to every arm including the control, so the comparator is not weakened. The only new number is the 0.2 mm tolerance, taken unchanged from decision rule P2.

C2 was decided **after the v2 table, including which configurations the rule would pick, had been seen**; it is the second post-hoc change (C1 was the first). The v3 selection is therefore a deterministic re-application of a known table, and the development comparison is development evidence only. A test compares v2 and v3 field by field: only the documented items differ.

Selection under v3 (development years, leave-one-year-out, cross-validation results reused by hash): B0 configuration 14 (the same model as v2, byte for byte, which also confirms training is deterministic), B1 configuration 15 (v2 chose 8), B0Z 14, B1Z 15. The pure rule is `select_configuration_aligned` in `backend/app/ml/geoaware_followup.py` with its own tests.

## The single test, designed before opening

- **One event.** 2022 is opened once. Raw and every unique selected model of selection freezes v2 and v3 (seven models) are scored together; nothing is selected, tuned or re-scored afterwards.
- **Two candidate sets.** Primary: the v3 selection, B1 against B0. Secondary: the frozen v2 selection, B1 against B0. A model chosen by both protocols is one model.
- **Multiplicity.** Two comparisons on the same year, so each paired whole-case interval is **97.5 percent** (Bonferroni, alpha 0.025), stored and labelled as such. The 95 percent intervals are reported as descriptive only. "Adds value" is claimed only for a candidate set satisfying P1 to P4 at that level; the primary set is the v3 set.
- **Decision rule (P1 to P4)** is the one of `docs/129` and `docs/131`: P1 zone heavy CSI of B1 minus its control positive with the interval excluding zero; P2 overall RMSE not worse by more than 0.2 mm; P3 G1, G2 and G4 pass (G3 reported); P4 the control is B0 selected under the same protocol.
- **Unevaluable, not failed.** If the Ghats-coast zone failed the support gate (at least 30 cases, 20 cells, 30 observed heavy event pairs) the test would be reported as unevaluable.

## The unseal record and the guard

`geoaware_followup_unseal_record.json` was written **before any 2022 observation value was read**. It quotes the owner message verbatim and lists 29 sha256 hashes: the three protocols, the three selection freezes, the development summary, the corpus protocol and evidence manifest, the static geography, the 2022 feature files and manifests, the IMD 2022 file, all eight model files, the scoring script and the four code modules the decision depends on. `scripts/score_geoaware_followup_2022.py` refuses to run unless that record exists, matches its own sidecar and every listed file still matches, including the script's own hash; it also refuses to run if a result already exists (one-shot). `backend/tests/test_geoaware_followup_unseal_guard.py` tests each refusal on temporary copies: no record, a tampered file, a sidecar mismatch, a wrong script hash, a missing owner message, and an existing result.

## Rehearsal and what it found

Because a runtime bug that first appeared after opening would have forced a new record, the identical code path was rehearsed on the **development year 2021** (in-sample for the models, so its numbers are meaningless; it writes outside the repository and emits no claim). The rehearsal found one real bug before the record was written (the IMD file hash was looked up in the wrong protocol file). It also validated the data path: the Raw numbers it produced for 2021 equal an independently computed 2021 Raw verification (`docs/artifacts/corpus2_context_check.json`) exactly in every zone for cell counts, RMSE, bias, event counts and CSI, with 1,301 paired cells in all 179 cases and none outside the land footprint. The decision logic was also tested on synthetic data (`backend/tests/test_geoaware_followup_scoring.py`), including a genuine pass, a no-gain case, an over-forecasting case and an unsupported zone; writing those tests exposed and fixed two weaknesses in the first fixtures (biased forecasts that could never pass, and independent noise that made the overall RMSE comparison meaningless).

Two supporting changes: `paired_bootstrap` in `backend/app/ml/zone_verification.py` gained an optional `level` (95 percent output unchanged; other levels are stored under `interval` with a `level` field so they cannot be mistaken for 95 percent), and the `docs/129` and `docs/131` descriptions were corrected earlier as recorded there.

## What this protocol does not do

It does not change any guardrail value, the grid, the cap, the development data or the sealing rule. It does not authorise scoring anything else on 2022, publishing IMD values, or re-running the test.

## Durability note

The recorded hashes of code files are over the bytes that existed when the record was written (line feeds). So that a Windows checkout cannot silently change them, `.gitattributes` marks exactly those files `-text` (the scoring script, `geoaware_followup.py`, `geoaware_followup_scoring.py`, `zone_verification.py` and `geoaware.py`), and the evidence test also accepts a line-feed-normalised match. Any later edit to a listed file is visible as a hash mismatch, which is intended: a change to the code that defined the test must be a new, versioned thing.
