import hashlib
import json
import os
import pandas as pd
from pathlib import Path

try:
    from backend.app.core.config import SOURCE_CSV_PATH, DATA_MANIFEST_PATH
except ModuleNotFoundError:
    from app.core.config import SOURCE_CSV_PATH, DATA_MANIFEST_PATH

def compute_file_hash(filepath: str | Path) -> str:
    """Computes SHA-256 hash of the source dataset."""
    hasher = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(8192):
            hasher.update(chunk)
    return hasher.hexdigest()


def load_data_manifest(manifest_path: str | Path = DATA_MANIFEST_PATH) -> dict:
    """Load the provenance manifest paired with the configured source CSV."""
    path = Path(manifest_path)
    if not path.exists():
        raise FileNotFoundError(
            f"Dataset manifest not found at: {path}. "
            "Set DIGIVARSHA_DATA_MANIFEST with DIGIVARSHA_SOURCE_CSV."
        )
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _validate_manifest(filepath: Path, manifest: dict, file_hash: str, df: pd.DataFrame) -> None:
    expected_hash = str(manifest.get("sha256", "")).lower()
    if not expected_hash:
        raise ValueError("Dataset manifest must declare sha256.")
    if file_hash.lower() != expected_hash:
        raise ValueError(
            f"Dataset checksum mismatch for {filepath.name}: "
            f"expected {expected_hash}, got {file_hash.lower()}"
        )

    expected_rows = manifest.get("row_count")
    if expected_rows is not None and int(expected_rows) != len(df):
        raise ValueError(
            f"Dataset row-count mismatch: expected {expected_rows}, got {len(df)}"
        )

    expected_columns = manifest.get("source_columns")
    if expected_columns is not None and list(expected_columns) != list(df.columns):
        raise ValueError("Dataset columns/order do not match the provenance manifest.")


def load_source_dataset() -> tuple[pd.DataFrame, dict]:
    """
    Loads the configured manifest-backed prototype dataset.
    Returns (df, metadata_dict).
    """
    filepath = Path(SOURCE_CSV_PATH)
    if not filepath.exists():
        raise FileNotFoundError(f"Configured dataset not found at: {SOURCE_CSV_PATH}")

    file_size_bytes = os.path.getsize(filepath)
    file_hash = compute_file_hash(filepath)
    manifest = load_data_manifest()

    df = pd.read_csv(filepath)
    source_columns = list(df.columns)
    _validate_manifest(filepath, manifest, file_hash, df)
    
    # Ensure datetime parsing
    df["datetime"] = pd.to_datetime(df["time"], utc=False)
    df["datetime_utc"] = pd.to_datetime(df["time"], utc=True)
    
    metadata = {
        "dataset_id": manifest["dataset_id"],
        "filename": filepath.name,
        "filepath": str(filepath),
        "manifest_path": str(Path(DATA_MANIFEST_PATH)),
        "sha256": file_hash,
        "file_size_bytes": file_size_bytes,
        "total_rows": int(len(df)),
        "total_columns": int(len(source_columns)),
        "columns": source_columns,
        "derived_columns": ["datetime", "datetime_utc"],
        "provenance_status": manifest["provenance_status"],
        "training_eligible": bool(manifest.get("training_eligible", False)),
    }
    
    return df, metadata
