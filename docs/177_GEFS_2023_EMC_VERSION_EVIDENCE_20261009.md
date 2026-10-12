# NOAA EMC June 2023 GEFS version context — 9 October 2026

## Source admitted

The public [NOAA/NWS/NCEP/EMC implementation review package](https://vlab.noaa.gov/documents/17693964/29773494/EMC%2BReview%2BPackage%2B-%2BImplementations.pdf/16039299-9768-1739-c0d9-9cdf02da4841?t=1685111831730)
was retrieved in one bounded 532,296-byte request and kept locally at
`data/raw/evidence/gefs_version_review_2023_v1/EMC_Review_Package_Implementations_2023.pdf`.
Its SHA-256 is
`97cefdcf67559e8872cbc059fab5c70c382e72fb2e6223d7820acda567b921e7`.
The HTTP response was `200`, `application/pdf`, with `Last-Modified: Fri, 26
May 2023 14:37:11 GMT`. The ten-page PDF title is *EMC Review Package -
Implementations*. Its printed header says "EMC Review, June 6-8, 2023".
Pages 8–10 were rendered and visually inspected; text extraction alone was
not used to infer table columns. The write-once local intake receipt
`gefs_2023_emc_review_intake_v1.json` has SHA-256
`2365f75f2d3964dc2473104915ef729fb59ea576401a06d4f9365d02701ece3f`.
`scripts/check_gefs_2023_emc_review.py check` verifies both hashes, size, PDF
signature, page count, source identity and no-clearance status without network
access. The PDF is retained for local source review; redistribution rights
were not assessed and the PDF is not published.

## What the table establishes and does not establish

The page 9 "EMC Operational Implementations, 2019–2023" table records a GEFS
12.3.1 implementation dated 19 October 2022. Its separate **Current (Ops)**
column shows **12.3.5** for that row and earlier GEFS rows. This is
authoritative context for the GEFS version family around the June 2023
review, stronger than a present-day code-directory listing. It is **not** a
cycle-by-cycle production log. The package was modified on 26 May 2023 and
includes future-dated rows in its 2023 table; its "Current (Ops)" column
cannot establish that every June–September 2023 00 UTC training cycle ran
the exact same 12.3.5 executable or postprocessor. The archived GRIB source
receipts still lack an executable-version field. No model or selected-predictor
comparison was inferred from the table.

The [NCO implementation history](https://www.nco.ncep.noaa.gov/pmb/changes/)
lists 2023 changes, but its public summary is not a complete per-cycle
runtime record. The [15 June 2026 service change notice](https://www.weather.gov/media/notification/pdf_2026/scn26-57_GEFS_Shortwave_radiation_fix.pdf)
announces GEFS 12.3.20 at 12 UTC with a possible postponement; its notice
wording is not an observed deployment log. The previously hash-verified
forecast GRIB header/DSWRF boundary evidence remains as reported in
`docs/155`, `docs/159` and `docs/172`. It cannot identify all affected
cycles or prove selected-predictor equivalence.

## Gate decision

This follow-up closes **none** of the four `docs/159` source gates. Exact
2023 training-cycle patch identity, actual 2026 deployment-cycle identity,
selected-predictor comparability and a complete authorized annual IMD 2026
reference remain **BLOCKED**. The 125 daily 2026 grids stay a separate
provisional sensitivity source. No 2026 rainfall value, forecast field, model
prediction or score was read or changed here. The v2 scorer remains blocked
before observation access; no clearance manifest was created.

## Verification and changed files

- Bounded official-source HEAD: HTTP 200, `Content-Length: 532296`.
- Bounded GET: 532,296 bytes, PDF SHA-256 above; no duplicate download.
- `pdfinfo`: ten pages; rendered pages 8–10 visually checked against the
  extracted version rows and headers.
- `python -m pytest backend/tests/test_gefs_2023_emc_review.py -q
  --basetemp=data/pytest-gefs-emc-review-20261009 -p no:cacheprovider`:
  **2 passed**, exit 0, including PDF-byte and receipt-tamper checks.
- Full backend `python -m pytest backend/tests -q
  --basetemp=data/pytest-gefs-emc-full-20261009 -p no:cacheprovider
  --durations=5` with the known Windows socket-enabled setup:
  **868 passed**, exit 0, 111.44 s.
- `python scripts/check_gefs_2023_emc_review.py write`: exit 0, write-once
  context receipt; `check`: exit 0, repeatable local integrity.
- `python scripts/score_2026_with_clearance_gate_v2.py --preflight`:
  exit 0, `BLOCKED_BEFORE_OBSERVATION_READ`, 213 forecast cases, no score.
- `git diff --check`: exit 0 (existing Windows line-ending notices only).
  Free C: space was 178.26 GiB, above the 50 GiB floor.

This increment adds the local PDF, its JSON/SHA-256 receipt,
`scripts/check_gefs_2023_emc_review.py`,
`backend/tests/test_gefs_2023_emc_review.py`, and this report. The source
gate document and index receive only append-only pointers. No frozen
experiment, default model, 2026 observation or scoring artifact changed.
