"""Freeze the reforecast study protocol v1 (docs/142): the heavy-rain model study (PS-R05) and the regime-detection tasks (PS-R03), BEFORE any observation or label is read for any year.

Run once, after the forecast-side corpus exists for 2000-2016 (it reads no observation). Writes backend/app/evidence_data/phase15/reforecast_study_protocol_v1.json and its .sha256 sidecar. The protocol pins
the hash of every forecast-side file and of the rule modules, so a later change to any of them is detected. A change needs a new protocol version.
"""

from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.app.ml import reforecast_study as rs  # noqa: E402

OUT = ROOT / "backend/app/evidence_data/phase15"
PROTOCOL = OUT / "reforecast_study_protocol_v1.json"
PROC = ROOT / "data/processed/reforecast_control_v1"
MODULES = ["backend/app/ml/reforecast_study.py", "backend/app/ml/regime_labels_reanalysis.py", "backend/app/ml/regime_validation.py", "backend/app/ml/regime_tasks.py", "backend/app/ml/wd_indicator.py",
           "scripts/build_reforecast_forecast_side.py", "scripts/build_reforecast_pairs.py", "scripts/build_regime_task_data.py"]


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def canonical_sha(path: Path) -> str:
    """Hash of a text file with line endings normalised, so a CRLF checkout reproduces the same value."""
    return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def main() -> int:
    if PROTOCOL.exists():
        raise SystemExit("protocol v1 is already frozen; a change needs a new version")
    OUT.mkdir(parents=True, exist_ok=True)
    forecast_side, totals = {}, {"included": 0, "excluded": 0}
    for year in range(2000, 2017):
        folder = PROC / str(year)
        cases = json.loads((folder / "cases.json").read_text(encoding="utf-8"))
        if cases["observation_read"] is not False or not (folder / "X_full.npy").exists():
            raise SystemExit(f"forecast-side corpus for {year} is missing or not observation-free")
        included = sum(1 for c in cases["cases"] if c["status"] == "INCLUDED")
        forecast_side[str(year)] = {"cases_json_sha256": sha(folder / "cases.json"), "X_full_sha256": sha(folder / "X_full.npy"), "regime_X_sha256": sha(folder / "regime_X.npy"),
                                    "included_cases": included, "excluded_cases": len(cases["cases"]) - included}
        totals["included"] += included
        totals["excluded"] += len(cases["cases"]) - included
    grid = rs.configurations()
    protocol = {
        "schema": "reforecast-study-protocol-v1", "status": "APPROVED_FOR_EXECUTION", "frozen_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"), "no_observation_read": True,
        "purpose": ("Two pre-registered questions on an independent, much longer GEFSv12 reforecast corpus (control member, June to September, 2000-2016): (R05) does a corrected forecast improve on Raw GEFS for rainfall error, "
                    "heavy rain and very-heavy rain on years no earlier model or experiment has seen, and does regime-awareness add value over the best non-regime model; (R03) can regime states (active, break, "
                    "low/depression, western disturbance, coastal/orographic rain) be detected from the forecast alone against labels that are independent of the forecast-time rules."),
        "populations": {"train_years": list(rs.TRAIN_YEARS), "validation_years": list(rs.VALIDATION_YEARS), "sealed_test_years": list(rs.SEALED_YEARS),
                        "note": "The sealed years 2014-2016 are untouched: no earlier model, selection or experiment of this project used them. 2017-2019 (Track A) and 2021-2025 (Track B) are NOT used here. "
                                "The reforecast lineage (GEFSv12 retrospective) is never pooled with the operational track.",
                        "labels": {"train": "training years 2000-2011", "validation": "validation years 2012-2013: development evidence, used for selection", "sealed": "POST-UNSEAL SEALED TEST 2014-2016: first use of these years"}},
        "data": {"forecast": "GEFSv12 reforecast control member c00, 00 UTC, Days 1-3 rainfall (canonical 24 h reconstruction on the 49x49 target grid) and six atmospheric fields, built by scripts/build_reforecast_forecast_side.py",
                 "observation": "IMD RF25 daily rainfall, official 0.25 degree files, hash-pinned (regime_validation_protocol_v1 climatology file hashes); IMD files stay local, only aggregates are tracked",
                 "reanalysis": "ERA5 geopotential from the public WeatherBench2 store (1.5 degree, 6-hourly, 13 levels), used ONLY to label past days; never a forecast input (AGENTS.md section 3.5)",
                 "forecast_side_files": forecast_side, "forecast_side_totals": totals, "static_geography_sha256": sha(ROOT / "backend/app/evidence_data/phase7/static_geography_v1.json")},
        "r05": {
            "models": {"M0": "Raw GEFS control", "global_arms": {"B0": {"features": rs.ARMS["B0"], "role": "non-regime event-weighted/global control"}, "B1": {"features": rs.ARMS["B1"], "role": "adds the eight static geography columns"}},
                       "regime_arms": {"R_hard": "M3-style hard routing to three regime experts", "R_soft": "M4-style probability-weighted mixture",
                                       "construction": "pseudo-labelling rule fitted on the training cases (Phase 2A method), logistic classifier on the 12 regime features fitted on the training cases, three experts trained with the SELECTED B0 configuration, "
                                                       "an expert with fewer than 100000 training rows falls back to the global B0 model"}},
            "model_spec": {"family": "xgboost", "fixed": {"learning_rate": 0.05, "subsample": 0.9, "colsample_bytree": 0.9, "reg_lambda": 2.0, "min_child_weight": 5}, "tree_method": "hist", "device": "cpu",
                           "n_jobs": 12, "seed": 26080, "tweedie_variance_power": 1.5, "output": "prediction clipped at zero", "gpu": "not used (the earlier equivalence gate was not met)",
                           "note": "the same fixed settings as the geography-aware follow-up protocol"},
            "grid": {"size": len(grid), "configurations": grid, "event_weight": "w = min(cap, 1 + y / 64.5) from the observed rainfall of a training row; cap None means no weighting", "sample_weights_at_inference": "never"},
            "selection": {"data": "validation years only, models trained on the training years only", "eligible": "RMSE no worse than Raw, heavy CSI at least Raw's, |bias| <= 1.5 mm, heavy frequency bias <= 2.0, very-heavy frequency bias <= 3.0",
                          "choice": "highest mean of heavy and very-heavy CSI; ties go to the lower RMSE, then the earlier grid position; none eligible means no candidate and the study reports that",
                          "refit": "the selected configuration of each arm is refit on training plus validation years (2000-2013) before the sealed test; nothing else changes"},
            "sealed_test": {"unit": "initialization date (whole dates resampled, 2000 resamples, seed 26080)", "intervals": "95 percent for RMSE, 97.5 percent (Bonferroni over the two thresholds) for heavy and very-heavy CSI differences",
                            "comparisons": ["each selected global arm (B0, B1) against Raw", "R_soft and R_hard against B0 (does regime-awareness add value)"],
                            "decision": {"IMPROVES_RMSE": "RMSE difference against Raw negative with the 95 percent interval excluding zero", "IMPROVES_HEAVY": "heavy-rain CSI difference positive with the 97.5 percent interval excluding zero",
                                         "IMPROVES_VERY_HEAVY": "very-heavy CSI difference positive with the 97.5 percent interval excluding zero", "BIAS_OK": "|bias| <= 1.5 mm and heavy and very-heavy frequency bias within the selection limits",
                                         "tiers": "FULL = all three improvements and BIAS_OK; RMSE_AND_HEAVY; PARTIAL; NONE", "regime_adds_value": "heavy CSI improves over B0 with the 97.5 percent interval excluding zero and the RMSE difference interval upper bound is at most 0.2 mm"},
                            "support_gate": "at least 30 observed event pairs per threshold in the sealed test, otherwise that threshold is reported as insufficient support and cannot count as an improvement",
                            "also_reported": ["by lead day", "by sealed year", "by pseudo-regime", "FSS is not part of this study"]},
            "coverage_mapping": {"IMPROVEMENT-VS-RAW_becomes_IMPLEMENTED_only_if": "a selected arm reaches tier FULL on the sealed test; otherwise the row stays PARTIAL and states which of the three improvements were and were not shown",
                                 "regime_wording": "regime-awareness is claimed to add skill only if regime_adds_value is true"}},
        "r03": {
            "tasks": {"ACTIVE": "IMD core-zone rainfall active spell (July and August; 1981-2011 climatology; +1 standard deviation; three days)", "BREAK": "same, -1 standard deviation",
                      "LOW_DEPRESSION": "ERA5 850 hPa geostrophic vorticity box maximum, 15-25 N, 70-95 E, at or above the training-years 85th percentile, on at least two consecutive days",
                      "WESTERN_DISTURBANCE": "ERA5 500 hPa geostrophic vorticity box maximum, 20-36.5 N, 60-80 E, same rule",
                      "COASTAL_OROGRAPHIC": "IMD mean rainfall over the Ghats-coast zone cells at or above the training-years 85th percentile (June to September days)"},
            "label_nature": "objective, rule-based, reanalysis- or IMD-derived labels in the style of the published trackers; NOT the published classifications and NOT an expert analysis; the percentile labels are relative by construction",
            "label_time": "the valid day of the case: initialization date plus the lead day",
            "features": ["the 12 forecast regime features", "forecast western-disturbance indicator (500 hPa geostrophic vorticity over 25-38 N, 62-78 E from the forecast height)", "coastal cross-barrier forcing index (docs/137)", "lead hours", "day-of-year sine and cosine"],
            "classifier": {"family": "standardised logistic regression, one per task", "C_grid": [0.01, 0.1, 1.0, 10.0], "selection": "validation-year AUC (training years only for fitting)",
                           "operating_point": "the validation-year threshold that maximises balanced accuracy", "refit": "training plus validation years", "baseline": "the same model on lead hours, day-of-year sine and cosine only (a climatology)"},
            "sealed_test": {"unit": "initialization date (2000 resamples, seed 26080)", "metrics": ["AUC", "balanced accuracy", "recall", "precision"], "intervals": "95 percent",
                            "support_gate": "at least 30 positive and 30 negative cases in the sealed test per task, otherwise insufficient support and no verdict",
                            "tiers": {"VALIDATED": "AUC lower bound above 0.5 and the AUC difference over the climatology baseline has a lower bound above zero", "USEFUL": "VALIDATED and AUC at least 0.70", "NOT_VALIDATED": "otherwise"}},
            "coverage_mapping": {"REGIME-CLASSIFIER": "IMPLEMENTED only if ACTIVE, BREAK and LOW_DEPRESSION are all VALIDATED", "REGIME-WESTERN-DISTURBANCE": "IMPLEMENTED only if WESTERN_DISTURBANCE is VALIDATED",
                                 "REGIME-COASTAL-OROGRAPHIC": "IMPLEMENTED only if COASTAL_OROGRAPHIC is VALIDATED", "otherwise": "the row stays PARTIAL and says which tasks were not validated",
                                 "wording": "validated against objective labels, never against an expert analysis; the western-disturbance label compares a forecast trough with a reanalysis trough, so it largely verifies the forecast height field"}},
        "forbidden": ["reading any sealed-year observation, label or reanalysis value before the unseal record exists", "using 2014-2016 for fitting, tuning, threshold choice, feature choice or selection",
                      "changing the grid, rules, thresholds or tiers after any validation result is seen without a new protocol version", "pooling with the 2017-2019 reforecast years or the operational years",
                      "using ERA5 or any observation as a model input", "claiming skill from the validation years as final evidence"],
        "code_hashes": {m: canonical_sha(ROOT / m) if (ROOT / m).exists() else None for m in MODULES},
        "approval": {"approved_by": "project owner", "record": "owner instruction of 2026-10-03: 'now try to close those two requirements download search data that is needed and proceed and implement both requirement properly', with the data scope confirmed in chat: "
                                                             "GEFSv12 reforecast control 2000-2016 with 2014-2016 sealed, and ERA5 1.5 degree geopotential 2000-2023",
                     "note": "Interpretation of a general instruction: the sealing, the decision rules and the unseal of 2014-2016 are recorded as the owner's authorised plan; the owner may withdraw it. The measured reforecast download (about 40 GB) was larger than the "
                             "20-25 GB estimate given when the scope was confirmed."}}
    PROTOCOL.write_text(json.dumps(protocol, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    (OUT / "reforecast_study_protocol_v1.sha256").write_text(sha(PROTOCOL) + "  reforecast_study_protocol_v1.json\n", encoding="ascii")
    print("protocol sha256", sha(PROTOCOL), totals)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
