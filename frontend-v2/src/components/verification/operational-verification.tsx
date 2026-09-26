"use client";

import { useState } from "react";
import { final2025, modelNames, probabilityValidation2024, validation2024 } from "@/science/frozen/results";

type Year = 2024 | 2025;
type Metric = "rmse_mm" | "mae_mm" | "bias_mm" | "POD" | "FAR" | "CSI" | "ETS";
const models = ["M0", "M1", "M2", "M3", "M4"] as const;

function metricValue(year: Year, model: typeof models[number], metric: Metric, event: "heavy" | "very_heavy", lead: "all" | "24" | "48" | "72"): number | null {
  const item = year === 2025 ? final2025.deterministic[model] : validation2024.metrics[model];
  if (["POD", "FAR", "CSI", "ETS"].includes(metric)) return lead === "all" ? item[event].metrics[metric as "POD" | "FAR" | "CSI" | "ETS"] : null;
  if (lead === "all") return item.continuous[metric as "rmse_mm" | "mae_mm" | "bias_mm"];
  if (metric !== "rmse_mm") return null;
  return year === 2025 ? final2025.deterministic[model].leads[lead].continuous.rmse_mm : validation2024.metrics[model].leads[lead].corrected_rmse_mm;
}

export function OperationalVerification() {
  const [year, setYear] = useState<Year>(2025);
  const [metric, setMetric] = useState<Metric>("rmse_mm");
  const [event, setEvent] = useState<"heavy" | "very_heavy">("heavy");
  const [lead, setLead] = useState<"all" | "24" | "48" | "72">("all");
  return <div className="phase5-verification"><section className="phase5-analysis-block"><h2>Operational-era verification skill cube</h2><p>Year × lead × model × metric × event type. Undefined intersections remain unavailable; no interpolation between metrics.</p><div className="phase5-controls"><label>Year<select value={year} onChange={(change) => setYear(Number(change.target.value) as Year)}><option value={2024}>2024 validation</option><option value={2025}>2025 completed final test</option></select></label><label>Lead<select value={lead} onChange={(change) => setLead(change.target.value as typeof lead)}><option value="all">All leads</option><option value="24">Day 1</option><option value="48">Day 2</option><option value="72">Day 3</option></select></label><label>Metric<select value={metric} onChange={(change) => setMetric(change.target.value as Metric)}><option value="rmse_mm">RMSE · mm</option><option value="mae_mm">MAE · mm</option><option value="bias_mm">Bias · mm</option><option value="POD">POD</option><option value="FAR">FAR</option><option value="CSI">CSI</option><option value="ETS">ETS</option></select></label><label>Event<select value={event} onChange={(change) => setEvent(change.target.value as typeof event)}><option value="heavy">Heavy ≥64.5</option><option value="very_heavy">Very Heavy ≥115.6</option></select></label></div><table className="phase5-table"><thead><tr><th>Model</th><th>{metric === "rmse_mm" ? "RMSE · mm" : metric === "mae_mm" ? "MAE · mm" : metric === "bias_mm" ? "Bias · mm" : metric}</th><th>Governance role</th></tr></thead><tbody>{models.map((model) => { const value = metricValue(year, model, metric, event, lead); return <tr key={model}><th>{model} · {modelNames[model]}</th><td>{value == null ? "Unavailable at selected lead" : value.toFixed(4)}</td><td>{model === "M1" ? "Preselected primary" : model === "M0" ? "Raw reference" : "Predeclared secondary"}</td></tr>; })}</tbody></table><p className="phase5-caveat">The 2025 M1 Ridge comparison was selected before the final test. The lower 2025 M2 RMSE is secondary and does not change that preselection.</p></section>
    <div className="phase5-analysis-block"><h2>2025 lead-time RMSE · paired common cells</h2><table className="phase5-table"><thead><tr><th>Model</th><th>Day 1</th><th>Day 2</th><th>Day 3</th></tr></thead><tbody>{models.map((model) => <tr key={model}><th>{modelNames[model]}</th>{(["24", "48", "72"] as const).map((hour) => <td key={hour}>{final2025.deterministic[model].leads[hour].continuous.rmse_mm.toFixed(3)}</td>)}</tr>)}</tbody></table></div>
    <div className="phase5-analysis-block"><h2>Case outcomes · selected M1 versus Raw</h2><div className="phase5-outcome-bar"><span style={{ flex: final2025.case_audit.improved }}>{final2025.case_audit.improved} improved</span><span style={{ flex: final2025.case_audit.worsened }}>{final2025.case_audit.worsened} worsened</span></div><p>0 tied · median per-case RMSE change {final2025.case_audit.median_M1_minus_raw_rmse_mm.toFixed(4)} mm. All 232 cases remain in the final result.</p></div>
    <div className="phase5-analysis-block"><h2>Validation → completed final test</h2><table className="phase5-table"><thead><tr><th>Population</th><th>Raw RMSE</th><th>Selected M1 RMSE</th><th>Heavy PR-AUC</th><th>Very Heavy PR-AUC</th></tr></thead><tbody><tr><th>2024 validation</th><td>{validation2024.metrics.M0.continuous.rmse_mm.toFixed(4)}</td><td>{validation2024.metrics.M1.continuous.rmse_mm.toFixed(4)}</td><td>{probabilityValidation2024.heavy.pr_auc.toFixed(5)}</td><td>{probabilityValidation2024.very_heavy.pr_auc.toFixed(5)}</td></tr><tr><th>2025 final</th><td>{final2025.deterministic.M0.continuous.rmse_mm.toFixed(4)}</td><td>{final2025.deterministic.M1.continuous.rmse_mm.toFixed(4)}</td><td>{final2025.probability.heavy.metrics.pr_auc.toFixed(5)}</td><td>{final2025.probability.very_heavy.metrics.pr_auc.toFixed(5)}</td></tr></tbody></table><p className="phase5-caveat">Probability discrimination weakened from validation to final test. The populations differ; this descriptive comparison does not reopen model selection.</p></div>
  </div>;
}
