# VarshaSetu Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

Meteorological and research reviewers at MoES/NCMRWF, Smart India Hackathon judges, and scientific decision-support viewers evaluating historical monsoon-rainfall forecasts.

## Product Purpose

VarshaSetu presents a scientifically traceable comparison between raw GEFS rainfall forecasts, frozen post-processed forecasts, and IMD observations, with forecast-only regime context, calibrated extreme-rain probabilities, FSS, district summaries, and held-out verification.

## Positioning

The product connects actual NWP reforecast inputs to canonical 24-hour rainfall reconstruction, frozen model outputs, and transparent verification. It is not a standalone black-box rainfall predictor or a generic weather dashboard.

## Operating Context

The present release is a read-only historical scientific prototype based on the frozen 2017 train, 2018 validation/calibration, and untouched 2019 test workflow. It is suitable for technical presentation and historical case exploration, not current-date operational forecasting.

## Capabilities and Constraints

- Forecast Explorer compares Raw GEFS, Phase 2B M2 Global XGBoost correction, and IMD observation on the same grid and scale.
- Phase 2C provides Heavy and Very Heavy probabilities, FSS, district aggregations, and official historical demo cases through read-only science APIs.
- Frozen scientific artifacts, thresholds, metrics, corpus, and model identities must not be changed by frontend work.
- Missing or invalid scientific data must be labeled unavailable, never fabricated or displayed as zero.
- The legacy frontend remains recoverable until the replacement passes its acceptance workflow.

## Brand Commitments

Canonical name: VarshaSetu. Subtitle: Regime-Aware AI Post-Processing of Monsoon Rainfall Forecasts. Tagline: Bridging Raw NWP Forecasts and Actionable Rainfall Intelligence. The interface must communicate institutional scientific credibility, modern meteorological intelligence, and honest limitations without consumer-weather, generic SaaS, cyberpunk, or student-dashboard styling.

## Evidence on Hand

The repository contains hash-verified Phase 2B/2C artifacts, read-only `/api/science` endpoints, 2019 held-out results, district geometry and aggregations, a video-case catalogue, and scientific methodology/reporting documents. The legacy frontend is not visual authority for the replacement.

## Product Principles

1. Preserve provenance and temporal causality.
2. Keep maps and measurements directly comparable.
3. Make limitations as visible as improvements.
4. Distinguish historical-prototype evidence from operational readiness.
5. Serve frozen results; never recompute science from the browser.

## Accessibility & Inclusion

Target WCAG AA, keyboard operation, readable numeric alternatives to maps and charts, reduced-motion support, responsive viewing, and scientific palettes that do not depend on red/green alone.
