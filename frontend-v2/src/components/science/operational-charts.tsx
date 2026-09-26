"use client";

import { CartesianGrid, Legend, Line, LineChart, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { ErrorState, MetricTerm } from "@/components/science/common";
import type { ProbabilityEventMetrics } from "@/lib/operational-probability-metrics";
import { MODEL_COLOR, MODEL_LABEL, MODEL_ORDER, MODEL_ROLE, type ModelKey } from "@/lib/model-colors";

// Phase 5A.2D: shared Track-B (2023-2025 operational-era) scientific
// visualization/table components. Extreme Rain and Verification both
// render the same deterministic-model detection table and the same FSS
// chart against the same live-fetched data rather than each carrying its
// own copy of the fetch/render logic (spec section 28-29).

export type DeterministicLeadMetrics = { continuous?: { rmse_mm: number }; corrected_rmse_mm?: number };
export type DeterministicModelMetrics = {
  case_count: number;
  cell_count: number;
  continuous: { rmse_mm: number; mae_mm: number; bias_mm: number };
  heavy: { metrics: { POD: number; FAR: number; CSI: number; ETS: number } };
  very_heavy: { metrics: { POD: number; FAR: number; CSI: number; ETS: number } };
  leads?: Record<string, DeterministicLeadMetrics>;
};

// Frozen artifacts differ structurally between years (2025's leads carry a
// nested `continuous.rmse_mm`; 2024's carry a flat `corrected_rmse_mm`) --
// detected here from whichever key is actually present rather than
// hardcoded on the selected year, so a real backend shape difference is
// read correctly instead of silently misattributed.
export function leadRmse(leadItem: DeterministicLeadMetrics | undefined): number | null {
  if (!leadItem) return null;
  if (leadItem.continuous) return leadItem.continuous.rmse_mm;
  if (typeof leadItem.corrected_rmse_mm === "number") return leadItem.corrected_rmse_mm;
  return null;
}

export const DETERMINISTIC_MODEL_ORDER = ["M0", "M1", "M2", "M3", "M4"] as const;
export type DeterministicModelKey = (typeof DETERMINISTIC_MODEL_ORDER)[number];

/** Raw/M1-M4 thresholded-rainfall event detection (POD/FAR/CSI/ETS), one row
 * per model -- distinct from the calibrated-probability model's own
 * categorical metrics (see ProbabilityQualityCards below). Renders
 * "Unavailable" per cell rather than omitting a model row, so a real gap in
 * the frozen artifact stays visible instead of silently shrinking the table. */
export function DeterministicCategoricalTable({
  metrics, event, modelNames,
}: {
  metrics: Record<string, DeterministicModelMetrics> | undefined;
  event: "heavy" | "very_heavy";
  modelNames: Record<string, string>;
}) {
  if (!metrics) return <ErrorState message="Deterministic event-detection metrics are unavailable for this year." />;
  return <table className="phase5-table"><thead><tr><th>Model</th><th><MetricTerm term="POD" /></th><th><MetricTerm term="FAR" /></th><th><MetricTerm term="CSI" /></th><th><MetricTerm term="ETS" /></th></tr></thead><tbody>
    {DETERMINISTIC_MODEL_ORDER.map((model) => {
      const item = metrics[model];
      const categorical = item?.[event]?.metrics;
      return <tr key={model}><th>{model} · {modelNames[model] ?? model}</th>
        <td>{categorical ? categorical.POD.toFixed(4) : "Unavailable"}</td>
        <td>{categorical ? categorical.FAR.toFixed(4) : "Unavailable"}</td>
        <td>{categorical ? categorical.CSI.toFixed(4) : "Unavailable"}</td>
        <td>{categorical ? categorical.ETS.toFixed(4) : "Unavailable"}</td>
      </tr>;
    })}
  </tbody></table>;
}

export type FssScaleResult = { matched_raw: { fss: number | null }; matched_selected: { fss: number | null }; matched_case_count: number };
export type FssEventResult = Record<"1" | "3" | "5" | "9", FssScaleResult>;

/** Canonical FSS visualization: a real recharts line/dot chart (not a CSS
 * bar), Raw versus the year-selected primary model, across the four frozen
 * neighborhood sizes. Distinguishes the two series by dash pattern as well
 * as color (axe: color must not be the only distinction). Used by both
 * Extreme Rain's Spatial mode and Verification's Spatial tab against
 * identical fetched data -- one component, not two. */
export function OperationalFssChart({ fss, selectedModelLabel = "Selected model" }: { fss: FssEventResult; selectedModelLabel?: string }) {
  const data = (["1", "3", "5", "9"] as const).map((scale) => ({
    scale: `${scale}×${scale}`,
    raw: fss[scale].matched_raw.fss,
    selected: fss[scale].matched_selected.fss,
    cases: fss[scale].matched_case_count,
  }));
  return <figure className="chart-figure"><div className="chart-frame"><ResponsiveContainer width="100%" height="100%"><LineChart data={data} margin={{ top: 10, right: 15, bottom: 0, left: -18 }}>
    <CartesianGrid stroke="var(--line)" strokeDasharray="2 6" />
    <XAxis dataKey="scale" tick={{ fill: "var(--text-subtle)", fontSize: 10 }} />
    <YAxis domain={[0, 0.3]} tick={{ fill: "var(--text-subtle)", fontSize: 10 }} />
    <Tooltip formatter={(value) => (typeof value === "number" ? value.toFixed(4) : value)} />
    <Legend />
    <Line type="linear" dataKey="raw" name="Raw GEFS" stroke="var(--raw)" strokeWidth={2.5} dot={{ r: 4 }} connectNulls={false} />
    <Line type="linear" dataKey="selected" name={selectedModelLabel} stroke="var(--corrected)" strokeWidth={2.5} strokeDasharray="5 3" dot={{ r: 4, strokeDasharray: "0" }} connectNulls={false} />
  </LineChart></ResponsiveContainer></div><figcaption>Fractions Skill Score on matched paired 2-D cases, frozen ≥50% valid-neighborhood rule. Higher is better; case-count denominators vary by scale (see table below the chart).</figcaption></figure>;
}

/** Reliability diagram: predicted probability vs. observed frequency, with
 * the perfect-calibration diagonal. Renders only bins the frozen artifact
 * actually carries -- never reconstructs a missing bin. */
export function OperationalReliabilityChart({ metric }: { metric: ProbabilityEventMetrics }) {
  const data = metric.reliability
    .map((bin) => ({ predicted: bin.mean_predicted_probability, observed: bin.observed_event_frequency, count: bin.sample_count }))
    .filter((bin) => bin.count > 0 && bin.predicted != null && bin.observed != null);
  return <figure className="chart-figure"><div className="chart-frame"><ResponsiveContainer width="100%" height="100%"><LineChart data={data} margin={{ top: 10, right: 15, bottom: 0, left: -18 }}>
    <CartesianGrid stroke="var(--line)" strokeDasharray="2 6" />
    <XAxis dataKey="predicted" type="number" domain={[0, 1]} tickFormatter={(v: number) => `${Math.round(v * 100)}%`} tick={{ fill: "var(--text-subtle)", fontSize: 10 }} />
    <YAxis domain={[0, 1]} tickFormatter={(v: number) => `${Math.round(v * 100)}%`} tick={{ fill: "var(--text-subtle)", fontSize: 10 }} />
    <Tooltip formatter={(v, name) => [typeof v === "number" ? `${(v * 100).toFixed(1)}%` : v, name]} labelFormatter={(v) => `Mean predicted ${(Number(v) * 100).toFixed(1)}%`} />
    <ReferenceLine segment={[{ x: 0, y: 0 }, { x: 1, y: 1 }]} stroke="var(--text-subtle)" strokeDasharray="4 4" label={{ value: "Perfect calibration", position: "insideTopLeft", fill: "var(--text-subtle)", fontSize: 9 }} />
    <Line type="linear" dataKey="observed" name="Observed frequency" stroke="var(--corrected)" strokeWidth={2.5} dot={{ r: 4 }} />
  </LineChart></ResponsiveContainer></div><figcaption>Predicted probability versus observed frequency. Empty upper bins are omitted from the line and listed with their zero sample count in the table below.</figcaption></figure>;
}

/** Scalar-only probability quality cards: Brier/BSS/PR-AUC/ROC-AUC. Section
 * 8/25's rule ("only scalar PR-AUC/ROC-AUC exist; never synthesize a curve")
 * is enforced by this component simply never accepting curve-point data. */
export function ProbabilityQualityCards({ metric }: { metric: ProbabilityEventMetrics }) {
  return <div className="phase5-metric-strip">
    <span><small><MetricTerm term="Brier" /> ↓</small><strong>{metric.brier.toFixed(5)}</strong></span>
    <span><small><MetricTerm term="BSS" /> ↑</small><strong>{metric.bss >= 0 ? "+" : ""}{metric.bss.toFixed(4)}</strong></span>
    <span><small><MetricTerm term="PR-AUC" /> ↑</small><strong>{metric.pr_auc.toFixed(3)}</strong></span>
    <span><small><MetricTerm term="ROC-AUC" /> ↑</small><strong>{metric.roc_auc.toFixed(3)}</strong></span>
    <span><small>Observed event cells</small><strong>{metric.observed_event_count.toLocaleString()}</strong></span>
  </div>;
}

/** Live denominator-context badge -- replaces a hardcoded case/cell count
 * literal in JSX with whatever the fetched artifact actually reports. */
export function PopulationBadge({ cases, cells, label }: { cases: number; cells: number; label?: string }) {
  return <span className="phase5-population-badge">{label ? `${label} · ` : ""}{cases.toLocaleString()} cases · {cells.toLocaleString()} cells</span>;
}

/** Canonical Raw/M1-M4 model-ladder rail: one consistent color per model,
 * M1's preselected-primary and M2's secondary-result roles always labeled
 * (never a visual "M2 won" crown), reused everywhere a model legend is
 * needed instead of each page inventing its own. */
export function ModelLadderRail({ selected }: { selected?: ModelKey }) {
  return <div className="phase5-model-rail" role="list" aria-label="Model ladder">{MODEL_ORDER.map((model) => <div key={model} role="listitem" className={model === selected ? "selected" : ""}>
    <span className="model-dot" style={{ background: MODEL_COLOR[model] }} aria-hidden="true" />
    <strong>{model}</strong><small>{MODEL_LABEL[model]}</small><span className="phase5-model-role">{MODEL_ROLE[model]}</span>
  </div>)}</div>;
}
