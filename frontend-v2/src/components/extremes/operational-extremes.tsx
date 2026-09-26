"use client";

import dynamic from "next/dynamic";
import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { ErrorState, LoadingState, PageHeading, PrototypeNote } from "@/components/science/common";
import { geometrySchema, getScience } from "@/lib/api/science";
import { ProbabilityLegend } from "@/components/maps/map-legend";
import { expandedField, getOperationalCase, getOperationalIndex, operationalGrid, operationalMask } from "@/science/frozen/operational";
import { final2025, thresholds } from "@/science/frozen/results";
import type { CellSelection } from "@/lib/maps/grid";

const GridMap = dynamic(() => import("@/components/maps/grid-map"), { ssr: false, loading: () => <div className="map-placeholder" /> });
type EventKey = "heavy" | "very_heavy";
type Mode = "probability" | "detection" | "spatial" | "reliability";

export function OperationalExtremes({ initialCase }: { initialCase?: string }) {
  const [event, setEvent] = useState<EventKey>("heavy");
  const [mode, setMode] = useState<Mode>("probability");
  const [caseId, setCaseId] = useState(initialCase ?? "");
  const [selected, setSelected] = useState<CellSelection | null>(null);
  const index = useQuery({ queryKey: ["operational-index"], queryFn: getOperationalIndex, staleTime: Infinity });
  const cases = index.data?.cases.filter((item) => item.year === 2025) ?? [];
  const summary = cases.find((item) => item.case_id === caseId) ?? cases[0];
  const detail = useQuery({ queryKey: ["operational-case", summary?.case_id], queryFn: () => getOperationalCase(summary!), enabled: Boolean(summary) });
  const geometry = useQuery({ queryKey: ["district-geometry"], queryFn: () => getScience("/geometry/districts", geometrySchema) });
  const metric = final2025.probability[event].metrics;
  const categorical = metric.categorical.metrics;
  const threshold = event === "heavy" ? thresholds.heavy : thresholds.veryHeavy;
  const fss = final2025.fss[event];
  const field = detail.data?.probabilities?.[event];
  if (index.isPending) return <div className="page-content"><LoadingState /></div>;
  if (index.isError) return <div className="page-content"><ErrorState message="Frozen operational-era case index unavailable." /></div>;
  return <div className="page-content phase5-extremes">
    <PageHeading title="Extreme Rain" subtitle="2025 final historical test · calibrated probability and separate spatial verification" action={<PrototypeNote />} />
    <div className="phase5-context-strip"><strong>2025 FINAL HISTORICAL TEST — COMPLETED</strong><span>232 paired cases · 301,832 paired cells</span><span>Not live warning guidance</span></div>
    <div className="phase5-tab-row" role="group" aria-label="Rainfall threshold"><button type="button" aria-pressed={event === "heavy"} onClick={() => setEvent("heavy")}>Heavy ≥64.5 mm / 24 h</button><button type="button" aria-pressed={event === "very_heavy"} onClick={() => setEvent("very_heavy")}>Very Heavy ≥115.6 mm / 24 h</button></div>
    <div className="phase5-tab-row" role="group" aria-label="Extreme analysis mode">{(["probability", "detection", "spatial", "reliability"] as const).map((item) => <button key={item} type="button" aria-pressed={mode === item} onClick={() => setMode(item)}>{item === "spatial" ? "Spatial skill / FSS" : item[0].toUpperCase() + item.slice(1)}</button>)}</div>
    <div className="phase5-metric-strip"><span><small>Brier ↓</small><strong>{metric.brier.toFixed(5)}</strong></span><span><small>BSS ↑</small><strong>+{metric.bss.toFixed(4)}</strong></span><span><small>PR-AUC ↑</small><strong>{metric.pr_auc.toFixed(3)}</strong></span><span><small>ROC-AUC ↑</small><strong>{metric.roc_auc.toFixed(3)}</strong></span><span><small>Observed event cells</small><strong>{metric.observed_event_count.toLocaleString()}</strong></span></div>
    {mode === "probability" ? <>
      <div className="phase5-controls"><label>Historical case<select value={summary?.case_id ?? ""} onChange={(event) => { setCaseId(event.target.value); setSelected(null); }}>{cases.map((item) => <option value={item.case_id} key={item.case_id}>{item.initialization_utc.slice(0, 10)} · Day {item.lead_hours / 24}</option>)}</select></label><span className="phase5-control-note">Frozen decision threshold: {metric.categorical.decision_threshold_probability.toFixed(2)} · probability scale 0–100%</span></div>
      {detail.isPending ? <LoadingState /> : detail.isError || !field ? <ErrorState message="The calibrated probability grid is unavailable for this case." /> : <>
        <div className="phase5-prob-map"><GridMap id="operational-probability" title={`${event === "heavy" ? "Heavy" : "Very Heavy"} calibrated probability`} subtitle={`P(IMD ≥${threshold} mm / 24 h)`} values={expandedField(index.data, field)} mask={operationalMask(index.data)} grid={operationalGrid(index.data)} palette="probability" geometry={geometry.data?.geometry} selected={selected} onSelect={setSelected} /></div><ProbabilityLegend />
        {selected ? <p className="phase5-legend-note">Selected {index.data.grid.latitude_centers[selected.row].toFixed(2)}° N, {index.data.grid.longitude_centers[selected.column].toFixed(2)}° E: {(() => { const position = index.data.pixel_indices.indexOf(selected.row * 49 + selected.column); return position >= 0 ? `${(100 * field[position]).toFixed(1)}%` : "masked IMD cell"; })()}</p> : null}
      </>}
    </> : null}
    {mode === "detection" ? <div className="phase5-analysis-block"><h2>Thresholded event detection</h2><p>Forecast probability ≥{metric.categorical.decision_threshold_probability.toFixed(2)}; evaluated against IMD ≥{threshold} mm / 24 h.</p><div className="phase5-metric-strip"><span><small>POD · detection</small><strong>{categorical.POD.toFixed(3)}</strong></span><span><small>FAR · false alarms</small><strong>{categorical.FAR.toFixed(3)}</strong></span><span><small>CSI</small><strong>{categorical.CSI.toFixed(3)}</strong></span><span><small>ETS</small><strong>{categorical.ETS.toFixed(3)}</strong></span></div><p className="phase5-caveat">{event === "heavy" ? "Positive Brier skill against the frozen 2023-prevalence reference, but substantial false alarms remain." : "Very-heavy probability discrimination and calibration remain limited by rare events; the false-alarm ratio is high."}</p></div> : null}
    {mode === "spatial" ? <div className="phase5-analysis-block"><h2>Fractions Skill Score · Raw versus preselected M1</h2><p>Matched paired 2-D cases, frozen ≥50% valid-neighborhood rule. Higher is better; sample denominators vary by threshold.</p><div className="phase5-fss-chart" role="img" aria-label={`${event === "heavy" ? "Heavy" : "Very Heavy"} FSS: Raw GEFS exceeds selected Ridge at all four neighborhood sizes`}>{(["1", "3", "5", "9"] as const).map((scale) => <div key={scale}><strong>{scale}×{scale}</strong><span className="phase5-fss-raw" style={{ width: `${100 * (fss[scale].matched_raw.fss ?? 0) / 0.3}%` }}>Raw {(fss[scale].matched_raw.fss ?? 0).toFixed(4)}</span><span className="phase5-fss-selected" style={{ width: `${100 * (fss[scale].matched_selected.fss ?? 0) / 0.3}%` }}>M1 {(fss[scale].matched_selected.fss ?? 0).toFixed(4)}</span><small>{fss[scale].matched_case_count} cases</small></div>)}</div><p className="phase5-caveat">Raw GEFS is better at every tested FSS scale. Lower overall RMSE did not translate into better extreme-rain spatial skill.</p></div> : null}
    {mode === "reliability" ? <div className="phase5-analysis-block"><h2>Reliability bins</h2><p>Mean predicted probability versus observed frequency. Sparse upper bins are not evidence of stable calibration.</p><table className="phase5-table"><thead><tr><th>Forecast bin</th><th>Mean predicted</th><th>Observed frequency</th><th>Cells</th></tr></thead><tbody>{metric.reliability.map((bin) => <tr key={bin.bin_lower}><th>{Math.round(bin.bin_lower * 100)}–{Math.round(bin.bin_upper * 100)}%</th><td>{bin.mean_predicted_probability == null ? "Undefined" : `${(100 * bin.mean_predicted_probability).toFixed(1)}%`}</td><td>{bin.observed_event_frequency == null ? "Undefined" : `${(100 * bin.observed_event_frequency).toFixed(1)}%`}</td><td>{bin.sample_count.toLocaleString()}</td></tr>)}</tbody></table></div> : null}
    <p className="phase5-caveat">POST-HOC EXPLORATORY VIEW OF THE COMPLETED FINAL TEST. Frozen overall metrics remain the evidence; individual maps are historical case inspection, not a new evaluation.</p>
  </div>;
}
