import sys
from pathlib import Path

import pytest


BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

# ---------------------------------------------------------------------------------------------------------------------
# Tests that need data or code which is deliberately NOT in git (too large, or local experiment code):
#   * the serving-data bundle (GitHub release serving-data-v1): data/manifests/phase2c/*.npy, data/operational_derived,
#     experiments/recent_historical/phase4f|4i|4j. CI downloads it and verifies its SHA-256; a bare clone does not have it.
#   * the local experiment code under experiments/ (gitignored), imported by the Phase 4 freeze tests.
# On a checkout that lacks them these tests are skipped or not collected, and the reason is printed in the report header
# and the skip summary. Nothing is hidden: with the data present every one of them runs and must pass.
# ---------------------------------------------------------------------------------------------------------------------
ROOT = BACKEND_DIR.parent
BUNDLE_MARKER = ROOT / "data/manifests/phase2c/district_weights.npy"
EXPERIMENT_CODE_MARKER = ROOT / "experiments/recent_historical/phase4i_operational_model_development_v1/freeze.py"
CORPUS_PROTOCOL = ROOT / "experiments/recent_historical/operational_corpus_protocol_v1"

EXPERIMENT_CODE_MODULES = (
    "test_phase4b_external.py", "test_phase4c_comparability.py", "test_phase4e_inventory.py", "test_phase4f_source.py",
    "test_phase4g_features.py", "test_phase4h_protocol.py", "test_phase4i_operational.py", "test_phase4j_final_test.py",
    "test_phase4m_regime_diagnostics.py",
)
collect_ignore = [] if EXPERIMENT_CODE_MARKER.is_file() else list(EXPERIMENT_CODE_MODULES)

# (module, test name or None for the whole module, required path, what it is)
SKIP_WITHOUT = (
    ("test_operational.py", None, BUNDLE_MARKER, "the serving-data bundle (release serving-data-v1)"),
    ("test_phase2c.py", "test_api_readonly_provenance_and_legacy_lock", BUNDLE_MARKER, "the serving-data bundle (release serving-data-v1)"),
    ("test_phase4d_protocol.py", None, CORPUS_PROTOCOL, "the local experiment protocol files under experiments/ (gitignored)"),
)


def pytest_report_header(config):
    lines = []
    if collect_ignore:
        lines.append(f"not collected (experiment code under experiments/ is gitignored and absent): {len(collect_ignore)} modules")
    if not BUNDLE_MARKER.is_file():
        lines.append("serving-data bundle absent: bundle-dependent tests are skipped")
    return lines or ["all optional data and experiment code present"]


def pytest_collection_modifyitems(config, items):
    for item in items:
        module = Path(str(item.fspath)).name
        for target, name, path, what in SKIP_WITHOUT:
            if module == target and (name is None or item.name == name) and not path.exists():
                item.add_marker(pytest.mark.skip(reason=f"requires {what}, which is not in this checkout"))
