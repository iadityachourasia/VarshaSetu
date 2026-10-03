"""Write the signed unseal record for the single 2022 test of the geography-aware follow-up (protocol v3, docs/132). Write-once.

It records the project owner's message verbatim and the sha256 of every file that defines the test (protocols, selection freezes, models, feature files, scoring
code, IMD file). It is written BEFORE any 2022 observation value is read, and scripts/score_geoaware_followup_2022.py refuses to run unless every hash still matches.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PHASE11 = ROOT / "backend/app/evidence_data/phase11"
TARGET = PHASE11 / "geoaware_followup_unseal_record.json"

FILES = {
    "protocol_v1": "backend/app/evidence_data/phase11/geoaware_followup_protocol_v1.json",
    "protocol_v2": "backend/app/evidence_data/phase11/geoaware_followup_protocol_v2.json",
    "protocol_v3": "backend/app/evidence_data/phase11/geoaware_followup_protocol_v3.json",
    "selection_freeze_v1": "backend/app/evidence_data/phase11/geoaware_followup_selection_freeze.json",
    "selection_freeze_v2": "backend/app/evidence_data/phase11/geoaware_followup_selection_freeze_v2.json",
    "selection_freeze_v3": "backend/app/evidence_data/phase11/geoaware_followup_selection_freeze_v3.json",
    "development_summary": "backend/app/evidence_data/phase11/geoaware_followup_development_summary.json",
    "corpus_v2_protocol": "backend/app/evidence_data/phase10/corpus_v2_protocol.json",
    "corpus_v2_evidence_manifest": "backend/app/evidence_data/phase10/corpus_v2_manifest.json",
    "static_geography": "backend/app/evidence_data/phase7/static_geography_v1.json",
    "features_2022_X": "data/operational_derived/v2/features/2022/sealed_forecast_only/deterministic/X.npy",
    "features_2022_pixel_index": "data/operational_derived/v2/features/2022/sealed_forecast_only/deterministic/pixel_index.npy",
    "features_2022_cases": "data/operational_derived/v2/features/2022/sealed_forecast_only/deterministic/cases.json",
    "features_2022_year_manifest": "data/operational_derived/v2/features/2022/sealed_forecast_only/year_manifest.json",
    "features_generation_manifest": "data/operational_derived/v2/features/feature_generation_manifest_v1.json",
    "imd_2022_file": "experiments/recent_historical/imd_v2/RF25_ind2022_rfp25.nc",
    "scoring_script": "scripts/score_geoaware_followup_2022.py",
    "code_geoaware_followup": "backend/app/ml/geoaware_followup.py",
    "code_geoaware_followup_scoring": "backend/app/ml/geoaware_followup_scoring.py",
    "code_zone_verification": "backend/app/ml/zone_verification.py",
    "code_geoaware_v1_helpers": "backend/app/ml/geoaware.py",
}
for version in ("v2", "v3"):
    for arm in ("B0", "B1", "B0Z", "B1Z"):
        FILES[f"model_{version}_{arm}"] = f"experiments/geoaware_followup_{version}/models/{arm}.json"


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def main() -> None:
    if TARGET.exists():
        raise SystemExit("an unseal record already exists; it is write-once")
    hashes = {}
    for name, relative in FILES.items():
        path = ROOT / relative
        if not path.is_file():
            raise SystemExit(f"missing file for the unseal record: {relative}")
        hashes[name] = {"path": relative, "sha256": sha(path)}
    for version in ("v2", "v3"):                                   # the freezes must already record 2022 as sealed
        freeze = json.loads((PHASE11 / f"geoaware_followup_selection_freeze_{version}.json").read_text(encoding="utf-8"))
        if freeze["sealed_test"]["opened"] is not False:
            raise SystemExit(f"selection freeze {version} does not record 2022 as sealed")
    features_freeze = json.loads((ROOT / FILES["features_generation_manifest"]).read_text(encoding="utf-8"))
    if features_freeze["observation_values_opened"]["2022"] is not False:
        raise SystemExit("the feature manifest does not record 2022 observations as unopened")
    record = {
        "schema": "geoaware-followup-unseal-record-v1", "year": 2022,
        "written_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "written_before_any_2022_observation_value_was_read": True,
        "owner_message": {"verbatim": "do all of three perfectly", "date": "2026-10-03",
                          "in_reply_to": ("docs/131 section 'Decisions for the project owner': (1) run the one-shot 2022 test as frozen, (2) draft protocol v3 aligning the selection criterion, "
                                          "(3) stop and report"),
                          "interpretation": ("treated as authorising all three in the only coherent order, because 2022 can be opened once: freeze v3 including its selection, open 2022 once and "
                                             "score both frozen candidate sets together under the Bonferroni rule of protocol v3, then report every result. This record is the signed form of "
                                             "the second step.")},
        "what_is_authorised": ["one scoring of Raw and every unique selected model of selection freezes v2 and v3 on 2022", "the pre-registered decision rule P1 to P4 with 97.5 percent intervals",
                               "a written-once result file labelled 'INDEPENDENT TEST: first use of this year'"],
        "what_is_not_authorised": ["scoring the frozen M1 to M4 (decision 5 stays no)", "any retuning, reselection or second scoring after the result", "publication of IMD values or anything that can reconstruct them (rights unresolved, D2)"],
        "disclosed_before_opening": ["both protocol changes C1 and C2 were made after earlier tables were seen (docs/131, docs/132)",
                                     "on development evidence the v2 candidate does not clearly beat its control on the primary quantity; the v3 candidate was selected by the aligned rule",
                                     "the scoring code was rehearsed on the development year 2021 (in-sample, writing outside the repository); the rehearsal reproduced an independent 2021 Raw verification exactly and found one bug before this record was written"],
        "hashes": hashes,
        "rule": "scripts/score_geoaware_followup_2022.py refuses to run unless every hash above matches, including the scoring script's own"}
    TARGET.write_text(json.dumps(record, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    (PHASE11 / "geoaware_followup_unseal_record.sha256").write_text(sha(TARGET) + "  geoaware_followup_unseal_record.json\n", encoding="ascii")
    print("unseal record sha256", sha(TARGET), "listing", len(hashes), "hashes")


if __name__ == "__main__":
    main()
