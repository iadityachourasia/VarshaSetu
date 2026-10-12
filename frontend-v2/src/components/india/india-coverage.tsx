"use client";

import dynamic from "next/dynamic";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { useMemo, useState } from "react";
import { ALL_INDIA_REGIONS, ALL_INDIA_YEARS, getAllIndiaRawCases, getAllIndiaRawGrid, getAllIndiaResult } from "@/lib/api/all-india-raw";
import { EmptyState, ErrorState, LoadingState, PageHeading } from "@/components/science/common";
import { RainLegend } from "@/components/maps/map-legend";
import { nearestValidCell, type CellSelection } from "@/lib/maps/grid";
import { HashChip } from "@/components/ui/hash-chip";
import { NationwideResearch } from "./nationwide-research";

const GridMap = dynamic(() => import("@/components/maps/grid-map"), { ssr: false, loading: () => <div className="map-placeholder" aria-label="Loading India-wide map" /> });
const REGION_LABEL: Record<(typeof ALL_INDIA_REGIONS)[number], string> = {
  ALL_INDIA: "All scored India", INSIDE_MODEL_DOMAIN: "Regional model box", NORTH_OF_DOMAIN: "North of model box",
  EAST_AND_NORTH_EAST: "East and north-east", EAST_COAST_PENINSULA: "East-coast peninsula", SOUTH_OF_DOMAIN: "South of model box",
};

export function IndiaCoverage() {
  const [year, setYear] = useState<number>(2025);
  const [caseId, setCaseId] = useState("");
  const [selected, setSelected] = useState<CellSelection | null>(null);
  const [landOnly, setLandOnly] = useState(true);
  const catalogue = useQuery({ queryKey: ["india-raw-cases", year], queryFn: () => getAllIndiaRawCases(year), staleTime: 5 * 60_000 });
  const verification = useQuery({ queryKey: ["india-raw-result", year], queryFn: () => getAllIndiaResult(year), staleTime: 5 * 60_000 });
  const available = catalogue.data?.cases.filter((item) => item.available_locally) ?? [];
  const chosen = available.find((item) => item.case_id === caseId)
    ?? [...available].reverse().find((item) => item.initialization.slice(5, 7) <= "09")
    ?? available[available.length - 1];
  const field = useQuery({ queryKey: ["india-raw-grid", year, chosen?.case_id], queryFn: () => getAllIndiaRawGrid(year, chosen!.case_id), enabled: Boolean(chosen) });
  const data = field.data;
  const displayMask = useMemo(() => data ? landOnly ? data.display_mask : data.values.map((row) => row.map(() => true)) : null, [data, landOnly]);
  const cell = data && displayMask ? selected && displayMask[selected.row]?.[selected.column] ? selected : nearestValidCell(displayMask) : null;
  const rawAtCell = cell && data ? data.values[cell.row][cell.column] : null;

  return <div className="page-content phase5-workspace india-page" data-testid="india-coverage-page">
    <header className="india-hero">
      <div className="india-hero-copy"><span className="india-eyebrow">National forecast workspace <span aria-hidden="true">/</span> Track B</span><PageHeading title="India-wide Rainfall Coverage" subtitle="Explore real NOAA GEFS rainfall across the 0.25° India grid, then inspect what the development evidence supports." /></div>
      <div className="india-hero-status" aria-label="Product scope"><span><i className="india-status-dot" /> Nationwide Raw grid</span><span>Corrected product · regional</span><span>Historical research · local</span></div>
    </header>
    <nav className="india-section-nav" aria-label="India page sections"><a href="#india-raw"><span>01</span> Forecast map</a><a href="#india-verification"><span>02</span> Raw verification</a><a href="#india-research"><span>03</span> Model research</a></nav>
    <div className="india-scope-note" role="note" data-testid="india-coverage-boundary"><div><span className="india-scope-kicker">Evidence boundary</span><strong>Nationwide input. Regional default.</strong></div><p>This map displays the verified Raw GEFS control. M2 correction has been scientifically supported only in the 10–22°N, 68–80°E model box. The east-coast research correction failed its Raw comparison and is not shown as a product.</p></div>
    <section id="india-raw" className="india-raw-section" aria-labelledby="india-raw-title">
      <div className="india-section-heading"><div><span className="india-section-number">01 / Forecast map</span><h2 id="india-raw-title">Explore a historical forecast</h2><p>Select a cycle and 24-hour window. The map displays the source forecast on the full national grid.</p></div><span className="india-section-tag">Raw GEFS · uncorrected</span></div>
    <div className="phase5-controls india-control-panel" role="group" aria-label="India-wide Raw forecast controls">
      <label>Year<select value={year} onChange={(event) => { setYear(Number(event.target.value)); setCaseId(""); setSelected(null); }}>{ALL_INDIA_YEARS.map((value) => <option value={value} key={value}>{value}{value === 2025 ? " · consumed historical test" : value === 2024 ? " · development" : " · training year"}</option>)}</select></label>
      <label>Initialization / lead<select value={chosen?.case_id ?? ""} onChange={(event) => { setCaseId(event.target.value); setSelected(null); }} disabled={!available.length} data-testid="india-case-select">{available.map((item) => <option key={item.case_id} value={item.case_id}>{item.initialization} · +{item.accumulation_window_hours[0]} to +{item.accumulation_window_hours[1]} h</option>)}</select></label>
      <label>Display footprint<select value={landOnly ? "land" : "full"} onChange={(event) => { setLandOnly(event.target.value === "land"); setSelected(null); }} data-testid="india-footprint-select"><option value="land">India land · research boundary</option><option value="full">Full forecast grid · includes sea</option></select></label>
    </div>
    {catalogue.isError ? <ErrorState message={(catalogue.error as Error).message} /> : catalogue.isPending ? <LoadingState label="Loading verified India-wide case catalogue" /> : available.length === 0 ? <EmptyState message="The local all-India Raw forecast cache is unavailable. The verified aggregate Raw statistics remain in the Verification Lab; no missing grid is invented." /> : null}
    {field.isError ? <ErrorState message={(field.error as Error).message} /> : field.isPending && chosen ? <LoadingState label="Loading hashed India-wide Raw field" /> : data && displayMask ? <>
      <div className="case-meta india-case-meta" data-testid="india-case-meta"><span><b>INIT</b> {data.initialization} 00 UTC</span><span><b>WINDOW</b> +{data.accumulation_window_hours[0]} to +{data.accumulation_window_hours[1]} h</span><span><b>GRID</b> 129 × 135 · 0.25°</span><span><b>FIELD</b> Raw GEFS c00 · mm/24 h</span></div>
      <div className="india-map-card"><div className="phase5-map-grid phase5-map-1" data-testid="india-raw-map"><GridMap id="india-raw" title="India-wide Raw GEFS" subtitle="Uncorrected 24-hour forecast · historical case" values={data.values} mask={displayMask} grid={data.grid} palette="rainfall" unit="mm / 24 h" selected={cell} onSelect={setSelected} /></div><div className="india-map-legend"><RainLegend /></div></div>
      <div className="phase5-inspector india-inspector" data-testid="india-point-inspector"><div><span className="small-label">SELECTED GRID CELL</span><h2>{cell ? `${data.grid.latitude_centers[cell.row].toFixed(2)}° N · ${data.grid.longitude_centers[cell.column].toFixed(2)}° E` : "Select an India cell"}</h2><p>Raw GEFS {rawAtCell != null ? `${rawAtCell.toFixed(2)} mm/24 h` : "unavailable"}</p></div><div><span className="small-label">DISPLAY FOOTPRINT</span><p>Raw land view includes cells whose centres fall inside the simplified 2021 boundary. The model research map includes any polygon-overlap cell, so its footprint is larger. Neither is the IMD verification mask or official current district geometry.</p></div></div>
      <div className="india-source-row"><p className="micro-note" data-testid="india-grid-provenance">{data.source_track} · Raw array <HashChip hash={data.raw_array_sha256} /> · frozen ledger <HashChip hash={data.ledger_sha256} /> · research geometry <HashChip hash={data.geometry_sha256} /></p><Link href={`/forecast?experiment=operational&year=${year}&case=${encodeURIComponent(data.case_id)}`}>Open this case in the regional Raw → corrected → IMD comparison <span aria-hidden="true">↗</span></Link></div>
      <p className="phase5-caveat india-caveat">{data.caveat}</p>
    </> : null}
    </section>
    {verification.data ? <section id="india-verification" className="phase5-analysis-block india-verification" aria-label="All-India Raw verification" data-testid="india-region-verification">
      <div className="india-section-heading"><div><span className="india-section-number">02 / Verification</span><h2>Raw GEFS verification by region · {year}</h2><p>{verification.data.evidence_label} · {verification.data.payload.cases_scored} cases. Historical aggregate Raw scores, not nationwide corrected skill.</p></div><span className="india-section-tag">Raw control only</span></div>
      <div className="district-table-wrap" tabIndex={0}><table className="phase5-table zone-table"><caption className="sr-only">Raw GEFS rainfall errors by geographic region</caption><thead><tr><th scope="col">Region</th><th scope="col">Reference-valid land cells</th><th scope="col">Raw RMSE (mm/24 h)</th><th scope="col">Raw heavy CSI</th></tr></thead><tbody>{ALL_INDIA_REGIONS.map((region) => { const result = verification.data!.payload.metrics[region]; const heavy = result.categorical.heavy; return <tr key={region}><th scope="row">{REGION_LABEL[region]}</th><td>{verification.data!.payload.region_cells_with_observation[region]?.toLocaleString("en-IN") ?? "—"}</td><td>{result.rmse_mm?.toFixed(2) ?? "insufficient support"}</td><td>{"CSI" in heavy && heavy.CSI != null ? heavy.CSI.toFixed(3) : "insufficient support"}</td></tr>; })}</tbody></table></div>
      <p className="phase5-caveat">The map’s research-boundary mask and the verification’s IMD valid-cell population differ. No missing observation or forecast cell is filled with zero. See the Verification Lab for event counts, lead breakdowns and uncertainty.</p>
    </section> : verification.isError ? <ErrorState message="The frozen all-India Raw verification is unavailable; the map does not imply skill." /> : <LoadingState compact label="Loading Raw verification by region" />}
    <NationwideResearch />
  </div>;
}
