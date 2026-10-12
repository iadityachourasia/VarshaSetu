"""Build a resumable, forecast-only 2026 JJAS GEFS corpus one month at a time.

The frozen protocol forbids observations, inference and model selection. Only
QC-passing leads receive feature arrays. Source byte ranges are retained in
the immutable hash-receipted NOAA cache. Failed cycles stop the month, so a
missing date can never be silently reported as complete.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import sys
import time
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import numpy as np  # noqa: E402

from backend.app.live import pipeline  # noqa: E402

PROTOCOL = ROOT / "data/manifests/research_pilot/2026_forecast_corpus_protocol_v1.json"
CORPUS = ROOT / "data/processed/gefs_2026_forecast_only_v1"
WINDOWS = {name: list(rule["window"]) for name, rule in pipeline.LEADS.items()}


def sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def protocol() -> tuple[dict, str]:
    digest = sha(PROTOCOL)
    if PROTOCOL.with_suffix(".sha256").read_text(encoding="ascii").split()[0] != digest:
        raise ValueError("2026 forecast-only corpus protocol hash mismatch")
    value = json.loads(PROTOCOL.read_text(encoding="utf-8"))
    if value["role"] != "2026_TRACK_B_TEST_CANDIDATE_FORECAST_SIDE_ONLY" or value["observation_read"] is not False or value["model_inference"] is not False or value["training_or_selection"] is not False:
        raise ValueError("forecast-only corpus role changed")
    if value["rainfall_windows_hours"] != WINDOWS or value["selected_messages_per_complete_cycle"] != len(pipeline.required_messages()):
        raise ValueError("forecast-only corpus differs from the canonical live rule")
    return value, digest


def dates_for_month(month: str, settings: dict) -> list[str]:
    if not re.fullmatch(r"2026(06|07|08|09)", month):
        raise ValueError("month must be one of 202606 through 202609")
    start = date.fromisoformat(f"{month[:4]}-{month[4:]}-01")
    end = date.fromisoformat(f"{settings['end_cycle'][:4]}-{settings['end_cycle'][4:6]}-{settings['end_cycle'][6:]}")
    dates = []
    current = start
    while current.month == start.month and current <= end:
        dates.append(current.strftime("%Y%m%d"))
        current += timedelta(days=1)
    return dates


def verify_case(directory: Path, expected_protocol_hash: str, *, source_root: Path = pipeline.SOURCE_CACHE) -> dict:
    manifest_path = directory / "manifest.json"
    sidecar = directory / "manifest.sha256"
    if not manifest_path.is_file() or not sidecar.is_file() or sidecar.read_text(encoding="ascii").split()[0] != sha(manifest_path):
        raise ValueError(f"forecast-only case manifest integrity failure: {directory}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest["protocol_sha256"] != expected_protocol_hash or manifest["cycle"] != directory.name or manifest["observation_read"] is not False or manifest["model_inference"] is not False:
        raise ValueError(f"forecast-only case identity failure: {directory}")
    for name, digest in manifest["array_sha256"].items():
        path = directory / name
        if not path.is_file() or sha(path) != digest:
            raise ValueError(f"forecast-only case array integrity failure: {path}")
    for key, digest in manifest.get("source_sha256", {}).items():
        family, hour, variable = key.split(":")
        path = source_root / directory.name / family / f"f{int(hour):03d}_{variable}.grib2"
        receipt = path.with_name(path.name + ".receipt.json")
        if not path.is_file() or not receipt.is_file() or sha(path) != digest:
            raise ValueError(f"forecast-only source integrity failure: {path}")
        metadata = json.loads(receipt.read_text(encoding="utf-8"))
        if metadata["sha256"] != digest or metadata["byte_size"] != path.stat().st_size:
            raise ValueError(f"forecast-only source receipt integrity failure: {receipt}")
    return manifest


def publish_case(root: Path, cycle: str, manifest: dict, arrays: dict[str, np.ndarray]) -> Path:
    directory = root / cycle
    if directory.exists():
        raise FileExistsError(f"forecast-only case is immutable: {directory}")
    root.mkdir(parents=True, exist_ok=True)
    stage = root / f".stage-{cycle}-{uuid4().hex}"
    stage.mkdir()
    try:
        hashes = {}
        for name, array in sorted(arrays.items()):
            if not re.fullmatch(r"(?:X|regime)_day[123]_24h\.npy", name):
                raise ValueError(f"unexpected forecast feature artifact: {name}")
            value = np.asarray(array)
            if value.dtype not in (np.float32, np.float64) or not np.isfinite(value).all():
                raise ValueError(f"invalid forecast feature artifact: {name}")
            path = stage / name
            np.save(path, value, allow_pickle=False)
            hashes[name] = sha(path)
        record = {**manifest, "array_sha256": hashes}
        value = json.dumps(record, indent=2, sort_keys=True, allow_nan=False) + "\n"
        (stage / "manifest.json").write_text(value, encoding="utf-8", newline="\n")
        (stage / "manifest.sha256").write_text(hashlib.sha256(value.encode("utf-8")).hexdigest() + "\n", encoding="ascii")
        if directory.exists():
            raise FileExistsError(f"forecast-only case is immutable: {directory}")
        # On Windows, a just-written staging directory may briefly be held by
        # filesystem indexing or scanning. Retry only a transient sharing/
        # access denial; the immutable destination check remains in force.
        for attempt in range(5):
            if directory.exists():
                raise FileExistsError(f"forecast-only case is immutable: {directory}")
            try:
                stage.rename(directory)
                break
            except PermissionError as error:
                if getattr(error, "winerror", None) != 5 or attempt == 4:
                    raise
                time.sleep(0.05 * (2 ** attempt))
    except Exception:
        shutil.rmtree(stage)
        raise
    return directory


def build_case(cycle: str, settings: dict, protocol_hash: str, *, root: Path = CORPUS) -> dict:
    target = root / cycle
    if target.exists():
        return verify_case(target, protocol_hash)
    source = pipeline.CachedHttpSource(cycle)
    plan = source.plan()
    planned = sum(row["bytes"] for row in plan)
    if len(plan) != settings["selected_messages_per_complete_cycle"] or planned > settings["per_cycle_transfer_cap_bytes"]:
        raise ValueError(f"{cycle}: selected-message count or transfer guard failed")
    root.mkdir(parents=True, exist_ok=True)
    if shutil.disk_usage(root).free < settings["minimum_free_disk_bytes"]:
        raise ValueError("50 GiB free-space guard failed")
    try:
        decoded = pipeline.decode_cycle(source, cycle)
    except pipeline.CycleRefused as error:
        if "no lead passed the canonical rainfall reconstruction" not in str(error):
            raise
        decoded = {"rainfall": {}, "failed_products": {"all": str(error)}, "atmosphere": {}}
    source_hashes = {}
    for family, hour, variable in pipeline.required_messages():
        message = source.get(family, hour, variable)  # verified cache hit after decoding
        source_hashes[f"{family}:{hour}:{variable}"] = message.sha256
    features = pipeline.build_features(decoded["rainfall"], decoded["atmosphere"]) if decoded["rainfall"] else {}
    arrays = {}
    for product, values in features.items():
        X = values["X"]
        if X.shape != (2401, settings["expected_feature_columns"]):
            raise ValueError(f"{cycle} {product}: unexpected feature matrix shape")
        arrays[f"X_{product}.npy"] = X
        arrays[f"regime_{product}.npy"] = np.asarray(values["regime"], dtype=np.float64)
    record = {"schema": settings["schema"], "cycle": cycle, "created_at_utc": datetime.now(timezone.utc).isoformat(),
              "protocol_sha256": protocol_hash, "role": settings["role"], "source": settings["source"],
              "observation_read": False, "model_inference": False, "training_or_selection": False,
              "planned_selected_bytes": planned, "source_sha256": source_hashes,
              "products_passing_qc": sorted(features), "withheld_products": decoded["failed_products"],
              "status": "FEATURES_READY" if features else "NO_ELIGIBLE_LEAD", "rainfall_windows_hours": WINDOWS}
    publish_case(root, cycle, record, arrays)
    return record


def transient_source_error(error: Exception) -> bool:
    """Retry availability failures only; never retry a scientific or hash gate."""
    if isinstance(error, OSError):
        return True
    return isinstance(error, pipeline.CycleRefused) and any(
        f"HTTP {status}" in str(error) for status in (429, 500, 502, 503, 504)
    )


def build_case_with_retries(cycle: str, settings: dict, protocol_hash: str, *, root: Path = CORPUS) -> dict:
    for attempt, delay in enumerate((10, 30, 60, None), 1):
        try:
            return build_case(cycle, settings, protocol_hash, root=root)
        except (pipeline.CycleRefused, OSError) as error:
            if delay is None or not transient_source_error(error):
                raise
            print(json.dumps({"cycle": cycle, "transient_source_error": str(error),
                              "attempt": attempt, "retry_after_seconds": delay}), flush=True)
            time.sleep(delay)
    raise AssertionError("unreachable retry state")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--month", required=True, help="202606, 202607, 202608 or 202609")
    parser.add_argument("--confirm-download", action="store_true")
    args = parser.parse_args()
    settings, protocol_hash = protocol()
    dates = dates_for_month(args.month, settings)
    if not args.confirm_download:
        print(json.dumps({"month": args.month, "cycles": len(dates), "protocol_sha256": protocol_hash,
                          "message": "No network request made. Pass --confirm-download to acquire selected ranges."}))
        return 0
    for i, cycle in enumerate(dates, 1):
        result = build_case_with_retries(cycle, settings, protocol_hash)
        print(json.dumps({"progress": f"{i}/{len(dates)}", "cycle": cycle, "status": result["status"],
                          "passing_leads": result["products_passing_qc"], "withheld": result["withheld_products"]}), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
