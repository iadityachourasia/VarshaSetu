"""Inventory local scientific inputs without changing any frozen experiment.

The ledger records *evidence of availability*, not a new split or a claim that a
year is untouched. Run ``--check`` to compare a saved ledger with current bytes.
Missing sources remain explicitly missing; no observation is opened for scoring.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "data/manifests/research_pilot/source_year_ledger_v1.json"
REFORECAST = ROOT / "data/processed/reforecast_control_v1"
REFORECAST_PROTOCOL = ROOT / "backend/app/evidence_data/phase15/reforecast_study_protocol_v1.json"
OPERATIONAL_MANIFESTS = {
    **{year: ROOT / f"experiments/recent_historical/corpus2_payload_acquisition_v1/manifests/{year}_source_manifest.json" for year in (2021, 2022)},
    **{year: ROOT / f"experiments/recent_historical/phase4f_payload_acquisition_v1/manifests/{year}_source_manifest.json" for year in (2023, 2024, 2025)},
}
IMD_DIRS = (
    ROOT / "experiments/recent_historical/imd_climatology",
    ROOT / "experiments/recent_historical/imd_v2",
    ROOT / "experiments/recent_historical/imd",
)
CONSUMED_TEST_YEARS = {2014, 2015, 2016, 2019, 2022, 2025}
TRACK_A_ROLES = {**{year: "training_history" for year in range(2000, 2012)}, 2012: "development_validation", 2013: "development_validation",
                 2014: "consumed_test", 2015: "consumed_test", 2016: "consumed_test", 2017: "reused_development", 2018: "reused_development", 2019: "consumed_test"}
TRACK_B_ROLES = {2020: "not_acquired", 2021: "development", 2022: "consumed_test", 2023: "training_history", 2024: "development_validation",
                 2025: "consumed_test", 2026: "test_candidate_audit_pending"}
WINDOWS = {"day1_24h": [3, 27], "day2_24h": [27, 51], "day3_24h": [51, 75]}


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def artifact(path: Path) -> dict:
    if not path.is_file():
        return {"status": "not_local", "path": path.relative_to(ROOT).as_posix(), "sha256": None, "bytes": None}
    return {"status": "local", "path": path.relative_to(ROOT).as_posix(), "sha256": digest(path), "bytes": path.stat().st_size}


def imd_artifact(year: int) -> dict:
    paths = [directory / f"RF25_ind{year}_rfp25.nc" for directory in IMD_DIRS]
    present = [path for path in paths if path.is_file()]
    if not present:
        return artifact(paths[0])
    hashes = {digest(path) for path in present}
    if len(hashes) != 1:
        raise ValueError(f"local IMD copies disagree for {year}")
    return artifact(present[0])


def source_row(track: str, year: int, role: str, forecast_path: Path, expected_hash: str | None = None) -> dict:
    forecast = artifact(forecast_path)
    if expected_hash is not None and forecast["status"] == "local" and forecast["sha256"] != expected_hash:
        raise ValueError(f"frozen forecast hash mismatch for {track} {year}")
    reference = imd_artifact(year)
    return {"track": track, "year": year, "role_in_prior_work": role, "consumed_test": year in CONSUMED_TEST_YEARS,
            "forecast": forecast, "imd_reference": reference, "reference_use": "local_research_only_redistribution_unresolved",
            "accumulation_windows_hours": WINDOWS, "observation_window_utc": "03:00 to next-day 03:00",
            "new_experiment_role": "UNASSIGNED; requires a separate frozen protocol"}


def build() -> dict:
    protocol = json.loads(REFORECAST_PROTOCOL.read_text(encoding="utf-8"))
    rows = []
    for year, role in TRACK_A_ROLES.items():
        expected = protocol["data"]["forecast_side_files"].get(str(year), {}).get("X_full_sha256")
        rows.append(source_row("A_GEFSV12_REFORECAST", year, role, REFORECAST / str(year) / "X_full.npy", expected))
    for year, role in TRACK_B_ROLES.items():
        if year in OPERATIONAL_MANIFESTS:
            manifest = OPERATIONAL_MANIFESTS[year]
            sidecar = manifest.with_suffix(".sha256")
            if manifest.is_file() and sidecar.is_file() and sidecar.read_text(encoding="ascii").split()[0] != digest(manifest):
                raise ValueError(f"operational source manifest hash mismatch for {year}")
            path = manifest
        elif year == 2026:
            path = ROOT / "data/live/live/20261004/manifest.json"
        else:
            path = ROOT / f"data/operational_gefs/{year}/source_manifest.json"
        rows.append(source_row("B_OPERATIONAL_GEFS", year, role, path))
    return {"schema": "source-year-ledger-v1", "meaning": "local evidence inventory; not a protocol, independent-test seal, licence determination, or skill claim",
            "sources": {"A_GEFSV12_REFORECAST": "https://psl.noaa.gov/forecasts/reforecast2/probabilities/index.html",
                        "B_OPERATIONAL_GEFS": "https://www.noaa.gov/nodd/datasets",
                        "IMD_RF25": "https://imdpune.gov.in/cmpg/Griddata/Rainfall_25_NetCDF.html"},
            "protocol_anchor_sha256": digest(REFORECAST_PROTOCOL), "rows": rows,
            "unavailable_or_unapproved": ["NCMRWF NCUM/NEPS historical grids and data terms", "expert-annotated regime labels", "IMERG Final V07 paired 03-03 UTC corpus",
                                        "winter western-disturbance rainfall corpus", "authorized current Survey of India district boundary"],
            "test_reservation": {"2026": "candidate only; prior-observation-use audit and protocol freeze required before any test claim", "fallback": 2027}}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="compare the existing ledger against current source bytes")
    args = parser.parse_args()
    payload = json.dumps(build(), indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    if args.check:
        if not OUTPUT.is_file() or OUTPUT.read_text(encoding="utf-8") != payload:
            raise SystemExit("source/year ledger differs from current verified bytes or is missing")
        print(f"verified {OUTPUT.relative_to(ROOT)}")
    else:
        if OUTPUT.exists():
            raise SystemExit("ledger v1 is immutable; use --check or create a new version")
        OUTPUT.parent.mkdir(parents=True, exist_ok=True)
        OUTPUT.write_text(payload, encoding="utf-8", newline="\n")
        print(f"wrote {OUTPUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
