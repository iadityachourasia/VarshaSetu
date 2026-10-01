# Independent years for a fair follow-up: source probe (2021 and 2022)

Status: **metadata probe only**. Nothing was downloaded, no corpus was built, no protocol was frozen, and no model was trained. This is the first step of option D1(a) in `docs/124`, and it answers one question: do the NOAA objects needed for a 2021 and 2022 corpus still exist?

## Why this matters

After the geography-aware experiment (`docs/126`), the 2024 and 2025 results have been seen, so no redesign informed by them can be judged on those years (risk R41). A fair test of any follow-up needs years that have never been used. The operational GEFS archive has used the same GEFSv12 lineage since 2020-09-23, so 2021 and 2022 are the nearest candidate years.

## What was done

`scripts/probe_gefs_availability.py` sent HTTP HEAD requests, which return existence, size and modification time and no body, for 19 sampled 00 UTC dates (nine each in 2021 and 2022, spread over 1 June to 1 October, plus 1 June 2023 as a positive control). For each date it checked the same product families the 2023 to 2025 corpus used, as both the GRIB object and its `.idx` sidecar: control and perturbed-member 0.25 degree rainfall at the first and last Day-1 and Day-3 source hours, and the 0.5 degree atmospheric files at f024 and f072. The recorded result is `docs/artifacts/gefs_2021_2022_head_probe.json`.

## Result

152 of 152 object pairs answered HTTP 200 (72 for 2021, 72 for 2022, 8 for the 2023 control). Five pairs first failed with transient network errors (no HTTP error status) and answered 200 on retry. Sizes are in line with 2023 (about 290 to 300 MB per date for the listed objects).

## What this does not establish

- **It is a sample, not an inventory.** Nine of 125 dates per year, eight of the required objects per date. A full index inventory like `docs/84` would be the next step.
- **Existence is not validity.** Phase 4B found that only 21 of 35 sampled rainfall member-products passed decoded rainfall QC in 2024, so decoded QC, GRIB template and grid checks, and packing-aware 24-hour reconstruction are all still required for 2021 and 2022.
- **IMD observations for 2021 and 2022 were not checked**, and IMD redistribution rights remain unresolved (D2), which limits what may be published or uploaded.
- **NOAA does not promise permanent retention** of this archive, so the objects could disappear before acquisition.

## Estimated cost, if approved

Based on the measured 2023 to 2025 transfer (about 10.5 GB for three years, roughly an hour per year), two years would be about 7 GB and about two hours of transfer, plus index inventory, decoded QC and the IMD side. These are estimates, not measurements for 2021 and 2022.

## Decisions that remain with the project owner

1. Whether to acquire 2021 and 2022 (the download needs explicit confirmation of file set, source and size before it starts).
2. Which year is sealed as the independent test, and which is used for training or validation, written down before any scoring.
3. IMD terms for the new years (D2).

Until these are decided, the geography-aware experiment stays a development-only, negative result.
