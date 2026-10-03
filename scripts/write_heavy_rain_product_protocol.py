"""Freeze the protocol for showing the frozen heavy-rain bundle (B1) in the 2019 map and district products (docs/143), BEFORE any prediction is computed for the product.

    python scripts/write_heavy_rain_product_protocol.py --owner-message "<verbatim owner instruction>"

The protocol records what will be computed, the gates that must pass, the labels and the limits. It refuses to run once an output exists, so it cannot be rewritten after seeing a result.
No free text below contains a typed number: figures are read from the frozen evidence at serving time.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PHASE15 = ROOT / "backend/app/evidence_data/phase15"
PHASE17 = ROOT / "backend/app/evidence_data/phase17"
PROTOCOL = PHASE17 / "heavy_rain_integration_protocol_v1.json"
MODELS = ROOT / "experiments/reforecast_study_v1/models"


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def main(message: str) -> int:
    if PROTOCOL.exists() or any(PHASE17.glob("heavy_rain_b1_*")):
        raise SystemExit("the protocol or an output already exists; it is write-once")
    PHASE17.mkdir(parents=True, exist_ok=True)
    record = json.loads((PHASE15 / "reforecast_confirmation_unseal_record.json").read_text(encoding="utf-8"))
    for name, digest in record["model_files_sha256"].items():
        if sha(MODELS / name) != digest:
            raise SystemExit(f"model file {name} differs from the confirmation record")
    exceedance = json.loads((PHASE15 / "reforecast_exceedance_freeze.json").read_text(encoding="utf-8"))
    protocol = {
        "schema": "heavy-rain-integration-protocol-v1",
        "written_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "written_before_any_product_prediction_was_computed": True,
        "authorisation": {"owner_message": {"verbatim": message, "date": "2026-10-03"},
                          "interpretation": "Display the already-frozen B1 bundle of the reforecast study (regression with its one-parameter mean-error shift, and the two exceedance classifiers with their frozen thresholds) in the existing Track A map and district products as an additional, clearly labelled layer next to the frozen global model. Nothing is refitted, reselected or retuned, and no frozen product artifact is changed. The owner may withdraw this interpretation."},
        "scope": {"track": "A", "year": 2019, "cases": "exactly the cases of the existing product, with exactly its valid cells",
                  "layers": ["B1 corrected rainfall (shifted regression)", "heavy-rain classifier score and decision at the frozen threshold", "very-heavy classifier score and decision at the frozen threshold"],
                  "surfaces": ["Forecast Explorer corrected panel (model choice)", "Extreme Rain map (source choice)", "District Intelligence map and table (model choice)"]},
        "bundle": {"confirmation_record_sha256": sha(PHASE15 / "reforecast_confirmation_unseal_record.json"), "round_one_evidence_sha256": sha(PHASE15 / "reforecast_r05_test.json"),
                   "confirmation_evidence_sha256": sha(PHASE15 / "reforecast_r05_confirmation.json"), "exceedance_freeze_sha256": sha(PHASE15 / "reforecast_exceedance_freeze.json"),
                   "model_files_sha256": record["model_files_sha256"], "shift_source": "pooled mean error of the selected B1 regression on the sealed years, read from the round-one evidence file",
                   "thresholds_source": "the frozen exceedance selection, read from the exceedance freeze", "builder_sha256_in_freeze": exceedance["builder_sha256"]},
        "gates": [
            "every model file hash equals the confirmation record",
            "every product case has exactly one corpus case with the same initialization and lead",
            "the cells scored for a case are exactly the valid cells of the product case",
            "recomputing the confirmatory pooled results with the same prediction function reproduces the frozen evidence: exceedance hits, misses and false alarms for both classifiers, and the pooled mean error and RMSE of the shifted regression",
            "the slice of the shifted regression for the product year equals the per-year entry of the confirmation evidence",
            "no rainfall value is negative or undefined on a valid cell, and scores lie between zero and one",
        ],
        "labels": {"track_a_2019_role": "TRACK_A_2019_CONSUMED_FINAL_TEST__POST_HOC_EXPLORATORY_ANALYSIS_OF_THE_COMPLETED_2019_FINAL_TEST",
                   "bundle_role": "REFORECAST_CONFIRMATORY_TEST_2017_2019",
                   "wording": "Descriptive display of frozen predictions. The product year was part of the confirmatory years and had been used by earlier Track A experiments; nothing is selected or tuned on it."},
        "must_state_wherever_shown": [
            "the classifier output is a score from a class-weighted model with a validation-fixed threshold, not a calibrated probability",
            "the decision at the threshold over-forecasts heavy and very-heavy events (frequency bias above one in the frozen evidence)",
            "the bundle was built on the reforecast control member; it is a different model version from the operational years and has not been tested there",
            "the first round failed the mean-error guardrail and the shift was read from that round; the second round is confirmatory, not untouched",
            "regime-aware routing is not part of this bundle and was not shown to add value",
        ],
        "not_authorised": ["refitting or reselecting anything", "changing the shift or a threshold", "applying the bundle to any other year or to the operational years", "calling the scores calibrated probabilities", "pooling with another track"],
    }
    PROTOCOL.write_bytes((json.dumps(protocol, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode("utf-8"))
    PROTOCOL.with_suffix(".sha256").write_text(sha(PROTOCOL) + f"  {PROTOCOL.name}\n", encoding="ascii")
    print("protocol written", sha(PROTOCOL))
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--owner-message", required=True)
    raise SystemExit(main(parser.parse_args().owner_message))
