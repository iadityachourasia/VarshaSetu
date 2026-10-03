"""Acquire the GEFSv12 reforecast CONTROL member (c00) for June to September of a range of years: rainfall plus six atmospheric fields, Days 1-3 (docs/142).

Source: the public NOAA bucket noaa-gefs-retrospective (object layout of ``backend/app/data_sources/noaa_gefs_monthly.object_url``). Only the selected byte ranges are fetched: the 25 APCP messages up to
+75 h (contiguous, so one range request that is split by the index offsets) and the six atmospheric messages at +24, +48 and +72 h. Every message is stored as its own file with a receipt (URL, byte range,
length, SHA-256), the same discipline as the operational corpus. Resumable: a message with a valid receipt is never fetched again. No observation is read here.

    python scripts/data/acquire_reforecast_control.py plan   --years 2016 --months 6          # index files only; reports the exact transfer
    python scripts/data/acquire_reforecast_control.py fetch  --years 2016 --months 6 --workers 6
    python scripts/data/acquire_reforecast_control.py status --years 2000-2016
"""

from __future__ import annotations

import argparse
import hashlib
import http.client
import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.app.data_sources.noaa_gefs_monthly import ATMOSPHERIC_SPECS, object_url, parse_generic_index, select_atmospheric_entry, select_precipitation_entries  # noqa: E402

RAW = ROOT / "data/raw/forecasts/gefsv12_control_v1"
LEADS = (24, 48, 72)
UTC = timezone.utc
_LOCAL = __import__("threading").local()


def days(year: int, month: int) -> list[datetime]:
    n = {6: 30, 7: 31, 8: 31, 9: 30}[month]
    return [datetime(year, month, d, tzinfo=UTC) for d in range(1, n + 1)]


def _conn(host: str) -> http.client.HTTPSConnection:
    c = getattr(_LOCAL, "conn", None)
    if c is None:
        c = _LOCAL.conn = http.client.HTTPSConnection(host, timeout=90)
    return c


def _get(url: str, headers: dict | None = None) -> tuple[int, dict, bytes]:
    parts = urlsplit(url)
    path = parts.path + (f"?{parts.query}" if parts.query else "")
    for attempt in range(5):
        try:
            conn = _conn(parts.netloc)
            conn.request("GET", path, headers=headers or {})
            r = conn.getresponse()
            body = r.read()
            if r.status in (500, 502, 503, 504, 429, 408):
                raise OSError(f"HTTP {r.status}")
            return r.status, {k.lower(): v for k, v in r.getheaders()}, body
        except (OSError, http.client.HTTPException):
            _LOCAL.conn = None
            if attempt == 4:
                raise
            time.sleep(2 ** (attempt + 1))
    raise AssertionError("unreachable")


def job_dir(init: datetime) -> Path:
    return RAW / f"{init:%Y}" / f"{init:%Y%m%d%H}"


def messages_for(init: datetime) -> list[tuple[str, str, str, int]]:
    """(family, name, kind, lead): the rain object once ("apcp_sfc"), and each atmospheric object at each lead."""
    out = [("apcp_sfc", "apcp", "rain", 0)]
    for variable, spec in ATMOSPHERIC_SPECS.items():
        out += [(spec.object_family, variable, "atm", lead) for lead in LEADS]
    return out


def plan_init(init: datetime) -> dict:
    """Index files only. Returns the byte ranges and total bytes this initialization needs."""
    plan, total = [], 0
    for family in sorted({m[0] for m in messages_for(init)}):
        url = object_url(init, "c00", family)
        status, _, body = _get(url + ".idx")
        if status != 200:
            return {"init": init.isoformat(), "status": f"index_http_{status}", "family": family, "bytes": 0, "ranges": []}
        entries = parse_generic_index(body.decode("ascii"))
        if family == "apcp_sfc":
            selected = select_precipitation_entries(entries)
            start, end = selected[0].byte_start, selected[-1].byte_end
            if end - start + 1 != sum(e.byte_size for e in selected):
                return {"init": init.isoformat(), "status": "rain_messages_not_contiguous", "family": family, "bytes": 0, "ranges": []}
            plan.append({"family": family, "url": url, "kind": "rain", "start": start, "end": end, "entries": [(e.message_number, e.byte_start, e.byte_end, e.description) for e in selected]})
            total += end - start + 1
        else:
            variable = next(v for v, s in ATMOSPHERIC_SPECS.items() if s.object_family == family)
            for lead in LEADS:
                e = select_atmospheric_entry(entries, ATMOSPHERIC_SPECS[variable], lead)
                plan.append({"family": family, "url": url, "kind": "atm", "variable": variable, "lead": lead, "start": e.byte_start, "end": e.byte_end,
                             "entries": [(e.message_number, e.byte_start, e.byte_end, e.description)]})
                total += e.byte_size
    return {"init": init.isoformat(), "status": "ok", "bytes": total, "ranges": plan}


def _fetch_range(url: str, start: int, end: int) -> bytes:
    status, headers, body = _get(url, {"Range": f"bytes={start}-{end}"})
    if status != 206 or not headers.get("content-range", "").startswith(f"bytes {start}-{end}/") or len(body) != end - start + 1:
        raise OSError(f"range refused or short: HTTP {status}, {len(body)} of {end - start + 1}")
    return body


def fetch_init(init: datetime) -> dict:
    directory = job_dir(init)
    done_marker = directory / "COMPLETE.json"
    if done_marker.exists():
        return {"init": init.isoformat(), "status": "already_complete", "bytes": 0}
    plan = plan_init(init)
    if plan["status"] != "ok":
        directory.mkdir(parents=True, exist_ok=True)
        (directory / "UNAVAILABLE.json").write_text(json.dumps(plan, indent=1), encoding="utf-8")
        return {"init": init.isoformat(), "status": plan["status"], "bytes": 0}
    directory.mkdir(parents=True, exist_ok=True)
    fetched, receipts = 0, []
    for item in plan["ranges"]:
        body = _fetch_range(item["url"], item["start"], item["end"])
        fetched += len(body)
        for number, start, stop, description in item["entries"]:
            piece = body[start - item["start"]: stop - item["start"] + 1]
            name = f"{item['family']}_msg{number:04d}" if item["kind"] == "rain" else f"{item['family']}_f{item['lead']:03d}"
            path = directory / f"{name}.grib2"
            path.write_bytes(piece)
            receipts.append({"file": path.name, "family": item["family"], "message_number": number, "byte_start": start, "byte_end": stop, "bytes": len(piece), "sha256": hashlib.sha256(piece).hexdigest(),
                             "index_line": description, "url": item["url"], "variable": item.get("variable", "rain"), "lead": item.get("lead")})
    done_marker.write_text(json.dumps({"init": init.isoformat(), "fetched_at_utc": datetime.now(UTC).isoformat(timespec="seconds"), "bytes": fetched, "receipts": receipts}, indent=1), encoding="utf-8")
    return {"init": init.isoformat(), "status": "fetched", "bytes": fetched}


def parse_years(text: str) -> list[int]:
    if "-" in text:
        a, b = text.split("-")
        return list(range(int(a), int(b) + 1))
    return [int(x) for x in text.split(",")]


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("command", choices=("plan", "fetch", "status"))
    p.add_argument("--years", required=True)
    p.add_argument("--months", default="6,7,8,9")
    p.add_argument("--workers", type=int, default=6)
    a = p.parse_args()
    inits = [i for y in parse_years(a.years) for m in (int(x) for x in a.months.split(",")) for i in days(y, m)]
    if a.command == "status":
        done = sum(1 for i in inits if (job_dir(i) / "COMPLETE.json").exists())
        unavailable = sum(1 for i in inits if (job_dir(i) / "UNAVAILABLE.json").exists())
        print(json.dumps({"initializations": len(inits), "complete": done, "unavailable": unavailable, "remaining": len(inits) - done - unavailable}))
        return 0
    started, total, results = time.time(), 0, []
    with ThreadPoolExecutor(max_workers=a.workers) as pool:
        futures = {pool.submit(plan_init if a.command == "plan" else fetch_init, i): i for i in inits}
        for k, f in enumerate(as_completed(futures), 1):
            try:
                r = f.result()
            except Exception as error:                      # reported, never hidden; the next run resumes
                r = {"init": futures[f].isoformat(), "status": f"error:{type(error).__name__}:{error}", "bytes": 0}
            results.append(r)
            total += r["bytes"]
            if k % 20 == 0 or k == len(inits):
                print(f"{k}/{len(inits)} done, {total / 1e6:.1f} MB, {time.time() - started:.0f}s", flush=True)
    counts: dict[str, int] = {}
    for r in results:
        counts[r["status"].split(":")[0] if r["status"].startswith("error") else r["status"]] = counts.get(r["status"].split(":")[0] if r["status"].startswith("error") else r["status"], 0) + 1
    print(json.dumps({"command": a.command, "initializations": len(inits), "total_bytes": total, "outcomes": counts, "seconds": round(time.time() - started)}))
    return 0 if not any(r["status"].startswith("error") for r in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
