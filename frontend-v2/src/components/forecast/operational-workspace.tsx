"use client";

import dynamic from "next/dynamic";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import type { Map as MapLibreMap } from "maplibre-gl";
import { ArrowLeftRight, Layers3 } from "lucide-react";
import { geometrySchema, getScience } from "@/lib/api/science";
import { DataSourceIndicator, ErrorState, LoadingState, PageHeading, PrototypeNote } from "@/components/science/common";
import { RainLegend } from "@/components/maps/map-legend";
import { MapControls } from "@/components/maps/map-controls";
import { nearestValidCell, type CellSelection, type Palette } from "@/lib/maps/grid";
import { expandedField, getOperationalIndex, operationalGrid, operationalMask, type OperationalCase, type OperationalIndex } from "@/science/frozen/operational";
import { loadOperationalCase } from "@/lib/operational-live-case";
import { caseDisplayLabel, loadOperationalCaseList } from "@/lib/operational-case-list";
import type { OperationalYear } from "@/lib/api/operational";

const GridMap = dynamic(() => import("@/components/maps/grid-map"), { ssr: false, loading: () => <div className="map-placeholder" aria-label="Loading historical map" /> });
const atmosphereFields: { key: keyof OperationalCase["atmosphere"]; label: string; unit: string; palette: Palette }[] = [
  { key: "forecast_u850", label: "850-hPa zonal wind (U)", unit: "m/s", palette: "u850" },
  { key: "forecast_v850", label: "850-hPa meridional wind (V)", unit: "m/s", palette: "v850" },
  { key: "forecast_q700", label: "700-hPa specific humidity", unit: "kg/kg", palette: "q700" },
  { key: "forecast_z500", label: "500-hPa geopotential height", unit: "gpm", palette: "z500" },
  { key: "forecast_mslp", label: "Mean sea-level pressure", unit: "Pa", palette: "mslp" },
  { key: "forecast_pwat", label: "Precipitable water", unit: "kg/m²", palette: "pwat" },
];

function errorAnatomy(raw: number[], model: number[], observed: number[]): { values: number[]; improved: number; worsened: number } {
  const values = model.map((value, point) => Math.abs(value - observed[point]) - Math.abs(raw[point] - observed[point]));
  return { values, improved: values.filter((value) => value < 0).length, worsened: values.filter((value) => value > 0).length };
}

function OperationalForecastContent({ index, initialYear, initialCase }: { index: OperationalIndex; initialYear: number; initialCase?: string }) {
  const router = useRouter();
  const [year, setYear] = useState(initialYear);
  const [caseId, setCaseId] = useState(initialCase ?? "");
  const [model, setModel] = useState("M1");
  const [view, setView] = useState("rainfall");
  const [layout, setLayout] = useState<"single" | "side" | "triple">("triple");
  const [selected, setSelected] = useState<CellSelection | null>(null);
  const maps = useRef(new Map<string, MapLibreMap>());
  const syncing = useRef(false);
  const mapFrame = useRef<HTMLDivElement>(null);
  // Phase 5A.2C: the case *list* (selector options/labels) is now live-API-
  // primary via the paginated case-index endpoint, independent of the
  // per-case grid data below. Falls back to the static bundle's index only
  // on a genuine network failure (lib/operational-case-list.ts).
  const caseListResult = useQuery({
    queryKey: ["operational-case-list", year],
    queryFn: () => loadOperationalCaseList(year as OperationalYear),
    staleTime: 60_000,
  });
  const cases = useMemo(
    () => (caseListResult.data?.data ?? []).filter((item) => item.deterministic_source_eligible),
    [caseListResult.data],
  );
  const caseListItem = cases.find((item) => item.case_id === caseId) ?? cases[0];
  // The frozen static per-case JSON (needed only as this case's fallback
  // source, and for its own `artifact` path) still comes from the static
  // bundle's index -- this is unrelated to which source drives the selector.
  const staticSummary = index.cases.find((item) => item.case_id === caseListItem?.case_id && item.year === year);
  // Phase 5A.2B: live /api/science/operational/* is now the primary source
  // for rainfall/probability/regime/ensemble; falls back to the static
  // bundle only on a genuine network failure (see lib/operational-live-case.ts).
  const detail = useQuery({
    queryKey: ["operational-live-case", year, caseListItem?.case_id],
    queryFn: () => loadOperationalCase(year as OperationalYear, caseListItem!.case_id, staticSummary!, index),
    enabled: Boolean(caseListItem && staticSummary),
  });
  const geometry = useQuery({ queryKey: ["district-geometry"], queryFn: () => getScience("/geometry/districts", geometrySchema) });
  const mask = useMemo(() => operationalMask(index), [index]);
  const grid = useMemo(() => operationalGrid(index), [index]);
  const cell = selected ?? nearestValidCell(mask);
  const loaded = detail.data;
  const data: OperationalCase | undefined = loaded?.case;
  const models = (loaded?.modelsPresent ?? staticSummary?.models.filter((item) => item !== "M0") ?? []);
  const selectedModel = models.includes(model) ? model : models[0];
  const diagnostic = useMemo(() => data && selectedModel && data.fields[selectedModel]
    ? errorAnatomy(data.fields.M0, data.fields[selectedModel], data.fields.observed) : null, [data, selectedModel]);
  const field = atmosphereFields.find((item) => item.key === view);
  const panels = useMemo(() => {
    if (!data) return [];
    if (field) return [
      { id: "atmosphere", title: field.label, subtitle: `Frozen forecast field · ${field.unit}`, values: data.atmosphere[field.key], palette: field.palette, unit: field.unit },
      { id: "raw", title: "Raw GEFS rainfall", subtitle: "Context · mm / 24 h", values: data.fields.M0, palette: "rainfall" as Palette, unit: "mm / 24 h" },
    ];
    if (view === "error" && diagnostic) return [
      { id: "error", title: "Absolute-error difference", subtitle: "Model |error| − Raw |error| · zero-centered", values: diagnostic.values, palette: "error-difference" as Palette, unit: "mm" },
      { id: "observed", title: "IMD reference", subtitle: "Historical daily rainfall", values: data.fields.observed, palette: "rainfall" as Palette, unit: "mm / 24 h" },
    ];
    const modelValues = selectedModel ? data.fields[selectedModel] : undefined;
    return [
      { id: "raw", title: "Raw operational GEFS", subtitle: "Uncorrected c00 · mm / 24 h", values: data.fields.M0, palette: "rainfall" as Palette, unit: "mm / 24 h" },
      // Defensive: only include the model panel when both a model is
      // selected and its grid actually came back from fields (guards against
      // an available-products/field-name mismatch surfacing as a crash
      // instead of a visible gap -- found and fixed once already for 2023's
      // "m2_out_of_fold" capability label vs its plain "m2" field name).
      ...(selectedModel && modelValues ? [{ id: "model", title: selectedModel === "M2_OOF" ? "M2 cross-fit / OOF" : `${selectedModel} ${selectedModel === "M1" ? "Ridge MOS" : "frozen model"}`, subtitle: year === 2023 ? "Out-of-fold prediction" : year === 2024 ? "Frozen validation prediction" : "Frozen final-test prediction", values: modelValues, palette: "rainfall" as Palette, unit: "mm / 24 h" }] : []),
      { id: "observed", title: "IMD observed", subtitle: "Historical verification reference", values: data.fields.observed, palette: "rainfall" as Palette, unit: "mm / 24 h" },
    ];
  }, [data, diagnostic, field, selectedModel, view, year]);
  const visiblePanels = layout === "single" ? panels.slice(0, 1) : layout === "side" ? panels.slice(0, 2) : panels;

  const updateCase = (nextYear: number, nextCase: string) => {
    setYear(nextYear); setCaseId(nextCase); setSelected(null);
    router.replace(nextCase
      ? `/forecast?experiment=operational&year=${nextYear}&case=${encodeURIComponent(nextCase)}`
      : `/forecast?experiment=operational&year=${nextYear}`, { scroll: false });
  };
  // Year switches don't know the live list's first case synchronously (it's
  // a fresh query per year); `caseListItem` already falls back to cases[0]
  // for rendering, so this effect only needs to sync the URL (an external
  // system), never React state, once that first case resolves.
  useEffect(() => {
    if (!caseId && caseListItem) {
      router.replace(`/forecast?experiment=operational&year=${year}&case=${encodeURIComponent(caseListItem.case_id)}`, { scroll: false });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [caseId, year, caseListItem?.case_id]);
  const onReady = useCallback((id: string, map: MapLibreMap | null) => {
    if (map) maps.current.set(id, map); else maps.current.delete(id);
  }, []);
  const onMove = useCallback((id: string, map: MapLibreMap) => {
    if (syncing.current) return;
    syncing.current = true;
    for (const [otherId, other] of maps.current) if (otherId !== id) other.jumpTo({ center: map.getCenter(), zoom: map.getZoom(), bearing: 0, pitch: 0 });
    syncing.current = false;
  }, []);
  const selectedPoint = cell ? index.pixel_indices.indexOf(cell.row * 49 + cell.column) : -1;
  const point = selectedPoint >= 0 && data ? {
    raw: data.fields.M0[selectedPoint], model: data.fields[selectedModel]?.[selectedPoint], observed: data.fields.observed[selectedPoint],
    heavy: data.probabilities?.heavy[selectedPoint], veryHeavy: data.probabilities?.very_heavy[selectedPoint],
  } : null;
  return <div className="page-content phase5-workspace">
    <PageHeading title="Forecast & Atmosphere" subtitle="Historical forecast analysis · frozen operational-era GEFS and IMD evidence" action={<span style={{ display: "flex", gap: 8, alignItems: "center" }}>{loaded ? <DataSourceIndicator mode={loaded.mode} /> : null}<PrototypeNote /></span>} />
    <div className="phase5-context-strip"><strong>Historical operational GEFS</strong><span>2023 cross-fit · 2024 validation · 2025 completed final test</span><span>Not live or an official warning service</span></div>
    <div className="phase5-controls" role="group" aria-label="Historical forecast controls">
      <label>Year<select value={year} onChange={(event) => updateCase(Number(event.target.value), "")}><option value={2023}>2023 · CROSS-FIT / OOF</option><option value={2024}>2024 · VALIDATION</option><option value={2025}>2025 · FINAL TEST</option></select></label>
      <label>Initialization / lead<select value={caseListItem?.case_id ?? ""} onChange={(event) => updateCase(year, event.target.value)}>{cases.map((item) => <option value={item.case_id} key={item.case_id}>{caseDisplayLabel(item)}</option>)}</select></label>
      <label>Variable<select value={view} onChange={(event) => setView(event.target.value)}><option value="rainfall">Rainfall comparison</option><option value="error">Error anatomy</option>{atmosphereFields.map((item) => <option value={item.key} key={item.key}>{item.label}</option>)}</select></label>
      <label>Model<select value={selectedModel ?? ""} onChange={(event) => setModel(event.target.value)}>{models.map((item) => <option key={item} value={item}>{item === "M2_OOF" ? "M2 cross-fit / OOF" : `${item}${item === "M1" ? " · preselected primary" : item === "M2" ? " · secondary" : ""}`}</option>)}</select></label>
      <label>Layout<select value={layout} onChange={(event) => setLayout(event.target.value as typeof layout)}><option value="single">Single</option><option value="side">Side-by-side</option><option value="triple">Triple</option></select></label>
    </div>
    {caseListItem ? <div className="case-meta"><span><b>INIT</b> {caseListItem.initialization_utc}</span><span><b>LEAD</b> {caseListItem.lead_label}</span><span><b>IMD DATE</b> {caseListItem.valid_date ?? "—"}</span><span><b>ROLE</b> {year === 2023 ? "TRAINING / CROSS-FIT" : year === 2024 ? "VALIDATION / MODEL SELECTION" : "FINAL HISTORICAL TEST — COMPLETED"}</span></div> : null}
    {detail.isPending ? <LoadingState /> : detail.isError
      ? <ErrorState message="This frozen historical case is unavailable. Select another case." />
      : loaded?.mode === "INTEGRITY_FAILURE"
        ? <ErrorState message={`Scientific artifact integrity check failed: ${loaded.message ?? "unknown error"}. This is a hard failure and is not masked by cached data.`} />
        : loaded?.mode === "UNAVAILABLE" || !data
          ? <ErrorState message={loaded?.message ?? "This frozen historical case is unavailable. Select another case."} />
          : <>
      <MapControls onReset={() => { for (const map of maps.current.values()) map.fitBounds([[67.875, 9.875], [80.125, 22.125]], { padding: 14, duration: 0 }); }} onZoom={(delta) => { for (const map of maps.current.values()) map.zoomTo(map.getZoom() + delta, { duration: 150 }); }} onFullscreen={async () => { if (document.fullscreenElement) await document.exitFullscreen(); else await mapFrame.current?.requestFullscreen(); for (const map of maps.current.values()) map.resize(); }} />
      <div ref={mapFrame} className={`phase5-map-grid phase5-map-${visiblePanels.length}`} aria-label="Synchronized historical forecast maps">
        {visiblePanels.map((panel) => <GridMap key={`${caseListItem?.case_id}-${panel.id}-${view}-${selectedModel}`} id={panel.id} title={panel.title} subtitle={panel.subtitle} values={expandedField(index, panel.values)} mask={mask} grid={grid} palette={panel.palette} unit={panel.unit} geometry={geometry.data?.geometry} selected={cell} onSelect={setSelected} onReady={onReady} onMove={onMove} />)}
      </div>
      {view === "rainfall" ? <RainLegend /> : <p className="phase5-legend-note">{view === "error" ? "Blue / negative: lower absolute error than Raw. Amber–red / positive: higher absolute error. The diverging scale is centered at exactly zero." : `${field?.label} · ${field?.unit}. Color is a visual scale, not increased source resolution.`}</p>}
      <p className="map-method-note">Scientific Grid shows native evaluated cells. Weather Visualization interpolates only for display; visualization interpolation does not increase meteorological source resolution. Atmospheric source context is 0.5° and was bilinearly aligned to 0.25° rainfall target centers in the frozen feature pipeline.</p>
      <div className="phase5-inspector"><div><span className="small-label">POINT INSPECTOR</span><h2>{cell ? `${grid.latitude_centers[cell.row].toFixed(2)}° N · ${grid.longitude_centers[cell.column].toFixed(2)}° E` : "Select a valid cell"}</h2><p>49×49 target grid · 10–22° N, 68–80° E · 0.25°</p></div><div className="phase5-point-values"><span>Raw <strong>{point ? point.raw.toFixed(2) : "—"} mm</strong></span><span>{selectedModel} <strong>{point?.model != null ? point.model.toFixed(2) : "—"} mm</strong></span><span>IMD <strong>{point ? point.observed.toFixed(2) : "—"} mm</strong></span><span>Error Δ <strong>{point?.model != null ? (Math.abs(point.model - point.observed) - Math.abs(point.raw - point.observed)).toFixed(2) : "—"} mm</strong></span>{point?.heavy != null ? <span>Heavy P <strong>{(100 * point.heavy).toFixed(1)}%</strong></span> : null}{point?.veryHeavy != null ? <span>Very Heavy P <strong>{(100 * point.veryHeavy).toFixed(1)}%</strong></span> : null}</div><div className="cell-controls"><label>Latitude row<select value={cell?.row ?? 0} onChange={(event) => setSelected({ row: Number(event.target.value), column: cell?.column ?? 24 })}>{grid.latitude_centers.map((latitude, row) => <option value={row} key={row}>{latitude.toFixed(2)}° N</option>)}</select></label><label>Longitude column<select value={cell?.column ?? 0} onChange={(event) => setSelected({ row: cell?.row ?? 24, column: Number(event.target.value) })}>{grid.longitude_centers.map((longitude, column) => <option value={column} key={column}>{longitude.toFixed(2)}° E</option>)}</select></label></div></div>
      <div className="phase5-evidence-row"><span><Layers3 size={15} /> {caseListItem?.event_very_heavy ? "Very Heavy event observed" : caseListItem?.event_heavy ? "Heavy event observed" : "No Heavy/Very Heavy event observed"}</span><span><ArrowLeftRight size={15} /> {diagnostic ? `${diagnostic.improved} lower-error cells · ${diagnostic.worsened} higher-error cells` : "Error comparison unavailable"}</span>{data.frozen_case_metrics ? <span>Frozen case RMSE: Raw {data.frozen_case_metrics.raw_rmse_mm.toFixed(2)} · M1 {data.frozen_case_metrics.M1_rmse_mm.toFixed(2)} mm</span> : <span>{year === 2023 ? "2023 model map is out-of-fold; no independent training-year skill claim." : "Case breakdown is exploratory, not model selection."}</span>}</div>
      <p className="phase5-caveat">{year === 2025 ? "POST-HOC EXPLORATORY VIEW OF THE COMPLETED FINAL TEST. The preselected primary comparison remains M0 Raw versus M1 Ridge on all 232 cases; this case does not determine overall skill." : year === 2024 ? "2024 validation / model-selection evidence; not the final test." : "2023 training / cross-fit evidence. M2 is an out-of-fold prediction, not an independent test result."}</p>
    </>}
  </div>;
}

export function OperationalForecastWorkspace({ initialYear = 2025, initialCase }: { initialYear?: number; initialCase?: string }) {
  const index = useQuery({ queryKey: ["operational-index"], queryFn: getOperationalIndex, staleTime: Infinity });
  if (index.isPending) return <div className="page-content"><LoadingState /></div>;
  if (index.isError) return <div className="page-content"><ErrorState message="Frozen operational-era presentation artifacts are unavailable." /></div>;
  return <OperationalForecastContent index={index.data} initialYear={initialYear} initialCase={initialCase} />;
}
