# Research-pilot advancement: executed work and remaining gates

Date: 2026-10-06. This is a new work package. Earlier frozen protocols, test
results, presentation evidence and submitted materials were not rewritten.

## Source and year governance

`scripts/build_source_year_ledger.py` generated the write-once
`data/manifests/research_pilot/source_year_ledger_v1.json` (SHA-256
`328390278292035927f78f20a87fa00edb935d94dfd723d16f278f312fe9ed34`).
Its 27 track/year rows record a local forecast artifact or source manifest,
an IMD file when present, checksums, accumulation and observation windows,
previous experimental roles and missing inputs. It marks 2014–2016, 2019,
2022 and 2025 as consumed tests. The 2026 row is **only a candidate** for a
future Track B test: prior-observation-use audit and a new frozen protocol are
still required. `--check` rebuilds the inventory and detects changed bytes.
This inventory is not a new train/test split, a licence determination or proof
that the 2026 season is untouched.

IMD-derived inputs remain local; redistribution terms are unresolved. NASA
IMERG Final V07, NCMRWF archives, expert regime labels, a winter disturbance
corpus and authorized current district geometry have not been acquired or
validated for this work package. A pure IMERG V07 half-hourly adapter now
requires 48 explicit contiguous 03–03 UTC intervals, converts mm/hour to
mm/24 h and preserves missing cells; it has no downloaded IMERG input or spatial
comparison yet. None of these sources is silently substituted for another.

## Multi-label regime correction: development result

`regime_residual_dev_protocol_v1.json` was frozen before fitting. Five
independent logistic heads were trained from objective retrospective labels on
2000–2010; their outputs are **uncalibrated model scores**, may overlap and are
not expert weather-regime truth. A B1 geography-aware global model was fitted
on the same years. Its 2011 predictions supplied a separate 2011 residual
training set for a matched global Ridge correction and five probability-weighted,
support-shrunk specialists. The only evaluation years were 2012–2013:
development years already used by earlier model selection. No consumed test
year was loaded and no Track B model was changed.

The write-once result (`backend/app/evidence_data/phase18/regime_residual_dev_result_v1.json`,
SHA-256 `b56ff421311b5359c4bc907995a4496ea1af17f8ed830a48616ac074f133ca2e`)
contains source/model hashes, 511 cases and 664,811 paired cells. Pooled figures:

| Model | RMSE, mm/24 h | Bias, mm/24 h | Heavy CSI | Hits / misses / false alarms |
|---|---:|---:|---:|---:|
| Raw | 16.116 | -0.156 | 0.0727 | 1,270 / 12,417 / 3,781 |
| B1 global base | 14.183 | +0.783 | **0.1587** | 2,760 / 10,927 / 3,707 |
| B1 + matched global residual | **14.061** | -0.143 | 0.0984 | 1,485 / 12,202 / 1,398 |
| B1 + soft regime residual | 14.071 | -0.140 | 0.1030 | 1,569 / 12,118 / 1,551 |

The regime correction is slightly higher than its matched residual control on
heavy CSI but slightly worse on RMSE, and both residual methods lose heavy CSI
substantially against the B1 base. **Do not promote it or claim regime-aware
rainfall skill.** The result has no paired interval and no independent test;
even a favourable development comparison would not justify promotion. The
method remains isolated from the live product. Very-heavy, lead and year
breakdowns are preserved in the result file rather than hidden by this table.

## New-cycle execution and live district product

The worker queried the NOAA index for 2026-10-05 (34 selected messages,
8,780,254 bytes). Every lead failed the established packing-aware canonical
rainfall reconstruction and **nothing was published**. The adjacent
2026-10-04 cycle (8,444,281 planned bytes) passed all three leads and published
24 forecast arrays with `observation_read: false`; its local bundle manifest
SHA-256 is `419c4e3addfee108487377a69f6e1e92acc77214c20a0c4c9d514a8e557690a6`.
The normal API process re-verified the complete bundle. Its applicability
report is **WARNING**: 100% of Day 3 cells are outside the 2023 training
0.1–99.9 percentile range for `z500_area_mean`. This is a distribution warning,
not a measured error. The cycle is an experimental forecast, not a verified
forecast or an official warning.

**2026-10-06 update.** The registered Task Scheduler worker published a new
NOAA cycle with manifest SHA-256
`81130489b24fdc15bd0750261990639344217eca50f027e1d08da687e1f9819b`.
The hash verifier accepted all 34 source messages and the bundle, with
`observation_read: false`. **Only Day 1 passed.** Day 2 and Day 3 were
withheld because +27→+30 h and +51→+54 h nested APCP differences exceeded
their packing bounds. The run receipt is
`data/live/run_logs/20261006T120352178965Z_897d55157355402db07ff4321d9a0b8e.json`.
This is an unattended publication-path success, not a verified forecast.

Both October cycles are outside the June–September research season. Their
feature-range warnings are therefore especially important; the 2026-10-06
Day 1 field has several area-mean features entirely beyond the 2023 training
range. The API and live page now mark `OUTSIDE_JJAS_RESEARCH_SCOPE`. The daily
scheduler now records `outside_jjas_scope` without fetching or publishing
October–May cycles. Previously published October bundles remain immutable
and explicitly labelled inference demonstrations, with no off-season skill or
reliability claim.

The cached 2026-10-05 and 2026-10-06 rainfall messages were independently
re-read through `scripts/live/diagnose_cached_rain_qc.py`. Write-once,
hash-linked diagnostics in `data/manifests/research_pilot/rain_qc_20261005_v1.json`
and `rain_qc_20261006_v1.json` record two to five cells per failed first
segment below the declared negative packing bound (for example, −0.07 mm
against −0.055 mm on 2026-10-05 +3→+6 h). No QC tolerance or published array
was changed.

The previously frozen Track B 2025 probability evidence remains the relevant
held-out reliability reference, not the October cycles. Its stored
`experiments/recent_historical/phase4j_operational_final_test_v1/metrics/probability.json`
reports heavy and very-heavy Brier skill scores of
0.095 and 0.027, respectively, on 301,832 paired cells. The very-heavy
0.2–0.3 probability bin contains only 22 cells; higher bins contain at most
two. This cannot establish reliable high-probability very-heavy estimates.
The live API now identifies the calibration as fitted in 2024 and explains
that new-cycle reliability is unknown; no calibrator was refitted.

The new `GET /api/science/live/districts?kind=live&date=20261004&product=day1_24h&model=M2`
returns forecast-only, area-weighted district rows from the existing hash-verified
regional geometry and weights. It exposes the cycle, model, 24-hour window,
regional coverage and evidence/geometry hashes. It never reads observations.
These 188 overlapping districts use simplified 2021 geometry and cover only
the validated 10–22 N, 68–80 E box; they are not an India-wide or official
current-boundary product. An area-averaged cell probability is not the chance
that any point in a district has an event.

The Experimental Live Cycle page now loads the matching district table on
request, with model, window, regional scope and hashes visible. Its table was
checked against the real API in a browser test. It does not show observation or
verification columns for the live cycle.

Live bundle creation now validates before writing and atomically renames a
staged directory into place; interrupted writes leave no visible cycle. New
downloads use an immutable, hash-receipted selected-message cache. The worker
refuses incoherent nested event probabilities rather than silently altering
frozen calibration. `scripts/live/run_scheduled.py --once` now provides one
bounded unattended attempt: one-process lock, newest four-cycle index search,
50 GiB free-space floor, 100 MiB transfer cap, immutable JSON run receipts and
no retry of a quality refusal within an invocation. The
`VarshaSetu-Experimental-GEFS` Windows Task Scheduler job was registered for
12:00 Asia/Kolkata daily under the current interactive user, using the
repository virtual environment. Its executable, arguments and next run were
verified on 2026-10-06. A manual launch through Task Scheduler completed:
its immutable receipt at `data/live/run_logs/20261005T204639356872Z_2224c43a73b546f09edefafa3832e1af.json`
records `cycle_refused` for the already known 2026-10-05 rainfall QC failure,
with no observation read and no publication. A later Task Scheduler execution
has `LastRunTime` 2026-10-06 17:32 local and result 0, matching the successful
2026-10-06 publication receipt above; the next configured run is 2026-10-07
12:00 local. The task runs only while that user has an interactive session.
The API's stale-cycle label is a visible local alert; external notification
has not been configured.

An independent 2026 verification, national corrected model, IMERG sensitivity
study, expert regime review and NCMRWF adapter remain future work.
`docs/147_INDEPENDENT_REGIME_REVIEW_PROTOCOL.md` prepares the blinded
review rubric without claiming any expert annotation has occurred.
NASA's [IMERG V07 technical documentation](https://gpm.nasa.gov/resources/documents/imerg-v07-technical-documentation)
describes half-hourly Final Run as gauge-adjusted and normally available about
3.5 months after the observation month. The V07 adapter is ready for a
separate 03–03 UTC sensitivity study, but no Final Run files were acquired
in this work; it has not been substituted for the IMD reference.

## Forecast-only 2026 archive probe

Before fetching 2026 monsoon GRIB payloads or pairing observations, the
write-once `2026_gefs_probe_protocol_v1.json` fixed four representative
initialization dates: 15 June, 15 July, 15 August and 15 September. The
`scripts/probe_gefs_2026.py` result reports all four selected NOAA indexes
complete with the expected 34 control-member messages and planned selected
payloads of 9.21–9.66 MB per date. It downloaded **index text only** and read
no observations. NOAA index rows do not declare a model version, so version
comparability and GRIB semantics remain unchecked. This is source availability,
not a complete 2026 corpus, independent-year clearance or skill evidence.
The protocol/result hashes and source-row digests are in
`data/manifests/research_pilot/2026_gefs_probe_{protocol,result}_v1.json`.

A separately frozen GRIB probe then fetched **only those four dates** through
the selected-range hash cache (about 38 MB planned), decoded all 34 messages
per date, and applied the unchanged 24-hour accumulation rule. Eight of the
12 date/lead products passed: 1/3 on 15 June, 3/3 on 15 July, 3/3 on 15
August and 1/3 on 15 September. Failed leads retain their packing-bound
reasons in the immutable
`2026_gefs_grib_probe_result_v1.json`. Sampled GRIB identification and packing
keys match locally stored 2023 and 2025 control-member examples, but those
keys do **not** prove a GEFS model version or forecast-distribution equivalence.
No model inference or observation pairing occurred. A complete 2026 forecast
corpus and an independent-test protocol are still required before scoring.

The next bounded stage is governed by
`data/manifests/research_pilot/2026_forecast_corpus_protocol_v1.json`.
`scripts/build_gefs_2026_forecast_corpus.py` acquires selected NOAA ranges one
month at a time, reuses hash-verified cache entries, applies the canonical
reconstruction and stores only forecast-time features for passing leads in
write-once per-date directories. It refuses to silently skip a missing date.
The June 2026 stage completed with all 30 dates verified and sealed in
`2026_forecast_month_202606_v1.json` plus its SHA-256 sidecar. Of 90 possible
date/lead products, 40 passed the unchanged canonical rainfall QC: Day 1 13,
Day 2 10 and Day 3 17. Four dates had no eligible lead. These are
**forecast-side availability counts, not skill or event-support counts**.
`scripts/summarize_gefs_2026_forecast_corpus.py` reproduces the month summary,
including source and feature hashes. The protocol caps each cycle at
100 MiB of selected messages, requires at least 50 GiB free and uses one
process, preserving the frozen hardware policy.
On 12 July acquisition first stopped at a NOAA index HTTP 503 after 11
verified July cases. A bounded retry for transient HTTP 429/5xx and transport
errors was added and tested; resumption reverified those 11 immutable cases
before fetching the next date. Scientific, hash and missing-date failures
still stop the month.
July then completed and was sealed in `2026_forecast_month_202607_v1.json`:
31/31 cycles verified, with Day 1 20, Day 2 20 and Day 3 22 strict-QC
passing products; two dates had no eligible lead. The following stages use
the same protocol. `scripts/summarize_gefs_2026_forecast_year.py` refuses
to seal the 122-date JJAS year until all four month summaries reverify
against every local source receipt and feature-array hash.
August subsequently completed in `2026_forecast_month_202608_v1.json`:
31/31 cycles verified, with Day 1 15, Day 2 22 and Day 3 25 passing
products; one date had no eligible lead. September completed in
`2026_forecast_month_202609_v1.json`: 30/30 cycles, with Day 1 16, Day 2 17
and Day 3 16 passing products; one date had no eligible lead. The sealed
`2026_forecast_jjas_year_v1.json` rechecks all 122 local case/source receipts
and feature hashes: **64/69/80 strict-QC Day 1/2/3 products** of 366 possible
date/lead products, with eight dates having no eligible lead. These are
forecast availability counts, never a 2026 skill estimate.

An exploratory, **post hoc** diagnostic in
`2026_june_masked_coverage_diagnostic_v1.json` re-read the verified cached
precipitation messages without observations. It retained NaN at every cell
where a nested difference crossed its packing bound, while leaving the
operational/corpus QC and products unchanged. All 50 canonically withheld
June leads had at least 99.2% valid regional cells under this alternative;
affected counts ranged from 1 to 19 of 2,401 cells (median 7). On the 40
passing leads, the diagnostic matched canonical rainfall exactly. This
motivates a separately frozen cell-mask validation study on development data;
it does **not** authorize replacing a withheld full-grid lead with a partial
forecast, interpolating the missing cells, or scoring those leads as passing.
The one-off diagnostic is not an independent performance test.

A second forecast-only exploratory check used the hash-verified **2021 June
development archive** under `2021_june_masked_coverage_protocol_v1.json`.
Its write-once result reports 34/90 canonical passing leads and 56 withheld;
all withheld leads retained at least 99.3% valid regional cells under the
same mask, with 1–16 invalid cells of 2,401 (median 5). Passing leads again
matched canonical rainfall exactly. This archive has already been used for
development, and the diagnostic was selected after looking at 2026 forecast
QC, so these cross-year counts remain exploratory. They do show the sparse
invalid-cell pattern is not confined to June 2026. A model/verification path
with explicit missing-cell support and paired-case evaluation still needs to
be designed, frozen and tested before any product change.

The full-year `2026_jjas_masked_coverage_diagnostic_v1.json` is also
forecast-only and post hoc. It found 153 canonically withheld leads; all had
at least 99% valid cells under the exploratory mask (minimum 99.21%). The
canonical 213 passing leads remained exact. This justifies a prospective
development-data experiment on partial spatial coverage, not promotion of
the masked path or a district forecast from an incomplete lead.

**7 October update:** the development-data experiment is now complete under
the frozen `partial_cell_development_protocol_v1.json`. See
`docs/148_PARTIAL_CELL_DEVELOPMENT_RESULTS.md`. June 2023/2024 had 180
date/lead cases, 96 strictly withheld. The experimental mask retained at
least 99% of regional cells in all cases and matched every strict-pass field
exactly, but 342 district-by-lead values fell below the prespecified 95%
weighted-area coverage gate. The current worker and product remain strict.
The subsequent frozen-model candidate and same-cell June 2024 score are in
`docs/149_PARTIAL_GRID_INFERENCE_CANDIDATE.md`. Of 90 leads, 55 passed the
candidate's model/probability gates and 35 failed the existing nested
probability check; 35 ready leads had been withheld by strict rainfall QC.
M2 remains the product default. The candidate has no live API or publication
path and supplies no independent-year claim. The backend regression suite
passed 749 tests after this candidate and the bounded Windows staging-rename
repair; see `docs/149` for the same-case findings.

The write-once `2026_june_feature_range_v1.json` checks the 40 strict-QC
passing June feature matrices against the 0.1–99.9 percentile range of the
frozen 2023 training matrix, with both the training and case-array SHA-256
hashes recorded. The training-X hash matches the frozen 2023 year manifest.
No observations or model predictions were read. Three date/lead cases had a
dynamic feature outside that range in more than 5% of
cells: Day 1 on 1 June (500 hPa geopotential), 4 June and 5 June (area-mean
relative vorticity). Longitude also has an edge-grid range difference in
10.2% of cells on every case; it is a static coordinate and is not counted
as weather drift. This is a descriptive applicability check, **not** proof
of model-version equivalence, distributional stationarity, or forecast skill.

The year-wide `2026_jjas_feature_range_v1.json` compares all 213 strict-QC
cases with the same frozen 2023 training-X hash. It records 123 dynamic
feature warnings across 45 date/lead cases (34 dates), concentrated in
September (99 warnings). A warning means over 5% of cells in one feature
fell outside the training 0.1–99.9 percentile range; area-mean features
can place all 2,401 cells outside together. Seasonal evolution and a GEFS
version change are possible explanations, not conclusions from this check.
The report does not use observations or authorize a new skill claim.

The official [NWS Service Change Notice 26-57](https://www.weather.gov/media/notification/pdf_2026/scn26-57_GEFS_Shortwave_radiation_fix.pdf)
announced GEFS 12.3.20 effective with the 15 June 2026 **12 UTC** run,
subject to weather-related postponement. It describes higher GRIB precision
for three short-wave radiation fields, none of which VarshaSetu selects, in
the same output families we read. Our 00 UTC corpus would therefore straddle
the announced version boundary between 15 and 16 June if implementation
occurred on schedule. `2026_gefs_model_change_note_v1.json` records this
provenance and the unresolved actual transition date. Matching sampled GRIB
keys and mostly in-range June features do not establish identical numerical
forecast behavior across model versions. Any later 2026 verification must
disclose the version partition and examine sensitivity without selecting the
primary comparison on 2026 observations.
The 15 and 16 June 00 UTC cases both passed the selected-message schema/hash
checks for all 34 inputs; 16 June had no 24-hour lead pass the separate strict
rainfall reconstruction. These checks establish readable source fields, not
the actual deployment timestamp or cross-version forecast equivalence.

**7 October forecast-only version audit:**
`docs/155_GEFS_2026_ANNOUNCED_VERSION_PARTITION.md` re-verifies the sealed
122-cycle corpus and records 15 00 UTC cycles before, and 107 after, the
announced 15 June 12 UTC boundary. The 21/192 strict-QC passing products and
their feature warnings are partitioned without observations. The actual
switchover and comparability to the 2023 training model remain unproven;
the second stratum spans July–September and is seasonally confounded.

Separately, `2026_track_b_evaluation_protocol_v1.json` freezes the proposed
M4-versus-M2 primary comparison, same-case metrics, guardrails and date-block
bootstrap **before 2026 observation pairing**. Its status is explicitly
`FROZEN_BEFORE_2026_OBSERVATION_PAIRING_CANDIDATE_NOT_CLEARED`: local or external prior use of 2026 observations,
reference availability, model version and corpus completeness must still be
audited before calling 2026 an independent test. A failed gate keeps M2 as
the default; this protocol itself is not a score.

On 6 October the project owner attested that no team member has inspected or
used 2026 IMD rainfall values for training, tuning, comparison or evaluation.
The known local 2026 IMD annual-file paths are absent. The write-once
`2026_prior_observation_use_audit_v1.json` records that answer and the local
check, with its limits. The **prior-use gate is provisionally cleared**;
an additional `git log -S'RF25_ind2026'` scan of tracked project history
found no earlier reference to that annual file name, while untracked files
outside this workspace remain outside the audit. A linked v2 audit also
checks the legacy `data/raw/observations/imd/2026/` location and leaves the
candidate status unchanged.
The original frozen candidate protocol remains unchanged. Complete forecast
coverage, an aligned IMD reference and the GEFS change review still gate
any independent-year score. Forecast coverage is now sealed as above; the
reference and model-version gates remain open. The frozen header-only IMD
probe attempted the official 2026 RF25 endpoint only after the forecast seal.

Its write-once `2026_imd_header_probe_result_v1.json` records a `URLError`
before any HTTP status or response bytes were obtained. Thus source
reachability or publication cannot be determined from this run. No 2026 IMD
rainfall values were read, retained, paired or scored. The versioned
`source_year_ledger_v2.json` links the completed forecast side and this
unresolved reference attempt without changing consumed-test history.

After a separate header-only GET returned HTTP 200, a versioned retry
protocol linked the first failed probe and repeated the bounded POST. The
immutable `2026_imd_header_probe_result_v2.json` records **HTTP 200 with
zero response bytes** for `RF25=2026`; there was no NetCDF file to retain or
inspect. This establishes endpoint reachability for that attempt, but does
not establish when IMD will publish a complete annual file. The append-only
`source_year_ledger_v3.json` records this newer result. The 2026 test
candidate remains unscored and reference-gated.

**7 October frozen-inference update:**
`docs/156_GEFS_2026_FROZEN_INFERENCE_SEAL.md` records immutable forecast-only
M0–M4 and probability outputs for all 213 strict-QC leads on the 122 cycles.
All 1,704 arrays reproduced bitwise. The original probability pair is
incoherent on 22 leads (159 cells), so those outputs have no warning-use
status. The source reference and model-version gates still prevent a 2026
skill or reliability score; no live product was changed.

**7 October one-shot verification preparation:**
`157_2026_VERIFICATION_SCORER_AND_PILOT_CLOSEOUT.md` records the separately
frozen scoring protocol and the blocked, observation-free preflight. Both the
complete authorized 2026 IMD reference and authoritative GEFS model-version
review are still absent. The research-pilot implementation is locally
prepared, but the 2026 independent score and operational-release gates are
open.

**7 October source-acquisition continuation:**
`158_IMD_2026_DAILY_SOURCE_AND_GEFS_EVIDENCE.md` records all 125 official
real-time daily IMD binary grids for June 1–October 3 in local, hash-receipted
storage. They remain unscored and distinct from the annual NetCDF, which again
returned HTTP 200 with zero bytes. The daily-source sensitivity scorer is
frozen to run only after the primary annual score. NOAA notices were saved and
hashed, but actual 2026 implementation timing and exact 2023 GEFS patch
comparability are still unconfirmed. `source_year_ledger_v4.json` is current.

## Checks for this work package

- Backend: `pytest backend/tests -q --basetemp=data/pytest-final-v3
  -p no:cacheprovider` passed **738 tests** on 2026-10-06 after the complete
  forecast seal, masked rainfall diagnostic, IMD transport classification,
  source audit and evidence code, with one Starlette dependency deprecation
  warning. The versioned source/year ledger `--check` reproduced its hash.
- Frontend: TypeScript, ESLint, 212 Vitest tests and the production Next build
  passed. After the October season-scope change, four focused real-backend
  Playwright checks passed with exit code 0, including the live district/API
  comparison and the out-of-season warning.
- A true 2026-10-04 cycle was re-read through the API. The 2026-10-05 worker
  refusal, first Task Scheduler receipt and the Day 3 applicability warning
  are part of the result rather than suppressed failures.
- The 2026-10-06 scheduler bundle passed hash verification. Live scheduler,
  API and pipeline regression tests passed (37 tests); direct TypeScript,
  live-client Vitest, lint and a production build passed after the new status
  field. One sandboxed test attempt could not start FastAPI TestClient because
  Windows asyncio could not create its local socketpair; rerunning with local
  sockets permitted passed. This was an execution restriction, not a test
  assertion failure.
- The full backend suite requires a writable repository-local pytest temp
  directory on this Windows runner; the default user temp path produced
  permission errors in test setup. Those environmental errors disappeared
  when `--basetemp` was set; no test assertions were waived.

## Local scheduler runbook

On the primary Windows machine, run the one-shot command from the repository
root under the same user that owns the local frozen artifacts:

```powershell
.\.venv\Scripts\python.exe scripts/live/run_scheduled.py --once
```

Read the latest JSON in `data/live/run_logs/` and query
`/api/science/live/status`. `published` means the bundle passed worker gates;
`already_published` means an immutable cycle exists; `source_unavailable`
means a NOAA index was incomplete or inaccessible; `cycle_refused` means the
selected cycle did not pass all worker checks and no bundle was published.
`outside_jjas_scope` is the intentional October–May skip, with no NOAA request.
`disk_guard` and `transfer_guard` require operator attention. A stale status
means no recent successful cycle, not a measured forecast failure. A lock file
must be investigated before manual removal after a crash. Do not treat a new
forecast as a skill result or issue a public warning from this path.
# 7 October 2026 probability-order diagnostic

The sealed development-only projection study is documented in
`150_COHERENT_PROBABILITY_PROJECTION_DIAGNOSTIC.md`. It found 92 nested-event
probability order violations among 238,083 archived Phase 4I 2024 rows.
The prespecified symmetric projection removes them and slightly reduces joint
Brier score. At this diagnostic stage, June partial-grid fields had not yet
been replayed through it. The 2024 selection block is consumed; no live
promotion occurred.

# 7 October 2026 coherent partial-grid replay

`151_COHERENT_PARTIAL_GRID_REPLAY.md` supersedes the earlier "not replayed"
status for the research path. All 90 June 2024 leads now pass the research
forecast-side coherence gate; 55 prior-ready leads match bitwise and 35 are
newly ready. The paired development score finds negative very-heavy Brier
skill and 9.24× very-heavy warning frequency bias at the frozen cutoff.
The strict live worker and default model remain unchanged.

# 7 October 2026 lead-aware extreme-event development

`152_LEAD_AWARE_PROBABILITY_DEVELOPMENT.md` records a new sealed early-2024
calibration and later-2024 scoring experiment. The lead-aware arm has a
small negative joint-Brier difference against a pooled recalibrator, but its
date-block interval crosses zero and its joint Brier is slightly worse than
the frozen isotonic control. The existing base choices used 2024 outcomes,
and the fixed very-heavy warning frequency varies strongly across blocks.
No live or calibrated-status promotion occurred.

# 7 October 2026 no-refit June probability transport

`153_JUNE_PROBABILITY_TRANSPORT.md` reports the fully sealed 90-lead June
forecast-side replay and later same-cell IMD score. The lead-aware candidate
lowers very-heavy warning frequency bias from 9.24× to 6.18× but worsens
joint Brier (0.0141130 to 0.0143997) and very-heavy BSS (−0.0302 to
−0.0835). The date-block joint-Brier interval is entirely worse against the
frozen projected control. June is consumed development data and overlaps
the new calibrator's early-2024 fit dates. No promotion occurred.

# 7 October 2026 bounded GEFS radiation packing evidence

The sealed forecast-only source probe in
`158_IMD_2026_DAILY_SOURCE_AND_GEFS_EVIDENCE.md` confirms that the sampled
published DSWRF GRIB packing changed between 15 June 2026 00 UTC and
16 June 2026 00 UTC, consistent with NOAA's announced change. The exact
GEFS software version and 2023-to-2026 rainfall-predictor comparability
remain unproven; independent 2026 annual-reference scoring stays blocked.
