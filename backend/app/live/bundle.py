"""Immutable, hash-manifested result bundle of one experimental cycle (docs/139). Light on dependencies: the read-only API imports this module to verify and serve bundles.

Layout: ``<root>/<kind>/<YYYYMMDD>/manifest.json`` (+ ``manifest.sha256``) and one ``.npy`` per array. A bundle is written once; an existing one is never changed. ``kind`` is ``live`` for a cycle
fetched from NOAA and ``replay`` for a stored historical cycle pushed through the same path (pipeline proof, not a forecast).
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

SCHEMA = "live-cycle-bundle-v1"
KINDS = ("live", "replay")
LABELS = {
    "live": "EXPERIMENTAL FORECAST: frozen models, no verification yet, not an official warning",
    "replay": "HISTORICAL REPLAY of a stored cycle through the live code path: a pipeline proof, not a forecast",
}
ROOT = Path(__file__).resolve().parents[3] / "data" / "live"


class BundleError(RuntimeError):
    pass


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _stats(array: np.ndarray) -> dict:
    a = np.asarray(array, dtype=np.float64)
    return {"min": float(a.min()), "max": float(a.max()), "mean": float(a.mean())}


def write_bundle(root: Path, kind: str, date: str, arrays: dict[str, np.ndarray], products: list[str], provenance: dict, *, extra: dict | None = None) -> Path:
    if kind not in KINDS:
        raise BundleError(f"unknown bundle kind {kind}")
    directory = root / kind / date
    if directory.exists():
        raise BundleError(f"bundle already exists and is immutable: {directory}")
    directory.mkdir(parents=True)
    entries = {}
    for name, array in sorted(arrays.items()):
        array = np.ascontiguousarray(array)
        if array.dtype not in (np.float32, np.float64) or not np.isfinite(array).all():
            raise BundleError(f"array {name} must be finite float32/float64")
        path = directory / f"{name}.npy"
        np.save(path, array, allow_pickle=False)
        entries[name] = {"sha256": sha256_file(path), "shape": list(array.shape), "dtype": str(array.dtype), **_stats(array)}
    manifest = {"schema": SCHEMA, "kind": kind, "label": LABELS[kind], "initialization": f"{date[:4]}-{date[4:6]}-{date[6:]}T00:00:00Z", "cycle": date,
                "created_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"), "observation_read": False, "retrained_or_recalibrated": False,
                "products": sorted(products), "arrays": entries, "provenance": provenance, **(extra or {})}
    text = json.dumps(manifest, indent=2, sort_keys=True, allow_nan=False) + "\n"
    (directory / "manifest.json").write_text(text, encoding="utf-8", newline="\n")
    (directory / "manifest.sha256").write_text(hashlib.sha256(text.encode("utf-8")).hexdigest() + "\n", encoding="ascii")
    return directory


def verify_bundle(directory: Path) -> dict:
    """Return the manifest after verifying its sidecar, schema, flags and every array hash, shape and finiteness. Any problem raises BundleError."""
    manifest_path, side = directory / "manifest.json", directory / "manifest.sha256"
    if not manifest_path.is_file() or not side.is_file():
        raise BundleError(f"bundle files are missing: {directory.name}")
    if side.read_text(encoding="ascii").split()[0] != sha256_file(manifest_path):
        raise BundleError(f"manifest hash differs from its sidecar: {directory.name}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("schema") != SCHEMA or manifest.get("kind") not in KINDS or manifest.get("label") != LABELS[manifest["kind"]]:
        raise BundleError(f"bundle schema, kind or label is wrong: {directory.name}")
    if manifest.get("observation_read") is not False or manifest.get("retrained_or_recalibrated") is not False or manifest["cycle"] != directory.name or manifest["kind"] != directory.parent.name:
        raise BundleError(f"bundle flags or location are inconsistent: {directory.name}")
    for name, entry in manifest["arrays"].items():
        path = directory / f"{name}.npy"
        if not path.is_file() or sha256_file(path) != entry["sha256"]:
            raise BundleError(f"array hash mismatch: {name}")
        array = np.load(path, allow_pickle=False)
        if list(array.shape) != entry["shape"] or not np.isfinite(array).all():
            raise BundleError(f"array shape or finiteness mismatch: {name}")
    return manifest


def list_bundles(root: Path = ROOT) -> list[tuple[str, str]]:
    """(kind, date) of every bundle directory, newest cycle first, live before replay for equal dates."""
    found = []
    for kind in KINDS:
        base = root / kind
        if base.is_dir():
            found += [(kind, p.name) for p in base.iterdir() if p.is_dir() and p.name.isdigit() and len(p.name) == 8]
    return sorted(found, key=lambda kd: (kd[1], kd[0] == "live"), reverse=True)


def load_array(directory: Path, name: str) -> np.ndarray:
    return np.load(directory / f"{name}.npy", allow_pickle=False)


__all__ = ["BundleError", "write_bundle", "verify_bundle", "list_bundles", "load_array", "ROOT", "LABELS", "SCHEMA", "KINDS"]
