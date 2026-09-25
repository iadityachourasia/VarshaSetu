"""Generate missing Phase 1F counters without rewriting completed replay artifacts."""

from __future__ import annotations

import csv
import hashlib
import json
import os
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.app.data.monthly_qc import ENSEMBLE_MEMBERS, PRODUCT_WINDOWS
from backend.app.data.seasonal_corpus import seasonal_initializations
from scripts.data.replay_canonical_2019_jjas import decode_member, method_diagnostics


OUTPUT = ROOT / "data/manifests/phase1f/2019-JJAS/reconstruction_diagnostics.csv"
REPLAY = ROOT / "data/manifests/phase1f/2019-JJAS/reconstruction_replay.csv"


def diagnose_initialization(stamp: str) -> list[dict]:
    period = f"{stamp[:4]}-{stamp[4:6]}"
    source_path = ROOT / f"data/manifests/phase1e/{period}/daily/source_{stamp}.json"
    source_manifest = json.loads(source_path.read_text(encoding="utf-8"))
    rows = []
    for member in ENSEMBLE_MEMBERS:
        messages, _ = decode_member(source_manifest, member)
        for product, (start, end) in PRODUCT_WINDOWS.items():
            for method, minimal in (("A", False), ("B", True)):
                result = method_diagnostics(messages, start, end, minimal=minimal)
                rows.append({
                    "initialization": stamp,
                    "product": product,
                    "member": member,
                    "method": method,
                    "subtraction_operations": result["subtraction_count"],
                    "segments": result["segment_count"],
                    "negative_intermediate_cells": result["negative_intermediate_cells"],
                    "packing_bound_violations": result["packing_bound_violations"],
                    "admission_policy_violations": result["admission_policy_violations"],
                    "justified_normalized_cells": result["justified_normalized_cells"],
                    "raw_final_negative_cells": result["raw_final_negative_cells"],
                    "post_policy_final_negative_cells": result["normalized_final_negative_cells"],
                    "raw_final_sha256": result["raw_final_sha256"],
                    "post_policy_final_sha256": result["normalized_final_sha256"],
                    "source_manifest": source_path.relative_to(ROOT).as_posix(),
                })
    return rows


def main() -> None:
    with REPLAY.open(newline="", encoding="utf-8") as handle:
        replay_rows = list(csv.DictReader(handle))
    replay = {
        (row["initialization"], row["product"], row["member"]): row
        for row in replay_rows
    }
    stamps = [item.strftime("%Y%m%d%H") for item in seasonal_initializations(2019)]
    rows = []
    # Six workers leave CPU/UI headroom and remain far below the RAM policy cap.
    with ProcessPoolExecutor(max_workers=6) as executor:
        for stamp, result in zip(stamps, executor.map(diagnose_initialization, stamps)):
            rows.extend(result)
            print(f"diagnosed {stamp}", flush=True)
    rows.sort(key=lambda row: (
        row["initialization"], list(PRODUCT_WINDOWS).index(row["product"]),
        ENSEMBLE_MEMBERS.index(row["member"]), row["method"],
    ))
    if len(rows) != 3660:
        raise ValueError(f"expected 3,660 method diagnostics, found {len(rows)}")
    disagreements = []
    for row in rows:
        key = (row["initialization"], row["product"], row["member"])
        expected = replay[key][f"method_{row['method'].lower()}_status"]
        derived = "PASS" if int(row["admission_policy_violations"]) == 0 else "FAIL"
        if expected != derived:
            disagreements.append({"key": key, "method": row["method"], "expected": expected, "derived": derived})
    if disagreements:
        raise ValueError(f"diagnostic/replay status disagreement: {disagreements[:5]}")
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    temporary = OUTPUT.with_suffix(".csv.partial")
    with temporary.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    os.replace(temporary, OUTPUT)
    digest = hashlib.sha256(OUTPUT.read_bytes()).hexdigest()
    summary = {
        "artifact": OUTPUT.relative_to(ROOT).as_posix(),
        "sha256": digest,
        "rows": len(rows),
        "cases": len(rows) // 2,
        "methods_per_case": 2,
        "cache_only": True,
        "network_calls": 0,
        "status_agreement_with_completed_replay": True,
    }
    summary_path = OUTPUT.with_name("reconstruction_diagnostics_manifest.json")
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2, sort_keys=True), flush=True)


if __name__ == "__main__":
    main()
