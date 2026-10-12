import ast
import re
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
CORPUS_PROTOCOL = ROOT / "experiments/recent_historical/operational_corpus_protocol_v1"

_EXPERIMENT_IMPORT = re.compile(r"experiments\.recent_historical\.([A-Za-z0-9_]+)")


def _local_dependencies(source_file: Path) -> tuple[set[str], set[str]]:
    """Return recent-historical experiment packages and scripts modules imported by a local source file."""
    try:
        tree = ast.parse(source_file.read_text(encoding="utf-8", errors="ignore"))
    except (OSError, SyntaxError):
        return set(), set()

    experiments: set[str] = set()
    scripts: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.ImportFrom) or not node.module:
            continue
        match = _EXPERIMENT_IMPORT.search(node.module)
        if match:
            experiments.add(match.group(1))
        if node.module == "scripts":
            scripts.update(alias.name for alias in node.names if alias.name != "*")
        elif node.module.startswith("scripts."):
            scripts.add(node.module.removeprefix("scripts.").split(".", 1)[0])
    return experiments, scripts


def _missing_experiment_code(test_file: Path) -> list[str]:
    """Experiment packages (gitignored local code under experiments/) that a test module needs but this checkout lacks.

    Transitive: a package that exists (the serving-data bundle ships some experiments/ directories) may itself import a package that
    does not, so the imports of every present package are followed. A package counts as present when its directory (possibly a
    namespace package) or a module file exists.
    """
    base = ROOT / "experiments" / "recent_historical"
    pending_experiments, pending_scripts = _local_dependencies(test_file)
    seen: set[str] = set()
    seen_scripts: set[str] = set()
    missing: list[str] = []
    scripts_dir = ROOT / "scripts"
    while pending_experiments or pending_scripts:
        while pending_scripts:
            script = pending_scripts.pop()
            if script in seen_scripts:
                continue
            seen_scripts.add(script)
            script_file = scripts_dir / f"{script}.py"
            if script_file.is_file():
                child_experiments, child_scripts = _local_dependencies(script_file)
                pending_experiments.update(child_experiments)
                pending_scripts.update(child_scripts - seen_scripts)
        if not pending_experiments:
            continue
        name = pending_experiments.pop()
        if name in seen:
            continue
        seen.add(name)
        if (base / name).is_dir():
            for source in (base / name).rglob("*.py"):
                child_experiments, child_scripts = _local_dependencies(source)
                pending_experiments.update(child_experiments - seen)
                pending_scripts.update(child_scripts - seen_scripts)
        elif (base / f"{name}.py").is_file():
            child_experiments, child_scripts = _local_dependencies(base / f"{name}.py")
            pending_experiments.update(child_experiments - seen)
            pending_scripts.update(child_scripts - seen_scripts)
        else:
            missing.append(name)
    return sorted(missing)


EXPERIMENT_CODE_MODULES = {f.name: missing for f in sorted(Path(__file__).parent.glob("test_*.py")) if (missing := _missing_experiment_code(f))}
collect_ignore = list(EXPERIMENT_CODE_MODULES)

# (module, test name or None for the whole module, required path, what it is)
SKIP_WITHOUT = (
    ("test_operational.py", None, BUNDLE_MARKER, "the serving-data bundle (release serving-data-v1)"),
    ("test_atmosphere_api.py", None, BUNDLE_MARKER, "the serving-data bundle (release serving-data-v1)"),
    ("test_phase2c.py", "test_api_readonly_provenance_and_legacy_lock", BUNDLE_MARKER, "the serving-data bundle (release serving-data-v1)"),
    ("test_phase4d_protocol.py", None, CORPUS_PROTOCOL, "the local experiment protocol files under experiments/ (gitignored)"),
)


def pytest_report_header(config):
    lines = []
    for module, missing in EXPERIMENT_CODE_MODULES.items():
        lines.append(f"not collected: {module} (needs gitignored local experiment code that is absent: {', '.join(missing)})")
    if not BUNDLE_MARKER.is_file():
        lines.append("serving-data bundle absent: bundle-dependent tests are skipped")
    return lines or ["all optional data and experiment code present"]


def pytest_collection_modifyitems(config, items):
    for item in items:
        module = Path(str(item.fspath)).name
        for target, name, path, what in SKIP_WITHOUT:
            if module == target and (name is None or item.name == name) and not path.exists():
                item.add_marker(pytest.mark.skip(reason=f"requires {what}, which is not in this checkout"))
