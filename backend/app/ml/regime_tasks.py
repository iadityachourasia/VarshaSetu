"""Pure rules of the regime-detection tasks (protocol reforecast_study_protocol_v1.json, docs/142): AUC, balanced accuracy, the validation-fitted operating point, the climatology baseline,
the date-level bootstrap and the verdict tiers. sklearn is used only to fit the standardised logistic models; everything that decides a verdict is plain arithmetic.
"""

from __future__ import annotations

import numpy as np
from sklearn.linear_model import LogisticRegression

TASKS = ("ACTIVE", "BREAK", "LOW_DEPRESSION", "WESTERN_DISTURBANCE", "COASTAL_OROGRAPHIC")
C_GRID = (0.01, 0.1, 1.0, 10.0)
MIN_CLASS_CASES = 30
USEFUL_AUC = 0.70
REPEATS, SEED = 2000, 26080
BASELINE_COLUMNS = ("lead_hours", "doy_sin", "doy_cos")


def auc(score: np.ndarray, label: np.ndarray) -> float:
    """Area under the ROC curve by the rank-sum formula with average ranks for ties. NaN if a class is empty."""
    score, label = np.asarray(score, dtype=np.float64), np.asarray(label).astype(bool)
    n1, n0 = int(label.sum()), int((~label).sum())
    if n1 == 0 or n0 == 0:
        return float("nan")
    order = np.argsort(score, kind="mergesort")
    ranks = np.empty(len(score), dtype=np.float64)
    sorted_scores = score[order]
    i = 0
    while i < len(score):
        j = i
        while j + 1 < len(score) and sorted_scores[j + 1] == sorted_scores[i]:
            j += 1
        ranks[order[i: j + 1]] = (i + j) / 2.0 + 1.0
        i = j + 1
    return float((ranks[label].sum() - n1 * (n1 + 1) / 2.0) / (n1 * n0))


def confusion(predicted: np.ndarray, label: np.ndarray) -> dict:
    p, y = np.asarray(predicted).astype(bool), np.asarray(label).astype(bool)
    tp, fn, fp, tn = int((p & y).sum()), int((~p & y).sum()), int((p & ~y).sum()), int((~p & ~y).sum())
    recall = tp / (tp + fn) if tp + fn else float("nan")
    specificity = tn / (tn + fp) if tn + fp else float("nan")
    return {"tp": tp, "fn": fn, "fp": fp, "tn": tn, "recall": recall, "specificity": specificity, "precision": tp / (tp + fp) if tp + fp else float("nan"),
            "balanced_accuracy": float((recall + specificity) / 2) if tp + fn and tn + fp else float("nan")}


def best_threshold(score: np.ndarray, label: np.ndarray) -> float:
    """The score threshold (taken at an observed score) that maximises balanced accuracy on the data given; the smallest such threshold on ties."""
    score = np.asarray(score, dtype=np.float64)
    best, arg = -1.0, float(np.median(score))
    for t in np.unique(score):
        ba = confusion(score >= t, label)["balanced_accuracy"]
        if np.isfinite(ba) and ba > best + 1e-12:
            best, arg = ba, float(t)
    return arg


def fit_logistic(X: np.ndarray, y: np.ndarray, C: float) -> dict:
    X = np.asarray(X, dtype=np.float64)
    mean, scale = X.mean(axis=0), X.std(axis=0)
    scale[scale == 0] = 1.0
    model = LogisticRegression(C=C, max_iter=2000, random_state=SEED).fit((X - mean) / scale, np.asarray(y).astype(int))
    return {"mean": mean, "scale": scale, "coef": model.coef_[0], "intercept": float(model.intercept_[0]), "C": C}


def score_logistic(model: dict, X: np.ndarray) -> np.ndarray:
    z = ((np.asarray(X, dtype=np.float64) - model["mean"]) / model["scale"]) @ model["coef"] + model["intercept"]
    return 1.0 / (1.0 + np.exp(-z))


def select_C(X_train: np.ndarray, y_train: np.ndarray, X_val: np.ndarray, y_val: np.ndarray) -> tuple[float, dict]:
    """The C of the grid with the highest validation AUC (ties go to the smaller C, the stronger regularisation)."""
    results = {}
    for C in C_GRID:
        results[C] = auc(score_logistic(fit_logistic(X_train, y_train, C), X_val), y_val)
    finite = {c: a for c, a in results.items() if np.isfinite(a)}
    if not finite:
        raise ValueError("validation has no usable AUC")
    best = max(sorted(finite), key=lambda c: (finite[c], -c))
    return best, {str(c): results[c] for c in C_GRID}


def supported(label: np.ndarray) -> bool:
    label = np.asarray(label).astype(bool)
    return bool(label.sum() >= MIN_CLASS_CASES and (~label).sum() >= MIN_CLASS_CASES)


def bootstrap(score: np.ndarray, baseline_score: np.ndarray, label: np.ndarray, predicted: np.ndarray, clusters: list, *, repeats: int = REPEATS, seed: int = SEED) -> dict:
    """95 percent percentile intervals of the AUC, the balanced accuracy and the AUC difference over the baseline, resampling whole initialization dates (optimistic: neighbouring dates are correlated)."""
    unique = sorted(set(clusters))
    members = {c: np.flatnonzero([x == c for x in clusters]) for c in unique}
    rng = np.random.default_rng(seed)
    draws = {"auc": [], "balanced_accuracy": [], "auc_over_baseline": []}
    for _ in range(repeats):
        pick = np.concatenate([members[unique[i]] for i in rng.integers(0, len(unique), size=len(unique))])
        a, b = auc(score[pick], label[pick]), auc(baseline_score[pick], label[pick])
        ba = confusion(predicted[pick], label[pick])["balanced_accuracy"]
        if np.isfinite(a) and np.isfinite(b):
            draws["auc"].append(a)
            draws["auc_over_baseline"].append(a - b)
        if np.isfinite(ba):
            draws["balanced_accuracy"].append(ba)
    point = {"auc": auc(score, label), "balanced_accuracy": confusion(predicted, label)["balanced_accuracy"], "auc_over_baseline": auc(score, label) - auc(baseline_score, label)}
    out = {"repeats": repeats, "seed": seed, "unit": "initialization date"}
    for name, values in draws.items():
        if len(values) < repeats * 0.9 or not np.isfinite(point[name]):
            out[name] = {"status": "undefined", "point": None if not np.isfinite(point[name]) else point[name]}
        else:
            low, high = (float(x) for x in np.quantile(values, [0.025, 0.975]))
            out[name] = {"status": "ok", "point": float(point[name]), "interval95": [low, high], "excludes_zero": bool(low > 0 or high < 0)}
    return out


def verdict(stats: dict, gate: bool) -> dict:
    """Tier of one task: VALIDATED needs the AUC lower bound above 0.5 and a positive lower bound of the AUC gain over the climatology baseline; USEFUL also needs an AUC of at least 0.70."""
    if not gate:
        return {"tier": "INSUFFICIENT_SUPPORT", "validated": False, "useful": False}
    a, d = stats["auc"], stats["auc_over_baseline"]
    validated = bool(a["status"] == "ok" and a["interval95"][0] > 0.5 and d["status"] == "ok" and d["interval95"][0] > 0.0)
    useful = bool(validated and a["point"] >= USEFUL_AUC)
    return {"tier": "USEFUL" if useful else "VALIDATED" if validated else "NOT_VALIDATED", "validated": validated, "useful": useful}
