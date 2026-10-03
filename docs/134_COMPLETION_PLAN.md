# Phase 11: completion plan for everything still partial or not built

Date: 2026-10-03. Scope: the 8 rows of `ps_coverage.json` that are not IMPLEMENTED (4 PARTIAL, 4 PLANNED), measured against the SIH26080 text. This plan says what each item needs, what **can** reach IMPLEMENTED, what **cannot** and why, the order, the acceptance test for each work package, and the rules that stay in force. It is the plan of record for the work that follows; each package updates the coverage manifest only when its own evidence exists.

## 0. Rules that do not bend (from `AGENTS.md` and the standing decisions)

1. **No fabricated science.** A status moves up only when the capability exists, is reachable in the app and is backed by hash-verified evidence. A heuristic label is shown as a heuristic.
2. **Protocol first, then stop for approval for any step that changes a model or opens unseen data.** The owner's instruction to implement everything is treated as approval of the packages below in the form written here; each protocol records that and the owner can withdraw it.
3. **Consumed holdouts:** 2019 (Track A), 2022 and 2025 (Track B). Any further use is labelled "POST-HOC EXPLORATORY ANALYSIS OF THE COMPLETED 20XX FINAL TEST". 2024 is a reused development year.
4. **Downloads** state file, source and size; IMD data stays local (rights unresolved, D2); nothing derived from IMD values that can reconstruct them is published or uploaded; no credentials or `.env` are committed.
5. **Report outcomes faithfully**, including failures, and never claim a requirement is met by renaming it.

## 1. Where each item stands and where it can honestly get to

| # | Row (status) | Gap today | Can it reach IMPLEMENTED? | What it can honestly reach |
|---|---|---|---|---|
| 1 | REGIME-CLASSIFIER (PARTIAL) | 3 pseudo-classes only; no independent validation; coastal/orographic and western disturbance not classified | Only with independent validation of the labels, which depends on item 4 | A hierarchical classifier with three heads (synoptic, coastal/orographic, western-disturbance indicator) plus an independent check of active and break |
| 2 | REGIME-COASTAL-OROGRAPHIC (PARTIAL) | Zones are static; no forecast-time regime label; no specialist | A forecast-time, evidence-linked heuristic regime plus the independently tested geography-aware correction can be shown as IMPLEMENTED **as a heuristic, rule-based regime**; a learned, validated regime cannot (no event labels exist) | IMPLEMENTED with the limitation stated, or PARTIAL if the label evaluation does not support it |
| 3 | REGIME-WESTERN-DISTURBANCE (PLANNED) | No labels, no upper-level fields, domain stops at 22 N | **No** as a validated regime. A forecast-only trough heuristic on 500 hPa height can exist with no download | PARTIAL: a labelled heuristic indicator, counted, and Raw verified over the north; never "validated" |
| 4 | REGIME-INDEPENDENT-VALIDATION (PLANNED) | No external labels | Active and break only, against observation-based criteria (Rajeevan et al. 2010 style) with a long IMD climatology; depression cannot be validated without a track source whose terms are unverified | PARTIAL (active vs not active, break vs not break) |
| 5 | IMPROVEMENT-VS-RAW (PARTIAL) | Very-heavy skill not improved; 2019 track heavy skill below Raw; frozen regime models mixed | **No** for very-heavy and for the 2019 track: no independent data remain (2019 and 2022 are consumed) | PARTIAL, with the event-weighted and geography-aware models added to the product so heavy-rain improvement is visible and not only in evidence files |
| 6 | DISTRICT-VERIFICATION (PARTIAL) | Operational-era track only | **Yes**: Track A (2018 development, 2019 post-hoc) can be done from frozen predictions under a protocol frozen first | IMPLEMENTED for both tracks |
| 7 | LIVE-INFERENCE (PLANNED) | Replays history only | A worker that fetches the latest NOAA cycle, runs the frozen models and publishes a labelled experimental forecast **can exist**; **skill cannot be shown** for a new cycle until observations exist | PARTIAL: a working experimental pipeline, no skill claim |
| 8 | ALL-INDIA-DOMAIN (PLANNED) | 10-22 N, 68-80 E only | A full all-India retrain, recalibration and re-verification is a new corpus version and months of work in practice; **Raw** can be verified over the whole IMD grid without new downloads | PARTIAL: Raw GEFS verified over all of India for the operational-era track; corrected models stay regional |

Not addressable at all, and stated as such: the raw forecast is NOAA GEFS, not an NCMRWF model (no access); very-heavy improvement and any new-cycle skill cannot be demonstrated on independent data that do not exist yet.

## 2. Work packages, in order, with acceptance tests

### WP-A District verification for the 2019 reforecast track (item 6)
- **Work:** freeze a protocol (the Track B district-verification protocol with the years, populations and labels of Track A: 2018 development, 2019 post-hoc), compute from the frozen predictions of M0 to M4, store hash-verified evidence, serve it, show it on the Verification page next to Track B.
- **Acceptance:** protocol hash recorded before compute; reproduction gate (Raw and M2 district means equal an independent recomputation); every metric carries its denominator; unsupported strata carry no number; API and page numbers equal the evidence file; 2019 labelled post-hoc.
- **Moves:** DISTRICT-VERIFICATION to IMPLEMENTED.

### WP-B Independent validation of active and break (items 4 and 1)
- **Work:** download the IMD annual 0.25 degree rainfall files needed for a climatology (stated before the download, local only); compute the observation-based active and break flags for the core monsoon zone; count days and cases against the support gate; freeze a protocol; report balanced accuracy, macro-F1, per-class precision and recall, a confusion matrix and support for the frozen classifier **separately** from the pseudo-label agreement figures; show it on the Regimes page and the Compliance page.
- **Acceptance:** climatology source and years recorded with hashes; criteria stated with their deviations (core-zone box, July and August only, IMD grid edge); support counted before any scoring; post-hoc labels for 2019 and 2025; depression explicitly "not validated".
- **Moves:** REGIME-INDEPENDENT-VALIDATION to PARTIAL; contributes to REGIME-CLASSIFIER.

### WP-C Forecast-time coastal and orographic regime (items 2 and 1)
- **Work:** a per-case, forecast-only coastal/orographic regime head built from the forcing quantities of `docs/118` (onshore and cross-barrier flux strength against training-year terciles) with its heuristic nature stated; per-cell and per-case soft scores; API and page; evidence of discrimination (share of observed Ghats-coast heavy events by predicted class on the development years, and on the consumed years labelled post-hoc); link to the geography-aware correction as the zone-aware corrector.
- **Acceptance:** thresholds fixed from the training year only; no observation enters; discrimination reported with support counts; labelled heuristic; no claim of validation.
- **Moves:** REGIME-COASTAL-OROGRAPHIC to IMPLEMENTED (as a labelled heuristic) if the discrimination supports it, otherwise it stays PARTIAL and says why.

### WP-D Western-disturbance indicator and all-India Raw verification (items 3 and 8)
- **Work:** (1) decode the stored global fields over a wider window (no new download) and compute a forecast-only 500 hPa trough indicator over north-west India, labelled a heuristic; (2) count indicator days per year against the support gate; (3) verify **Raw** GEFS against the IMD observations over the whole IMD grid for 2023 to 2025 (and 2021 to 2022 as development and consumed years with their labels); (4) stratify Raw verification north of 22 N by the indicator, descriptively.
- **Acceptance:** counts before any scoring; no model is trained; the page says "indicator, not a validated regime" and "Raw only outside the regional domain".
- **Moves:** REGIME-WESTERN-DISTURBANCE to PARTIAL; ALL-INDIA-DOMAIN to PARTIAL.

### WP-E Heavy-rain models in the product (item 5)
- **Work:** serve the selected event-weighted and geography-aware models (B0, B1) as an additional model in the comparison views for the years where they were evaluated, with the evidence labels and their leakage-free provenance; keep the frozen M1 to M4 unchanged.
- **Acceptance:** predictions are reproducible from the frozen model hashes; 2022 is shown only with the first-use label; no new selection is made.
- **Moves:** IMPROVEMENT-VS-RAW stays PARTIAL with its limitation updated.

### WP-F Live new-cycle pipeline (item 7)
- **Work:** per `docs/125`: a cycle-parameterised acquisition of the selected NOAA messages for the latest available 00 UTC cycle, decode and the canonical rainfall quality control, inference with the frozen models, publication of a labelled experimental product with initialisation time, lead, quality-control status and model hashes, an API endpoint and a page; a separate worker script (the API stays read-only).
- **Acceptance:** runs end to end on a real current cycle or reports honestly that none is available; every output labelled "experimental, no verification possible yet"; the same code reproduces a historical case exactly; failures are reported, never hidden.
- **Moves:** LIVE-INFERENCE to PARTIAL.

### WP-G Closing audit
- **Work:** update the coverage manifest, the Compliance page, the documents and the judge material to the evidence of each package; run every suite; reconcile the numbers; report each remaining gap and why it remains.
- **Acceptance:** all suites green; no document states a status the manifest does not.

## 3. Order and dependencies

A (independent) then B (needs the download, independent of A) then C (independent) then D (uses the wider-window decode and the IMD files B downloads or the ones already held) then E then F then G. A, B and C can proceed in parallel in principle; they are done in sequence here so each is verified before the next.

## 4. Estimates (labelled as estimates, not measurements)

A: hours. B: dominated by the IMD download (many files of about 25 MB each from a slow host). C: hours. D: hours for the indicator and Raw verification. E: hours of coding plus whatever the NOAA transfer needs. F: hours to a day for a reliable end to end path. G: hours. A true all-India retrain and recalibration of every model, and any validated western-disturbance regime, are not in this plan because they would each be a new corpus and protocol and cannot be independently tested on data that exist today.

## 5. What "complete" will and will not mean at the end

Every requirement of the problem statement will be **built and reachable** with honest labels, but not every one can be **proven**: the regime classifier stays pseudo-labelled except for the independently checked active and break classes, the western-disturbance regime is an unvalidated indicator, the very-heavy improvement is not demonstrated, the live pipeline has no skill to show yet, and the forecast being corrected is NOAA GEFS, not an NCMRWF model. The final audit states each of these.

## Status (2026-10-03)

All work packages WP-A to WP-G were carried out; the outcome, the final status of each item and the remaining gaps are in `docs/141_COMPLETION_CLOSING_AUDIT.md`. No coverage row is planned; 7 are partial for the reasons stated there.
