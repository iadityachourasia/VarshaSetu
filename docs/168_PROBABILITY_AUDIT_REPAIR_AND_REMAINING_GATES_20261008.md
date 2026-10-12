# Nationwide probability audit and repair candidate — 8 October 2026

## Decision

The original nationwide probability **inference arrays remain sealed historical
research output**, but their 2023 out-of-fold reliability/threshold evidence is
invalid for model selection. The original head-fold training features include
base-model out-of-fold predictions whose training folds include head-held dates.
The warning cutoff was selected on uncalibrated head probabilities but used
after lead calibration and coherence projection. The code and fold manifest
confirm both defects; the original builder and results were not rewritten.

The separate v2 candidate removes the fitted M2 input and uses only the 22
forecast-time national features. Its head folds train directly on dates outside
their held blocks, with a three-day embargo. Cutoffs are selected from the
calibrated, coherent 2023 out-of-fold probabilities that are actually displayed.
This fixes the two code-method defects for **v2**; it does not repair or erase
the original experiment. The v2 protocol SHA-256 is
`af59dcabed694beba184023adbb7e39f542b6ecb93a7366c8c1764abcdc9b8b3`.
It was written before the v2 fit or 2024 reference pairing. The 156 v2 2024
forecast arrays were sealed before scoring (fit seal
`4611feba330552aabadfb2fd0a66ec4dc9d3ae6c9e9050d1849cb6e227ad8a60`).
No 2025 or 2026 observation was read.

## Consumed 2024 development result

Same 156 cases, 760,812 reference-valid forecast cells and 24-hour thresholds
as the original national probability study. This is a **consumed development
diagnostic**, not an independent test. Lower Brier is better. The paired
bootstrap resamples 2024 initialization dates 1,000 times; it does not remove
spatial or serial dependence.

| Head | Original v1 Brier | Repaired v2 Brier | v2 Brier skill | v2 minus v1 Brier, 95% date interval | v2 warning count / observed count |
|---|---:|---:|---:|---:|---:|
| Heavy ≥64.5 mm | 0.015524 | 0.016496 | 0.04187 | +0.000972 [0.000527, 0.001432] | 7,471 / 13,320 |
| Very heavy ≥115.6 mm | 0.003807 | 0.003901 | 0.01254 | +0.0000947 [0.0000355, 0.000162] | 0 / 3,017 |

The repair candidate **fails** the paired Brier comparison for both heads;
the very-heavy cutoff also suppresses every 2024 warning. It is retained as
research evidence and is **not** connected to the API, dashboard, live worker,
or district product. The regional M2 remains the corrected product default.
Neither v1 nor v2 supports a nationwide calibrated warning claim.

The score and its SHA-256 sidecar are
`data/manifests/research_pilot/nationwide_probability_score_v2.json`
(`828dd9d359496ed9a3f61eecab9cc433f542e0cc169fceb56f76654d74ebeb74`).
The model and 156 arrays are ignored local artifacts under
`data/processed/nationwide_probability_v2/`. The read-only v1 national API
now reports `RESEARCH_METHOD_AUDIT_FAILED_RELIABILITY_UNVALIDATED` for its
probability fields and makes the failed methodology audit explicit in its
caveat. It continues to expose the original arrays for transparent research
inspection; no stored array or frozen score changed.

## UI and footprint corrections

The homepage now identifies when its 2025 benchmark is a pinned frozen result
without a reconciled live case index. The India Raw map explains that its
centre-in-polygon mask has 4,652 cells, while the separate research model uses
positive polygon overlap (5,105 cells); 453 overlap cells are therefore absent
from the default Raw land display. Neither mask is an IMD verification mask or
official district geometry. A future common-footprint map comparison needs a
separately versioned display contract; silently changing either frozen mask
would break its evidence chain.

## Verification and open gates

`python scripts/nationwide_probability_v2.py check` passes the protocol, seal,
156 prediction hashes and score hash. The source national protocol/hash check
still passes with 328 forecast feature cases, 156 sealed v1 prediction cases
and 5,105 research land cells. The national uncertainty and district hash
checks also pass (102 initialization dates, 735 represented research polygons,
156 district tables). Exact checks for this increment:

| Check | Result |
|---|---|
| Targeted v2 head and national API tests | 7 passed |
| Full backend `python -m pytest backend/tests -q --basetemp=data/pytest-probability-repair-final -p no:cacheprovider --durations=5` | 835 passed in 162.97 s |
| Frontend typecheck, lint, Vitest, production build | All exit 0; 31 files / 212 tests; 19 static pages generated |
| India Chromium end-to-end | 3 passed with local nationwide research enabled |
| Demo launcher preflight after restart | Twice `DEMO_PREFLIGHT_RESULT=READY`; local `/india` HTTP 200; national API serves the audit-failed probability status |
| Frozen 2026 scorer `--preflight` | Correctly blocked before observation read; 213 forecast cases |
| `git diff --check` | Exit 0; line-ending notices only |
| Free C: space after final browser run | 180.7 GiB, above the 50 GiB floor |

The first targeted API run in the restricted Windows socket sandbox hung and
was interrupted; its isolated retry also hung and was interrupted. An
unsandboxed rerun completed with 7 passes. The first frontend Vitest run
failed because the sandbox removed temporary transform files; its unsandboxed
rerun completed with 212 passes. These interrupted and failed runs are not
counted as passes. A later India browser run failed because the rebuilt client
met a still-running old backend; after a launcher-owned restart, all three
browser tests passed. That failed run is likewise not counted as a pass.

The restart exposed two Windows PowerShell 5.1 launcher defects. Wrapping a
decoded JSON array in `@()` nested the process records and prevented
`stop-demo.ps1` from matching its own PIDs. `Invoke-WebRequest` without
`-UseBasicParsing` made the health check report failure despite HTTP 200.
`start-demo.ps1`, `stop-demo.ps1`, and `preflight-demo.ps1` now handle these
cases. The launcher stopped only its recorded processes, restarted the
project, completed both preflight phases, and left the site running locally.

The 2026 one-shot score remains blocked by the four source/version gates in
`docs/159`: complete authorized annual IMD 2026 reference, actual 2026 GEFS
deployment identity, exact 2023 training patch and selected-predictor
comparability. The 72-case regime packet still requires independent qualified
reviewers and dated evidence. The winter western-disturbance corpus, nationwide
ensemble-member fields and authorized current district geometry remain absent.
The nationwide M2 failed its frozen 2023 selection gate and has regional and
very-heavy 2024 development failures (`docs/167`). Those scientific gates
cannot be fixed by relabeling the UI or reusing consumed outcomes as an
independent test. The next probability candidate requires a newly frozen,
scientifically motivated method and an untouched comparable year before
promotion.

## 9 October forecast-only failure diagnosis

`175_NATIONWIDE_PROBABILITY_CUTOFF_TRANSPORT_DIAGNOSTIC_20261009.md`
reproduces the sealed v2 model and 156 forecast arrays without opening an
IMD reference. For very heavy rain, lead calibration places the maximum
2024 probability below the unchanged 0.03 cutoff at all three leads; the
coherence step does not cause the zero-warning result. This explains the
previous failure but does not change the frozen v2 Brier score, threshold,
model or no-promotion decision. The separate read-only diagnostic and its
protocol are hash-receipted; the full backend suite reached 860 passes.
