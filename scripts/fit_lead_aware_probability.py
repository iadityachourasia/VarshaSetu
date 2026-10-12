"""Fit 2024 early-block recalibrators and seal later-block predictions before scoring."""

from __future__ import annotations

import hashlib
import json
import shutil
import sys
import time
from pathlib import Path
from uuid import uuid4

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.app.ml.coherent_probability import project_nested_probabilities  # noqa: E402
from backend.app.ml.lead_aware_calibration import apply_recalibrator, fit_recalibrator  # noqa: E402
from experiments.recent_historical.phase4i_operational_model_development_v1.core import HERE, sha256  # noqa: E402

MANIFEST = ROOT / "data/manifests/research_pilot"
PROTOCOL = MANIFEST / "lead_aware_probability_protocol_v1.json"
OUT = MANIFEST / "lead_aware_probability_prediction_seal_v1.json"
CACHE = ROOT / "data/processed/lead_aware_probability_v1"
YEAR = ROOT / "data/operational_derived/operational_features_2023_2025_v1/2024/validation"
TARGETS = ("heavy", "very_heavy")
ARMS = ("raw", "frozen", "global", "lead_aware")


def checked(path: Path) -> tuple[dict, str]:
    digest = sha256(path)
    if path.with_suffix(".sha256").read_text(encoding="ascii").split()[0] != digest:
        raise ValueError(f"hash sidecar mismatch: {path}")
    return json.loads(path.read_text(encoding="utf-8")), digest


def source() -> dict:
    rule, protocol_sha = checked(PROTOCOL)
    if (rule["status"] != "FROZEN_BEFORE_CANDIDATE_FITTING_AND_SELECTION_BLOCK_SCORING"
            or rule["excluded_years"] != [2025, 2026]):
        raise ValueError("lead-aware calibration protocol role differs")
    split_path = HERE / "calibration/split_2024.json"
    split = json.loads(split_path.read_text(encoding="utf-8"))
    split_sha = sha256(split_path)
    year_path = YEAR / "year_manifest.json"
    year = json.loads(year_path.read_text(encoding="utf-8"))
    det = YEAR / "deterministic"
    cases_path = det / "cases.json"
    if sha256(cases_path) != year["outputs_sha256"]["deterministic"]["cases"]:
        raise ValueError("2024 case ledger hash differs")
    cases = json.loads(cases_path.read_text(encoding="utf-8"))
    if len(cases) != 183 or sum(int(case["row_count"]) for case in cases) != 238083:
        raise ValueError("2024 calibration population differs")
    count = 238083
    lead = np.zeros(count, dtype=np.int8)
    masks = {block: np.zeros(count, dtype=bool) for block in ("calibration", "purged", "selection")}
    members = {block: set(split[f"{block}_case_ids"]) for block in masks}
    for i, case in enumerate(cases):
        start, n = int(case["row_start"]), int(case["row_count"])
        if start != i * 1301 or n != 1301 or case["lead_hours"] not in (24, 48, 72):
            raise ValueError("2024 case row or lead differs")
        lead[start:start+n] = case["lead_hours"] // 24
        matched = [block for block in masks if case["case_id"] in members[block]]
        if len(matched) != 1:
            raise ValueError("2024 chronological split is incomplete or overlapping")
        masks[matched[0]][start:start+n] = True
    if any(int(masks[block].sum()) != split[f"{block}_case_count"] * 1301 for block in masks):
        raise ValueError("2024 split row counts differ")
    if not np.all(masks["calibration"] | masks["purged"] | masks["selection"]):
        raise ValueError("2024 split does not cover every row")
    inputs, raw, frozen, labels = {}, {}, {}, {}
    for target in TARGETS:
        report_path = HERE / "validation" / f"probability_{target}_2024.json"
        report = json.loads(report_path.read_text(encoding="utf-8"))
        if report["calibration_split_sha256"] != split_sha:
            raise ValueError("probability selection used another chronological split")
        selected = report["selected_base_model_id"]
        candidate = next(row for row in report["candidate_models"] if row["id"] == selected)
        raw_path = HERE / "probability_models" / target / f"{selected}_2024.npy"
        frozen_path = HERE / "probability_models" / target / "selected_2024_probability.npy"
        if sha256(raw_path) != candidate["prediction_sha256"] or sha256(frozen_path) != report["selected_probability_sha256"]:
            raise ValueError("2024 base or frozen prediction hash differs")
        raw[target] = np.load(raw_path, allow_pickle=False)
        frozen[target] = np.load(frozen_path, allow_pickle=False)
        label_path = det / f"{target}_label.npy"
        label_hash = sha256(label_path)  # integrity scan only; no non-calibration label is decoded here
        if label_hash != year["outputs_sha256"]["deterministic"][f"{target}_label"]:
            raise ValueError("2024 IMD-derived label file hash differs")
        labels[target] = np.load(label_path, mmap_mode="r", allow_pickle=False)
        if raw[target].shape != (count,) or frozen[target].shape != (count,) or labels[target].shape != (count,):
            raise ValueError("2024 probability/label row alignment differs")
        inputs[target] = {"base_id": selected, "base_probability_sha256": candidate["prediction_sha256"],
                          "frozen_probability_sha256": report["selected_probability_sha256"],
                          "label_file_sha256": label_hash, "report_sha256": sha256(report_path)}
    return {"rule": rule, "protocol_sha256": protocol_sha, "split": split, "split_sha256": split_sha,
            "year_manifest_sha256": sha256(year_path), "cases_sha256": sha256(cases_path), "cases": cases,
            "lead": lead, "masks": masks, "raw": raw, "frozen": frozen, "labels": labels, "inputs": inputs}


def verified_cache(expected_protocol_sha: str) -> dict:
    path = CACHE / "manifest.json"
    manifest = json.loads(path.read_text(encoding="utf-8"))
    if (manifest["schema"] != "varshasetu-lead-aware-probability-fit-v1"
            or manifest["protocol_sha256"] != expected_protocol_sha
            or manifest["selection_labels_decoded"] is not False
            or sha256(path) != (CACHE / "manifest.sha256").read_text(encoding="ascii").split()[0]
            or sha256(CACHE / "predictions.npz") != manifest["prediction_archive_sha256"]):
        raise ValueError("lead-aware fit cache hash or identity differs")
    with np.load(CACHE / "predictions.npz", allow_pickle=False) as archive:
        for arm in ARMS:
            h, v = archive[f"{arm}_heavy"], archive[f"{arm}_very_heavy"]
            if (h.shape != (238083,) or v.shape != h.shape or not np.isfinite(h).all()
                    or not np.isfinite(v).all() or np.any((h < 0) | (h > 1) | (v < 0) | (v > 1))
                    or np.any(v > h)):
                raise ValueError("sealed lead-aware probability array is invalid")
    return manifest


def fit() -> dict:
    data = source()
    if CACHE.exists():
        return verified_cache(data["protocol_sha256"])
    if shutil.disk_usage(ROOT).free < 50 * 1024**3:
        raise ValueError("50 GiB disk guard failed")
    train = data["masks"]["calibration"]
    lead = data["lead"]
    support, models = {}, {"global": {}, "lead_aware": {}}
    predictions = {}
    for target in TARGETS:
        # A memory-mapped file is used here; only the early calibration rows
        # are converted to label values. Purged/selection labels enter later.
        y = np.asarray(data["labels"][target][train], dtype=np.uint8)
        event_cases = 0
        lead_support = {str(day): {"positive_cells": 0, "event_bearing_cases": 0} for day in (1, 2, 3)}
        for case in data["cases"]:
            if case["case_id"] not in set(data["split"]["calibration_case_ids"]):
                continue
            day = case["lead_hours"] // 24
            sl = slice(case["row_start"], case["row_start"] + case["row_count"])
            positive = int(np.asarray(data["labels"][target][sl]).sum())
            lead_support[str(day)]["positive_cells"] += positive
            lead_support[str(day)]["event_bearing_cases"] += int(positive > 0)
            event_cases += int(positive > 0)
        if int(y.sum()) < 100 or event_cases < 20:
            raise ValueError(f"{target} event-support gate failed")
        support[target] = {"positive_cells": int(y.sum()), "event_bearing_cases": event_cases,
                           "lead": lead_support, "calibration_rows": int(train.sum())}
        for arm, aware in (("global", False), ("lead_aware", True)):
            model = fit_recalibrator(data["raw"][target][train], lead[train], y, lead_aware=aware)
            model["base_score_sha256"] = data["inputs"][target]["base_probability_sha256"]
            model["training_block"] = "2024_early_calibration_only"
            models[arm][target] = model
            predictions[f"{arm}_{target}"] = apply_recalibrator(data["raw"][target], lead, model)
        predictions[f"raw_{target}"] = data["raw"][target]
        predictions[f"frozen_{target}"] = data["frozen"][target]
    projection = {}
    for arm in ARMS:
        h, v = predictions[f"{arm}_heavy"], predictions[f"{arm}_very_heavy"]
        projection[arm] = {"modified_cells": int(np.sum(v > h)),
                           "maximum_gap": float(np.max(np.maximum(v - h, 0)))}
        predictions[f"{arm}_heavy"], predictions[f"{arm}_very_heavy"] = project_nested_probabilities(h, v)
    CACHE.parent.mkdir(parents=True, exist_ok=True)
    stage = CACHE.parent / f".stage-{uuid4().hex}"
    stage.mkdir(exist_ok=False)
    try:
        np.savez_compressed(stage / "predictions.npz", **predictions)
        manifest = {"schema": "varshasetu-lead-aware-probability-fit-v1",
                    "protocol_sha256": data["protocol_sha256"], "split_sha256": data["split_sha256"],
                    "year_manifest_sha256": data["year_manifest_sha256"], "cases_sha256": data["cases_sha256"],
                    "selected_base_inputs": data["inputs"], "calibration_support": support,
                    "models": models, "projection": projection,
                    "fit_block": "2024_early_calibration_only", "selection_labels_decoded": False,
                    "calibration_case_count": data["split"]["calibration_case_count"],
                    "purged_case_count": data["split"]["purged_case_count"],
                    "selection_case_count": data["split"]["selection_case_count"],
                    "prediction_archive_sha256": sha256(stage / "predictions.npz"),
                    "meaning": "Retrospective development recalibration; all arms projected for nested-event coherence, no independent or live calibration claim"}
        payload = json.dumps(manifest, indent=2, sort_keys=True, allow_nan=False) + "\n"
        (stage / "manifest.json").write_text(payload, encoding="utf-8", newline="\n")
        (stage / "manifest.sha256").write_text(hashlib.sha256(payload.encode()).hexdigest() + "  manifest.json\n", encoding="ascii")
        for attempt in range(5):
            if CACHE.exists() or stage.resolve().parent != CACHE.parent.resolve():
                raise ValueError("lead-aware fit cache changed or escaped")
            try:
                stage.rename(CACHE)
                break
            except PermissionError as error:
                if getattr(error, "winerror", None) != 5 or attempt == 4:
                    raise
                time.sleep(0.2 * (attempt + 1))
    except Exception:
        if stage.exists() and stage.resolve().parent == CACHE.parent.resolve():
            shutil.rmtree(stage)
        raise
    return verified_cache(data["protocol_sha256"])


def seal() -> dict:
    data = source()
    manifest = verified_cache(data["protocol_sha256"])
    manifest_sha = sha256(CACHE / "manifest.json")
    result = {"schema": "varshasetu-lead-aware-probability-prediction-seal-v1",
              "protocol_sha256": data["protocol_sha256"], "fit_manifest_sha256": manifest_sha,
              "prediction_archive_sha256": manifest["prediction_archive_sha256"],
              "calibration_case_count": manifest["calibration_case_count"],
              "purged_case_count": manifest["purged_case_count"],
              "selection_case_count": manifest["selection_case_count"],
              "selection_labels_decoded": False,
              "role": "consumed_2024_development_candidates_no_independent_reliability_claim"}
    payload = json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n"
    if OUT.exists():
        if OUT.read_text(encoding="utf-8") != payload or OUT.with_suffix(".sha256").read_text(encoding="ascii").split()[0] != sha256(OUT):
            raise ValueError("immutable lead-aware prediction seal differs")
    else:
        with OUT.open("x", encoding="utf-8", newline="\n") as stream:
            stream.write(payload)
        OUT.with_suffix(".sha256").write_text(hashlib.sha256(payload.encode()).hexdigest() + "  " + OUT.name + "\n", encoding="ascii")
    return result


def main() -> None:
    manifest = fit()
    result = seal()
    print(json.dumps({"fit_rows": manifest["calibration_support"]["heavy"]["calibration_rows"],
                      "calibration_support": manifest["calibration_support"],
                      "projection": manifest["projection"],
                      "prediction_seal_sha256": sha256(OUT),
                      "selection_labels_decoded": result["selection_labels_decoded"]}))


if __name__ == "__main__":
    main()
