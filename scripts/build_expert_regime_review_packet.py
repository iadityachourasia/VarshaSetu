"""Build a blinded, forecast-only JJAS case packet; no labels or rainfall outcomes are read.

The output is a handoff to meteorologists, not an expert-validation result.
Run from the repository root: python scripts/build_expert_regime_review_packet.py
"""

from __future__ import annotations

import csv
import hashlib
import json
import sys
from datetime import date, timedelta
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.app.ml.expert_regime_review import TASKS, select_cases  # noqa: E402

SOURCE = ROOT / "data/processed/reforecast_control_v1"
SOURCE_FREEZE = ROOT / "backend/app/evidence_data/phase15/reforecast_study_protocol_v1.json"
PROTOCOL = ROOT / "data/manifests/research_pilot/expert_regime_review_protocol_v1.json"
OUT = ROOT / "data/processed/expert_regime_review_v1"
MANIFEST = ROOT / "data/manifests/research_pilot/expert_regime_review_packet_v1.json"
YEARS = (2014, 2015, 2016)
FIELDS = (("forecast_u850", "850 hPa U (m/s)"), ("forecast_v850", "850 hPa V (m/s)"),
          ("forecast_q700", "700 hPa specific humidity (kg/kg)"), ("forecast_z500", "500 hPa height (m)"),
          ("forecast_mslp", "MSLP (Pa)"), ("forecast_pwat", "precipitable water (kg/m²)"))
LEADS = {"day1_24h": (3, 27, 24), "day2_24h": (27, 51, 48), "day3_24h": (51, 75, 72)}


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def verified_protocol() -> dict:
    if PROTOCOL.with_suffix(".sha256").read_text(encoding="ascii").split()[0] != sha(PROTOCOL):
        raise ValueError("review protocol sidecar mismatch")
    protocol = json.loads(PROTOCOL.read_text(encoding="utf-8"))
    if protocol["builder_sha256"] != sha(Path(__file__)):
        raise ValueError("builder differs from frozen review protocol")
    if protocol["sampling_module_sha256"] != sha(ROOT / "backend/app/ml/expert_regime_review.py"):
        raise ValueError("sampling module differs from frozen review protocol")
    if protocol["source_protocol_sha256"] != sha(SOURCE_FREEZE):
        raise ValueError("source protocol differs from review protocol")
    return protocol


def render_map(path: Path, x: np.ndarray) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    from backend.app.ml.geoaware import BASE_FEATURES

    fig, axes = plt.subplots(2, 3, figsize=(12, 7), constrained_layout=True)
    for ax, (name, title) in zip(axes.flat, FIELDS):
        values = np.asarray(x[:, BASE_FEATURES.index(name)], dtype=np.float64).reshape(49, 49)
        if not np.isfinite(values).all():
            raise ValueError(f"nonfinite forecast field {name}")
        image = ax.imshow(values, origin="lower", extent=(68, 80, 10, 22), interpolation="nearest", aspect="auto")
        ax.set(title=title, xlabel="longitude E", ylabel="latitude N")
        fig.colorbar(image, ax=ax, fraction=0.046, pad=0.04)
    fig.suptitle("GEFSv12 reforecast c00: forecast atmospheric fields only", fontsize=12)
    fig.savefig(path, dpi=100, metadata={"Software": "VarshaSetu review packet"})
    plt.close(fig)


def main() -> int:
    if MANIFEST.exists() or OUT.exists():
        raise SystemExit("review packet already exists: write-once; verify the existing artifact")
    protocol = verified_protocol()
    source_freeze = json.loads(SOURCE_FREEZE.read_text(encoding="utf-8"))
    if protocol["years"] != list(YEARS) or protocol["cases_per_year_month_lead"] != 2:
        raise ValueError("unexpected review population or sampling rule")
    all_cases, source_hashes = [], {}
    for year in YEARS:
        folder = SOURCE / str(year)
        path = folder / "cases.json"
        expected = source_freeze["data"]["forecast_side_files"][str(year)]
        for name, key in (("cases.json", "cases_json_sha256"), ("X_full.npy", "X_full_sha256")):
            if sha(folder / name) != expected[key]:
                raise ValueError(f"source hash mismatch {year}/{name}")
        source_hashes[str(year)] = {"cases_json_sha256": expected["cases_json_sha256"], "X_full_sha256": expected["X_full_sha256"]}
        source = json.loads(path.read_text(encoding="utf-8"))
        if source["observation_read"] is not False:
            raise ValueError("case source is not forecast-only")
        all_cases.extend(source["cases"])
    selected = select_cases(all_cases, per_stratum=2)
    if len(selected) != 72:
        raise ValueError(f"expected 72 balanced cases, got {len(selected)}")
    OUT.mkdir(parents=True)
    maps = OUT / "forecast_maps"
    maps.mkdir()
    records = []
    matrices = {y: np.load(SOURCE / str(y) / "X_full.npy", mmap_mode="r", allow_pickle=False) for y in YEARS}
    for case in selected:
        issue = date.fromisoformat(case["initialization"])
        start, end, atmos_hour = LEADS[case["product"]]
        x = matrices[issue.year][case["row"]]
        if x.shape != (2401, 22) or np.any(np.asarray(x[:, -1]) != atmos_hour):
            raise ValueError(f"feature row/lead mismatch: {case['case_id']}")
        image_path = maps / f"{case['case_id']}.png"
        render_map(image_path, x)
        records.append({"case_id": case["case_id"], "forecast_source": "NOAA GEFSv12 reforecast c00",
                        "source_track": "A_REFORECAST", "source_version": "GEFSv12 reforecast", "issue_utc": f"{issue.isoformat()}T00:00:00Z",
                        "atmosphere_valid_utc": f"{(issue + timedelta(hours=atmos_hour)).isoformat()}T00:00:00Z",
                        "lead_window_h": [start, end], "rain_valid_date_03_03_utc": (issue + timedelta(days=atmos_hour // 24)).isoformat(),
                        "region_id": "WEST_CENTRAL_INDIA_10_22N_68_80E", "forecast_fields_png": f"forecast_maps/{image_path.name}",
                        "forecast_fields_sha256": sha(image_path), "bulletin_inventory": [],
                        "review_scope": "JJAS central-western India; western disturbance requires additional broad-domain evidence and a separate winter corpus"})
    packet = {"schema": "expert-regime-review-packet-v1", "status": "AWAITING_INDEPENDENT_REVIEW",
              "protocol_sha256": sha(PROTOCOL), "builder_sha256": sha(Path(__file__)), "source_hashes": source_hashes,
              "selection": "2 SHA256(case_id)-ranked complete cases per year x JJAS month x lead; no outcome or detector score used",
              "case_count": len(records), "cases": records,
              "limitations": ["No bulletin documents or expert labels are included", "Map fields cover only 10-22 N, 68-80 E", "2014-2016 are consumed rainfall test years", "Western-disturbance rainfall claims require a separate winter corpus"]}
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST.write_text(json.dumps(packet, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
    MANIFEST.with_suffix(".sha256").write_text(f"{sha(MANIFEST)}  {MANIFEST.name}\n", encoding="ascii")
    fieldnames = ["case_id", "forecast_source", "source_version", "issue_utc", "lead_window_h", "region_id",
                  "reviewer_id", "annotation_utc", "rubric_version", "bulletin_issue_utc", "bulletin_evidence_uri_or_hash"]
    for task in TASKS:
        fieldnames += [task, f"{task}_rationale", f"{task}_evidence", f"{task}_uncertainty_reason"]
    with (OUT / "annotation_template.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames)
        writer.writeheader()
        for case in records:
            writer.writerow({"case_id": case["case_id"], "forecast_source": case["forecast_source"],
                             "source_version": case["source_version"], "issue_utc": case["issue_utc"],
                             "lead_window_h": f"{case['lead_window_h'][0]}-{case['lead_window_h'][1]}",
                             "region_id": case["region_id"], "rubric_version": "expert-regime-review-v1"})
    print(json.dumps({"case_count": len(records), "manifest_sha256": sha(MANIFEST), "local_map_dir": str(maps),
                      "annotation_template": str(OUT / "annotation_template.csv"), "expert_labels": 0}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
