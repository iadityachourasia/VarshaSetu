"use client";

import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { DataSourceIndicator, ErrorState, LoadingState } from "@/components/science/common";
import { modelNames } from "@/science/frozen/results";
import { getOperationalDeterministicMetrics, getOperationalProbabilityMetrics, type OperationalYear } from "@/lib/api/operational";
import { loadOperationalCaseList, type CaseListItem } from "@/lib/operational-case-list";
import { withStaticFallback, type DataSourceMode } from "@/lib/data-source";
import { extractProbabilityEventMetrics } from "@/lib/operational-probability-metrics";
import { median } from "@/lib/stats";

type Year = 2024 | 2025;
type EventKey = "heavy" | "very_heavy";
type LeadKey = "all" | "24" | "48" | "72";
type Metric = "rmse_mm" | "mae_mm" | "bias_mm" | "POD" | "FAR" | "CSI" | "ETS";
const models = ["M0", "M1", "M2", "M3", "M4"] as const;
type ModelKey = (typeof models)[number];

type DeterministicLeadMetrics = { continuous?: { rmse_mm: number }; corrected_rmse_mm?: number };
type DeterministicModelMetrics = {
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
function leadRmse(leadItem: DeterministicLeadMetrics | undefined): number | null {
  if (!leadItem) return null;
  if (leadItem.continuous) return leadItem.continuous.rmse_mm;
  if (typeof leadItem.corrected_rmse_mm === "number") return leadItem.corrected_rmse_mm;
  return null;
}

function metricValue(
  det: Partial<Record<Year, Record<string, DeterministicModelMetrics> | undefined>>,
  year: Year, model: ModelKey, metric: Metric, event: EventKey, lead: LeadKey,
): number | null {
  const item = det[year]?.[model];
  if (!item) return null;
  if (metric === "POD" || metric === "FAR" || metric === "CSI" || metric === "ETS") {
    return lead === "all" ? item[event]?.metrics?.[metric] ?? null : null;
  }
  if (lead === "all") return item.continuous?.[metric] ?? null;
  if (metric !== "rmse_mm") return null;
  return leadRmse(item.leads?.[lead]);
}

// Phase 5A.2D: live-API-primary for the deterministic and probability metric
// families (getOperationalDeterministicMetrics / getOperationalProbabilityMetrics),
// same withStaticFallback pattern as Casebook/Ensemble/Regime Intelligence.
// The "Case outcomes" panel has no dedicated metrics endpoint; it is computed
// here directly from the already-proven live per-case index
// (loadOperationalCaseList) using the exact same sign-of-delta rule the
// backend itself uses for `selected_model_improved_vs_raw`
// (backend/app/api/operational.py) -- a transparent aggregate over real
// per-case values, not a new or invented statistic. Track A's own
// verification (VerificationView) is untouched.
export function OperationalVerification() {
  const [year, setYear] = useState<Year>(2025);
  const [metric, setMetric] = useState<Metric>("rmse_mm");
  const [event, setEvent] = useState<EventKey>("heavy");
  const [lead, setLead] = useState<LeadKey>("all");

  const det2024 = useQuery({ queryKey: ["operational-deterministic", 2024], queryFn: () => withStaticFallback(() => getOperationalDeterministicMetrics(2024 as OperationalYear), null) });
  const det2025 = useQuery({ queryKey: ["operational-deterministic", 2025], queryFn: () => withStaticFallback(() => getOperationalDeterministicMetrics(2025 as OperationalYear), null) });
  const prob2024 = useQuery({ queryKey: ["operational-probability-metrics", 2024], queryFn: () => withStaticFallback(() => getOperationalProbabilityMetrics(2024 as OperationalYear), null) });
  const prob2025 = useQuery({ queryKey: ["operational-probability-metrics", 2025], queryFn: () => withStaticFallback(() => getOperationalProbabilityMetrics(2025 as OperationalYear), null) });
  const caseList2025 = useQuery({ queryKey: ["operational-case-list", 2025], queryFn: () => loadOperationalCaseList(2025 as OperationalYear), staleTime: 60_000 });

  const det = useMemo(() => ({
    2024: det2024.data?.data?.metrics as Record<string, DeterministicModelMetrics> | undefined,
    2025: det2025.data?.data?.metrics as Record<string, DeterministicModelMetrics> | undefined,
  }), [det2024.data, det2025.data]);

  const outcomeCases = useMemo(
    () => (caseList2025.data?.data ?? []).filter((item): item is CaseListItem & { m1_minus_raw_rmse_mm: number } => item.m1_minus_raw_rmse_mm !== null),
    [caseList2025.data],
  );
  const improved = outcomeCases.filter((item) => item.m1_minus_raw_rmse_mm < 0).length;
  const worsened = outcomeCases.filter((item) => item.m1_minus_raw_rmse_mm > 0).length;
  const tied = outcomeCases.length - improved - worsened;
  const medianDelta = median(outcomeCases.map((item) => item.m1_minus_raw_rmse_mm));

  const heavy2024 = extractProbabilityEventMetrics(prob2024.data?.data?.metrics, "heavy");
  const veryHeavy2024 = extractProbabilityEventMetrics(prob2024.data?.data?.metrics, "very_heavy");
  const heavy2025 = extractProbabilityEventMetrics(prob2025.data?.data?.metrics, "heavy");
  const veryHeavy2025 = extractProbabilityEventMetrics(prob2025.data?.data?.metrics, "very_heavy");

  const indicatorMode: DataSourceMode | undefined = [det2024.data?.mode, det2025.data?.mode, prob2024.data?.mode, prob2025.data?.mode]
    .find((candidate) => candidate && candidate !== "VERIFIED_API") ?? det2025.data?.mode;

  if (det2024.isPending || det2025.isPending || prob2024.isPending || prob2025.isPending || caseList2025.isPending) {
    return <div className="phase5-verification"><LoadingState /></div>;
  }
  if (caseList2025.isError || !caseList2025.data || caseList2025.data.mode === "UNAVAILABLE") {
    return <div className="phase5-verification"><ErrorState message={caseList2025.data?.message ?? "Frozen 2025 case catalogue unavailable."} /></div>;
  }
  if (caseList2025.data.mode === "INTEGRITY_FAILURE") {
    return <div className="phase5-verification"><ErrorState message={`Scientific artifact integrity check failed: ${caseList2025.data.message}. This is a hard failure and is not masked by cached data.`} /></div>;
  }

  return <div className="phase5-verification"><section className="phase5-analysis-block"><h2>Operational-era verification skill cube {indicatorMode ? <DataSourceIndicator mode={indicatorMode} /> : null}</h2><p>Year × lead × model × metric × event type. Undefined intersections remain unavailable; no interpolation between metrics.</p><div className="phase5-controls"><label>Year<select value={year} onChange={(change) => setYear(Number(change.target.value) as Year)}><option value={2024}>2024 validation</option><option value={2025}>2025 completed final test</option></select></label><label>Lead<select value={lead} onChange={(change) => setLead(change.target.value as LeadKey)}><option value="all">All leads</option><option value="24">Day 1</option><option value="48">Day 2</option><option value="72">Day 3</option></select></label><label>Metric<select value={metric} onChange={(change) => setMetric(change.target.value as Metric)}><option value="rmse_mm">RMSE · mm</option><option value="mae_mm">MAE · mm</option><option value="bias_mm">Bias · mm</option><option value="POD">POD</option><option value="FAR">FAR</option><option value="CSI">CSI</option><option value="ETS">ETS</option></select></label><label>Event<select value={event} onChange={(change) => setEvent(change.target.value as EventKey)}><option value="heavy">Heavy ≥64.5</option><option value="very_heavy">Very Heavy ≥115.6</option></select></label></div><table className="phase5-table"><thead><tr><th>Model</th><th>{metric === "rmse_mm" ? "RMSE · mm" : metric === "mae_mm" ? "MAE · mm" : metric === "bias_mm" ? "Bias · mm" : metric}</th><th>Governance role</th></tr></thead><tbody>{models.map((model) => { const value = metricValue(det, year, model, metric, event, lead); return <tr key={model}><th>{model} · {modelNames[model]}</th><td>{value == null ? "Unavailable at selected lead" : value.toFixed(4)}</td><td>{model === "M1" ? "Preselected primary" : model === "M0" ? "Raw reference" : "Predeclared secondary"}</td></tr>; })}</tbody></table><p className="phase5-caveat">The 2025 M1 Ridge comparison was selected before the final test. The lower 2025 M2 RMSE is secondary and does not change that preselection.</p></section>
    <div className="phase5-analysis-block"><h2>2025 lead-time RMSE · paired common cells</h2><table className="phase5-table"><thead><tr><th>Model</th><th>Day 1</th><th>Day 2</th><th>Day 3</th></tr></thead><tbody>{models.map((model) => <tr key={model}><th>{modelNames[model]}</th>{(["24", "48", "72"] as const).map((hour) => { const value = leadRmse(det[2025]?.[model]?.leads?.[hour]); return <td key={hour}>{value == null ? "Unavailable" : value.toFixed(3)}</td>; })}</tr>)}</tbody></table></div>
    <div className="phase5-analysis-block"><h2>Case outcomes · selected M1 versus Raw</h2><div className="phase5-outcome-bar"><span style={{ flex: improved }}>{improved} improved</span><span style={{ flex: worsened }}>{worsened} worsened</span></div><p>{tied} tied · median per-case RMSE change {medianDelta == null ? "unavailable" : `${medianDelta.toFixed(4)} mm`}. All {outcomeCases.length} cases remain in the final result.</p></div>
    <div className="phase5-analysis-block"><h2>Validation → completed final test</h2><table className="phase5-table"><thead><tr><th>Population</th><th>Raw RMSE</th><th>Selected M1 RMSE</th><th>Heavy PR-AUC</th><th>Very Heavy PR-AUC</th></tr></thead><tbody><tr><th>2024 validation</th><td>{det[2024]?.M0?.continuous.rmse_mm.toFixed(4) ?? "Unavailable"}</td><td>{det[2024]?.M1?.continuous.rmse_mm.toFixed(4) ?? "Unavailable"}</td><td>{heavy2024 ? heavy2024.pr_auc.toFixed(5) : "Unavailable"}</td><td>{veryHeavy2024 ? veryHeavy2024.pr_auc.toFixed(5) : "Unavailable"}</td></tr><tr><th>2025 final</th><td>{det[2025]?.M0?.continuous.rmse_mm.toFixed(4) ?? "Unavailable"}</td><td>{det[2025]?.M1?.continuous.rmse_mm.toFixed(4) ?? "Unavailable"}</td><td>{heavy2025 ? heavy2025.pr_auc.toFixed(5) : "Unavailable"}</td><td>{veryHeavy2025 ? veryHeavy2025.pr_auc.toFixed(5) : "Unavailable"}</td></tr></tbody></table><p className="phase5-caveat">Probability discrimination weakened from validation to final test. The populations differ; this descriptive comparison does not reopen model selection.</p></div>
  </div>;
}
