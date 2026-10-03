"""Raw GEFS verification over the whole IMD grid (protocol v1, docs/140). Two stages, write-once.

    python scripts/build_all_india_raw.py freeze   # stored GEFS control rainfall only (no new download, no observation): the all-India 24 h rainfall of every case that passed the regional quality control
    python scripts/build_all_india_raw.py score    # verifies the frozen protocol and ledger hashes, then compares the Raw forecast with IMD by region

Nothing is fitted, tuned or applied: only the unmodified control-member rainfall is compared with IMD, so the result says how large the Raw errors are outside the regional modelling domain and nothing about
any correction there. 2023 is the training year of the downstream models (this analysis fits nothing), 2024 a reused development year, 2025 a consumed holdout (post-hoc). IMD files stay local; only
aggregate counts and scores are written.
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
from concurrent.futures import ProcessPoolExecutor
from datetime import date, timedelta
from pathlib import Path

import numpy as np
from scipy.io import netcdf_file

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.app.ml import all_india_raw as air  # noqa: E402

OUT = ROOT / "backend/app/evidence_data/phase14"
PROTOCOL, LEDGER = OUT / "all_india_raw_protocol_v1.json", OUT / "all_india_raw_ledger_v1.json"
CACHE = ROOT / "data/operational_derived/all_india_raw_v1"
EXP = ROOT / "experiments/recent_historical"
P4F = EXP / "phase4f_payload_acquisition_v1"
PRODUCTS = {"day1_24h": {"rain_hours": (3, 6, 12, 18, 24, 27), "window": (3, 27), "offset": 1}, "day2_24h": {"rain_hours": (27, 30, 36, 42, 48, 51), "window": (27, 51), "offset": 2},
            "day3_24h": {"rain_hours": (51, 54, 60, 66, 72, 75), "window": (51, 75), "offset": 3}}
YEARS = {
    2023: {"role": "training_year_of_downstream_models", "imd": EXP / "imd/RF25_ind2023_rfp25.nc", "evidence_role": "ALLINDIA_2023_TRAINING_YEAR_OF_THE_DOWNSTREAM_MODELS_RAW_ONLY",
           "label": "2023: training year of the downstream models (this analysis fits nothing; Raw only)", "development": False},
    2024: {"role": "development", "imd": EXP / "imd/RF25_ind2024_rfp25.nc", "evidence_role": "ALLINDIA_2024_DEVELOPMENT_YEAR_REUSED_FOR_MODEL_SELECTION",
           "label": "2024 validation/selection year: development evidence", "development": True},
    2025: {"role": "post_hoc", "imd": EXP / "imd/RF25_ind2025_rfp25.nc", "evidence_role": "ALLINDIA_2025_CONSUMED_FINAL_TEST__POST_HOC_EXPLORATORY_ANALYSIS_OF_THE_COMPLETED_2025_FINAL_TEST",
           "label": "POST-HOC EXPLORATORY ANALYSIS OF THE COMPLETED 2025 FINAL TEST", "development": False},
}
IMD_SHA = {2023: "1fa0cbcb56769fd3cd2702e36dc3ee1b81b74755b77c7f058c70dfc3afb82831", 2024: "1ef02aeba5694dbb57a6cca23a3c2cc11740affb185137c1eacbeab59893228a",
           2025: "7d03cd397ebb1d7209ffae947d3965113643e1f30023cca657f0aa2c800af035"}


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def clean(value):
    if isinstance(value, dict):
        return {str(k) if not isinstance(k, str) else k: clean(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [clean(v) for v in value]
    if isinstance(value, (np.floating, float)):
        return None if not np.isfinite(value) else float(value)
    if isinstance(value, np.integer):
        return int(value)
    if isinstance(value, np.bool_):
        return bool(value)
    return value


def encode(value) -> bytes:
    return (json.dumps(clean(value), sort_keys=True, indent=2, ensure_ascii=False, allow_nan=False) + "\n").encode("utf-8")


def write_once(path: Path, data: bytes) -> str:
    if path.exists() and path.read_bytes() != data:
        raise RuntimeError(f"frozen evidence would change: {path}")
    path.write_bytes(data)
    return hashlib.sha256(data).hexdigest()


def process_date(day: str) -> dict:
    """Worker: decode the 16 stored control rainfall messages of one date over the IMD domain and reconstruct each regionally eligible lead. Imports are local so each process loads eccodes itself."""
    from backend.app.data.accumulation import GriddedAccumulationMessage, reconstruct_minimal_accumulation_window
    from backend.app.data_sources.noaa_gefs_monthly import crop_grid, decode_precipitation_message
    from backend.app.live.pipeline import CycleRefused, RAIN_HOURS, _grib_extra, validate_message
    from backend.app.live.stored import StoredSource

    year = int(day[:4])
    checkpoint = json.loads((P4F / "checkpoints" / str(year) / f"{day}.json").read_text(encoding="utf-8"))
    eligible = {c["product"]: bool(c["C00_RAINFALL_QC_PASS"]) for c in checkpoint["cases"]}
    rows = {p: {"case_id": f"{day}_{p}", "initialization": f"{day[:4]}-{day[4:6]}-{day[6:]}", "product": p, "regional_qc_pass": eligible[p], "status": None, "reason": None, "sha256": None, "path": None} for p in PRODUCTS}
    if not any(eligible.values()):
        for r in rows.values():
            r["status"], r["reason"] = "EXCLUDED_REGIONAL_QC", "the regional canonical rainfall reconstruction failed for this lead in the study corpus"
        return {"day": day, "rows": list(rows.values()), "lat": None, "lon": None}
    source, messages, lat, lon = StoredSource(day), {}, None, None
    try:
        for hour in RAIN_HOURS:
            message = source.get("pgrb2sp25", hour, "rain")
            accumulation, grid = decode_precipitation_message(message.payload, member="c00", description=message.description, source_id=message.sha256)
            validate_message(message, day, grid.metadata, _grib_extra(message.payload))
            region = crop_grid(grid, **air.IMD_BOUNDS)
            if not np.isfinite(region.values).all():
                raise CycleRefused(f"rain f{hour:03d}: non-finite values in the all-India crop")
            lat, lon = region.latitude, region.longitude
            messages[hour] = GriddedAccumulationMessage(accumulation.start_hour, accumulation.end_hour, region.values, accumulation.source_id, accumulation.packing_quantum_mm)
    except Exception as error:
        for p, r in rows.items():
            r["status"], r["reason"] = "EXCLUDED_DECODE", f"{type(error).__name__}: {error}"
        return {"day": day, "rows": list(rows.values()), "lat": None, "lon": None}
    for product, lead in PRODUCTS.items():
        r = rows[product]
        if not eligible[product]:
            r["status"], r["reason"] = "EXCLUDED_REGIONAL_QC", "the regional canonical rainfall reconstruction failed for this lead in the study corpus"
            continue
        try:
            result = reconstruct_minimal_accumulation_window([messages[h] for h in lead["rain_hours"]], window_start_hour=lead["window"][0], window_end_hour=lead["window"][1])
            field = np.asarray(result.rainfall_mm, dtype=np.float64)
            if field.shape != (len(lat), len(lon)) or not np.isfinite(field).all() or np.any(field < 0):
                raise ValueError("reconstructed field is not finite, non-negative and on the IMD grid")
        except Exception as error:
            r["status"], r["reason"] = "EXCLUDED_WIDE_RECONSTRUCTION", f"{type(error).__name__}: {error}"
            continue
        inner = field[np.ix_((lat >= 10) & (lat <= 22), (lon >= 68) & (lon <= 80))]
        stored = np.load(P4F / "rainfall_qc" / str(year) / day / f"{product}_c00.npy", allow_pickle=False)
        if not np.array_equal(inner, stored):
            r["status"], r["reason"] = "EXCLUDED_BOX_MISMATCH", "the all-India field restricted to the regional box differs from the stored regional field"
            continue
        path = CACHE / str(year) / f"{day}_{product}.npy"
        path.parent.mkdir(parents=True, exist_ok=True)
        np.save(path, field, allow_pickle=False)
        r["status"], r["sha256"], r["path"] = "INCLUDED", sha(path), path.relative_to(ROOT).as_posix()
    return {"day": day, "rows": list(rows.values()), "lat": lat.tolist() if lat is not None else None, "lon": lon.tolist() if lon is not None else None}


def season_days(year: int) -> list[str]:
    d, out = date(year, 6, 1), []
    while d <= date(year, 10, 3):
        if (P4F / "checkpoints" / str(year) / f"{d.strftime('%Y%m%d')}.json").is_file():
            out.append(d.strftime("%Y%m%d"))
        d += timedelta(days=1)
    return out


def freeze() -> None:
    if PROTOCOL.exists():
        raise SystemExit("all-India Raw protocol v1 already frozen; a change needs a new version")
    OUT.mkdir(parents=True, exist_ok=True)
    workers = min(8, max(1, (os.cpu_count() or 4) // 2))          # process-based, bounded: leaves headroom for the desktop (AGENTS.md section 13)
    ledger, coordinates = {}, None
    for year in YEARS:
        days = season_days(year)
        with ProcessPoolExecutor(max_workers=workers) as pool:
            results = list(pool.map(process_date, days, chunksize=4))
        rows = []
        for item in results:
            rows += item["rows"]
            if item["lat"] is not None:
                if coordinates is None:
                    coordinates = {"lat": item["lat"], "lon": item["lon"]}
                elif coordinates != {"lat": item["lat"], "lon": item["lon"]}:
                    raise SystemExit("the all-India crop differs between dates")
        ledger[str(year)] = rows
        counts = {}
        for r in rows:
            counts[r["status"]] = counts.get(r["status"], 0) + 1
        print(year, len(days), "dates", counts, flush=True)
    lat, lon = np.array(coordinates["lat"]), np.array(coordinates["lon"])
    masks = air.region_masks(lat, lon)
    ledger_digest = write_once(LEDGER, encode({"schema": "all-india-raw-ledger-v1", "note": "stored control-member rainfall only; no observation was read", "grid": {"latitude": coordinates["lat"], "longitude": coordinates["lon"]}, "populations": ledger}))
    protocol = {
        "schema": "all-india-raw-protocol-v1", "status": "APPROVED_FOR_EXECUTION", "no_observation_read": True,
        "purpose": ("Describe how large the errors of the unmodified (Raw) GEFS control rainfall are over the whole IMD grid, by region, BEFORE any observation is compared. "
                    "Nothing is fitted or corrected: this says nothing about post-processing outside the regional modelling domain."),
        "definition": {"forecast": "the stored control-member (c00) GEFS 24 h rainfall, cropped to the IMD land grid, reconstructed with the canonical accumulation rule; only leads that passed the regional canonical reconstruction in the study corpus are used",
                       "observation": "IMD RF25 daily rainfall on the day initialization date + lead day (valid cells only; fill values excluded, never zero-filled)", "grid": "IMD 0.25 degree grid, 6.5 to 38.5 N, 66.5 to 100 E (129 by 135), the same grid points as GEFS",
                       "regions": {"order": "first match wins", "INSIDE_MODEL_DOMAIN": "10 to 22 N and 68 to 80 E (the regional modelling box)", "NORTH_OF_DOMAIN": "north of 22 N and at or west of 88 E",
                                   "EAST_AND_NORTH_EAST": "east of 88 E", "EAST_COAST_PENINSULA": "at or south of 22 N and east of 80 E up to 88 E", "SOUTH_OF_DOMAIN": "south of 10 N and at or west of 80 E",
                                   "cell_counts": {name: int(masks[name].sum()) for name in air.REGIONS}, "all_scored_cells": int(masks["ALL"].sum()),
                                   "note": "a fixed latitude-longitude rule, a description of where the forecast is checked and not a meteorological regime"},
                       "thresholds_mm_per_24h": {"heavy": 64.5, "very_heavy": 115.6}, "ledger_file_sha256": ledger_digest, "imd_files_sha256": {str(y): IMD_SHA[y] for y in YEARS}},
        "populations": {str(y): {"year": y, "role": YEARS[y]["role"], "evidence_role": YEARS[y]["evidence_role"], "label": YEARS[y]["label"],
                                 "forecast_only_status_counts": {s: sum(1 for r in ledger[str(y)] if r["status"] == s) for s in sorted({r["status"] for r in ledger[str(y)]})}} for y in YEARS},
        "evaluation": {"statistics": ["RMSE, bias and MAE of Raw against IMD per region", "heavy and very-heavy POD, FAR, CSI, ETS and frequency bias per region",
                                      "the same by lead day", "95 percent bootstrap intervals (whole initialization dates, 2000 resamples, seed 26080) for RMSE, bias and the CSIs"],
                       "support_gate": {"min_cells": air.MIN_CELLS, "min_cases": air.MIN_CASES, "min_observed_event_pairs": air.MIN_EVENT_PAIRS, "otherwise": "insufficient_support, no number"},
                       "uncertainty_note": "optimistic: consecutive dates are correlated"},
        "decision_rule": "none: the analysis is descriptive. No region is declared better or worse than another by a rule; the numbers are reported with their support and the consumed years carry their labels.",
        "not_established_whatever_the_result": ["any skill or error of a corrected forecast outside the 10 to 22 N and 68 to 80 E box (no model was applied there)", "that the errors are caused by a regime or by geography",
                                                "behaviour of a post-processing model if one were trained for these regions", "Raw behaviour outside June to early October"],
        "forbidden": ["applying or training any model on the all-India fields", "changing the regions, thresholds or gate after any observation is compared", "describing the 2023 row as independent evidence for any model",
                      "reading an IMD cell of a case excluded in the ledger"],
        "reproduction_gate": ["every included all-India field restricted to the regional box equals the stored regional QC field exactly (checked at freeze)", "region cell counts equal the frozen counts",
                              "region statistics add up to the all-India statistics", "where no case was excluded by the wider reconstruction, the INSIDE_MODEL_DOMAIN Raw statistics equal the Stage 1 evidence exactly"],
        "approval": {"approved_by": "project owner", "record": "owner instruction of 2026-10-03: 'make a full plan to implement everything left partial or not completely and implement'; work package WP-D(2) of docs/134",
                     "note": "Interpretation of a general instruction (Raw only, no model applied outside the regional domain, no new download); the owner may withdraw it."}}
    PROTOCOL.write_text(json.dumps(clean(protocol), indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    (OUT / "all_india_raw_protocol_v1.sha256").write_text(sha(PROTOCOL) + "  all_india_raw_protocol_v1.json\n", encoding="ascii")
    print("protocol sha256", sha(PROTOCOL))


def imd_year(year: int):
    path = YEARS[year]["imd"]
    if sha(path) != IMD_SHA[year]:
        raise SystemExit(f"IMD file hash mismatch: {path.name}")
    with netcdf_file(path, "r", mmap=False) as dataset:
        times = np.asarray(dataset.variables["TIME"].data, dtype=np.float64)
        origin = date.fromisoformat(dataset.variables["TIME"].units.decode().split("since ")[1].strip()[:10])
        lat = np.asarray(dataset.variables["LATITUDE"].data, dtype=np.float64)
        lon = np.asarray(dataset.variables["LONGITUDE"].data, dtype=np.float64)
        fill = float(dataset.variables["RAINFALL"]._attributes["_FillValue"])
        rain = np.asarray(dataset.variables["RAINFALL"].data, dtype=np.float64)
    lat_i, lon_i = np.flatnonzero((lat >= 6.5) & (lat <= 38.5)), np.flatnonzero((lon >= 66.5) & (lon <= 100.0))
    days = {origin + timedelta(days=int(t)): i for i, t in enumerate(times)}
    return days, lat[lat_i], lon[lon_i], rain[:, lat_i[0]: lat_i[-1] + 1, lon_i[0]: lon_i[-1] + 1], fill


def score() -> None:
    if (OUT / "all_india_raw_protocol_v1.sha256").read_text(encoding="ascii").split()[0] != sha(PROTOCOL):
        raise SystemExit("protocol differs from its sidecar: refusing to run")
    protocol = json.loads(PROTOCOL.read_text(encoding="utf-8"))
    if sha(LEDGER) != protocol["definition"]["ledger_file_sha256"]:
        raise SystemExit("the frozen ledger differs from the protocol")
    ledger = json.loads(LEDGER.read_text(encoding="utf-8"))
    lat, lon = np.array(ledger["grid"]["latitude"]), np.array(ledger["grid"]["longitude"])
    masks = air.region_masks(lat, lon)
    counts = {name: int(masks[name].sum()) for name in air.REGIONS}
    if counts != protocol["definition"]["regions"]["cell_counts"]:
        raise SystemExit("region cell counts differ from the frozen counts")
    cell_counts = {"ALL_INDIA": int(masks["ALL"].sum()), **counts}
    files = {}
    for year in YEARS:
        days, ilat, ilon, rain, fill = imd_year(year)
        if not (np.array_equal(ilat, lat) and np.array_equal(ilon, lon)):
            raise SystemExit("IMD grid differs from the frozen all-India grid")
        included = [r for r in ledger["populations"][str(year)] if r["status"] == "INCLUDED"]
        rows, per_date, per_product, unscored, valid_obs_cells = [], {}, {p: [] for p in PRODUCTS}, 0, 0
        ever_valid = np.zeros(lat.size * lon.size, dtype=bool)
        for r in included:
            d0 = date.fromisoformat(r["initialization"])
            valid_day = d0 + timedelta(days=PRODUCTS[r["product"]]["offset"])
            if valid_day not in days:
                continue
            path = ROOT / r["path"]
            if sha(path) != r["sha256"]:
                raise SystemExit(f"cached field differs from the ledger: {path.name}")
            field = np.load(path, allow_pickle=False).ravel()
            obs = rain[days[valid_day]].ravel().copy()
            obs[(obs == fill) | ~np.isfinite(obs)] = np.nan
            valid_obs_cells += int(np.isfinite(obs).sum())
            ever_valid |= np.isfinite(obs)
            unscored += air.unscored_cells(obs, masks)
            stats = air.case_stats(obs, np.where(np.isfinite(obs), field, np.nan), masks)
            rows.append(r)
            per_date.setdefault(r["initialization"], np.zeros_like(stats))
            per_date[r["initialization"]] += stats
            per_product[r["product"]].append(stats)
        stack_cases = np.stack([stats for p in per_product.values() for stats in p]) if rows else None
        if stack_cases is None:
            raise SystemExit(f"{year}: no scorable case")
        dates = sorted(per_date)
        date_stack = np.stack([per_date[d] for d in dates])
        totals = stack_cases.sum(axis=0)
        if not np.allclose(totals[1:].sum(axis=0), totals[0]):
            raise SystemExit("reproduction gate failed: region statistics do not add up to the all-India statistics")
        land = {"ALL_INDIA": int((ever_valid & masks["ALL"]).sum()), **{n: int((ever_valid & masks[n]).sum()) for n in air.REGIONS}}
        gate = air.support(stack_cases, land)
        metrics = air.region_metrics(totals)
        by_lead = {p: air.region_metrics(np.stack(v).sum(axis=0)) for p, v in per_product.items() if v}
        boot = air.bootstrap(date_stack)
        out_metrics, out_boot, out_lead = {}, {}, {}
        for name in air.NAMES:
            g = gate[name]
            block = {"cell_count": metrics[name]["cell_count"], "cases": g["cases"], "continuous_supported": g["continuous_supported"]}
            if g["continuous_supported"]:
                block.update({k: metrics[name][k] for k in ("rmse_mm", "mae_mm", "bias_mm")})
            block["categorical"] = {t: (metrics[name]["categorical"][t] if g[t]["supported"] else {"status": "insufficient_support", "observed_event_pairs": g[t]["observed_event_pairs"]}) for t in ("heavy", "very_heavy")}
            out_metrics[name] = block
            out_boot[name] = {m: boot[(name, m)] for m in air.METRICS if ((m in ("rmse", "bias", "mae") and g["continuous_supported"]) or (m.startswith("heavy") and g["heavy"]["supported"]) or (m.startswith("very_heavy") and g["very_heavy"]["supported"]))}
            out_lead[name] = {p: {"rmse_mm": by_lead[p][name]["rmse_mm"], "bias_mm": by_lead[p][name]["bias_mm"], "cell_count": by_lead[p][name]["cell_count"]} for p in by_lead if g["continuous_supported"]}
        reproduction = {"status": "REPRODUCED", "checks": ["every included all-India field restricted to the regional box equals the stored regional QC field exactly (checked at freeze)", "region cell counts equal the frozen counts", "region statistics add up to the all-India statistics"]}
        excluded = {s: sum(1 for r in ledger["populations"][str(year)] if r["status"] == s) for s in sorted({r["status"] for r in ledger["populations"][str(year)]}) if s != "INCLUDED"}
        stage1 = ROOT / f"backend/app/evidence_data/phase7/zone_verification_B_{year}.json"
        if stage1.is_file() and not any(s in excluded for s in ("EXCLUDED_WIDE_RECONSTRUCTION", "EXCLUDED_BOX_MISMATCH", "EXCLUDED_DECODE")):
            ref = json.loads(stage1.read_text(encoding="utf-8"))["pooled"]["ALL"]["M0"]
            mine = metrics["INSIDE_MODEL_DOMAIN"]
            match = (ref["rmse_mm"] == mine["rmse_mm"] and ref["bias_mm"] == mine["bias_mm"] and ref["categorical"]["heavy"]["hits"] == mine["categorical"]["heavy"]["hits"])
            reproduction["stage1_comparison"] = {"compared": True, "inside_domain_raw_equals_stage1": bool(match)}
            if not match:
                raise SystemExit(f"{year}: reproduction gate failed: INSIDE_MODEL_DOMAIN Raw statistics differ from the Stage 1 evidence")
            reproduction["checks"].append("INSIDE_MODEL_DOMAIN Raw statistics equal the Stage 1 evidence exactly")
        else:
            reproduction["stage1_comparison"] = {"compared": False, "reason": "no Stage 1 evidence for this year, or cases were excluded by the wider reconstruction so the populations differ"}
        result = {"schema": "all-india-raw-evidence-v1", "year": year, "evidence_role": YEARS[year]["evidence_role"], "label": YEARS[year]["label"], "development": YEARS[year]["development"],
                  "protocol_sha256": sha(PROTOCOL), "cases_scored": len(rows), "initialization_dates": len(dates), "excluded_cases": excluded, "valid_observation_cells": valid_obs_cells, "paired_cells_outside_every_region": unscored,
                  "region_grid_points": cell_counts, "region_cells_with_observation": land, "support": gate, "metrics": out_metrics, "bootstrap": {"repeats": 2000, "seed": 26080, "unit": "initialization date", "intervals": out_boot},
                  "by_lead": out_lead, "reproduction": reproduction,
                  "forecast_nature": "the unmodified control-member Raw GEFS rainfall; no model was applied; descriptive only"}
        name = f"all_india_raw_{year}.json"
        files[name] = {"sha256": write_once(OUT / name, encode(result)), "year": year, "evidence_role": YEARS[year]["evidence_role"], "development": YEARS[year]["development"]}
        print(year, len(rows), "cases;", {n: (out_metrics[n].get("rmse_mm"), out_metrics[n].get("bias_mm")) for n in air.NAMES}, flush=True)
    manifest = {"schema": "all-india-raw-manifest-v1", "protocol_sha256": sha(PROTOCOL), "ledger_file_sha256": sha(LEDGER), "files": files,
                "notes": ["Raw control-member rainfall only; no model was applied anywhere.", "2023 is the training year of the downstream models and carries no independent role; 2025 is a consumed holdout (post-hoc)."]}
    digest = write_once(OUT / "all_india_raw_manifest.json", encode(manifest))
    (OUT / "all_india_raw_manifest.sha256").write_text(digest + "\n", encoding="ascii", newline="\n")
    print("manifest sha256", digest)


if __name__ == "__main__":
    stage = sys.argv[1] if len(sys.argv) > 1 else ""
    if stage == "freeze":
        freeze()
    elif stage == "score":
        score()
    else:
        raise SystemExit("usage: build_all_india_raw.py freeze|score")
