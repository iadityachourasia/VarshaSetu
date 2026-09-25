try:
    from backend.app.core.config import TARGET_COLUMN
except ModuleNotFoundError:
    from app.core.config import TARGET_COLUMN

FORBIDDEN_KEYWORDS = [
    TARGET_COLUMN,
    "rain_6h_accum",
    "observed_rain",
    "target",
    "future_rain"
]


def validate_feature_registry(
    feature_columns: list[str], feature_registry: dict[str, dict], *, operational: bool
) -> bool:
    """Validate semantic timing/provenance metadata, not just feature names."""
    missing = [name for name in feature_columns if name not in feature_registry]
    if missing:
        raise ValueError(f"FEATURE REGISTRY MISSING ENTRIES: {missing}")

    unsafe = []
    for name in feature_columns:
        definition = feature_registry[name]
        if definition.get("role") not in {"forecast", "static", "calendar", "derived"}:
            unsafe.append((name, "invalid role"))
        if not definition.get("available_at_issue_time", False):
            unsafe.append((name, "not available at forecast issue time"))
        if operational and definition.get("provenance_status") != "verified":
            unsafe.append((name, "provenance is not verified"))

    if unsafe:
        raise ValueError(f"SEMANTIC FEATURE SAFETY VIOLATION: {unsafe}")
    return True

def checkForTargetLeakage(feature_columns: list[str]) -> bool:
    """
    Automated target leakage checker.
    Verifies that target or target-derived columns are absent from feature lists.
    Raises ValueError if target leakage is detected.
    """
    detected = []
    for col in feature_columns:
        for keyword in FORBIDDEN_KEYWORDS:
            if keyword.lower() in col.lower():
                detected.append((col, keyword))
                
    if detected:
        raise ValueError(
            f"TARGET LEAKAGE DETECTED! The following features violate leakage rules: {detected}"
        )
        
    return True
