"""Acquire ERA5 geopotential (6-hourly, 13 levels, 1.5 degree) for 1 June to 3 October of a range of years from the public WeatherBench2 store (docs/142).

Source: gs://weatherbench2/datasets/era5/1959-2023_01_10-6h-240x121_equiangular_with_poles_conservative.zarr, read over HTTPS with no credentials (zarr v2, blosc chunks of 8 time steps x 13 levels).
ERA5 is a REANALYSIS: it is used only to derive retrospective regime labels (AGENTS.md section 3.5); it is never a forecast input. Only the geopotential variable is read (about 7.7 MB per 2-day chunk): the
geostrophic vorticity at 500 and 850 hPa that the labels use is computed from it, the same quantity the forecast-side western-disturbance indicator uses. Each chunk is stored raw with its SHA-256.

    python scripts/data/acquire_era5_geopotential.py plan  --years 2000-2023
    python scripts/data/acquire_era5_geopotential.py fetch --years 2000-2023 --workers 4
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BASE = "https://storage.googleapis.com/weatherbench2/datasets/era5/1959-2023_01_10-6h-240x121_equiangular_with_poles_conservative.zarr"
OUT = ROOT / "data/raw/era5_wb2_1p5_geopotential_v1"
ORIGIN = date(1959, 1, 1)
STEPS_PER_CHUNK = 8


def chunks_for(year: int) -> list[int]:
    """Chunk indices covering 1 June 00 UTC to 3 October 18 UTC of the year (6-hourly steps, 4 per day)."""
    first = (date(year, 6, 1) - ORIGIN).days * 4
    last = (date(year, 10, 3) - ORIGIN).days * 4 + 3
    return list(range(first // STEPS_PER_CHUNK, last // STEPS_PER_CHUNK + 1))


def get(path: str, retries: int = 5) -> bytes:
    for attempt in range(retries):
        try:
            return urllib.request.urlopen(f"{BASE}/{path}", timeout=120).read()
        except (urllib.error.URLError, OSError):
            if attempt == retries - 1:
                raise
            time.sleep(2 ** (attempt + 1))
    raise AssertionError("unreachable")


def fetch_chunk(chunk: int) -> dict:
    path = OUT / "geopotential" / f"{chunk}.0.0.0"
    receipt = OUT / "receipts" / f"{chunk}.json"
    if path.exists() and receipt.exists():
        saved = json.loads(receipt.read_text(encoding="utf-8"))
        if hashlib.sha256(path.read_bytes()).hexdigest() == saved["sha256"]:
            return {"chunk": chunk, "bytes": 0, "status": "cached"}
    body = get(f"geopotential/{chunk}.0.0.0")
    path.parent.mkdir(parents=True, exist_ok=True)
    receipt.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(body)
    receipt.write_text(json.dumps({"chunk": chunk, "bytes": len(body), "sha256": hashlib.sha256(body).hexdigest(), "url": f"{BASE}/geopotential/{chunk}.0.0.0",
                                   "fetched_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds")}), encoding="utf-8")
    return {"chunk": chunk, "bytes": len(body), "status": "fetched"}


def fetch_metadata() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    for name in ("geopotential/.zarray", "geopotential/.zattrs", "level/.zarray", "level/0", "latitude/.zarray", "latitude/0", "longitude/.zarray", "longitude/0", "time/.zarray", "time/.zattrs"):
        target = OUT / "meta" / name.replace("/", "__")
        target.parent.mkdir(parents=True, exist_ok=True)
        if not target.exists():
            target.write_bytes(get(name))


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("command", choices=("plan", "fetch"))
    p.add_argument("--years", required=True)
    p.add_argument("--workers", type=int, default=4)
    a = p.parse_args()
    years = list(range(int(a.years.split("-")[0]), int(a.years.split("-")[1]) + 1)) if "-" in a.years else [int(x) for x in a.years.split(",")]
    chunks = sorted({c for y in years for c in chunks_for(y)})
    if a.command == "plan":
        sizes = [int(urllib.request.urlopen(urllib.request.Request(f"{BASE}/geopotential/{c}.0.0.0", method="HEAD"), timeout=60).headers["Content-Length"]) for c in chunks[:: max(1, len(chunks) // 12)]]
        est = sum(sizes) / len(sizes) * len(chunks)
        print(json.dumps({"chunks": len(chunks), "sampled": len(sizes), "estimated_bytes": int(est), "estimated_gb": round(est / 1e9, 2)}))
        return 0
    fetch_metadata()
    started, total = time.time(), 0
    with ThreadPoolExecutor(max_workers=a.workers) as pool:
        futures = [pool.submit(fetch_chunk, c) for c in chunks]
        for k, f in enumerate(as_completed(futures), 1):
            total += f.result()["bytes"]
            if k % 50 == 0 or k == len(chunks):
                print(f"{k}/{len(chunks)} chunks, {total / 1e6:.0f} MB, {time.time() - started:.0f}s", flush=True)
    print(json.dumps({"chunks": len(chunks), "bytes": total, "seconds": round(time.time() - started)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
