# Phase 2C Historical Video Case Catalogue

These six 2019 cases were chosen **after** the one-time held-out verification,
only as descriptive examples: the three largest observed-heavy-area cases,
then the middle chronological common case at each +24/+48/+72-hour lead.
They are not “best model cases,” and selection is not evidence of overall
superiority. The aggregate 2019 reports remain the evidence. Full valid
periods, regime probabilities, heavy/very-heavy probability summaries,
threshold/scale FSS, and district tables are in the hash-verified per-case
JSONs and `data/manifests/phase2c/video_case_catalogue.json`.

| Case ID | Lead | Observed heavy cells | Raw RMSE mm | Corrected RMSE mm | Mean heavy probability | Dominant prototype regime | Descriptor |
|---|---:|---:|---:|---:|---:|---|---|
| `20190807T000000Z_day2_24h` | +48h | 200 | 49.49 | 50.16 | 0.0479 | Low/depression influenced | High observed heavy area; correction worsened |
| `20190808T000000Z_day1_24h` | +24h | 200 | 44.91 | 51.28 | 0.0320 | Low/depression influenced | High observed heavy area; correction worsened |
| `20190804T000000Z_day3_24h` | +72h | 174 | 33.12 | 33.36 | 0.0388 | Low/depression influenced | High observed heavy area at longer lead |
| `20190801T000000Z_day1_24h` | +24h | 44 | 17.30 | 17.34 | 0.0367 | Low/depression influenced | Middle chronological +24h example |
| `20190802T000000Z_day2_24h` | +48h | 147 | 40.91 | 42.89 | 0.0706 | Active monsoon | Different predicted regime; correction worsened |
| `20190802T000000Z_day3_24h` | +72h | 158 | 41.74 | 41.33 | 0.0628 | Low/depression influenced | Longer lead; modest case-level RMSE improvement |

This set deliberately includes failures. The frozen 2019 aggregate RMSE
improvement is 9.73% versus Raw GEFS, but corrected deterministic heavy-rain
CSI/ETS and FSS are worse. The separate calibrated probability models should
be described on their own metrics and held-out event counts.
