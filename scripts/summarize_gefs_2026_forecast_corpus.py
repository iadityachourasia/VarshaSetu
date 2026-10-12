"""Verify and seal a complete month of the forecast-only 2026 corpus."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts import build_gefs_2026_forecast_corpus as corpus

OUT = corpus.ROOT / "data/manifests/research_pilot"


def summary(month: str, *, root: Path = corpus.CORPUS) -> dict:
    settings, protocol_hash = corpus.protocol()
    dates = corpus.dates_for_month(month, settings)
    cases = []
    for cycle in dates:
        directory = root / cycle
        if not directory.is_dir():
            raise ValueError(f"forecast-only month is incomplete: {cycle} is missing")
        manifest = corpus.verify_case(directory, protocol_hash)
        cases.append({"cycle": cycle, "status": manifest["status"], "products_passing_qc": manifest["products_passing_qc"],
                      "products_withheld": [p for p in corpus.WINDOWS if p not in manifest["products_passing_qc"]],
                      "withheld_products": manifest["withheld_products"],
                      "planned_selected_bytes": manifest["planned_selected_bytes"],
                      "manifest_sha256": corpus.sha(directory / "manifest.json")})
    return {"schema": "varshasetu-2026-forecast-only-month-summary-v1", "month": month,
            "role": settings["role"], "protocol_sha256": protocol_hash,
            "observation_read": False, "model_inference": False, "training_or_selection": False,
            "cycle_count": len(cases), "products_passing_qc": {p: sum(p in row["products_passing_qc"] for row in cases) for p in corpus.WINDOWS},
            "products_withheld_qc": {p: sum(p in row["products_withheld"] for row in cases) for p in corpus.WINDOWS},
            "no_eligible_lead_cycles": sum(row["status"] == "NO_ELIGIBLE_LEAD" for row in cases),
            "planned_selected_bytes": sum(row["planned_selected_bytes"] for row in cases), "cases": cases,
            "interpretation": "Forecast-side acquisition and QC only. No observation, 2026 skill, independence, or model promotion claim."}


def write_once(month: str, value: dict, *, output: Path | None = None) -> Path:
    target = output or OUT / f"2026_forecast_month_{month}_v1.json"
    data = json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n"
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        if target.read_text(encoding="utf-8") != data or target.with_suffix(".sha256").read_text(encoding="ascii").split()[0] != corpus.sha(target):
            raise ValueError("frozen monthly forecast summary differs from current cases")
        return target
    with target.open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(data)
    target.with_suffix(".sha256").write_text(hashlib.sha256(data.encode("utf-8")).hexdigest() + "  " + target.name + "\n", encoding="ascii")
    return target


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--month", required=True)
    args = parser.parse_args()
    result = summary(args.month)
    path = write_once(args.month, result)
    print(json.dumps({"path": str(path), "cycle_count": result["cycle_count"],
                      "products_passing_qc": result["products_passing_qc"], "no_eligible_lead_cycles": result["no_eligible_lead_cycles"]}))


if __name__ == "__main__":
    main()
