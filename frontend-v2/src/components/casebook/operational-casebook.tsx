"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { ErrorState, LoadingState, PageHeading, PrototypeNote } from "@/components/science/common";
import { getOperationalIndex } from "@/science/frozen/operational";
import { regimeNames } from "@/science/frozen/results";

export function OperationalCasebook({ initialYear }: { initialYear: number }) {
  const [year, setYear] = useState(initialYear);
  const [month, setMonth] = useState("all");
  const [lead, setLead] = useState("all");
  const [event, setEvent] = useState("all");
  const [outcome, setOutcome] = useState("all");
  const [regime, setRegime] = useState("all");
  const [page, setPage] = useState(0);
  const index = useQuery({ queryKey: ["operational-index"], queryFn: getOperationalIndex, staleTime: Infinity });
  const cases = useMemo(() => index.data?.cases.filter((item) => {
    if (item.year !== year || month !== "all" && item.initialization_utc.slice(5, 7) !== month || lead !== "all" && String(item.lead_hours) !== lead) return false;
    if (event === "heavy" && item.heavy_cells === 0 || event === "very-heavy" && item.very_heavy_cells === 0) return false;
    if (outcome !== "all" && (!item.frozen_case_metrics || (outcome === "improved" ? item.frozen_case_metrics.M1_minus_raw_rmse_mm >= 0 : item.frozen_case_metrics.M1_minus_raw_rmse_mm <= 0))) return false;
    if (regime !== "all" && item.regime_probabilities.indexOf(Math.max(...item.regime_probabilities)) !== Number(regime)) return false;
    return true;
  }) ?? [], [index.data, year, month, lead, event, outcome, regime]);
  if (index.isPending) return <div className="page-content"><LoadingState /></div>;
  if (index.isError) return <div className="page-content"><ErrorState message="Frozen case catalogue unavailable." /></div>;
  const pageCases = cases.slice(page * 24, (page + 1) * 24);
  const reset = () => setPage(0);
  return <div className="page-content"><PageHeading title="Event Casebook" subtitle="Browse every eligible historical case; event classes come from paired IMD observations." action={<PrototypeNote />} />
    <div className="phase5-context-strip"><strong>{year} {year === 2023 ? "CROSS-FIT / OOF" : year === 2024 ? "VALIDATION / MODEL SELECTION" : "FINAL HISTORICAL TEST — COMPLETED"}</strong><span>{cases.length} filtered cases</span><span>Not a ranking of best forecasts</span></div>
    <div className="phase5-controls"><label>Year<select value={year} onChange={(event) => { setYear(Number(event.target.value)); reset(); }}><option value={2023}>2023 · cross-fit</option><option value={2024}>2024 · validation</option><option value={2025}>2025 · final test</option></select></label><label>Month<select value={month} onChange={(event) => { setMonth(event.target.value); reset(); }}><option value="all">All months</option>{["06", "07", "08", "09", "10"].map((value) => <option value={value} key={value}>{value}</option>)}</select></label><label>Lead<select value={lead} onChange={(event) => { setLead(event.target.value); reset(); }}><option value="all">All leads</option><option value="24">Day 1</option><option value="48">Day 2</option><option value="72">Day 3</option></select></label><label>Observed event<select value={event} onChange={(change) => { setEvent(change.target.value); reset(); }}><option value="all">All cases</option><option value="heavy">Heavy ≥64.5</option><option value="very-heavy">Very Heavy ≥115.6</option></select></label><label>Predicted pseudo-regime<select value={regime} onChange={(change) => { setRegime(change.target.value); reset(); }}><option value="all">All</option>{regimeNames.map((name, index) => <option value={index} key={name}>{name}</option>)}</select></label>{year === 2025 ? <label>M1 case outcome<select value={outcome} onChange={(change) => { setOutcome(change.target.value); reset(); }}><option value="all">Improved and worsened</option><option value="improved">M1 lower case RMSE</option><option value="worsened">M1 higher case RMSE</option></select></label> : null}</div>
    <p className="phase5-caveat">Observed event filters describe the completed historical reference. For 2023, the available M2 model output is out-of-fold. Case-level 2025 filters are post-hoc exploratory views and do not alter the frozen overall result.</p>
    <div className="phase5-case-list">{pageCases.map((item) => <Link key={item.case_id} href={`/forecast?experiment=operational&year=${year}&case=${encodeURIComponent(item.case_id)}`} className="phase5-case-row"><strong>{item.initialization_utc.slice(0, 10)} · Day {item.lead_hours / 24}</strong><span>{item.heavy_cells} Heavy · {item.very_heavy_cells} Very Heavy observed cells · max {item.max_observed_mm.toFixed(1)} mm</span><span>{regimeNames[item.regime_probabilities.indexOf(Math.max(...item.regime_probabilities))]} · {item.frozen_case_metrics ? `M1 ΔRMSE ${item.frozen_case_metrics.M1_minus_raw_rmse_mm.toFixed(2)} mm` : year === 2023 ? "M2 OOF" : "validation"}</span></Link>)}</div>
    {cases.length === 0 ? <div className="state-message"><strong>No cases match these filters.</strong><p>Try another observed-event category, lead, or year.</p></div> : null}
    {cases.length > 24 ? <div className="phase5-pagination"><button type="button" disabled={page === 0} onClick={() => setPage(page - 1)}>Previous</button><span>Page {page + 1} of {Math.ceil(cases.length / 24)}</span><button type="button" disabled={(page + 1) * 24 >= cases.length} onClick={() => setPage(page + 1)}>Next</button></div> : null}
  </div>;
}
