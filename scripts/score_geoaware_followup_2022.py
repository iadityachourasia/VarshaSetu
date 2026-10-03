"""The single, pre-registered test of the geography-aware follow-up on the sealed year 2022 (protocol v3, docs/132).

ONE event, write-once. The script refuses to run unless geoaware_followup_unseal_record.json exists and every hash it lists (protocols, selection freezes, models,
feature files, scoring code, IMD file) matches the file on disk, including this script's own hash. Only after those checks does it open the 2022 IMD values.
It scores Raw and every unique selected model of selection freezes v2 and v3 together, then applies the pre-registered decision rule (pure code in
backend/app/ml/geoaware_followup_scoring.py, tested on synthetic data) with Bonferroni 97.5 percent paired whole-case intervals, and writes the result once.

    python scripts/score_geoaware_followup_2022.py

It never retunes, reselects or re-scores. The frozen M1 to M4 are NOT scored (decision 5 stays no).

    python scripts/score_geoaware_followup_2022.py --rehearsal OUTPUT.json

The rehearsal runs the IDENTICAL code path on the DEVELOPMENT year 2021 (in-sample for the models, so its numbers are meaningless as a result), needs no unseal record,
never touches 2022 and writes only to the path given (outside the repository). It exists so that a runtime bug cannot first appear after 2022 is opened.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from xgboost import XGBRegressor  # noqa: E402

from backend.app.ml import geoaware_followup as gf  # noqa: E402
from backend.app.ml import geoaware_followup_scoring as sc  # noqa: E402
from backend.app.ml import zone_verification as zv  # noqa: E402

PHASE7 = ROOT / "backend/app/evidence_data/phase7"
PHASE10 = ROOT / "backend/app/evidence_data/phase10"
PHASE11 = ROOT / "backend/app/evidence_data/phase11"
UNSEAL = PHASE11 / "geoaware_followup_unseal_record.json"
RESULT = PHASE11 / "geoaware_followup_test_2022.json"
FEATURES_ROOT = ROOT / "data/operational_derived/v2/features"
FEATURE_DIRS = {2022: "2022/sealed_forecast_only", 2021: "2021/development"}
PAYLOAD = ROOT / "experiments/recent_historical/corpus2_payload_acquisition_v1"
IMD_DIR = ROOT / "experiments/recent_historical/imd_v2"
PRODUCTS = ("day1_24h", "day2_24h", "day3_24h")
HEAVY = 64.5
SCHEMA = "geoaware-followup-test-2022-v1"
LABEL = "INDEPENDENT TEST: first use of this year"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def clean(value):
    if isinstance(value, dict):
        return {(k if isinstance(k, str) else "|".join(str(x) for x in k)): clean(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [clean(v) for v in value]
    if isinstance(value, (np.floating, float)):
        return None if not np.isfinite(value) else float(value)
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.bool_,)):
        return bool(value)
    return value


def verify_unseal_record() -> dict:
    """Refuse to continue unless the unseal record exists and every listed hash matches. Nothing about 2022 observations has been read yet."""
    if RESULT.exists():
        raise SystemExit("the 2022 test result already exists: the test is one-shot and write-once")
    if not UNSEAL.is_file():
        raise SystemExit("no unseal record: 2022 stays sealed")
    record = json.loads(UNSEAL.read_text(encoding="utf-8"))
    if (PHASE11 / "geoaware_followup_unseal_record.sha256").read_text(encoding="ascii").split()[0] != sha256_file(UNSEAL):
        raise SystemExit("the unseal record differs from its sidecar")
    if record["written_before_any_2022_observation_value_was_read"] is not True or not record["owner_message"]["verbatim"]:
        raise SystemExit("the unseal record does not carry the owner authorisation")
    for name, entry in record["hashes"].items():
        path = ROOT / entry["path"]
        if not path.is_file() or sha256_file(path) != entry["sha256"]:
            raise SystemExit(f"hash mismatch against the unseal record: {name}")
    if record["hashes"]["scoring_script"]["sha256"] != sha256_file(Path(__file__)):
        raise SystemExit("this script differs from the one named in the unseal record")
    return record


def main(rehearsal: Path | None = None) -> None:
    year = 2021 if rehearsal else 2022
    if rehearsal:
        if rehearsal.resolve().is_relative_to(ROOT.resolve()):
            raise SystemExit("a rehearsal must not write inside the repository")
        record = None
    else:
        record = verify_unseal_record()
    FEATURES = FEATURES_ROOT / FEATURE_DIRS[year]
    IMD_FILE = IMD_DIR / f"RF25_ind{year}_rfp25.nc"
    protocol = json.loads((PHASE11 / "geoaware_followup_protocol_v3.json").read_text(encoding="utf-8"))
    freezes = {"v2": json.loads((PHASE11 / "geoaware_followup_selection_freeze_v2.json").read_text(encoding="utf-8")),
               "v3": json.loads((PHASE11 / "geoaware_followup_selection_freeze_v3.json").read_text(encoding="utf-8"))}
    if freezes["v2"]["sealed_test"]["opened"] is not False or freezes["v3"]["sealed_test"]["opened"] is not False:
        raise SystemExit("a selection freeze does not record 2022 as sealed")

    # unique selected models, identified by (arm, grid index, model hash)
    models: dict[str, dict] = {}
    membership: dict[str, dict[str, str]] = {"v2": {}, "v3": {}}
    for version, freeze in freezes.items():
        folder = ROOT / f"experiments/geoaware_followup_{version}/models"
        for arm, block in freeze["selection"].items():
            chosen = block["selected"]
            if chosen is None:
                continue
            label = f"{arm}#{chosen['grid_index']}"
            path = folder / f"{arm}.json"
            if sha256_file(path) != chosen["model_sha256"]:
                raise SystemExit(f"model hash differs from its freeze: {version} {arm}")
            if label in models and models[label]["sha256"] != chosen["model_sha256"]:
                raise SystemExit(f"two different models carry the label {label}")
            models[label] = {"arm": arm, "grid_index": chosen["grid_index"], "config": chosen["config"], "path": path, "sha256": chosen["model_sha256"]}
            membership[version][arm] = label
    names = ["M0"] + sorted(models)

    # forecast side (already sealed-safe) and input gate
    x = np.load(FEATURES / "deterministic/X.npy")
    pixel = np.load(FEATURES / "deterministic/pixel_index.npy").astype(np.int64)
    cases = json.loads((FEATURES / "deterministic/cases.json").read_text(encoding="utf-8"))
    geography = json.loads((PHASE7 / "static_geography_v1.json").read_text(encoding="utf-8"))
    masks = zv.zone_masks(geography["fields"]["zone"])
    static_fields = {n: np.array([[np.nan if v is None else v for v in row] for row in geography["fields"][n]], dtype=np.float64).ravel() for n in gf.STATIC_FEATURES}
    static = gf.static_columns(static_fields, pixel)
    raw_rain = x[:, 0].astype(np.float64)
    for case in cases:       # the Raw forecast feature must be the stored, QC-passed control rainfall of the case
        day = case["case_id"].split("_")[0]
        qc = np.load(PAYLOAD / f"rainfall_qc/{year}" / day / f"{case['product']}_c00.npy").ravel()
        rows = slice(case["row_start"], case["row_start"] + case["row_count"])
        if not np.array_equal(raw_rain[rows].astype(np.float32), qc[pixel[rows]].astype(np.float32)):
            raise SystemExit(f"input gate failed: Raw feature differs from the QC rainfall array for {case['case_id']}")
    predictions = {}
    for label, meta in models.items():
        model = XGBRegressor()
        model.load_model(str(meta["path"]))
        predictions[label] = np.maximum(0.0, model.predict(gf.assemble(x, static, meta["arm"]))).astype(np.float64)

    # unseal: only now are the 2022 observation values opened
    from backend.app.data_sources.imd_rainfall import load_imd_day
    corpus_protocol = json.loads((PHASE10 / "corpus_v2_protocol.json").read_text(encoding="utf-8"))
    if sha256_file(IMD_FILE) != corpus_protocol["observation_source"]["sha256"][str(year)]:
        raise SystemExit(f"the IMD {year} file differs from the protocol")
    per_case, valid_counts, outside = [], [], 0
    case_lead = []
    for case in cases:
        init = date.fromisoformat(case["initialization_utc"][:10])
        field = load_imd_day(IMD_FILE, init + timedelta(days=PRODUCTS.index(case["product"]) + 1), south=10, north=22, west=68, east=80)
        obs_flat = np.full(zv.GRID_CELLS, np.nan)
        rows = slice(case["row_start"], case["row_start"] + case["row_count"])
        cells = pixel[rows]
        observed = field.rainfall_mm.ravel()
        ok = field.valid_mask.ravel() & np.isfinite(observed) & (observed >= 0)
        paired = ok[cells]
        outside += int(np.count_nonzero(ok & ~masks["ALL"]))
        obs_flat[cells[paired]] = observed[cells[paired]]
        forecasts = {}
        for label in names:
            source = raw_rain if label == "M0" else predictions[label]
            fc = np.full(zv.GRID_CELLS, np.nan)
            fc[cells[paired]] = source[rows][paired]
            forecasts[label] = fc
        valid_counts.append(int(paired.sum()))
        case_lead.append(case["product"])
        if (np.isfinite(obs_flat) & ~masks["ALL"]).any():     # IMD valid cells that lie outside the terrain-derived footprint: cannot be assigned to a zone
            keep = np.isfinite(obs_flat) & masks["ALL"]
            obs_flat = np.where(keep, obs_flat, np.nan)
            forecasts = {k: np.where(keep, v, np.nan) for k, v in forecasts.items()}
        per_case.append(zv.case_stats(obs_flat, forecasts, masks, names=zv.ZONES))
    stack = np.stack(per_case)
    totals = stack.sum(axis=0)
    cell_counts = {zone: int(masks[zone].sum()) for zone in zv.ZONES}
    pooled = {label: {zone: zv.metrics(totals[zi, mi]) for zi, zone in enumerate(zv.ZONES)} for mi, label in enumerate(names)}
    support = zv.support(stack, cell_counts)

    sets = {"v3_primary": {"candidate": membership["v3"]["B1"], "comparator": membership["v3"]["B0"]},
            "v2_secondary": {"candidate": membership["v2"]["B1"], "comparator": membership["v2"]["B0"]}}
    sensitivity = [(membership[v]["B1Z"], membership[v]["B1"]) for v in ("v3", "v2")] + [(membership[v]["B0Z"], membership[v]["B0"]) for v in ("v3", "v2")]
    versus_raw = [(label, "M0") for label in sorted(models)]
    pairs = []
    for pair in [(s["candidate"], s["comparator"]) for s in sets.values()] + sensitivity + versus_raw:
        if pair[0] != pair[1] and pair not in pairs:
            pairs.append(pair)
    statistic = sc.difference_statistic_factory(pairs)
    boot_decision = zv.paired_bootstrap(stack, names, statistic=statistic, repeats=2000, seed=26080, level=sc.DECISION_LEVEL)
    boot_95 = zv.paired_bootstrap(stack, names, statistic=statistic, repeats=2000, seed=26080)
    decisions = {}
    for key, pair in sets.items():
        a, b = pair["candidate"], pair["comparator"]
        if a == b:
            decisions[key] = {"status": "NOT_A_COMPARISON", "reason": "candidate and comparator are the same model", **pair}
        else:
            decisions[key] = {**pair, **sc.decide(a, b, pooled[a], pooled["M0"], boot_decision, support)}
    by_lead = {}
    shown = ("M0", sets["v3_primary"]["candidate"], sets["v3_primary"]["comparator"], sets["v2_secondary"]["candidate"])
    for lead in PRODUCTS:
        sel = np.array([p == lead for p in case_lead])
        lead_totals = stack[sel].sum(axis=0)
        by_lead[lead] = {"cases": int(sel.sum()),
                         "models": {label: {zone: zv.metrics(lead_totals[zv.ZONES.index(zone), names.index(label)]) for zone in ("ALL", sc.ZONE)} for label in dict.fromkeys(shown)}}
    primary = decisions["v3_primary"]
    claim = ("REHEARSAL_NO_CLAIM" if rehearsal else
             "ADDS_VALUE_ON_AN_INDEPENDENT_YEAR" if primary.get("adds_value") is True else
             "UNEVALUABLE" if primary.get("status") == "UNEVALUABLE" else "NO_INDEPENDENT_EVIDENCE_OF_ADDED_VALUE")
    result = {
        "schema": SCHEMA, "label": LABEL if not rehearsal else "REHEARSAL on development year 2021: in-sample for the models, NOT A RESULT",
        "year": year, "evidence_role": "INDEPENDENT_TEST_FIRST_USE_OF_2022" if not rehearsal else "REHEARSAL_NOT_A_RESULT",
        "protocol_v3_sha256": sha256_file(PHASE11 / "geoaware_followup_protocol_v3.json"), "unseal_record_sha256": None if rehearsal else sha256_file(UNSEAL),
        "run_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "cases": len(cases), "paired_cells_per_case": {"min": min(valid_counts), "max": max(valid_counts)}, "imd_valid_cells_outside_footprint": outside,
        "models": {label: {"arm": m["arm"], "grid_index": m["grid_index"], "config": m["config"], "model_sha256": m["sha256"]} for label, m in models.items()},
        "candidate_sets": sets, "pooled": pooled, "support": support,
        "bootstrap": {"repeats": 2000, "seed": 26080, "note": "paired whole-case, optimistic (cells in a case and consecutive days are correlated)",
                      "decision_level_0975": boot_decision, "descriptive_level_095": boot_95},
        "decisions": decisions, "multiplicity": "two candidate sets on one year: Bonferroni, each interval two-sided at 97.5 percent (alpha 0.025)",
        "sensitivity_pairs": [{"a": a, "b": b} for a, b in sensitivity], "by_lead": by_lead,
        "claim": claim, "claim_wording": {"ADDS_VALUE_ON_AN_INDEPENDENT_YEAR": "the primary (v3) candidate satisfied P1 to P4 at the stated level on the independent year",
                                           "NO_INDEPENDENT_EVIDENCE_OF_ADDED_VALUE": "no independent evidence that geography-aware features improve on the pipeline without them",
                                           "UNEVALUABLE": "the Ghats-coast zone failed the support gate on the test year",
                                           "REHEARSAL_NO_CLAIM": "a rehearsal on a development year is in-sample for the models and supports no claim"}[claim],
        "limits": ["single test year", "one training window of three development years", "forecast eligibility about half of the scheduled cases", "bootstrap intervals are optimistic",
                   "historical replay, not warning skill", "frozen M1 to M4 were not scored (decision 5 stayed no)", "IMD redistribution rights are unresolved"]}
    encoded = (json.dumps(clean(result), indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode("utf-8")
    if rehearsal:
        rehearsal.write_bytes(encoded)
        print("REHEARSAL (development year 2021, in-sample, not a result) written to", rehearsal)
    else:
        RESULT.write_bytes(encoded)
        (PHASE11 / "geoaware_followup_test_2022.sha256").write_text(sha256_file(RESULT) + "  geoaware_followup_test_2022.json\n", encoding="ascii")
    print("claim:", claim)
    for key, d in decisions.items():
        print(key, d.get("status"), "adds_value", d.get("adds_value"), {k: d.get(k) for k in ("P1_zone_heavy_csi_beats_comparator_975", "P2_overall_rmse_within_tolerance", "P3_gating_guardrails_G1_G2_G4")})
    if not rehearsal:
        print("result sha256", sha256_file(RESULT))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--rehearsal", type=Path, default=None, help="run the identical path on development year 2021 and write only to this path (outside the repository)")
    args = parser.parse_args()
    main(args.rehearsal)
