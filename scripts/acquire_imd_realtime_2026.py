"""Acquire official IMD real-time 0.25-degree daily grids as a separate candidate.

The daily binary feed is not silently substituted for the frozen annual-NetCDF
reference. This command records bytes and hashes; it never scores 2026 outcomes.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import numpy as np
from scipy.io import netcdf_file

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.run_2026_frozen_inference import sealed, sha  # noqa: E402

BASE = ROOT / "data/manifests/research_pilot"
PROTOCOL = BASE / "2026_imd_realtime_acquisition_protocol_v1.json"
SOURCE = "https://imdpune.gov.in/cmpg/Realtimedata/Rainfall/rain.php"
PAGE = "https://imdpune.gov.in/cmpg/Realtimedata/Rainfall/Rain_Download.html"
RAW = ROOT / "data/raw/observations/imd_realtime_2026_v1"
PILOT = ROOT / "data/raw/observations/imd_realtime_2025_pilot_v1"
FINAL = BASE / "2026_imd_realtime_acquisition_v1.json"
EXPECTED_BYTES = 129 * 135 * 4
START, END = date(2026, 6, 1), date(2026, 10, 3)


def _request(target: date) -> tuple[bytes, dict]:
    body = urlencode({"rain": target.strftime("%d%m%Y")}).encode("ascii")
    request = Request(SOURCE, data=body, method="POST", headers={
        "User-Agent": "VarshaSetu-research/1.0 (local academic use)",
        "Referer": PAGE,
        "Accept": "application/octet-stream,*/*;q=0.8",
    })
    last = None
    for attempt in range(1, 4):
        try:
            with urlopen(request, timeout=75) as response:
                if response.status != 200:
                    raise ValueError(f"HTTP {response.status}")
                declared = response.headers.get("Content-Length")
                if declared is not None and int(declared) != EXPECTED_BYTES:
                    raise ValueError(f"unexpected Content-Length {declared}")
                raw = response.read(EXPECTED_BYTES + 1)
                if len(raw) != EXPECTED_BYTES:
                    raise ValueError(f"unexpected response length {len(raw)}")
                return raw, {"http_status": response.status, "content_type": response.headers.get("Content-Type"),
                             "content_length": declared, "retrieved_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                             "attempts": attempt}
        except (HTTPError, URLError, OSError, ValueError) as error:
            last = error
            if attempt < 3:
                time.sleep(2 * attempt)
    raise RuntimeError(f"{target}: source unavailable after 3 bounded attempts: {type(last).__name__}: {last}")


def _write_day(target: date, folder: Path) -> dict:
    name = f"rainfall_{target:%Y%m%d}.grd"
    path = folder / name
    receipt = folder / "receipts" / f"{target:%Y%m%d}.json"
    if path.exists() or receipt.exists():
        if not (path.exists() and receipt.exists()):
            raise ValueError(f"partial local day requires investigation: {target}")
        record = json.loads(receipt.read_text(encoding="utf-8"))
        if sha(path) != record["sha256"] or path.stat().st_size != EXPECTED_BYTES:
            raise ValueError(f"cached day changed: {target}")
        return record
    raw, transport = _request(target)
    folder.mkdir(parents=True, exist_ok=True)
    receipt.parent.mkdir(parents=True, exist_ok=True)
    stage = path.with_suffix(".grd.part")
    if stage.exists():
        raise ValueError(f"prior staging file requires investigation: {target}")
    with stage.open("xb") as stream:
        stream.write(raw)
    digest = hashlib.sha256(raw).hexdigest()
    record = {"date": target.isoformat(), "source_endpoint": SOURCE, "request_form": {"rain": target.strftime("%d%m%Y")},
              "byte_size": len(raw), "sha256": digest, "local_path": path.relative_to(ROOT).as_posix(),
              "observation_values_decoded": False, "forecast_pairing": False, **transport}
    stage.rename(path)
    with receipt.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(record, stream, indent=2, sort_keys=True)
        stream.write("\n")
    return record


def compare_2025() -> dict:
    target = date(2025, 9, 30)
    record = _write_day(target, PILOT)
    path = ROOT / record["local_path"]
    grid = np.fromfile(path, dtype="<f4").reshape(129, 135)
    annual_path = ROOT / "experiments/recent_historical/imd/RF25_ind2025_rfp25.nc"
    with netcdf_file(annual_path, "r", mmap=False) as dataset:
        times = np.asarray(dataset.variables["TIME"].data, dtype=np.float64)
        offset = (target - date(1900, 12, 31)).days
        indices = np.flatnonzero(times == offset)
        if len(indices) != 1:
            raise ValueError("2025 annual file missing pilot date")
        annual = np.asarray(dataset.variables["RAINFALL"].data[int(indices[0])], dtype="<f4").copy()
    valid = np.isfinite(grid) & np.isfinite(annual) & (grid >= 0) & (annual >= 0)
    return {"date": target.isoformat(), "daily_sha256": record["sha256"], "annual_sha256": sha(annual_path),
            "shape": list(grid.shape), "valid_both": int(valid.sum()),
            "exact_all_cells": bool(np.array_equal(grid, annual)),
            "exact_valid_cells": bool(np.array_equal(grid[valid], annual[valid])),
            "maximum_absolute_valid_difference_mm": float(np.max(np.abs(grid[valid] - annual[valid]))) if valid.any() else None,
            "daily_missing_cells": int(np.count_nonzero(grid < 0)), "annual_missing_cells": int(np.count_nonzero(annual < 0)),
            "observation_values_read": True, "year_role": "2025_consumed_test_diagnostic_only"}


def acquire_2026() -> dict:
    protocol = sealed(PROTOCOL)
    if protocol["source_endpoint"] != SOURCE or protocol["start_date"] != START.isoformat() or protocol["end_date"] != END.isoformat() or protocol["expected_bytes_per_day"] != EXPECTED_BYTES:
        raise ValueError("acquisition code differs from frozen protocol")
    if FINAL.exists():
        raise FileExistsError("2026 realtime acquisition summary is write-once")
    if shutil.disk_usage(ROOT).free < 50 * 1024**3:
        raise ValueError("50 GiB free-space guard failed")
    dates = [START + timedelta(days=i) for i in range((END - START).days + 1)]
    records, errors = {}, {}
    with ThreadPoolExecutor(max_workers=3) as pool:
        future_by_date = {pool.submit(_write_day, day, RAW): day for day in dates}
        for future in as_completed(future_by_date):
            day = future_by_date[future]
            try:
                records[day.isoformat()] = future.result()
            except Exception as error:  # keep successful immutable files for a later resume
                errors[day.isoformat()] = f"{type(error).__name__}: {error}"
    result = {"schema": "varshasetu-imd-realtime-2026-acquisition-v1", "source_endpoint": SOURCE,
              "source_page": PAGE, "protocol_sha256": sha(PROTOCOL), "expected_dates": len(dates),
              "received_dates": len(records), "errors": errors, "records": dict(sorted(records.items())),
              "observation_values_decoded": False, "forecast_observation_pairing": False,
              "status": "COMPLETE_UNSCORED_CANDIDATE" if not errors else "INCOMPLETE_UNSCORED_CANDIDATE",
              "scientific_role": "separate real-time gauge-product candidate; not annual RF25 NetCDF clearance"}
    if not errors:
        with FINAL.open("x", encoding="utf-8", newline="\n") as stream:
            json.dump(result, stream, indent=2, sort_keys=True)
            stream.write("\n")
        FINAL.with_suffix(".sha256").write_text(f"{sha(FINAL)}  {FINAL.name}\n", encoding="ascii")
    return result


def check_2026() -> dict:
    manifest = sealed(FINAL)
    dates = [START + timedelta(days=i) for i in range((END - START).days + 1)]
    if manifest["status"] != "COMPLETE_UNSCORED_CANDIDATE" or manifest["received_dates"] != len(dates) or manifest["errors"]:
        raise ValueError("2026 real-time source manifest is incomplete")
    if sorted(manifest["records"]) != [day.isoformat() for day in dates]:
        raise ValueError("2026 real-time date set differs")
    for day in dates:
        record = manifest["records"][day.isoformat()]
        expected = RAW / f"rainfall_{day:%Y%m%d}.grd"
        receipt = RAW / "receipts" / f"{day:%Y%m%d}.json"
        if (record["date"] != day.isoformat() or record["local_path"] != expected.relative_to(ROOT).as_posix()
                or record["byte_size"] != EXPECTED_BYTES or expected.stat().st_size != EXPECTED_BYTES
                or sha(expected) != record["sha256"] or json.loads(receipt.read_text(encoding="utf-8")) != record):
            raise ValueError(f"2026 real-time day changed: {day}")
    return {"status": "VERIFIED_UNSCORED", "dates": len(dates), "total_bytes": len(dates) * EXPECTED_BYTES,
            "manifest_sha256": sha(FINAL), "observation_values_decoded": False}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--compare-2025", action="store_true")
    group.add_argument("--acquire-2026", action="store_true")
    group.add_argument("--check-2026", action="store_true")
    args = parser.parse_args()
    result = compare_2025() if args.compare_2025 else check_2026() if args.check_2026 else acquire_2026()
    print(json.dumps(result if args.compare_2025 or args.check_2026 else {k: result[k] for k in ("status", "expected_dates", "received_dates", "errors")}, sort_keys=True))


if __name__ == "__main__":
    main()
