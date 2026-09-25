"""Resume the authorized 2017/2018 JJAS canonical acquisition month by month."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.app.data.cache import sha256_file
from scripts.data.acquire_monthly_pilot import run


VERSION = "varshasetu-gefs12r-imd025-jjas-2000-2019-v2"
IMD_HASHES = {
    2017: "49786e2d2b661c5d3bcfb3ffd90385c1133ec27a8a04bf272ff2df5029106a9c",
    2018: "26bd53aeb2d6f3f7d39516c41606db005dede474906b33462d1a0caef69cd6ec",
}


def completed(year: int, month: int) -> bool:
    root = ROOT / f"data/manifests/phase2a/{year}-{month:02d}"
    collection_path = root / "monthly_collection_manifest.json"
    execution_paths = sorted(root.glob("execution_*.json"))
    if not collection_path.exists() or not execution_paths:
        return False
    collection = json.loads(collection_path.read_text(encoding="utf-8"))
    executions = [json.loads(path.read_text(encoding="utf-8")) for path in execution_paths]
    return (
        collection.get("dataset_version") == VERSION
        and collection.get("reconstruction_method") == "canonical_v2"
        and collection.get("observed_initializations") == collection.get("expected_initializations")
        and any(
            execution.get("collection_manifest_sha256") == sha256_file(collection_path)
            for execution in executions
        )
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--start-year", type=int, choices=(2017, 2018), default=2017)
    parser.add_argument("--start-month", type=int, choices=(6, 7, 8, 9), default=6)
    args = parser.parse_args()
    for year in (2017, 2018):
        for month in (6, 7, 8, 9):
            if (year, month) < (args.start_year, args.start_month):
                continue
            if completed(year, month):
                print(f"[{year}-{month:02d}] verified completed; skipping", flush=True)
                continue
            print(f"[{year}-{month:02d}] acquisition starting", flush=True)
            run(
                ROOT / f"data/raw/observations/imd/{year}/RF25_ind{year}_rfp25.nc",
                ROOT / "data",
                cache_only=False,
                year=year,
                month=month,
                phase_id="phase2a",
                network_workers=6,
                reconstruction_method="canonical_v2",
                dataset_version=VERSION,
                raw_phase="phase2a",
                imd_source_manifest=f"data/manifests/phase2a/sources/imd_rf25_{year}.json",
                expected_imd_sha256=IMD_HASHES[year],
                access_date="2026-09-22",
            )
            if not completed(year, month):
                raise RuntimeError(f"{year}-{month:02d} did not finalize consistently")
            print(f"[{year}-{month:02d}] acquisition finalized", flush=True)


if __name__ == "__main__":
    main()
