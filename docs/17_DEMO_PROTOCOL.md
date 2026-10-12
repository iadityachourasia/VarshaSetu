# SIH Demo Protocol

## Demo goal

Prove:

> VarshaSetu applies a traceable correction to real NOAA GEFS rainfall and measures its regional historical skill against Raw and linear MOS on matched cases. Nationwide and regime-conditioned corrections remain research comparisons until their separate gates pass.

## October 2026 evaluator run (current evidence)

Use the regional NOAA GEFS Track B product and the frozen M2 global correction as the default. The live-cycle page opens on M2; M3/M4 are comparison arms because regime conditioning has not beaten the matched global control for heavy rain. Keep the original 2019 reforecast and 2024/2025 operational-era reports in their separate tracks. Open a stored historical case for the Raw/M2/IMD three-map comparison and aggregate metrics; then open the new-cycle page to demonstrate forecast-only processing without observations. Do not use a new cycle as a verification case.

Open `/india` to show the full 129×135 historical Raw GEFS forecast first; the display-footprint selector can reveal the complete grid including sea. Then follow its same-case link to the regional corrected comparison. State that India-wide Raw coverage is available, while corrected coverage beyond the established box has not passed promotion gates. The three-lead 2025-09-26 Raw bundle keeps this geographic demonstration available without the large ignored cache.

On the original local machine, the optional sealed 2024 nationwide M0–M4 research maps can be shown with `& .\scripts\demo\start-demo.ps1 -IncludeNationwideResearch`. This launches the API on `127.0.0.1` with the explicit local-only research switch and makes the failed selection and no-promotion status visible beside the maps. To change an already running launcher-owned demo from its default mode, run `& .\scripts\demo\stop-demo.ps1` first, then start with the switch. Never present those maps as live corrected India-wide skill.

The live-cycle probability field and district table report `RESEARCH_ONLY_RELIABILITY_UNVERIFIED`. The ordinal, nationwide v2 and nationwide v4 probability candidates failed their prespecified promotion gates; the frozen product remains unchanged. State this before discussing warning thresholds. The 2026 independent score is blocked at the four source/version gates in `docs/159`; no 2026 observation value has been opened. The first east-coast correction lost to Raw on consumed 2024 and is disconnected. The 72-case expert regime packet has no submitted labels. These are the explicit scientific limits of the current demo.

Before presenting, run `python scripts/audit_four_workstreams.py --check`, `python scripts/score_2026_with_clearance_gate_v2.py --preflight`, and `& .\scripts\demo\preflight-demo.ps1 -IncludeNationwideResearch` when the research switch is enabled (omit that switch in default mode). The last check includes the 129×135 India Raw grid, regional M2 district lineage and, in research mode, the sealed national no-promotion status. If an integrity check fails, stop the scientific walkthrough and investigate. A successful 2026 preflight must report `BLOCKED_BEFORE_OBSERVATION_READ`; it is a seal check, not a score. Use the locally cached replay, verified backend/API and frontend build as the offline fallback. Do not replace a missing API value with a slide or hand-entered metric.

The requirement-coverage page is an optional build-time view. Build with `NEXT_PUBLIC_SHOW_COMPLIANCE_PAGE=1` when the evaluator walkthrough includes `/compliance`; its note separates implementation coverage from scientific promotion. The default build hides that page and its API endpoint.

The demo is not primarily a website tour.

## Recommended 6–8 minute structure

### 1. Problem — 30 seconds
- raw NWP errors depend on weather regime,
- one correction may not work for all regimes,
- heavy rain is high impact.

### 2. Forecast metadata — 30 seconds
Show:
- forecast source,
- initialization,
- lead,
- valid date,
- accumulation.

### 3. Raw NWP — 30 seconds
Display raw rainfall grid.

### 4. Regime engine — 45 seconds
Display forecast-only pseudo-regime probabilities with their validation boundary.

Explain that regimes are inferred from forecast-time atmospheric fields, while independent expert labels and a demonstrated regime-correction gain remain open.

### 5. Corrected forecast — 45 seconds
Show corrected map beside raw.

### 6. Observation reveal — 45 seconds
For a held-out historical case:
- show observed map,
- raw error,
- corrected error.

### 7. Heavy-rain probability — 45 seconds
Show:
- correct 24-hour threshold definition,
- probability grid,
- district risk summary,
- calibration status.

### 8. Verification — 90 seconds
Show:
- Raw NWP,
- MOS,
- Global ML,
- Regime-aware,
- Soft MoE if implemented.

Mandatory:
- RMSE,
- ETS,
- CSI,
- POD,
- FAR,
- FSS.

Show event counts.

### 9. Regime ablation — 45 seconds
Answer:
> Does regime awareness itself add skill?

### 10. Limitations & scaling — 30 seconds
Briefly say:
- current data source/domain,
- what changes for NCMRWF deployment.

## Core visual

The most persuasive display is:

```text
RAW NWP | CORRECTED | OBSERVED | ERROR REDUCTION
```

same case, same valid time, same color scale.

## Demo integrity

Never:
- cherry-pick without saying it is a case study,
- imply one event proves aggregate superiority,
- hide a baseline that performs better,
- display fake probability curves,
- call historical observations “live.”

## Offline fallback

Prepare:
- cached model artifacts,
- cached forecast case,
- cached observation,
- cached API fixture,
- local frontend/backend.

The scientific story should work without internet.
