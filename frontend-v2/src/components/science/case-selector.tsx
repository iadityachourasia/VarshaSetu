"use client";

import { useMemo, useState } from "react";
import { ChevronLeft, ChevronRight } from "lucide-react";
import type { CaseSummary } from "@/lib/api/science";
import { leadName, regimeName, utc } from "@/lib/format";

export function CaseSelector({ cases, demos, selectedId, onSelect }: {
  cases: CaseSummary[]; demos: CaseSummary[]; selectedId: string; onSelect: (id: string) => void;
}) {
  const [lead, setLead] = useState("all");
  const [regime, setRegime] = useState("all");
  const visible = useMemo(() => cases.filter((item) =>
    (lead === "all" || String(item.lead_hours) === lead) &&
    (regime === "all" || item.dominant_regime === regime)), [cases, lead, regime]);
  const index = visible.findIndex((item) => item.case_id === selectedId);
  return <div className="case-selector" aria-label="Historical case selector">
    <div className="case-selector-main"><div className="selector-title"><span className="small-label">HISTORICAL CASE</span><strong>{selectedId ? utc(cases.find((item) => item.case_id === selectedId)?.initialization_utc ?? "") : "Select a case"}</strong></div>
      <button className="icon-button" type="button" aria-label="Previous case" disabled={index <= 0} onClick={() => onSelect(visible[index - 1].case_id)}><ChevronLeft size={18} /></button>
      <button className="icon-button" type="button" aria-label="Next case" disabled={index < 0 || index >= visible.length - 1} onClick={() => onSelect(visible[index + 1].case_id)}><ChevronRight size={18} /></button>
      <label className="select-wrap"><span className="sr-only">Select historical case</span><select value={selectedId} onChange={(event) => onSelect(event.target.value)}>{visible.map((item) => <option key={item.case_id} value={item.case_id}>{utc(item.initialization_utc)} · {leadName(item.lead_hours)} · {regimeName(item.dominant_regime)} · {item.observed_heavy_cells} observed heavy cells</option>)}</select></label>
    </div>
    <div className="case-selector-filters"><label>Lead <select value={lead} onChange={(event) => setLead(event.target.value)}><option value="all">All leads</option><option value="24">Day 1</option><option value="48">Day 2</option><option value="72">Day 3</option></select></label>
      <label>Regime <select value={regime} onChange={(event) => setRegime(event.target.value)}><option value="all">All regimes</option><option value="ACTIVE_MONSOON">Active</option><option value="BREAK_WEAK_MONSOON">Break / Weak</option><option value="LOW_DEPRESSION_INFLUENCED">Low / Depression</option></select></label>
      <label>Demo cases <select value="" onChange={(event) => onSelect(event.target.value)}><option value="">Choose official case</option>{demos.map((item) => <option key={item.case_id} value={item.case_id}>{utc(item.initialization_utc)} · {leadName(item.lead_hours)}</option>)}</select></label>
    </div>
  </div>;
}
