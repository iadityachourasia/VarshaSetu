import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent
REPO_ROOT = BASE_DIR.parent
DEFAULT_SOURCE_CSV_PATH = REPO_ROOT / "data" / "GOA_CLEAN.csv"
DEFAULT_DATA_MANIFEST_PATH = REPO_ROOT / "data" / "manifests" / "goa_clean.prototype.json"


def _resolve_configured_path(variable: str, default: Path) -> Path:
    configured = Path(os.environ.get(variable, str(default))).expanduser()
    if not configured.is_absolute():
        configured = REPO_ROOT / configured
    return configured.resolve()


# Paths are portable by default and may be overridden together for an externally
# supplied, manifest-backed dataset.
SOURCE_CSV_PATH = _resolve_configured_path("DIGIVARSHA_SOURCE_CSV", DEFAULT_SOURCE_CSV_PATH)
DATA_MANIFEST_PATH = _resolve_configured_path("DIGIVARSHA_DATA_MANIFEST", DEFAULT_DATA_MANIFEST_PATH)
MODELS_DIR = BASE_DIR / "models"
REPORTS_DIR = BASE_DIR / "reports"

os.makedirs(MODELS_DIR, exist_ok=True)
os.makedirs(REPORTS_DIR, exist_ok=True)

TARGET_COLUMN = "rain_6h_accum (mm)"
NWP_COLUMN = "raw_nwp_rain_6h_forecast (mm)"

RANDOM_SEED = 10
TARGET_ACCUMULATION_HOURS = 6

TRAIN_YEARS = [2020, 2021, 2022, 2023]
VAL_YEARS = [2024]
TEST_YEARS = [2025]
UNSEEN_YEARS = []

# Legacy prototype regime names. Their labels are not reproducible from the
# checked-in dataset, so training is blocked until a documented label source or
# generator is supplied.
REGIME_NAMES = {
    0: "Active Monsoon / Coastal Orographic Regime",
    1: "Break Monsoon / Weak Monsoon Regime",
    2: "Monsoon Depression / Low Pressure System"
}

# Legacy 24-hour category boundaries retained only to interpret the quarantined
# historical report. They MUST NOT be evaluated against TARGET_ACCUMULATION_HOURS.
LEGACY_THRESHOLDS_24H_MM = {
    "light": 2.5,
    "moderate": 15.6,
    "heavy": 64.5,
    "very_heavy": 115.5
}
