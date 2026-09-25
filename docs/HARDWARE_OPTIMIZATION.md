# Hardware Optimization Record

## Phase 2A bounded benchmark

The benchmark used the primary HP Victus development machine described in
`AGENTS.md`. It was intentionally bounded and did not alter scientific
artifacts. Full measurements, per-object hashes, retry counts, and failures are
in `data/manifests/phase2a/hardware_concurrency_benchmark.json`.

| Workload | Configurations | Selected | Selected wall time | Selected peak aggregate RSS | Stability |
|---|---|---:|---:|---:|---|
| Cached ecCodes rainfall decode, 15 chunks | 4/6/8 processes | 8 | 4.782 s | 5.39 GiB | decoded hashes identical; 0 failures |
| Eight official NOAA one-MiB GRIB ranges | 4/6/8 threads | 6 | 5.083 s | recorded in artifact | response hashes identical; 0 failures/retries |
| Twelve Zarr QC chunks | 4/6 processes | 6 | 0.577 s | 0.30 GiB | output hashes identical; 0 failures |

The first network attempt used an incorrect object-key spelling and produced
404 responses only. It was corrected before selection and is not treated as a
performance run. The retained artifact contains the valid rerun.

## Frozen Phase 2A settings

- GRIB decode benchmark selection: 8 processes.
- Network range/index acquisition: 6 threads.
- Local QC/normalization benchmark selection: 6 processes.
- Native numerical-library thread multiplication must remain disabled when a
  process pool is active.
- Normal active scientific RAM remains capped near 18–20 GB.

The monthly acquisition runner uses six I/O threads within one initialization
and processes initializations serially. This avoids nesting a process pool over
the network thread pool. The current decoder remains serial inside that runner;
the eight-process result is recorded for bounded independent decode/replay
stages rather than being forced into a mixed I/O/decode path without another
equivalence check.
