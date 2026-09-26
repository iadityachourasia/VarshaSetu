"use client";

import dynamic from "next/dynamic";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Info, Layers3 } from "lucide-react";
import type { Map as MapLibreMap } from "maplibre-gl";
import type { CaseSummary } from "@/lib/api/science";
import { caseDetailSchema, fssSchema, geometrySchema, getScience, rainfallSchema, regimeSchema } from "@/lib/api/science";
import { nearestValidCell, type CellSelection } from "@/lib/maps/grid";
import { leadName, mm, score, utc } from "@/lib/format";
import { CaseSelector } from "@/components/science/case-selector";
import { RegimeBars } from "@/components/science/regime-bars";
import { ErrorState, LoadingState, PageHeading, PrototypeNote } from "@/components/science/common";
import { RainLegend } from "@/components/maps/map-legend";
import { MapControls } from "@/components/maps/map-controls";
import { mapBounds } from "@/components/maps/use-weather-map";
import { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle, SheetTrigger } from "@/components/ui/sheet";
import { Button } from "@/components/ui/button";

const GridMap = dynamic(() => import("@/components/maps/grid-map"), { ssr: false, loading: () => <div className="map-placeholder" aria-label="Loading rainfall map" /> });

export function ForecastWorkspace({ cases, demos, initialCase }: { cases: CaseSummary[]; demos: CaseSummary[]; initialCase: string }) {
  const router = useRouter();
  const [caseId, setCaseId] = useState(initialCase);
  const [selected, setSelected] = useState<CellSelection | null>(null);
  const maps = useRef(new Map<string, MapLibreMap>());
  const triptych = useRef<HTMLDivElement>(null);
  const [mobile, setMobile] = useState<boolean | null>(null);
  const [activeMap, setActiveMap] = useState<"raw" | "corrected" | "observed">("corrected");
  const syncing = useRef(false);
  const selectedCase = cases.find((item) => item.case_id === caseId);
  const rainfall = useQuery({ queryKey: ["rainfall", caseId], queryFn: () => getScience(`/cases/${caseId}/rainfall`, rainfallSchema) });
  const regime = useQuery({ queryKey: ["regime", caseId], queryFn: () => getScience(`/cases/${caseId}/regime`, regimeSchema) });
  const detail = useQuery({ queryKey: ["case", caseId], queryFn: () => getScience(`/cases/${caseId}`, caseDetailSchema) });
  const fss = useQuery({ queryKey: ["fss", caseId], queryFn: () => getScience(`/cases/${caseId}/fss`, fssSchema) });
  const geometry = useQuery({ queryKey: ["district-geometry"], queryFn: () => getScience("/geometry/districts", geometrySchema) });
  useEffect(() => {
    const match = window.matchMedia("(max-width: 760px)");
    const update = () => setMobile(match.matches);
    update(); match.addEventListener("change", update);
    return () => match.removeEventListener("change", update);
  }, []);
  const handleCase = useCallback((id: string) => { setCaseId(id); setSelected(null); router.replace(`/forecast?case=${encodeURIComponent(id)}`, { scroll: false }); }, [router]);
  const handleReady = useCallback((id: string, map: MapLibreMap | null) => {
    if (!map) { maps.current.delete(id); return; }
    maps.current.set(id, map);
    if (maps.current.size === 3 && rainfall.data) {
      const [west, south, east, north] = rainfall.data.data.grid.bounds_west_south_east_north;
      requestAnimationFrame(() => {
        for (const instance of maps.current.values()) {
          instance.resize();
          instance.fitBounds([[west, south], [east, north]], { padding: 14, duration: 0 });
        }
      });
    }
  }, [rainfall.data]);
  const handleMove = useCallback((id: string, map: MapLibreMap) => {
    if (syncing.current) return;
    syncing.current = true;
    for (const [otherId, other] of maps.current) if (otherId !== id) other.jumpTo({ center: map.getCenter(), zoom: map.getZoom(), bearing: 0, pitch: 0 });
    syncing.current = false;
  }, []);
  const resetExtent = () => {
    const bounds = rainfall.data?.data.grid.bounds_west_south_east_north;
    if (bounds) for (const map of maps.current.values()) { map.resize(); map.fitBounds(mapBounds(bounds), { padding: 14, duration: 0 }); }
  };
  const zoom = (delta: number) => { for (const map of maps.current.values()) map.zoomTo(map.getZoom() + delta, { duration: 150 }); };
  const fullscreen = async () => {
    if (document.fullscreenElement) await document.exitFullscreen();
    else await triptych.current?.requestFullscreen();
    for (const map of maps.current.values()) map.resize();
  };
  const data = rainfall.data?.data;
  const activeCell = selected ?? (data ? nearestValidCell(data.valid_mask) : null);
  const coordinate = useMemo(() => activeCell && data ? `${data.grid.latitude_centers[activeCell.row].toFixed(2)}° N, ${data.grid.longitude_centers[activeCell.column].toFixed(2)}° E` : "No valid grid cell", [activeCell, data]);
  const values = activeCell && data ? { raw: data.raw[activeCell.row]?.[activeCell.column], corrected: data.corrected[activeCell.row]?.[activeCell.column], observed: data.observed[activeCell.row]?.[activeCell.column], valid: data.valid_mask[activeCell.row]?.[activeCell.column] } : null;
  return <div className="page-content forecast-page">
    <PageHeading title="Forecast Explorer" subtitle="2019 historical GEFSv12 reforecast evaluation: Raw, corrected, and IMD observed rainfall. Not a live forecast." action={<PrototypeNote />} />
    <CaseSelector cases={cases} demos={demos} selectedId={caseId} onSelect={handleCase} />
    {selectedCase ? <div className="case-meta"><span><b>GEFS INIT</b> {utc(selectedCase.initialization_utc)}</span><span><b>VALID PERIOD</b> {utc(selectedCase.valid_period_start_utc)} — {utc(selectedCase.valid_period_end_utc)}</span><span><b>LEAD</b> {leadName(selectedCase.lead_hours)}</span><Sheet><SheetTrigger render={<Button variant="outline" size="sm" />}><Info size={15} /> Provenance</SheetTrigger><SheetContent><SheetHeader><SheetTitle>Scientific provenance</SheetTitle><SheetDescription>Frozen historical artifacts for this forecast case.</SheetDescription></SheetHeader><dl className="provenance-list"><dt>Case ID</dt><dd>{caseId}</dd><dt>Corpus</dt><dd>{rainfall.data?.provenance.corpus_version ?? "Unavailable"}</dd><dt>Deterministic model</dt><dd>{rainfall.data?.provenance.deterministic_model ?? "Unavailable"}</dd><dt>Artifact manifest SHA-256</dt><dd>{rainfall.data?.provenance.artifact_manifest_sha256 ?? "Unavailable"}</dd><dt>Status</dt><dd>Historical prototype only — not operational</dd></dl></SheetContent></Sheet></div> : null}
    {rainfall.isPending ? <LoadingState /> : rainfall.isError || !data ? <ErrorState /> : <>
      <MapControls onReset={resetExtent} onZoom={zoom} onFullscreen={fullscreen} />
      {mobile ? <div className="mobile-map-tabs" role="group" aria-label="Rainfall field"><button type="button" aria-pressed={activeMap === "raw"} className={activeMap === "raw" ? "selected" : ""} onClick={() => setActiveMap("raw")}>Raw GEFS</button><button type="button" aria-pressed={activeMap === "corrected"} className={activeMap === "corrected" ? "selected" : ""} onClick={() => setActiveMap("corrected")}>Corrected</button><button type="button" aria-pressed={activeMap === "observed"} className={activeMap === "observed" ? "selected" : ""} onClick={() => setActiveMap("observed")}>IMD Observed</button></div> : null}
      <div ref={triptych} className="triptych" aria-label="Synchronized rainfall comparison">
        {mobile === null ? <div className="map-placeholder" aria-label="Preparing geographic maps" /> : null}
        {mobile === false || activeMap === "raw" && mobile ? <GridMap id="raw" title="Raw GEFS" subtitle="Uncorrected control forecast" values={data.raw} mask={data.valid_mask} grid={data.grid} palette="rainfall" geometry={geometry.data?.geometry} selected={activeCell} onSelect={setSelected} onReady={handleReady} onMove={handleMove} /> : null}
        {mobile === false || activeMap === "corrected" && mobile ? <GridMap id="corrected" title="VarshaSetu Corrected" subtitle="Frozen M2 Global XGBoost" values={data.corrected} mask={data.valid_mask} grid={data.grid} palette="rainfall" geometry={geometry.data?.geometry} selected={activeCell} onSelect={setSelected} onReady={handleReady} onMove={handleMove} /> : null}
        {mobile === false || activeMap === "observed" && mobile ? <GridMap id="observed" title="IMD Observed" subtitle="Verification reference" values={data.observed} mask={data.valid_mask} grid={data.grid} palette="rainfall" geometry={geometry.data?.geometry} selected={activeCell} onSelect={setSelected} onReady={handleReady} onMove={handleMove} /> : null}
      </div>
      <RainLegend />
      <p className="map-method-note">Weather Visualization interpolates only fully valid neighboring cells for display. Scientific Grid shows the original 49×49 cells. All inspection values and verification remain unchanged.</p>
      <div className="forecast-bottom"><section className="inspection-panel"><div className="panel-caption"><span className="small-label">CELL INSPECTOR</span><strong>{coordinate}</strong></div><div className="cell-values"><span>Raw <b>{values?.valid ? mm(values.raw) : "—"}</b></span><span>Corrected <b>{values?.valid ? mm(values.corrected) : "—"}</b></span><span>Observed <b>{values?.valid ? mm(values.observed) : "—"}</b></span><span>Correction Δ <b>{values?.valid && values.raw != null && values.corrected != null ? mm(values.corrected - values.raw) : "—"}</b></span></div><p className="micro-note">The nearest valid cell to the grid center is preselected for the demonstration. Click or hover a map cell; keyboard users can choose a grid row and column below. All maps use the same paired valid-cell mask.</p><div className="cell-controls"><label>Latitude row <select value={activeCell?.row ?? ""} onChange={(event) => setSelected({ row: Number(event.target.value), column: activeCell?.column ?? 24 })}><option value="" disabled>Select</option>{data.grid.latitude_centers.map((latitude, row) => <option value={row} key={row}>{latitude.toFixed(2)}° N</option>)}</select></label><label>Longitude column <select value={activeCell?.column ?? ""} onChange={(event) => setSelected({ row: activeCell?.row ?? 24, column: Number(event.target.value) })}><option value="" disabled>Select</option>{data.grid.longitude_centers.map((longitude, column) => <option value={column} key={column}>{longitude.toFixed(2)}° E</option>)}</select></label></div></section>
      {regime.data ? <RegimeBars probabilities={regime.data.data.probabilities} dominant={regime.data.data.dominant_regime} /> : <div className="state-message">Regime context unavailable</div>}
      <section className="case-skill"><div className="panel-caption"><span className="small-label">CASE VERIFICATION</span><strong>Correction behavior</strong></div><div className="case-skill-values"><span>Raw RMSE <b>{mm(detail.data?.data.raw_rmse_mm ?? selectedCase?.raw_rmse_mm)}</b></span><span>Corrected RMSE <b>{mm(detail.data?.data.corrected_rmse_mm ?? selectedCase?.corrected_rmse_mm)}</b></span></div><p className="micro-note">A single case is illustrative, not evidence of overall superiority. {fss.data ? `Heavy 3×3 FSS: Raw ${score(fss.data.data.heavy?.["3"]?.raw.fss)} · Corrected ${score(fss.data.data.heavy?.["3"]?.corrected.fss)}.` : ""}</p><span className="model-note"><Layers3 size={14} /> 49×49 · 0.25° target grid</span></section></div>
    </>}
  </div>;
}
