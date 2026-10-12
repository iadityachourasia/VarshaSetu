# UI Scientific Data Contract

## Primary rule

> The frontend renders scientific values; it does not invent them.

The `/india` page is an India-wide **Raw NWP** view. Its visual research-boundary mask and the verification reference-valid mask are different. The page keeps the regional corrected-model domain explicit and links to the same-case regional comparison; unsupported India-wide corrected or probability cells must never be colored as model output.

The Regime Intelligence entry displays a development notice for the 2019
reforecast context or when the operational catalogue is unavailable. Verified
operational-era data remains available when present; an artifact integrity
failure remains an explicit error rather than a development notice.

Ensemble & Uncertainty currently has a matched 2025 operational-era subset.
The shared navigation targets that experiment directly, and unsupported
Ensemble URLs redirect there instead of showing a misleading 2019 empty state.

Any scientific number must map to a documented backend field or a transparent arithmetic transformation of backend fields defined in this file.

## Current issues to remove

The audited frontend contained examples of:
- multiplied synthetic rainfall trajectory values,
- static exceedance probabilities,
- static dataset mean cards,
- static accuracy/improvement text,
- controls not connected to backend computation,
- filters not connected to analysis,
- a “calibrated” label stronger than the evidence.

## Required mapping

| UI element | Source |
|---|---|
| Raw rainfall | backend forecast field |
| Corrected rainfall | backend prediction field |
| Observation | backend historical reference field only |
| Correction magnitude | corrected − raw |
| Regime probability | regime API |
| Heavy probability | calibrated threshold API |
| Very-heavy probability | calibrated threshold API |
| RMSE | verification report |
| ETS/CSI/POD/FAR | verification report |
| FSS | verification report |
| Model improvement | calculated in backend/report |
| District statistics | district aggregation API |
| Data source | forecast-run metadata |
| Lead | forecast-run metadata |

## Map layout

Judge-facing core map:
- Raw NWP.
- Corrected forecast.
- Observation.
- Error reduction.

Use synchronized extent/color scale where scientifically appropriate.

## Historical replay labels

When observation is available:
- explicitly show `Historical Replay`.
- include `Valid Time`.
- include `Lead`.
- include `Observation Source`.

Do not label it “live forecast.”

## Operational mode

Observation panel should be hidden or marked unavailable until after verification data arrive.

## Probability display

For the experimental live-cycle API, render its `probability_status` alongside every selected probability map and the district probability columns. `RESEARCH_ONLY_RELIABILITY_UNVERIFIED` means the model output may be inspected as research evidence but must not be presented as a public warning or a reliability-validated new-cycle probability. The live rainfall map defaults to M2, the frozen product default; M3/M4 remain labelled comparison arms.

Display:
- event definition,
- accumulation period,
- probability,
- calibration status.

Example:

```text
Heavy Rain ≥64.5 mm / 24h
Probability: 42%
Calibration: validated on 2024 validation period
```

If calibration is not validated:
```text
Prototype probability — calibration under evaluation
```

## Insufficient-event state

For zero/too-few positive cases:

```text
Insufficient held-out events for reliable calibration assessment.
```

Never show:
```text
Brier 0.0000 — Excellent
```

without event context.

## Dashboard hierarchy

### First screen
Answer:
1. What did raw NWP predict?
2. What did VarshaSetu change?
3. Why?
4. Was it better?

### Verification screen
Answer:
1. Does it improve aggregate held-out skill?
2. Does it improve heavy-rain events?
3. At what spatial scale?
4. Does regime awareness add value?

## Allowed client-side computations

Safe:
- display formatting,
- percentage formatting,
- simple difference if both source values supplied,
- chart transformations that preserve values.

Not safe:
- generating new scientific probability values,
- multiplying one forecast into a time series,
- manufacturing confidence intervals,
- changing metric definitions.

## Scientific placeholder design

If backend not ready, use:

```text
Not yet implemented
```

or a visibly labeled design placeholder.

Never use realistic fake numbers in production/demo mode.

## Nationwide development research view (8 October 2026)

The original national probability fields have failed a method audit and must
display an explicit unvalidated-reliability/warning-cutoff notice. The separate
v2 repair candidate failed its consumed-2024 comparison and is not a product
field (`docs/168`). The Raw India map uses a centre-in-polygon visual mask;
the national model research map uses positive polygon overlap. The UI must
explain this footprint difference rather than imply identical land coverage.
When the 2025 homepage case index is missing or cannot reconcile, label its
pinned historical benchmark as a frozen result instead of silently implying a
live API case series.

The opt-in section on `/india` consumes only
`/api/science/research/nationwide/{overview,verification,cases,grid,districts}`. Its
model scores, 129 × 135 map cells, probability values, district rows,
coverage, and evidence hashes must be server supplied. The frontend may
format values and filter district rows, but must not synthesize missing
cells, warning thresholds, or skill. Keep the 2024 consumed-development,
research-geometry, unvalidated-probability, and no-promotion labels visible
whenever a corrected or probability field is shown. A disabled local API
must render an unavailable state. Other forecast pages retain their
existing geographic and scientific scope until separately verified.
The verification detail may filter only server-supplied region/lead score
blocks. It must show identical paired-cell support, heavy-event contingency
counts, spatial FSS and date-block uncertainty with their limitations.
The regional live map displays source track, model, lead/window, finite-cell mask
count and evidence hashes. The versioned live district API carries its own
common valid-cell mask, lead and initialization. The table shows each row's represented
grid coverage and the count withheld below the 95% gate. It must state that
represented-grid coverage is not full-district area coverage.

The India page groups Raw forecast exploration, Raw verification, and the
opt-in development comparison in that order. The research district table may
filter and paginate server-supplied rows on the client; pagination changes
only visibility, not values, coverage, or ordering. The section navigation
must remain keyboard-accessible and must not obscure the historical and
no-promotion labels on narrow screens.

## Page-level experiment context and QC display (9 October 2026)

The app-shell experiment/year selector applies only to the historical case
workspace (`/`, `/forecast`, `/casebook`, `/extremes`, `/ensemble`, `/regimes`,
and `/districts`). Pages with their own source population or local selection,
including `/india`, `/live`, `/zones`, and `/verification`, must not inherit an
unrelated global year label. Their own cycle, period, source track, and evidence
status remain visible in the page content.

On the experimental live page, a withheld lead must have a short readable QC
summary. The exact source error remains available in an expandable technical
detail for auditability. This formatting does not change the source mask, lead
eligibility, or scientific output. Narrow-screen select controls must display
their selected values without clipping or page-wide horizontal overflow.
Evidence tables that scroll within their own container must be reachable by
keyboard and show a visible focus outline; they must not widen the page.

The six homepage feature tiles are short descriptions of implemented views,
not a second verification scorecard. They name Forecast Explorer, Regime
Intelligence, Extreme Rain, Ensemble & Uncertainty, District Intelligence,
and Verification Lab, with the pseudo-regime, five-member subset, and regional
district limits stated in their captions. Numerical skill remains in the
source-scoped benchmark and verification sections.
Each tile is a full-area link to its matching implemented page; the ensemble
route resolves to the supported 2025 subset. Keyboard activation and a visible
focus state must work without changing the six-card layout.
