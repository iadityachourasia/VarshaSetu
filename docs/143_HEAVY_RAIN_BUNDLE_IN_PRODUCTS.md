# 143. The frozen heavy-rain bundle in the map and district products

Status: built and verified on 3 October 2026. Scope: Track A, the 255 cases of 2019. Protocol frozen before any prediction was computed: `backend/app/evidence_data/phase17/heavy_rain_integration_protocol_v1.json` (sha256 in its sidecar).

## Why

The reforecast study (docs/142) produced the only correction in this project that improves heavy and very-heavy rain detection with intervals that exclude zero: a B1 regression (event-weighted, with static geography) plus two exceedance classifiers. It lived on the Verification Lab only. The maps and district product showed the frozen global model (M2), which suppresses extremes, so the product did not show the improvement the problem statement asks for. This work puts the frozen bundle into those products as an additional, clearly labelled layer. Nothing is refitted, reselected or retuned, and no frozen product artifact is changed.

## What a user can now do

| Surface | Control | What changes |
|---|---|---|
| Forecast Explorer (2019) | Corrected model: M2 or B1 | The corrected panel shows the B1 rainfall (shifted regression). The inspector and the case RMSE follow the choice. If the layer cannot be verified the panel stays M2 and says so. |
| Extreme Rain (2019) | Output: calibrated probability or B1 classifier | The classifier view shows the score or the yes/no forecast at the frozen threshold, for heavy and very heavy, with its own quality figures and no reliability curve (the score is not calibrated). |
| District Intelligence (2019) | Corrected model: M2 or B1 | Map and table use the frozen district aggregation of the B1 fields: mean and maximum rainfall, area-weighted classifier score, and the share of the district where the yes/no forecast says yes. |

Every use shows the governed label (`POST-HOC EXPLORATORY ANALYSIS OF THE COMPLETED 2019 FINAL TEST`), the 2019 numbers read from the frozen manifest, and the limits.

## How it was built and checked

- `scripts/write_heavy_rain_product_protocol.py` froze the protocol (write-once, with the owner's instruction recorded verbatim as an interpretation the owner may withdraw).
- `scripts/build_heavy_rain_product.py` (local only: it needs the gitignored models, the forecast-side cache and the IMD files) applies the frozen bundle and writes `heavy_rain_b1_2019_v1.npz` and `heavy_rain_b1_manifest.json` (write-once, sidecars). **It checks every gate before writing and writes nothing on a failure.** All gates passed:
  1. every model file hash equals the confirmatory record;
  2. each product case has exactly one corpus case, and the cells scored are exactly the product's valid cells;
  3. recomputing the confirmatory pooled results with the same prediction function reproduces the frozen evidence exactly (hits, misses and false alarms of both classifiers, pooled mean error and RMSE, within 1e-9) over all confirmatory years;
  4. the 2019 slice equals the per-year entry of the confirmatory evidence;
  5. no rainfall value is negative or undefined on a valid cell, and scores lie between zero and one.
- `backend/app/api/heavy_rain.py` serves it read-only. Each request checks the protocol and manifest sidecars, the protocol hash in the manifest, the array hash, and that the confirmatory record and evidence still carry the hashes the protocol froze. Any mismatch is a 503 integrity failure.
- `backend/tests/test_heavy_rain_product.py` (15 tests): chain and protocol, frozen thresholds and shift, served values, decisions equal "score at or above the frozen threshold", exactly the product's cases and cells, an independent loop over the cells reproducing every district number, tamper cases, and a local-only test that fresh predictions equal the stored arrays.
- Browser checks: `frontend-v2/tests/e2e/heavy-rain-product.spec.ts`.

## Results on the 2019 cases (descriptive, post-hoc)

| | Raw GEFS | M2 global model | B1 |
|---|---|---|---|
| RMSE (mm per 24 h) | 19.77 | 17.85 | 17.42 |
| Mean error (mm) | 0.59 | -1.60 | +1.93 |

The B1 mean error on these cases alone is above the frozen 1.5 mm guardrail, although the pooled confirmatory years pass it; the notice says both.

| Classifier at its frozen threshold | Heavy | Very heavy |
|---|---|---|
| CSI | 0.294 (Raw 0.120) | 0.220 |
| Frequency bias | 1.90 (Raw 0.51) | 1.96 |

The yes/no forecast flags roughly twice as many events as occur, so hits and false alarms rise together.

## What this does and does not show

- It makes the improvement visible in the products and puts the cost next to it (over-forecasting, mean error above the guardrail on these cases, scores that are not probabilities).
- It does **not** make the bundle an operational or validated forecast. It was built on the GEFSv12 reforecast control member, a different model version from the operational years, and has not been tested there. The first confirmatory round failed the mean-error guardrail and the shift was read from it; 2019 was in the confirmatory years and had been used by earlier Track A experiments.
- It adds nothing for regime-aware routing, which was not shown to add value.
- Only the 2019 cases carry the layer. The operational years (2024, 2025) are not covered, and applying the bundle to them is not authorised by the protocol.

## Rebuilding

The outputs are write-once. A rebuild needs a new protocol version and a new output name; do not delete and rerun to "fix" a result.
