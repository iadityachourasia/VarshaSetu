"""One bounded unattended attempt at an experimental NOAA GEFS 00 UTC cycle.

Designed for Windows Task Scheduler. The published bundle remains immutable and
the API remains read-only. This process never reads observations. A quality
refusal is logged and is not retried within the same invocation.
"""

from __future__ import annotations

import argparse
from contextlib import redirect_stderr
from io import StringIO
import json
import os
import shutil
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from backend.app.live import bundle, pipeline, season  # noqa: E402
from scripts.live.run_live_cycle import cmd_run  # noqa: E402

LOG_ROOT = ROOT / "data/live/run_logs"
MIN_FREE_BYTES = 50 * 1024**3


def record(outcome: str, *, date: str | None, detail: str, log_root: Path = LOG_ROOT) -> Path:
    log_root.mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc)
    path = log_root / f"{now.strftime('%Y%m%dT%H%M%S%fZ')}_{uuid4().hex}.json"
    payload = {"time_utc": now.isoformat(), "outcome": outcome, "cycle": date, "detail": detail,
               "observation_read": False, "worker": "research_pilot_scheduled_v1"}
    with path.open("x", encoding="utf-8") as stream:
        json.dump(payload, stream, sort_keys=True)
        stream.write("\n")
    return path


def run_once(*, today=None, live_root: Path | None = None, log_root: Path = LOG_ROOT,
             source_factory=pipeline.HttpSource, runner=cmd_run, disk_free=None) -> int:
    live_root = live_root or bundle.ROOT
    live_root.mkdir(parents=True, exist_ok=True)
    lock = live_root / ".scheduled.lock"
    try:
        with lock.open("x", encoding="utf-8") as stream:
            stream.write(f"pid={os.getpid()} utc={datetime.now(timezone.utc).isoformat()}\n")
    except FileExistsError:
        print("scheduled worker already has a lock; inspect and remove a stale lock manually", file=sys.stderr)
        return 7
    try:
        current = today or datetime.now(timezone.utc).date()
        if season.jjas_scope(current.strftime("%Y%m%d")) != "JJAS_RESEARCH_SCOPE":
            record("outside_jjas_scope", date=current.strftime("%Y%m%d"),
                   detail="scheduled NOAA inference is limited to June-September research initializations", log_root=log_root)
            return 0
        candidates = [(current - timedelta(days=back)).strftime("%Y%m%d") for back in range(4)]
        for date in candidates:
            if season.jjas_scope(date) != "JJAS_RESEARCH_SCOPE":
                continue
            if (live_root / "live" / date).is_dir():
                record("already_published", date=date, detail="latest available published cycle was found", log_root=log_root)
                return 0
            try:
                rows = source_factory(date).plan()
            except (pipeline.CycleRefused, OSError) as error:
                record("source_unavailable", date=date, detail=str(error), log_root=log_root)
                continue
            free = disk_free if disk_free is not None else shutil.disk_usage(live_root).free
            if free < MIN_FREE_BYTES:
                record("disk_guard", date=date, detail=f"free bytes {free} below {MIN_FREE_BYTES}", log_root=log_root)
                return 8
            planned = sum(row["bytes"] for row in rows)
            if planned > 100 * 1024**2:
                record("transfer_guard", date=date, detail=f"planned bytes {planned} exceed 100 MiB", log_root=log_root)
                return 9
            stderr = StringIO()
            with redirect_stderr(stderr):
                outcome = runner(date, True)
            reason = stderr.getvalue().strip()[:2000]
            record("published" if outcome == 0 else "cycle_refused", date=date,
                   detail=f"worker exit {outcome}; planned selected NOAA bytes {planned}" + (f"; {reason}" if reason else ""), log_root=log_root)
            return outcome
        record("no_complete_index", date=None, detail="no complete index in the newest four 00 UTC cycles", log_root=log_root)
        return 4
    finally:
        lock.unlink()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--once", action="store_true", required=True,
                        help="run one bounded scheduled attempt; required to avoid accidental execution")
    parser.parse_args()
    return run_once()


if __name__ == "__main__":
    raise SystemExit(main())
