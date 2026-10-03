"""Does the 2021-07-21 change in the NOAA 0.25 degree rainfall file layout coincide with a change in forecast-only rainfall QC?

Reads only forecast-side source-QC checkpoints (no observation, model or score). Writes docs/artifacts/corpus2_layout_change_qc.json.
Honest scope: this compares QC pass rates on either side of one date; it cannot say why the layout changed.
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

from scipy.stats import fisher_exact

ROOT = Path(__file__).resolve().parents[1]
CHECK = ROOT / "experiments/recent_historical/corpus2_payload_acquisition_v1/checkpoints"
BOUNDARY = "20210721"
MEMBERS = ("c00", "p01", "p02", "p03", "p04")


def tally(year: int, lo: str, hi: str) -> dict:
    cases = Counter()
    fails = Counter()
    for path in sorted((CHECK / str(year)).glob("2*.json")):
        day = path.stem
        if not (lo <= day <= hi):
            continue
        for case in json.loads(path.read_text(encoding="utf-8"))["cases"]:
            cases["n"] += 1
            for member in MEMBERS:
                block = case["rainfall_by_member"][member]
                cases[f"{member}_pass"] += block["status"] == "PASS"
                if block["status"] != "PASS":
                    reason = (block.get("reason") or "unknown").split(":")[1].strip()[:40] if ":" in (block.get("reason") or "") else (block.get("reason") or "unknown")
                    fails[reason[:30]] += 1
    return {"cases": cases["n"], "pass": {m: cases[f"{m}_pass"] for m in MEMBERS}, "top_failure_reasons": fails.most_common(4)}


def main() -> None:
    before = tally(2021, "20210601", "20210720")
    after = tally(2021, BOUNDARY, "20211003")
    control_before = tally(2022, "20220601", "20220720")
    control_after = tally(2022, "20220721", "20221003")
    out = {"boundary_date": BOUNDARY, "before": before, "on_or_after": after, "fisher_exact": {},
           "seasonal_control_2022_same_calendar_split": {"before_jul21": control_before, "on_or_after_jul21": control_after, "pass_rate_c00": {
               "before": round(control_before["pass"]["c00"] / control_before["cases"], 3), "after": round(control_after["pass"]["c00"] / control_after["cases"], 3)}, "fisher_exact_by_member": {}}}
    for member in MEMBERS:
        t = [[control_before["pass"][member], control_before["cases"] - control_before["pass"][member]], [control_after["pass"][member], control_after["cases"] - control_after["pass"][member]]]
        out["seasonal_control_2022_same_calendar_split"]["fisher_exact_by_member"][member] = {"pass_rate_before": round(t[0][0] / control_before["cases"], 3), "pass_rate_after": round(t[1][0] / control_after["cases"], 3), "p_value": round(float(fisher_exact(t)[1]), 4)}
    for member in MEMBERS:
        table = [[before["pass"][member], before["cases"] - before["pass"][member]], [after["pass"][member], after["cases"] - after["pass"][member]]]
        odds, p = fisher_exact(table)
        out["fisher_exact"][member] = {"table_pass_fail_before_after": table, "pass_rate_before": round(before["pass"][member] / before["cases"], 3),
                                      "pass_rate_after": round(after["pass"][member] / after["cases"], 3), "p_value": round(float(p), 4)}
    out["scope"] = "forecast-side QC flags only; 2021 is a development year and 2022 is the sealed test year (only forecast-side QC flags are read, no observation, model or score); correlation in time, not a cause"
    target = ROOT / "docs/artifacts/corpus2_layout_change_qc.json"
    target.write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(out, indent=1)[:2500])


if __name__ == "__main__":
    main()
