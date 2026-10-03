"""Forecast-side corpus of the GEFSv12 reforecast control member (docs/142). Reads NO observation, so it can be built for sealed years.

For each initialization (June to September) and each lead (Day 1, 2, 3): decode the stored control messages (every file hash-checked against its receipt), apply the canonical rainfall reconstruction on the
49x49 target crop, keep the six atmospheric fields at +24/+48/+72 h on the 51x81 context grid, and build the 22-column frozen feature matrix (all 2401 cells) and the forecast-only regime features exactly as the
operational corpus does (``backend.app.live.pipeline.build_features``). A lead whose canonical reconstruction fails is excluded with its reason. Pairing with IMD happens in a later stage and only for years
the protocol allows.

    python scripts/build_reforecast_forecast_side.py --years 2000-2016 [--workers 6]

Output (untracked): data/processed/reforecast_control_v1/<year>/{X_full.npy, regime_X.npy, cases.json}.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from concurrent.futures import ProcessPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

RAW = ROOT / "data/raw/forecasts/gefsv12_control_v1"
OUT = ROOT / "data/processed/reforecast_control_v1"
PRODUCTS = {"day1_24h": (3, 27, 24), "day2_24h": (27, 51, 48), "day3_24h": (51, 75, 72)}
VERSION = "reforecast-control-forecast-side-v1"


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def decode_init(stamp: str) -> dict:
    """Worker: one initialization. Returns per-product results; arrays only for products that pass."""
    from backend.app.data.accumulation import GriddedAccumulationMessage, reconstruct_minimal_accumulation_window
    from backend.app.data_sources.noaa_gefs_monthly import ATMOSPHERIC_SPECS, crop_grid, decode_atmospheric_message, decode_precipitation_message
    from backend.app.data.monthly_qc import bilinear_to_context
    from backend.app.live.pipeline import build_features

    year = stamp[:4]
    folder = RAW / year / stamp
    done = folder / "COMPLETE.json"
    result = {"stamp": stamp, "products": {}, "status": None}
    if not done.exists():
        result["status"] = "source_missing"
        return result
    receipts = json.loads(done.read_text(encoding="utf-8"))["receipts"]
    try:
        rain, atmosphere = [], {}
        for r in receipts:
            payload = (folder / r["file"]).read_bytes()
            if sha(payload) != r["sha256"] or len(payload) != r["bytes"]:
                raise ValueError(f"payload differs from its receipt: {r['file']}")
            if r["variable"] == "rain":
                accumulation, grid = decode_precipitation_message(payload, member="c00", description=r["index_line"], source_id=r["sha256"])
                region = crop_grid(grid, south=10, north=22, west=68, east=80)
                if region.values.shape != (49, 49) or not np.isfinite(region.values).all():
                    raise ValueError("rainfall target crop invalid")
                if grid.metadata["forecast_init"] != f"{stamp[:8]}T0000Z":
                    raise ValueError("decoded initialization differs from the stamp")
                rain.append(GriddedAccumulationMessage(accumulation.start_hour, accumulation.end_hour, region.values, accumulation.source_id, accumulation.packing_quantum_mm))
            else:
                grid = decode_atmospheric_message(payload, member="c00", description=r["index_line"], spec=ATMOSPHERIC_SPECS[r["variable"]], lead_hour=r["lead"])
                region = crop_grid(grid, south=5, north=30, west=55, east=95)
                # the reforecast pressure-level fields are on a coarser native grid: bilinear to the 0.5 degree context grid, as the Track A corpus does
                context, _, _ = bilinear_to_context(region.values, region.latitude, region.longitude)
                if context.shape != (51, 81) or not np.isfinite(context).all():
                    raise ValueError("atmospheric context field invalid")
                atmosphere.setdefault(r["lead"], {})[r["variable"]] = context
    except Exception as error:
        result["status"] = f"decode_failure:{type(error).__name__}:{error}"
        return result
    result["status"] = "decoded"
    rainfall = {}
    for product, (start, end, _) in PRODUCTS.items():
        try:
            window = reconstruct_minimal_accumulation_window(rain, window_start_hour=start, window_end_hour=end)
            field = np.asarray(window.rainfall_mm, dtype=np.float64)
            if field.shape != (49, 49) or not np.isfinite(field).all() or np.any(field < 0):
                raise ValueError("reconstructed field invalid")
            rainfall[product] = field
        except Exception as error:
            result["products"][product] = {"status": "EXCLUDED_RECONSTRUCTION", "reason": f"{type(error).__name__}: {error}"}
    if rainfall:
        features = build_features(rainfall, atmosphere)
        for product, block in features.items():
            result["products"][product] = {"status": "INCLUDED", "X": block["X"], "regime": block["regime"]}
    return result


def build_year(year: int, workers: int) -> dict:
    stamps = [f"{year}{m:02d}{d:02d}00" for m, n in ((6, 30), (7, 31), (8, 31), (9, 30)) for d in range(1, n + 1)]
    with ProcessPoolExecutor(max_workers=workers) as pool:
        results = list(pool.map(decode_init, stamps, chunksize=2))
    cases, xs, regimes = [], [], []
    ledger = {"source_missing": 0, "decode_failure": 0, "EXCLUDED_RECONSTRUCTION": 0, "INCLUDED": 0}
    for r in results:
        if r["status"] != "decoded":
            ledger["source_missing" if r["status"] == "source_missing" else "decode_failure"] += 1
            for product in PRODUCTS:
                cases.append({"case_id": f"{r['stamp'][:8]}_{product}", "initialization": f"{r['stamp'][:4]}-{r['stamp'][4:6]}-{r['stamp'][6:8]}", "product": product, "status": "EXCLUDED_SOURCE", "reason": r["status"], "row": None})
            continue
        for product in PRODUCTS:
            block = r["products"].get(product)
            base = {"case_id": f"{r['stamp'][:8]}_{product}", "initialization": f"{r['stamp'][:4]}-{r['stamp'][4:6]}-{r['stamp'][6:8]}", "product": product}
            if block and block["status"] == "INCLUDED":
                base.update({"status": "INCLUDED", "reason": None, "row": len(xs)})
                xs.append(block["X"])
                regimes.append(block["regime"])
                ledger["INCLUDED"] += 1
            else:
                base.update({"status": block["status"] if block else "EXCLUDED_SOURCE", "reason": block["reason"] if block else "no result", "row": None})
                ledger["EXCLUDED_RECONSTRUCTION"] += 1
            cases.append(base)
    folder = OUT / str(year)
    folder.mkdir(parents=True, exist_ok=True)
    if xs:
        np.save(folder / "X_full.npy", np.stack(xs).astype(np.float32), allow_pickle=False)
        np.save(folder / "regime_X.npy", np.stack(regimes).astype(np.float64), allow_pickle=False)
    (folder / "cases.json").write_text(json.dumps({"version": VERSION, "year": year, "built_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"), "observation_read": False, "cases": cases}, indent=1), encoding="utf-8")
    return {"year": year, **ledger}


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--years", required=True)
    p.add_argument("--workers", type=int, default=6)
    a = p.parse_args()
    years = list(range(int(a.years.split("-")[0]), int(a.years.split("-")[1]) + 1)) if "-" in a.years else [int(x) for x in a.years.split(",")]
    for year in years:
        print(json.dumps(build_year(year, a.workers)), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
