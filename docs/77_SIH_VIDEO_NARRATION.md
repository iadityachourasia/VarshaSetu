# Phase 3C — Spoken SIH video narration

**00:00–00:20 — Problem.** “Numerical weather prediction gives us gridded
rainfall forecasts, but raw output can carry systematic errors. For monsoon
decisions, the forecast, event risk, and uncertainty all need to be
interpretable and verified.”

**00:20–00:40 — Product and evidence.** “VarshaSetu is a historical scientific
prototype for post-processing NOAA GEFSv12 reforecasts against IMD gridded
rainfall. On a frozen, common-case 2019 JJAS test set, the selected Global
XGBoost correction reduces RMSE from 19.7735 to 17.8487 millimetres—9.73
percent. Those are season-wide API results, not a claim about every case.”

**00:40–01:25 — Forecast comparison.** “Here is an official Day 3 case. The
three maps share a geographic extent, valid-cell mask, and rainfall legend:
Raw GEFS, VarshaSetu’s corrected forecast, and the IMD observation reference.
This grid is 0.25 degrees. Weather Visualization smooths only the display;
the selected-cell measurements remain the original scientific values. This
particular case improves slightly in RMSE, but it is an example, not the
evaluation denominator.”

**01:25–01:45 — Regime.** “A separate forecast-only classifier estimates
Active, Break/Weak, and Low/Depression-influenced regimes. Its validation is
agreement with a defined pseudo-label method, not independent accuracy
against observed meteorological regime truth. The primary Global XGBoost
rainfall correction does not need regime inputs; hard and soft routing were
tested as comparators.”

**01:45–02:15 — Extremes.** “For this heavy-rain example, separate calibrated
models estimate the probability of at least 64.5 and at least 115.6
millimetres in 24 hours. A probability is not a rainfall amount. We show
Brier score, precision–recall discrimination and reliability with event
counts, including the sparse upper bins that limit very-heavy confidence.”

**02:15–02:40 — District.** “Pinned public district boundaries are intersected
with the validated rainfall grid. The resulting case-specific table reports
area-weighted rainfall and event probabilities. Coverage is limited to the
validated domain, and polygon/grid overlap remains an approximation—not
a nationwide operational service.”

**02:40–03:15 — Verification.** “The full held-out comparison includes Raw
GEFS, linear MOS, Global XGBoost, hard regime routing and soft mixture of
experts. Global XGBoost wins overall deterministic RMSE. Soft routing edges
hard routing, but neither beats Global ML on RMSE. Raw GEFS remains stronger
on the reported deterministic heavy-event CSI/ETS, and stronger than Global
XGBoost on every evaluated FSS scale.
In this **2019 retrospective benchmark**, very-heavy categorical false-alarm
ratio is about 0.872 at the frozen probability threshold. Lower average error does not guarantee better extreme-event
spatial skill.”

**03:15–03:40 — Methodology and close.** “The science is chronological:
2017 trained, 2018 validated and calibrated, and the held-out 2019 final test
has been completed. Forecast-time fields drive the models; observations are reserved for
targets and verification. This read-only interface demonstrates validated
historical artifacts. Live ingestion and operational readiness remain future
work.”

Use natural pacing and trim pauses, not caveats. If official SIH submission
limits differ, edit timing while preserving all scientific qualifications.

**Optional separate 2025 line, only with a sourced report/Verification summary
and additional time:** “A different historical operational-GEFS experiment
trained in 2023, selected its Ridge model in 2024, and completed one final
2025 evaluation. On 232 cases, selected Ridge reduced RMSE from 16.1657 to
15.5736 millimetres, or 3.66 percent. Raw GEFS still had stronger heavy and
very-heavy spatial FSS than that selected Ridge model. These experiments are not pooled, and neither is a
live operational service.” Do not narrate 2025 over 2019 case maps.
