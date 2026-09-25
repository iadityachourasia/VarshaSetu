export interface Station {
  location_id: number;
  district_name: string;
  taluka_name: string;
  latitude: number;
  longitude: number;
  elevation_m: number;
  record_count: number;
}

export interface DateItem {
  date: string;
  year: number;
  partition: string;
}

export interface ForecastRecord {
  station_id: number;
  district_name: string;
  taluka_name: string;
  latitude: number;
  longitude: number;
  elevation_m: number;
  date: string;
  time: string;
  available_times?: string[];
  temperature_2m_c?: number;
  relative_humidity_pct?: number;
  pressure_msl_hpa?: number;
  wind_speed_10m_kmh?: number;
  raw_nwp_forecast_mm: number;
  ai_corrected_forecast_mm: number;
  observed_rain_mm: number | null;
  raw_nwp_abs_error: number | null;
  ai_abs_error: number | null;
  predicted_regime_id: number;
  predicted_regime_name: string;
  regime_probabilities: number[];
  physics_predicted_regime?: string;
  physics_confidence?: number;
  physics_regime_probabilities?: Record<string, number>;
  heavy_rain_probability: number;
  very_heavy_rain_probability: number;
  exceedance_probabilities?: Record<string, number>;
  rainfall_category: string;
  alert_level: 'GREEN' | 'YELLOW' | 'ORANGE' | 'RED';
  raw_record_predictors?: SandboxRequest;
}

export interface ContinuousMetrics {
  n: number;
  rmse: number;
  mae: number;
  bias: number;
  r_corr: number;
  r2: number;
  rmse_improvement_pct?: number;
  mae_improvement_pct?: number;
}

export interface ContingencyTable {
  threshold_mm: number;
  total_records: number;
  observed_events: number;
  hits: number;
  misses: number;
  false_alarms: number;
  correct_negatives: number;
  pod: number | string;
  far: number | string;
  csi: number | string;
  ets: number | string;
  rare_event_warning: boolean;
}

export interface AblationExperiment {
  experiment: string;
  model_type: string;
  rmse: number;
  mae: number;
  bias: number;
  r2: number;
  rmse_imp_pct: number;
}

export interface FeatureImportanceItem {
  feature: string;
  importance_score: number;
  std: number;
}

export interface CalibrationMetric {
  heavy_64_5mm: {
    threshold_mm: number;
    brier_score: number;
    sample_size: number;
    positive_cases: number;
  };
  very_heavy_115_5mm: {
    threshold_mm: number;
    brier_score: number;
    sample_size: number;
    positive_cases: number;
  };
}

export interface ProvenanceData {
  dataset_id: string;
  dataset_hash_sha256: string;
  filename: string;
  total_rows: number;
  total_columns: number;
  manifest_file: string;
  provenance_status: string;
  training_eligible: boolean;
  scientific_readiness: SystemStatus['scientific_readiness'];
  legacy_report: SystemStatus['legacy_report'];
}

export interface JuryQuestion {
  q: string;
  a: string;
}

export interface ScientificAuditItem {
  check: string;
  status: 'PASS' | 'WARNING' | 'FAIL';
  detail: string;
}

export interface SandboxRequest {
  nwp_rain: number;
  nwp_temp: number;
  nwp_pressure: number;
  nwp_wind_speed: number;
  temp_2m: number;
  dew_point_2m: number;
  relative_humidity: number;
  pressure_msl: number;
  surface_pressure: number;
  cloud_cover: number;
  wind_direction: number;
  wind_speed: number;
  boundary_layer_height: number;
  tcwv: number;
  latitude: number;
  longitude: number;
  elevation: number;
  month: number;
  hour: number;
}

export interface SandboxResponse {
  raw_nwp_rain_mm: number;
  ai_corrected_rain_mm: number;
  bias_correction_mm: number;
  predicted_regime_id: number;
  regime_probabilities: number[];
  heavy_rain_probability: number;
  very_heavy_rain_probability: number;
  is_out_of_distribution: boolean;
}

export interface SystemStatus {
  project: string;
  phase: string;
  scientific_readiness: {
    ready: boolean;
    mode: string;
    blockers: string[];
    resolved_controls: string[];
  };
  current_dataset: {
    dataset_id: string;
    filename: string;
    sha256: string;
    rows: number;
    source_columns: number;
    provenance_status: string;
  };
  legacy_report: {
    present: boolean;
    status?: string;
    filename?: string;
    sha256?: string;
    experiment_id?: string;
    reason?: string;
  };
}
