"use client";

import { EvidenceChip } from "@/components/science/evidence-chip";
import { useQueries, useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { ErrorState, LoadingState } from "@/components/science/common";
import { EvidenceApiError } from "@/lib/api/evidence";
import { WD_YEARS, getWdCases, getWdOverview, getWdResult, type WdResult } from "@/lib/api/wd-indicator";
import { HashChip } from "@/components/ui/hash-chip";

const fixed = (value: number | null | undefined, digits: number) => (value == null || !Number.isFinite(value) ? "undefined" : value.toFixed(digits));

function association(result: WdResult) {
  const a = result.payload.association;
  if ("status" in a) return null;
  return a;
}

function CaseLookup({ year }: { year: number }) {
  const cases = useQuery({ queryKey: ["wd-indicator-cases", year], queryFn: () => getWdCases(year), staleTime: 5 * 60_000 });
  const [caseId, setCaseId] = useState<string>("");
  if (cases.isError) return <ErrorState message={cases.error instanceof Error ? cases.error.message : "Case flags are unavailable."} />;
  if (!cases.data) return <LoadingState compact label="Loading case flags" />;
  const chosen = cases.data.cases.find((c) => c.case_id === caseId) ?? cases.data.cases[Math.floor(cases.data.cases.length / 2)];
  return <div data-testid="wd-case-lookup">
    <div className="phase5-controls"><label>Case<select value={chosen.case_id} onChange={(event) => setCaseId(event.target.value)}>{cases.data.cases.map((c) => <option key={c.case_id} value={c.case_id}>{c.case_id} · {c.flag == null ? "undefined" : c.flag ? "flagged" : "not flagged"}</option>)}</select></label></div>
    <p data-testid="wd-case-reading"><strong>{chosen.flag == null ? "Undefined" : chosen.flag ? "Flagged" : "Not flagged"}</strong>: north-west India trough-vorticity index {fixed(chosen.index, 2)} against the training-year threshold {fixed(cases.data.threshold.threshold, 2)} (units of 1e-5 per second, positive is cyclonic). A flag marks a relatively strong forecast trough over the box; it does not say a western disturbance is present. Forecast height only; no observation and no model output enter it.</p>
  </div>;
}

export function WdIndicatorPanel() {
  const overview = useQuery({ queryKey: ["wd-indicator-overview"], queryFn: () => getWdOverview(), staleTime: 5 * 60_000 });
  const results = useQueries({ queries: WD_YEARS.map((year) => ({ queryKey: ["wd-indicator-result", year], queryFn: () => getWdResult(year), staleTime: 5 * 60_000 })) });
  const [year, setYear] = useState<number>(2025);
  const failed = [overview, ...results].find((q) => q.isError);
  if (failed) {
    const error = failed.error;
    const integrity = error instanceof EvidenceApiError && error.code === "SCIENCE_INTEGRITY_FAILURE";
    return <section className="phase5-analysis-block"><ErrorState message={integrity ? `Western-disturbance indicator integrity check failed: ${error.message}. This is a hard failure.` : error instanceof Error ? error.message : "The western-disturbance indicator evidence is unavailable."} /></section>;
  }
  if (!overview.data || results.some((q) => !q.data)) return <section className="phase5-analysis-block"><LoadingState compact label="Loading the western-disturbance indicator" /></section>;
  const ov = overview.data;
  const all = results.map((q) => q.data!);
  return <section className="phase5-analysis-block" aria-labelledby="wd-indicator-heading" data-testid="wd-indicator">
    <h2 id="wd-indicator-heading">Western-disturbance trough indicator (forecast-time heuristic)</h2>
    <div className="zone-banner zone-banner-posthoc" role="note" data-testid="wd-indicator-banner"><strong>Rule-based heuristic, forecast height only, not a validated detection of western disturbances</strong>
      <span>{ov.definition.indicator}. {ov.definition.flag}. No model uses this indicator as an input.</span></div>
    <p data-testid="wd-indicator-decision"><strong>{ov.decision.associated ? "On the development years the indicator is associated with rainfall" : "On the development years there is no consistent association"}: {ov.decision.wording}.</strong> The decision rule was frozen before any observation was compared: {ov.decision.rule}.</p>
    <div className="district-table-wrap"><table className="phase5-table zone-table">
      <caption className="sr-only">Cases, mean observed rainfall in the north-west India rain box by indicator flag, and the association, by population</caption>
      <thead><tr><th scope="col">Population</th><th scope="col">Cases flagged / not flagged</th><th scope="col">Mean rain flagged / not flagged (mm per day)</th><th scope="col">Flagged minus not flagged [95 % interval]</th><th scope="col">Spearman [95 % interval]</th></tr></thead>
      <tbody>{all.map((r) => { const a = association(r); const g = r.payload.groups; return <tr key={r.year} data-testid={`wd-row-${r.year}`}><th scope="row"><EvidenceChip label={r.evidence_label} /><br /><span className="micro-note">{r.year}</span></th>
        <td>{g.flagged.cases} / {g.not_flagged.cases}</td><td>{fixed(g.flagged.mean_rain_mm_per_day, 2)} / {fixed(g.not_flagged.mean_rain_mm_per_day, 2)}</td>
        <td>{a ? `${fixed(a.flagged_minus_not_flagged_mean_rain.point, 2)} [${fixed(a.flagged_minus_not_flagged_mean_rain.interval95?.[0], 2)}, ${fixed(a.flagged_minus_not_flagged_mean_rain.interval95?.[1], 2)}]` : "insufficient support"}</td>
        <td>{a ? `${fixed(a.spearman.point, 2)} [${fixed(a.spearman.interval95?.[0], 2)}, ${fixed(a.spearman.interval95?.[1], 2)}]` : "insufficient support"}</td></tr>; })}</tbody></table></div>
    <p className="micro-note">The threshold is the upper tercile of the {ov.definition.training_year} training year ({ov.definition.threshold.training_cases} cases). Observed quantity: {ov.evaluation.observed_quantity}. The sign of the difference changes between years, which is why no association is claimed. The 2022 and 2025 rows are post-hoc descriptive analyses.</p>
    <div className="phase5-controls"><label>Population for the case lookup<select value={year} onChange={(event) => setYear(Number(event.target.value))}>{all.map((r) => <option key={r.year} value={r.year}>{r.evidence_label}</option>)}</select></label></div>
    <CaseLookup year={year} />
    <p className="micro-note">Not established whatever the result: {ov.not_established.join("; ")}.</p>
    <ul className="phase5-caveats">{ov.caveats.map((c) => <li className="phase5-caveat" key={c}>{c}</li>)}</ul>
    <p className="micro-note">Protocol <HashChip hash={ov.protocol_sha256} /> · cases file <HashChip hash={ov.cases_file_sha256} /> · manifest <HashChip hash={ov.manifest_sha256} />. Historical scientific prototype.</p>
  </section>;
}
