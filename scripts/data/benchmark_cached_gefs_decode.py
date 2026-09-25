"""Benchmark cache-only GEFS decode concurrency without changing values."""

from __future__ import annotations

import argparse
import hashlib
import json
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.data.investigate_accumulation_anomaly import decode


def decode_digest(path_text: str) -> dict:
    path = Path(path_text)
    messages = decode(path)
    digest = hashlib.sha256()
    for message in messages:
        digest.update(message["values"].tobytes())
    return {"path": path_text, "messages": len(messages), "decoded_sha256": digest.hexdigest()}


def run(paths: list[Path], workers: int) -> tuple[float, list[dict]]:
    started = time.perf_counter()
    if workers == 1:
        result = [decode_digest(str(path)) for path in paths]
    else:
        with ProcessPoolExecutor(max_workers=workers) as pool:
            result = list(pool.map(decode_digest, map(str, paths)))
    return time.perf_counter() - started, result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path("data/raw/phase1c/gefsv12/2019072200"))
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    paths = [args.root / member / "apcp_sfc" / f"selected_003_075_2019072200_{member}.grib2" for member in ("c00", "p01", "p02", "p03", "p04")]
    warmup_seconds, warmup = run(paths, 1)
    sequential_seconds, sequential = run(paths, 1)
    two_process_seconds, parallel = run(paths, 2)
    if warmup != sequential or sequential != parallel:
        raise RuntimeError("parallel decode changed decoded-value digests")
    result = {
        "case": "2019-07-22 five cached rainfall members, 25 messages each",
        "warmup_seconds": warmup_seconds,
        "sequential_seconds": sequential_seconds,
        "two_process_seconds": two_process_seconds,
        "speedup": sequential_seconds / two_process_seconds,
        "decoded_values_identical": True,
        "members": sequential,
    }
    rendered = json.dumps(result, indent=2, sort_keys=True)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)


if __name__ == "__main__":
    main()
