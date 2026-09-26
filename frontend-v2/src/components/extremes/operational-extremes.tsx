"use client";

import dynamic from "next/dynamic";
import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { DataSourceIndicator, ErrorState, LoadingState, PageHeading, PrototypeNote } from "@/components/science/common";
import { geometrySchema, getScience } from "@/lib/api/science";
import { ProbabilityLegend } from "@/components/maps/map-legend";
import { getOperationalIndex, operationalGrid, operationalMask } from "@/science/frozen/operational";
import { thresholds } from "@/science/frozen/results";
import { getOperationalFSS, getOperationalProbability, getOperationalProbabilityMetrics, type OperationalYear } from "@/lib/api/operational";
import { loadOperationalCaseList } from "@/lib/operational-case-list";
import { withStaticFallback, type DataSourceMode } from "@/lib/data-source";
import { extractProbabilityEventMetrics } from "@/lib/operational-probability-metrics";
import type { CellSelection } from "@/lib/maps/grid";

const GridMap = dynamic(() => import("@/components/maps/grid-map"), { ssr: false, loading: () => <div className="map-placeholder" /> });
type EventKey = "heavy" | "very_heavy";
type Mode = "probability" | "detection" | "spatial" | "reliability";
type FssScaleResult = { matched_raw: { fss: number | null }; matched_selected: { fss: number | null }; matched_case_count: number };
type FssEventResult = Record<"1" | "3" | "5" | "9", FssScaleResult>;
const YEAR = 2025 as OperationalYear;

// Phase 5A.2D: live-API-primary for the calibrated per-case probability grid
// (getOperationalProbability), the probability metric family (brier/BSS/
// PR-AUC/ROC-AUC/categorical/reliability, getOperationalProbabilityMetrics),
// and FSS (getOperationalFSS). Falls back to the static bundle only on a
// genuine network failure (lib/data-source.ts), same as Casebook/Ensemble/
// Regime Intelligence. Grid geometry (lat/lon centers, valid-cell mask) is
// presentation-only, unrelated to any scientific value, and continues to
// read the static bundle exactly as Ensemble/Regime already do (docs/96
// section 19).
export function OperationalExtremes({ initialCase }: { initialCase?: string }) {
  const [event, setEvent] = useState<EventKey>("heavy");
  const [mode, setMode] = useState<Mode>("probability");
  const [caseId, setCaseId] = useState(initialCase ?? "");
  const [selected, setSelected] = useState<CellSelection | null>(null);

  const index = useQuery({ queryKey: ["operational-index"], queryFn: getOperationalIndex, staleTime: Infinity });
  const caseListResult = useQuery({
    queryKey: ["operational-case-list", YEAR],
    queryFn: () => loadOperationalCaseList(YEAR),
    staleTime: 60_000,
  });
  const cases = useMemo(
    () => (caseListResult.data?.data ?? []).filter((item) => item.probability_source_eligible),
    [caseListResult.data],
  );
  const selectedCase = cases.find((item) => item.case_id === caseId) ?? cases[0];

  const probabilityFieldResult = useQuery({
    queryKey: ["operational-probability-field", YEAR, selectedCase?.case_id, event],
    queryFn: () => withStaticFallback(() => getOperationalProbability(YEAR, selectedCase!.case_id, event), null),
    enabled: Boolean(selectedCase),
  });
  const probabilityMetricsResult = useQuery({
    queryKey: ["operational-probability-metrics", YEAR],
    queryFn: () => withStaticFallback(() => getOperationalProbabilityMetrics(YEAR), null),
  });
  const fssResult = useQuery({
    queryKey: ["operational-fss", YEAR],
    queryFn: () => withStaticFallback(() => getOperationalFSS(YEAR), null),
  });
  const geometry = useQuery({ queryKey: ["district-geometry"], queryFn: () => getScience("/geometry/districts", geometrySchema) });

  const grid = index.data ? operationalGrid(index.data) : null;
  const mask = index.data ? operationalMask(index.data) : null;
  const metric = extractProbabilityEventMetrics(probabilityMetricsResult.data?.data?.metrics, event);
  const fssEvent = fssResult.data?.data?.fss?.[event] as FssEventResult | undefined;
  const threshold = event === "heavy" ? thresholds.heavy : thresholds.veryHeavy;
  const values = probabilityFieldResult.data?.data?.values ?? null;

  const indicatorMode: DataSourceMode | undefined = [probabilityFieldResult.data?.mode, probabilityMetricsResult.data?.mode, fssResult.data?.mode]
    .find((candidate) => candidate && candidate !== "VERIFIED_API") ?? probabilityMetricsResult.data?.mode;

  if (index.isPending || caseListResult.isPending) return <div className="page-content"><LoadingState /></div>;
  if (index.isError) return <div className="page-content"><ErrorState message="Frozen operational-era grid geometry unavailable." /></div>;
  if (caseListResult.isError || !caseListResult.data || caseListResult.data.mode === "UNAVAILABLE") {
    return <div className="page-content"><ErrorState message={caseListResult.data?.message ?? "Frozen probability case catalogue unavailable."} /></div>;
  }
  if (caseListResult.data.mode === "INTEGRITY_FAILURE") {
    return <div className="page-content"><ErrorState message={`Scientific artifact integrity check failed: ${caseListResult.data.message}. This is a hard failure and is not masked by cached data.`} /></div>;
  }

  return <div className="page-content phase5-extremes">
    <PageHeading title="Extreme Rain" subtitle="2025 final historical test · calibrated probability and separate spatial verification" action={<span style={{ display: "flex", gap: 8, alignItems: "center" }}>{indicatorMode ? <DataSourceIndicator mode={indicatorMode} /> : null}<PrototypeNote /></span>} />
    <div className="phase5-context-strip"><strong>2025 FINAL HISTORICAL TEST — COMPLETED</strong><span>232 paired cases · 301,832 paired cells</span><span>Not live warning guidance</span></div>
    <div className="phase5-tab-row" role="group" aria-label="Rainfall threshold"><button type="button" aria-pressed={event === "heavy"} onClick={() => setEvent("heavy")}>Heavy ≥64.5 mm / 24 h</button><button type="button" aria-pressed={event === "very_heavy"} onClick={() => setEvent("very_heavy")}>Very Heavy ≥115.6 mm / 24 h</button></div>
    <div className="phase5-tab-row" role="group" aria-label="Extreme analysis mode">{(["probability", "detection", "spatial", "reliability"] as const).map((item) => <button key={item} type="button" aria-pressed={mode === item} onClick={() => setMode(item)}>{item === "spatial" ? "Spatial skill / FSS" : item[0].toUpperCase() + item.slice(1)}</button>)}</div>
    {probabilityMetricsResult.isPending ? <LoadingState /> : !metric ? <ErrorState message="Probability quality metrics are unavailable." /> : <div className="phase5-metric-strip"><span><small>Brier ↓</small><strong>{metric.brier.toFixed(5)}</strong></span><span><small>BSS ↑</small><strong>+{metric.bss.toFixed(4)}</strong></span><span><small>PR-AUC ↑</small><strong>{metric.pr_auc.toFixed(3)}</strong></span><span><small>ROC-AUC ↑</small><strong>{metric.roc_auc.toFixed(3)}</strong></span><span><small>Observed event cells</small><strong>{metric.observed_event_count.toLocaleString()}</strong></span></div>}
    {mode === "probability" ? <>
      <div className="phase5-controls"><label>Historical case<select value={selectedCase?.case_id ?? ""} onChange={(change) => { setCaseId(change.target.value); setSelected(null); }}>{cases.map((item) => <option value={item.case_id} key={item.case_id}>{item.initialization_utc.slice(0, 10)} · {item.lead_label}</option>)}</select></label>{metric ? <span className="phase5-control-note">Frozen decision threshold: {metric.categorical.decision_threshold_probability.toFixed(2)} · probability scale 0–100%</span> : null}</div>
      {probabilityFieldResult.isPending ? <LoadingState /> : probabilityFieldResult.isError || !values || !grid || !mask ? <ErrorState message="The calibrated probability grid is unavailable for this case." /> : <>
        <div className="phase5-prob-map"><GridMap id="operational-probability" title={`${event === "heavy" ? "Heavy" : "Very Heavy"} calibrated probability`} subtitle={`P(IMD ≥${threshold} mm / 24 h)`} values={values} mask={mask} grid={grid} palette="probability" geometry={geometry.data?.geometry} selected={selected} onSelect={setSelected} /></div><ProbabilityLegend />
        {selected ? <p className="phase5-legend-note">Selected {grid.latitude_centers[selected.row].toFixed(2)}° N, {grid.longitude_centers[selected.column].toFixed(2)}° E: {(() => { const point = values[selected.row]?.[selected.column]; return point != null ? `${(100 * point).toFixed(1)}%` : "masked IMD cell"; })()}</p> : null}
      </>}
    </> : null}
    {mode === "detection" ? <div className="phase5-analysis-block"><h2>Thresholded event detection</h2>{!metric ? <ErrorState message="Categorical detection metrics are unavailable." /> : <><p>Forecast probability ≥{metric.categorical.decision_threshold_probability.toFixed(2)}; evaluated against IMD ≥{threshold} mm / 24 h.</p><div className="phase5-metric-strip"><span><small>POD · detection</small><strong>{metric.categorical.metrics.POD.toFixed(3)}</strong></span><span><small>FAR · false alarms</small><strong>{metric.categorical.metrics.FAR.toFixed(3)}</strong></span><span><small>CSI</small><strong>{metric.categorical.metrics.CSI.toFixed(3)}</strong></span><span><small>ETS</small><strong>{metric.categorical.metrics.ETS.toFixed(3)}</strong></span></div><p className="phase5-caveat">{event === "heavy" ? "Positive Brier skill against the frozen 2023-prevalence reference, but substantial false alarms remain." : "Very-heavy probability discrimination and calibration remain limited by rare events; the false-alarm ratio is high."}</p></>}</div> : null}
    {mode === "spatial" ? <div className="phase5-analysis-block"><h2>Fractions Skill Score · Raw versus preselected M1</h2><p>Matched paired 2-D cases, frozen ≥50% valid-neighborhood rule. Higher is better; sample denominators vary by threshold.</p>{fssResult.isPending ? <LoadingState /> : fssResult.isError || !fssEvent ? <ErrorState message="Spatial skill (FSS) results are unavailable." /> : <div className="phase5-fss-chart" role="img" aria-label={`${event === "heavy" ? "Heavy" : "Very Heavy"} FSS: Raw GEFS exceeds selected Ridge at all four neighborhood sizes`}>{(["1", "3", "5", "9"] as const).map((scale) => <div key={scale}><strong>{scale}×{scale}</strong><span className="phase5-fss-raw" style={{ width: `${100 * (fssEvent[scale].matched_raw.fss ?? 0) / 0.3}%` }}>Raw {(fssEvent[scale].matched_raw.fss ?? 0).toFixed(4)}</span><span className="phase5-fss-selected" style={{ width: `${100 * (fssEvent[scale].matched_selected.fss ?? 0) / 0.3}%` }}>M1 {(fssEvent[scale].matched_selected.fss ?? 0).toFixed(4)}</span><small>{fssEvent[scale].matched_case_count} cases</small></div>)}</div>}<p className="phase5-caveat">Raw GEFS is better at every tested FSS scale. Lower overall RMSE did not translate into better extreme-rain spatial skill.</p></div> : null}
    {mode === "reliability" ? <div className="phase5-analysis-block"><h2>Reliability bins</h2><p>Mean predicted probability versus observed frequency. Sparse upper bins are not evidence of stable calibration.</p>{!metric ? <ErrorState message="Reliability bins are unavailable." /> : <table className="phase5-table"><thead><tr><th>Forecast bin</th><th>Mean predicted</th><th>Observed frequency</th><th>Cells</th></tr></thead><tbody>{metric.reliability.map((bin) => <tr key={bin.bin_lower}><th>{Math.round(bin.bin_lower * 100)}–{Math.round(bin.bin_upper * 100)}%</th><td>{bin.mean_predicted_probability == null ? "Undefined" : `${(100 * bin.mean_predicted_probability).toFixed(1)}%`}</td><td>{bin.observed_event_frequency == null ? "Undefined" : `${(100 * bin.observed_event_frequency).toFixed(1)}%`}</td><td>{bin.sample_count.toLocaleString()}</td></tr>)}</tbody></table>}</div> : null}
    <p className="phase5-caveat">POST-HOC EXPLORATORY VIEW OF THE COMPLETED FINAL TEST. Frozen overall metrics remain the evidence; individual maps are historical case inspection, not a new evaluation.</p>
  </div>;
}
