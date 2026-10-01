# Phase 7D (Stage 2): forecast-time forcing strength inside the geographic zones

Date: 2026-10-01. Protocol: `docs/115`, frozen v3. Execution spec: `backend/app/evidence_data/phase7/zone_stage2_spec_v1.json`, SHA-256 `3755e06c…33ff`, committed **before** any Stage 2 result existed.
Zones: `docs/116`. Stage 1: `docs/117`. Nothing was trained, tuned or selected; the frozen M0–M4 grids were re-aggregated by forcing-strength stratum.

## What the spec settled (the protocol was silent or ambiguous; no rule changed)

- Forcing = component × PWAT, from forecast U850, V850 and PWAT resampled bilinearly from the 0.5° context grid to the 0.25° cells, and the static unit vectors of `docs/116`. Day K uses the forecast snapshot at lead 24·K hours. Q700 is not used by the formula and is not read. No observation is read to compute forcing (the function has no observation argument; a test asserts this).
- COASTAL cells use the onshore component, OROGRAPHIC cells the cross-barrier component. Cells that are both have both definitions applying, so both are reported separately and no combined index was invented. OTHER has no defined component and is not stratified.
- Strata are the weak (≤ lower tercile), middle and strong (> upper tercile) groups of forcing, with cut-points fitted on the **training year only** (Track A 2017, Track B 2023) over every zone cell of every training case. The evaluation years never refit them.
- Strata support gate: ≥ 30 cases, ≥ 600 cell-case pairs and, for categorical scores, ≥ 30 observed heavy events; otherwise `insufficient_support` and no number.
- Q3 = metric(strong) − metric(weak) per model with the same paired whole-case bootstrap (2,000 resamples, seed 26080). FSS is not reported.

## Gates

- The three strata of each zone and component add up exactly to the Stage 1 zone totals in all four populations, and those reproduce the published evidence (`docs/108`).
- Every stratum of every zone and component met the cell-case-pair gate; strata without enough heavy events (for example the thin middle strata) show `insufficient_support` instead of a score.
- Evidence: `zone_stage2_{A_2018,A_2019,B_2024,B_2025}.json`, `zone_stage2_summary.json`, `zone_stage2_manifest.json` (SHA-256 `155380e43f769070e77633fcf8a9ae415210ee2bfe193b18b16a57bcdd1e1af7`), built by `scripts/build_phase7_zone_stage2.py`.

## Training-year cut-points (forcing, kg m⁻¹ s⁻¹ proxy)

A lower cut-point of 0.0 means at least a third of the zone's training pairs have no onshore or cross-barrier flow at all (for example offshore flow on the east coast), so the weak stratum is the no-forcing group.

| Track (fit year) | Zone and component | Training pairs | Lower cut | Upper cut |
|---|---|---:|---:|---:|
| A (2017, 258 cases) | COASTAL onshore | 54,180 | 0.0 | 136.5 |
| A (2017, 258 cases) | OROGRAPHIC cross_barrier | 63,210 | 0.0 | 63.9 |
| A (2017, 258 cases) | COASTAL_AND_OROGRAPHIC onshore | 28,122 | 0.0 | 133.8 |
| A (2017, 258 cases) | COASTAL_AND_OROGRAPHIC cross_barrier | 28,122 | 225.1 | 433.0 |
| B (2023, 200 cases) | COASTAL onshore | 42,000 | 0.0 | 158.7 |
| B (2023, 200 cases) | OROGRAPHIC cross_barrier | 49,000 | 0.0 | 51.7 |
| B (2023, 200 cases) | COASTAL_AND_OROGRAPHIC onshore | 21,800 | 0.0 | 172.5 |
| B (2023, 200 cases) | COASTAL_AND_OROGRAPHIC cross_barrier | 21,800 | 217.9 | 425.4 |

## Results

**Track B 2024 (development evidence)**, 183 cases

| Zone and component | Heavy events weak / middle / strong (strong share) | Heavy frequency bias, weak: Raw / M2 / M4 | Heavy frequency bias, strong: Raw / M2 / M4 |
|---|---|---|---|
| COASTAL onshore | 351 / 63 / 1,729 (81%) | 0.15 / 0.83 / 1.07 | 0.25 / 1.28 / 1.40 |
| OROGRAPHIC cross_barrier | 141 / 4 / 423 (74%) | 0.28 / 0.09 / 0.10 | 0.24 / 0.17 / 0.18 |
| COASTAL_AND_OROGRAPHIC onshore | 1,195 / 19 / 1,413 (54%) | 0.11 / 0.37 / 0.43 | 0.14 / 0.69 / 0.77 |
| COASTAL_AND_OROGRAPHIC cross_barrier | 53 / 109 / 2,465 (94%) | 0.15 / 0.23 / 0.23 | 0.13 / 0.57 / 0.64 |

**Track B 2025 (POST-HOC EXPLORATORY ANALYSIS OF THE COMPLETED 2025 FINAL TEST)**, 232 cases

| Zone and component | Heavy events weak / middle / strong (strong share) | Heavy frequency bias, weak: Raw / M2 / M4 | Heavy frequency bias, strong: Raw / M2 / M4 |
|---|---|---|---|
| COASTAL onshore | 295 / 59 / 1,487 (81%) | 0.14 / 0.22 / 0.25 | 0.13 / 0.42 / 0.47 |
| OROGRAPHIC cross_barrier | 166 / 10 / 477 (73%) | 0.49 / 0.00 / 0.02 | 0.31 / 0.04 / 0.04 |
| COASTAL_AND_OROGRAPHIC onshore | 1,008 / 39 / 1,311 (56%) | 0.10 / 0.08 / 0.11 | 0.05 / 0.17 / 0.24 |
| COASTAL_AND_OROGRAPHIC cross_barrier | 86 / 305 / 1,967 (83%) | 0.16 / 0.00 / 0.06 | 0.06 / 0.15 / 0.21 |

**Track A 2018 (development evidence)**, 251 cases

| Zone and component | Heavy events weak / middle / strong (strong share) | Heavy frequency bias, weak: Raw / M2 / M4 | Heavy frequency bias, strong: Raw / M2 / M4 |
|---|---|---|---|
| COASTAL onshore | 293 / 43 / 1,428 (81%) | 0.20 / 0.00 / 0.00 | 0.32 / 0.32 / 0.11 |
| OROGRAPHIC cross_barrier | 86 / 10 / 378 (80%) | 1.30 / 0.00 / 0.00 | 0.46 / 0.08 / 0.01 |
| COASTAL_AND_OROGRAPHIC onshore | 1,304 / 6 / 1,479 (53%) | 0.12 / 0.10 / 0.03 | 0.17 / 0.07 / 0.03 |
| COASTAL_AND_OROGRAPHIC cross_barrier | 20 / 221 / 2,548 (91%) | n/a / n/a / n/a | 0.15 / 0.09 / 0.03 |

**Track A 2019 (POST-HOC EXPLORATORY ANALYSIS OF THE COMPLETED 2019 FINAL TEST)**, 255 cases

| Zone and component | Heavy events weak / middle / strong (strong share) | Heavy frequency bias, weak: Raw / M2 / M4 | Heavy frequency bias, strong: Raw / M2 / M4 |
|---|---|---|---|
| COASTAL onshore | 389 / 81 / 2,531 (84%) | 0.65 / 0.00 / 0.00 | 0.49 / 0.20 / 0.05 |
| OROGRAPHIC cross_barrier | 217 / 14 / 771 (77%) | 0.84 / 0.00 / 0.00 | 0.57 / 0.04 / 0.00 |
| COASTAL_AND_OROGRAPHIC onshore | 2,035 / 20 / 2,020 (50%) | 0.20 / 0.09 / 0.01 | 0.25 / 0.06 / 0.01 |
| COASTAL_AND_OROGRAPHIC cross_barrier | 67 / 169 / 3,839 (94%) | 0.31 / 0.00 / 0.00 | 0.22 / 0.08 / 0.01 |

## What the evidence shows

1. **Forcing strength is a strong discriminator of where heavy rain falls, most clearly for the cross-barrier component.** For the Western Ghats coast with the cross-barrier definition the strong stratum holds 83 to 94 % of the zone's observed heavy events; for the coastal-only (onshore) and orographic-only zones it holds 73 to 84 %. For the Ghats coast with the onshore definition it holds only 50 to 56 %, so about half of the heavy events there occur when the coast-normal onshore component is weak or zero. The cross-barrier component describes Ghats rain better than the onshore component as defined here.
2. **Raw still underforecasts heavy rain under strong forcing.** Even in the strong cross-barrier stratum of the coastal-and-orographic zone Raw forecasts only a small fraction of the observed heavy events (frequency bias 0.06 to 0.22), so the Stage 1 deficiency is not a weak-forcing artefact: it is concentrated exactly where the forcing is strongest.
3. **Corrected-model behaviour under strong forcing is track- and year-dependent.** On Track B 2024 M2 to M4 recover a large share (frequency bias 0.57 to 0.77 on the Ghats coast) but only 0.15 to 0.24 in 2025; on Track A they recover almost none (0.01 to 0.09). This matches Stage 1 and must not be generalised from one track or year.
4. **Small strata need their event counts.** Where a stratum holds few heavy events the scores are unstable and Raw can overforecast (for example Track A OROGRAPHIC weak, Raw frequency bias above 1 on 86 events in 2018); middle strata are often too thin to score and are reported as `insufficient_support`.

## Q3, applied literally

The analogue of the protocol rule (development interval of strong minus weak excludes zero, final-test point estimate has the same sign, decision metrics heavy frequency bias and heavy CSI) gives:

| Track | Q3 decision tests | Development-significant | Same-sign (forcing gaps) | Expected by chance (rough) |
|---|---:|---:|---:|---|
| A (2018 to 2019) | 24 | 15 | 15 | about 1.2 and 0.6 |
| B (2024 to 2025) | 40 | 22 | 19 | about 2.0 and 1.0 |

Heavy CSI depends on how common the events are, and heavy events are far more common in the strong stratum, so a large part of the CSI differences reflects the base rate rather than model skill; the frequency-bias contrast is the more comparable measure. Q3 is descriptive only: it does not change the Stage 1 recommendation, and the tests share cases and models.

## Consequences

- Stages 1 and 2 are complete. Under the protocol's coverage mapping the coastal/orographic requirement may now move from **PLANNED** to **PARTIAL** with the wording "rule-based geographic zones with stratified verification; no coastal/orographic specialist model". That change belongs with serving this evidence (API and page), because every number on `/compliance` must be resolved from hash-verified evidence; it has not been made yet.
- It would **never** become IMPLEMENTED on this evidence. That needs Stage 3, which is not authorised and needs its own protocol, a model that beats M2 on held-out data and a test period that no frozen data currently provide.
- The most defensible scientific statement is narrow: the frozen models, raw and corrected, underforecast heavy rain on the Western Ghats coast under strong cross-barrier forcing, in both tracks, with corrected-model behaviour varying by track and year.

## Limitations

Coarse 0.25° geometry; forcing uses 0.5° forecast winds and a moisture-flux proxy; zones and strata are rule-based conventions, not a validated regime; one control-member snapshot per case; tests are dependent and intervals optimistic; 2024 is a reused development year and 2019 and 2025 are consumed holdouts analysed post-hoc; historical replay only.

## Tests

`backend/tests/test_zone_stage2.py` (14): forcing signature and arithmetic, exact bilinear resampling, terciles and strata partition, Q3 formulas, strata support gate, spec and manifest hash chain, per-year partition and training-year cut-points, unsupported strata carry no number, summary consistency and post-hoc labels.

Gate: `P0_7_STAGE2_COMPLETE`.
