# Phase 9B: geography-aware correction (M5a), frozen-protocol results

Date: 2026-10-01. Protocol: `backend/app/evidence_data/phase9/geoaware_protocol_v1.json` (SHA-256 `e04c0504dfc7a8f68f020241010b82344d89ab8270eef816e6fd5f43359f393c`), frozen and committed **before any training**; selection freeze
`geoaware_selection_freeze.json` (SHA-256 `dd63aec4f53866f34932a10dad3eb9869fd3a92926a425319bd7ca87c5438f22`), committed **before any 2024 or 2025 prediction**; manifest `geoaware_manifest.json` (SHA-256 `89077bcc8ea18644bcb86409d17048093a58c366e2256fbf54e46d3d715e7ef2`).
This is a development-only experiment (option D1(b) of `docs/124`): there is no independent test, 2024 is a reused development year, and 2025 is a post-hoc analysis of a completed final test.

## Result in one paragraph

**The pre-registered decision rule is not met: "no evidence that geography-aware features improve on M2".** The reason is specific. The declared candidate (A3: the 22 existing features plus static
geography plus forecast-time forcing) improves heavy-rain detection on the Western Ghats coast by a large, replicated margin (heavy CSI up by +0.120 in 2024
and +0.133 in 2025 over M2, both intervals excluding zero), but in 2024 it **over-forecasts**: overall bias +5.17 mm against the 1.5 mm guardrail and overall RMSE worse
than M2 by +1.68 mm (tolerance 0.2 mm). In 2025 it passes every criterion on the post-hoc population. A candidate that is better at the target and worse overall in one year is not a model
that can be called an improvement, and the rule says so.

## What was done, in order

1. Protocol frozen, with the proposed values of `docs/124` accepted as written (record in the file), and committed.
2. Four feature arms trained on 2023 only with the 16-configuration grid and the embargoed five-block cross-validation (320 fits), selection by the guardrailed rule on pooled out-of-fold predictions, selection freeze written and committed.
3. Only then 2024 and 2025 predictions, after a gate: the recomputed M0 to M4 reproduce the published zone evidence exactly in both years (maximum difference at floating-point noise, counts exact).
4. The pre-registered decision rule applied literally.

## Selection on the training year (2023 out-of-fold; Raw reference: RMSE 15.09 mm, heavy CSI 0.068)

| Arm | Configurations passing G1, G2 and G3 | Selected | Out-of-fold RMSE (mm) | Heavy CSI | Very-heavy frequency bias |
|---|---|---|---:|---:|---:|
| A0 | 0 of 16 | **none** | none | none | none |
| A1 | 2 of 16 | #6: reg:squarederror, capped_event, depth 6, 200 rounds | 14.61 | 0.152 | 0.058 |
| A2 | 0 of 16 | **none** | none | none | none |
| A3 | 1 of 16 | #5: reg:squarederror, capped_event, depth 4, 350 rounds | 14.40 | 0.179 | 0.054 |

The **control arm (A0, same recipe, no new features) and the forcing-only arm (A2) have no candidate**: every configuration forecasts almost no very-heavy rain (guardrail G3), the behaviour already seen in M2.
Only arms with static geography produce configurations that pass. The selected A3 passes G3 narrowly (0.054 against a floor of 0.05) and G2 narrowly (bias +1.39 mm against 1.5).

## Evaluation (selected models; M0 Raw, M2 global XGBoost and M4 shown as comparators)

**2024 (development evidence; a reused year)**, 183 cases

| Population | Model | RMSE (mm) | Bias (mm) | Heavy CSI | Heavy frequency bias | Very-heavy CSI |
|---|---|---:|---:|---:|---:|---:|
| All land cells | M0 | 17.13 | -0.85 | 0.075 | 0.21 | 0.015 |
| All land cells | M2 | 16.85 | +2.24 | 0.213 | 0.71 | 0.044 |
| All land cells | M4 | 17.26 | +3.15 | 0.227 | 0.80 | 0.035 |
| All land cells | A1 | 17.79 | +4.41 | 0.277 | 1.17 | 0.117 |
| All land cells | A3 | 18.53 | +5.17 | 0.276 | 1.27 | 0.118 |
| Ghats coast (coastal and orographic) | M0 | 30.81 | -10.71 | 0.059 | 0.13 | 0.006 |
| Ghats coast (coastal and orographic) | M2 | 27.41 | -3.77 | 0.263 | 0.54 | 0.030 |
| Ghats coast (coastal and orographic) | M4 | 27.09 | -2.95 | 0.279 | 0.61 | 0.039 |
| Ghats coast (coastal and orographic) | A1 | 28.35 | +7.02 | 0.381 | 1.27 | 0.169 |
| Ghats coast (coastal and orographic) | A3 | 28.76 | +7.38 | 0.383 | 1.28 | 0.159 |
| Interior (other) | M0 | 13.00 | +0.94 | 0.032 | 0.38 | 0.013 |
| Interior (other) | M2 | 12.60 | +2.76 | 0.021 | 0.44 | 0.000 |
| Interior (other) | M4 | 13.18 | +3.54 | 0.030 | 0.52 | 0.000 |
| Interior (other) | A1 | 12.95 | +3.68 | 0.016 | 0.36 | 0.000 |
| Interior (other) | A3 | 13.90 | +4.41 | 0.027 | 0.64 | 0.000 |

**2025 (POST-HOC EXPLORATORY ANALYSIS OF THE COMPLETED 2025 FINAL TEST)**, 232 cases

| Population | Model | RMSE (mm) | Bias (mm) | Heavy CSI | Heavy frequency bias | Very-heavy CSI |
|---|---|---:|---:|---:|---:|---:|
| All land cells | M0 | 16.17 | -1.26 | 0.048 | 0.22 | 0.020 |
| All land cells | M2 | 15.00 | -0.93 | 0.073 | 0.15 | 0.001 |
| All land cells | M4 | 15.22 | +0.25 | 0.088 | 0.20 | 0.009 |
| All land cells | A1 | 15.15 | +0.51 | 0.125 | 0.37 | 0.018 |
| All land cells | A3 | 14.84 | +0.64 | 0.135 | 0.35 | 0.033 |
| Ghats coast (coastal and orographic) | M0 | 26.27 | -9.60 | 0.033 | 0.07 | 0.018 |
| Ghats coast (coastal and orographic) | M2 | 24.62 | -7.48 | 0.083 | 0.13 | 0.000 |
| Ghats coast (coastal and orographic) | M4 | 24.20 | -6.11 | 0.106 | 0.18 | 0.009 |
| Ghats coast (coastal and orographic) | A1 | 23.09 | -1.05 | 0.201 | 0.47 | 0.034 |
| Ghats coast (coastal and orographic) | A3 | 22.13 | -0.82 | 0.216 | 0.45 | 0.058 |
| Interior (other) | M0 | 14.13 | +0.05 | 0.053 | 0.45 | 0.014 |
| Interior (other) | M2 | 12.76 | -0.47 | 0.004 | 0.02 | 0.000 |
| Interior (other) | M4 | 13.03 | +0.69 | 0.021 | 0.06 | 0.000 |
| Interior (other) | A1 | 12.90 | +0.40 | 0.017 | 0.09 | 0.000 |
| Interior (other) | A3 | 12.81 | +0.47 | 0.007 | 0.06 | 0.000 |

## Paired differences (whole-case bootstrap, 2,000 resamples, optimistic intervals)

| Year | Population | Comparison | Heavy CSI | RMSE (mm) | Bias (mm) |
|---|---|---|---|---|---|
| 2024 | Ghats coast | A3 minus M2 | +0.120 [+0.085, +0.153] | +1.35 [-0.04, +2.74] | +11.15 [+9.96, +12.46] |
| 2024 | Ghats coast | A3 minus A1 | +0.002 [-0.009, +0.016] | +0.41 [-0.18, +1.04] | +0.36 [-0.15, +0.91] |
| 2024 | All cells | A3 minus M2 | +0.063 [+0.042, +0.086] | +1.68 [+1.09, +2.34] | +2.93 [+2.54, +3.38] |
| 2024 | All cells | A3 minus A1 | -0.001 [-0.014, +0.012] | +0.74 [+0.24, +1.31] | +0.76 [+0.41, +1.17] |
| 2024 | Interior | A3 minus M2 | +0.007 [-0.000, +0.016] | +1.30 [+0.69, +2.04] | +1.65 [+1.28, +2.08] |
| 2024 | Interior | A3 minus A1 | +0.011 [+0.002, +0.019] | +0.94 [+0.26, +1.72] | +0.74 [+0.37, +1.16] |
| 2025 | Ghats coast | A3 minus M2 | +0.133 [+0.101, +0.162] | -2.49 [-3.08, -1.86] | +6.66 [+6.08, +7.23] |
| 2025 | Ghats coast | A3 minus A1 | +0.015 [-0.004, +0.033] | -0.96 [-1.39, -0.56] | +0.23 [-0.22, +0.66] |
| 2025 | All cells | A3 minus M2 | +0.062 [+0.045, +0.079] | -0.16 [-0.33, +0.00] | +1.57 [+1.44, +1.71] |
| 2025 | All cells | A3 minus A1 | +0.009 [-0.003, +0.023] | -0.31 [-0.45, -0.17] | +0.13 [-0.02, +0.27] |
| 2025 | Interior | A3 minus M2 | +0.003 [-0.001, +0.008] | +0.05 [-0.06, +0.17] | +0.94 [+0.81, +1.08] |
| 2025 | Interior | A3 minus A1 | -0.009 [-0.022, -0.001] | -0.09 [-0.19, +0.00] | +0.07 [-0.07, +0.20] |

## The pre-registered decision, criterion by criterion

| Criterion | 2024 | 2025 (post-hoc) |
|---|---|---|
| A3 beats M2 on heavy CSI in the Ghats-coast zone, interval excluding zero | **met** (+0.120 [+0.085, +0.153]) | **met** (+0.133 [+0.101, +0.162]) |
| Overall RMSE not worse than M2 by more than 0.2 mm | **not met** (+1.68 [+1.09, +2.34]) | met (-0.16 [-0.33, +0.00]) |
| Guardrails G1, G2, G3 on the evaluation population | G1 True, **G2 False**, G3 True | G1 True, G2 True, G3 True |
| Sign of the zone difference agrees across the two years | yes | yes |
| **Rule met** | **no** | |

Consequence stated by the protocol: "no evidence that geography-aware features improve on M2"; the coastal/orographic requirement stays **PARTIAL**.

## What the data show beyond the verdict (descriptive, not a claim of improvement)

- **The heavy-rain gain on the Ghats coast is large and appears in both years.** Heavy CSI in that zone is 0.383 (2024) and 0.216 (2025) for A3 against 0.263 and 0.083 for M2, and 0.059 and 0.033 for Raw.
- **The cost is over-forecasting in 2024.** A3's bias in the zone is +7.4 mm (M2: -3.8) and its heavy frequency bias is above one overall, which also worsens RMSE in the interior. In 2025 the same model is close to unbiased
  in the zone (-0.8 mm against -7.5 for M2). The year-to-year difference was **not diagnosed**; the event-weighted training pushes forecasts upward, which is a candidate explanation, not a finding.
- **In 2024 A3's overall RMSE is also worse than Raw's** (18.53 against 17.13 mm), although better than Raw inside the Ghats-coast zone; in 2025 it is better than Raw overall.
- **Static geography does the work; forecast forcing adds nothing detectable.** A1 (static only) has nearly the same heavy-rain gain as A3, and A3 minus A1 on zone heavy CSI is indistinguishable from zero in both years.
- **The interior gains nothing.** Heavy CSI there is no better than M2's, and A3's interior RMSE is worse in 2024.
- **Very-heavy forecasting is no longer zero** for the geography-aware models (very-heavy CSI 0.118 in 2024, 0.033 in 2025, against 0.044 and 0.001 for M2) but remains low and unstable between years.
- **The recipe itself cannot forecast very-heavy rain.** The control arm has no guardrail-passing configuration at all; this concerns the squared-error regression recipe, not geography.

## Limits that apply to every statement here

One training year; 2024 is a reused development year and 2025 a post-hoc analysis of a completed final test; no independent test; the operational-era track only; historical replay, not warning skill;
optimistic bootstrap intervals; coarse 0.25-degree zones.

**Contamination notice.** The 2024 and 2025 results have now been seen. Any redesign that responds to them (a smaller event-weight cap, a bias correction, zone-restricted use) is **post-hoc relative to those years** and cannot be judged on them.
A fair test of any such design needs new data: option D1(a) of `docs/124` (independent 2021 and 2022 years) or waiting for 2026.

## Protocol gap, disclosed

The protocol attributes a gain to geography only if A3 beats the internal control A0, but it did not anticipate that A0 could have no configuration passing the guardrails. The comparison cannot be made, so attribution is recorded as
**undetermined** rather than forced (`geoaware_decision.json`, field `protocol_gap`). The descriptive fact that 0 of 16 control configurations and 2 of 16 and 1 of 16 of the static-geography arms pass the guardrails in 2023 is reported above but is not the pre-registered test.

## What may and may not be said

| May say | Must not say |
|---|---|
| Adding static geography to the post-processing model markedly improved heavy-rain detection on the Western Ghats coast in both evaluation years, in development evidence. | That the model is better, validated, or implemented. It failed the pre-registered rule because it over-forecast in 2024. |
| The improvement is mostly attributable to static geography features, not to forecast forcing. | That geography is proven to be the cause (attribution is undetermined). |
| The squared-error regression recipe alone never forecasts very-heavy rain. | That very-heavy skill is solved. |

## Consequences

- The coastal/orographic row on `/compliance` is unchanged (PARTIAL), and nothing in the app presents these models.
- Nothing frozen was modified: M0 to M4, feature registry v1, zone protocol v3 and the Stage 1 and 2 evidence are untouched; the new files live under `backend/app/evidence_data/phase9/`.
- Options for the owner: stop here with the honest negative-and-positive result; or write protocol v2 (for example a bias-controlled recipe) **and** obtain independent years (D1(a)) to test it; or restrict ambitions to the heavy-probability models, which are the tool built for extremes.

Tests: `backend/tests/test_geoaware.py` (13, pure functions equal the protocol) and `backend/tests/test_geoaware_evidence.py` (7, hash chain, the selection re-derived from the stored table, baselines equal to the Stage 1 evidence, the decision re-derived from the evaluation files).

Gate: `P3_GEOAWARE_M5A_RESULT_RECORDED_RULE_NOT_MET`.

## Addendum: serving the experiment (2026-10-01)

The frozen Phase 9 files are now served read-only and hash-verified at `/api/science/evidence/geoaware/{overview,evaluation?year=}` (`backend/app/api/geoaware.py`) and shown at the page `/geoaware` ("Geography-Aware Experiment"). The API walks the whole chain (protocol, selection freeze, manifest, every listed file and the references between them) and answers 503 on any mismatch; the 2025 evaluation carries the mandatory post-hoc label; an unknown year is a structured 404. The page shows the negative verdict first, the per-year tables for Raw, the global model and the two selected geography arms, the selection table (including the arms with no eligible configuration), and the protocol gap. Its narrative sentences are derived from the decision file's flags, not typed. Tests: `backend/tests/test_geoaware_api.py`, `frontend-v2/src/lib/api/geoaware.test.ts`, `frontend-v2/tests/e2e/geoaware.spec.ts`. Nothing here changes any result, status or the PS coverage row.

