"use client";

import dynamic from "next/dynamic";
import { useRouter } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { useRef, useState } from "react";
import type { Map as MapLibreMap } from "maplibre-gl";
import type { CaseSummary, Verification } from "@/lib/api/science";
import { geometrySchema, getScience, probabilitiesSchema, rainfallSchema } from "@/lib/api/science";
import { nearestValidCell, type CellSelection } from "@/lib/maps/grid";
import { mm, percent, score, utc } from "@/lib/format";
import { CaseSelector } from "@/components/science/case-selector";
import { ErrorState, LoadingState, Metric, PageHeading, PrototypeNote, SectionHeading } from "@/components/science/common";
import { ProbabilityLegend } from "@/components/maps/map-legend";
import { MapControls } from "@/components/maps/map-controls";
import { fitToData } from "@/components/maps/use-weather-map";
import { ExtremeClassifierView } from "./extreme-classifier-view";
import { Segmented } from "@/components/ui/segmented";

const GridMap = dynamic(() => import("@/components/maps/grid-map"), { ssr: false, loading: () => <div className="map-placeholder" aria-label="Loading probability map" /> });
const ReliabilityChart = dynamic(() => import("@/components/verification/verification-charts").then((module) => module.ReliabilityChart), { ssr: false, loading: () => <div className="chart-placeholder" /> });

export function ExtremesWorkspace({ cases, demos, initialCase, verification }: { cases: CaseSummary[]; demos: CaseSummary[]; initialCase: string; verification: Verification }) {
  const router = useRouter();
  const [caseId, setCaseId] = useState(initialCase);
  const [threshold, setThreshold] = useState<"heavy" | "very_heavy">("heavy");
  const [selected, setSelected] = useState<CellSelection | null>(null);
  const [source, setSource] = useState<"calibrated" | "classifier">("calibrated");
  const mapRef = useRef<MapLibreMap | null>(null);
  const mapPanel = useRef<HTMLDivElement>(null);
  const probability = useQuery({ queryKey: ["probability", caseId], queryFn: () => getScience(`/cases/${caseId}/probabilities`, probabilitiesSchema) });
  const rainfall = useQuery({ queryKey: ["rainfall", caseId], queryFn: () => getScience(`/cases/${caseId}/rainfall`, rainfallSchema) });
  const geometry = useQuery({ queryKey: ["district-geometry"], queryFn: () => getScience("/geometry/districts", geometrySchema) });
  const record = cases.find((item) => item.case_id === caseId);
  const metric = verification.metrics.targets[threshold];
  const values = threshold === "heavy" ? probability.data?.data.heavy_probability : probability.data?.data.very_heavy_probability;
  const limit = threshold === "heavy" ? 64.5 : 115.6;
  const activeCell = selected ?? (rainfall.data ? nearestValidCell(rainfall.data.data.valid_mask) : null);
  const point = activeCell && values ? values[activeCell.row]?.[activeCell.column] : null;
  const observed = activeCell && rainfall.data ? rainfall.data.data.observed[activeCell.row]?.[activeCell.column] : null;
  const valid = activeCell && rainfall.data ? rainfall.data.data.valid_mask[activeCell.row]?.[activeCell.column] : false;
  const resetExtent = () => { if (mapRef.current && probability.data) fitToData(mapRef.current, probability.data.data.grid.bounds_west_south_east_north); };
  const fullscreen = async () => { if (document.fullscreenElement) await document.exitFullscreen(); else await mapPanel.current?.requestFullscreen(); mapRef.current?.resize(); };
  return <div className="page-content extremes-page">
    <PageHeading title="Extreme Rain" subtitle={source === "calibrated" ? "2019 historical reforecast probabilities, calibrated on 2018; not live warnings or 2025 forecasts." : "2019 historical reforecast: scores of the dedicated heavy-rain classifier (reforecast study). Scores are not calibrated probabilities; not live warnings."} action={<PrototypeNote />} />
    <CaseSelector cases={cases} demos={demos} selectedId={caseId} onSelect={(id) => { setCaseId(id); setSelected(null); router.replace(`/extremes?case=${encodeURIComponent(id)}`, { scroll: false }); }} />
    <div className="corrected-model-choice" data-testid="extreme-source-choice"><span className="small-label">OUTPUT</span><Segmented label="Heavy-rain output" value={source} onChange={setSource} options={[{ value: "calibrated", label: "Calibrated probability (frozen, 2018 calibration)" }, { value: "classifier", label: "Heavy-rain classifier B1 (reforecast study)" }]} /></div>
    <Segmented label="Event threshold" value={threshold} onChange={setThreshold} options={[{ value: "heavy", label: "Heavy · ≥64.5 mm / 24 h" }, { value: "very_heavy", label: "Very Heavy · ≥115.6 mm / 24 h" }]} />
    {source === "classifier" ? <ExtremeClassifierView caseId={caseId} threshold={threshold} record={record} /> : probability.isPending || rainfall.isPending ? <LoadingState label="Loading verified probabilities" /> : probability.isError || rainfall.isError || !values || !rainfall.data ? <ErrorState /> : <>
      <div className="extremes-layout"><div className="extremes-map"><MapControls onReset={resetExtent} onZoom={(delta) => mapRef.current?.zoomTo((mapRef.current?.getZoom() ?? 0) + delta, { duration: 150 })} onFullscreen={fullscreen} /><div ref={mapPanel}><GridMap id="probability" title={threshold === "heavy" ? "Heavy rainfall probability" : "Very-heavy rainfall probability"} subtitle={`P(IMD ≥ ${limit} mm / 24 h) · ${record ? utc(record.valid_period_end_utc) : ""}`} values={values} mask={rainfall.data.data.valid_mask} grid={probability.data.data.grid} palette="probability" geometry={geometry.data?.geometry} selected={activeCell} onSelect={setSelected} onReady={(_, map) => { mapRef.current = map; }} /></div><ProbabilityLegend /><p className="micro-note">Probability is calibrated forecast likelihood, not rainfall amount. The nearest valid cell to the grid center is preselected. Weather Visualization is a mask-aware display interpolation, not higher source resolution. Keyboard users can inspect exact grid values below.</p><div className="cell-controls"><label>Latitude row <select value={activeCell?.row ?? ""} onChange={(event) => setSelected({ row: Number(event.target.value), column: activeCell?.column ?? 24 })}><option value="" disabled>Select</option>{probability.data.data.grid.latitude_centers.map((latitude, row) => <option key={row} value={row}>{latitude.toFixed(2)}° N</option>)}</select></label><label>Longitude column <select value={activeCell?.column ?? ""} onChange={(event) => setSelected({ row: activeCell?.row ?? 24, column: Number(event.target.value) })}><option value="" disabled>Select</option>{probability.data.data.grid.longitude_centers.map((longitude, column) => <option key={column} value={column}>{longitude.toFixed(2)}° E</option>)}</select></label></div><div className="cell-values"><span>Selected probability <b>{activeCell ? valid ? percent(point) : "Unavailable — masked cell" : "No valid cell"}</b></span><span>Observed IMD rainfall <b>{activeCell ? valid ? mm(observed) : "Unavailable — masked cell" : "No valid cell"}</b></span><span>Observed event <b>{valid && observed != null ? observed >= limit ? "Yes" : "No" : "Unavailable"}</b></span></div></div>
      <aside className="extremes-aside"><span className="small-label">HELD-OUT 2019 · {threshold === "heavy" ? "HEAVY" : "VERY HEAVY"}</span><h2>Probability quality</h2><p className="micro-note">{metric.observed_event_count.toLocaleString("en-US")} observed event cells across {metric.sample_count.toLocaleString("en-US")} valid test cells.</p><div className="quality-metrics"><Metric label="Brier score · lower is better" value={score(metric.brier, 4)} tone="teal" /><Metric label="Brier skill score" value={score(metric.bss)} /><Metric label="PR-AUC" value={score(metric.pr_auc)} /><Metric label="ROC-AUC" value={score(metric.roc_auc)} /></div><div className="threshold-quality"><strong>At frozen {percent(metric.categorical.decision_threshold_probability, 0)} decision threshold</strong><div><span>POD {score(metric.categorical.metrics.POD)}</span><span>FAR {score(metric.categorical.metrics.FAR)}</span><span>CSI {score(metric.categorical.metrics.CSI)}</span><span>ETS {score(metric.categorical.metrics.ETS)}</span></div></div><p className="micro-note">Sparse high-probability bins limit reliability claims, particularly for Very Heavy events. No 2019 recalibration or threshold retuning.</p></aside></div>
    </>}
    {source === "calibrated" ? <><SectionHeading title="Reliability" note="Predicted probability versus observed event frequency · 2019 held-out test" /><div className="extremes-reliability"><ReliabilityChart verification={verification} threshold={threshold} /><div className="reliability-note"><strong>Read the curve with counts.</strong><p>Each point represents a non-empty probability bin. The diagonal indicates perfect reliability. Upper bins with zero samples are not evidence of calibration.</p><table className="mini-table"><caption>Reliability bin counts</caption><thead><tr><th>Forecast bin</th><th>Samples</th><th>Observed frequency</th></tr></thead><tbody>{metric.reliability.map((bin) => <tr key={bin.bin_lower}><th>{Math.round(bin.bin_lower * 100)}–{Math.round(bin.bin_upper * 100)}%</th><td>{bin.sample_count.toLocaleString("en-US")}</td><td>{bin.observed_event_frequency == null ? "Undefined" : percent(bin.observed_event_frequency)}</td></tr>)}</tbody></table></div></div></> : null}
  </div>;
}
