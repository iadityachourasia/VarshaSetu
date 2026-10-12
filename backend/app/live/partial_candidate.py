"""Research-only partial-grid inference; never called by the live publisher.

Missing rainfall cells are excluded before frozen-model inference. The output
keeps NaN on those cells and marks districts with insufficient area coverage
unsupported. This module does not publish a forecast or read observations.
"""

from __future__ import annotations

import numpy as np

from backend.app.data.accumulation_masked import reconstruct_masked_diagnostic
from backend.app.live import pipeline

GRID_SHAPE = (49, 49)
MODEL_FIELDS = ("M0", "M2", "M4", "heavy_probability", "very_heavy_probability")


def infer_field(rainfall: np.ndarray, valid_mask: np.ndarray, atmosphere: dict, product: str,
                models, *, minimum_fraction: float = 0.99) -> dict:
    rain = np.asarray(rainfall, dtype=np.float64)
    valid = np.asarray(valid_mask, dtype=bool)
    if product not in pipeline.LEADS or rain.shape != GRID_SHAPE or valid.shape != GRID_SHAPE:
        raise ValueError("partial-grid product or shape is invalid")
    if (not 0 < minimum_fraction <= 1 or valid.mean() < minimum_fraction
            or not np.isfinite(rain[valid]).all() or np.any(rain[valid] < 0)
            or not np.isnan(rain[~valid]).all()):
        raise ValueError("partial-grid rainfall or coverage is invalid")
    # The placeholder exists only to reuse the frozen full-grid feature builder.
    # Invalid rows are sliced out before models.apply sees the matrix.
    safe_rain = np.where(valid, rain, 0.0)
    block = pipeline.build_features({product: safe_rain}, atmosphere)[product]
    flat_valid = valid.ravel()
    X = block["X"][flat_valid]
    if X.shape != (int(flat_valid.sum()), 22) or not np.isfinite(X).all() or not np.array_equal(X[:, 0], rain.ravel()[flat_valid].astype(np.float32)):
        raise ValueError("eligible feature rows differ from valid rain cells")
    applied = models.apply(X, block["regime"])
    out = {}
    for name in MODEL_FIELDS:
        values = np.asarray(applied[name], dtype=np.float64)
        if values.shape != (len(X),) or not np.isfinite(values).all() or np.any(values < 0):
            raise ValueError(f"{name} produced invalid eligible predictions")
        if name.endswith("probability") and np.any(values > 1):
            raise ValueError(f"{name} exceeded one")
        field = np.full(flat_valid.size, np.nan, dtype=np.float64)
        field[flat_valid] = values
        out[name] = field.reshape(GRID_SHAPE)
    if np.any(out["very_heavy_probability"][valid] > out["heavy_probability"][valid] + 1e-12):
        raise ValueError("nested event probabilities are incoherent")
    if not np.array_equal(out["M0"][valid], rain[valid].astype(np.float32)):
        raise ValueError("raw forecast changed during partial inference")
    result = {"fields": out, "valid_mask": valid.copy(), "regime_probability": np.asarray(applied["regime_probability"], dtype=np.float64),
              "valid_fraction": float(valid.mean()), "valid_cells": int(valid.sum()), "invalid_cells": int((~valid).sum())}
    if "projection_modified_cells" in applied:
        result["projection_modified_cells"] = int(applied["projection_modified_cells"])
        result["projection_max_gap"] = float(applied["projection_max_gap"])
    return result


def district_rows(districts: list[dict], weights: np.ndarray, inferred: dict, *, minimum_fraction: float = 0.95) -> list[dict]:
    valid = np.asarray(inferred["valid_mask"], dtype=bool).ravel()
    if weights.shape != (len(districts), valid.size) or not 0 < minimum_fraction <= 1:
        raise ValueError("district geometry or coverage rule differs")
    totals = weights.sum(axis=1)
    if np.any(totals <= 0) or not np.isfinite(weights).all() or np.any(weights < 0):
        raise ValueError("district weights are invalid")
    rows = []
    for district, weight, total in zip(districts, weights, totals):
        coverage = float(weight[valid].sum() / total)
        supported = coverage >= minimum_fraction
        row = {"district_id": district["district_id"], "district_name": district["district_name"],
               "coverage_fraction": coverage, "supported": bool(supported),
               "reason": None if supported else "weighted valid area below 95%"}
        if supported:
            q = weight[valid] / weight[valid].sum()
            for name in MODEL_FIELDS:
                values = np.asarray(inferred["fields"][name], dtype=float).ravel()[valid]
                if not np.isfinite(values).all():
                    raise ValueError(f"supported district {name} field is invalid")
                row[f"{name}_mean"] = float(q @ values)
        else:
            row.update({f"{name}_mean": None for name in MODEL_FIELDS})
        rows.append(row)
    return rows


def run_candidate_cycle(source, date: str, models, districts: list[dict], weights: np.ndarray,
                        *, regional_minimum: float = 0.99, district_minimum: float = 0.95) -> dict:
    decoded = pipeline.decode_cycle(source, date, allow_no_eligible=True)
    products = {}
    for product, rule in pipeline.LEADS.items():
        messages = [decoded["rain_messages"][hour] for hour in rule["rain_hours"]]
        masked = reconstruct_masked_diagnostic(messages, window_start_hour=rule["window"][0], window_end_hour=rule["window"][1])
        if product in decoded["rainfall"] and (not masked.valid_mask.all() or not np.array_equal(masked.rainfall_mm, decoded["rainfall"][product])):
            raise ValueError(f"candidate differs from strict rainfall on {product}")
        try:
            inferred = infer_field(masked.rainfall_mm, masked.valid_mask, decoded["atmosphere"], product, models,
                                   minimum_fraction=regional_minimum)
            if product in decoded["rainfall"]:
                complete = pipeline.build_features({product: decoded["rainfall"][product]}, decoded["atmosphere"])[product]
                strict_prediction = models.apply(complete["X"], complete["regime"])
                for name in MODEL_FIELDS:
                    if not np.allclose(inferred["fields"][name].ravel(), strict_prediction[name], rtol=0, atol=1e-6):
                        raise ValueError(f"candidate {name} differs from the frozen full-grid model on {product}")
        except pipeline.CycleRefused as error:
            # A model/probability guard may fail for one lead. Retain a
            # refusal receipt, never partial arrays or district values.
            products[product] = {"status": "REFUSED_BY_FROZEN_MODEL_GATE", "reason": str(error),
                                 "strict_passed": product in decoded["rainfall"],
                                 "valid_cells": int(masked.valid_mask.sum()), "invalid_cells": masked.invalid_cells}
            continue
        products[product] = {"status": "READY", "inference": inferred,
                             "districts": district_rows(districts, weights, inferred, minimum_fraction=district_minimum),
                             "strict_passed": product in decoded["rainfall"]}
    return {"products": products, "sources": decoded["sources"], "frozen_models": models.hashes,
            "withheld_by_strict": decoded["failed_products"], "observation_read": False}
