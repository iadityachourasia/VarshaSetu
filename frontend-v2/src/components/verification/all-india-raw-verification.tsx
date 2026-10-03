"use client";

import { useQueries, useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { ErrorState, LoadingState } from "@/components/science/common";
import { EvidenceApiError } from "@/lib/api/evidence";
import { ALL_INDIA_REGIONS, ALL_INDIA_YEARS, getAllIndiaOverview, getAllIndiaResult, type AllIndiaResult } from "@/lib/api/all-india-raw";

const fixed = (value: number | null | undefined, digits: number) => (value == null || !Number.isFinite(value) ? "undefined" : value.toFixed(digits));
const REGION_LABEL: Record<string, string> = {
  ALL_INDIA: "All India (every scored land cell)", INSIDE_MODEL_DOMAIN: "Inside the modelling box (10 to 22 N, 68 to 80 E)", NORTH_OF_DOMAIN: "North of the box (north of 22 N, up to 88 E)",
  EAST_AND_NORTH_EAST: "East and north-east (east of 88 E)", EAST_COAST_PENINSULA: "East-coast peninsula (south of 22 N, 80 to 88 E)", SOUTH_OF_DOMAIN: "South of the box (south of 10 N, up to 80 E)",
};

function heavyText(result: AllIndiaResult, region: (typeof ALL_INDIA_REGIONS)[number]) {
  const h = result.payload.metrics[region].categorical.heavy;
  return "status" in h ? "insufficient support" : `CSI ${fixed(h.CSI, 3)} · POD ${fixed(h.POD, 3)} · frequency bias ${fixed(h.frequency_bias, 2)}`;
}

function intervalText(result: AllIndiaResult, region: (typeof ALL_INDIA_REGIONS)[number], metric: string, digits: number) {
  const e = result.payload.bootstrap.intervals[region][metric];
  if (!e || e.status !== "ok" || e.point == null || !e.interval95) return "not reported";
  return `${fixed(e.point, digits)} [${fixed(e.interval95[0], digits)}, ${fixed(e.interval95[1], digits)}]`;
}

export function AllIndiaRawVerification() {
  const overview = useQuery({ queryKey: ["all-india-raw-overview"], queryFn: () => getAllIndiaOverview(), staleTime: 5 * 60_000 });
  const results = useQueries({ queries: ALL_INDIA_YEARS.map((year) => ({ queryKey: ["all-india-raw-result", year], queryFn: () => getAllIndiaResult(year), staleTime: 5 * 60_000 })) });
  const [year, setYear] = useState<number>(2025);
  const failed = [overview, ...results].find((q) => q.isError);
  if (failed) {
    const error = failed.error;
    const integrity = error instanceof EvidenceApiError && error.code === "SCIENCE_INTEGRITY_FAILURE";
    return <section className="phase5-analysis-block"><ErrorState message={integrity ? `All-India Raw verification integrity check failed: ${error.message}. This is a hard failure.` : error instanceof Error ? error.message : "The all-India Raw verification evidence is unavailable."} /></section>;
  }
  if (!overview.data || results.some((q) => !q.data)) return <section className="phase5-analysis-block"><LoadingState compact label="Loading the all-India Raw verification" /></section>;
  const ov = overview.data;
  const all = results.map((q) => q.data!);
  const chosen = all.find((r) => r.year === year) ?? all[all.length - 1];
  const postHoc = /POST-HOC/.test(chosen.evidence_label);
  return <section className="phase5-analysis-block" aria-labelledby="all-india-raw-heading" data-testid="all-india-raw">
    <h2 id="all-india-raw-heading">All-India verification of Raw GEFS rainfall (no model applied)</h2>
    <div className="zone-banner zone-banner-posthoc" role="note" data-testid="all-india-raw-banner"><strong>Raw only, outside the regional domain no correction exists</strong>
      <span>{ov.definition.forecast}. {ov.decision_rule}</span></div>
    <div className="phase5-controls"><label>All-India year<select value={chosen.year} onChange={(event) => setYear(Number(event.target.value))}>{all.map((r) => <option key={r.year} value={r.year}>{r.evidence_label}</option>)}</select></label></div>
    <div className={postHoc ? "zone-banner zone-banner-posthoc" : "zone-banner"} role="note" data-testid="all-india-raw-year-label"><strong>{chosen.evidence_label}</strong>
      <span>{chosen.payload.cases_scored} cases on {chosen.payload.initialization_dates} initialization dates · excluded: {Object.entries(chosen.payload.excluded_cases).map(([k, v]) => `${v} ${k.toLowerCase().replaceAll("_", " ")}`).join(", ")}</span></div>
    <div className="district-table-wrap"><table className="phase5-table zone-table" data-testid="all-india-raw-table">
      <caption className="sr-only">Raw GEFS rainfall error and heavy-rain skill against IMD by region</caption>
      <thead><tr><th scope="col">Region</th><th scope="col">Land cells</th><th scope="col">RMSE mm per 24 h [95 %]</th><th scope="col">Bias mm [95 %]</th><th scope="col">Heavy rain (64.5 mm per 24 h)</th></tr></thead>
      <tbody>{ALL_INDIA_REGIONS.map((region) => <tr key={region} data-testid={`all-india-row-${region}`}><th scope="row">{REGION_LABEL[region]}</th>
        <td>{chosen.payload.region_cells_with_observation[region]}</td><td>{intervalText(chosen, region, "rmse", 2)}</td><td>{intervalText(chosen, region, "bias", 2)}</td><td>{heavyText(chosen, region)}</td></tr>)}</tbody></table></div>
    <p className="micro-note">{ov.evaluation.uncertainty_note}. {ov.definition.regions.note}. Protocol {ov.protocol_sha256.slice(0, 12)}… · ledger {ov.ledger_sha256.slice(0, 12)}… · manifest {ov.manifest_sha256.slice(0, 12)}…. Historical scientific prototype.</p>
    <p className="micro-note">Not established whatever the result: {ov.not_established.join("; ")}.</p>
    <ul className="phase5-caveats">{ov.caveats.map((c) => <li className="phase5-caveat" key={c}>{c}</li>)}</ul>
  </section>;
}
