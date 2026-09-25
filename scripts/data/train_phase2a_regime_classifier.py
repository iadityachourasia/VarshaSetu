"""Fit the 2017-only pseudo-label definition and safe regime classifier."""

from __future__ import annotations

import csv
import hashlib
import json
import os
import sys
from collections import Counter
from pathlib import Path

import numpy as np
import sklearn
import zarr
from sklearn.metrics import (
    balanced_accuracy_score,
    confusion_matrix,
    f1_score,
    log_loss,
    precision_recall_fscore_support,
)

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.app.ml.forecast_regimes import (
    FEATURE_NAMES,
    FEATURE_REGISTRY,
    REGIME_NAMES,
    SafeLogisticRegimeClassifier,
    TrainingOnlyPseudoLabeler,
    extract_regime_features,
    validate_feature_registry,
    validate_temporal_roles,
)


OUTPUT = ROOT / "data/manifests/phase2a/regimes-v1"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def write_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".partial")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".partial")
    with temporary.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    os.replace(temporary, path)


def _truth(value) -> bool:
    return value is True or str(value).lower() == "true"


def read_eligible(year: int) -> set[tuple[str, str]]:
    path = ROOT / f"data/manifests/phase2a/{year}-JJAS/eligibility_index.csv"
    with path.open(newline="", encoding="utf-8") as handle:
        return {
            (row["initialization"], row["product"])
            for row in csv.DictReader(handle)
            if _truth(row["REGIME_ELIGIBLE"])
        }


def extract_year(year: int) -> tuple[list[dict], np.ndarray]:
    path = ROOT / (
        f"data/processed/phase2a/{year}-JJAS/"
        f"varshasetu-gefs12r-imd025-{year}-jjas-v2.zarr"
    )
    group = zarr.open_group(str(path), mode="r")
    variables = tuple(group.attrs["atmospheric_variable_names"])
    products = tuple(group.attrs["product_names"])
    if variables != ("u850", "v850", "q700", "z500", "mslp", "pwat"):
        raise ValueError("seasonal atmospheric variable order is not frozen Phase 2A order")
    eligible = read_eligible(year)
    latitude = np.asarray(group["context_latitude"][:], dtype=np.float64)
    longitude = np.asarray(group["context_longitude"][:], dtype=np.float64)
    init_seconds = np.asarray(group["init_time_unix_seconds"][:], dtype=np.int64)
    leads = np.asarray(group["lead_hours"][:], dtype=np.int64)
    rows, feature_rows = [], []
    from datetime import datetime, timezone

    for init_index, seconds in enumerate(init_seconds):
        initialization = datetime.fromtimestamp(int(seconds), timezone.utc).isoformat()
        for product_index, product in enumerate(products):
            if (initialization, product) not in eligible:
                continue
            field = np.asarray(group["atmosphere"][init_index, product_index], dtype=np.float64)
            features = extract_regime_features(field, latitude, longitude)
            rows.append(
                {
                    "year": year,
                    "initialization": initialization,
                    "product": product,
                    "lead_hours": int(leads[product_index]),
                }
            )
            feature_rows.append(features)
    if not feature_rows:
        raise ValueError(f"no REGIME_ELIGIBLE cases for {year}")
    return rows, np.stack(feature_rows)


def reliability_rows(probability: np.ndarray, labels: np.ndarray) -> list[dict]:
    rows = []
    edges = np.linspace(0.0, 1.0, 11)
    for class_id, regime in enumerate(REGIME_NAMES):
        observed = labels == class_id
        for bin_index in range(10):
            left, right = edges[bin_index], edges[bin_index + 1]
            selected = (probability[:, class_id] >= left) & (
                probability[:, class_id] < right if bin_index < 9 else probability[:, class_id] <= right
            )
            rows.append(
                {
                    "regime": regime,
                    "bin_lower": left,
                    "bin_upper": right,
                    "count": int(selected.sum()),
                    "mean_predicted_probability": (
                        float(probability[selected, class_id].mean()) if selected.any() else ""
                    ),
                    "observed_pseudo_label_fraction": (
                        float(observed[selected].mean()) if selected.any() else ""
                    ),
                }
            )
    return rows


def metrics(labels: np.ndarray, predicted: np.ndarray, probability: np.ndarray) -> dict:
    precision, recall, per_f1, support = precision_recall_fscore_support(
        labels, predicted, labels=np.arange(3), zero_division=0
    )
    return {
        "interpretation": "classifier reproduction/consistency with deterministic prototype pseudo-labels; not objective meteorological truth",
        "case_count": int(labels.size),
        "confusion_matrix_rows_true_columns_predicted": confusion_matrix(
            labels, predicted, labels=np.arange(3)
        ).tolist(),
        "macro_f1": float(f1_score(labels, predicted, average="macro")),
        "balanced_accuracy": float(balanced_accuracy_score(labels, predicted)),
        "multiclass_log_loss": float(log_loss(labels, probability, labels=np.arange(3))),
        "multiclass_brier_score": float(
            np.mean(np.sum((probability - np.eye(3)[labels]) ** 2, axis=1))
        ),
        "per_class": {
            REGIME_NAMES[index]: {
                "precision": float(precision[index]),
                "recall": float(recall[index]),
                "f1": float(per_f1[index]),
                "support": int(support[index]),
                "probability_minimum": float(probability[:, index].min()),
                "probability_median": float(np.median(probability[:, index])),
                "probability_maximum": float(probability[:, index].max()),
            }
            for index in range(3)
        },
    }


def main() -> None:
    validate_feature_registry()
    validate_temporal_roles(2017, 2018, 2019)
    train_rows, train_features = extract_year(2017)
    validation_rows, validation_features = extract_year(2018)

    labeler = TrainingOnlyPseudoLabeler.fit(train_features, fitted_year=2017)
    train_labels, train_low, train_active = labeler.transform(train_features)
    validation_labels, validation_low, validation_active = labeler.transform(validation_features)
    classifier = SafeLogisticRegimeClassifier.fit(train_features, train_labels)
    validation_probability = classifier.predict_proba(validation_features)
    validation_predicted = classifier.predict(validation_features)

    labeler_path = OUTPUT / "pseudo_label_definition.json"
    model_path = OUTPUT / "regime_classifier.safe.json"
    write_json(labeler_path, labeler.to_dict())
    write_json(
        model_path,
        classifier.to_dict()
        | {
            "training_year": 2017,
            "validation_year": 2018,
            "test_year": 2019,
            "test_year_accessed": False,
            "sklearn_version": sklearn.__version__,
        },
    )

    artifact_rows = []
    for rows, features, labels, low_scores, active_scores, probability, predicted in (
        (
            train_rows,
            train_features,
            train_labels,
            train_low,
            train_active,
            classifier.predict_proba(train_features),
            classifier.predict(train_features),
        ),
        (
            validation_rows,
            validation_features,
            validation_labels,
            validation_low,
            validation_active,
            validation_probability,
            validation_predicted,
        ),
    ):
        for index, row in enumerate(rows):
            artifact_rows.append(
                row
                | {name: float(features[index, position]) for position, name in enumerate(FEATURE_NAMES)}
                | {
                    "prototype_regime_id": int(labels[index]),
                    "prototype_regime": REGIME_NAMES[int(labels[index])],
                    "low_depression_score": float(low_scores[index]),
                    "active_monsoon_score": float(active_scores[index]),
                    "predicted_regime_id": int(predicted[index]),
                    "predicted_regime": REGIME_NAMES[int(predicted[index])],
                    "probability_active": float(probability[index, 0]),
                    "probability_break_weak": float(probability[index, 1]),
                    "probability_low_depression": float(probability[index, 2]),
                }
            )
    table_path = OUTPUT / "regime_cases_2017_2018.csv"
    write_csv(table_path, artifact_rows)
    reliability_path = OUTPUT / "validation_reliability.csv"
    write_csv(reliability_path, reliability_rows(validation_probability, validation_labels))

    validation_metrics = metrics(
        validation_labels, validation_predicted, validation_probability
    )
    by_lead = {}
    validation_leads = np.asarray([row["lead_hours"] for row in validation_rows])
    for lead in (24, 48, 72):
        selected = validation_leads == lead
        by_lead[str(lead)] = metrics(
            validation_labels[selected],
            validation_predicted[selected],
            validation_probability[selected],
        )
    validation_metrics["by_lead"] = by_lead
    validation_metrics["training_class_counts"] = {
        REGIME_NAMES[key]: value for key, value in sorted(Counter(train_labels).items())
    }
    validation_metrics["validation_class_counts"] = {
        REGIME_NAMES[key]: value for key, value in sorted(Counter(validation_labels).items())
    }
    validation_metrics["training_class_fractions"] = {
        key: value / len(train_labels)
        for key, value in validation_metrics["training_class_counts"].items()
    }
    validation_metrics["validation_class_fractions"] = {
        key: value / len(validation_labels)
        for key, value in validation_metrics["validation_class_counts"].items()
    }
    validation_metrics["qualitative_sanity_cases"] = []
    for name, scores, maximize in (
        ("strongest_low_depression_score", validation_low, True),
        ("strongest_active_score", validation_active, True),
        ("weakest_active_score", validation_active, False),
    ):
        index = int(np.argmax(scores) if maximize else np.argmin(scores))
        validation_metrics["qualitative_sanity_cases"].append(
            validation_rows[index]
            | {
                "selection": name,
                "pseudo_label": REGIME_NAMES[int(validation_labels[index])],
                "low_depression_score": float(validation_low[index]),
                "active_monsoon_score": float(validation_active[index]),
                "pwat_area_mean": float(
                    validation_features[index, FEATURE_NAMES.index("pwat_area_mean")]
                ),
                "mslp_minimum": float(
                    validation_features[index, FEATURE_NAMES.index("mslp_minimum")]
                ),
                "relative_vorticity_p90": float(
                    validation_features[index, FEATURE_NAMES.index("relative_vorticity_p90")]
                ),
                "note": "forecast-field diagnostic only; no observation was consulted",
            }
        )
    metrics_path = OUTPUT / "validation_metrics.json"
    write_json(metrics_path, validation_metrics)
    registry_path = OUTPUT / "feature_registry.json"
    write_json(
        registry_path,
        {
            "schema_version": 1,
            "features": list(FEATURE_REGISTRY),
            "leakage_gate": "PASS",
            "test_year_accessed": False,
        },
    )
    artifacts = [labeler_path, model_path, table_path, reliability_path, metrics_path, registry_path]
    manifest = {
        "artifact_version": "phase2a-regimes-v1",
        "training_year": 2017,
        "validation_year": 2018,
        "held_out_test_year": 2019,
        "held_out_test_accessed": False,
        "random_seed": 26080,
        "feature_names": list(FEATURE_NAMES),
        "training_cases": len(train_rows),
        "validation_cases": len(validation_rows),
        "artifacts": {
            path.name: {"sha256": sha256_file(path), "byte_size": path.stat().st_size}
            for path in artifacts
        },
    }
    write_json(OUTPUT / "artifact_manifest.json", manifest)
    print(json.dumps(manifest | {"validation_metrics": validation_metrics}, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
