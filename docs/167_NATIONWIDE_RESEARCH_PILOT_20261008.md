# Nationwide model development research pilot — 8 October 2026

## Scope and evidence boundary

This is a local Track B **development** experiment for JJAS Day 1–3 rainfall
on the 129 × 135 IMD RF25 grid. Its forecast inputs are operational GEFS
initializations; its reference is locally held annual IMD RF25 for 2023 and
2024. The 2023 cases are fitting and date-block out-of-fold selection data.
The 2024 cases are already consumed development evaluation. No 2026
observation was opened or paired, and this work makes no independent-year
skill, operational-warning, or public-product claim. Track A reforecasts and
the existing regional M2 are separate experiments.

The protocol was written and SHA-256 sealed **before** national atmospheric
feature decoding, fitting, or observation pairing. It specifies the source
role, land mask, atmospheric context, forecast-only 22-feature contract,
+3→+27 / +27→+51 / +51→+75 h accumulation windows, date-block splits,
M0–M4 ladder, event thresholds, support rules, and no-promotion boundary.
The 2021 simplified geoBoundaries ADM2 polygon overlap defines a research
land mask of 5,105 cells. It does not establish official district geometry
or national reference coverage. Unavailable cells remain missing, never zero.

## Reproducible corpus and model ladder

The source-checked national atmospheric context is 5–40°N, 60–105°E at
0.5°. All dynamic features come from the forecast cycle; static location,
terrain, coast and calendar data are treated separately. The local feature
corpus contains 172 2023 and 156 2024 cases, with three 24-hour leads.
The 2023 training set has 838,844 same-case paired cells. The sealed 2024
set has 760,812 paired cells from 156 cases (102 initialization dates).

The named arms are M0 Raw GEFS, M1 Ridge MOS, M2 global XGBoost research
correction, M3 hard pseudo-regime residual and M4 soft pseudo-regime residual.
M2 direct and residual candidates were compared using 2023 initialization
date folds. **Neither passed the frozen heavy-rain CSI selection rule**:
Raw 0.07166, direct 0.06565, residual 0.06743. The residual candidate was
kept as a labelled research arm, not selected for product use. Only two
pseudo-regime specialists had enough distinct dates; the third had 29 dates
against the 30-date minimum and was withheld. Forecast-derived pseudo labels
are not independent meteorologist labels.

All 156 2024 forecast arrays were sealed before the 2024 reference was
opened for this experiment. The reference was then used once for the stated
development comparison, not for model promotion or a new independent test.

| Same 760,812 2024 pairs | RMSE mm/24 h | Heavy CSI | Very-heavy CSI |
|---|---:|---:|---:|
| M0 Raw | 16.8793 | 0.06567 | 0.02529 |
| M1 MOS | 15.6746 | 0.01443 | 0.00297 |
| M2 global research | 15.3562 | 0.10178 | 0.01466 |
| M3 hard pseudo-regime | 15.3840 | 0.10663 | 0.01560 |
| M4 soft pseudo-regime | 15.3894 | 0.10514 | 0.01592 |

The 1,000-resample initialization-date bootstrap gives M2 minus Raw national
heavy CSI 95% interval [0.01220, 0.05951]. That aggregate gain does not
overrule the failed 2023 selection gate or the regional failures. M2 heavy
CSI falls below Raw in the east/northeast (0.01931 versus 0.05835), east
coast peninsula (0.05004 versus 0.06350), and north of the old model domain
(0.02848 versus 0.06836). Very-heavy CSI falls below Raw nationally for
every corrected arm. The south-of-domain stratum has only 43 observed heavy
events; unsupported strata must remain explicit. The model default stays
**regional M2**.

## Extremes, ensemble and districts

2023 out-of-fold base predictions feed separate heavy (≥64.5 mm/24 h) and
very-heavy (≥115.6 mm/24 h) probability heads. Lead-aware isotonic
calibration is applied where development support exists, and outputs enforce
`P(very heavy) ≤ P(heavy)`. On consumed 2024 pairs, heavy Brier skill is
0.09833 and very-heavy Brier skill is 0.03651 against their climatology
references. These are **development** results, not independent reliability.
At the development-selected display thresholds, heavy event frequency is
54,535 forecasts versus 13,320 observations; very-heavy frequency is 9,606
versus 3,017. False-alarm ratios are 0.865 and 0.909 respectively. These
heads are research-only; there is no nationwide public warning threshold.

The full-grid ensemble-spread product is withheld. Existing P4E/P4F
member receipts cover a much smaller strict-QC population and do not
establish complete nationwide member fields for this corpus. The local
research district table uses 2021 simplified, non-official geometry:
735 polygons are represented with sparse sampled-grid weights and per-case
weighted coverage. It is a forecast-only experiment; its sampled coverage
must not be read as authoritative district area coverage. Redistribution
rights and official Survey of India boundary suitability remain open.

## Local product and verification

The `/india` page contains an opt-in 2024 historical research section. With
`VARSHASETU_LOCAL_NATIONWIDE_RESEARCH=1`, read-only endpoints expose the
sealed M0–M4 and probability grids on the national grid, a case catalogue,
scores, and non-official district tables. The API verifies the evidence
chain and prediction/table hashes on access, refuses 2026 cases, and returns
null for cells outside the research land mask. It does not alter the live
regional forecast pages or product default. Without the local flag the
research endpoint returns 404.

Immutable local manifests under `data/manifests/research_pilot/` include:

| Evidence | SHA-256 |
|---|---|
| `nationwide_research_protocol_v1.json` | `f342c99477702dee346bd8fbb4ab3ddbd7dea2e8d4241d26e8165b2555c73e26` |
| `nationwide_research_features_v1.json` | `f683eb1705ccd4deb7cacb55d80d049fa7d9bff09c3cdc522908389427bc3141` |
| `nationwide_research_fit_seal_v1.json` | `bdabca698f7365222e979088255c8d8cfd261dd6022ab7c2c87742ee3a4da2d1` |
| `nationwide_research_score_v1.json` | `09dd920d989bed829d2a415cffb5a120fd4888e65c554ab773be552022519652` |
| `nationwide_research_uncertainty_v1.json` | `e333b6397169112ba56960937ece4d29f58415bda8692eb902784d0fe371bc5d` |
| `nationwide_district_tables_v1.json` | `3d8b5f752798ce3ab1152f80f15e960b2dcc33478203ab8c007549f84994adbb` |

The ignored source and prediction arrays remain in the original local
checkout, not in Git. They should be preserved with their manifests. Run
`python scripts/nationwide_research.py check`,
`python scripts/summarize_nationwide_research.py check`,
`python scripts/build_nationwide_district_research.py check`, and
`python scripts/build_nationwide_district_tables.py check` for local
integrity. Do not rerun `fit` or `score` over the sealed evidence.

## Executed checks on 8 October 2026

| Check | Result |
|---|---|
| Full backend, `python -m pytest backend/tests -q --basetemp=data/pytest-nationwide-final -p no:cacheprovider --durations=5` | **832 passed** in 257.48 s |
| National protocol/features/fit/score hash check | Passed: 328 feature cases, 156 sealed 2024 predictions, 5,105 research land cells |
| Date-bootstrap uncertainty hash check | Passed: 102 initialization dates |
| District static weights and 156 table hashes | Both passed: 735 represented research polygons |
| Frontend `npm test -- --run` | **31 files, 212 tests passed** |
| Frontend `npm run lint` | Passed, exit 0 |
| Frontend `npm run build` | Passed; 19 static pages generated |
| India page Playwright with local research flag | **3 passed**, including research map and probability/no-promotion caveat |
| Frozen 2026 scorer `--preflight` | Correctly **blocked before observation read**: annual IMD reference and GEFS version review missing; 213 forecast cases |

The first sandboxed frontend test/build attempts failed on Windows
temporary-path access; unsandboxed reruns above completed successfully. The
first browser run found an unreadable probability status label. After the
label was fixed, a second run failed because its new assertion omitted the
word “probability”; the corrected third run passed all three tests. Neither
interrupted nor failed run is counted as a pass. Free C: space after the
build was 194,946,187,264 bytes (about 181.5 GiB), above the 50 GiB floor.

New implementation files are `backend/app/ml/nationwide_research.py`,
`scripts/nationwide_research.py`,
`scripts/summarize_nationwide_research.py`,
`scripts/build_nationwide_district_research.py`,
`scripts/build_nationwide_district_tables.py`,
`backend/app/api/nationwide_research.py`,
`frontend-v2/src/lib/api/nationwide-research.ts`, and
`frontend-v2/src/components/india/nationwide-research.tsx`. The API router,
India page, tests, `.gitignore`, project index, and API/UI contracts were
updated. Existing frozen experiments and 2026 forecast files were not
rewritten. National forecast arrays remain local and ignored; the small
manifests and hashes are reviewable in the working tree.

## Release decision and shortest path

The national development research view is permitted locally. National
corrected live inference, corrected district release, ensemble spread, and
warning use are **not** promoted. Next: obtain and license a complete annual
2026 IMD reference; document actual 2026 and training-year GEFS deployment
versions and selected-predictor comparability; obtain independent regime
reviews; confirm authorized district geometry; then run the already frozen
2026 one-shot scorer only after all source gates pass. Any future national
model needs a fresh prespecified protocol and a genuinely untouched
comparable year, with region/lead/extreme/reliability gates. The 2024
development scores cannot serve that role.
