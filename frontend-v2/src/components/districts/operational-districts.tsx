"use client";

import dynamic from "next/dynamic";
import { useQuery } from "@tanstack/react-query";
import { useMemo, useRef, useState } from "react";
import type { Map as MapLibreMap } from "maplibre-gl";
import type { District, Geometry } from "@/lib/api/science";
import { geometrySchema, getScience } from "@/lib/api/science";
import {
  getOperationalAvailability, getOperationalDistricts, operationalDistrictModelSchema, operationalYearSchema,
  type OperationalDistrictModel, type OperationalDistrictRow, type OperationalYear,
} from "@/lib/api/operational";
import { loadOperationalCaseList, caseDisplayLabel } from "@/lib/operational-case-list";
import { withStaticFallback } from "@/lib/data-source";
import { mm, percent, regimeName } from "@/lib/format";
import { DataSourceIndicator, ErrorState, LoadingState, PageHeading, PrototypeNote, SectionHeading } from "@/components/science/common";
import { RainLegend } from "@/components/maps/map-legend";
import { MapControls } from "@/components/maps/map-controls";
import { mapBounds } from "@/components/maps/use-weather-map";

const DistrictMap = dynamic(() => import("./district-map"), { ssr: false, loading: () => <div className="map-placeholder" /> });

const YEARS = [2023, 2024, 2025] as const;
const MODEL_LABEL: Record<OperationalDistrictModel, string> = {
  m1: "M1 Ridge MOS (primary)", m2: "M2 global ML", m3: "M3 hard regime-routed", m4: "M4 soft regime-mixture",
};
type MapVariable = "corrected" | "raw" | "observed";
const MAP_VARIABLE: Record<MapVariable, { label: string; field: "corrected_mean_mm" | "raw_mean_mm" | "observed_mean_mm" }> = {
  corrected: { label: "Corrected mean", field: "corrected_mean_mm" },
  raw: { label: "Raw GEFS mean", field: "raw_mean_mm" },
  observed: { label: "IMD observed mean (replay)", field: "observed_mean_mm" },
};
type SortKey = "district_name" | "raw_mean_mm" | "corrected_mean_mm" | "observed_mean_mm" | "error_mm" | "heavy_probability" | "very_heavy_probability" | "heavy_area_fraction" | "observed_heavy_area_fraction";
const columns: { key: SortKey; label: string }[] = [
  { key: "district_name", label: "District" }, { key: "raw_mean_mm", label: "Raw Mean" },
  { key: "corrected_mean_mm", label: "Corrected Mean" }, { key: "observed_mean_mm", label: "IMD Mean" },
  { key: "error_mm", label: "Corrected − IMD" }, { key: "heavy_probability", label: "Heavy P" },
  { key: "very_heavy_probability", label: "Very Heavy P" }, { key: "heavy_area_fraction", label: "Corrected Heavy Area" },
  { key: "observed_heavy_area_fraction", label: "IMD Heavy Area" },
];

const valueOf = (row: OperationalDistrictRow, key: SortKey): string | number =>
  key === "error_mm" ? row.corrected_mean_mm - row.observed_mean_mm : (row[key as keyof OperationalDistrictRow] as string | number | null) ?? Number.NEGATIVE_INFINITY;

function positions(value: unknown, out: number[][] = []): number[][] {
  if (!Array.isArray(value)) return out;
  if (value.length >= 2 && typeof value[0] === "number" && typeof value[1] === "number") out.push(value as number[]);
  else value.forEach((item) => positions(item, out));
  return out;
}

export function OperationalDistrictWorkspace({ initialYear, initialCase }: { initialYear?: OperationalYear; initialCase?: string }) {
  const [year, setYear] = useState<OperationalYear>(initialYear ?? 2025);
  const [caseId, setCaseId] = useState(initialCase ?? "");
  const [model, setModel] = useState<OperationalDistrictModel>("m1");
  const [variable, setVariable] = useState<MapVariable>("corrected");
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [sort, setSort] = useState<SortKey>("observed_mean_mm");
  const [ascending, setAscending] = useState(false);
  const mapRef = useRef<MapLibreMap | null>(null);

  const availability = useQuery({ queryKey: ["operational-availability", year], queryFn: () => withStaticFallback(() => getOperationalAvailability(year), null) });
  const caseList = useQuery({ queryKey: ["operational-case-list", year], queryFn: () => loadOperationalCaseList(year), staleTime: 60_000 });
  const geometry = useQuery({ queryKey: ["district-geometry"], queryFn: () => getScience("/geometry/districts", geometrySchema) });
  const cases = useMemo(() => (caseList.data?.data ?? []).filter((item) => item.deterministic_source_eligible && item.probability_source_eligible), [caseList.data]);
  const selectedCase = cases.find((item) => item.case_id === caseId) ?? cases.find((item) => item.event_very_heavy) ?? cases.find((item) => item.event_heavy) ?? cases[0];
  const districtsAvailable = availability.data?.data?.district_aggregates ?? false;
  const districts = useQuery({
    queryKey: ["operational-districts", year, selectedCase?.case_id, model],
    queryFn: () => withStaticFallback(() => getOperationalDistricts(year, selectedCase!.case_id, model), null),
    enabled: Boolean(selectedCase) && districtsAvailable,
  });

  const body = districts.data?.data ?? null;
  const list = body?.districts;
  const ordered = useMemo(() => [...(list ?? [])].sort((a, b) => {
    const x = valueOf(a, sort), y = valueOf(b, sort);
    const order = typeof x === "string" && typeof y === "string" ? x.localeCompare(y) : Number(x) - Number(y);
    return (ascending ? order : -order) || a.district_name.localeCompare(b.district_name);
  }), [list, sort, ascending]);
  // Map coloring reuses the shared choropleth (which reads `corrected_mean_mm`) by feeding it the selected variable.
  const mapDistricts: District[] = useMemo(() => (list ?? []).map((row) => ({
    district_id: row.district_id, district_name: row.district_name, raw_mean_mm: row.raw_mean_mm,
    corrected_mean_mm: row[MAP_VARIABLE[variable].field], corrected_max_mm: row.corrected_max_mm,
    heavy_probability: row.heavy_probability ?? 0, very_heavy_probability: row.very_heavy_probability ?? 0,
    heavy_area_fraction: row.heavy_area_fraction, very_heavy_area_fraction: row.very_heavy_area_fraction,
    dominant_regime: body?.predicted_regime ?? "", valid_grid_cells: row.valid_grid_cells,
  })), [list, variable, body?.predicted_regime]);

  const defaultId = list?.reduce<OperationalDistrictRow | undefined>((first, item) => !first || item.observed_mean_mm > first.observed_mean_mm ? item : first, undefined)?.district_id ?? null;
  const effectiveId = selectedId ?? defaultId;
  const selected = list?.find((item) => item.district_id === effectiveId) ?? null;
  const changeSort = (key: SortKey) => { if (sort === key) setAscending(!ascending); else { setSort(key); setAscending(key === "district_name"); } };

  const selectDistrict = (id: string, geo: Geometry) => {
    setSelectedId(id);
    const feature = geo.geometry.features.find((item) => item.properties.district_id === id);
    const points = positions((feature?.geometry as { coordinates?: unknown } | undefined)?.coordinates);
    if (!points.length || !mapRef.current) return;
    const west = Math.max(67.875, Math.min(...points.map((p) => p[0]))), east = Math.min(80.125, Math.max(...points.map((p) => p[0])));
    const south = Math.max(9.875, Math.min(...points.map((p) => p[1]))), north = Math.min(22.125, Math.max(...points.map((p) => p[1])));
    if (west < east && south < north) mapRef.current.fitBounds([[west, south], [east, north]], { padding: 45, maxZoom: 8, duration: 300 });
  };

  const heading = <PageHeading title="District Intelligence" subtitle={`Historical operational GEFS · ${year} · area-weighted district aggregation of frozen grids; historical replay, not an advisory or live warning.`}
    action={<span style={{ display: "flex", gap: 8, alignItems: "center" }}>{districts.data && districts.data.mode !== "VERIFIED_API" ? <DataSourceIndicator mode={districts.data.mode} /> : null}<PrototypeNote /></span>} />;
  const controls = <div className="phase5-controls">
    <label>Year<select value={year} onChange={(change) => { setYear(operationalYearSchema.parse(Number(change.target.value))); setCaseId(""); setSelectedId(null); }}>{YEARS.map((item) => <option key={item} value={item}>{item}</option>)}</select></label>
    {districtsAvailable ? <>
      <label>Historical case<select value={selectedCase?.case_id ?? ""} onChange={(change) => { setCaseId(change.target.value); setSelectedId(null); }}>{cases.map((item) => <option key={item.case_id} value={item.case_id}>{caseDisplayLabel(item)}</option>)}</select></label>
      <label>Corrected model<select value={model} onChange={(change) => setModel(operationalDistrictModelSchema.parse(change.target.value))}>{operationalDistrictModelSchema.options.map((item) => <option key={item} value={item}>{MODEL_LABEL[item]}</option>)}</select></label>
      <label>Map shows<select value={variable} onChange={(change) => setVariable(change.target.value as MapVariable)}>{(Object.keys(MAP_VARIABLE) as MapVariable[]).map((item) => <option key={item} value={item}>{MAP_VARIABLE[item].label}</option>)}</select></label>
    </> : null}
  </div>;

  if (availability.isPending || caseList.isPending) return <div className="page-content districts-page">{heading}<LoadingState label="Loading district availability" /></div>;
  if (availability.isError || !availability.data?.data) return <div className="page-content districts-page">{heading}<ErrorState message={availability.data?.message ?? "Year availability metadata unavailable."} /></div>;
  if (!districtsAvailable) {
    return <div className="page-content districts-page">{heading}{controls}
      <div className="state-message" role="status"><strong>No district product for {year}</strong>
        {availability.data.data.notes.filter((note) => /district/i.test(note)).map((note) => <p key={note}>{note}</p>)}
        <p className="phase5-caveat">Choose 2024 or 2025 for the district product. Other views of {year} are in Forecast &amp; Atmosphere and the Casebook.</p></div></div>;
  }
  if (caseList.isError || !caseList.data?.data) return <div className="page-content districts-page">{heading}{controls}<ErrorState message={caseList.data?.message ?? "Frozen case catalogue unavailable."} /></div>;
  if (geometry.isPending || districts.isPending) return <div className="page-content districts-page">{heading}{controls}<LoadingState label="Loading district aggregation" /></div>;
  if (geometry.isError || !geometry.data) return <div className="page-content districts-page">{heading}{controls}<ErrorState message="District geometry unavailable." /></div>;
  if (districts.isError || !body || !list) {
    return <div className="page-content districts-page">{heading}{controls}<ErrorState message={districts.data?.mode === "INTEGRITY_FAILURE" ? `Scientific artifact integrity check failed: ${districts.data.message}. This is a hard failure and is not masked by cached data.` : (districts.data?.message ?? "District aggregation is unavailable for this case.")} /></div>;
  }
  const geo = geometry.data;
  const regime = body.predicted_regime;

  return <div className="page-content districts-page">{heading}{controls}
    <div className="phase5-context-strip"><strong>{year} · {body.year_role === "FINAL_TEST_COMPLETED" ? "Consumed final-test holdout (historical replay)" : "Validation / selection year"}</strong>
      <span>{body.model_role}</span>{regime ? <span>Forecast-only pseudo-regime: {regimeName(regime)}</span> : null}<span>Not live warning guidance</span></div>
    <div className="case-meta"><span><b>DISTRICTS</b> {list.length} case-valid of {body.source_district_count} intersecting the domain</span><span><b>METHOD</b> Area-overlap weighting</span><span><b>WEIGHTS</b> sha256 {body.weights_sha256.slice(0, 12)}…</span></div>
    <div className="districts-layout"><section className="districts-map-panel" aria-label="District rainfall map"><div className="map-panel-heading"><div><strong>{MAP_VARIABLE[variable].label} · district mean rainfall</strong><span>{list.length} case-valid · {geo.geometry.features.length} source districts intersect domain</span></div></div>
      <MapControls district onReset={() => mapRef.current?.fitBounds(mapBounds([67.875, 9.875, 80.125, 22.125]), { padding: 18, duration: 0 })} onZoom={(delta) => mapRef.current?.zoomTo((mapRef.current?.getZoom() ?? 0) + delta, { duration: 150 })} />
      <DistrictMap geometry={geo.geometry} districts={mapDistricts} selectedId={effectiveId} onSelect={(id) => selectDistrict(id, geo)} onReady={(map) => { mapRef.current = map; }} />
      <div className="district-map-legend"><RainLegend /></div>
      <p className="micro-note">Polygon color is the frozen case-specific district mean of the selected variable, not interpolated grid rainfall. Geography: {body.geometry_source} · {body.geometry_license}. Domain-limited coverage only.</p></section>
      <aside className="district-detail"><span className="small-label">DISTRICT INSPECTOR</span>{selected ? <><h2>{selected.district_name}</h2>
        <p className="micro-note">{selected.valid_grid_cells} valid intersecting grid cells.</p>
        <div className="detail-pair"><span>Raw GEFS mean <b>{mm(selected.raw_mean_mm)}</b></span><span>Corrected mean <b>{mm(selected.corrected_mean_mm)}</b></span><span>IMD observed mean <b>{mm(selected.observed_mean_mm)}</b></span><span>Corrected − Raw <b>{mm(selected.corrected_mean_mm - selected.raw_mean_mm)}</b></span><span>Corrected − IMD <b>{mm(selected.corrected_mean_mm - selected.observed_mean_mm)}</b></span><span>Raw − IMD <b>{mm(selected.raw_mean_mm - selected.observed_mean_mm)}</b></span></div>
        <div className="detail-pair"><span>Corrected maximum <b>{mm(selected.corrected_max_mm)}</b></span><span>IMD maximum <b>{mm(selected.observed_max_mm)}</b></span><span>Heavy probability <b>{percent(selected.heavy_probability)}</b></span><span>Very Heavy probability <b>{percent(selected.very_heavy_probability)}</b></span><span>Corrected heavy area <b>{percent(selected.heavy_area_fraction)}</b></span><span>IMD heavy area <b>{percent(selected.observed_heavy_area_fraction)}</b></span><span>Corrected very heavy area <b>{percent(selected.very_heavy_area_fraction)}</b></span><span>IMD very heavy area <b>{percent(selected.observed_very_heavy_area_fraction)}</b></span></div></> : <><h2>No case-valid district</h2><p>The selected historical case has no district product in this domain.</p></>}</aside></div>
    <SectionHeading title="District product" note="Sort by any column · probabilities and area fractions are distinct measures · IMD columns are historical replay" />
    <div className="district-table-wrap"><table className="science-table district-table"><caption className="sr-only">Area-weighted district rainfall, event probabilities and IMD replay for the selected historical operational-era case</caption><thead><tr>{columns.map((column) => <th scope="col" key={column.key} aria-sort={sort === column.key ? ascending ? "ascending" : "descending" : "none"}><button type="button" onClick={() => changeSort(column.key)}>{column.label}{sort === column.key ? ascending ? " ↑" : " ↓" : ""}</button></th>)}</tr></thead>
      <tbody>{ordered.map((item) => <tr key={item.district_id} className={item.district_id === effectiveId ? "selected-row" : ""}><th scope="row"><button type="button" onClick={() => selectDistrict(item.district_id, geo)}>{item.district_name}</button></th><td>{mm(item.raw_mean_mm)}</td><td>{mm(item.corrected_mean_mm)}</td><td>{mm(item.observed_mean_mm)}</td><td>{mm(item.corrected_mean_mm - item.observed_mean_mm)}</td><td>{percent(item.heavy_probability)}</td><td>{percent(item.very_heavy_probability)}</td><td>{percent(item.heavy_area_fraction)}</td><td>{percent(item.observed_heavy_area_fraction)}</td></tr>)}</tbody></table></div>
    <ul className="phase5-caveats">{body.caveats.map((caveat) => <li key={caveat} className="phase5-caveat">{caveat}</li>)}</ul>
  </div>;
}
