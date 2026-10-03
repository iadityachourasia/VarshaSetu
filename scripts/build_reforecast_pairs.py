"""Pair the forecast-side reforecast corpus with IMD observations, for the years the study protocol allows (docs/142).

Reads IMD for the requested years ONLY, and refuses a sealed year unless a valid unseal record exists (written by ``write_reforecast_unseal_record.py``). For every included case it keeps the cells with a valid
IMD value (the same 1,301-cell land footprint as the other corpora), writes the aligned rows and records counts. Nothing is fitted here.

    python scripts/build_reforecast_pairs.py --years 2000-2013

Output (untracked): data/processed/reforecast_control_v1/<year>/{X.npy, y_mm.npy, pixel_index.npy, regime_rows.npy, pairs.json}.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

import numpy as np
from scipy.io import netcdf_file

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

OUT = ROOT / "data/processed/reforecast_control_v1"
IMD = ROOT / "experiments/recent_historical/imd_climatology"
PROTOCOL = ROOT / "backend/app/evidence_data/phase15/reforecast_study_protocol_v1.json"
UNSEAL = ROOT / "backend/app/evidence_data/phase15/reforecast_unseal_record.json"
OFFSET = {"day1_24h": 1, "day2_24h": 2, "day3_24h": 3}
BOX = {"south": 10.0, "north": 22.0, "west": 68.0, "east": 80.0}


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def sealed_years() -> tuple[int, ...]:
    if not PROTOCOL.exists():
        raise SystemExit("the study protocol is not frozen yet: no observation may be read before it is")
    protocol = json.loads(PROTOCOL.read_text(encoding="utf-8"))
    return tuple(protocol["populations"]["sealed_test_years"])


def check_allowed(years: list[int]) -> None:
    protocol_sha = sha(PROTOCOL)
    if (PROTOCOL.with_suffix(".sha256")).read_text(encoding="ascii").split()[0] != protocol_sha:
        raise SystemExit("protocol differs from its sidecar")
    locked = [y for y in years if y in sealed_years()]
    if not locked:
        return
    if not UNSEAL.exists():
        raise SystemExit(f"years {locked} are sealed: no unseal record exists")
    record = json.loads(UNSEAL.read_text(encoding="utf-8"))
    if record.get("protocol_sha256") != protocol_sha or sorted(record.get("years", [])) != sorted(sealed_years()) or record.get("written_before_any_sealed_observation_was_read") is not True:
        raise SystemExit("the unseal record does not match the frozen protocol")


def imd_year(year: int):
    path = IMD / f"RF25_ind{year}_rfp25.nc"
    expected = json.loads((ROOT / "backend/app/evidence_data/phase6/regime_validation_protocol_v1.json").read_text(encoding="utf-8"))["criteria"]["climatology"]["file_sha256"][str(year)]
    if sha(path) != expected:
        raise SystemExit(f"IMD file hash mismatch: {path.name}")
    with netcdf_file(path, "r", mmap=False) as dataset:
        times = np.asarray(dataset.variables["TIME"].data, dtype=np.float64)
        origin = date.fromisoformat(dataset.variables["TIME"].units.decode().split("since ")[1].strip()[:10])
        lat = np.asarray(dataset.variables["LATITUDE"].data, dtype=np.float64)
        lon = np.asarray(dataset.variables["LONGITUDE"].data, dtype=np.float64)
        fill = float(dataset.variables["RAINFALL"]._attributes["_FillValue"])
        rain = np.asarray(dataset.variables["RAINFALL"].data, dtype=np.float64)
    lat_i, lon_i = np.flatnonzero((lat >= BOX["south"]) & (lat <= BOX["north"])), np.flatnonzero((lon >= BOX["west"]) & (lon <= BOX["east"]))
    if (len(lat_i), len(lon_i)) != (49, 49):
        raise SystemExit("IMD box is not 49 by 49")
    box = rain[:, lat_i[0]: lat_i[-1] + 1, lon_i[0]: lon_i[-1] + 1]
    days = {origin + timedelta(days=int(t)): i for i, t in enumerate(times)}
    return days, box, fill


def pair_year(year: int) -> dict:
    folder = OUT / str(year)
    cases = json.loads((folder / "cases.json").read_text(encoding="utf-8"))["cases"]
    x_full = np.load(folder / "X_full.npy", mmap_mode="r", allow_pickle=False)
    days, box, fill = imd_year(year)
    rows_x, rows_y, rows_pixel, rows_case, meta = [], [], [], [], []
    start, dropped = 0, {"no_valid_cell": 0, "no_obs_day": 0}
    for case in cases:
        if case["status"] != "INCLUDED":
            continue
        valid_day = date.fromisoformat(case["initialization"]) + timedelta(days=OFFSET[case["product"]])
        if valid_day not in days:
            dropped["no_obs_day"] += 1
            continue
        obs = box[days[valid_day]].ravel().copy()
        valid = np.isfinite(obs) & (obs != fill) & (obs >= 0)
        if not valid.any():
            dropped["no_valid_cell"] += 1
            continue
        cells = np.flatnonzero(valid)
        rows_x.append(np.asarray(x_full[case["row"]])[cells])
        rows_y.append(obs[cells])
        rows_pixel.append(cells.astype(np.int32))
        rows_case.append(np.full(len(cells), case["row"], dtype=np.int32))
        meta.append({"case_id": case["case_id"], "initialization": case["initialization"], "product": case["product"], "row": case["row"], "row_start": start, "row_count": int(len(cells)), "valid_observation_date": valid_day.isoformat()})
        start += len(cells)
    np.save(folder / "X.npy", np.concatenate(rows_x).astype(np.float32), allow_pickle=False)
    np.save(folder / "y_mm.npy", np.concatenate(rows_y), allow_pickle=False)
    np.save(folder / "pixel_index.npy", np.concatenate(rows_pixel), allow_pickle=False)
    np.save(folder / "regime_rows.npy", np.asarray([m["row"] for m in meta], dtype=np.int32), allow_pickle=False)
    (folder / "pairs.json").write_text(json.dumps({"year": year, "paired_at_utc": datetime.utcnow().isoformat(timespec="seconds") + "Z", "protocol_sha256": sha(PROTOCOL), "cases": meta, "dropped": dropped, "rows": start}, indent=1), encoding="utf-8")
    return {"year": year, "paired_cases": len(meta), "rows": start, "dropped": dropped}


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--years", required=True)
    a = p.parse_args()
    years = list(range(int(a.years.split("-")[0]), int(a.years.split("-")[1]) + 1)) if "-" in a.years else [int(x) for x in a.years.split(",")]
    check_allowed(years)
    for year in years:
        print(json.dumps(pair_year(year)), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
