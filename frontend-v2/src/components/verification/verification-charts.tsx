"use client";

import { Bar, BarChart, CartesianGrid, Legend, Line, LineChart, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { ModelComparison, Verification } from "@/lib/api/science";

const models = [
  ["M0_RAW_GEFS", "Raw GEFS"], ["M1_LINEAR_RIDGE_MOS", "Linear MOS"],
  ["M2_GLOBAL_XGBOOST", "Global ML"], ["M3_HARD_REGIME_XGBOOST", "Hard Regime"],
  ["M4_SOFT_REGIME_MOE", "Soft MoE"],
] as const;

export function RmseChart({ comparison }: { comparison: ModelComparison }) {
  const data = models.map(([key, name]) => ({ name, rmse: comparison.results[key].overall.continuous.rmse_mm }));
  return <figure className="chart-figure"><div className="chart-frame"><ResponsiveContainer width="100%" height="100%"><BarChart data={data} layout="vertical" margin={{ top: 7, right: 25, bottom: 0, left: 5 }}><CartesianGrid stroke="var(--line)" strokeDasharray="2 6" horizontal={false} /><XAxis type="number" domain={[0, 22]} tick={{ fill: "var(--text-subtle)", fontSize: 10 }} /><YAxis type="category" dataKey="name" width={97} tick={{ fill: "var(--foreground)", fontSize: 10 }} /><Tooltip formatter={(value) => `${Number(value).toFixed(4)} mm`} /><Bar dataKey="rmse" fill="var(--raw)" radius={[0, 3, 3, 0]} name="RMSE (mm)" /></BarChart></ResponsiveContainer></div><figcaption>RMSE in mm across the same frozen 255 cases and paired valid-cell mask. Lower is better; M2 Global ML is the minimum.</figcaption></figure>;
}

export function FssChart({ verification, threshold }: { verification: Verification; threshold: "heavy" | "very_heavy" }) {
  const data = ["1", "3", "5", "9"].map((scale) => ({ scale: `${scale}×${scale}`, raw: verification.metrics.fss[threshold][scale].raw.fss, corrected: verification.metrics.fss[threshold][scale].corrected.fss }));
  return <figure className="chart-figure"><div className="chart-frame"><ResponsiveContainer width="100%" height="100%"><LineChart data={data} margin={{ top: 10, right: 15, bottom: 0, left: -18 }}><CartesianGrid stroke="var(--line)" strokeDasharray="2 6" /><XAxis dataKey="scale" tick={{ fill: "var(--text-subtle)", fontSize: 10 }} /><YAxis domain={[0, 1]} tick={{ fill: "var(--text-subtle)", fontSize: 10 }} /><Tooltip /><Legend /><Line type="linear" dataKey="raw" name="Raw GEFS" stroke="var(--raw)" strokeWidth={2.5} dot={{ r: 3 }} connectNulls={false} /><Line type="linear" dataKey="corrected" name="VarshaSetu Corrected" stroke="var(--corrected)" strokeWidth={2.5} strokeDasharray="5 3" dot={{ r: 3 }} connectNulls={false} /></LineChart></ResponsiveContainer></div><figcaption>Fractions Skill Score on actual 2-D fields. Raw and corrected case counts differ by scale where denominator cases are undefined; see the table below.</figcaption></figure>;
}

export function ReliabilityChart({ verification, threshold }: { verification: Verification; threshold: "heavy" | "very_heavy" }) {
  const bins = verification.metrics.targets[threshold].reliability;
  const data = bins.map((bin) => ({ predicted: bin.mean_predicted_probability, observed: bin.observed_event_frequency, count: bin.sample_count })).filter((bin) => bin.count > 0 && bin.predicted != null && bin.observed != null);
  return <figure className="chart-figure"><div className="chart-frame"><ResponsiveContainer width="100%" height="100%"><LineChart data={data} margin={{ top: 10, right: 15, bottom: 0, left: -18 }}><CartesianGrid stroke="var(--line)" strokeDasharray="2 6" /><XAxis dataKey="predicted" type="number" domain={[0, 1]} tickFormatter={(v: number) => `${Math.round(v * 100)}%`} tick={{ fill: "var(--text-subtle)", fontSize: 10 }} /><YAxis domain={[0, 1]} tickFormatter={(v: number) => `${Math.round(v * 100)}%`} tick={{ fill: "var(--text-subtle)", fontSize: 10 }} /><Tooltip formatter={(v, name) => [typeof v === "number" ? `${(v * 100).toFixed(1)}%` : v, name]} labelFormatter={(v) => `Mean predicted ${(Number(v) * 100).toFixed(1)}%`} /><ReferenceLine segment={[{ x: 0, y: 0 }, { x: 1, y: 1 }]} stroke="var(--text-subtle)" strokeDasharray="4 4" /><Line type="linear" dataKey="observed" name="Observed frequency" stroke="var(--corrected)" strokeWidth={2.5} dot={{ r: 4 }} /></LineChart></ResponsiveContainer></div><figcaption>Predicted probability versus observed frequency. Empty upper bins are omitted from the line and listed as zero-sample bins below.</figcaption></figure>;
}
