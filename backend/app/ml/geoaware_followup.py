"""Pure functions of the geography-aware follow-up (protocol geoaware_followup_protocol_v1.json, docs/129).

Deterministic arithmetic with no model library and no data access: the four feature arms, the 16-configuration grid with the event-weight cap
of 4, leave-one-year-out folds, the per-year guardrails G1 to G4 and the selection rule. The training script calls these so the rules are
tested on their own. Unchanged v1 helpers (metrics, static columns, event weights) are reused, not copied.
"""

from __future__ import annotations

from itertools import product

import numpy as np

from backend.app.ml.geoaware import (BASE_FEATURES, G2_MAX_ABS_BIAS_MM, G3_MIN_VERY_HEAVY_FREQUENCY_BIAS, STATIC_FEATURES, event_weights,
                                     pooled_metrics, static_columns)

__all__ = ["ARMS", "ARM_ROLES", "DEVELOPMENT_YEARS", "G4_MAX_ZONE_HEAVY_FREQUENCY_BIAS", "EVENT_WEIGHT_CAP", "Z500_FEATURES", "ZONE", "assemble",
           "configurations", "event_weights", "RMSE_TOLERANCE_MM", "select_configuration_aligned", "GUARDRAILS_V1", "GUARDRAILS_V2", "guardrails_for_year", "leave_one_year_out_masks", "mean_zone_heavy_csi", "pooled_metrics", "select_configuration",
           "static_columns", "year_metrics"]

DEVELOPMENT_YEARS = (2021, 2023, 2024)
EVENT_WEIGHT_CAP = 4.0
G4_MAX_ZONE_HEAVY_FREQUENCY_BIAS = 1.5
ZONE = "COASTAL_AND_OROGRAPHIC"
Z500_FEATURES = ("forecast_z500", "z500_area_mean")
_WITH_STATIC = list(BASE_FEATURES) + list(STATIC_FEATURES)
ARMS = {
    "B0": list(BASE_FEATURES),
    "B1": _WITH_STATIC,
    "B0Z": [f for f in BASE_FEATURES if f not in Z500_FEATURES],
    "B1Z": [f for f in _WITH_STATIC if f not in Z500_FEATURES],
}
ARM_ROLES = {"B0": "control", "B1": "declared candidate", "B0Z": "sensitivity of the control to the 500 hPa height offset", "B1Z": "sensitivity of the candidate to the 500 hPa height offset"}


def assemble(base: np.ndarray, static: np.ndarray, arm: str) -> np.ndarray:
    """Feature matrix of one arm, columns in the registry order. ``base`` has the 22 frozen deterministic features, ``static`` the 8 static columns."""
    if arm not in ARMS:
        raise ValueError(f"unknown arm {arm}")
    if base.shape[1] != len(BASE_FEATURES) or static.shape != (base.shape[0], len(STATIC_FEATURES)):
        raise ValueError("base must have 22 columns and static 8 columns with the same rows")
    full = np.concatenate([base, static], axis=1)
    names = _WITH_STATIC
    matrix = full[:, [names.index(f) for f in ARMS[arm]]].astype(np.float32)
    if matrix.shape[1] != len(ARMS[arm]):
        raise ValueError("column count does not match the registry")
    return matrix


def configurations() -> list[dict]:
    """The 16 configurations in the frozen order (objective, weights, depth, rounds). ``capped_event`` uses the cap of this protocol (4)."""
    return [{"objective": o, "weights": w, "max_depth": d, "n_estimators": n}
            for o, w, d, n in product(["reg:squarederror", "reg:tweedie"], ["none", "capped_event"], [4, 6], [200, 350])]


def leave_one_year_out_masks(year_of_row: np.ndarray, held_out: int) -> tuple[np.ndarray, np.ndarray]:
    """(train_rows, test_rows) when ``held_out`` is held out: train on every other development year, never on the held-out one."""
    year_of_row = np.asarray(year_of_row)
    if held_out not in DEVELOPMENT_YEARS or not np.any(year_of_row == held_out):
        raise ValueError(f"{held_out} is not a development year present in the data")
    if set(np.unique(year_of_row).tolist()) - set(DEVELOPMENT_YEARS):
        raise ValueError("a non-development year is present: the sealed year can never enter selection")
    test = year_of_row == held_out
    return ~test, test


def year_metrics(y: np.ndarray, prediction: np.ndarray, zone_rows: np.ndarray) -> dict:
    """All-cell metrics of one held-out year plus the heavy-rain frequency bias inside the Ghats-coast zone."""
    metrics = pooled_metrics(y, prediction)
    zone = pooled_metrics(np.asarray(y)[zone_rows], np.asarray(prediction)[zone_rows])
    metrics["zone"] = {"cells": zone["cells"], "heavy_frequency_bias": zone["heavy"]["frequency_bias"], "heavy_csi": zone["heavy"]["csi"], "heavy_observed_events": zone["heavy"]["observed_events"], "bias_mm": zone["bias_mm"]}
    return metrics


def guardrails_for_year(metrics: dict, raw_heavy_csi: float) -> dict[str, bool]:
    """G1 heavy CSI at least Raw's, G2 |bias| at most 1.5 mm, G3 very-heavy frequency bias at least 0.05, G4 zone heavy frequency bias at most 1.5.

    An undefined quantity never passes."""
    heavy_csi = metrics["heavy"]["csi"]
    very_fb = metrics["very_heavy"]["frequency_bias"]
    zone_fb = metrics["zone"]["heavy_frequency_bias"]
    return {"G1": heavy_csi is not None and heavy_csi >= raw_heavy_csi,
            "G2": abs(metrics["bias_mm"]) <= G2_MAX_ABS_BIAS_MM,
            "G3": very_fb is not None and very_fb >= G3_MIN_VERY_HEAVY_FREQUENCY_BIAS,
            "G4": zone_fb is not None and zone_fb <= G4_MAX_ZONE_HEAVY_FREQUENCY_BIAS}


GUARDRAILS_V1 = ("G1", "G2", "G3", "G4")
GUARDRAILS_V2 = ("G1", "G2", "G4")        # protocol v2: G3 is reported for every held-out year but does not gate eligibility


def select_configuration(results: list[dict], raw_heavy_csi_by_year: dict[int, float], gating: tuple[str, ...] = GUARDRAILS_V1) -> dict | None:
    """Among configurations passing every GATING guardrail in EVERY held-out year, the lowest pooled out-of-fold RMSE; ties go to the earlier grid position.

    ``gating`` is the protocol's set of eligibility guardrails (v1: all four; v2: G1, G2 and G4, with G3 reported but not gating).
    ``results`` entries carry ``grid_index``, ``pooled`` (metrics over all held-out predictions) and ``by_year`` ({year: metrics}). None if nothing passes."""
    if not gating or not set(gating) <= set(GUARDRAILS_V1):
        raise ValueError("gating must be a non-empty subset of G1 to G4")
    eligible = []
    for r in results:
        if set(r["by_year"]) != set(raw_heavy_csi_by_year):
            raise ValueError("a configuration lacks a held-out year")
        if all(guardrails_for_year(r["by_year"][y], raw_heavy_csi_by_year[y])[g] for y in raw_heavy_csi_by_year for g in gating):
            eligible.append((r["pooled"]["rmse_mm"], r["grid_index"], r))
    return min(eligible, key=lambda item: (item[0], item[1]))[2] if eligible else None


RMSE_TOLERANCE_MM = 0.2                   # protocol v3: the same tolerance as decision-rule P2


def mean_zone_heavy_csi(result: dict) -> float:
    """Mean over the held-out years of the Ghats-coast zone heavy-rain CSI. An undefined year makes the whole value -inf (it can never win)."""
    values = [result["by_year"][y]["zone"]["heavy_csi"] for y in sorted(result["by_year"])]
    return float("-inf") if any(v is None for v in values) else float(sum(values) / len(values))


def select_configuration_aligned(results: list[dict], raw_heavy_csi_by_year: dict[int, float], gating: tuple[str, ...] = GUARDRAILS_V2,
                                 rmse_tolerance: float = RMSE_TOLERANCE_MM) -> dict | None:
    """Protocol v3 selection: aligned with the primary question (Ghats-coast heavy-rain CSI), bounded by overall error.

    Eligible = every gating guardrail in every held-out year (as v2). Among eligible configurations within ``rmse_tolerance`` mm of the lowest eligible
    pooled out-of-fold RMSE, the highest mean zone heavy CSI; ties go to the lower pooled RMSE, then the earlier grid position. None if nothing is eligible."""
    if rmse_tolerance < 0:
        raise ValueError("the RMSE tolerance cannot be negative")
    eligible = []
    for r in results:
        if set(r["by_year"]) != set(raw_heavy_csi_by_year):
            raise ValueError("a configuration lacks a held-out year")
        if all(guardrails_for_year(r["by_year"][y], raw_heavy_csi_by_year[y])[g] for y in raw_heavy_csi_by_year for g in gating):
            eligible.append(r)
    if not eligible:
        return None
    floor = min(r["pooled"]["rmse_mm"] for r in eligible)
    near = [r for r in eligible if r["pooled"]["rmse_mm"] <= floor + rmse_tolerance]
    return max(near, key=lambda r: (mean_zone_heavy_csi(r), -r["pooled"]["rmse_mm"], -r["grid_index"]))
