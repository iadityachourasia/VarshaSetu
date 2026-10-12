# 2026 selected-predictor source metadata — 9 October 2026

This is a bounded, forecast-only follow-up to the four still-open source gates
in `docs/159`. It does **not** clear the 2026 independent test. No 2026
observation value, forecast data value, model prediction or verification score
was read. Regional M2 remains the product default.

## Prespecified local GRIB check

The write-once protocol
`data/manifests/research_pilot/2026_selected_predictor_metadata_protocol_v1.json`
(SHA-256 `17cc03151aa5f1144c115c7dd2d7f06050e5981269c12a257cd3a87f3fec9a29`)
selected a 2023 training cycle (16 June 00 UTC) and the 15/16 June 2026
00 UTC cycles around the **announced** GEFS 12.3.20 boundary. For each cycle it
selected the c00 f024 GRIB message for rainfall, U850, V850, Q700, Z500,
MSLP and PWAT. The 2023 bytes were checked against the sealed 2023 source
manifest; the 2026 bytes against their existing NOAA URL/range/size/hash
receipts. No data were downloaded or duplicated.

`scripts/audit_2026_selected_predictor_metadata.py write` parsed only GRIB
headers from these 21 messages. The write-once result is
`2026_selected_predictor_metadata_result_v1.json` (SHA-256
`a4b5630240ab953a428f844fb649dfb89ed138da9747eb964e324192686440db`).
The `check` mode recomputes the result from the same hash-verified local
messages and refuses a changed protocol, source receipt or result.

| Comparison | Identity-key differences | Encoding-key differences |
|---|---|---|
| 2023 → pre-announcement 2026 | None among the inspected keys for all seven fields | MSLP: binary scale, decimal scale and bit width; V850: bit width; Z500: binary scale and bit width |
| Pre → post-announcement 2026 | None among the inspected keys for all seven fields | Rainfall and MSLP: bit width |

The identity keys include GRIB parameter, level, grid shape, accumulation
step, process identifier and production status. A bit-width or scale difference
can depend on the forecast field's range and packing. These three **different
weather days** cannot isolate a software change. Identical GRIB identity keys
do not identify the executable, prove the same forecast equations, establish
numerical equivalence, or clear forecast-time model applicability. The separate
DSWRF radiation packing change in `docs/158` is stronger evidence for the
specific notice field, but radiation is outside the seven model inputs.

## Authoritative source review and four-gate disposition

The [NWS SCN 26-57](https://www.weather.gov/media/notification/pdf_2026/scn26-57_GEFS_Shortwave_radiation_fix.pdf)
still supplies an intended 15 June 12 UTC implementation, with possible
postponement. The [NWS notice index](https://www.weather.gov/notification/)
lists the notice as effective on that date; it is an announcement index,
not a per-cycle production log. The [NCO change-history page](https://www.nco.ncep.noaa.gov/pmb/changes/)
reviewed on 9 October lacks the required cycle-specific 2026 rollout and
2023 patch entries. The current [NCO public code-directory index](https://www.nco.ncep.noaa.gov/pmb/codes/nwprod/)
exposes a GEFS 12.3.22 directory, but a present-day code tree cannot establish
which executable generated historical 2023 or June 2026 cycles. These new
web observations are bibliographic review; unlike the local GRIBs and the
previously downloaded SCN PDF, no new web-page byte receipt is claimed.

| Frozen source gate | 9 October state | Exact missing evidence |
|---|---|---|
| Complete authorized annual IMD 2026 RF25 reference | **BLOCKED** | The full calendar year is still in progress. Need the complete annual file, its checksum, daily time-window and local-use/redistribution terms. The 125 real-time daily files remain a distinct provisional source. Do not retry the known empty annual response as if it were data. |
| Actual GEFS 2026 deployment identity | **BLOCKED** | NCO/EMC production record mapping the actual GEFS executable and any postponement or subsequent patches to the frozen 00 UTC cycles. |
| Exact 2023 training GEFS version | **BLOCKED** | Provider record for the patch/executable used on the admitted 2023 training cycles; the broad GEFS v12.3 family and current code directory are insufficient. |
| Selected-predictor comparability | **PARTIAL DIAGNOSTIC; GATE BLOCKED** | Provider-supported processing/change review of rainfall, U850, V850, Q700, Z500, MSLP and PWAT across the actual versions, plus the already recorded forecast-feature shift. Header agreement alone cannot decide equivalence. |

No `2026_imd_reference_clearance_v1.json` or
`2026_gefs_version_clearance_v1.json` was created. The frozen one-shot scorer
must continue to return `BLOCKED_BEFORE_OBSERVATION_READ`. No 2026 model skill,
probability reliability, warning use or promotion is established.

## Checks

- The protocol was sealed before the 21-header result was computed.
- `python scripts/audit_2026_selected_predictor_metadata.py write`: exit 0;
  seven fields and 21 source messages; no observation or forecast values.
- `python scripts/audit_2026_selected_predictor_metadata.py check`: exit 0;
  reproduces the sealed result.
- Focused backend tests: 4 passed, including result reproduction and receipt
  tamper refusal.
- Full backend suite, with the established Windows socket-enabled setup:
  `python -m pytest backend/tests -q
  --basetemp=data/pytest-selected-predictor-final-20261009
  -p no:cacheprovider --durations=5`: **848 passed**, exit 0 in 172.89 s.
- `python scripts/probe_2026_source_clearance.py --check`: exit 0,
  `OPEN_NO_CLEARANCE`, all four blockers retained.
- `python scripts/score_2026_frozen_inference.py --preflight`: exit 0,
  `BLOCKED_BEFORE_OBSERVATION_READ`, 213 sealed cases, observation read false.
- `git diff --check`: exit 0; only Windows line-ending notices.
