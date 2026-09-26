"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { DataSourceIndicator, ErrorState, LoadingState, PageHeading, PrototypeNote } from "@/components/science/common";
import { getOperationalQuality } from "@/lib/api/operational";
import { withStaticFallback } from "@/lib/data-source";
import staticQuality from "../../../public/science/operational-v1/quality.json";
import { presentationManifest } from "@/science/frozen/results";

async function loadQuality() {
  return withStaticFallback(
    () => getOperationalQuality(),
    async () => ({
      scheduled_date_lead_cases: Object.values(staticQuality.years).reduce((sum, y) => sum + y.scheduled_cases, 0),
      atmosphere_complete: Object.values(staticQuality.years).reduce((sum, y) => sum + y.atmospheric_complete_cases, 0),
      c00_eligible_total: Object.values(staticQuality.years).reduce((sum, y) => sum + y.c00_source_qc_cases, 0),
      five_member_eligible_total: Object.values(staticQuality.years).reduce((sum, y) => sum + y.full_five_member_cases, 0),
      c00_eligible_by_year: Object.fromEntries(Object.entries(staticQuality.years).map(([y, v]) => [y, v.c00_source_qc_cases])),
      five_member_eligible_by_year: Object.fromEntries(Object.entries(staticQuality.years).map(([y, v]) => [y, v.full_five_member_cases])),
      atmosphere_complete_by_year: Object.fromEntries(Object.entries(staticQuality.years).map(([y, v]) => [y, v.atmospheric_complete_cases])),
      deterministic_eligible_by_year: Object.fromEntries(Object.entries(staticQuality.years).map(([y, v]) => [y, v.paired_deterministic_cases])),
      scheduled_by_year: Object.fromEntries(Object.entries(staticQuality.years).map(([y, v]) => [y, v.scheduled_cases])),
      note: "All selected source messages were acquired; the eligible counts below reflect canonical QC attrition, not download failure.",
    }),
  );
}

const nodes = [
  { title: "NOAA GEFS", detail: "Historical operational source messages; exact selected byte ranges acquired in Phase 4F." },
  { title: "Message selection", detail: "00 UTC initialization, three 24-hour products and five available rainfall members." },
  { title: "Source QC", detail: "Canonical reconstruction and packing-derived tolerances; rejection is not a missing-file count." },
  { title: "Feature extraction", detail: "22 forecast-time deterministic features; 0.5° atmospheric context aligned to 0.25° target centers." },
  { title: "M1 / M2 / pseudo-regime", detail: "2023 training and cross-fit, 2024 validation selection, frozen 2025 final-test inference." },
  { title: "M3 / M4 routing", detail: "Shared frozen regime experts; hard routing and soft blend are secondary comparisons." },
  { title: "Probability + calibration", detail: "26 inputs: 22 forecast features + M2 correction + 3 forecast-only pseudo-regime probabilities." },
  { title: "Verification", detail: "Paired IMD observations, matched masks, continuous, categorical, probabilistic and 2-D FSS results." },
  { title: "Frozen result", detail: "The 2025 holdout was unsealed once; no model-development decision was revised afterward." },
];

const ROLE_LABEL: Record<string, string> = { "2023": "train / cross-fit", "2024": "validate / select", "2025": "final test" };

export function DataQuality() {
  const [selected, setSelected] = useState(0);
  const result = useQuery({ queryKey: ["operational-quality"], queryFn: loadQuality, staleTime: 5 * 60 * 1000 });
  if (result.isPending) return <div className="page-content"><LoadingState label="Loading quality funnel" /></div>;
  const source = result.data;
  if (!source || source.mode === "UNAVAILABLE" || source.mode === "INTEGRITY_FAILURE" || !source.data) {
    return <div className="page-content"><ErrorState message={source?.message ?? "Data quality summary is unavailable."} /></div>;
  }
  const quality = source.data;
  const years = ["2023", "2024", "2025"] as const;
  return <div className="page-content"><PageHeading title="Data Quality & Provenance" subtitle="Source eligibility, scientific lineage and reproducible presentation outputs" action={<span style={{ display: "flex", gap: 8, alignItems: "center" }}><DataSourceIndicator mode={source.mode} /><PrototypeNote /></span>} />
    <div className="phase5-context-strip"><strong>PHASE 4F–4J FROZEN OPERATIONAL CORPUS</strong><span>Required source messages acquired</span><span>QC eligibility is a separate gate</span></div>
    <section className="phase5-analysis-block"><h2>Operational source-to-eligibility flow</h2><div className="phase5-funnel"><div><strong>{quality.scheduled_date_lead_cases.toLocaleString()}</strong><span>Scheduled date × lead</span></div><div><strong>{quality.atmosphere_complete.toLocaleString()}</strong><span>Atmospheric complete</span></div><div><strong>{quality.c00_eligible_total.toLocaleString()}</strong><span>c00 source-QC eligible</span></div><div><strong>{quality.five_member_eligible_total.toLocaleString()}</strong><span>Full five-member subset</span></div></div><p className="phase5-caveat">{quality.note}</p></section>
    <section className="phase5-analysis-block"><h2>By year</h2><table className="phase5-table"><thead><tr><th>Year / role</th><th>Scheduled</th><th>Atmosphere</th><th>c00 QC</th><th>Five-member</th><th>Deterministic-eligible</th></tr></thead><tbody>{years.map((year) => <tr key={year}><th>{year} · {ROLE_LABEL[year]}</th><td>{quality.scheduled_by_year[year]}</td><td>{quality.atmosphere_complete_by_year[year]}</td><td>{quality.c00_eligible_by_year[year]}</td><td>{quality.five_member_eligible_by_year[year]}</td><td>{quality.deterministic_eligible_by_year[year]}</td></tr>)}</tbody></table></section>
    <section className="phase5-analysis-block"><h2>Packing-aware rainfall reconstruction</h2><p>Forecast accumulation total minus prefix accumulation can produce a small negative decoded residual because GRIB messages have finite packing precision. The accepted tolerance is derived from the relevant message packing quanta. There is no universal fixed 0.055-mm rule.</p></section>
    <section className="phase5-analysis-block"><h2>Read-only lineage</h2><div className="phase5-dag"><div role="group" aria-label="Scientific lineage nodes">{nodes.map((node, index) => <button type="button" key={node.title} aria-pressed={selected === index} onClick={() => setSelected(index)}>{node.title}</button>)}</div><aside><strong>{nodes[selected].title}</strong><p>{nodes[selected].detail}</p><details><summary>Artifact identity</summary><code>{presentationManifest.source_hashes.phase4j_final_test_result}</code><small>Phase 4J FINAL_TEST_RESULT SHA-256</small></details></aside></div></section>
  </div>;
}
