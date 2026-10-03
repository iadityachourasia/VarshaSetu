"""Worker for the experimental live view (docs/139). Run from the repository root with the project virtual environment.

    python scripts/live/run_live_cycle.py latest                  # newest cycle whose index files exist (index files only, a few kilobytes)
    python scripts/live/run_live_cycle.py plan   --date YYYYMMDD  # exactly which byte ranges and how many bytes a run would transfer; no message body is fetched
    python scripts/live/run_live_cycle.py run    --date YYYYMMDD --confirm-download   # fetch, decode, infer with the frozen models, publish a live bundle
    python scripts/live/run_live_cycle.py replay --date 2025MMDD  # the same code path on an already-acquired 2025 cycle, compared with the frozen artifacts; writes a replay bundle

The web API stays read-only; it only serves finished, hash-verified bundles under data/live/. Nothing here reads an observation, retrains or recalibrates. A refused cycle publishes nothing.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

import numpy as np  # noqa: E402

from backend.app.live import bundle, pipeline  # noqa: E402
from backend.app.ml.phase2b import FEATURE_NAMES  # noqa: E402

TRAIN_MATRIX = ROOT / "data/operational_derived/operational_features_2023_2025_v1/2023/train/deterministic/X.npy"


def _training():
    return (np.load(TRAIN_MATRIX, mmap_mode="r", allow_pickle=False), tuple(FEATURE_NAMES)) if TRAIN_MATRIX.is_file() else (None, None)


def cmd_plan(date: str) -> int:
    rows = pipeline.HttpSource(date).plan()
    total = sum(r["bytes"] for r in rows)
    print(json.dumps({"source": f"https://{pipeline.NOAA_HOST}", "date": date, "messages": len(rows), "total_bytes": total, "ranges": rows}, indent=1))
    print(f"\n{len(rows)} messages, {total:,} bytes ({total / 1e6:.1f} MB) would be transferred as byte ranges from {pipeline.NOAA_HOST}.", file=sys.stderr)
    return 0


def cmd_latest() -> int:
    today = datetime.now(timezone.utc).date()
    for back in range(0, 8):
        date = (today - timedelta(days=back)).strftime("%Y%m%d")
        try:
            rows = pipeline.HttpSource(date).plan()
        except pipeline.CycleRefused as error:
            print(f"{date}: not available ({error})")
            continue
        print(f"{date}: complete index; {sum(r['bytes'] for r in rows):,} bytes for the {len(rows)} selected messages")
        return 0
    print("no cycle with a complete index was found in the last 8 days")
    return 1


def _publish(kind: str, date: str, result: dict, extra: dict | None = None) -> Path:
    products = sorted({k.rsplit("_", 2)[-2] + "_" + k.rsplit("_", 2)[-1] for k in result["arrays"] if k.startswith("M1_")})
    return bundle.write_bundle(bundle.ROOT, kind, date, result["arrays"], products, result["provenance"], extra=extra)


def cmd_run(date: str, confirmed: bool) -> int:
    if not confirmed:
        print("refusing to download without --confirm-download; run `plan` first to see the exact transfer", file=sys.stderr)
        return 2
    if (bundle.ROOT / "live" / date).exists():
        print(f"a live bundle for {date} already exists and is immutable", file=sys.stderr)
        return 3
    models = pipeline.FrozenModels.load()
    training, names = _training()
    try:
        result = pipeline.run_cycle(pipeline.HttpSource(date), date, models, training_matrix=training, feature_names=names)
    except pipeline.CycleRefused as error:
        print(f"CYCLE REFUSED, nothing published: {error}", file=sys.stderr)
        return 4
    path = _publish("live", date, result)
    print(f"published {path}")
    return 0


def cmd_replay(date: str) -> int:
    from backend.app.live import replay
    from backend.app.live.stored import StoredSource
    if not replay.available():
        print("the local acquisition and frozen-artifact tree is not available; the replay gate cannot run", file=sys.stderr)
        return 5
    models = pipeline.FrozenModels.load()
    report = replay.replay(date, models)
    worst = max((v for p in report["products"].values() for k, v in p.items() if k.endswith("difference")), default=0.0)
    print(json.dumps(report, indent=1))
    print(f"largest absolute difference against the frozen artifacts: {worst:.3g}", file=sys.stderr)
    if worst > 1e-9:
        print("REPLAY GATE FAILED: the worker path does not reproduce the frozen outputs; nothing published", file=sys.stderr)
        return 6
    if (bundle.ROOT / "replay" / date).exists():
        print(f"a replay bundle for {date} already exists", file=sys.stderr)
        return 0
    training, names = _training()
    result = pipeline.run_cycle(StoredSource(date), date, models, training_matrix=training, feature_names=names)
    path = _publish("replay", date, result, extra={"replay_comparison": report, "replay_tolerance": 1e-9})
    print(f"published {path}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("latest")
    for name in ("plan", "run", "replay"):
        p = sub.add_parser(name)
        p.add_argument("--date", required=True, help="cycle date YYYYMMDD (00 UTC)")
        if name == "run":
            p.add_argument("--confirm-download", action="store_true")
    args = parser.parse_args()
    if args.command == "latest":
        return cmd_latest()
    if args.command == "plan":
        return cmd_plan(args.date)
    if args.command == "run":
        return cmd_run(args.date, args.confirm_download)
    return cmd_replay(args.date)


if __name__ == "__main__":
    raise SystemExit(main())
