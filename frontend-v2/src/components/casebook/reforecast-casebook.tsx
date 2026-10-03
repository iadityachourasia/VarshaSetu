"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import type { CaseSummary } from "@/lib/api/science";
import { leadName, regimeName } from "@/lib/format";

type EventFilter = "all" | "heavy" | "very_heavy" | "none";
type Outcome = "all" | "improved" | "worsened";
type Sort = "date" | "gain" | "events";

/**
 * The 2019 reforecast casebook: every control-model-eligible case, filterable by observed event, lead and outcome. Counts and changes are read from the frozen case
 * records; nothing here is a new score. A case that improved is one whose corrected RMSE is below its Raw RMSE, nothing more.
 */
export function ReforecastCasebook({ cases }: { cases: CaseSummary[] }) {
  const [event, setEvent] = useState<EventFilter>("all");
  const [lead, setLead] = useState("all");
  const [outcome, setOutcome] = useState<Outcome>("all");
  const [sort, setSort] = useState<Sort>("date");
  const shown = useMemo(() => {
    const list = cases.filter((item) => {
      if (event === "heavy" && item.observed_heavy_cells === 0) return false;
      if (event === "very_heavy" && item.observed_very_heavy_cells === 0) return false;
      if (event === "none" && item.observed_heavy_cells > 0) return false;
      if (lead !== "all" && item.lead_hours !== Number(lead)) return false;
      const change = item.corrected_rmse_mm - item.raw_rmse_mm;
      if (outcome === "improved" && !(change < 0)) return false;
      if (outcome === "worsened" && !(change > 0)) return false;
      return true;
    });
    if (sort === "gain") return [...list].sort((a, b) => (a.corrected_rmse_mm - a.raw_rmse_mm) - (b.corrected_rmse_mm - b.raw_rmse_mm));
    if (sort === "events") return [...list].sort((a, b) => b.observed_heavy_cells - a.observed_heavy_cells || b.observed_very_heavy_cells - a.observed_very_heavy_cells);
    return list;
  }, [cases, event, lead, outcome, sort]);
  const improved = shown.filter((item) => item.corrected_rmse_mm < item.raw_rmse_mm).length;
  const withHeavy = shown.filter((item) => item.observed_heavy_cells > 0).length;
  const maxChange = Math.max(1, ...cases.map((item) => Math.abs(item.corrected_rmse_mm - item.raw_rmse_mm)));
  const leads = [...new Set(cases.map((item) => item.lead_hours))].sort((a, b) => a - b);

  return <>
    <div className="phase5-controls casebook-controls">
      <label>Observed event<select value={event} onChange={(change) => setEvent(change.target.value as EventFilter)}><option value="all">All cases</option><option value="heavy">Any Heavy cell (≥ 64.5 mm)</option><option value="very_heavy">Any Very Heavy cell (≥ 115.6 mm)</option><option value="none">No Heavy cell</option></select></label>
      <label>Lead<select value={lead} onChange={(change) => setLead(change.target.value)}><option value="all">All leads</option>{leads.map((hours) => <option key={hours} value={hours}>{leadName(hours)}</option>)}</select></label>
      <label>Case outcome<select value={outcome} onChange={(change) => setOutcome(change.target.value as Outcome)}><option value="all">Improved and worsened</option><option value="improved">Lower corrected RMSE</option><option value="worsened">Higher corrected RMSE</option></select></label>
      <label>Sort<select value={sort} onChange={(change) => setSort(change.target.value as Sort)}><option value="date">Initialization date</option><option value="gain">Largest RMSE reduction first</option><option value="events">Most Heavy cells first</option></select></label>
    </div>
    <div className="casebook-summary" role="status" aria-live="polite">
      <span><b>{shown.length}</b> of {cases.length} cases</span>
      <span><b>{improved}</b> with lower corrected RMSE</span>
      <span><b>{withHeavy}</b> with an observed Heavy cell</span>
    </div>
    <div className="phase5-case-list casebook-list">{shown.map((item) => {
      const change = item.corrected_rmse_mm - item.raw_rmse_mm;
      return <Link key={item.case_id} href={`/forecast?case=${encodeURIComponent(item.case_id)}`} className="phase5-case-row casebook-row">
        <strong>{item.initialization_utc.slice(0, 10)} · Day {item.lead_hours / 24}<small>{regimeName(item.dominant_regime)}</small></strong>
        <span className="casebook-events">
          <i className={item.observed_heavy_cells > 0 ? "event-chip event-heavy" : "event-chip"}>{item.observed_heavy_cells} Heavy</i>
          <i className={item.observed_very_heavy_cells > 0 ? "event-chip event-very-heavy" : "event-chip"}>{item.observed_very_heavy_cells} Very Heavy</i>
          <em>observed cells</em>
        </span>
        <span className="casebook-rmse">Raw {item.raw_rmse_mm.toFixed(2)} → M2 {item.corrected_rmse_mm.toFixed(2)} mm RMSE</span>
        <span className={`casebook-change ${change < 0 ? "is-better" : change > 0 ? "is-worse" : ""}`} aria-label={`Change ${change > 0 ? "+" : ""}${change.toFixed(2)} mm`}>
          <i style={{ width: `${(Math.abs(change) / maxChange) * 100}%` }} aria-hidden="true" />{change > 0 ? "+" : change < 0 ? "−" : ""}{Math.abs(change).toFixed(2)}
        </span>
      </Link>;
    })}</div>
    {shown.length === 0 ? <div className="state-message"><strong>No cases match these filters.</strong><p>Try another observed-event category, lead or outcome.</p></div> : null}
  </>;
}
