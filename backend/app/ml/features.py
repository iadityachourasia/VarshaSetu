import numpy as np
import pandas as pd
try:
    from backend.app.ml.leakage import checkForTargetLeakage, validate_feature_registry
except ModuleNotFoundError:
    from app.ml.leakage import checkForTargetLeakage, validate_feature_registry


def _definition(role: str, source: str, units: str, transformation: str = "identity") -> dict:
    return {
        "role": role,
        "source": source,
        "units": units,
        "transformation": transformation,
        "available_at_issue_time": True,
        # The intended timing is safe, but the checked-in file has no source
        # evidence. Operational validation therefore remains fail-closed.
        "provenance_status": "unverified" if role == "forecast" else "verified",
    }


FEATURE_REGISTRY = {
    "nwp_rain": _definition("forecast", "raw_nwp_rain_6h_forecast (mm)", "mm/6h"),
    "nwp_temp": _definition("forecast", "raw_nwp_temp_forecast (?C)", "degC"),
    "nwp_pressure": _definition("forecast", "raw_nwp_pressure_msl_forecast (hPa)", "hPa"),
    "nwp_wind_speed": _definition("forecast", "raw_nwp_wind_speed_forecast (km/h)", "km/h"),
    "latitude": _definition("static", "latitude", "degrees_north"),
    "longitude": _definition("static", "longitude", "degrees_east"),
    "elevation": _definition("static", "elevation (m)", "m"),
    "month": _definition("calendar", "valid timestamp", "1-12"),
    "day_of_year": _definition("calendar", "valid timestamp", "1-366"),
    "hour": _definition("calendar", "valid timestamp", "0-23"),
    "sin_month": _definition("derived", "month", "1", "sin(2*pi*month/12)"),
    "cos_month": _definition("derived", "month", "1", "cos(2*pi*month/12)"),
    "sin_hour": _definition("derived", "hour", "1", "sin(2*pi*hour/24)"),
    "cos_hour": _definition("derived", "hour", "1", "cos(2*pi*hour/24)"),
}

def get_base_feature_names(df: pd.DataFrame) -> list[str]:
    """Returns exact feature column names present in the dataset (excluding target and ID metadata)."""
    exclude = [
        "location_id", "time", "date", "time_ist", "hour_ist", 
        "district_name", "taluka_name", "district_code", 
        "datetime", "year", "rain_6h_accum (mm)"
    ]
    cols = [c for c in df.columns if c not in exclude]
    return cols

def prepare_features(df: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
    """
    Engineers legitimate, non-leaking predictors from source dataframe.
    Returns (X_df, feature_names).
    """
    df_feat = pd.DataFrame(index=df.index)
    
    # 1. Intended NWP features. Their source provenance remains unverified, so
    # operational training is blocked by the readiness gate.
    nwp_rain_col = "raw_nwp_rain_6h_forecast (mm)"
    df_feat["nwp_rain"] = df[nwp_rain_col]
    
    # NWP atmospheric forecasts
    nwp_temp_col = [c for c in df.columns if "raw_nwp_temp" in c][0]
    nwp_p_col = [c for c in df.columns if "raw_nwp_pressure" in c][0]
    nwp_w_col = [c for c in df.columns if "raw_nwp_wind" in c][0]

    df_feat["nwp_temp"] = df[nwp_temp_col]
    df_feat["nwp_pressure"] = df[nwp_p_col]
    df_feat["nwp_wind_speed"] = df[nwp_w_col]

    # Geographic Features
    df_feat["latitude"] = df["latitude"]
    df_feat["longitude"] = df["longitude"]
    df_feat["elevation"] = df["elevation (m)"]

    # 2. Temporal cyclic features
    if "datetime" in df.columns:
        dt = df["datetime"]
    else:
        dt = pd.to_datetime(df["time"])

    df_feat["month"] = dt.dt.month
    df_feat["day_of_year"] = dt.dt.dayofyear
    df_feat["hour"] = dt.dt.hour
    
    df_feat["sin_month"] = np.sin(2 * np.pi * df_feat["month"] / 12)
    df_feat["cos_month"] = np.cos(2 * np.pi * df_feat["month"] / 12)
    df_feat["sin_hour"] = np.sin(2 * np.pi * df_feat["hour"] / 24)
    df_feat["cos_hour"] = np.cos(2 * np.pi * df_feat["hour"] / 24)

    feature_names = list(df_feat.columns)
    
    # Run name-based and semantic leakage audits. Operational mode additionally
    # requires verified source provenance and is intentionally blocked today.
    checkForTargetLeakage(feature_names)
    validate_feature_registry(feature_names, FEATURE_REGISTRY, operational=False)

    return df_feat, feature_names


def validate_operational_features(feature_names: list[str]) -> bool:
    return validate_feature_registry(feature_names, FEATURE_REGISTRY, operational=True)
