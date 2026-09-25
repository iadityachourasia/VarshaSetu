"""Read-only export of frozen operational-era arrays for the historical UI.

No model is loaded or executed. Source arrays are hash-checked before use; every
export is a lossless JSON rendering of already frozen values on their paired mask.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
from scipy.io import netcdf_file
from datetime import date, datetime, timedelta

ROOT = Path(__file__).resolve().parents[1]
G = ROOT / "data/operational_derived/operational_features_2023_2025_v1"
I = ROOT / "experiments/recent_historical/phase4i_operational_model_development_v1"
J = ROOT / "experiments/recent_historical/phase4j_operational_final_test_v1"
OUT = ROOT / "frontend-v2/public/science/operational-v1"
IMD_SOURCE = {
    2017: (ROOT / "data/raw/observations/imd/2017/RF25_ind2017_rfp25.nc", "49786e2d2b661c5d3bcfb3ffd90385c1133ec27a8a04bf272ff2df5029106a9c"),
    2018: (ROOT / "data/raw/observations/imd/2018/RF25_ind2018_rfp25.nc", "26bd53aeb2d6f3f7d39516c41606db005dede474906b33462d1a0caef69cd6ec"),
    2019: (ROOT / "data/raw/observations/imd/2019/RF25_ind2019_rfp25.nc", "c551c563b3514d492a2de94c706c1c254d5826656738b4a8e7dbd83841344a5b"),
    2023: (ROOT / "experiments/recent_historical/imd/RF25_ind2023_rfp25.nc", "1fa0cbcb56769fd3cd2702e36dc3ee1b81b74755b77c7f058c70dfc3afb82831"),
    2024: (ROOT / "experiments/recent_historical/imd/RF25_ind2024_rfp25.nc", "1ef02aeba5694dbb57a6cca23a3c2cc11740affb185137c1eacbeab59893228a"),
    2025: (ROOT / "experiments/recent_historical/imd/RF25_ind2025_rfp25.nc", "7d03cd397ebb1d7209ffae947d3965113643e1f30023cca657f0aa2c800af035"),
}

PINNED = {
    "phase4g_feature_freeze": (G / "feature_generation_manifest_v1.json", "f1520a32aadef460249ba26a39c106f9593fcd3407c23d2967ddc90d889ed67b"),
    "phase4i_final_test_ready": (I / "final_freeze/FINAL_TEST_READY.json", "67170a350abb0663aedb2ea129d4eac3ce10ce9d77863af43b4f5c22700b2b48"),
    "phase4j_final_test_result": (J / "FINAL_TEST_RESULT.json", "04a7fc2a434d24449365e2cb9978cbc8584f5cc87ea4f132cfaf6e7fc7a4abca"),
    "phase4k_audit": (ROOT / "experiments/recent_historical/phase4k_independent_final_audit_v1/artifact_manifest.json", "074975ebeafa3d4c11a89fb45f0661dfd6e28dd973a500b0c73914ba7344c24f"),
    "phase4l_communication": (ROOT / "experiments/recent_historical/phase4l_communication_alignment_v1/artifact_manifest.json", "71098c8c70823a72962bf4b34a4e838a2eeea7a0beb1cd7ea45c3162620372c6"),
}


def sha(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def verify(path: Path, expected: str) -> None:
    if sha(path) != expected:
        raise ValueError(f"Frozen source hash mismatch: {path}")


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value: object, *, replace: bool = False) -> str:
    data = (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n").encode("utf-8")
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and path.read_bytes() != data and not replace:
        raise ValueError(f"Existing presentation artifact differs: {path}")
    if replace or not path.exists():
        path.write_bytes(data)
    return sha(path)


def serial(values: np.ndarray) -> list[float]:
    if not np.isfinite(values).all():
        raise ValueError("Non-finite paired scientific value")
    return values.astype(float).tolist()


def verify_phase4j() -> None:
    integrity = read_json(J / "ARTIFACT_INTEGRITY.json")
    for relative, metadata in integrity["files"].items():
        verify(J / relative, metadata["sha256"])


def verify_phase4i(paths: list[str]) -> None:
    ready = read_json(I / "final_freeze/FINAL_TEST_READY.json")
    for relative in paths:
        verify(I / relative, ready["files_sha256"][relative])


def verify_year(year: int, split: str) -> dict:
    base = G / str(year) / split
    manifest = read_json(base / "year_manifest.json")
    names = {
        "deterministic/cases.json": "cases",
        "deterministic/X.npy": "features",
        "deterministic/pixel_index.npy": "pixel_index",
    }
    if year < 2025:
        names["deterministic/y_mm.npy"] = "target_mm"
    for relative, key in names.items():
        verify(base / relative, manifest["outputs_sha256"]["deterministic"][key])
    verify(base / "regime/cases.json", manifest["outputs_sha256"]["regime"]["cases"])
    if year == 2025:
        verify(base / "ensemble_baseline/members_mm.npy", manifest["outputs_sha256"]["ensemble_baseline"]["members"])
        verify(base / "ensemble_baseline/cases.json", manifest["outputs_sha256"]["ensemble_baseline"]["cases"])
    return manifest


def export_observations(common_pixels: list[int]) -> dict:
    """Daily IMD descriptive context only; not a forecast or trend analysis."""
    records = []
    source_hashes = {}
    for year, (path, expected) in IMD_SOURCE.items():
        verify(path, expected)
        source_hashes[str(year)] = expected
        with netcdf_file(path, "r", mmap=False) as nc:
            latitude = np.asarray(nc.variables["LATITUDE"].data, dtype=float)
            longitude = np.asarray(nc.variables["LONGITUDE"].data, dtype=float)
            lat_indices = np.flatnonzero((latitude >= 10) & (latitude <= 22))
            lon_indices = np.flatnonzero((longitude >= 68) & (longitude <= 80))
            if len(lat_indices) != 49 or len(lon_indices) != 49 or not np.allclose(latitude[lat_indices], np.arange(10, 22.01, 0.25)) or not np.allclose(longitude[lon_indices], np.arange(68, 80.01, 0.25)):
                raise ValueError(f"IMD target grid mismatch for {year}")
            units = nc.variables["TIME"].units.decode("utf-8")
            origin = datetime.fromisoformat(units.removeprefix("days since "))
            time_lookup = {date.fromisoformat((origin + timedelta(days=float(offset))).date().isoformat()): position for position, offset in enumerate(np.asarray(nc.variables["TIME"].data))}
            rain = nc.variables["RAINFALL"]
            fill = float(rain._FillValue)
            current = date(year, 6, 1)
            end = date(year, 10, 3)
            while current <= end:
                if current not in time_lookup:
                    raise ValueError(f"IMD date missing: {current}")
                field = np.asarray(rain.data[time_lookup[current]], dtype=float)[np.ix_(lat_indices, lon_indices)].reshape(-1)[common_pixels]
                valid = np.isfinite(field) & (field != fill) & (field >= 0)
                good = field[valid]
                records.append({"date": current.isoformat(), "year": year, "month": current.month,
                                "valid_cells": int(valid.sum()), "mean_mm": float(good.mean()) if len(good) else None,
                                "max_mm": float(good.max()) if len(good) else None,
                                "heavy_cells": int(np.count_nonzero(good >= 64.5)),
                                "very_heavy_cells": int(np.count_nonzero(good >= 115.6))})
                current += timedelta(days=1)
    return {"schema": "phase5a-six-season-imd-observations-v1", "description": "Descriptive daily IMD context across six evaluated monsoon seasons; not climatology or a trend test",
            "domain": "10–22 N, 68–80 E on the 0.25-degree grid; 1301 common land-cell positions with per-day missingness excluded",
            "date_window": "June 1 through October 3 inclusive for each listed year", "accumulation_bounds_limitation": "Annual IMD files label daily dates but do not encode explicit accumulation bounds",
            "source_sha256": source_hashes, "records": records}


def main() -> None:
    for path, expected in PINNED.values():
        verify(path, expected)
    verify_phase4j()
    phase4i_files = [f"deterministic_models/M{number}_2024.npy" for number in range(5)] + [
        "deterministic_models/validation_manifest.json",
        "oof_m2/prediction.npy", "oof_m2/row_fit_index.npy", "oof_regime/probability.npy",
        "regime_models/2024_prospective_probability.npy",
        "validation/probability_heavy_2024.json", "validation/probability_very_heavy_2024.json",
    ]
    verify_phase4i(phase4i_files)
    feature_order = read_json(G / "feature_generation_manifest_v1.json")["deterministic_feature_order"]
    column = {name: feature_order.index(name) for name in feature_order}
    use_columns = ("forecast_u850", "forecast_v850", "forecast_q700", "forecast_z500", "forecast_mslp", "forecast_pwat")
    case_level = {case["case_id"]: case for case in read_json(J / "metrics/case_level.json")["cases"]}
    paired_2025 = read_json(J / "population/2025_population_manifest.json")["paired_cases"]
    all_cases = []
    outputs = {}
    common_pixels = None
    years = ((2023, "train"), (2024, "validation"), (2025, "test_sealed"))
    for year, split in years:
        year_manifest = verify_year(year, split)
        base = G / str(year) / split
        source_cases = read_json(base / "deterministic/cases.json")
        cases = paired_2025 if year == 2025 else source_cases
        X = np.load(base / "deterministic/X.npy", mmap_mode="r", allow_pickle=False)
        source_pixels = np.load(base / "deterministic/pixel_index.npy", mmap_mode="r", allow_pickle=False)
        if year == 2025:
            source_rows = np.load(J / "pairing/source_row_index.npy", mmap_mode="r", allow_pickle=False)
            pixels = np.load(J / "pairing/pixel_index.npy", mmap_mode="r", allow_pickle=False)
            observed = np.load(J / "pairing/observation_mm.npy", mmap_mode="r", allow_pickle=False)
            predictions = {f"M{number}": np.load(J / f"predictions/M{number}.npy", mmap_mode="r", allow_pickle=False) for number in range(5)}
            heavy = np.load(J / "predictions/heavy_probability.npy", mmap_mode="r", allow_pickle=False)
            very_heavy = np.load(J / "predictions/very_heavy_probability.npy", mmap_mode="r", allow_pickle=False)
            regime = np.load(J / "predictions/regime_375x3.npy", mmap_mode="r", allow_pickle=False)
            ensemble_cases = {case["case_id"]: case for case in read_json(base / "ensemble_baseline/cases.json")}
            members = np.load(base / "ensemble_baseline/members_mm.npy", mmap_mode="r", allow_pickle=False)
        else:
            source_rows = np.arange(len(X))
            pixels = source_pixels
            observed = np.load(base / "deterministic/y_mm.npy", mmap_mode="r", allow_pickle=False)
            predictions = ({"M2_OOF": np.load(I / "oof_m2/prediction.npy", mmap_mode="r", allow_pickle=False)} if year == 2023 else
                           {f"M{number}": np.load(I / f"deterministic_models/M{number}_2024.npy", mmap_mode="r", allow_pickle=False) for number in range(5)})
            regime = np.load(I / ("oof_regime/probability.npy" if year == 2023 else "regime_models/2024_prospective_probability.npy"), mmap_mode="r", allow_pickle=False)
        regime_cases = read_json(base / "regime/cases.json")
        regime_index = {case["case_id"]: index for index, case in enumerate(regime_cases)}
        for case in cases:
            case_id = case["case_id"]
            start = case["row_start"]
            count = case["row_count"]
            stop = start + count
            these_pixels = pixels[start:stop]
            if len(np.unique(these_pixels)) != count or count != 1301:
                raise ValueError(f"Unexpected paired mask: {case_id}")
            if common_pixels is None:
                common_pixels = these_pixels.tolist()
            elif common_pixels != these_pixels.tolist():
                raise ValueError(f"Paired pixel mask differs: {case_id}")
            rows = source_rows[start:stop]
            fields = {"observed": serial(observed[start:stop])}
            for name, data in predictions.items():
                fields[name] = serial(data[start:stop])
            if "M0" not in fields:
                fields["M0"] = serial(X[rows, column["raw_c00_rain_mm"]])
            atmosphere = {name: serial(X[rows, column[name]]) for name in use_columns}
            regime_probabilities = serial(regime[regime_index[case_id]])
            detail = case_level.get(case_id)
            payload = {
                "schema": "phase5a-operational-case-v1", "case_id": case_id, "year": year,
                "source": "historical_operational_gefs", "role": year_manifest["role"],
                "initialization_utc": case["initialization_utc"], "lead_hours": case["lead_hours"],
                "product": case["product"], "valid_observation_date": case["valid_observation_date"],
                "row_count": count, "fields": fields, "atmosphere": atmosphere,
                "regime_probabilities": regime_probabilities,
                "probabilities": ({"heavy": serial(heavy[start:stop]), "very_heavy": serial(very_heavy[start:stop])} if year == 2025 else None),
                "frozen_case_metrics": detail,
                "ensemble_members": None,
            }
            if year == 2025 and case_id in ensemble_cases:
                ensemble = ensemble_cases[case_id]
                at = ensemble["ensemble_row_start"] + np.asarray(these_pixels, dtype=int)
                payload["ensemble_members"] = {name: serial(members[at, member]) for member, name in enumerate(("c00", "p01", "p02", "p03", "p04"))}
            relative = f"cases/{year}/{case_id}.json"
            outputs[relative] = write_json(OUT / relative, payload)
            observation = observed[start:stop]
            all_cases.append({
                "case_id": case_id, "year": year, "role": year_manifest["role"],
                "initialization_utc": case["initialization_utc"], "lead_hours": case["lead_hours"],
                "valid_observation_date": case["valid_observation_date"],
                "heavy_cells": int(np.count_nonzero(observation >= 64.5)),
                "very_heavy_cells": int(np.count_nonzero(observation >= 115.6)),
                "max_observed_mm": float(np.max(observation)),
                "regime_probabilities": regime_probabilities,
                "has_ensemble": payload["ensemble_members"] is not None,
                "models": sorted(fields), "has_probabilities": payload["probabilities"] is not None,
                "frozen_case_metrics": detail,
                "artifact": relative,
            })
    if [sum(case["year"] == year for case in all_cases) for year in (2023, 2024, 2025)] != [200, 183, 232]:
        raise ValueError("Unexpected frozen case population")
    index = {
        "schema": "phase5a-operational-index-v1", "experiment": "historical_operational_gefs",
        "grid": {"shape": [49, 49], "latitude_centers": [10 + 0.25 * i for i in range(49)],
                 "longitude_centers": [68 + 0.25 * i for i in range(49)], "cell_size_degrees": 0.25,
                 "bounds_west_south_east_north": [67.875, 9.875, 80.125, 22.125],
                 "crs": "EPSG:4326", "row_order": "south_to_north", "column_order": "west_to_east",
                 "mask_policy": "frozen paired 1301-cell IMD-valid mask"},
        "pixel_indices": common_pixels, "cases": all_cases, "source_hashes": {name: value for name, (_, value) in PINNED.items()},
    }
    outputs["index.json"] = write_json(OUT / "index.json", index)
    outputs["observations_six_seasons.json"] = write_json(OUT / "observations_six_seasons.json", export_observations(common_pixels))
    outputs["final_result_2025.json"] = write_json(OUT / "final_result_2025.json", read_json(J / "FINAL_TEST_RESULT.json"))
    outputs["validation_metrics_2024.json"] = write_json(
        OUT / "validation_metrics_2024.json",
        {"schema": "phase5a-2024-validation-metrics-v1", "source_sha256": sha(I / "deterministic_models/validation_manifest.json"),
         "metrics": read_json(I / "deterministic_models/validation_manifest.json")["metrics"]},
    )
    outputs["probability_validation_2024.json"] = write_json(
        OUT / "probability_validation_2024.json",
        {"schema": "phase5a-2024-probability-validation-v1",
         "heavy": read_json(I / "validation/probability_heavy_2024.json")["full_2024_descriptive_metrics"],
         "very_heavy": read_json(I / "validation/probability_very_heavy_2024.json")["full_2024_descriptive_metrics"],
         "source_sha256": {name: sha(I / f"validation/probability_{name}_2024.json") for name in ("heavy", "very_heavy")}},
    )
    year_quality = {}
    for year, split in years:
        manifest_path = G / str(year) / split / "year_manifest.json"
        source = read_json(manifest_path)
        year_quality[str(year)] = {"scheduled_cases": source["scheduled_cases"], "atmospheric_complete_cases": source["regime_cases"],
                                   "c00_source_qc_cases": source["source_deterministic_cases"], "full_five_member_cases": source["source_ensemble_cases"],
                                   "paired_deterministic_cases": source["deterministic_cases"], "source_manifest_sha256": sha(manifest_path)}
    outputs["quality.json"] = write_json(OUT / "quality.json", {"schema": "phase5a-quality-summary-v1", "years": year_quality,
        "source_message_acquisition": "Phase 4F selected-range acquisition complete; source-QC attrition is not missing-source attrition",
        "packing_policy": "Packing-derived per-message tolerance; no universal fixed subtraction threshold"})
    manifest = {"schema": "phase5a-presentation-science-manifest-v1", "read_only": True,
                "scientific_inference_run": False, "source_hashes": index["source_hashes"], "outputs_sha256": outputs}
    digest = write_json(OUT / "presentation_science_manifest.json", manifest, replace=True)
    print(f"Export verified: {len(all_cases)} cases, {len(outputs)} artifacts; manifest {digest}")


if __name__ == "__main__":
    main()
