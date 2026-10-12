"""Forecast-only 2026 feature-range diagnostic against frozen 2023 training X.

This does not establish GEFS version equivalence or rainfall skill. It reads
no reference rainfall and fits or selects no model.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import numpy as np  # noqa: E402

from backend.app.ml.phase2b import FEATURE_NAMES  # noqa: E402
from scripts import build_gefs_2026_forecast_corpus as corpus  # noqa: E402

TRAIN = ROOT / "data/operational_derived/operational_features_2023_2025_v1/2023/train/deterministic/X.npy"
TRAIN_MANIFEST = TRAIN.parents[1] / "year_manifest.json"
OUTPUT = ROOT / "data/manifests/research_pilot/2026_june_feature_range_v1.json"


def summarize(month: str) -> dict:
    settings, protocol_hash = corpus.protocol()
    training_hash = corpus.sha(TRAIN)
    anchor = json.loads(TRAIN_MANIFEST.read_text(encoding="utf-8"))["outputs_sha256"]["deterministic"]["features"]
    if training_hash != anchor:
        raise ValueError("training matrix differs from frozen 2023 year manifest")
    training = np.load(TRAIN, mmap_mode="r", allow_pickle=False)
    if training.ndim != 2 or training.shape[1] != len(FEATURE_NAMES):
        raise ValueError("frozen training feature layout differs")
    low, high = np.quantile(training, [0.001, 0.999], axis=0)
    if not np.isfinite(low).all() or not np.isfinite(high).all():
        raise ValueError("training quantiles are not finite")
    rows = []
    for cycle in corpus.dates_for_month(month, settings):
        case = corpus.verify_case(corpus.CORPUS / cycle, protocol_hash)
        for name in case["products_passing_qc"]:
            path = corpus.CORPUS / cycle / f"X_{name}.npy"
            matrix = np.load(path, mmap_mode="r", allow_pickle=False)
            if matrix.shape != (2401, len(FEATURE_NAMES)) or not np.isfinite(matrix).all():
                raise ValueError(f"invalid forecast features: {cycle} {name}")
            fractions = ((matrix < low) | (matrix > high)).mean(axis=0)
            rows.append({"cycle": cycle, "lead": name, "X_sha256": corpus.sha(path),
                         "outside_fraction_by_feature": {feature: float(fractions[i]) for i, feature in enumerate(FEATURE_NAMES)}})
    by_lead = {}
    for name in corpus.WINDOWS:
        subset = [row for row in rows if row["lead"] == name]
        if subset:
            by_lead[name] = {"cases": len(subset), "mean_outside_fraction_by_feature":
                             {feature: float(np.mean([row["outside_fraction_by_feature"][feature] for row in subset])) for feature in FEATURE_NAMES}}
        else:
            by_lead[name] = {"cases": 0, "mean_outside_fraction_by_feature": None}
    return {"schema": "varshasetu-2026-june-feature-range-v1", "month": month,
            "source_track": "B_OPERATIONAL_GEFS", "observation_read": False, "model_inference": False,
            "training_X_sha256": training_hash, "training_rows": int(training.shape[0]),
            "corpus_protocol_sha256": protocol_hash, "range_quantiles": [0.001, 0.999],
            "cases": len(rows), "by_lead": by_lead, "rows": rows,
            "interpretation": "Forecast-feature applicability diagnostic only; not model-version proof or rainfall skill."}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--month", default="202606", choices=["202606"])
    args = parser.parse_args()
    report = summarize(args.month)
    value = json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + "\n"
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT.open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(value)
    OUTPUT.with_suffix(".sha256").write_text(hashlib.sha256(value.encode("utf-8")).hexdigest() + "  " + OUTPUT.name + "\n", encoding="ascii")
    print(json.dumps({"cases": report["cases"], "by_lead": report["by_lead"]}, sort_keys=True))


if __name__ == "__main__":
    main()
