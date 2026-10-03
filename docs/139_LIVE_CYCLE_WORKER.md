# Phase 12: the experimental live-cycle worker

Date: 2026-10-03. Work package WP-F of `docs/134`, built from the design in `docs/125`. A separate worker takes one NOAA GEFS 00 UTC cycle, applies the **frozen** Track B models without any retraining, and publishes an immutable bundle that a **read-only** API and the Experimental Live Cycle page serve. The coverage row `LIVE-INFERENCE` moves from PLANNED to **PARTIAL**: the path is built and proven by replay; **no live NOAA cycle had been fetched when this was written** (a download needs explicit owner confirmation, see "Running it").

## What it does

1. **Acquire** (`backend/app/live/pipeline.py`, `HttpSource`): reads the small `.idx` files of the selected objects, derives each message's byte range, and fetches only those ranges from `noaa-gefs-pds.s3.amazonaws.com` (control member `gec00`: 16 rainfall messages from `pgrb2sp25` and 18 atmospheric messages from `pgrb2ap5` and `pgrb2bp5`, 34 in all). Every range response is checked for status 206, the exact `Content-Range` and the exact length. `plan` reports the ranges and bytes without fetching any body.
2. **Decode and gate**: the corpus decoder, the corpus metadata checks (GRIB edition and length, initialization, valid time, member, native grid, units, accumulation interval and time-range semantics) and the canonical rainfall reconstruction. A message that fails any check refuses the whole cycle and nothing is published. A *lead* whose canonical reconstruction fails is withheld with its reason and the others stand, because the study corpus treats each (cycle, lead) as its own case.
3. **Features and models**: the 22-column matrix and the forecast-only regime features exactly as the corpus builds them, then the frozen M1 to M4, the regime probabilities and the calibrated heavy and very-heavy probabilities. Every model file is hash-checked against the final-freeze readiness record before use. Nothing is fitted, calibrated or tuned.
4. **Applicability**: the share of cells of each forecast feature outside the 0.1 to 99.9 percentile range of the 2023 training matrix, a warning above 5 percent. A range heuristic, not a validity test; coordinates and lead are excluded because they are fixed by construction.
5. **Publish** (`backend/app/live/bundle.py`): `data/live/<kind>/<YYYYMMDD>/` with one `.npy` per field, `manifest.json` (source messages with their SHA-256 and byte ranges, reconstruction segments, frozen model hashes, applicability, labels, `observation_read: false`, `retrained_or_recalibrated: false`) and `manifest.sha256`. A bundle is written once and never changed. `kind` is `live` for a NOAA cycle and `replay` for a stored historical cycle pushed through the same code.
6. **Serve** (`backend/app/api/live.py`, `/api/science/live/{status,cycle,field}`): verifies the sidecar, schema, label, flags and every array hash on every request and refuses with an integrity failure (503) otherwise. A stale live cycle (older than two days) is flagged, never silently reused. A replay is never presented as a live cycle. The `frontend-v2` page `/live` shows the label, the status message, a 49 by 49 map of any field, domain statistics, the regime probabilities, withheld leads with reasons, the applicability, the provenance and the caveats.

## The scientific gate (docs/125 phase L1): the replay is bit-identical

`python scripts/live/run_live_cycle.py replay --date 20250926` feeds an already-acquired 2025 cycle (read from the hash-verified raw store, each payload checked against its receipt) through exactly the code a live cycle uses, and compares every stage with the frozen artifacts, reading **no observation**:

- the decoded rainfall and atmospheric arrays equal the stored quality-controlled arrays exactly;
- the 22-feature matrix and the regime features equal the stored Phase 4G matrices (maximum absolute difference 0);
- the regime probabilities equal the stored ones (at most about 1e-16, a floating-point summation-order difference);
- M0 to M4 and both probabilities equal the frozen 2025 prediction arrays exactly over the paired cells (difference 0).

For 20250926 all three leads reproduce; for 20250715 the worker withholds Day 1 and Day 2 with the reason "negative difference exceeds packing bound" and publishes Day 3, **exactly the leads the study corpus withheld for that date**. The replay command refuses to publish if the largest difference exceeds 1e-9.

## Quality-gate tests (docs/125 phase L2)

Deliberately broken inputs are each refused: a missing message, a truncated payload, a payload under the wrong cycle date, a payload whose index line is not the control member, and a payload whose hash differs. Range responses with the wrong status, a wrong `Content-Range` or a short body are refused, and an unavailable index is refused. A static test asserts that the worker modules contain no path to the observation reader and no fitting call, and that the CLI refuses to download without `--confirm-download`.

## Running it

```text
python scripts/live/run_live_cycle.py latest                       # which recent cycle has a complete index (index files only)
python scripts/live/run_live_cycle.py plan   --date YYYYMMDD       # exact ranges and bytes; no message body
python scripts/live/run_live_cycle.py run    --date YYYYMMDD --confirm-download
python scripts/live/run_live_cycle.py replay --date 2025MMDD       # the proof; needs the local frozen tree
```

A replay cycle is about 8.7 MB of stored messages; a live cycle transfers the same 34 byte ranges (about 9 MB, to be confirmed by `plan`). The worker needs the local, gitignored acquisition and frozen-artifact tree (`experiments/`, `data/`) and `eccodes` and `xgboost`; the web API image does not, and imports only the light bundle verifier.

## What it does not establish

- **No skill for a new cycle.** No observation exists for it, so nothing is verified, and every live product is labelled "EXPERIMENTAL FORECAST: frozen models, no verification yet, not an official warning".
- **Very-heavy skill is still not shown to improve on Raw** (`docs/133`), and the calibrated probabilities were estimated on 2023 and 2024.
- **Model drift.** NOAA can change the GEFS configuration after the training years; the frozen models would then extrapolate. The range check only flags it.
- **Not operational infrastructure.** No scheduler, retries, alerting, hosted worker or storage service; the input is NOAA GEFS, not an NCMRWF model; only the control member is used; no district table is produced for a live cycle.
- **NOAA retention.** The public bucket has no stated long-term retention.

## Tests

`backend/tests/test_live_pipeline.py` (selection and range rules, plan, bundle, tamper, no-observation path, the replay gate and the broken-input cases; the last two skip, not pass, when the local tree is absent), `backend/tests/test_live_api.py` (synthetic bundles: served equals stored, labels, staleness, withheld leads, tamper refusal, path traversal), `frontend-v2/src/lib/api/live.test.ts`, `frontend-v2/tests/e2e/live-cycle.spec.ts`.
