"use client";

import dynamic from "next/dynamic";
import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { DataSourceIndicator, ErrorState, LoadingState, PageHeading, PrototypeNote } from "@/components/science/common";
import { RainLegend } from "@/components/maps/map-legend";
import { geometrySchema, getScience } from "@/lib/api/science";
import { getOperationalIndex, operationalGrid, operationalMask } from "@/science/frozen/operational";
import { getOperationalEnsemble, getOperationalEnsembleMetrics, type OperationalYear } from "@/lib/api/operational";
import { loadOperationalCaseList } from "@/lib/operational-case-list";
import { withStaticFallback } from "@/lib/data-source";
import type { CellSelection } from "@/lib/maps/grid";

const GridMap = dynamic(() => import("@/components/maps/grid-map"), { ssr: false, loading: () => <div className="map-placeholder" /> });
const MEMBERS = ["c00", "p01", "p02", "p03", "p04"] as const;
const HEAVY_THRESHOLD_MM = 64.5;
const VERY_HEAVY_THRESHOLD_MM = 115.6;

// Phase 5A.2C: live-API-primary for both the per-case ensemble grids and the
// matched-75-case comparison metrics; falls back to the static bundle only
// on a genuine network failure (lib/data-source.ts).
export function OperationalEnsemble({ initialCase }: { initialCase?: string }) {
  const [caseId, setCaseId] = useState(initialCase ?? "");
  const [member, setMember] = useState<(typeof MEMBERS)[number]>("c00");
  const [selected, setSelected] = useState<CellSelection | null>(null);
  const index = useQuery({ queryKey: ["operational-index"], queryFn: getOperationalIndex, staleTime: Infinity });
  const caseListResult = useQuery({
    queryKey: ["operational-case-list", 2025],
    queryFn: () => loadOperationalCaseList(2025 as OperationalYear),
    staleTime: 60_000,
  });
  const cases = useMemo(
    () => (caseListResult.data?.data ?? []).filter((item) => item.ensemble_source_eligible),
    [caseListResult.data],
  );
  const caseListItem = cases.find((item) => item.case_id === caseId) ?? cases[0];
  const ensembleResult = useQuery({
    queryKey: ["operational-ensemble", caseListItem?.case_id],
    queryFn: () => withStaticFallback(() => getOperationalEnsemble(2025, caseListItem!.case_id), null),
    enabled: Boolean(caseListItem),
  });
  const metricsResult = useQuery({
    queryKey: ["operational-ensemble-metrics"],
    queryFn: () => withStaticFallback(() => getOperationalEnsembleMetrics(2025), null),
  });
  const geometry = useQuery({ queryKey: ["district-geometry"], queryFn: () => getScience("/geometry/districts", geometrySchema) });

  const grid = index.data ? operationalGrid(index.data) : null;
  const mask = index.data ? operationalMask(index.data) : null;
  const memberGrid = ensembleResult.data?.data?.members.find((m) => m.member === member);
  const mapValues = useMemo(() => {
    if (!memberGrid?.values || !index.data) return null;
    // Live grids are already fully expanded 49x49 matrices -- no reshape needed.
    return memberGrid.values;
  }, [memberGrid, index.data]);

  if (index.isPending || caseListResult.isPending) return <div className="page-content"><LoadingState /></div>;
  if (index.isError) return <div className="page-content"><ErrorState message="Frozen ensemble grid geometry unavailable." /></div>;
  if (caseListResult.isError || !caseListResult.data || caseListResult.data.mode === "UNAVAILABLE") {
    return <div className="page-content"><ErrorState message={caseListResult.data?.message ?? "Frozen ensemble case catalogue unavailable."} /></div>;
  }
  if (caseListResult.data.mode === "INTEGRITY_FAILURE") {
    return <div className="page-content"><ErrorState message={`Scientific artifact integrity check failed: ${caseListResult.data.message}. This is a hard failure and is not masked by cached data.`} /></div>;
  }

  const position = selected && index.data ? index.data.pixel_indices.indexOf(selected.row * 49 + selected.column) : -1;
  const cellMembers = position >= 0 && ensembleResult.data?.data
    ? MEMBERS.map((name) => {
        const memberData = ensembleResult.data!.data!.members.find((m) => m.member === name);
        return memberData?.values?.[selected!.row]?.[selected!.column] ?? null;
      })
    : null;
  const eligibleCellValues = cellMembers?.filter((value): value is number => value != null) ?? null;
  const heavyFraction = eligibleCellValues ? eligibleCellValues.filter((value) => value >= HEAVY_THRESHOLD_MM).length : null;
  const veryHeavyFraction = eligibleCellValues ? eligibleCellValues.filter((value) => value >= VERY_HEAVY_THRESHOLD_MM).length : null;
  const eligibleCount = eligibleCellValues?.length ?? 0;

  const ensembleSourceMode = ensembleResult.data?.mode;
  const metricsData = metricsResult.data?.data?.metrics as {
    case_count: number; cell_count: number;
    heavy: { five_member_fraction: { brier: number }; frozen_ML_same_cells: { brier: number } };
    very_heavy: { five_member_fraction: { brier: number }; frozen_ML_same_cells: { brier: number } };
  } | undefined;

  return <div className="page-content"><PageHeading title="Ensemble & Uncertainty" subtitle="Available five-member subset · c00, p01, p02, p03, p04" action={<span style={{ display: "flex", gap: 8, alignItems: "center" }}>{ensembleSourceMode ? <DataSourceIndicator mode={ensembleSourceMode} /> : null}<PrototypeNote /></span>} />
    <div className="phase5-context-strip"><strong>MATCHED 75-CASE SUBSET</strong><span>97,575 paired cells</span><span>Not a full operational ensemble</span></div>
    <div className="phase5-controls"><label>Case<select value={caseListItem?.case_id ?? ""} onChange={(event) => { setCaseId(event.target.value); setSelected(null); }}>{cases.map((item) => <option value={item.case_id} key={item.case_id}>{item.initialization_utc.slice(0, 10)} · {item.lead_label}</option>)}</select></label><label>Member<select value={member} onChange={(event) => setMember(event.target.value as typeof member)}>{MEMBERS.map((name) => <option key={name} value={name}>{name}</option>)}</select></label></div>
    {ensembleResult.isPending ? <LoadingState /> : ensembleResult.isError || !mapValues || !grid || !mask ? <ErrorState message="Five-member fields are unavailable for the selected case." /> : <><div className="phase5-prob-map"><GridMap id={`member-${member}`} title={`${member} rainfall`} subtitle="Frozen member field · mm / 24 h" values={mapValues} mask={mask} grid={grid} palette="rainfall" geometry={geometry.data?.geometry} selected={selected} onSelect={setSelected} /></div><RainLegend /></>}
    <section className="phase5-analysis-block"><h2>Selected-cell member distribution</h2>{eligibleCellValues && eligibleCellValues.length > 0 ? <><div className="phase5-member-values">{MEMBERS.map((name) => {
      const memberData = ensembleResult.data?.data?.members.find((m) => m.member === name);
      const value = position >= 0 && memberData?.values ? memberData.values[selected!.row]?.[selected!.column] : null;
      return <span key={name}><small>{name}{memberData && !memberData.qc_eligible ? " (QC failed)" : ""}</small><strong>{value != null ? `${value.toFixed(2)} mm` : "—"}</strong></span>;
    })}</div><p>Heavy member threshold fraction: <strong>{heavyFraction}/{eligibleCount} = {eligibleCount ? (((heavyFraction ?? 0) / eligibleCount) * 100).toFixed(0) : 0}%</strong>. Very Heavy: <strong>{veryHeavyFraction}/{eligibleCount} = {eligibleCount ? (((veryHeavyFraction ?? 0) / eligibleCount) * 100).toFixed(0) : 0}%</strong>.</p></> : <p>Click or keyboard-select a valid map cell to inspect the five member values.</p>}<p className="phase5-caveat">Member exceedance fraction is not the calibrated ML probability. Five members are an available source subset, not the full operational GEFS ensemble. QC-failed members remain listed, never silently dropped.</p></section>
    <section className="phase5-analysis-block" tabIndex={0} aria-label="Matched-population probability comparison table"><h2>Matched-population probability comparison</h2>{metricsResult.isPending ? <LoadingState /> : !metricsData ? <ErrorState message="Matched-population comparison metrics are unavailable." /> : <table className="phase5-table"><thead><tr><th>Event</th><th>Five-member fraction Brier</th><th>Calibrated ML Brier</th><th>Population</th></tr></thead><tbody><tr><th>Heavy ≥64.5 mm</th><td>{metricsData.heavy.five_member_fraction.brier.toFixed(5)}</td><td>{metricsData.heavy.frozen_ML_same_cells.brier.toFixed(5)}</td><td>{metricsData.case_count} cases · {metricsData.cell_count.toLocaleString("en-GB")} cells</td></tr><tr><th>Very Heavy ≥115.6 mm</th><td>{metricsData.very_heavy.five_member_fraction.brier.toFixed(5)}</td><td>{metricsData.very_heavy.frozen_ML_same_cells.brier.toFixed(5)}</td><td>{metricsData.case_count} cases · {metricsData.cell_count.toLocaleString("en-GB")} cells</td></tr></tbody></table>}<p className="phase5-caveat">This matched 75-case comparison must not be interpreted as a head-to-head result on all 232 final-test cases.</p></section>
  </div>;
}

