# Independent regime review protocol — prepared, not executed

Date: 2026-10-06. This is a handoff protocol for a meteorologist-led review.
No expert labels have been collected, and no independent expert-validation
score exists. The development result in `docs/146` uses objective retrospective
labels and must retain that description.

On 2026-10-07, the 72-case blinded forecast-only JJAS packet was prepared
under a separate frozen sampling protocol. See `docs/154_BLINDED_REGIME_REVIEW_PACKET.md`.
The packet does not include expert labels or bulletins and does not close this gate.

## Review unit and evidence

Use one forecast initialization, lead window and defined synoptic region as a
review unit. Pin its UTC issue and valid times, 24-hour rainfall window,
geographic footprint, forecast model/version, and bulletin source URL or
document hash. Each reviewer receives only the case identifier, dated
forecast-time synoptic fields, and independently issued dated IMD bulletins
available for retrospective adjudication. Hide VarshaSetu detector outputs,
corrected rainfall, verifying IMD rainfall and all model scores during the
first annotation pass. Record which information the bulletin itself contained
and its issue time; a later bulletin may inform a retrospective reference
label but must never become a forecast predictor.

## Five independent binary questions

For each unit, the reviewer records `present`, `absent`, or `uncertain` for
active monsoon, break/weak monsoon, low/depression influence,
coastal/orographic forcing and western disturbance. Overlap is allowed;
these are not mutually exclusive classes. Every positive needs a short cited
physical rationale and at least one timestamped evidence reference. Every
uncertain label needs a reason such as missing bulletin, ambiguous synoptic
evidence or disagreement between sources. Do not infer an event merely from
the model's high rainfall value. Western-disturbance rainfall relevance must
be assessed on a separately declared winter/pre-monsoon corpus; the JJAS
trough detector alone cannot establish that claim.

## Independence and adjudication

Freeze the sampled cases, rubric, bulletin inventory, reviewer identities,
annotation form and analysis code hash before opening model scores. Use at
least two independent reviewers per case. Preserve their original labels and
timestamps; disagreements go to an adjudicator who has not seen the model
scores. Publish agreement, prevalence, uncertain/abstention counts, and a
confusion table for each phenomenon. Keep years consumed by previous project
tests marked as such. Expert review on those years may assess construct
validity but cannot be presented as a fresh rainfall model test.

Only after adjudication should the five forecast-time detector outputs be
joined by immutable case IDs. Assess discrimination and reliability for each
binary target separately, with date-grouped uncertainty and explicit minimum
positive/negative support. Calibrate on development years only; reserve any
truly untouched year before reviewing its labels. A detector may be useful
for research even if it fails a probability-calibration gate, but its output
must then be called a score. Do not promote regime-conditioned correction
from this review alone: rainfall skill needs its own matched global control
and sealed-year guardrails.

## Required annotation fields

`case_id`, `forecast_source`, `source_version`, `issue_utc`, `lead_window_h`,
`region_id`, `reviewer_id`, `annotation_utc`, five independent labels,
`evidence_uri_or_hash`, `bulletin_issue_utc`, `rationale`, `uncertainty_reason`,
`rubric_version`. Keep a separate adjudication record rather than overwriting
the two original reviews. Do not place licensed bulletin text or IMD gridded
observations in the tracked repository without confirmed rights.

## Inputs still needed

An authorized reviewer or curated dated bulletin corpus, winter cases,
document rights, and a predeclared untouched evaluation period are required
before this protocol can produce independent validation. The current
research-pilot release reports this gate as **not met**.
