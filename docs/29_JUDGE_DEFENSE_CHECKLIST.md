# Judge Defense Evidence Checklist

Do not memorize unsupported answers. Prepare evidence.

## Q1 — Where did the NWP forecast come from?

Must show:
- provider/model,
- archive/source,
- initialization,
- lead,
- variable,
- checksum/manifest.

## Q2 — Is this actually post-processing?

Show:
```text
Raw NWP → model → corrected NWP
```
and raw-vs-corrected verification.

## Q3 — How are regimes defined?

Show:
- methodology,
- inputs,
- label source,
- class/multi-label design,
- confusion/calibration results.

## Q4 — Why is regime awareness useful?

Show:
- global non-regime baseline,
- regime-aware model,
- same held-out data,
- per-regime and overall results.

If regime model is worse on a metric, say so.

## Q5 — Why not just use a neural network?

Answer with evidence:
- statistical baselines are strong,
- project selects architecture by held-out skill,
- complexity is justified only if it adds value.

## Q6 — How do you handle heavy rainfall?

Show:
- accumulation period,
- event threshold,
- positive sample count,
- probability model,
- calibration/reliability,
- ETS/CSI/POD/FAR.

## Q7 — Where is FSS?

Show:
- gridded forecast/observation,
- threshold,
- neighbourhood scales,
- FSS curve/table.

## Q8 — Are probabilities calibrated?

Show:
- reliability diagram,
- Brier/Brier Skill,
- calibration period separate from final test.

## Q9 — Is there leakage?

Show:
- feature registry,
- issue-time availability flags,
- split policy,
- tests.

## Q10 — What happens if the model makes things worse?

Show:
- failure-case view,
- raw fallback/reference,
- aggregate degradation monitoring,
- honest limits.

## Q11 — How does NCMRWF use this?

Position:
- a calibration/post-processing layer around existing NWP,
- not a replacement for the physical forecasting system.

## Q12 — What is genuinely novel?

Do not claim universal novelty.

Describe differentiation as the integrated system:
- regime-conditioned correction,
- probabilistic soft expert blending,
- physics-guided features,
- extreme event specialization,
- spatial verification,
- district translation.
Only mention pieces actually implemented.
