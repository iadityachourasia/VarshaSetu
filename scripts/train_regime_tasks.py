"""Fit and freeze the regime-detection classifiers under the frozen protocol reforecast_study_protocol_v1.json (docs/142, R03). Development years only.

    python scripts/train_regime_tasks.py       # fits one standardised logistic model per task (and its climatology baseline) on 2000-2011, selects C on 2012-2013,
                                               # fixes the operating threshold on 2012-2013, refits on 2000-2013 and writes the tracked selection freeze

Reads the assembled task files of the training and validation years only. No sealed-year label exists until the unseal record does. After this the script STOPS.
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.app.ml import regime_tasks as rt  # noqa: E402
from backend.app.ml import reforecast_study as rs  # noqa: E402

PHASE15 = ROOT / "backend/app/evidence_data/phase15"
PROTOCOL = PHASE15 / "reforecast_study_protocol_v1.json"
FREEZE = PHASE15 / "regime_tasks_selection_freeze.json"
TASKS = ROOT / "data/processed/regime_tasks_v1"


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def clean(v):
    if isinstance(v, dict):
        return {k: clean(x) for k, x in v.items()}
    if isinstance(v, (list, tuple)):
        return [clean(x) for x in v]
    if isinstance(v, (float, np.floating)):
        return None if not np.isfinite(v) else float(v)
    return v


def load(years) -> dict:
    if set(years) & set(rs.SEALED_YEARS):
        raise SystemExit("a sealed year can never be loaded by the training script")
    F, Y, names, year_of = [], [], None, []
    for y in years:
        meta = json.loads((TASKS / f"features_{y}.json").read_text(encoding="utf-8"))
        names = meta["feature_names"]
        F.append(np.load(TASKS / f"features_{y}.npy", allow_pickle=False))
        Y.append(np.load(TASKS / f"tasks_Y_{y}.npy", allow_pickle=False))
        year_of.append(np.full(len(Y[-1]), y))
    return {"F": np.concatenate(F), "Y": np.concatenate(Y), "names": names, "year": np.concatenate(year_of)}


def columns(names: list[str], wanted) -> list[int]:
    return [names.index(c) for c in wanted]


MIN_VALIDATION_CLASS = 20          # amendment 1: below this many positives or negatives the validation years cannot select C or the threshold


def loyo_select(X: np.ndarray, y: np.ndarray, years: np.ndarray) -> tuple[float, dict, float]:
    """Amendment 1: C by the mean leave-one-year-out AUC over the training years (years holding both classes), and the operating threshold that maximises balanced accuracy on the pooled out-of-fold scores."""
    table, oof = {}, {}
    for C in rt.C_GRID:
        scores = np.full(len(y), np.nan)
        aucs = []
        for held in np.unique(years):
            test = years == held
            if not (y[test] == 1).any() or not (y[test] == 0).any():
                continue
            scores[test] = rt.score_logistic(rt.fit_logistic(X[~test], y[~test], C), X[test])
            aucs.append(rt.auc(scores[test], y[test]))
        table[str(C)], oof[C] = float(np.mean(aucs)), scores
    best = max(rt.C_GRID, key=lambda c: (table[str(c)], -c))
    keep = np.isfinite(oof[best])
    return best, table, rt.best_threshold(oof[best][keep], y[keep])


def main() -> int:
    if FREEZE.exists():
        raise SystemExit("regime-task selection freeze already exists: refusing to refit (write-once)")
    if PROTOCOL.with_suffix(".sha256").read_text(encoding="ascii").split()[0] != sha(PROTOCOL):
        raise SystemExit("protocol differs from its sidecar")
    train, valid = load(rs.TRAIN_YEARS), load(rs.VALIDATION_YEARS)
    names = train["names"]
    base_cols = columns(names, rt.BASELINE_COLUMNS)
    freeze = {"schema": "regime-tasks-selection-freeze-v1", "protocol_sha256": sha(PROTOCOL), "feature_names": names, "baseline_columns": list(rt.BASELINE_COLUMNS), "tasks": {},
              "label_thresholds_sha256": sha(TASKS / "label_thresholds.json"), "sealed_test": {"years": list(rs.SEALED_YEARS), "opened": False, "note": "no sealed-year label or reanalysis value was read"}}
    for j, task in enumerate(rt.TASKS):
        tr, va = train["Y"][:, j] >= 0, valid["Y"][:, j] >= 0
        Xtr, ytr, Xva, yva = train["F"][tr], train["Y"][tr, j], valid["F"][va], valid["Y"][va, j]
        block = {"train_cases": int(tr.sum()), "train_positives": int((ytr == 1).sum()), "validation_cases": int(va.sum()), "validation_positives": int((yva == 1).sum())}
        if (ytr == 1).sum() < 30 or (yva == 1).sum() + (yva == 0).sum() < 10:
            block["status"] = "NOT_FITTED_TOO_FEW_CASES"
            freeze["tasks"][task] = block
            print(task, block, flush=True)
            continue
        use_validation = bool((yva == 1).sum() >= MIN_VALIDATION_CLASS and (yva == 0).sum() >= MIN_VALIDATION_CLASS)
        ytr_years = train["year"][tr]
        if use_validation:
            C, table = rt.select_C(Xtr, ytr, Xva, yva)
            model = rt.fit_logistic(Xtr, ytr, C)
            threshold = rt.best_threshold(rt.score_logistic(model, Xva), yva)
            bC, bTable = rt.select_C(Xtr[:, base_cols], ytr, Xva[:, base_cols], yva)
            bmodel = rt.fit_logistic(Xtr[:, base_cols], ytr, bC)
            bthreshold = rt.best_threshold(rt.score_logistic(bmodel, Xva[:, base_cols]), yva)
            method = "validation_years"
        else:
            C, table, threshold = loyo_select(Xtr, ytr, ytr_years)
            bC, bTable, bthreshold = loyo_select(Xtr[:, base_cols], ytr, ytr_years)
            model, bmodel = rt.fit_logistic(Xtr, ytr, C), rt.fit_logistic(Xtr[:, base_cols], ytr, bC)
            method = "leave_one_year_out_over_training_years (amendment 1)"
        full = np.concatenate([Xtr, Xva]), np.concatenate([ytr, yva])
        final, bfinal = rt.fit_logistic(full[0], full[1], C), rt.fit_logistic(full[0][:, base_cols], full[1], bC)
        block.update({"status": "FITTED", "selection_method": method, "C": C, "validation_auc_by_C": table, "validation_auc": rt.auc(rt.score_logistic(model, Xva), yva), "operating_threshold": threshold,
                      "validation_balanced_accuracy": rt.confusion(rt.score_logistic(model, Xva) >= threshold, yva)["balanced_accuracy"],
                      "baseline": {"C": bC, "validation_auc_by_C": bTable, "validation_auc": rt.auc(rt.score_logistic(bmodel, Xva[:, base_cols]), yva), "operating_threshold": bthreshold},
                      "model": {k: (v.tolist() if hasattr(v, "tolist") else v) for k, v in final.items()}, "baseline_model": {k: (v.tolist() if hasattr(v, "tolist") else v) for k, v in bfinal.items()}})
        freeze["tasks"][task] = block
        print(task, {k: block[k] for k in ("train_positives", "validation_positives", "selection_method", "C", "validation_auc")}, flush=True)
    freeze["builder_sha256"] = {"train_script": sha(Path(__file__)), "pure_functions": sha(ROOT / "backend/app/ml/regime_tasks.py")}
    FREEZE.write_bytes((json.dumps(clean(freeze), indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False) + "\n").encode("utf-8"))
    (PHASE15 / "regime_tasks_selection_freeze.sha256").write_text(sha(FREEZE) + "  regime_tasks_selection_freeze.json\n", encoding="ascii")
    print("regime-task selection freeze written", sha(FREEZE))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
