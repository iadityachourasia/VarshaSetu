"use client";

import dynamic from "next/dynamic";
import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { ErrorState, LoadingState, PageHeading, PrototypeNote } from "@/components/science/common";
import { RainLegend } from "@/components/maps/map-legend";
import { geometrySchema, getScience } from "@/lib/api/science";
import { expandedField, getOperationalCase, getOperationalIndex, operationalGrid, operationalMask } from "@/science/frozen/operational";
import { final2025, thresholds } from "@/science/frozen/results";
import type { CellSelection } from "@/lib/maps/grid";

const GridMap = dynamic(() => import("@/components/maps/grid-map"), { ssr: false, loading: () => <div className="map-placeholder" /> });
const members = ["c00", "p01", "p02", "p03", "p04"] as const;

export function OperationalEnsemble({ initialCase }: { initialCase?: string }) {
  const [caseId, setCaseId] = useState(initialCase ?? "");
  const [member, setMember] = useState<typeof members[number]>("c00");
  const [selected, setSelected] = useState<CellSelection | null>(null);
  const index = useQuery({ queryKey: ["operational-index"], queryFn: getOperationalIndex, staleTime: Infinity });
  const cases = index.data?.cases.filter((item) => item.year === 2025 && item.has_ensemble) ?? [];
  const summary = cases.find((item) => item.case_id === caseId) ?? cases[0];
  const detail = useQuery({ queryKey: ["operational-case", summary?.case_id], queryFn: () => getOperationalCase(summary!), enabled: Boolean(summary) });
  const geometry = useQuery({ queryKey: ["district-geometry"], queryFn: () => getScience("/geometry/districts", geometrySchema) });
  const mapValues = useMemo(() => detail.data?.ensemble_members?.[member] && index.data ? expandedField(index.data, detail.data.ensemble_members[member]) : null, [detail.data, index.data, member]);
  if (index.isPending) return <div className="page-content"><LoadingState /></div>;
  if (index.isError) return <div className="page-content"><ErrorState message="Frozen ensemble presentation artifacts unavailable." /></div>;
  const position = selected ? index.data.pixel_indices.indexOf(selected.row * 49 + selected.column) : -1;
  const cellMembers = position >= 0 && detail.data?.ensemble_members ? members.map((name) => detail.data!.ensemble_members![name][position]) : null;
  const heavyFraction = cellMembers ? cellMembers.filter((value) => value >= thresholds.heavy).length : null;
  const veryHeavyFraction = cellMembers ? cellMembers.filter((value) => value >= thresholds.veryHeavy).length : null;
  return <div className="page-content"><PageHeading title="Ensemble & Uncertainty" subtitle="Available five-member subset · c00, p01, p02, p03, p04" action={<PrototypeNote />} />
    <div className="phase5-context-strip"><strong>MATCHED 75-CASE SUBSET</strong><span>97,575 paired cells</span><span>Not a full operational ensemble</span></div>
    <div className="phase5-controls"><label>Case<select value={summary?.case_id ?? ""} onChange={(event) => { setCaseId(event.target.value); setSelected(null); }}>{cases.map((item) => <option value={item.case_id} key={item.case_id}>{item.initialization_utc.slice(0, 10)} · Day {item.lead_hours / 24}</option>)}</select></label><label>Member<select value={member} onChange={(event) => setMember(event.target.value as typeof member)}>{members.map((name) => <option key={name} value={name}>{name}</option>)}</select></label></div>
    {detail.isPending ? <LoadingState /> : detail.isError || !mapValues ? <ErrorState message="Five-member fields are unavailable for the selected case." /> : <><div className="phase5-prob-map"><GridMap id={`member-${member}`} title={`${member} rainfall`} subtitle="Frozen member field · mm / 24 h" values={mapValues} mask={operationalMask(index.data)} grid={operationalGrid(index.data)} palette="rainfall" geometry={geometry.data?.geometry} selected={selected} onSelect={setSelected} /></div><RainLegend /></>}
    <section className="phase5-analysis-block"><h2>Selected-cell member distribution</h2>{cellMembers ? <><div className="phase5-member-values">{members.map((name, index) => <span key={name}><small>{name}</small><strong>{cellMembers[index].toFixed(2)} mm</strong></span>)}</div><p>Heavy member threshold fraction: <strong>{heavyFraction}/5 = {((heavyFraction ?? 0) * 20).toFixed(0)}%</strong>. Very Heavy: <strong>{veryHeavyFraction}/5 = {((veryHeavyFraction ?? 0) * 20).toFixed(0)}%</strong>.</p></> : <p>Click or keyboard-select a valid map cell to inspect the five member values.</p>}<p className="phase5-caveat">Member exceedance fraction is not the calibrated ML probability. Five members are an available source subset, not the full operational GEFS ensemble.</p></section>
    <section className="phase5-analysis-block"><h2>Matched-population probability comparison</h2><table className="phase5-table"><thead><tr><th>Event</th><th>Five-member fraction Brier</th><th>Calibrated ML Brier</th><th>Population</th></tr></thead><tbody><tr><th>Heavy ≥64.5 mm</th><td>{final2025.ensemble.heavy.five_member_fraction.brier.toFixed(5)}</td><td>{final2025.ensemble.heavy.frozen_ML_same_cells.brier.toFixed(5)}</td><td>75 cases · 97,575 cells</td></tr><tr><th>Very Heavy ≥115.6 mm</th><td>{final2025.ensemble.very_heavy.five_member_fraction.brier.toFixed(5)}</td><td>{final2025.ensemble.very_heavy.frozen_ML_same_cells.brier.toFixed(5)}</td><td>75 cases · 97,575 cells</td></tr></tbody></table><p className="phase5-caveat">This matched 75-case comparison must not be interpreted as a head-to-head result on all 232 final-test cases.</p></section>
  </div>;
}
