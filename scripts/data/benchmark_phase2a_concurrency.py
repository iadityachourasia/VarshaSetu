"""Bounded Phase 2A concurrency benchmark; never mutates scientific artifacts."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import threading
import time
import urllib.request
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


class PeakMemory:
    """Sample aggregate RSS for this process and its live children."""

    def __init__(self) -> None:
        import psutil

        self.process = psutil.Process()
        self.peak = 0
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._sample, daemon=True)

    def _sample(self) -> None:
        while not self._stop.wait(0.01):
            children = self.process.children(recursive=True)
            rss = self.process.memory_info().rss
            for child in children:
                try:
                    rss += child.memory_info().rss
                except Exception:
                    pass
            self.peak = max(self.peak, rss)

    def __enter__(self):
        self._thread.start()
        return self

    def __exit__(self, exc_type, exc, traceback) -> None:
        self._stop.set()
        self._thread.join()
        self._sample_once()

    def _sample_once(self) -> None:
        rss = self.process.memory_info().rss
        for child in self.process.children(recursive=True):
            try:
                rss += child.memory_info().rss
            except Exception:
                pass
        self.peak = max(self.peak, rss)


def decode_digest(path_text: str) -> dict:
    from scripts.data.investigate_accumulation_anomaly import decode

    messages = decode(Path(path_text))
    digest = hashlib.sha256()
    for message in messages:
        digest.update(message["values"].tobytes())
    return {
        "path": Path(path_text).relative_to(ROOT).as_posix(),
        "message_count": len(messages),
        "decoded_sha256": digest.hexdigest(),
    }


def qc_digest(task: tuple[str, int]) -> dict:
    import numpy as np
    import zarr

    path_text, index = task
    group = zarr.open_group(path_text, mode="r")
    forecast = np.asarray(group["forecast_rain"][index], dtype=np.float64)
    observation = np.asarray(group["observation_rain"][index], dtype=np.float64)
    mask = np.asarray(group["valid_mask"][index], dtype=bool)
    atmosphere = np.asarray(group["atmosphere"][index], dtype=np.float64)
    valid_observation = observation[mask]
    if not np.isfinite(forecast[forecast >= 0]).all():
        raise ValueError("forecast contains non-finite valid values")
    if not np.isfinite(valid_observation).all():
        raise ValueError("observation contains non-finite valid values")
    if not np.isfinite(atmosphere[atmosphere > -999]).all():
        raise ValueError("atmosphere contains non-finite valid values")
    digest = hashlib.sha256()
    digest.update(forecast.tobytes())
    digest.update(observation.tobytes())
    digest.update(mask.tobytes())
    digest.update(atmosphere.tobytes())
    return {
        "index": index,
        "sha256": digest.hexdigest(),
        "negative_forecast_cells": int((forecast < 0).sum()),
        "valid_observation_cells": int(mask.sum()),
    }


def fetch_index(url: str) -> dict:
    started = time.perf_counter()
    retries = 0
    last_error = None
    for attempt in range(3):
        try:
            request = urllib.request.Request(url, headers={"User-Agent": "VarshaSetu/2A-benchmark"})
            with urllib.request.urlopen(request, timeout=45) as response:
                payload = response.read()
            return {
                "url": url,
                "byte_size": len(payload),
                "sha256": hashlib.sha256(payload).hexdigest(),
                "retries": retries,
                "elapsed_seconds": time.perf_counter() - started,
            }
        except Exception as exc:
            last_error = f"{type(exc).__name__}: {exc}"
            retries += 1
            if attempt < 2:
                time.sleep(0.5 * (attempt + 1))
    raise RuntimeError(f"{url}: {last_error}")


def fetch_range(task: tuple[str, int, int]) -> dict:
    url, start, end = task
    started = time.perf_counter()
    retries = 0
    last_error = None
    for attempt in range(3):
        try:
            request = urllib.request.Request(
                url,
                headers={
                    "User-Agent": "VarshaSetu/2A-benchmark",
                    "Range": f"bytes={start}-{end}",
                },
            )
            with urllib.request.urlopen(request, timeout=60) as response:
                payload = response.read()
                status = int(getattr(response, "status", 0) or 0)
                content_range = response.headers.get("Content-Range", "")
            if status != 206 or len(payload) != end - start + 1:
                raise IOError(
                    f"range response mismatch: status={status}, bytes={len(payload)}"
                )
            if not content_range.startswith(f"bytes {start}-{end}/"):
                raise IOError(f"invalid Content-Range: {content_range}")
            return {
                "url": url,
                "byte_range": [start, end],
                "byte_size": len(payload),
                "sha256": hashlib.sha256(payload).hexdigest(),
                "retries": retries,
                "elapsed_seconds": time.perf_counter() - started,
            }
        except Exception as exc:
            last_error = f"{type(exc).__name__}: {exc}"
            retries += 1
            if attempt < 2:
                time.sleep(0.5 * (attempt + 1))
    raise RuntimeError(f"{url}: {last_error}")


def run_pool(function, tasks, workers: int, pool_class) -> dict:
    started = time.perf_counter()
    failures = []
    results = []
    with PeakMemory() as memory:
        with pool_class(max_workers=workers) as pool:
            futures = [pool.submit(function, task) for task in tasks]
            for future in futures:
                try:
                    results.append(future.result())
                except Exception as exc:
                    failures.append(f"{type(exc).__name__}: {exc}")
    return {
        "workers": workers,
        "wall_seconds": time.perf_counter() - started,
        "peak_aggregate_rss_bytes": memory.peak,
        "failures": failures,
        "retry_count": sum(item.get("retries", 0) for item in results),
        "results": results,
    }


def stable_hashes(runs: list[dict], key) -> bool:
    if any(run["failures"] for run in runs):
        return False
    reference = sorted(key(item) for item in runs[0]["results"])
    return all(sorted(key(item) for item in run["results"]) == reference for run in runs[1:])


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--network", action="store_true")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    raw_root = ROOT / "data/raw/phase1c/gefsv12"
    decode_paths = sorted(raw_root.glob("2019060[1-3]00/*/apcp_sfc/selected_*.grib2"))
    if len(decode_paths) != 15:
        raise FileNotFoundError(f"expected 15 cached decode samples, found {len(decode_paths)}")
    decode_runs = [
        run_pool(decode_digest, [str(path) for path in decode_paths], workers, ProcessPoolExecutor)
        for workers in (4, 6, 8)
    ]

    zarr_path = ROOT / "data/processed/phase1f/2019-JJAS/varshasetu-gefs12r-imd025-2019-jjas-v2.zarr"
    qc_tasks = [(str(zarr_path), index) for index in range(12)]
    qc_runs = [
        run_pool(qc_digest, qc_tasks, workers, ProcessPoolExecutor)
        for workers in (4, 6)
    ]

    network_runs = []
    if args.network:
        from datetime import datetime, timezone

        from backend.app.data_sources.noaa_gefs_monthly import object_url

        initialization = datetime(2017, 6, 1, tzinfo=timezone.utc)
        families = (
            "apcp_sfc", "ugrd_pres", "vgrd_pres", "spfh_pres_abv700mb",
            "hgt_pres_abv700mb", "pres_msl", "pwat_eatm",
        )
        urls = [object_url(initialization, "c00", family) for family in families]
        # Include one perturbation object so the sample exercises both key layouts.
        urls.append(object_url(initialization, "p01", "apcp_sfc"))
        range_tasks = [(url, 0, 1024 * 1024 - 1) for url in urls]
        network_runs = [
            run_pool(fetch_range, range_tasks, workers, ThreadPoolExecutor)
            for workers in (4, 6, 8)
        ]

    output = {
        "benchmark_scope": "bounded representative samples; no scientific artifact mutation",
        "hardware_logical_cpu_count": os.cpu_count(),
        "decode": {
            "sample": "15 cached GEFS rainfall chunks from 2019-06-01 through 2019-06-03",
            "runs": decode_runs,
            "hashes_stable": stable_hashes(
                decode_runs, lambda item: (item["path"], item["decoded_sha256"])
            ),
        },
        "qc": {
            "sample": "12 initialization chunks from immutable Phase 1F 2019 v2 Zarr",
            "runs": qc_runs,
            "hashes_stable": stable_hashes(
                qc_runs, lambda item: (item["index"], item["sha256"])
            ),
        },
        "network": {
            "sample": "eight one-MiB HTTP ranges from official NOAA 2017 GRIB objects",
            "executed": args.network,
            "runs": network_runs,
            "hashes_stable": (
                stable_hashes(
                    network_runs,
                    lambda item: (item["url"], tuple(item["byte_range"]), item["sha256"]),
                )
                if network_runs else None
            ),
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(output, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
