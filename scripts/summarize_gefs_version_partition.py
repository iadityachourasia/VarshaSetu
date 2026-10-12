"""Forecast-only sensitivity strata around the *announced* June 2026 GEFS change.

This does not identify an actual model binary or establish equivalence to 2023.
It reads only sealed 2026 forecast-side manifests and feature-range warnings.
"""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "data/manifests/research_pilot"
OUT = BASE / "2026_gefs_announced_partition_v1.json"
MONTHS = ("202606", "202607", "202608", "202609")
LEADS = ("day1_24h", "day2_24h", "day3_24h")


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def sealed(path: Path) -> dict:
    if not path.is_file() or not path.with_suffix(".sha256").is_file():
        raise ValueError(f"missing sealed input: {path.name}")
    if path.with_suffix(".sha256").read_text(encoding="ascii").split()[0] != sha(path):
        raise ValueError(f"sealed input hash mismatch: {path.name}")
    return json.loads(path.read_text(encoding="utf-8"))


def partition(cycle: str, effective_utc: str) -> str:
    if len(cycle) != 8 or not cycle.isdigit():
        raise ValueError("cycle must be YYYYMMDD")
    issue = datetime.strptime(cycle, "%Y%m%d").replace(tzinfo=timezone.utc)
    effective = datetime.fromisoformat(effective_utc.replace("Z", "+00:00"))
    if effective.tzinfo is None:
        raise ValueError("effective time must be timezone aware")
    return "before_announced_change" if issue < effective else "after_announced_change"


def summarize(base: Path = BASE) -> dict:
    note_path = base / "2026_gefs_model_change_note_v1.json"
    note = sealed(note_path)
    effective = note["announced_effective_cycle_utc"]
    if effective != "2026-06-15T12:00:00Z":
        raise ValueError("unexpected announced transition time")
    year_path = base / "2026_forecast_jjas_year_v1.json"
    year = sealed(year_path)
    if year["observation_read"] is not False or year["cycle_count"] != 122:
        raise ValueError("forecast-only year identity mismatch")
    feature_path = base / "2026_jjas_feature_range_v1.json"
    features = sealed(feature_path)
    if features["cases"] != sum(year["products_passing_qc"].values()):
        raise ValueError("feature report and year seal differ")
    cycle_rows = []
    source_hashes = {p.name: sha(p) for p in (note_path, year_path, feature_path)}
    for month in MONTHS:
        path = base / f"2026_forecast_month_{month}_v1.json"
        report = sealed(path)
        expected_month = next((r for r in year["months"] if r["month"] == month), None)
        if expected_month is None or sha(path) != expected_month["manifest_sha256"] or report["month"] != month:
            raise ValueError(f"month seal differs from year seal: {month}")
        source_hashes[path.name] = sha(path)
        for case in report["cases"]:
            cycle = case["cycle"]
            if not cycle.startswith(month) or len(cycle) != 8:
                raise ValueError(f"cycle/month mismatch: {cycle}")
            daily_path = ROOT / "data/processed/gefs_2026_forecast_only_v1" / cycle / "manifest.json"
            if sha(daily_path) != case["manifest_sha256"]:
                raise ValueError(f"cycle manifest differs from month seal: {cycle}")
            passing = case["products_passing_qc"]
            withheld = case["products_withheld"]
            if sorted(passing + withheld) != sorted(LEADS):
                raise ValueError(f"incomplete lead accounting: {cycle}")
            cycle_rows.append({"cycle": cycle, "stratum": partition(cycle, effective), "passing": passing, "withheld": withheld})
    if len(cycle_rows) != 122 or len({r["cycle"] for r in cycle_rows}) != 122:
        raise ValueError("cycle accounting mismatch")
    warnings = features["dynamic_case_feature_warnings_over_5pct"]
    warned = {(w["cycle"], w["lead"]) for w in warnings}
    result = {}
    for label in ("before_announced_change", "after_announced_change"):
        rows = [r for r in cycle_rows if r["stratum"] == label]
        dates = {r["cycle"] for r in rows}
        passes = Counter(p for r in rows for p in r["passing"])
        withheld = Counter(p for r in rows for p in r["withheld"])
        result[label] = {"cycle_count": len(rows), "first_cycle": min(dates), "last_cycle": max(dates),
                         "strict_qc_passing": {p: passes[p] for p in LEADS},
                         "strict_qc_withheld": {p: withheld[p] for p in LEADS},
                         "no_eligible_lead_cycles": sum(not r["passing"] for r in rows),
                         "dynamic_feature_warning_case_count": sum(cycle in dates for cycle, _ in warned),
                         "dynamic_feature_warning_case_feature_count": sum(w["cycle"] in dates for w in warnings)}
    for lead in LEADS:
        if sum(result[k]["strict_qc_passing"][lead] for k in result) != year["products_passing_qc"][lead]:
            raise ValueError("partition passing count differs from year seal")
        if sum(result[k]["strict_qc_withheld"][lead] for k in result) != year["products_withheld_qc"][lead]:
            raise ValueError("partition withheld count differs from year seal")
    return {"schema": "varshasetu-2026-gefs-announced-partition-v1", "status": "ANNOUNCED_BOUNDARY_ONLY_ACTUAL_VERSION_UNCONFIRMED",
            "announced_effective_utc": effective, "cycle_hour_utc": 0, "source_hashes": source_hashes,
            "strata": result, "observation_read": False, "model_inference": False,
            "interpretation": "Calendar and forecast-QC sensitivity strata only. The change notice names three radiation fields, none selected here. Counts and feature warnings cannot prove actual implementation time, numerical equivalence to the 2023 training model, or forecast skill.",
            "evaluation_rule": "Preserve the frozen pooled primary comparison; report these pre/post strata without using 2026 observations to choose a model or cutoff."}


def main() -> None:
    report = summarize()
    value = json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + "\n"
    if OUT.exists():
        if OUT.read_text(encoding="utf-8") != value or sealed(OUT) != report:
            raise SystemExit("existing partition report differs: write-once")
        print("verified existing partition", sha(OUT))
        return
    with OUT.open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(value)
    OUT.with_suffix(".sha256").write_text(f"{sha(OUT)}  {OUT.name}\n", encoding="ascii")
    print(json.dumps({"sha256": sha(OUT), "strata": report["strata"]}, sort_keys=True))


if __name__ == "__main__":
    main()
