"use client";

import { useQueries, useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { ErrorState, LoadingState } from "@/components/science/common";
import { EvidenceApiError } from "@/lib/api/evidence";
import { COASTAL_CLASSES, COASTAL_YEARS, getCoastalCases, getCoastalOverview, getCoastalResult, type CoastalResult } from "@/lib/api/coastal-regime";

const fixed = (value: number | null | undefined, digits: number) => (value == null || !Number.isFinite(value) ? "undefined" : value.toFixed(digits));
const pct = (value: number | null | undefined) => (value == null ? "undefined" : `${(100 * value).toFixed(0)} %`);
const CLASS_LABEL = { WEAK: "Weak", MODERATE: "Moderate", STRONG: "Strong" } as const;

function discrimination(result: CoastalResult) {
  const d = result.payload.discrimination;
  if ("status" in d) return null;
  return d;
}

function CaseLookup({ year }: { year: number }) {
  const cases = useQuery({ queryKey: ["coastal-regime-cases", year], queryFn: () => getCoastalCases(year), staleTime: 5 * 60_000 });
  const [caseId, setCaseId] = useState<string>("");
  if (cases.isError) return <ErrorState message={cases.error instanceof Error ? cases.error.message : "Case classes are unavailable."} />;
  if (!cases.data) return <LoadingState label="Loading case classes" />;
  const chosen = cases.data.cases.find((c) => c.case_id === caseId) ?? cases.data.cases[Math.floor(cases.data.cases.length / 2)];
  const training = cases.data.cut_points;
  return <div data-testid="coastal-case-lookup">
    <div className="phase5-controls"><label>Case<select value={chosen.case_id} onChange={(event) => setCaseId(event.target.value)}>{cases.data.cases.map((c) => <option key={c.case_id} value={c.case_id}>{c.case_id} · {c.class ?? "undefined"}</option>)}</select></label></div>
    <p data-testid="coastal-case-reading"><strong>{chosen.class ? CLASS_LABEL[chosen.class] : "Undefined"}</strong> Ghats-coast forcing for this case (index {fixed(chosen.index, 1)}; training-year cut-points {fixed(training.q33, 1)} and {fixed(training.q67, 1)}). Its rank within the {training.training_year} training distribution is {pct(chosen.percentile_vs_training)}: a rank, not a probability of rain. Forecast fields only; no observation and no model output enter this label.</p>
  </div>;
}

export function CoastalRegimePanel() {
  const overview = useQuery({ queryKey: ["coastal-regime-overview"], queryFn: () => getCoastalOverview(), staleTime: 5 * 60_000 });
  const results = useQueries({ queries: COASTAL_YEARS.map((year) => ({ queryKey: ["coastal-regime-result", year], queryFn: () => getCoastalResult(year), staleTime: 5 * 60_000 })) });
  const [year, setYear] = useState<number>(2025);
  const failed = [overview, ...results].find((q) => q.isError);
  if (failed) {
    const error = failed.error;
    const integrity = error instanceof EvidenceApiError && error.code === "SCIENCE_INTEGRITY_FAILURE";
    return <section className="phase5-analysis-block"><ErrorState message={integrity ? `Coastal regime integrity check failed: ${error.message}. This is a hard failure.` : error instanceof Error ? error.message : "The coastal regime evidence is unavailable."} /></section>;
  }
  if (!overview.data || results.some((q) => !q.data)) return <section className="phase5-analysis-block"><LoadingState label="Loading the coastal and orographic regime" /></section>;
  const ov = overview.data;
  const all = results.map((q) => q.data!);
  return <section className="phase5-analysis-block" aria-labelledby="coastal-regime-heading" data-testid="coastal-regime">
    <h2 id="coastal-regime-heading">Coastal and orographic forcing regime (forecast-time heuristic)</h2>
    <div className="zone-banner zone-banner-posthoc" role="note" data-testid="coastal-regime-banner"><strong>Rule-based heuristic, forecast fields only, not a validated regime and not a probability</strong>
      <span>{ov.definition.index}. {ov.definition.classes}. No model uses this regime as an input.</span></div>
    <p data-testid="coastal-regime-decision"><strong>{ov.decision.discriminates ? "On the development years" : "On the development years it does not"} {ov.decision.discriminates ? `the heuristic discriminates: ${ov.decision.wording}.` : "discriminate, so it is shown without a claim."}</strong> The decision rule was frozen before any observation was compared: {ov.decision.rule}.</p>
    <div className="district-table-wrap"><table className="phase5-table zone-table">
      <caption className="sr-only">Cases, share of observed Ghats-coast heavy-rain pairs and mean heavy fraction by forcing class and population</caption>
      <thead><tr><th scope="col">Population</th><th scope="col">Cases weak / moderate / strong</th><th scope="col">Share of observed heavy pairs weak / moderate / strong</th><th scope="col">Mean heavy fraction of the zone weak / moderate / strong</th><th scope="col">Strong minus weak [95 % interval]</th><th scope="col">Spearman [95 % interval]</th></tr></thead>
      <tbody>{all.map((r) => { const d = discrimination(r); const g = r.payload.groups; return <tr key={r.year} data-testid={`coastal-row-${r.year}`}><th scope="row">{r.evidence_label}<br /><span className="micro-note">Track {r.track} · {r.year}</span></th>
        <td>{COASTAL_CLASSES.map((c) => g[c].cases).join(" / ")}</td><td>{COASTAL_CLASSES.map((c) => pct(g[c].share_of_all_heavy_event_pairs)).join(" / ")}</td><td>{COASTAL_CLASSES.map((c) => fixed(g[c].mean_heavy_fraction, 3)).join(" / ")}</td>
        <td>{d ? `${fixed(d.strong_minus_weak_heavy_fraction.point, 3)} [${fixed(d.strong_minus_weak_heavy_fraction.interval95?.[0], 3)}, ${fixed(d.strong_minus_weak_heavy_fraction.interval95?.[1], 3)}]` : "insufficient support"}</td>
        <td>{d ? `${fixed(d.spearman.point, 2)} [${fixed(d.spearman.interval95?.[0], 2)}, ${fixed(d.spearman.interval95?.[1], 2)}]` : "insufficient support"}</td></tr>; })}</tbody></table></div>
    <p className="micro-note">Terciles were fitted on the training year of each track ({Object.entries(ov.definition.cut_points).map(([t, c]) => `Track ${t}: ${c.training_year}, ${c.training_cases} cases`).join("; ")}); later years have more strong cases than a third, so the class shares shift between years. The 2019 and 2025 rows are post-hoc descriptive analyses.</p>
    <div className="phase5-controls"><label>Population for the case lookup<select value={year} onChange={(event) => setYear(Number(event.target.value))}>{all.map((r) => <option key={r.year} value={r.year}>{r.evidence_label}</option>)}</select></label></div>
    <CaseLookup year={year} />
    <ul className="phase5-caveats">{ov.caveats.map((c) => <li className="phase5-caveat" key={c}>{c}</li>)}</ul>
    <p className="micro-note">Protocol {ov.protocol_sha256.slice(0, 12)}… · cases file {ov.cases_file_sha256.slice(0, 12)}… · manifest {ov.manifest_sha256.slice(0, 12)}…. Historical scientific prototype.</p>
  </section>;
}
