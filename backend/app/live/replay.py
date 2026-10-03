"""Replay gate (docs/125 phase L1): run the worker path on an already-known historical cycle and compare every stage with the frozen Track B 2025 artifacts.

Only forecast-side artifacts are read: the stored decoded arrays, the stored feature matrices, the stored regime probabilities and the stored frozen-model predictions. No observation is read. The
comparison covers the cells that carry a paired observation in the frozen prediction arrays (identified by the stored pixel index, not by opening any observation).
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from backend.app.live import pipeline
from backend.app.live.stored import P4F, ROOT, StoredSource

HERE = ROOT / "experiments/recent_historical/phase4j_operational_final_test_v1"
DATA = ROOT / "data/operational_derived/operational_features_2023_2025_v1/2025/test_sealed"
TRAIN = ROOT / "data/operational_derived/operational_features_2023_2025_v1/2023/train/deterministic/X.npy"


def available() -> bool:
    return all(p.exists() for p in (HERE / "predictions/M1.npy", DATA / "deterministic/X.npy", P4F / "rainfall_qc", TRAIN))


def replay(date: str, models: pipeline.FrozenModels) -> dict:
    """Return per-product comparison of the worker path against the frozen artifacts for a 2025 cycle. Differences are exact (0.0) when the path reproduces the frozen outputs."""
    if not date.startswith("2025"):
        raise ValueError("the frozen prediction arrays exist for 2025 only")
    result = pipeline.run_cycle(StoredSource(date), date, models)
    pop = json.loads((HERE / "population/2025_population_manifest.json").read_text(encoding="utf-8"))
    paired = {c["case_id"]: c for c in pop["paired_cases"]}
    pixel = np.load(HERE / "pairing/pixel_index.npy", allow_pickle=False)
    frozen = {name: np.load(HERE / f"predictions/{name}.npy", allow_pickle=False) for name in ("M0", "M1", "M2", "M3", "M4", "heavy_probability", "very_heavy_probability")}
    regime_frozen = np.load(HERE / "predictions/regime_375x3.npy", allow_pickle=False)
    regime_cases = json.loads((DATA / "regime/cases.json").read_text(encoding="utf-8"))
    regime_index = {c["case_id"]: i for i, c in enumerate(regime_cases)}
    regime_X = np.load(DATA / "regime/X.npy", allow_pickle=False)
    det_cases = {c["case_id"]: c for c in json.loads((DATA / "deterministic/cases.json").read_text(encoding="utf-8"))}
    det_X = np.load(DATA / "deterministic/X.npy", mmap_mode="r", allow_pickle=False)
    report = {}
    for product in result["features"]:
        case_id = f"{date}_{product}"
        row = det_cases[case_id]
        stored_X = np.asarray(det_X[row["row_start"]: row["row_start"] + row["row_count"]])
        entry = {"feature_matrix_max_abs_difference": float(np.max(np.abs(result["features"][product]["X"].astype(np.float64) - stored_X.astype(np.float64)))),
                 "regime_feature_max_abs_difference": float(np.max(np.abs(result["features"][product]["regime"] - regime_X[regime_index[case_id]]))),
                 "regime_probability_max_abs_difference": float(np.max(np.abs(result["arrays"][f"regime_probability_{product}"] - regime_frozen[regime_index[case_id]])))}
        if case_id in paired:
            c = paired[case_id]
            sl = slice(c["row_start"], c["row_start"] + c["row_count"])
            cells = pixel[sl]
            entry["paired_cells"] = int(len(cells))
            for name, key in (("M0", "M0"), ("M1", "M1"), ("M2", "M2"), ("M3", "M3"), ("M4", "M4"), ("heavy_probability", "heavy_probability"), ("very_heavy_probability", "very_heavy_probability")):
                mine = result["arrays"][f"{key}_{product}"].ravel()[cells].astype(np.float64)
                entry[f"{name}_max_abs_difference"] = float(np.max(np.abs(mine - frozen[name][sl].astype(np.float64))))
        else:
            entry["paired_cells"] = 0                                    # no observation pairing for this case: model outputs are not compared (never opened to find out)
        report[product] = entry
    return {"date": date, "products": report, "withheld_products": result["provenance"]["withheld_products"]}
