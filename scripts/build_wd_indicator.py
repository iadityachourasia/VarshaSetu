"""Forecast-time western-disturbance indicator: definition, per-case flags and a pre-registered descriptive check (protocol v1, docs/138). Two stages, write-once.

    python scripts/build_wd_indicator.py freeze   # stored GLOBAL forecast 500 hPa height fields ONLY (no new download): training-year threshold and the indicator of every case; no observation is read
    python scripts/build_wd_indicator.py score    # verifies the frozen protocol and case-file hashes, then compares the flags with observed rainfall in the north-west India rain box

The indicator is the mean geostrophic vorticity at 500 hPa over north-west India from the forecast height alone (docs/122 option C, a forecast-only trough heuristic). It is NOT a validated detection of
western disturbances: no label source exists. Training year 2023; development 2021 and 2024; POST-HOC 2022 and 2025 (consumed holdouts). The 2017-2019 reforecast track is not used because only a
5-30 N context window was kept for it. IMD files are local only; only aggregate counts and scores are written.
"""

from __future__ import annotations

import hashlib
import json
import sys
from datetime import date, timedelta
from pathlib import Path

import numpy as np
from scipy.io import netcdf_file

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.app.data_sources.noaa_gefs_monthly import ATMOSPHERIC_SPECS, crop_grid, decode_atmospheric_message  # noqa: E402
from backend.app.ml import regime_validation as rv  # noqa: E402
from backend.app.ml import wd_indicator as wd  # noqa: E402

OUT = ROOT / "backend/app/evidence_data/phase13"
PROTOCOL, CASES = OUT / "wd_indicator_protocol_v1.json", OUT / "wd_indicator_cases_v1.json"
EXP = ROOT / "experiments/recent_historical"
YEARS = {
    2021: {"role": "development", "gefs": "v2", "receipts": EXP / "corpus2_payload_acquisition_v1/receipts", "imd": EXP / "imd_v2/RF25_ind2021_rfp25.nc",
           "evidence_role": "WD_2021_DEVELOPMENT_YEAR_NEVER_USED_FOR_ANY_SELECTION"},
    2022: {"role": "post_hoc", "gefs": "v2", "receipts": EXP / "corpus2_payload_acquisition_v1/receipts", "imd": EXP / "imd_v2/RF25_ind2022_rfp25.nc",
           "evidence_role": "WD_2022_CONSUMED_FINAL_TEST__POST_HOC_EXPLORATORY_ANALYSIS_OF_THE_COMPLETED_2022_FINAL_TEST"},
    2023: {"role": "training", "gefs": "v1", "receipts": EXP / "phase4f_payload_acquisition_v1/receipts", "imd": EXP / "imd/RF25_ind2023_rfp25.nc", "evidence_role": "WD_2023_TRAINING_YEAR"},
    2024: {"role": "development", "gefs": "v1", "receipts": EXP / "phase4f_payload_acquisition_v1/receipts", "imd": EXP / "imd/RF25_ind2024_rfp25.nc",
           "evidence_role": "WD_2024_DEVELOPMENT_YEAR_REUSED_FOR_MODEL_SELECTION"},
    2025: {"role": "post_hoc", "gefs": "v1", "receipts": EXP / "phase4f_payload_acquisition_v1/receipts", "imd": EXP / "imd/RF25_ind2025_rfp25.nc",
           "evidence_role": "WD_2025_CONSUMED_FINAL_TEST__POST_HOC_EXPLORATORY_ANALYSIS_OF_THE_COMPLETED_2025_FINAL_TEST"},
}
EVALUATED = (2021, 2022, 2024, 2025)
LABELS = {2021: "Track B-style 2021: development year (never used for any selection)", 2022: "POST-HOC EXPLORATORY ANALYSIS OF THE COMPLETED 2022 FINAL TEST",
          2024: "2024 validation/selection year: development evidence", 2025: "POST-HOC EXPLORATORY ANALYSIS OF THE COMPLETED 2025 FINAL TEST"}
CROP = dict(south=20.0, north=43.0, west=57.0, east=83.0)


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def clean(value):
    if isinstance(value, dict):
        return {k: clean(v) for k, v in value.items()}
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


def season_dates(year: int) -> list[date]:
    d, out = date(year, 6, 1), []
    while d <= date(year, 10, 3):
        out.append(d)
        d += timedelta(days=1)
    return out


def case_index(year: int, day: date, lead_day: int) -> tuple[float, str | None]:
    """The indicator of one case from the stored global forecast Z500 message, after checking the raw file's hash against its receipt."""
    meta = YEARS[year]
    stamp, hour = day.strftime("%Y%m%d"), 24 * lead_day
    raw = ROOT / f"data/operational_gefs/{meta['gefs']}/{year}/{stamp}/pgrb2ap5/c00_f{hour:03d}_z500.grib2"
    receipt = meta["receipts"] / str(year) / stamp / f"{stamp}_pgrb2ap5_c00_f{hour:03d}_z500.json"
    if not raw.is_file() or not receipt.is_file():
        return float("nan"), "source_missing"
    saved = json.loads(receipt.read_text(encoding="utf-8"))
    if saved.get("state") != "HASH_VERIFIED" or sha(raw) != saved["sha256"]:
        return float("nan"), "source_integrity_failure"
    try:
        grid = decode_atmospheric_message(raw.read_bytes(), member="c00", description="ENS=low-res ctl", spec=ATMOSPHERIC_SPECS["z500"], lead_hour=hour)
        region = crop_grid(grid, **CROP)
        return wd.index_from_z500(region.values, region.latitude, region.longitude), None
    except Exception as error:                      # an undecodable message is recorded, never patched
        return float("nan"), f"decode_failure:{type(error).__name__}"


def year_cases(year: int) -> list[dict]:
    rows = []
    for day in season_dates(year):
        for lead in (1, 2, 3):
            value, problem = case_index(year, day, lead)
            rows.append({"case_id": f"{day.strftime('%Y%m%d')}_day{lead}_24h", "initialization": day.isoformat(), "lead_day": lead, "index": None if not np.isfinite(value) else value, "problem": problem})
    return rows


def freeze() -> None:
    if PROTOCOL.exists():
        raise SystemExit("western-disturbance protocol v1 already frozen; a change needs a new version")
    OUT.mkdir(parents=True, exist_ok=True)
    training = year_cases(2023)
    values = np.array([np.nan if r["index"] is None else r["index"] for r in training])
    cut = wd.upper_tercile(values[np.isfinite(values)])
    cases, counts = {}, {}
    for year in EVALUATED:
        rows = year_cases(year)
        for r in rows:
            flagged = wd.flag(np.nan if r["index"] is None else r["index"], cut)
            r["flag"] = flagged
        cases[str(year)] = rows
        counts[str(year)] = {"cases": len(rows), "undefined_index": sum(1 for r in rows if r["index"] is None), "flagged": sum(1 for r in rows if r["flag"] is True), "not_flagged": sum(1 for r in rows if r["flag"] is False)}
    cases_digest = write_once(CASES, encode({"schema": "wd-indicator-cases-v1", "note": "forecast-only indicator and flag per case; no observation was read", "threshold": cut, "populations": cases}))
    protocol = {
        "schema": "wd-indicator-protocol-v1", "status": "APPROVED_FOR_EXECUTION", "no_observation_read": True,
        "purpose": ("Define a forecast-time western-disturbance indicator and the descriptive test of whether it relates to observed north-west India rainfall, BEFORE any observation is compared. "
                    "A rule-based trough heuristic (docs/122 option C); not a validated detection of western disturbances."),
        "definition": {"indicator": "mean geostrophic relative vorticity at 500 hPa over the box 25-38 N, 62-78 E, from the forecast 500 hPa geopotential height alone (spherical centred differences), in units of 1e-5 per second; positive is cyclonic",
                       "inputs": "the stored global 0.5 degree forecast HGT 500 mb message of the control member at the lead hour (24, 48, 72); no observation, model output or other field",
                       "flag": "indicator at or above the upper tercile of the 2023 training-year distribution", "threshold": cut, "training_year": 2023, "cases_file_sha256": cases_digest,
                       "lineage": "every raw message's hash is checked against its HASH_VERIFIED receipt before decoding", "boxes": {"indicator": list(wd.WD_BOX), "rain": list(wd.RAIN_BOX)}},
        "populations": {str(y): {"year": y, "role": YEARS[y]["role"], "evidence_role": YEARS[y]["evidence_role"], "label": LABELS[y], "forecast_only_counts": counts[str(y)]} for y in EVALUATED},
        "evaluation": {"observed_quantity": "IMD area-mean daily rainfall over the valid cells of the rain box 28-36 N, 70-80 E (western Himalaya and Punjab plains), on the day initialization date + lead day",
                       "statistics": ["flagged versus not flagged: cases and mean observed rainfall", "flagged-minus-not-flagged mean rainfall and the Spearman correlation of the indicator with the rainfall, each with a 95 percent bootstrap interval over initialization dates"],
                       "support_gate": {"min_flagged_cases": wd.MIN_CASES, "min_not_flagged_cases": wd.MIN_CASES, "otherwise": "insufficient_support, no number"},
                       "uncertainty": {"repeats": wd.REPEATS, "seed": wd.SEED, "unit": "initialization date", "note": "optimistic: consecutive dates are correlated"}},
        "decision_rule": {"associated_only_if": "in BOTH development populations (2021 and 2024) the flagged-minus-not-flagged mean rainfall is positive with the 95 percent interval excluding zero and the population meets the support gate",
                          "post_hoc_populations": "2022 and 2025 are reported descriptively and cannot change the decision",
                          "wording_if_met": "the heuristic indicator is associated with higher observed rainfall in the western Himalaya and Punjab region; this is not a validation that it detects western disturbances",
                          "wording_if_not_met": "no association with observed rainfall in the north-west India rain box on the development evidence; the indicator is shown without a claim"},
        "not_established_whatever_the_result": ["that a flagged case contains a western disturbance (no label source exists)", "any skill of a western-disturbance-aware correction (none exists)", "behaviour in winter, when these systems mainly act (the corpus is June to early October)"],
        "forbidden": ["fitting the threshold on any development or post-hoc year", "changing the boxes, the flag or the rule after any observation is compared", "calling the flag a validated detection of western disturbances",
                      "using the indicator as an input to any correction model"],
        "reproduction_gate": ["flag counts must equal the frozen forecast-only counts", "the group case counts must sum to the cases with a defined index and a rainfall value", "one group mean must equal an independent loop"],
        "approval": {"approved_by": "project owner", "record": "owner instruction of 2026-10-03: 'make a full plan to implement everything left partial or not completely and implement'; work package WP-D of docs/134, option C of docs/122",
                     "note": "Interpretation of a general instruction (label source option C, monsoon season only, no new download, the evaluation domain left unchanged); the owner may withdraw it."}}
    PROTOCOL.write_text(json.dumps(clean(protocol), indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    (OUT / "wd_indicator_protocol_v1.sha256").write_text(sha(PROTOCOL) + "  wd_indicator_protocol_v1.json\n", encoding="ascii")
    print("protocol sha256", sha(PROTOCOL), "threshold", cut)
    print(json.dumps(counts, indent=1))


def rain_series(path: Path) -> dict[date, float]:
    with netcdf_file(path, "r", mmap=False) as dataset:
        times = np.asarray(dataset.variables["TIME"].data, dtype=np.float64)
        lat = np.asarray(dataset.variables["LATITUDE"].data, dtype=np.float64)
        lon = np.asarray(dataset.variables["LONGITUDE"].data, dtype=np.float64)
        rainfall = np.asarray(dataset.variables["RAINFALL"].data, dtype=np.float64)
    series = rv.area_mean_series(rainfall, lat, lon, lat_box=(wd.RAIN_BOX[0], wd.RAIN_BOX[1]), lon_box=(wd.RAIN_BOX[2], wd.RAIN_BOX[3]))
    return {d: float(v) for d, v in zip(rv.dates_of(times), series) if np.isfinite(v)}


def score() -> None:
    if (OUT / "wd_indicator_protocol_v1.sha256").read_text(encoding="ascii").split()[0] != sha(PROTOCOL):
        raise SystemExit("protocol differs from its sidecar: refusing to run")
    protocol = json.loads(PROTOCOL.read_text(encoding="utf-8"))
    if sha(CASES) != protocol["definition"]["cases_file_sha256"]:
        raise SystemExit("the frozen case file differs from the protocol")
    cases = json.loads(CASES.read_text(encoding="utf-8"))["populations"]
    files = {}
    for year in EVALUATED:
        series = rain_series(YEARS[year]["imd"])
        rows = [r for r in cases[str(year)] if r["flag"] is not None]
        want = protocol["populations"][str(year)]["forecast_only_counts"]
        if (sum(1 for r in cases[str(year)] if r["flag"] is True), sum(1 for r in cases[str(year)] if r["flag"] is False)) != (want["flagged"], want["not_flagged"]):
            raise SystemExit(f"{year}: flag counts differ from the frozen forecast-only counts")
        usable = []
        for r in rows:
            day = date.fromisoformat(r["initialization"]) + timedelta(days=r["lead_day"])
            if day in series:
                usable.append((r, series[day]))
        flagged = np.array([r["flag"] for r, _ in usable], dtype=bool)
        rain = np.array([v for _, v in usable])
        index = np.array([r["index"] for r, _ in usable])
        clusters = [r["initialization"] for r, _ in usable]
        groups = wd.group_statistics(flagged, rain)
        loop = sum(v for (r, v) in usable if r["flag"]) / max(1, sum(1 for r, _ in usable if r["flag"]))
        if groups["flagged"]["cases"] and abs(groups["flagged"]["mean_rain_mm_per_day"] - loop) > 1e-9:
            raise SystemExit("reproduction gate failed: a group mean differs from an independent loop")
        gate = wd.supported(groups)
        result = {"schema": "wd-indicator-evidence-v1", "year": year, "evidence_role": YEARS[year]["evidence_role"], "label": LABELS[year], "development": YEARS[year]["role"] == "development",
                  "protocol_sha256": sha(PROTOCOL), "cases_with_defined_index": len(rows), "cases_scored": len(usable), "undefined_index_cases": len(cases[str(year)]) - len(rows), "groups": groups, "supported": gate,
                  "association": wd.bootstrap(index, flagged, rain, clusters) if gate else {"status": "insufficient_support"},
                  "reproduction": {"status": "REPRODUCED", "checks": ["flag counts equal the frozen counts", "group counts sum to the scored cases", "a group mean equals an independent loop"]},
                  "indicator_nature": "rule-based forecast-time trough heuristic; not a validated detection of western disturbances; the flag is relative to the 2023 training year"}
        if groups["flagged"]["cases"] + groups["not_flagged"]["cases"] != len(usable):
            raise SystemExit("reproduction gate failed: group counts do not sum to the scored cases")
        name = f"wd_indicator_{year}.json"
        files[name] = {"sha256": write_once(OUT / name, encode(result)), "year": year, "evidence_role": YEARS[year]["evidence_role"], "development": result["development"], "supported": gate}
        a = result["association"].get("flagged_minus_not_flagged_mean_rain", {})
        print(year, len(usable), "scored", {k: v["cases"] for k, v in groups.items()}, "supported", gate, a.get("point"), flush=True)
    dev = [json.loads((OUT / f"wd_indicator_{y}.json").read_text(encoding="utf-8")) for y in (2021, 2024)]
    met = all(r["supported"] and r["association"]["flagged_minus_not_flagged_mean_rain"]["status"] == "ok" and r["association"]["flagged_minus_not_flagged_mean_rain"]["point"] > 0
              and r["association"]["flagged_minus_not_flagged_mean_rain"]["excludes_zero"] for r in dev)
    decision = {"associated": bool(met), "rule": protocol["decision_rule"]["associated_only_if"], "wording": protocol["decision_rule"]["wording_if_met" if met else "wording_if_not_met"]}
    manifest = {"schema": "wd-indicator-manifest-v1", "protocol_sha256": sha(PROTOCOL), "cases_file_sha256": sha(CASES), "files": files, "decision": decision,
                "notes": ["A rule-based forecast-time trough heuristic; not a validated detection of western disturbances.", "2022 and 2025 are consumed holdouts: post-hoc descriptive analyses only."]}
    digest = write_once(OUT / "wd_indicator_manifest.json", encode(manifest))
    (OUT / "wd_indicator_manifest.sha256").write_text(digest + "\n", encoding="ascii", newline="\n")
    print("decision associated:", decision["associated"], "|", decision["wording"]); print("manifest sha256", digest)


if __name__ == "__main__":
    stage = sys.argv[1] if len(sys.argv) > 1 else ""
    if stage == "freeze":
        freeze()
    elif stage == "score":
        score()
    else:
        raise SystemExit("usage: build_wd_indicator.py freeze|score")
