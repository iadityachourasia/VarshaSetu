# Nationwide nonlinear probability development — 9 October 2026

> **Lineage corrigendum:** Read `docs/178` before interpreting the frozen
> `observation_values_read_before_freeze` flag or the phrase "before 2024
> pairing" below. Earlier v3 work used 2023 reference values and earlier
> v1/v2 studies had already consumed 2024; v4 sealed forecasts before only
> its **own** 2024 scoring step. Its failed development decision is unchanged.

> **Spatial follow-up:** `docs/179` verifies same-case warning-map FSS at a
> common 0.05 probability cutoff. It is a consumed-2024 diagnostic and does
> not change the failed very-heavy Brier gate or model default.

## Scope and chronology

This is a **consumed-2024 development experiment**, not independent validation
or a released warning product. The v2 fold/cutoff repair failed its Brier gate
(`docs/168`); the forecast-only cutoff transport audit (`docs/175`) identified
lead calibration as the source of zero very-heavy cutoff exceedances. The next
candidate tests a fixed nonlinear head with monotone Platt calibration and
cutoff selection on persisted-precision nested out-of-fold predictions. It is
a distinct head/calibration method, not a post-hoc lowering of v2's cutoff.

The first v3 execution froze protocol SHA-256
`94b413b11d5e6cce5588708098aeefd53f47016e8828c43cf10a57c4a01bfa3f`
before fitting. Training saved two heads and nested out-of-fold data, but
XGBoost's native Windows path loader denied access to the partial model path.
It produced **no fit seal, 2024 prediction, or score**. Its partial directory
is preserved. A new v4 runner changed only the reload to XGBoost's bytearray
API. That reload passed a toy model test and a 128-cell forecast-only smoke
check using the saved v3 model bytes, before v4 was frozen.

The v4 protocol was write-once frozen **before v4 fitting or its own 2024 pairing**:
`data/manifests/research_pilot/nationwide_probability_protocol_v4.json`, SHA-256
`93b6f93c0e174f80efa2175a97932b9968ea8697f799c534467e8633fb247516`.
It pins runner/helper hashes, the 22 forecast-time national features, source
manifests, thresholds, model hyperparameters, split recipe, decision gates and
the failed v3 lineage. Its fit uses 172 cases and 838,844 eligible cells from
2023 only. The XGBoost heads have 80 depth-3 trees each, CPU hist mode and
four threads. Outer three-fold, inner two-fold initialization-date blocks and
three-day embargo protect the nested calibration; final calibration uses
three inner folds. Per-lead Platt fits require at least 30 events and
nonevents and a positive slope. Very-heavy probability is capped at the
heavy probability. Warning cutoffs come from coherent nested out-of-fold
probabilities converted to the same float32 precision as saved predictions.
The v4 recipe and cutoff choices preceded **v4's own** 2024 reference pairing;
prior v1/v2 2024 results had already been consumed and motivated the candidate
(`docs/178`).

The v4 fit seal, SHA-256
`e9073dc770fef5ff6a8074786e229178ea75b0ae505c82a8410e858155e20814`,
records 156 hashed 2024 predictions and that the **v4 fit/prediction step**
had not opened the 2024 reference. It passed the lineage/hash check before scoring.
There were 11,364 heavy and 2,440 very-heavy 2023 fit events. Nested cutoffs
were 0.17 and 0.14, respectively. The 2024 score is write-once, SHA-256
`91bb11098c2f082c5ba650999e21794b0cbb52dda5713c7d373e14f9042f3758`.
The score reads no 2025/2026 observation. The 2026 independent-test seal and
four source/version gates in `docs/159` and `docs/174` remain intact.

## Same-case 2024 development result

The v1, v2 and v4 probabilities were checked on the same 156 cases and
760,812 reference-valid forecast cells. The observed counts are 13,320 heavy
(≥64.5 mm/24 h) and 3,017 very heavy (≥115.6 mm/24 h). Lower Brier is better.

| Head | v1 Brier | v2 Brier | v4 Brier | v4 Brier skill | v4 minus v1, 95% date interval | v4 minus v2, 95% date interval |
|---|---:|---:|---:|---:|---:|---:|
| Heavy | 0.015524 | 0.016496 | **0.015303** | 0.1112 | −0.000221 [−0.000442, −0.000010] | −0.001193 [−0.001635, −0.000763] |
| Very heavy | **0.003807** | 0.003901 | 0.003823 | 0.0323 | +0.0000166 [−0.000103, +0.000122] | −0.0000781 [−0.000241, +0.0000563] |

The paired intervals resample initialization dates 1,000 times. They do not
eliminate spatial or serial dependence. Positive Brier skill against a 2023
climatology does not establish superiority over v1, v2 or an independent year.

| v4 head/cutoff | Forecast/observed events | CSI | ETS | POD | FAR | Assessment |
|---|---:|---:|---:|---:|---:|---|
| Heavy, 0.17 | 16,925 / 13,320 (1.27×) | 0.168 | 0.158 | 0.326 | 0.743 | Supported as a development diagnostic only |
| Very heavy, 0.14 | 5,672 / 3,017 (1.88×) | 0.097 | 0.095 | 0.255 | 0.864 | High false-alarm fraction; not a public warning rule |

At a **common fixed 0.05 cutoff**, v4 issues 19,399 very-heavy warnings
against 3,017 observed events (6.43×), with CSI 0.067 and FAR 0.928. This
illustrates why the nested cutoff and fixed display threshold cannot be
silently interchanged. The very-heavy 0.1–0.2 reliability bin predicts a mean
0.142 while observing 0.0549 over 5,520 cells; higher populated bins are
also generally overconfident. Lead breakdowns, ten-bin reliability and all
same-cutoff categorical comparators are in the hash-receipted score JSON.
For very-heavy rain, v4 Brier is 0.003636/0.003699/0.004063 on Day 1/2/3.

The **prespecified diagnostic gate fails**: the v4 very-heavy Brier intervals
against both v1 and v2 cross zero. Its Brier skill, heavy Brier guardrail and
very-heavy nested-cutoff frequency gate pass. The observed development
improvement for heavy rain does not license a headwise cherry-picked product
change. V1, v2, failed v3 and v4 remain research evidence. The regional M2
is still the corrected-rainfall product default; there is no v4 API, live,
district or public warning promotion.

## Reproduction and remaining gate

`python scripts/nationwide_probability_v4.py check` validates the protocol,
model, nested out-of-fold, 156 prediction and score hashes. Focused v3/v4
tests cover fold disjointness, calibration monotonicity and support, persisted
precision cutoff, model byte reload and v3/v4 artifact separation.

| Check | Final result |
|---|---|
| `python -m pytest backend/tests/test_nationwide_probability_v3.py backend/tests/test_nationwide_probability_v4.py -q --basetemp=data/pytest-probability-v4-targeted-20261009 -p no:cacheprovider` | **6 passed**, exit 0 |
| `python -m pytest backend/tests -q --basetemp=data/pytest-probability-v4-final-20261009 -p no:cacheprovider --durations=5` with the known Windows socket-enabled setup | **866 passed**, exit 0, 158.44 s |
| `python scripts/nationwide_probability_v4.py check` | Exit 0, protocol/fit/156 predictions/score receipt verified |
| V2, cutoff diagnostic and national model integrity checks | All exit 0, frozen hashes unchanged |
| `python scripts/score_2026_with_clearance_gate_v2.py --preflight` | Exit 0, `BLOCKED_BEFORE_OBSERVATION_READ`, 213 forecast cases, no 2026 score |
| `git diff --check` | Exit 0; existing Windows line-ending notices only |

This increment created
`backend/app/ml/nationwide_probability_v3.py`,
`backend/tests/test_nationwide_probability_v3.py`,
`backend/tests/test_nationwide_probability_v4.py`,
`scripts/nationwide_probability_v3.py`,
`scripts/nationwide_probability_v4.py`, this report, and the v3/v4
write-once manifests and local processed artifacts. It updated
`docs/00_INDEX.md`. No frontend, API, live-worker, frozen v1/v2 or 2026
forecast artifact changed in this increment. Final free C: space was
178.49 GiB, above the 50 GiB floor. No file was committed.

An untouched, source-comparable reference year and independently demonstrated
very-heavy reliability are still needed before considering any national
probability promotion. The missing complete authorized annual IMD 2026 file,
actual 2026 GEFS deployment identity, 2023 training patch evidence and
selected-predictor comparability are external blockers. No available result
supports a nationwide operational warning claim.
