"""Write the unseal record that authorises reading the sealed years 2014-2016 once (docs/142). It is written BEFORE any sealed observation, label or reanalysis value is read, and says so only if that is true.

    python scripts/write_reforecast_unseal_record.py --owner-message "<verbatim owner instruction>"

The record pins the protocol, both selection freezes and every frozen model file. Opening the sealed years afterwards is limited to pairing, labelling and scoring those frozen models once.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PHASE15 = ROOT / "backend/app/evidence_data/phase15"
RECORD = PHASE15 / "reforecast_unseal_record.json"
PROC = ROOT / "data/processed/reforecast_control_v1"
TASKS = ROOT / "data/processed/regime_tasks_v1"
MODELS = ROOT / "experiments/reforecast_study_v1/models"
SEALED = (2014, 2015, 2016)


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--owner-message", required=True)
    a = p.parse_args()
    if RECORD.exists():
        raise SystemExit("an unseal record already exists")
    leaked = [str(f) for y in SEALED for f in list((PROC / str(y)).glob("y_mm.npy")) + list((PROC / str(y)).glob("pairs.json")) + list(TASKS.glob(f"labels_{y}.json")) + list(TASKS.glob(f"tasks_Y_{y}.npy"))]
    if leaked:
        raise SystemExit(f"sealed-year observation or label files already exist: {leaked}")
    files = {"protocol": PHASE15 / "reforecast_study_protocol_v1.json", "selection_freeze": PHASE15 / "reforecast_selection_freeze.json", "regime_tasks_freeze": PHASE15 / "regime_tasks_selection_freeze.json", "exceedance_freeze": PHASE15 / "reforecast_exceedance_freeze.json"}
    for name, path in files.items():
        if not path.exists() or path.with_suffix(".sha256").read_text(encoding="ascii").split()[0] != sha(path):
            raise SystemExit(f"{name} is missing or differs from its sidecar")
    freeze = json.loads(files["selection_freeze"].read_text(encoding="utf-8"))
    models = {n: sha(MODELS / n) for n in sorted(x.name for x in MODELS.iterdir())} if MODELS.exists() else {}
    for arm, block in freeze["models"].items():
        if arm != "regime_arms" and models.get(block["file"]) != block["sha256"]:
            raise SystemExit(f"model file {block['file']} differs from the selection freeze")
    for key, block in json.loads(files["exceedance_freeze"].read_text(encoding="utf-8"))["models"].items():
        if models.get(block["file"]) != block["sha256"]:
            raise SystemExit(f"model file {block['file']} differs from the exceedance freeze")
    record = {"schema": "reforecast-unseal-record-v1", "written_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"), "years": list(SEALED), "protocol_sha256": sha(files["protocol"]),
              "selection_freeze_sha256": sha(files["selection_freeze"]), "regime_tasks_freeze_sha256": sha(files["regime_tasks_freeze"]), "exceedance_freeze_sha256": sha(files["exceedance_freeze"]),
              "amendments_sha256": {n: sha(PHASE15 / n) for n in ("reforecast_protocol_v1_amendment_1.json", "reforecast_protocol_v1_amendment_2.json")}, "model_files_sha256": models,
              "written_before_any_sealed_observation_was_read": True,
              "owner_message": {"verbatim": a.owner_message, "date": "2026-10-03", "interpretation": "A general instruction to close the two partial requirements; the owner confirmed the data scope (reforecast 2000-2016 with 2014-2016 sealed) in chat. "
                                                                 "The decision to open the sealed years once, after the selections were frozen, is recorded as the owner's authorised plan and may be withdrawn."},
              "what_is_authorised": ["pairing the 2014-2016 forecast-side corpus with IMD", "labelling 2014-2016 days (IMD and ERA5) with the frozen thresholds", "scoring the frozen models and classifiers once", "writing the evidence files"],
              "what_is_not_authorised": ["retraining, re-selecting or changing any threshold, configuration or rule", "a second scoring run with different settings", "using 2014-2016 for any fitting"],
              "disclosed_before_opening": ["the validation results (2012-2013) were seen and used only for selection", "the selection freezes and models were written before this record", "the download was larger than estimated (measured about 40 GB against 20-25 GB)"]}
    RECORD.write_bytes((json.dumps(record, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode("utf-8"))
    (PHASE15 / "reforecast_unseal_record.sha256").write_text(sha(RECORD) + "  reforecast_unseal_record.json\n", encoding="ascii")
    print("unseal record written", sha(RECORD))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
