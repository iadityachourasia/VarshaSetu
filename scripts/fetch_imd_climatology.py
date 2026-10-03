"""Fetch the IMD annual RF25 files for the active/break climatology (1981-2016) into experiments/recent_historical/imd_climatology/.

Source: the IMD Pune gridded-data endpoint already used for the project's observation files (POST form RF25=<year>), about 25 MB per file, 36 files (about 0.9 GB).
The climatology period 1981-2016 shares no year with any year that is later evaluated (2018, 2019, 2023, 2024, 2025), so no evaluated year contributes to its own labels.
Resumable (an existing file with a manifest is kept), bounded retries with backoff, header-level validation only (coordinate and time axes; the rainfall array is not read here).
Local research use only: IMD redistribution rights are unresolved (docs/80); the files must not be uploaded or republished.

    python scripts/fetch_imd_climatology.py [YEAR ...]    # no argument: all 36 years
"""

from __future__ import annotations

import hashlib
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import numpy as np
from scipy.io import netcdf_file

ROOT = Path(__file__).resolve().parents[1]
ENDPOINT = "https://www.imdpune.gov.in/cmpg/Griddata/RF25.php"
OUT = ROOT / "experiments/recent_historical/imd_climatology"
YEARS = tuple(range(1981, 2017))


def header_check(year: int, path: Path) -> dict:
    with netcdf_file(path, "r", mmap=False) as dataset:
        times = np.asarray(dataset.variables["TIME"].data, dtype=np.float64)
        lat = np.asarray(dataset.variables["LATITUDE"].data, dtype=np.float64)
        lon = np.asarray(dataset.variables["LONGITUDE"].data, dtype=np.float64)
        shape = list(dataset.variables["RAINFALL"].shape)
        units = dataset.variables["RAINFALL"].units.decode()
        time_units = dataset.variables["TIME"].units.decode()
    return {"records": int(times.size), "contiguous_daily": bool(np.all(np.diff(times) == 1)), "variable_shape": shape, "grid_points": [int(lat.size), int(lon.size)],
            "latitude_bounds": [float(lat[0]), float(lat[-1])], "longitude_bounds": [float(lon[0]), float(lon[-1])], "rainfall_units": units, "time_units": time_units,
            "rainfall_values_read": False}


def fetch(year: int) -> dict:
    target, manifest_path = OUT / f"RF25_ind{year}_rfp25.nc", OUT / f"imd_{year}_manifest.json"
    if target.exists() and manifest_path.exists():
        return json.loads(manifest_path.read_text(encoding="utf-8"))
    OUT.mkdir(parents=True, exist_ok=True)
    request = Request(ENDPOINT, data=urlencode({"RF25": year}).encode(), method="POST", headers={"User-Agent": "VarshaSetu-research/1.0 (local academic use)"})
    started = time.time()
    for attempt in range(1, 9):
        try:
            with urlopen(request, timeout=300) as response:
                headers = {k.lower(): v for k, v in response.getheaders()}
                payload = response.read()
            if len(payload) < 5_000_000:
                raise OSError(f"unexpectedly small response ({len(payload)} bytes)")
            break
        except OSError as error:
            print(f"year {year} attempt {attempt} failed: {type(error).__name__}", flush=True)
            if attempt == 8:
                raise
            time.sleep(10 * attempt)
    temporary = target.with_name(target.name + ".part")
    temporary.write_bytes(payload)
    temporary.replace(target)
    meta = {"year": year, "byte_size": len(payload), "sha256": hashlib.sha256(payload).hexdigest(), "download_endpoint": ENDPOINT, "request_form": {"RF25": year},
            "retrieved_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"), "elapsed_seconds": round(time.time() - started, 1),
            "response_headers": {k: headers[k] for k in ("content-type", "content-disposition", "date", "server") if k in headers},
            "header_validation": header_check(year, target)}
    manifest_path.write_text(json.dumps(meta, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return meta


if __name__ == "__main__":
    years = tuple(int(a) for a in sys.argv[1:]) or YEARS
    for y in years:
        if y not in YEARS:
            raise SystemExit(f"{y} is outside the climatology period 1981-2016")
    for y in years:
        m = fetch(y)
        print(y, m["byte_size"], m["sha256"][:16], m["header_validation"]["records"], m["header_validation"]["grid_points"], flush=True)
