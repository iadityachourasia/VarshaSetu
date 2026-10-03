"""Context checks on the independent-years corpus v2, before any follow-up is designed.

(a) Raw GEFS (M0) verification on the development years 2021, 2023 and 2024 by zone: does 2021 look like the other development years?
(b) Forecast-side feature drift of the sealed year 2022 (and 2025) against the development years, land cells only.

Observation values are read ONLY for development years (2021, 2023, 2024) through the stored target arrays. Targets of 2022 do not exist and the
2025 targets are never loaded. Descriptive only: no model, no selection, no claim of skill. Writes docs/artifacts/corpus2_context_check.json.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
V1 = ROOT / "data/operational_derived/operational_features_2023_2025_v1"
V2 = ROOT / "data/operational_derived/v2/features"
GEO = ROOT / "backend/app/evidence_data/phase7/static_geography_v1.json"
LOCATIONS = {2021: V2 / "2021/development/deterministic", 2022: V2 / "2022/sealed_forecast_only/deterministic",
             2023: V1 / "2023/train/deterministic", 2024: V1 / "2024/validation/deterministic", 2025: V1 / "2025/test_sealed/deterministic"}
OBSERVED_YEARS = (2021, 2023, 2024)       # development years: targets may be read
HEAVY = 64.5


def zone_of_pixel() -> tuple[np.ndarray, set]:
    zone = json.loads(GEO.read_text(encoding="utf-8"))["fields"]["zone"]
    flat = np.array([zone[i][j] or "" for i in range(49) for j in range(49)], dtype=object)
    return flat, {i for i, z in enumerate(flat) if z}


def load(year: int) -> tuple[np.ndarray, np.ndarray]:
    base = LOCATIONS[year]
    return np.load(base / "X.npy"), np.load(base / "pixel_index.npy").astype(np.int64)


def raw_verification(year: int, flat: np.ndarray, land: set) -> dict:
    assert year in OBSERVED_YEARS
    x, pix = load(year)
    y = np.load(LOCATIONS[year] / "y_mm.npy")
    keep = np.isin(pix, list(land))
    raw, obs, zone = x[keep, 0].astype(np.float64), y[keep].astype(np.float64), flat[pix[keep]]
    out = {}
    for name in ("ALL", "COASTAL", "OROGRAPHIC", "COASTAL_AND_OROGRAPHIC", "OTHER"):
        m = np.ones(len(raw), bool) if name == "ALL" else zone == name
        r, o = raw[m], obs[m]
        fe, oe = int((r >= HEAVY).sum()), int((o >= HEAVY).sum())
        hits = int(((r >= HEAVY) & (o >= HEAVY)).sum())
        out[name] = {"cells": int(m.sum()), "rmse_mm": round(float(np.sqrt(np.mean((r - o) ** 2))), 3), "bias_mm": round(float(np.mean(r - o)), 3),
                     "observed_heavy": oe, "forecast_heavy": fe, "heavy_frequency_bias": round(fe / oe, 3) if oe >= 30 else None,
                     "heavy_csi": round(hits / (fe + oe - hits), 3) if oe >= 30 and (fe + oe - hits) else None}
    return out


def feature_drift(land: set) -> dict:
    from backend.app.ml.phase2b import FEATURE_NAMES
    names = list(FEATURE_NAMES)
    stats = {}
    for year in LOCATIONS:
        x, pix = load(year)
        keep = np.isin(pix, list(land))
        stats[year] = (x[keep].astype(np.float64).mean(axis=0), x[keep].astype(np.float64).std(axis=0))
    def smd(a: int, bs: tuple[int, ...]) -> dict:
        ref_mean = np.mean([stats[b][0] for b in bs], axis=0)
        ref_std = np.sqrt(np.mean([stats[b][1] ** 2 for b in bs], axis=0))
        return {n: round(float((stats[a][0][i] - ref_mean[i]) / ref_std[i]), 3) for i, n in enumerate(names) if ref_std[i] > 0 and n not in ("latitude_deg", "longitude_deg", "lead_hours")}
    out = {"2022_vs_2021": smd(2022, (2021,)), "2022_vs_2023_2024": smd(2022, (2023, 2024)), "2025_vs_2023_2024": smd(2025, (2023, 2024)),
           "2021_vs_2023_2024": smd(2021, (2023, 2024))}
    out["largest_abs_smd"] = {k: sorted(v.items(), key=lambda kv: -abs(kv[1]))[:4] for k, v in out.items()}
    return out


def main() -> None:
    flat, land = zone_of_pixel()
    result = {"raw_gefs_by_zone": {str(y): raw_verification(y, flat, land) for y in OBSERVED_YEARS},
              "feature_drift_standardised_mean_difference": feature_drift(land),
              "scope": ("descriptive; observations read only for development years 2021, 2023 and 2024; no 2022 target exists and 2025 targets were not loaded; "
                        "forecast-side feature means only for 2022 and 2025; no model, selection or skill claim"),
              "caveat": "cases are not equally eligible across years (about half pass control rainfall QC), so differences mix weather, eligibility and data effects"}
    target = ROOT / "docs/artifacts/corpus2_context_check.json"
    target.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    for y, block in result["raw_gefs_by_zone"].items():
        print(y, {z: (v["rmse_mm"], v["bias_mm"], v["heavy_frequency_bias"]) for z, v in block.items()})
    for k, v in result["feature_drift_standardised_mean_difference"]["largest_abs_smd"].items():
        print(k, v)


if __name__ == "__main__":
    main()
