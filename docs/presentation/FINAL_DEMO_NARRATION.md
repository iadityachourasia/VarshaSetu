# Final Demo Narration — Phase 5B

Three scripts: a 90-second primary walkthrough (the one to rehearse until
it's automatic), a 2-minute extended version for a full slot, and a
30-second elevator pitch for a hallway conversation. All three use only
numbers from `docs/presentation/FINAL_PPT_FACTS.md` and the official demo
cases from `docs/presentation/OFFICIAL_DEMO_CASES.md`. All three follow
Story Mode's scene order (`frontend-v2/src/components/story/story-mode.tsx`)
so the spoken narration and the on-screen overlay never contradict each
other — a presenter can literally read Story Mode's own scene text as
narration if memory fails under pressure.

Load order before starting: `/forecast?demo=official` (redirects to the
official 2025 case), then open Story Mode ("Present VarshaSetu" button or
the app's usual entry point) if using the guided overlay.

## 1. 90-second primary script (targets 60-90s; do not run over 120s)

> "VarshaSetu asks one question: can regime-aware, forecast-time
> post-processing reduce systematic error in raw NWP monsoon rainfall
> forecasts — without inventing new observations?
>
> We test this on two separate, completed historical benchmarks with
> different GEFS lineages — they're never pooled into one number. [advance
> to Track A/B slide or Story Mode scene 2]
>
> On the 2019 GEFSv12 reforecast test — 255 held-out cases — our Global
> XGBoost correction cut RMSE from 19.77 to 17.85 millimetres, a 9.73%
> reduction. [open the official 2019 case, show the three-map comparison]
>
> On the more recent, completed 2025 historical operational-era test — 232
> cases — the preselected Ridge model cut RMSE from 16.17 to 15.57
> millimetres, 3.66%, selected before that holdout was ever opened.
> [switch to `?demo=official`, the 2025 case]
>
> But here's the honest part: in 2025, Raw GEFS actually kept *better*
> extreme-rain spatial skill than our corrected model, at every scale we
> tested. Lower overall error did not mean better extreme-event skill — we
> say that on the same screen as the RMSE win, not in a footnote.
>
> Our calibrated Heavy and Very-Heavy rainfall probability models both beat
> a naive reference — but false-alarm rates stayed high, and we show that
> number too.
>
> Everything here is frozen, hash-verified, and reproducible: no retraining
> after a test opened, no cherry-picked case — this case was chosen because
> its result is *near-neutral*, not because it's our best one.
>
> This is a research prototype for honest, verifiable forecast
> post-processing — not a live forecasting system."

## 2. 2-minute extended script

Use the 90-second script above as the backbone, and insert these four
additional beats at the marked points:

- **After the two-track intro**, insert Story Mode's "Synoptic Context"
  beat: *"Every correction sits inside real atmospheric context — 850-hPa
  wind, 700-hPa moisture, 500-hPa geopotential height, mean sea-level
  pressure, precipitable water, all frozen forecast-time fields you can
  inspect alongside the rainfall grid. That's not a causal proof any one
  feature drove any one correction — it's transparency into what the model
  could see."*
- **Before the 2019 number**, insert the pseudo-regime architecture beat:
  *"Underneath both tracks sits a forecast-only pseudo-regime classifier —
  we call it 'pseudo' deliberately, because it's not independently observed
  monsoon-regime truth. It feeds a hard-routing model and a soft mixture,
  and neither beats the plain global model overall. Regime-awareness is a
  research question here, not a marketing claim."*
- **After the FAR caveat**, insert the data-quality beat: *"Underneath all
  of this: 1,125 scheduled forecast messages, every one of them actually
  acquired. Only 615 passed control-member quality control and 218 passed
  full five-member ensemble QC — that attrition is deliberate scientific
  filtering, not missing data."*
- **Before the closing line**, show the district or ensemble page briefly
  and say: *"District aggregation exists for the 2019 track; it wasn't
  built for the newer 2025 corpus, and we say so on the page rather than
  faking a table. Same with the five-member ensemble comparison — it only
  exists for this exact 2025 subset."*

Close with the same closing line as the 90-second script.

## 3. 30-second elevator pitch

> "VarshaSetu is a research prototype that tests whether regime-aware
> post-processing can fix systematic bias in raw monsoon rainfall
> forecasts. On our two completed historical benchmarks, we cut RMSE by
> about 9.7% in 2019 and 3.7% in 2025 — but we're upfront that in 2025, the
> raw forecast actually kept better skill on the extreme events that matter
> most for warnings. Everything's frozen, hash-verified, and reproducible —
> this isn't a live system, it's honest science."

## 4. Delivery notes

- Say the RMSE-reduction number and the extreme-skill caveat **in the same
  breath**, every time — never let the audience walk away with only the
  positive number.
- If a judge interrupts to ask about a specific page (Ensemble, Districts,
  Regimes), it is fine to say plainly which track that page covers and
  which it doesn't (see `docs/presentation/ROUTE_INVENTORY.md`) — do not
  improvise a number that isn't in `FINAL_PPT_FACTS.md`.
- If the primary 2025 case (`20250714_day2_24h`) has a rendering or network
  problem live, switch to the backup (`20250903_day2_24h`) via the Reset
  Demo link or by typing the case ID — and it's fine to say out loud that
  you're switching to the backup case; that's honest, not a failure to
  hide.
- Press "P" to enter Presentation View before starting, so the sidebar and
  non-context header controls collapse and the screen reads cleanly on a
  projector.
