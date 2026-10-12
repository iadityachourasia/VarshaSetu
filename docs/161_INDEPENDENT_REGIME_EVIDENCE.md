# Independent regime evidence: annotation gate and winter boundary

> **9 October source-preparation follow-up:** `docs/180` indexes exact-date
> page leads in the three locally retained RSMC annual reports for the frozen
> 72-case packet. No page is an admitted dated bulletin or expert label;
> reviewer and rights gates below remain unchanged.

Date: 2026-10-07. **The gate remains open.** This work adds a validator for
the prepared 72-case blinded JJAS packet, but no meteorologist submitted a
review, no bulletin document was admitted, and no western-disturbance winter
case was acquired. It therefore reports **zero expert labels, zero adjudicated
labels and zero detector-vs-expert scores**. Forecast-only pseudo-labels remain
project rules, never expert truth.

## Existing blinded population

`docs/154` and its immutable packet manifest define 72 GEFSv12 reforecast
control cases from 2014–2016, balanced over JJAS month and Day 1/2/3 lead.
These years were previously consumed rainfall tests. The packet exposes six
forecast-time atmospheric maps, issue/valid times and map hashes. It hides
observations, detector outputs, corrected rainfall and verification. The
original checkout has the ignored local maps; all 72 maps and the packet
manifest were independently hash-checked during this work. No map bytes are copied
into the worktree or tracked repository.

`backend/app/ml/regime_annotation_review.py` checks the frozen packet sidecar
and, if supplied, every local map hash. It requires a source ledger with exact
document SHA-256, URI, issuance and validity times, local file, source kind and
permitted use. The command rehashes source files. Metadata cannot by itself
prove that a bulletin's printed issue time is genuine; reviewers must inspect
the source. A later bulletin can inform a retrospective reference label but
must never be a forecast predictor.

Two named independent reviewers must each label every case on five separate
`present`/`absent`/`uncertain` tasks. A positive requires physical rationale
and an inventoried dated source whose validity overlaps the forecast case.
An uncertainty requires a reason. The roster, rubric and analysis-code hashes
must be frozen before review and are compared with the actual files when the
validator runs. Each form declares that detector outputs remained hidden. A
third adjudicator, distinct from both
reviewers, resolves every disagreement in a separate record after both forms
are complete. Neither original form is overwritten. The validator emits an
audit of counts and agreement only; detector comparison is a later, separately
frozen analysis after real labels exist.

Run the validator only with actual reviewer material:

```text
python scripts/build_regime_annotation_review.py --packet <packet.json> \
  --map-root <existing-local-packet-dir> --source-ledger <sources.json> \
  --source-root <existing-local-source-dir> --roster <roster.json> \
  --reviews <two-reviewer-forms.csv> --adjudications <adjudications.csv> \
  --output <new-local-audit.json>
```

The source-ledger JSON has a `sources` array; each entry needs `source_id`,
`kind`, `uri`, `local_path`, `sha256`, `issued_utc`, `valid_start_utc`,
`valid_end_utc` and `use_rights`. The roster JSON needs `reviewer_ids` (exactly
two), `adjudicator_id`, `frozen_utc`, `rubric_sha256` and
`analysis_code_sha256`. Each review CSV row needs `case_id`, `reviewer_id`,
`rubric_version`, `annotation_utc`, `blind_to_detector_outputs=true`, and the
five task labels. A positive also needs `{task}_rationale` and semicolon
separated `{task}_evidence_ids`; an uncertainty needs
`{task}_uncertainty_reason`. Each disagreement gets a separate adjudication
row with `case_id`, `task`, `adjudicator_id`, `decision`,
`adjudication_utc`, `rationale`, `evidence_ids` and
`blind_to_detector_outputs=true`. The command is write-once and fails on incomplete or
unadjudicated forms. Source files and reviewer identities should be retained
in access-controlled local storage unless publication rights and consent are
established. No actual form is supplied in this repository.

## Source availability and rights

The [IMD All India bulletin archive](https://mausam.imd.gov.in/responsive/all_india_forcast_bulletin_archive.php)
currently exposes a short recent list rather than the 2014–2016 daily archive
needed for these cases. The [RSMC historical bulletin archive](https://rsmcnewdelhi.imd.gov.in/report.php?internal_menu=MzQ%3D)
lists 2014–2016 cyclone names, but its year pages did not expose usable
case-level attachments in this inspection. Separate official
[2014](https://rsmcnewdelhi.imd.gov.in/uploads/report/27/27_4e1280_rsmc-2014.pdf),
[2015](https://rsmcnewdelhi.imd.gov.in/uploads/report/27/27_9bbd0d_RSMC-2015.pdf)
and [2016](https://rsmcnewdelhi.imd.gov.in/uploads/report/27/27_ad292c_rsmc-2016.pdf)
annual RSMC reports are discoverable. They may support dated
cyclone/depression references after byte-level intake and geographic review;
they do not cover all low-pressure systems or active/break and geographic
forcing. The [RSMC best-track page](https://rsmcnewdelhi.imd.gov.in/report.php?internal_menu=MzM)
also lists those years. Best tracks are post-season synoptic records, not
forecast-time predictors.
The [RSMC copyright policy](https://rsmcnewdelhi.imd.gov.in/copyright-policy.php)
requires permission for partial or full reproduction. None of these landing
pages is a dated, byte-verified case label. IMD provides a historical-data
contact on its bulletin page; the project owner must secure case-level access
and permitted use, or arrange direct expert review.

## Independent reviewers still needed

The project needs two meteorologists and a separate adjudicator, with their
identities, affiliation/competence, conflict declaration, consent for local
record retention and blind-review dates recorded before annotation. They
must receive the frozen case list, local forecast maps, a dated source ledger
and the fixed five-task rubric. The broad synoptic region and forecast map
limit a western-disturbance judgment; `uncertain` is the appropriate response
when the evidence does not resolve it. Neither a missing bulletin nor a
pseudo-label can be silently treated as `absent`.

## Separate winter western-disturbance corpus

`data/manifests/research_pilot/winter_regime_readiness_v1.json` records a
**zero-case readiness state**, separate from JJAS. The present project archive
inventory (`docs/122`, `docs/138`) concerns June–September forecasts; the
rainfall verification domain ends at 22°N and the 500-hPa trough heuristic had
an unstable, failed association with northwest-India rainfall. It cannot be
relabelled as a western-disturbance classifier or transported to winter.

A winter study needs genuine December–March forecast cycles over a wider
northwest-India/Himalayan domain, upper-air context and versioned source hashes;
dated IMD synoptic bulletins or authorized experts; an independent label rule;
and a reserved period before any scoring. The manifest intentionally names no
year split or case as admitted. The owner must settle source access, document
rights, reviewer recruitment and winter acquisition scope before a corpus can
be built. No 2026 rainfall values or sealed test outcomes were opened here.

## Scientific boundary

These annotations can assess construct validity of the regime indicators.
They cannot by themselves establish calibrated regime probabilities or an
improvement in rainfall correction. The latter still needs same-case matched
global controls and its own untouched evaluation period. No scientific API,
public warning or operational-skill status changes follow from this work.

## Validated local handoff, 7 October

The older ignored `annotation_template.csv` from `docs/154` used `{task}_evidence` and omitted `blind_to_detector_outputs`; the stricter `docs/161` validator requires `{task}_evidence_ids` and an explicit blind declaration. `scripts/prepare_regime_reviewer_handoff.py` now verifies all 72 frozen map hashes and writes two separate blank, validator-compatible reviewer CSVs, an empty adjudication CSV, an empty source-ledger template, a roster template with the actual rubric/code hashes and a handoff manifest under ignored `data/processed/expert_regime_review_handoff_v1/`. It is write-once. The roster still has **blank real names and freeze time**; no form is complete or accepted as a label. Every cited positive source must now overlap the case window; the validator rejects a mixed list containing an unrelated document. Nine focused handoff/annotation tests passed.

Three official RSMC annual PDFs for 2014, 2015 and 2016 were downloaded within a 65 MB per-file cap, kept only under ignored local `data/raw/evidence/regime_review_rsmc_annual_v1/`, and SHA-256 receipted by `regime_support_docs_v1.json` (manifest SHA-256 `bb43d176327bbc7f78991e190d1e95bfe54b48ce115245f544017737e9cebdf8`). The intake check passes. These annual reports are **bibliographic aids**: exact issuance times, relevant pages, case validity, and the scope of reproduction permission have not been established. They are deliberately absent from the annotation source ledger and cannot be used as automatic positive labels. The [RSMC copyright policy](https://rsmcnewdelhi.imd.gov.in/copyright-policy.php) must be honored before sharing report content.

Exactly what the project owner must obtain: (1) identities, meteorological qualifications, independence/conflict declarations and local-retention consent for two reviewers plus a distinct adjudicator; (2) their agreed UTC roster-freeze time before annotation; (3) dated, case-relevant bulletin pages or other synoptic records with exact issue/validity time, source URL, local byte hash and permitted use, or explicit expert justification using the forecast maps where a bulletin is unavailable; (4) two complete blind forms and a separate adjudication form; (5) authorization and data for a wider-domain December–March winter corpus if western-disturbance rainfall relevance is to be claimed. No request has been sent to an outside person.
