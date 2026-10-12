# Local RSMC page leads for blinded regime review — 9 October 2026

## Role and decision

The frozen 72-case JJAS reviewer packet in `docs/154` and `docs/161` still has
**zero independent expert labels, zero adjudications and zero admitted
case-level dated bulletins**. This increment adds a local-only bibliographic
page finder for the three already hash-receipted annual RSMC reports. It does
not infer the presence or absence of a low/depression, active/break monsoon or
coastal/orographic regime. Neither a date-string hit nor a missing hit is a
meteorological label. The reviewer forms and source ledger remain blank.

The write-once protocol
`data/manifests/research_pilot/rsmc_regime_page_index_protocol_v1.json`
(SHA-256 `92d8ba28a935525b89304b91aa2e84b9e9d18a6fdd2b5a2da740299e947e2101`)
was frozen before matching report dates to case valid dates. It pins the
72-case packet hash, the three local PDF hashes, PDF page counts, extraction
tool version, runner hash and exact text rule. The result
`data/manifests/research_pilot/rsmc_regime_page_index_result_v1.json`
(SHA-256 `dd16a9f84f68dd46b60375050b5b361f762250826532104139cf913584163c21`)
and both `.sha256` sidecars are write-once. `check` re-extracts and reproduces
the exact result from the retained PDF bytes.

## Boundaries of the search

The script reads only each case's valid calendar date and the three RSMC
annual PDFs already retained under `data/raw/evidence/regime_review_rsmc_annual_v1/`.
It scans one-based **PDF page numbers** for explicit day/month or month/day
wording, with optional ordinal and matching explicit year. It does not match
date ranges or numeric-only dates. It stores page numbers, not report text,
observations, detector outputs, scores or labels. The three reports were
published after their respective seasons (January 2015, April 2016 and July
2017 on their covers), so these retrospective report pages cannot be used as
forecast-time features or dated operational bulletins.

| Annual report | Blind cases | Cases with an exact date-string page | Candidate page references |
|---|---:|---:|---:|
| 2014 | 24 | 5 | 25 |
| 2015 | 24 | 6 | 19 |
| 2016 | 24 | 5 | 12 |
| **Total** | **72** | **16** | **56** |

Three rendered page checks confirmed that text extraction does point to real
calendar-date text: 2014 PDF page 23 (printed page 19), 2015 PDF page 37
(printed page 33), and 2016 PDF page 69 (printed page 65). They also expose
the danger of auto-labeling. For example, the 2016 page includes realized
rainfall for states outside the packet's 10–22°N, 68–80°E review domain.
The 2015 page discusses a named Arabian Sea cyclone whose position and
influence would need expert assessment for this domain. No visual sample was
used to assign a label or to classify any of the 72 cases.

The annual reports are limited to cyclonic disturbances over the North Indian
Ocean. They do not systematically establish active/break monsoon or
orographic/coastal forcing, and exact-date matching can miss relevant pages
that express a date range or use figures without extractable text. A hit can
be a historical comparison, a verification table or an out-of-domain event.
The 56 references are **triage leads only**; they are not admitted into the
annotation source ledger. The 56 misses among cases are **unknown**, never
negative labels.

## Rights and handoff

The public [RSMC copyright policy](https://rsmcnewdelhi.imd.gov.in/copyright-policy.php)
requires permission for partial or full reproduction. The report PDFs and
page finder output stay local; no page image or excerpt was added to the
tracked repository or reviewer delivery. The reports' month-level publication
dates do not meet the validator's exact `issued_utc` source field. A reviewer
must inspect geographic and synoptic relevance, record a valid dated source
with permitted local use where available, and justify each positive or
uncertain task independently. Two qualified blinded meteorologists and a
distinct adjudicator are still required under `docs/161`. No outside person
was contacted.

## Checks and files

`python scripts/build_regime_report_page_index.py prepare` returned
`FROZEN_BEFORE_REPORT_DATE_TO_CASE_MATCHING`; `write` returned
`LOCAL_BIBLIOGRAPHIC_LEADS_ONLY`; `check` returned
`RSMC_PAGE_INDEX_REPRODUCED`, all exit 0. The focused tests covered date
forms, no-hit semantics and checksum tamper refusal: **3 passed**.

| Check | Result |
|---|---|
| Focused page-index tests | 3 passed, exit 0 |
| Exact PDF/source/protocol/result reproduction | Passed, exit 0 |
| `python -m pytest backend/tests -q --basetemp=data/pytest-regime-report-index-full-20261009 -p no:cacheprovider --durations=5` with the known Windows socket-enabled setup | **878 passed**, exit 0, 111.44 s |
| `python scripts/score_2026_with_clearance_gate_v2.py --preflight` | Exit 0, `BLOCKED_BEFORE_OBSERVATION_READ`, 213 forecast cases, no score |
| `git diff --check` | Exit 0; existing Windows line-ending notices only |

Final free C: space was 178.14 GiB, above the 50 GiB floor. No artifact was
committed.

This increment adds `scripts/build_regime_report_page_index.py`,
`backend/tests/test_regime_report_page_index.py`, this report and the four
write-once protocol/result files. It adds only pointers to `docs/00_INDEX.md`
and `docs/161`. Frozen packet, PDF receipts, source ledger, reviewer forms,
models, 2026 forecasts and scored outcomes were not changed.
