"use client";

import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { useMemo, useState } from "react";
import { COVERAGE_STATUSES, EvidenceApiError, getPsCoverage, type CoverageStatus, type PsCoverageRow } from "@/lib/api/evidence";
import { ErrorState, LoadingState, PageHeading, PrototypeNote } from "@/components/science/common";
import { HashChip } from "@/components/ui/hash-chip";

const STATUS_LABEL: Record<CoverageStatus, string> = { IMPLEMENTED: "Implemented", PARTIAL: "Partial", PLANNED: "Planned" };
const STATUS_HELP: Record<CoverageStatus, string> = {
  IMPLEMENTED: "Exists, is reachable in the app and is backed by hash-verified evidence.",
  PARTIAL: "Exists with a material gap that is stated on the row.",
  PLANNED: "Does not exist yet; it is never counted as implemented.",
};

function formatFact(value: number, format: "mm2" | "score3" | "int") {
  return format === "int" ? value.toLocaleString("en-GB") : format === "mm2" ? value.toFixed(2) : value.toFixed(3);
}

function Row({ row }: { row: PsCoverageRow }) {
  return <tr>
    <th scope="row"><strong>{row.requirement}</strong>
      <span className="micro-note">{row.ps_ids.length ? row.ps_ids.join(", ") : "beyond the PS minimum"}{row.ps_mandatory ? " · mandatory" : ""}</span></th>
    <td><span className={`coverage-status coverage-${row.status.toLowerCase()}`}>{STATUS_LABEL[row.status]}</span></td>
    <td><p>{row.summary}</p>
      {row.limitation ? <p className="phase5-caveat"><b>{row.status === "IMPLEMENTED" ? "Limitation: " : "Gap: "}</b>{row.limitation}</p> : null}
      {row.facts.length ? <ul className="coverage-facts" aria-label={`Evidence values for ${row.requirement}`}>{row.facts.map((fact) => <li key={fact.label + fact.source}>
        <span>{fact.label}</span> <b>{formatFact(fact.value, fact.format)}</b> <span className="micro-note">{/POST-HOC/.test(fact.evidence_label) ? "post-hoc analysis of a completed final test" : "development evidence"} · {fact.source_sha256.slice(0, 8)}…</span></li>)}</ul> : null}</td>
    <td>{row.pages.length ? <ul className="coverage-links">{row.pages.map((page) => <li key={page.href}><Link href={page.href}>{page.label}</Link></li>)}</ul> : <span className="micro-note">no page yet</span>}
      {row.docs.length ? <details className="micro-note"><summary>Evidence documents</summary><ul>{row.docs.map((doc) => <li key={doc}><code>{doc}</code></li>)}</ul></details> : null}</td>
  </tr>;
}

export function PsCoverage() {
  const [filter, setFilter] = useState<CoverageStatus | "ALL">("ALL");
  const query = useQuery({ queryKey: ["ps-coverage"], queryFn: () => getPsCoverage(), staleTime: 5 * 60_000 });
  const rows = useMemo(() => (query.data?.rows ?? []).filter((row) => filter === "ALL" || row.status === filter), [query.data, filter]);
  const groups = useMemo(() => [...new Set(rows.map((row) => row.group))], [rows]);

  if (query.isPending) return <div className="page-content"><LoadingState label="Loading requirement coverage" /></div>;
  if (query.isError || !query.data) {
    const error = query.error;
    const integrity = error instanceof EvidenceApiError && error.code === "SCIENCE_INTEGRITY_FAILURE";
    return <div className="page-content"><ErrorState message={integrity ? `Coverage integrity check failed: ${error.message}. This is a hard failure.` : error instanceof Error ? error.message : "Requirement coverage is unavailable."} /></div>;
  }
  const data = query.data;
  const mandatoryTotal = Object.values(data.mandatory_counts).reduce((sum, value) => sum + value, 0);

  return <div className="page-content compliance-page">
    <PageHeading title="SIH26080 Requirement Coverage" subtitle="What the problem statement asks for, what exists, and what does not · every figure is read from hash-verified evidence" action={<PrototypeNote />} />
    <div className="phase5-metric-strip" aria-label="Coverage summary">
      {COVERAGE_STATUSES.map((status) => <span key={status}><b>{STATUS_LABEL[status]}</b> {data.counts[status] ?? 0} of {data.rows.length} rows · {data.mandatory_counts[status] ?? 0} of {mandatoryTotal} mandatory</span>)}
    </div>
    <ul className="phase5-caveats">{data.rules.map((rule) => <li className="phase5-caveat" key={rule}>{rule}</li>)}</ul>
    <div className="phase5-tab-row" role="group" aria-label="Filter by status">
      <button type="button" aria-pressed={filter === "ALL"} onClick={() => setFilter("ALL")}>All rows</button>
      {COVERAGE_STATUSES.map((status) => <button key={status} type="button" aria-pressed={filter === status} onClick={() => setFilter(status)} title={STATUS_HELP[status]}>{STATUS_LABEL[status]}</button>)}
    </div>
    {groups.map((group) => <section key={group} className="phase5-analysis-block" aria-labelledby={`group-${group.replace(/\W+/g, "-")}`}>
      <h2 id={`group-${group.replace(/\W+/g, "-")}`}>{group}</h2>
      <div className="district-table-wrap"><table className="phase5-table coverage-table"><caption className="sr-only">{group}: requirement, status, evidence and links</caption>
        <thead><tr><th scope="col">Requirement</th><th scope="col">Status</th><th scope="col">What exists and what is missing</th><th scope="col">Where to see it</th></tr></thead>
        <tbody>{rows.filter((row) => row.group === group).map((row) => <Row key={row.id} row={row} />)}</tbody></table></div>
    </section>)}
    {rows.length === 0 ? <p className="micro-note">No rows have this status.</p> : null}
    <p className="micro-note">Coverage manifest SHA-256 <HashChip hash={data.coverage_sha256} /> · Historical scientific prototype, not an operational service. Regimes are forecast-only pseudo-labels; consumed final-test years are post-hoc analyses.</p>
  </div>;
}
