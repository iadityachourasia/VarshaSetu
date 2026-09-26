"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { DataSourceIndicator, ErrorState, LoadingState, PageHeading, PrototypeNote } from "@/components/science/common";
import { caseDisplayLabel, loadOperationalCaseList, REGIME_CLASS_ORDER, type RegimeClass } from "@/lib/operational-case-list";
import type { OperationalYear } from "@/lib/api/operational";

const REGIME_LABEL: Record<RegimeClass, string> = {
  ACTIVE_MONSOON: "Active Monsoon", BREAK_WEAK_MONSOON: "Break / Weak Monsoon", LOW_DEPRESSION_INFLUENCED: "Low / Depression Influenced",
};

// Phase 5A.2C: Casebook is now live-API-primary via the operational case
// index (lib/operational-case-list.ts), falling back to the static bundle
// only on a genuine network failure -- never on an integrity failure or a
// real "this filter has no data for this year" answer.
export function OperationalCasebook({ initialYear }: { initialYear: number }) {
  const [year, setYear] = useState(initialYear);
  const [month, setMonth] = useState("all");
  const [lead, setLead] = useState("all");
  const [event, setEvent] = useState("all");
  const [outcome, setOutcome] = useState("all");
  const [regime, setRegime] = useState("all");
  const [page, setPage] = useState(0);
  const result = useQuery({
    queryKey: ["operational-case-list", year],
    queryFn: () => loadOperationalCaseList(year as OperationalYear),
    staleTime: 60_000,
  });
  const allCases = useMemo(() => result.data?.data ?? [], [result.data]);
  const hasCaseOutcomeData = useMemo(() => allCases.some((item) => item.m1_minus_raw_rmse_mm !== null), [allCases]);
  const cases = useMemo(() => allCases.filter((item) => {
    if (month !== "all" && String(item.month).padStart(2, "0") !== month) return false;
    if (lead !== "all" && String(item.lead_hours) !== lead) return false;
    if (event === "heavy" && !item.event_heavy) return false;
    if (event === "very-heavy" && !item.event_very_heavy) return false;
    if (outcome !== "all") {
      if (item.selected_model_improved_vs_raw === null) return false;
      if (outcome === "improved" && !item.selected_model_improved_vs_raw) return false;
      if (outcome === "worsened" && item.selected_model_improved_vs_raw) return false;
    }
    if (regime !== "all" && item.pseudo_regime_class !== regime) return false;
    return true;
  }), [allCases, month, lead, event, outcome, regime]);

  if (result.isPending) return <div className="page-content"><LoadingState /></div>;
  if (result.isError || !result.data) return <div className="page-content"><ErrorState message="Frozen case catalogue unavailable." /></div>;
  if (result.data.mode === "INTEGRITY_FAILURE") {
    return <div className="page-content"><ErrorState message={`Scientific artifact integrity check failed: ${result.data.message ?? "unknown error"}. This is a hard failure and is not masked by cached data.`} /></div>;
  }
  if (result.data.mode === "UNAVAILABLE") {
    return <div className="page-content"><ErrorState message={result.data.message ?? "Frozen case catalogue unavailable."} /></div>;
  }

  const pageCases = cases.slice(page * 24, (page + 1) * 24);
  const reset = () => setPage(0);
  return <div className="page-content"><PageHeading title="Event Casebook" subtitle="Browse every eligible historical case; event classes come from paired IMD observations." action={<span style={{ display: "flex", gap: 8, alignItems: "center" }}><DataSourceIndicator mode={result.data.mode} /><PrototypeNote /></span>} />
    <div className="phase5-context-strip"><strong>{year} {year === 2023 ? "CROSS-FIT / OOF" : year === 2024 ? "VALIDATION / MODEL SELECTION" : "FINAL HISTORICAL TEST — COMPLETED"}</strong><span>{cases.length} filtered cases</span><span>Not a ranking of best forecasts</span></div>
    <div className="phase5-controls">
      <label>Year<select value={year} onChange={(event) => { setYear(Number(event.target.value)); reset(); }}><option value={2023}>2023 · cross-fit</option><option value={2024}>2024 · validation</option><option value={2025}>2025 · final test</option></select></label>
      <label>Month<select value={month} onChange={(event) => { setMonth(event.target.value); reset(); }}><option value="all">All months</option>{["06", "07", "08", "09", "10"].map((value) => <option value={value} key={value}>{value}</option>)}</select></label>
      <label>Lead<select value={lead} onChange={(event) => { setLead(event.target.value); reset(); }}><option value="all">All leads</option><option value="24">Day 1</option><option value="48">Day 2</option><option value="72">Day 3</option></select></label>
      <label>Observed event<select value={event} onChange={(change) => { setEvent(change.target.value); reset(); }}><option value="all">All cases</option><option value="heavy">Heavy ≥64.5</option><option value="very-heavy">Very Heavy ≥115.6</option></select></label>
      <label>Predicted pseudo-regime<select value={regime} onChange={(change) => { setRegime(change.target.value); reset(); }}><option value="all">All</option>{REGIME_CLASS_ORDER.map((name) => <option value={name} key={name}>{REGIME_LABEL[name]}</option>)}</select></label>
      {hasCaseOutcomeData ? <label>Selected-model case outcome<select value={outcome} onChange={(change) => { setOutcome(change.target.value); reset(); }}><option value="all">Improved and worsened</option><option value="improved">Lower case RMSE</option><option value="worsened">Higher case RMSE</option></select></label> : null}
    </div>
    <p className="phase5-caveat">Observed event filters describe the completed historical reference. For 2023, the available M2 model output is out-of-fold. Case-level 2025 filters are post-hoc exploratory views and do not alter the frozen overall result.</p>
    <div className="phase5-case-list">{pageCases.map((item) => <Link key={item.case_id} href={`/forecast?experiment=operational&year=${year}&case=${encodeURIComponent(item.case_id)}`} className="phase5-case-row">
      <strong>{caseDisplayLabel(item)}</strong>
      <span>{item.pseudo_regime_class ? REGIME_LABEL[item.pseudo_regime_class] : "Regime unavailable"} · {item.m1_minus_raw_rmse_mm != null ? `Selected-model ΔRMSE ${item.m1_minus_raw_rmse_mm.toFixed(2)} mm` : year === 2023 ? "M2 OOF" : "validation"}</span>
    </Link>)}</div>
    {cases.length === 0 ? <div className="state-message"><strong>No cases match these filters.</strong><p>Try another observed-event category, lead, or year.</p></div> : null}
    {cases.length > 24 ? <div className="phase5-pagination"><button type="button" disabled={page === 0} onClick={() => setPage(page - 1)}>Previous</button><span>Page {page + 1} of {Math.ceil(cases.length / 24)}</span><button type="button" disabled={(page + 1) * 24 >= cases.length} onClick={() => setPage(page + 1)}>Next</button></div> : null}
  </div>;
}
