"use client";

import dynamic from "next/dynamic";
import { useQuery } from "@tanstack/react-query";
import { useRef, useState } from "react";
import type { Map as MapLibreMap } from "maplibre-gl";
import type { CaseSummary } from "@/lib/api/science";
import { geometrySchema, getScience, rainfallSchema } from "@/lib/api/science";
import { getHeavyRainCase, getHeavyRainOverview } from "@/lib/api/heavy-rain";
import { nearestValidCell, type CellSelection } from "@/lib/maps/grid";
import { mm, score, utc } from "@/lib/format";
import { ErrorState, LoadingState, Metric } from "@/components/science/common";
import { HeavyRainNotice } from "@/components/science/heavy-rain-controls";
import { DecisionLegend, ScoreLegend } from "@/components/maps/map-legend";
import { MapControls } from "@/components/maps/map-controls";
import { Segmented } from "@/components/ui/segmented";
import { mapBounds } from "@/components/maps/use-weather-map";

const GridMap = dynamic(() => import("@/components/maps/grid-map"), { ssr: false, loading: () => <div className="map-placeholder" aria-label="Loading classifier map" /> });

/** The frozen heavy-rain classifiers (reforecast study) on one 2019 case: the score and the yes/no forecast at the frozen threshold, beside the same quality figures the study froze. */
export function ExtremeClassifierView({ caseId, threshold, record }: { caseId: string; threshold: "heavy" | "very_heavy"; record: CaseSummary | undefined }) {
  const [layer, setLayer] = useState<"score" | "decision">("score");
  const [selected, setSelected] = useState<CellSelection | null>(null);
  const mapRef = useRef<MapLibreMap | null>(null);
  const panel = useRef<HTMLDivElement>(null);
  const b1 = useQuery({ queryKey: ["heavy-rain-case", caseId], queryFn: () => getHeavyRainCase(caseId) });
  const overview = useQuery({ queryKey: ["heavy-rain-overview"], queryFn: getHeavyRainOverview, staleTime: 10 * 60_000 });
  const rainfall = useQuery({ queryKey: ["rainfall", caseId], queryFn: () => getScience(`/cases/${caseId}/rainfall`, rainfallSchema) });
  const geometry = useQuery({ queryKey: ["district-geometry"], queryFn: () => getScience("/geometry/districts", geometrySchema) });
  if (b1.isPending || rainfall.isPending || overview.isPending) return <LoadingState label="Loading the heavy-rain classifier layer" />;
  if (b1.isError || rainfall.isError || overview.isError || !b1.data || !rainfall.data || !overview.data) return <ErrorState message={(b1.error ?? overview.error ?? rainfall.error) instanceof Error ? ((b1.error ?? overview.error ?? rainfall.error) as Error).message : undefined} />;
  const heavy = threshold === "heavy";
  const limit = heavy ? 64.5 : 115.6;
  const scores = heavy ? b1.data.heavy_score : b1.data.very_heavy_score;
  const decisions = heavy ? b1.data.heavy_decision : b1.data.very_heavy_decision;
  const values = layer === "score" ? scores : decisions;
  const tau = b1.data.decision_thresholds[threshold];
  const stats = overview.data.summary.classifier[threshold];
  const raw = overview.data.summary.rainfall.M0[threshold];
  const confirmation = overview.data.confirmation.exceedance[heavy ? "B1:heavy" : "B1:very_heavy"];
  const grid = rainfall.data.data.grid;
  const mask = rainfall.data.data.valid_mask;
  const cell = selected ?? nearestValidCell(mask);
  const valid = cell ? mask[cell.row]?.[cell.column] : false;
  const cellScore = cell && valid ? scores[cell.row]?.[cell.column] : null;
  const cellDecision = cell && valid ? decisions[cell.row]?.[cell.column] : null;
  const observed = cell && valid ? rainfall.data.data.observed[cell.row]?.[cell.column] : null;
  const fullscreen = async () => { if (document.fullscreenElement) await document.exitFullscreen(); else await panel.current?.requestFullscreen(); mapRef.current?.resize(); };
  return <>
    <HeavyRainNotice />
    <Segmented label="Classifier layer" value={layer} onChange={setLayer} options={[{ value: "score", label: "Classifier score" }, { value: "decision", label: "Forecast yes / no at the frozen threshold" }]} />
    <div className="extremes-layout" data-testid="classifier-view"><div className="extremes-map"><MapControls onReset={() => mapRef.current?.fitBounds(mapBounds(grid.bounds_west_south_east_north), { padding: 14, duration: 0 })} onZoom={(delta) => mapRef.current?.zoomTo((mapRef.current?.getZoom() ?? 0) + delta, { duration: 150 })} onFullscreen={fullscreen} />
      <div ref={panel}><GridMap id="classifier" title={`${heavy ? "Heavy" : "Very-heavy"} rain · ${layer === "score" ? "classifier score" : "classifier forecast (yes / no)"}`} subtitle={`B1 · frozen threshold ${tau.toFixed(3)} · rain ≥ ${limit} mm / 24 h · ${record ? utc(record.valid_period_end_utc) : ""}`}
        values={values} mask={mask} grid={grid} palette={layer === "score" ? "probability" : "decision"} valueFormat={layer === "score" ? "score" : "decision"} geometry={geometry.data?.geometry} selected={cell} onSelect={setSelected} onReady={(_, map) => { mapRef.current = map; }} /></div>
      {layer === "score" ? <ScoreLegend /> : <DecisionLegend />}
      <p className="micro-note">The score comes from a class-weighted model whose threshold was fixed on validation years: it ranks cells, it is not a calibrated probability, and the yes/no forecast flags more events than occur. Weather Visualization is a mask-aware display interpolation, not higher source resolution.</p>
      <div className="cell-values" data-testid="classifier-cell"><span>Selected score <b>{cell ? valid ? score(cellScore, 3) : "Unavailable — masked cell" : "No valid cell"}</b></span><span>Forecast at threshold <b>{valid && cellDecision != null ? cellDecision >= 0.5 ? "Yes" : "No" : "Unavailable"}</b></span><span>Observed IMD rainfall <b>{valid ? mm(observed) : "Unavailable — masked cell"}</b></span><span>Observed event <b>{valid && observed != null ? observed >= limit ? "Yes" : "No" : "Unavailable"}</b></span></div></div>
    <aside className="extremes-aside"><span className="small-label">2019 CASES · {heavy ? "HEAVY" : "VERY HEAVY"} · POST-HOC</span><h2>Classifier quality</h2>
      <p className="micro-note">{stats.observed_events.toLocaleString("en-US")} observed event cells across {overview.data.summary.cells.toLocaleString("en-US")} valid cells in {overview.data.summary.cases} cases.</p>
      <div className="quality-metrics"><Metric label="CSI · higher is better" value={score(stats.csi, 3)} tone="teal" /><Metric label="Raw GEFS CSI (same cells)" value={score(raw?.csi ?? null, 3)} /><Metric label="Frequency bias · 1 is unbiased" value={score(stats.frequency_bias, 2)} /><Metric label="Raw GEFS frequency bias" value={score(raw?.frequency_bias ?? null, 2)} /></div>
      <div className="threshold-quality"><strong>At the frozen threshold {tau.toFixed(3)}</strong><div><span>POD {score(stats.pod ?? null, 3)}</span><span>FAR {score(stats.far ?? null, 3)}</span><span>Hits {stats.hits.toLocaleString("en-US")}</span><span>False alarms {stats.false_alarms.toLocaleString("en-US")}</span></div></div>
      <p className="micro-note" data-testid="classifier-confirmation">All confirmatory years pooled ({overview.data.confirmation.cases} cases): CSI {score(confirmation.csi, 3)}, frequency bias {score(confirmation.frequency_bias, 2)}. This view is a descriptive display of frozen predictions, not a selection or a tuning.</p></aside></div>
  </>;
}
