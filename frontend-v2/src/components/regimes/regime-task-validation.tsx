"use client";

import { useQuery } from "@tanstack/react-query";
import { ErrorState, LoadingState } from "@/components/science/common";
import { EvidenceApiError } from "@/lib/api/evidence";
import { R03_TASKS, getR03Result, getReforecastOverview } from "@/lib/api/reforecast";

const fixed = (value: number | null | undefined, digits: number) => (value == null || !Number.isFinite(value) ? "undefined" : value.toFixed(digits));
const TASK_LABEL: Record<string, string> = { ACTIVE: "Active monsoon", BREAK: "Break monsoon", LOW_DEPRESSION: "Low / depression", WESTERN_DISTURBANCE: "Western disturbance", COASTAL_OROGRAPHIC: "Coastal / orographic rain" };
const TIER_LABEL: Record<string, string> = { USEFUL: "validated and useful", VALIDATED: "validated", NOT_VALIDATED: "not validated", INSUFFICIENT_SUPPORT: "insufficient support" };

function interval(entry: { status: string; point?: number | null; interval95?: [number, number] } | null | undefined, digits: number) {
  if (!entry || entry.status !== "ok" || entry.point == null || !entry.interval95) return "not reported";
  return `${fixed(entry.point, digits)} [${fixed(entry.interval95[0], digits)}, ${fixed(entry.interval95[1], digits)}]`;
}

export function RegimeTaskValidation() {
  const overview = useQuery({ queryKey: ["reforecast-overview"], queryFn: () => getReforecastOverview(), staleTime: 5 * 60_000 });
  const result = useQuery({ queryKey: ["reforecast-r03"], queryFn: () => getR03Result(), staleTime: 5 * 60_000 });
  const failed = [overview, result].find((q) => q.isError);
  if (failed) {
    const error = failed.error;
    const integrity = error instanceof EvidenceApiError && error.code === "SCIENCE_INTEGRITY_FAILURE";
    return <section className="phase5-analysis-block"><ErrorState message={integrity ? `Regime-task evidence integrity check failed: ${error.message}. This is a hard failure.` : error instanceof Error ? error.message : "The regime-task evidence is unavailable."} /></section>;
  }
  if (!overview.data || !result.data) return <section className="phase5-analysis-block"><LoadingState compact label="Loading the regime-detection validation" /></section>;
  const ov = overview.data;
  const r = result.data;
  return <section className="phase5-analysis-block" aria-labelledby="regime-task-heading" data-testid="regime-task-validation">
    <h2 id="regime-task-heading">Regime detection from the forecast, validated on sealed reforecast years</h2>
    <div className="zone-banner" role="note" data-testid="regime-task-banner"><strong>{r.evidence_label}</strong>
      <span>{r.payload.label_nature}. One standardised logistic model per task, fitted on {ov.populations.train_years[0]}-{ov.populations.train_years[ov.populations.train_years.length - 1]}; the climatology baseline uses lead and day of year only.</span></div>
    <div className="district-table-wrap"><table className="phase5-table zone-table" data-testid="regime-task-table">
      <caption className="sr-only">Cases, AUC, balanced accuracy and verdict of each regime-detection task on the sealed years</caption>
      <thead><tr><th scope="col">Task</th><th scope="col">Cases (positive / negative)</th><th scope="col">AUC [95 %]</th><th scope="col">Balanced accuracy [95 %] (chance 0.5)</th><th scope="col">AUC gain over climatology [95 %]</th><th scope="col">Verdict</th></tr></thead>
      <tbody>{R03_TASKS.map((t) => { const x = r.payload.tasks[t]; return <tr key={t} data-testid={`regime-task-row-${t}`}><th scope="row">{TASK_LABEL[t]}<br /><span className="micro-note">{ov.r03.tasks[t]}</span></th>
        <td>{x.cases} ({x.positives} / {x.negatives})</td><td>{x.tier === "INSUFFICIENT_SUPPORT" ? "no number" : interval(x.auc, 3)}</td><td>{x.tier === "INSUFFICIENT_SUPPORT" ? "no number" : interval(x.balanced_accuracy, 3)}</td>
        <td>{x.tier === "INSUFFICIENT_SUPPORT" ? "no number" : interval(x.auc_over_baseline, 3)}</td><td><strong>{TIER_LABEL[x.tier] ?? x.tier}</strong>{x.reason ? <><br /><span className="micro-note">{x.reason}</span></> : null}</td></tr>; })}</tbody></table></div>
    <p className="micro-note">Verdict rule, frozen before any score: validated needs an AUC lower bound above 0.5 and a positive lower bound of the gain over the climatology baseline; useful also needs an AUC of at least 0.70; a task needs at least 30 positive and 30 negative sealed cases. Protocol {ov.protocol_sha256.slice(0, 12)}… · evidence {r.evidence_sha256.slice(0, 12)}….</p>
    <ul className="phase5-caveats">{ov.caveats.map((c) => <li className="phase5-caveat" key={c}>{c}</li>)}</ul>
  </section>;
}
