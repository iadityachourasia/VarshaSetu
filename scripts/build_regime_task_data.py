"""Regime-detection task data for the reforecast years (docs/142, work package R03).

Stages (each is gated by the frozen study protocol; a sealed year needs a valid unseal record):

    python scripts/build_regime_task_data.py features --years 2000-2016    # forecast-only: regime features, forecast WD indicator, coastal forcing index per case; reads NO observation or reanalysis
    python scripts/build_regime_task_data.py labels   --years 2000-2013    # IMD (active, break, coastal rain) and ERA5 (western disturbance, low/depression) labels per day; thresholds from the training years only
    python scripts/build_regime_task_data.py assemble --years 2000-2013    # join features and labels at the valid day (initialization date + lead day)

Labels (all objective and rule-based, relative where stated; see backend/app/ml/regime_labels_reanalysis.py and regime_validation.py):
  ACTIVE / BREAK  IMD core-zone rainfall spells in July and August (1981-2011 climatology, one standard deviation, three days; the style of Rajeevan et al. 2010);
  LOW_DEPRESSION  ERA5 850 hPa geostrophic vorticity box maximum (15-25 N, 70-95 E) at or above the training 85th percentile on at least two consecutive days;
  WESTERN_DISTURBANCE  ERA5 500 hPa geostrophic vorticity box maximum (20-36.5 N, 60-80 E), same rule;
  COASTAL_OROGRAPHIC  IMD mean rainfall over the Ghats-coast zone cells at or above the training 85th percentile (June to September days).
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

from backend.app.ml import regime_labels_reanalysis as rl  # noqa: E402
from backend.app.ml import regime_validation as rv  # noqa: E402
from backend.app.ml import reforecast_study as rs  # noqa: E402

PROC = ROOT / "data/processed/reforecast_control_v1"
RAW = ROOT / "data/raw/forecasts/gefsv12_control_v1"
ERA5 = ROOT / "data/raw/era5_wb2_1p5_geopotential_v1"
IMD = ROOT / "experiments/recent_historical/imd_climatology"
TASKS = ROOT / "data/processed/regime_tasks_v1"
PROTOCOL = ROOT / "backend/app/evidence_data/phase15/reforecast_study_protocol_v1.json"
UNSEAL = ROOT / "backend/app/evidence_data/phase15/reforecast_unseal_record.json"
CLIM_YEARS = tuple(range(1981, 2012))
TASK_NAMES = ("ACTIVE", "BREAK", "LOW_DEPRESSION", "WESTERN_DISTURBANCE", "COASTAL_OROGRAPHIC")
FEATURES = tuple(rs.REGIME_FEATURES) + ("wd_indicator", "coastal_forcing_index", "lead_hours", "doy_sin", "doy_cos")
ZONE = "COASTAL_AND_OROGRAPHIC"
LEAD_HOURS = {"day1_24h": 24, "day2_24h": 48, "day3_24h": 72}
ORIGIN = date(1959, 1, 1)


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def protocol() -> dict:
    if not PROTOCOL.exists():
        raise SystemExit("the study protocol is not frozen yet")
    if PROTOCOL.with_suffix(".sha256").read_text(encoding="ascii").split()[0] != sha(PROTOCOL):
        raise SystemExit("protocol differs from its sidecar")
    return json.loads(PROTOCOL.read_text(encoding="utf-8"))


def gate(years: list[int], reads_outcomes: bool) -> None:
    p = protocol()
    locked = [y for y in years if y in p["populations"]["sealed_test_years"]]
    if locked and reads_outcomes:
        record = json.loads(UNSEAL.read_text(encoding="utf-8")) if UNSEAL.exists() else None
        if not record or record["protocol_sha256"] != sha(PROTOCOL) or record.get("written_before_any_sealed_observation_was_read") is not True:
            raise SystemExit(f"years {locked} are sealed: no valid unseal record")


def parse_years(text: str) -> list[int]:
    return list(range(int(text.split("-")[0]), int(text.split("-")[1]) + 1)) if "-" in text else [int(x) for x in text.split(",")]


def geography() -> tuple[dict, np.ndarray]:
    data = json.loads((ROOT / "backend/app/evidence_data/phase7/static_geography_v1.json").read_text(encoding="utf-8"))
    fields = {k: np.array([[np.nan if v is None else v for v in row] for row in data["fields"][k]], dtype=np.float64).ravel() for k in ("coast_landward_east", "coast_landward_north", "terrain_uphill_east", "terrain_uphill_north")}
    zone = np.array([z == ZONE for row in data["fields"]["zone"] for z in row])
    return fields, zone


# ------------------------------------------------------------------ features (forecast only)
def wd_indicator(stamp: str, lead: int) -> float:
    from backend.app.data_sources.noaa_gefs_monthly import ATMOSPHERIC_SPECS, crop_grid, decode_atmospheric_message
    from backend.app.ml.wd_indicator import index_from_z500
    folder = RAW / stamp[:4] / stamp
    receipts = {(r["variable"], r["lead"]): r for r in json.loads((folder / "COMPLETE.json").read_text(encoding="utf-8"))["receipts"] if r["variable"] != "rain"}
    r = receipts[("z500", lead)]
    payload = (folder / r["file"]).read_bytes()
    if hashlib.sha256(payload).hexdigest() != r["sha256"]:
        return float("nan")
    grid = decode_atmospheric_message(payload, member="c00", description=r["index_line"], spec=ATMOSPHERIC_SPECS["z500"], lead_hour=lead)
    region = crop_grid(grid, south=20.0, north=43.0, west=57.0, east=83.0)
    return float(index_from_z500(region.values, region.latitude, region.longitude))


def features_for_year(year: int) -> dict:
    from backend.app.ml.coastal_regime import zone_index
    from backend.app.ml.zone_verification import forcing_fields
    geometry, zone = geography()
    folder = PROC / str(year)
    cases = json.loads((folder / "cases.json").read_text(encoding="utf-8"))["cases"]
    x_full = np.load(folder / "X_full.npy", mmap_mode="r", allow_pickle=False)
    regime = np.load(folder / "regime_X.npy", allow_pickle=False)
    rows, meta = [], []
    for c in cases:
        if c["status"] != "INCLUDED":
            continue
        x = np.asarray(x_full[c["row"]], dtype=np.float64)
        forcing = forcing_fields(x[:, 1], x[:, 2], x[:, 6], geometry)["cross_barrier"]
        stamp = c["initialization"].replace("-", "") + "00"
        lead = LEAD_HOURS[c["product"]]
        valid = date.fromisoformat(c["initialization"]) + timedelta(days=lead // 24)
        doy = valid.timetuple().tm_yday
        rows.append(np.concatenate([regime[c["row"]], [wd_indicator(stamp, lead), zone_index(forcing, zone), lead, np.sin(2 * np.pi * doy / 365.25), np.cos(2 * np.pi * doy / 365.25)]]))
        meta.append({"case_id": c["case_id"], "initialization": c["initialization"], "product": c["product"], "valid_date": valid.isoformat()})
    TASKS.mkdir(parents=True, exist_ok=True)
    np.save(TASKS / f"features_{year}.npy", np.array(rows, dtype=np.float64), allow_pickle=False)
    (TASKS / f"features_{year}.json").write_text(json.dumps({"year": year, "feature_names": list(FEATURES), "cases": meta, "observation_read": False}, indent=1), encoding="utf-8")
    return {"year": year, "cases": len(meta), "undefined_wd": int(np.isnan(np.array(rows)[:, 12]).sum())}


# ------------------------------------------------------------------ labels
def imd_year(year: int):
    path = IMD / f"RF25_ind{year}_rfp25.nc"
    expected = json.loads((ROOT / "backend/app/evidence_data/phase6/regime_validation_protocol_v1.json").read_text(encoding="utf-8"))["criteria"]["climatology"]["file_sha256"][str(year)]
    if sha(path) != expected:
        raise SystemExit(f"IMD hash mismatch {path.name}")
    with netcdf_file(path, "r", mmap=False) as ds:
        times = np.asarray(ds.variables["TIME"].data, dtype=np.float64)
        lat, lon = np.asarray(ds.variables["LATITUDE"].data, dtype=np.float64), np.asarray(ds.variables["LONGITUDE"].data, dtype=np.float64)
        rain = np.asarray(ds.variables["RAINFALL"].data, dtype=np.float64)
        fill = float(ds.variables["RAINFALL"]._attributes["_FillValue"])
    rain[(rain == fill) | ~np.isfinite(rain)] = np.nan
    return rv.dates_of(times), lat, lon, rain


def zone_series(days, lat, lon, rain, zone_flat) -> dict[date, float]:
    li, lj = np.flatnonzero((lat >= 10) & (lat <= 22)), np.flatnonzero((lon >= 68) & (lon <= 80))
    box = rain[:, li[0]: li[-1] + 1, lj[0]: lj[-1] + 1].reshape(len(days), -1)
    sel = box[:, zone_flat]
    out = {}
    for d, row in zip(days, sel):
        vals = row[np.isfinite(row)]
        if vals.size >= 20:
            out[d] = float(vals.mean())
    return out


def era5_daily_maxima(year: int) -> dict[str, np.ndarray]:
    """Daily maxima of 500 hPa (WD box) and 850 hPa (monsoon-low box) geostrophic vorticity for 1 June to 3 October (NaN for a day with any missing time)."""
    meta = ERA5 / "meta"
    from numcodecs import Blosc
    zarray = json.loads((meta / "latitude__.zarray").read_text(encoding="utf-8"))
    codec = Blosc()
    lat = np.frombuffer(codec.decode((meta / "latitude__0").read_bytes()), dtype=zarray["dtype"]).astype(np.float64)
    zlon = json.loads((meta / "longitude__.zarray").read_text(encoding="utf-8"))
    lon = np.frombuffer(codec.decode((meta / "longitude__0").read_bytes()), dtype=zlon["dtype"]).astype(np.float64)
    first = (date(year, 6, 1) - ORIGIN).days * 4
    last = (date(year, 10, 3) - ORIGIN).days * 4 + 3
    n_days = (date(year, 10, 3) - date(year, 6, 1)).days + 1
    wd, lps = np.full(n_days * 4, np.nan), np.full(n_days * 4, np.nan)
    for chunk in range(first // 8, last // 8 + 1):
        data = rl.decode_chunk((ERA5 / "geopotential" / f"{chunk}.0.0.0").read_bytes())
        for k in range(8):
            step = chunk * 8 + k
            if first <= step <= last:
                i = step - first
                field = data[k:k + 1]
                wd[i] = rl.box_maximum(rl.level_vorticity(field, rl.LEVELS_HPA.index(500), lat, lon), lat, lon, rl.WD_BOX)[0]
                lps[i] = rl.box_maximum(rl.level_vorticity(field, rl.LEVELS_HPA.index(850), lat, lon), lat, lon, rl.LPS_BOX)[0]
    return {"wd": rl.daily_maximum(wd), "lps": rl.daily_maximum(lps)}


def thresholds_path() -> Path:
    return TASKS / "label_thresholds.json"


def compute_thresholds(train_years: tuple[int, ...]) -> dict:
    zone = geography()[1]
    mean_series, sigma, info = None, None, None
    per_year = {}
    for y in CLIM_YEARS:
        days, lat, lon, rain = imd_year(y)
        per_year[y] = rv.season_series(rv.area_mean_series(rain, lat, lon), days)
    mean_series, sigma, info = rv.climatology(per_year)
    wd_all, lps_all, zone_all = [], [], []
    for y in train_years:
        e = era5_daily_maxima(y)
        keep = slice(0, 122)                                  # 1 June to 30 September
        wd_all.append(e["wd"][keep]); lps_all.append(e["lps"][keep])
        days, lat, lon, rain = imd_year(y)
        zs = zone_series(days, lat, lon, rain, zone)
        zone_all.append([zs[d] for d in (date(y, 6, 1) + timedelta(days=i) for i in range(122)) if d in zs])
    th = {"climatology_years": [CLIM_YEARS[0], CLIM_YEARS[-1]], "climatology_sigma_mm_per_day": sigma, "climatology_mean_mm_per_day": mean_series.tolist(),
          "wd_threshold": rl.percentile_threshold(np.concatenate(wd_all)), "lps_threshold": rl.percentile_threshold(np.concatenate(lps_all)),
          "coastal_threshold": float(np.quantile(np.concatenate(zone_all), rl.PERCENTILE)), "percentile": rl.PERCENTILE, "training_years": list(train_years),
          "persistence_days": rl.MIN_DAYS, "built_from": "training years and the 1981-2011 climatology only: no validation or sealed observation"}
    return th


def labels_for_year(year: int, th: dict) -> dict:
    zone = geography()[1]
    days, lat, lon, rain = imd_year(year)
    series = rv.season_series(rv.area_mean_series(rain, lat, lon), days)
    z = rv.normalised_anomaly(series, np.array(th["climatology_mean_mm_per_day"]), th["climatology_sigma_mm_per_day"])
    am = rv.label_days(z, year)
    zs = zone_series(days, lat, lon, rain, zone)
    e = era5_daily_maxima(year)
    wd_flag, lps_flag = rl.persistent_days(e["wd"], th["wd_threshold"]), rl.persistent_days(e["lps"], th["lps_threshold"])
    out = {}
    for i in range((date(year, 10, 3) - date(year, 6, 1)).days + 1):
        d = date(year, 6, 1) + timedelta(days=i)
        out[d.isoformat()] = {"ACTIVE": None if d not in am else am[d] == "ACTIVE", "BREAK": None if d not in am else am[d] == "BREAK",
                              "LOW_DEPRESSION": bool(lps_flag[i]) if np.isfinite(e["lps"][i]) else None, "WESTERN_DISTURBANCE": bool(wd_flag[i]) if np.isfinite(e["wd"][i]) else None,
                              "COASTAL_OROGRAPHIC": (zs[d] >= th["coastal_threshold"]) if d in zs else None, "wd_daily_max": None if not np.isfinite(e["wd"][i]) else float(e["wd"][i]),
                              "lps_daily_max": None if not np.isfinite(e["lps"][i]) else float(e["lps"][i]), "zone_mean_mm": zs.get(d)}
    return out


def assemble_year(year: int) -> dict:
    meta = json.loads((TASKS / f"features_{year}.json").read_text(encoding="utf-8"))
    F = np.load(TASKS / f"features_{year}.npy", allow_pickle=False)
    labels = json.loads((TASKS / f"labels_{year}.json").read_text(encoding="utf-8"))["days"]
    Y = np.full((len(meta["cases"]), len(TASK_NAMES)), -1, dtype=np.int8)
    for i, c in enumerate(meta["cases"]):
        day = labels.get(c["valid_date"])
        if day:
            for j, name in enumerate(TASK_NAMES):
                if day[name] is not None:
                    Y[i, j] = int(day[name])
    np.save(TASKS / f"tasks_Y_{year}.npy", Y, allow_pickle=False)
    return {"year": year, "cases": len(Y), "positives": {n: int((Y[:, j] == 1).sum()) for j, n in enumerate(TASK_NAMES)}, "defined": {n: int((Y[:, j] >= 0).sum()) for j, n in enumerate(TASK_NAMES)}}


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("stage", choices=("features", "labels", "assemble"))
    p.add_argument("--years", required=True)
    a = p.parse_args()
    years = parse_years(a.years)
    proto = protocol()
    gate(years, reads_outcomes=a.stage != "features")
    if a.stage == "features":
        for y in years:
            print(json.dumps(features_for_year(y)), flush=True)
        return 0
    TASKS.mkdir(parents=True, exist_ok=True)
    tp = thresholds_path()
    if tp.exists():
        th = json.loads(tp.read_text(encoding="utf-8"))
    else:
        th = compute_thresholds(tuple(proto["populations"]["train_years"]))
        tp.write_text(json.dumps(th, indent=1), encoding="utf-8")
    if a.stage == "labels":
        for y in years:
            (TASKS / f"labels_{y}.json").write_text(json.dumps({"year": y, "thresholds_sha256": sha(tp), "days": labels_for_year(y, th)}), encoding="utf-8")
            print(json.dumps({"year": y, "labelled": True}), flush=True)
        return 0
    for y in years:
        print(json.dumps(assemble_year(y)), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
