# Phase 11C: a forecast-time coastal and orographic forcing regime

Date: 2026-10-03. Work package WP-C of `docs/134`. The coastal and orographic part of the problem statement existed only as static zones and a cell-level forcing analysis (`docs/115` to `docs/118`). This adds a **per-case, forecast-time regime label** that the app serves, with a pre-registered check of whether it discriminates observed Ghats-coast heavy rain. It is a transparent heuristic, **not a learned or validated regime and not a probability**, and the requirement stays PARTIAL (a standing rule says it cannot be IMPLEMENTED without a validated model).

## Definition (frozen before any observation was compared)

- **Index.** For each case, the mean over the 109 land cells of the Ghats-coast zone (coastal and orographic) of the forecast cross-barrier forcing of `docs/118`: the 850 hPa wind component along the local terrain gradient (positive upslope) multiplied by precipitable water. Inputs are forecast U850, V850 and PWAT and static terrain geometry only; no observation and no model output enter it.
- **Classes.** WEAK below the lower tercile and STRONG at or above the upper tercile of the **training-year** index (Track A 2017, 258 cases; Track B 2023, 200 cases), MODERATE between. A rank against the training distribution accompanies each class and is a rank, not a probability.
- **Frozen artifacts.** `coastal_regime_protocol_v1.json` (sha256 `f55beb112943dc586e64441bd9c447bbf032fdb10ebeb35d94b960078676e8f9`) with the cut-points, definition, gate and decision rule, and `coastal_regime_cases_v1.json` (the index, class and rank of every evaluation case, forecast fields only), written by the `freeze` stage before the `score` stage opened any observation.

## Pre-registered check and decision rule

Per case, the observed number of heavy-rain cells (at least 64.5 mm per 24 h) among the zone's valid IMD cells. The heuristic is said to discriminate only if, in **both development populations** (Track A 2018 and Track B 2024), the strong-minus-weak mean heavy fraction is positive with its 95 percent whole-case bootstrap interval excluding zero and the population meets the support gate (at least 30 cases per class and 30 heavy pairs). The consumed years 2019 and 2025 are reported descriptively (labelled post-hoc) and cannot change the decision.

## Result (stored values)

| Population | Cases weak / moderate / strong | Share of observed heavy pairs weak / moderate / strong | Strong minus weak heavy fraction [95 %] | Spearman [95 %] |
|---|---|---|---|---|
| Track A 2018 (development) | 66 / 50 / 135 | 0.5 % / 2.5 % / 97 % | 0.182 [0.157, 0.210] | 0.79 [0.74, 0.83] |
| Track A 2019 (post-hoc) | 48 / 51 / 156 | 1.6 % / 5.6 % / 93 % | 0.209 [0.174, 0.245] | 0.80 [0.73, 0.85] |
| Track B 2024 (development) | 44 / 40 / 99 | 1.4 % / 3.5 % / 95 % | 0.224 [0.188, 0.258] | 0.84 [0.79, 0.88] |
| Track B 2025 (post-hoc) | 44 / 68 / 120 | 2.0 % / 13.8 % / 84 % | 0.142 [0.117, 0.168] | 0.60 [0.50, 0.69] |

**The decision rule is met**: both development populations pass the gate and have a positive difference with an interval that excludes zero. The reproduction gate passed in all four populations: the observed Ghats-coast heavy pairs equal the Stage 1 zone evidence exactly (2,789; 4,075; 2,627 and 2,358), the class counts equal the frozen forecast-only counts, and the group totals equal an independent sum.

## How to read it

- **The strong class holds most of the heavy rain** (84 to 97 percent of the observed Ghats-coast heavy pairs), the weak class almost none, and the ordering weak, moderate, strong holds in every population including the two post-hoc ones. The 2025 association is weaker (Spearman 0.60) than the others.
- **Part of the concentration is class size.** In the evaluation years the training-year terciles put well over a third of the cases in STRONG (52 to 61 percent), so the training years were weaker than the later ones and the class shares shift; the strong class would hold a large share of events even with modest discrimination, which is why the strong-minus-weak difference and the rank correlation are also shown.
- **It restates, per case, what `docs/118` found at cell level**: observed Ghats-coast heavy rain concentrates under strong cross-barrier forcing. What is new is a forecast-time label the app can serve, not new meteorological information, and it is descriptive evidence against the heavy-rain target, not an independent validation of a regime label.
- **No model uses it.** The frozen correction models and the geography-aware correction (`docs/133`) do not take this regime as an input, and the earlier experiment found forecast-time forcing added nothing to the geography features.

## Served and tested

`GET /api/science/evidence/coastal-regime/{overview,result?year=,cases?year=}` (hash-verified, 503 on any tamper including an edit of the case file's cut-points) and a panel on the Regime Intelligence page with the population table and a per-case lookup. Tests: `backend/tests/test_coastal_regime.py` (pure functions), `backend/tests/test_coastal_regime_evidence.py` (chain; every stored class re-derived from its stored index and the frozen cut-points; scores reproduce Stage 1; decision re-derived; API; tamper), `frontend-v2/src/lib/api/coastal-regime.test.ts` and `frontend-v2/tests/e2e/coastal-regime.spec.ts`. Scripts: `scripts/build_coastal_regime.py` (stages `freeze` and `score`, write-once).

## Limits

A heuristic of one physical quantity over one zone; thresholds fitted on one training year per track; bootstrap intervals resample whole cases and are optimistic because consecutive days are correlated; Track A and Track B are never pooled; the approval of this protocol is an interpretation of the owner's general instruction (recorded in the protocol) and may be withdrawn.
