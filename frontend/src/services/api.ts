import {
  Station, DateItem, ForecastRecord, AblationExperiment,
  FeatureImportanceItem, CalibrationMetric, ProvenanceData,
  JuryQuestion, ScientificAuditItem, SandboxRequest, SandboxResponse,
  SystemStatus
} from '../types';

const API_BASE = '/api';

export async function fetchSystemStatus(): Promise<SystemStatus> {
  const res = await fetch(`${API_BASE}/status`);
  if (!res.ok) throw new Error('Failed to fetch scientific readiness status');
  return res.json();
}

export async function fetchStations(): Promise<Station[]> {
  const res = await fetch(`${API_BASE}/stations`);
  if (!res.ok) throw new Error('Failed to fetch stations');
  return res.json();
}

export async function fetchDates(): Promise<DateItem[]> {
  const res = await fetch(`${API_BASE}/dates`);
  if (!res.ok) throw new Error('Failed to fetch dates');
  return res.json();
}

export async function fetchForecast(station_id: number, date: string, time?: string): Promise<ForecastRecord> {
  let url = `${API_BASE}/forecast?station_id=${station_id}&date=${encodeURIComponent(date)}`;
  if (time) url += `&time=${encodeURIComponent(time)}`;
  const res = await fetch(url);
  if (!res.ok) throw new Error('Failed to fetch forecast');
  return res.json();
}

export async function fetchOverallMetrics(): Promise<any> {
  const res = await fetch(`${API_BASE}/metrics/overall`);
  if (!res.ok) throw new Error('Failed to fetch overall metrics');
  return res.json();
}

export async function fetchThresholdMetrics(): Promise<any> {
  const res = await fetch(`${API_BASE}/metrics/thresholds`);
  if (!res.ok) throw new Error('Failed to fetch threshold metrics');
  return res.json();
}

export async function fetchRegimeMetrics(): Promise<any> {
  const res = await fetch(`${API_BASE}/metrics/regimes`);
  if (!res.ok) throw new Error('Failed to fetch regime metrics');
  return res.json();
}

export async function fetchAblationStudy(): Promise<AblationExperiment[]> {
  const res = await fetch(`${API_BASE}/metrics/ablation`);
  if (!res.ok) throw new Error('Failed to fetch ablation study');
  return res.json();
}

export async function fetchFeatureImportance(): Promise<FeatureImportanceItem[]> {
  const res = await fetch(`${API_BASE}/metrics/features`);
  if (!res.ok) throw new Error('Failed to fetch feature importance');
  return res.json();
}

export async function fetchCalibration(): Promise<CalibrationMetric> {
  const res = await fetch(`${API_BASE}/metrics/calibration`);
  if (!res.ok) throw new Error('Failed to fetch calibration');
  return res.json();
}

export async function fetchProvenance(): Promise<ProvenanceData> {
  const res = await fetch(`${API_BASE}/provenance`);
  if (!res.ok) throw new Error('Failed to fetch provenance');
  return res.json();
}

export async function fetchJuryDefense(): Promise<JuryQuestion[]> {
  const res = await fetch(`${API_BASE}/jury-defense`);
  if (!res.ok) throw new Error('Failed to fetch jury defense Q&A');
  return res.json();
}

export async function fetchScientificAudit(): Promise<ScientificAuditItem[]> {
  const res = await fetch(`${API_BASE}/audit`);
  if (!res.ok) throw new Error('Failed to fetch scientific audit');
  return res.json();
}

export async function postSandboxPredict(req: SandboxRequest): Promise<SandboxResponse> {
  const res = await fetch(`${API_BASE}/sandbox/predict`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(req)
  });
  if (!res.ok) throw new Error('Sandbox prediction failed');
  return res.json();
}
