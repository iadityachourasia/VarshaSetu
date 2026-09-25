"""Acquire official annual IMD 0.25-degree rainfall with atomic provenance."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import time
import urllib.parse
import urllib.request
from datetime import date, datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCE_PAGE = "https://www.imdpune.gov.in/cmpg/Griddata/Rainfall_25_NetCDF.html"
DOWNLOAD_ENDPOINT = "https://www.imdpune.gov.in/cmpg/Griddata/RF25.php"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def validate(path: Path, year: int) -> dict:
    import sys

    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    from backend.app.data_sources.imd_rainfall import inspect_imd_netcdf, load_imd_day

    inspection = inspect_imd_netcdf(path)
    first = load_imd_day(
        path, date(year, 1, 1), south=10, north=22, west=68, east=80
    )
    last = load_imd_day(
        path, date(year, 12, 31), south=10, north=22, west=68, east=80
    )
    return {
        "inspection": inspection,
        "first_record": first.metadata,
        "last_record": last.metadata,
        "target_grid_shape": list(first.rainfall_mm.shape),
        "first_valid_cells": int(first.valid_mask.sum()),
        "last_valid_cells": int(last.valid_mask.sum()),
    }


def acquire(year: int, destination: Path, manifest: Path) -> dict:
    if destination.exists() and manifest.exists():
        existing = json.loads(manifest.read_text(encoding="utf-8"))
        digest = sha256_file(destination)
        if digest != existing.get("sha256") or destination.stat().st_size != existing.get("byte_size"):
            raise ValueError("existing IMD source bytes do not match their manifest")
        validate(destination, year)
        return existing | {"from_cache": True}
    if destination.exists() != manifest.exists():
        raise ValueError("partial IMD cache state; quarantine before retrying")

    destination.parent.mkdir(parents=True, exist_ok=True)
    manifest.parent.mkdir(parents=True, exist_ok=True)
    partial = destination.with_name(destination.name + ".part")
    manifest_partial = manifest.with_name(manifest.name + ".part")
    if partial.exists() or manifest_partial.exists():
        raise ValueError("stale IMD partial artifact exists; quarantine before retrying")

    payload = urllib.parse.urlencode({"RF25": str(year)}).encode("ascii")
    request = urllib.request.Request(
        DOWNLOAD_ENDPOINT,
        data=payload,
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "User-Agent": "VarshaSetu-Authoritative-Corpus/2A",
            "Referer": SOURCE_PAGE,
        },
        method="POST",
    )
    started = time.perf_counter()
    digest = hashlib.sha256()
    byte_size = 0
    response_headers = {}
    try:
        with urllib.request.urlopen(request, timeout=300) as response:
            status = int(getattr(response, "status", 0) or 0)
            if status != 200:
                raise IOError(f"unexpected IMD status {status}")
            response_headers = {
                key.lower(): value for key, value in response.headers.items()
            }
            with partial.open("xb") as handle:
                while True:
                    block = response.read(1024 * 1024)
                    if not block:
                        break
                    handle.write(block)
                    digest.update(block)
                    byte_size += len(block)
                handle.flush()
                os.fsync(handle.fileno())
        scientific_validation = validate(partial, year)
        record = {
            "provider": "India Meteorological Department",
            "product": "0.25 degree daily gridded rainfall",
            "year": year,
            "source_page": SOURCE_PAGE,
            "download_endpoint": DOWNLOAD_ENDPOINT,
            "request_method": "POST",
            "request_form": {"RF25": year},
            "retrieved_at_utc": datetime.now(timezone.utc).isoformat(),
            "elapsed_seconds": time.perf_counter() - started,
            "response_headers": response_headers,
            "path": destination.relative_to(ROOT).as_posix(),
            "byte_size": byte_size,
            "sha256": digest.hexdigest(),
            "scientific_validation": scientific_validation,
            "from_cache": False,
        }
        manifest_partial.write_text(
            json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        partial.replace(destination)
        manifest_partial.replace(manifest)
        return record
    except Exception:
        partial.unlink(missing_ok=True)
        manifest_partial.unlink(missing_ok=True)
        raise


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("year", type=int, choices=range(1901, 2025))
    parser.add_argument("--destination", type=Path)
    parser.add_argument("--manifest", type=Path)
    args = parser.parse_args()
    destination = args.destination or ROOT / (
        f"data/raw/observations/imd/{args.year}/RF25_ind{args.year}_rfp25.nc"
    )
    manifest = args.manifest or ROOT / (
        f"data/manifests/phase2a/sources/imd_rf25_{args.year}.json"
    )
    result = acquire(args.year, destination.resolve(), manifest.resolve())
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
