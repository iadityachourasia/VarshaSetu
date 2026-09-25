import numpy as np
import pandas as pd

try:
    from backend.app.core.config import (
        TARGET_COLUMN,
        NWP_COLUMN,
        LEGACY_THRESHOLDS_24H_MM,
        TARGET_ACCUMULATION_HOURS,
    )
except ModuleNotFoundError:
    from app.core.config import (
        TARGET_COLUMN,
        NWP_COLUMN,
        LEGACY_THRESHOLDS_24H_MM,
        TARGET_ACCUMULATION_HOURS,
    )

def datasetAudit(df: pd.DataFrame, file_metadata: dict) -> dict:
    """
    Performs complete scientific dataset audit on raw CSV dataframe.
    Returns comprehensive metrics and quality checks.
    """
    total_rows = int(len(df))
    total_cols = int(file_metadata.get("total_columns", len(df.columns)))
    
    # Missing values
    missing_dict = df.isnull().sum().to_dict()
    total_missing = int(sum(missing_dict.values()))
    
    # Duplicate rows
    duplicate_rows = int(df.duplicated().sum())
    duplicate_station_time = int(df.duplicated(subset=['location_id', 'time']).sum())
    
    # Dates and locations
    min_date = df["datetime"].min().date().isoformat()
    max_date = df["datetime"].max().date().isoformat()
    unique_dates = int(df['date'].nunique())
    unique_timestamps = int(df['time'].nunique())
    unique_stations = int(df['location_id'].nunique())
    unique_districts = int(df['district_name'].nunique())
    
    # Distributions per breakdown
    station_counts = df.groupby('location_id').size().to_dict()
    district_counts = df.groupby('district_name').size().to_dict()
    
    # Year / Month breakdowns
    df_temp = df.copy()
    df_temp['year'] = df_temp['datetime'].dt.year
    df_temp['month'] = df_temp['datetime'].dt.month
    df_temp['hour'] = df_temp['datetime'].dt.hour
    
    year_counts = df_temp['year'].value_counts().sort_index().to_dict()
    month_counts = df_temp['month'].value_counts().sort_index().to_dict()
    period_6h_counts = df_temp['hour'].value_counts().sort_index().to_dict()
    
    # Regime breakdown
    regime_counts = {}
    if 'regime_id' in df.columns:
        regime_counts = df['regime_id'].value_counts().to_dict()
        
    # Observed rainfall statistics
    y_obs = df[TARGET_COLUMN].values
    obs_stats = {
        "min": float(np.min(y_obs)),
        "max": float(np.max(y_obs)),
        "mean": float(np.mean(y_obs)),
        "median": float(np.median(y_obs)),
        "std": float(np.std(y_obs)),
        "p90": float(np.percentile(y_obs, 90)),
        "p95": float(np.percentile(y_obs, 95)),
        "p99": float(np.percentile(y_obs, 99)),
        "zero_count": int(np.sum(y_obs == 0)),
        "amount_exceedance_counts_not_operational_categories": {
            f"ge_{str(value).replace('.', '_')}_mm": int(np.sum(y_obs >= value))
            for value in LEGACY_THRESHOLDS_24H_MM.values()
        },
        "accumulation_hours": TARGET_ACCUMULATION_HOURS,
        "threshold_warning": (
            "Counts are descriptive 6-hour amount exceedances only. They are not "
            "IMD 24-hour operational rainfall categories."
        ),
    }
    
    # NWP rainfall statistics
    y_nwp = df[NWP_COLUMN].values
    nwp_stats = {
        "min": float(np.min(y_nwp)),
        "max": float(np.max(y_nwp)),
        "mean": float(np.mean(y_nwp)),
        "median": float(np.median(y_nwp)),
        "std": float(np.std(y_nwp)),
        "p90": float(np.percentile(y_nwp, 90)),
        "p95": float(np.percentile(y_nwp, 95)),
        "p99": float(np.percentile(y_nwp, 99))
    }
    
    # Quality Rules Validation
    negative_obs = int(np.sum(y_obs < 0))
    negative_nwp = int(np.sum(y_nwp < 0))
    invalid_rh = int(np.sum((df['relative_humidity_2m (%)'] < 0) | (df['relative_humidity_2m (%)'] > 100)))
    invalid_cloud = int(np.sum((df['cloud_cover (%)'] < 0) | (df['cloud_cover (%)'] > 100)))
    
    quality_audit = {
        "missing_values_pass": total_missing == 0,
        "duplicate_rows_pass": duplicate_rows == 0,
        "duplicate_station_time_pass": duplicate_station_time == 0,
        "non_negative_obs_pass": negative_obs == 0,
        "non_negative_nwp_pass": negative_nwp == 0,
        "relative_humidity_pass": invalid_rh == 0,
        "cloud_cover_pass": invalid_cloud == 0
    }
    
    return {
        "file_metadata": file_metadata,
        "total_rows": total_rows,
        "total_columns": total_cols,
        "derived_columns": list(file_metadata.get("derived_columns", [])),
        "missing_values": missing_dict,
        "total_missing": total_missing,
        "duplicate_rows": duplicate_rows,
        "duplicate_station_time": duplicate_station_time,
        "date_range": {"min": min_date, "max": max_date},
        "unique_dates": unique_dates,
        "unique_timestamps": unique_timestamps,
        "unique_stations": unique_stations,
        "unique_districts": unique_districts,
        "station_record_counts": station_counts,
        "district_record_counts": district_counts,
        "year_record_counts": year_counts,
        "month_record_counts": month_counts,
        "period_6h_counts": period_6h_counts,
        "regime_record_counts": regime_counts,
        "observed_rainfall_stats": obs_stats,
        "nwp_rainfall_stats": nwp_stats,
        "quality_audit": quality_audit
    }
