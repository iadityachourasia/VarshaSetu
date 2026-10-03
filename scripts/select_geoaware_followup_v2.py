"""Select and fit the geography-aware follow-up under protocol v2 (docs/131): G1, G2 and G4 gate, G3 is reported.

Development only. Reuses the out-of-fold results of the v1 run (verified by hash: predictions do not depend on which guardrails gate), applies the v2
gating mechanically with the pure rule, refits each selected configuration on all 562 development cases, saves the models locally (gitignored) and writes the
tracked v2 selection freeze. It never reads 2022. After it, opening the 2022 observations needs a separate signed owner record.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import xgboost  # noqa: E402

from backend.app.ml import geoaware_followup as gf  # noqa: E402

PHASE11 = ROOT / "backend/app/evidence_data/phase11"
PROTOCOL_V1 = PHASE11 / "geoaware_followup_protocol_v1.json"
PROTOCOL_V2 = PHASE11 / "geoaware_followup_protocol_v2.json"
FREEZE_V2 = PHASE11 / "geoaware_followup_selection_freeze_v2.json"
CHECKPOINT = ROOT / "experiments/geoaware_followup_v1/cv_results.jsonl"
MODELS = ROOT / "experiments/geoaware_followup_v2/models"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def load_train_module():
    spec = importlib.util.spec_from_file_location("train_geoaware_followup", ROOT / "scripts/train_geoaware_followup.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main() -> None:
    if FREEZE_V2.exists():
        raise SystemExit("v2 selection freeze already exists: refusing to refit (write-once). A change needs a new protocol version.")
    if (PHASE11 / "geoaware_followup_protocol_v2.sha256").read_text(encoding="ascii").split()[0] != sha256_file(PROTOCOL_V2):
        raise SystemExit("protocol v2 hash differs from its sidecar")
    protocol = json.loads(PROTOCOL_V2.read_text(encoding="utf-8"))
    if protocol["selection"]["gating_guardrails"] != list(gf.GUARDRAILS_V2):
        raise SystemExit("the code's gating set differs from protocol v2")
    if sha256_file(CHECKPOINT) != protocol["selection"]["cross_validation_reuse"]["checkpoint_sha256"]:
        raise SystemExit("the reused cross-validation checkpoint differs from the one recorded in protocol v2")
    train = load_train_module()
    v1 = json.loads(PROTOCOL_V1.read_text(encoding="utf-8"))
    train.verify_inputs(v1)                                   # the development inputs are identical in v1 and v2
    data = train.load_development()
    X, y, year_of_row = data["X"], data["y"], data["year"]
    raw = {year: gf.pooled_metrics(y[year_of_row == year], X[year_of_row == year, 0])["heavy"]["csi"] for year in gf.DEVELOPMENT_YEARS}
    records = {}
    for line in CHECKPOINT.read_text(encoding="utf-8").splitlines():
        if line.strip():
            r = json.loads(line)
            records[(r["arm"], r["grid_index"])] = r
    configs = gf.configurations()
    if len(records) != 64:
        raise SystemExit("the checkpoint must hold all 64 configurations")
    MODELS.mkdir(parents=True, exist_ok=True)
    spec = protocol["model"]
    selection = {}
    for arm in gf.ARMS:
        results = [{**records[(arm, i)], "by_year": {int(k): v for k, v in records[(arm, i)]["by_year"].items()}} for i in range(len(configs))]
        chosen = gf.select_configuration(results, raw, gating=gf.GUARDRAILS_V2)
        if chosen is None:
            selection[arm] = {"selected": None, "reason": "no configuration passed G1, G2 and G4 in every held-out year"}
            continue
        model = train.fit(chosen["config"], spec, gf.assemble(X, data["static"], arm), y)
        path = MODELS / f"{arm}.json"
        model.save_model(str(path))
        weights = gf.event_weights(y, spec["event_weight"]["cap"]) if chosen["config"]["weights"] == "capped_event" else None
        g3 = {str(year): chosen["by_year"][year]["very_heavy"]["frequency_bias"] for year in gf.DEVELOPMENT_YEARS}
        selection[arm] = {"selected": {"grid_index": chosen["grid_index"], "config": chosen["config"], "pooled_out_of_fold": chosen["pooled"],
                                       "by_year": {str(k): v for k, v in chosen["by_year"].items()},
                                       "guardrails_by_year": {str(year): gf.guardrails_for_year(chosen["by_year"][year], raw[year]) for year in gf.DEVELOPMENT_YEARS},
                                       "g3_reported_very_heavy_frequency_bias_by_year": g3, "g3_passes_in_every_year": all(v is not None and v >= gf.G3_MIN_VERY_HEAVY_FREQUENCY_BIAS for v in g3.values()),
                                       "model_sha256": sha256_file(path), "features": len(gf.ARMS[arm]),
                                       "event_weight_effective_sample_size": None if weights is None else round(float(weights.sum() ** 2 / (weights ** 2).sum()), 1)}}
    table = []
    for arm in gf.ARMS:
        for i in range(len(configs)):
            r = records[(arm, i)]
            flags = r["guardrails_by_year"]
            table.append({"arm": arm, "grid_index": i, **r["config"], "pooled_rmse_mm": r["pooled"]["rmse_mm"], "guardrails_by_year": flags,
                          "eligible_v2": all(flags[y][g] for y in flags for g in gf.GUARDRAILS_V2)})
    freeze = {"schema": "geoaware-followup-selection-freeze-v2", "protocol_sha256": sha256_file(PROTOCOL_V2), "supersedes_protocol_sha256": sha256_file(PROTOCOL_V1),
              "development": {"years": list(gf.DEVELOPMENT_YEARS), "cases": data["cases"], "rows": int(len(y)), "raw_heavy_csi_by_year": {str(k): v for k, v in raw.items()},
                              "input_sha256": v1["development_data_sha256"]},
              "cross_validation_checkpoint_sha256": sha256_file(CHECKPOINT),
              "builder_sha256": {"select_script": sha256_file(Path(__file__)), "train_script": sha256_file(ROOT / "scripts/train_geoaware_followup.py"),
                                 "pure_functions": sha256_file(ROOT / "backend/app/ml/geoaware_followup.py")},
              "libraries": {"xgboost": xgboost.__version__, "numpy": np.__version__}, "selection": selection, "all_configurations": table,
              "sealed_test": {"year": 2022, "opened": False, "note": "no 2022 feature, target or observation was read; unsealing needs a separate signed owner record"},
              "note": "Post-hoc protocol change C1 (G3 reported, not gating), decided after the v1 table was seen; see protocol v2 post_hoc_disclosure. Written before any 2022 value is opened."}
    FREEZE_V2.write_bytes((json.dumps(freeze, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode("utf-8"))
    (PHASE11 / "geoaware_followup_selection_freeze_v2.sha256").write_text(sha256_file(FREEZE_V2) + "  geoaware_followup_selection_freeze_v2.json\n", encoding="ascii")
    for arm, block in selection.items():
        c = block["selected"]
        print(arm, "NO CANDIDATE" if c is None else f"selected #{c['grid_index']} {c['config']} pooled rmse {c['pooled_out_of_fold']['rmse_mm']:.3f} G3 passes in every year: {c['g3_passes_in_every_year']}")
    print("v2 selection freeze written", sha256_file(FREEZE_V2))


if __name__ == "__main__":
    main()
