# Judge Q&A — Phase 5B

Anticipated questions, grouped by theme, with honest answers grounded in
`docs/presentation/FINAL_PPT_FACTS.md` and the canonical claims in
`docs/91_SCIENTIFIC_COMMUNICATION_ALIGNMENT.md`. Where the honest answer is
"we haven't built that yet" or "this is a real limitation," say so plainly
— a confident wrong answer costs more credibility than an honest gap.

## Data and provenance

**Q: Is this using real weather data, or synthetic/simulated data?**
Real historical data on both tracks: NOAA GEFSv12 reforecast (Track A) and
historical NOAA operational GEFS (Track B), both paired with IMD gridded
rainfall observations. Nothing is synthesized. Reanalysis products (ERA5/
IMDAA) inform regime-label research and diagnostics elsewhere in the
project, but are never presented as the raw forecast itself.

**Q: Is this live data — is it forecasting today's weather right now?**
No. Both benchmarks are completed, historical, one-time final tests —
2019 and 2025 respectively. This is a research prototype, not an
operational forecasting system, and it makes no live forecast.

**Q: What's the difference between the two "tracks" I keep seeing?**
Track A uses the NOAA GEFSv12 *reforecast* product (2017 train / 2018
validate / 2019 final test). Track B uses historical NOAA *operational*
GEFS (2023 train / 2024 validate / 2025 final test). Different lineages,
different case populations — we never combine their scores into one
number.

## Scientific method

**Q: Why two separate benchmarks instead of one clean number?**
Because they're genuinely different experiments with different forecast
sources and different populations. Pooling them would misrepresent both.
Showing them side by side, honestly labeled, is more defensible than a
single inflated headline.

**Q: How do you know you're not leaking future information into the
forecast?**
Every dynamic predictor is either the forecast itself (precipitation,
wind, humidity, pressure, geopotential, TCWV, ensemble statistics) or a
static or calendar field known at forecast issuance time. (Static
geography such as elevation and coastline distance is permitted by the project
rules but is **not used by any current model**; it is the planned basis for the
coastal/orographic regime and is not in the frozen feature schema.) No observed-at-valid-time value or future
reanalysis state is used as a predictor — this is an explicit,
non-negotiable project rule (`AGENTS.md` §3.4).

**Q: What does "held-out" or "final test" actually mean here — could you
retrain if the result looked bad?**
No. Both 2019 and 2025 are one-time final tests: models were selected and
frozen using only earlier years (2017-18 for Track A, 2023-24 for Track B)
before either holdout was opened. Neither was reopened for retuning after
unsealing. That's a structural governance rule, not a promise — the
Provenance DAG and Holdout Governance timeline on the Scientific Audit page
show the actual sealed → authorized → unsealed-once lifecycle.

## Regime awareness (the project's core research question)

**Q: Does the "regime-aware" part actually help?**
Not conclusively, and we say so directly. On overall RMSE (and MAE and bias),
regime-aware routing (hard or soft) did not beat the plain global ML model on
either benchmark; soft mixture-of-experts improves on hard routing for RMSE,
but neither beats Global XGBoost. That is an honest negative result for the
headline metric — not a hidden failure.
There is a narrower, post-hoc finding we also report, clearly labelled as
exploratory (`docs/106`): on heavy-rain categorical and spatial skill
(CSI, FSS) in the 2024 validation year and the consumed 2025 test, the
regime-aware models were ahead of Raw GEFS, and in 2025 ahead of the global
model too, but only in the predicted Low/Depression pseudo-regime. In the
Active regime the global model was as good or better, and in the Break/Weak
regime every corrected model essentially stopped forecasting heavy rain and
lost to Raw. This was seen on the operational-era track only: on the 2018/2019
reforecast track the regime-aware models forecast almost no heavy events and
scored below Raw (`docs/108`). It is a hypothesis for future work, not a
demonstrated benefit — these are pseudo-labels, one year each, with optimistic
intervals.

**Q: What is a "pseudo-regime," and why not just call it "the regime"?**
Because it is a forecast-only classifier output, not an independently
observed ground-truth monsoon regime. We deliberately call it a
forecast-only pseudo-label everywhere in the UI and documentation, so
nobody mistakes a model's internal state for verified meteorological
classification.

**Q: If regime-awareness doesn't help, why build it at all?**
Because "does it help" was the research question, not a foregone
conclusion — a negative result, honestly reported, is still a real
scientific contribution, and the architecture remains available for future
work (e.g., richer regime features, different routing strategies) once the
current negative result is understood.

## Extreme rainfall skill (the hardest honest answer)

**Q: Your model reduces RMSE — does that mean it's better at warning about
extreme rain?**
Not for the headline model, and this is the single most important caveat in
the whole project: in the 2025 test, Raw GEFS retained *stronger* extreme-rain
spatial skill (FSS) than our RMSE-selected model (preselected M1 Ridge), at
every neighbourhood scale tested. Lower average error and better extreme-event
skill are different properties, and improving one did not improve the other
for that model. We have not shown that *no* corrected model can do better:
post-hoc diagnostics on the same frozen predictions (`docs/106`) show the
regime-aware models scoring above Raw on heavy-rain FSS/CSI on the operational-era
track while still being worse on mean error; on the 2018/2019 reforecast track every
corrected model, including M3/M4, scores below Raw (`docs/108`). None of the
corrected models is reliably good at very-heavy events. Those post-hoc numbers do not change the declared headline
and were not used to choose a model.

**Q: Then why report the RMSE win at all if it doesn't help on extremes?**
Because RMSE and extreme-event spatial skill are genuinely different,
useful metrics that answer different questions — RMSE about
typical-magnitude accuracy, FSS about localized extreme-event detection.
Reporting one without the other would be the actual dishonesty; reporting
both, together, is the whole point of this project's verification
protocol.

**Q: What's the false-alarm rate on your extreme-rain probability
warnings?**
High. At the frozen decision thresholds, heavy-rain FAR is about 0.696 and
very-heavy FAR is about 0.855, even though both models have positive Brier
Skill Score against a naive reference. We show the FAR number next to the
BSS number specifically so it's never read as "this is reliable enough to
issue warnings."

## Product and scope

**Q: Can I see district-level results for 2025?**
Yes, as a historical replay (`docs/107`). District Intelligence now also
serves 2024 and 2025: each district's raw, corrected (M1 by default, M2–M4
selectable), calibrated heavy/very-heavy probability and area fraction, next
to the IMD observed values, area-weighted with the same overlap weights as
the 2019 track. Limits we state up front: it is a read-only aggregation of
frozen grids (not a new model or a separately frozen artifact), 2023 has no
district product. District-level verification was run separately under a
protocol frozen before any result (`docs/112`, `docs/113`): regime-aware models
detect district heavy-rain events better than Raw, but their district-mean
error is worse and very-heavy detection is not improved — a trade-off, not a
general district-level skill claim, and post-hoc for 2025.

**Q: Can I see the ensemble comparison for [some other year]?**
Only 2025 has the matched five-member-ensemble-vs-calibrated-ML comparison.
Other years show an honest "not available for this selection" message.

**Q: Is this ready for operational deployment at NCMRWF/IMD?**
No. This is explicitly a historical scientific prototype. It does not
ingest live NWP data, has known extreme-skill limitations, and has not been
through operational verification, infrastructure, or governance review.
Its purpose right now is to demonstrate and honestly evaluate a
regime-aware post-processing methodology, not to replace an operational
system.

## Reproducibility and "gotcha" questions

**Q: How do I know these numbers aren't just made up for the demo?**
Every headline number is hash-pinned to a frozen result artifact (SHA-256
`04a7fc2a…` for the 2025 result), and an automated frontend test compares
every displayed value against that exact file. The Scientific Audit page
shows the full provenance chain and holdout lifecycle for anyone who wants
to check.

**Q: Why did you pick this specific case for the demo — is it your best
one?**
No, deliberately not. The official 2025 demo case
(`20250714_day2_24h`) was chosen because its case-level RMSE delta is
near-neutral (+0.046 mm), specifically to avoid giving the false impression
that the corrected model always wins. Full reasoning is in
`docs/presentation/OFFICIAL_DEMO_CASES.md`.

**Q: What happens if I ask you to show me a case where your model made
things worse?**
It exists, and we're not hiding it: e.g., the 2019 case
`20190807T000000Z_day2_24h` (Day 2, 200 observed heavy cells) had the
correction *worsen* RMSE (49.49 → 50.16 mm) — it's one of the six
descriptive video-catalogue cases chosen deliberately to include failures,
not just successes (`docs/67_VIDEO_DEMO_CASE_CATALOGUE.md`).

**Q: What's the single biggest limitation of this project right now?**
That improving overall rainfall RMSE did not improve extreme-event spatial
skill in the more recent 2025 benchmark — the exact metric that matters
most for heavy-rain warnings. That is the project's own stated primary
open problem, not a footnote.
