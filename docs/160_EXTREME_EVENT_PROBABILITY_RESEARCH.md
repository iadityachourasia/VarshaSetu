# Conditional extreme-event probability research

Date: 2026-10-07. Status: **completed consumed-development experiment; failed prespecified gate; research only**.

## Problem and scope

The frozen Track B heavy and very-heavy calibrators were fitted separately.
Projection made their output coherent, but the 90-lead June 2024 development
replay had negative very-heavy Brier skill and a 9.24-fold warning-frequency
ratio at the unchanged 0.05 cutoff. A subsequent pooled/lead-aware logistic
recalibration reduced warning frequency but worsened Brier and Brier skill.
Those results are in `docs/150`–`docs/153`; this study does not re-label them as
successful. It tests a distinct conditional event formulation.

## Prespecified method

The machine-readable authority is
`data/manifests/research_pilot/extreme_ordinal_probability_protocol_v1.json`,
SHA-256 `a8432a1e2d10f7b79f9697d9881fa9f9d2be2b67c8942b8a1e1b2bba93b91f96`.
It was sealed before fitting or selection-block scoring. The 2023-trained
Phase 4I logistic base scores and its 2024 chronological split are reused.
Only the 108 early calibration cases fit the candidate. Seven cases remain
purged; 68 later cases are the fixed comparison population. The study uses
all 1,301 cells per admitted case with no threshold or hyperparameter search.

Two unweighted logistic heads, each fixed at `C=0.1`, are fitted:

1. Heavy occurrence from the clipped heavy base-score logit.
2. Very-heavy occurrence *conditional on an observed heavy event* from the
   clipped very-heavy base-score logit.

At prediction time, `P(very heavy) = P(heavy) × P(very heavy | heavy)`, so the
24-hour event probabilities obey nesting by construction. The conditional
head is a research method, not a calibrated-status claim. It has no lead or
month terms and cannot silently adapt to June after the earlier failure.

The frozen isotonic-plus-projection and previously sealed pooled-logistic-plus-
projection predictions are controls on exactly the same selection cells.
The primary comparison is very-heavy Brier against frozen isotonic, with
heavy and joint Brier, BSS against unchanged 2023 climatology, ten-bin
reliability, event-bearing case counts, fixed-cutoff CSI/POD/FAR/ETS and
warning-frequency ratio reported together. A fixed-seed, 1,000-repeat
initialization-date paired bootstrap supplies descriptive Brier-difference
intervals. Its date clusters do not remove spatial or serial dependence.

The prespecified diagnostic gate requires a very-heavy Brier improvement
whose date-bootstrap 95% interval lies entirely below zero, positive
very-heavy BSS, heavy Brier degradation no greater than 0.0001, and a
warning-frequency ratio closer to one on a log scale at the unchanged cutoff.
Even passing this gate would only motivate a later independent evaluation.

## Data and release boundary

Phase 4I selected the base models and frozen controls using 2024 outcomes.
Consequently, the later 2024 block and any June replay are **consumed
development diagnostics**, not independent reliability evidence. The June
replay overlaps early-block fitting cases; it will only be considered under a
separately sealed no-refit protocol if the later-block diagnostic gate passes.
The previous June 9.24-fold warning-frequency finding remains unresolved
until that specific same-cell replay is run and evaluated.

No 2025 or 2026 outcomes enter this experiment. The 2026 independent-year
gate remains closed pending a complete comparable reference and GEFS
model-version decision. The scripts do not connect to the live worker, API,
dashboard or district product; no public warning, probability-calibration
or operational-skill claim follows from this study.

## Execution record

The source checkout is passed explicitly to
`scripts/experiment_extreme_ordinal_fit.py` and
`scripts/experiment_extreme_ordinal_score.py` and read without modification.
The model and every 2024 candidate/control probability are SHA-256 sealed
before the scorer reads purge or selection label values. The scorer refuses
changed source bytes or a changed prior control cache. No large source copy
is required.

The exclusive bounded fit finished. The read-only source check found 183 cases,
140,508 calibration rows, 9,107 purged rows and 88,468 later selection rows
with verified hashes. The prediction seal records 5,047 heavy and 1,256
very-heavy positive calibration cells, with very-heavy events in 71 calibration
cases. It records `selection_labels_decoded=false` at seal time. The saved
probabilities are coherent on every cell. The separate score is sealed in
`extreme_ordinal_probability_score_v1.json` and remains a consumed-2024
development diagnostic.

| Later selection population (88,468 paired cells) | Frozen projected | Ordinal candidate |
|---|---:|---:|
| Heavy Brier | 0.01179583 | 0.01184657 |
| Very-heavy Brier | 0.00336839 | 0.00337111 |
| Very-heavy BSS against fixed 2023 climatology | 0.09111 | 0.09038 |
| Very-heavy warnings / observed events at 0.05 | 1.489 | 1.337 |

The ordinal minus frozen very-heavy Brier difference is **+0.00000271**;
the 1,000-repeat initialization-date bootstrap 95% interval is
**[−0.00003736, +0.00003844]**. Heavy Brier worsens by +0.00005074.
The later block contains 329 observed very-heavy cells in 29 event-bearing
cases. The warning-frequency ratio moves closer to one, but the primary
Brier improvement and interval gates fail. The prespecified diagnostic gate
is `false`, and `promotion_eligible` is `false`. The June replay was not run;
the previously reported June 9.24-fold warning-frequency result is still
unresolved for this candidate. The complete score artifact contains the
lead-specific results, reliability bins, categorical counts and intervals.

Four focused model/protocol tests were present before fitting. The integrated
checkout reruns those and the sealed-score reproducibility check separately;
neither changes a frozen model or scientific product.

## Final diagnostic interpretation and next experiment boundary

The failed ordinal gate is final for protocol v1. A read-only decomposition of its already sealed 2024 selection score finds 58 observed very-heavy cells at Day 1, 112 at Day 2 and 159 at Day 3. Ordinal very-heavy Brier improves only at Day 1 (0.00245043 to 0.00237931), while it worsens at Day 2 (0.00326635 to 0.00330008) and Day 3 (0.00392766 to 0.00394288). At the unchanged 0.05 warning cutoff, the ordinal warning/event ratios are 1.07, 1.70 and 1.18 by lead; Day 2 remains the largest overforecast. The overall paired Brier interval crosses zero and the warning-ratio bootstrap intervals are wide. These are consumed-development diagnostics with correlated grid cells, not a new validation result.

No new fitted protocol was opened in this follow-up. The available 2024 outcomes have already selected the base calibrators and informed three failed/limited correction experiments; 2025 is a consumed test; and 2026 remains sealed behind source and version clearance. A future scientifically distinct calibration experiment needs a newly reserved evaluation period or a clearly declared development-only purpose with a frozen fit/selection split, fixed lead-specific warning policy and enough very-heavy event dates before any fit. The current product default and research-only probability status are unchanged.

The sealed ten-bin reliability table also shows why warning frequency and probability calibration must be assessed separately. In the 0–0.1 bin, the ordinal mean is 0.001365 against an observed 0.002889 over 88,256 cells; in the 0.1–0.2 bin, the mean is 0.1398 against 0.3534 over only 133 cells. Both bins underpredict on average, yet the fixed 0.05 decision rule still issues 1.34 warnings per observed very-heavy cell overall. Higher bins contain very few cells and are unstable. A threshold change might alter warnings without improving Brier reliability; choosing it from these consumed diagnostics would be another post-hoc selection. The paired date bootstrap and event-bearing case counts remain the relevant uncertainty summary.
