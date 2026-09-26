"use client";

import dynamic from "next/dynamic";
import { useRouter } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { useMemo, useRef, useState } from "react";
import type { Map as MapLibreMap } from "maplibre-gl";
import type { CaseSummary, District, Geometry } from "@/lib/api/science";
import { districtsSchema, getScience } from "@/lib/api/science";
import { leadName, mm, percent, regimeName, utc } from "@/lib/format";
import { CaseSelector } from "@/components/science/case-selector";
import { ErrorState, LoadingState, PageHeading, PrototypeNote, SectionHeading } from "@/components/science/common";
import { RainLegend } from "@/components/maps/map-legend";
import { MapControls } from "@/components/maps/map-controls";
import { mapBounds } from "@/components/maps/use-weather-map";

const DistrictMap = dynamic(() => import("./district-map"), { ssr: false, loading: () => <div className="map-placeholder" /> });
type SortKey = "district_name" | "corrected_mean_mm" | "corrected_max_mm" | "heavy_probability" | "very_heavy_probability" | "heavy_area_fraction" | "very_heavy_area_fraction";
const columns: { key: SortKey; label: string }[] = [
  { key: "district_name", label: "District" }, { key: "corrected_mean_mm", label: "Corrected Mean" },
  { key: "corrected_max_mm", label: "Corrected Max" }, { key: "heavy_probability", label: "Heavy P" },
  { key: "very_heavy_probability", label: "Very Heavy P" }, { key: "heavy_area_fraction", label: "Heavy Area" },
  { key: "very_heavy_area_fraction", label: "Very Heavy Area" },
];

export function DistrictWorkspace({ cases, demos, initialCase, geometry }: { cases: CaseSummary[]; demos: CaseSummary[]; initialCase: string; geometry: Geometry }) {
  const router = useRouter();
  const [caseId, setCaseId] = useState(initialCase);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [sort, setSort] = useState<SortKey>("corrected_mean_mm");
  const [ascending, setAscending] = useState(false);
  const mapRef = useRef<MapLibreMap | null>(null);
  const districts = useQuery({ queryKey: ["districts", caseId], queryFn: () => getScience(`/cases/${caseId}/districts`, districtsSchema) });
  const list = districts.data?.data.districts;
  const ordered = useMemo(() => [...(list ?? [])].sort((a, b) => {
    const x = a[sort], y = b[sort];
    const order = typeof x === "string" && typeof y === "string" ? x.localeCompare(y) : Number(x) - Number(y);
    return (ascending ? order : -order) || a.district_name.localeCompare(b.district_name);
  }), [list, sort, ascending]);
  const defaultId = list?.reduce((first, item) => !first || item.corrected_mean_mm > first.corrected_mean_mm || item.corrected_mean_mm === first.corrected_mean_mm && item.district_id.localeCompare(first.district_id) < 0 ? item : first, undefined as District | undefined)?.district_id ?? null;
  const effectiveId = selectedId ?? defaultId;
  const selected = list?.find((item) => item.district_id === effectiveId) ?? null;
  const record = cases.find((item) => item.case_id === caseId);
  const changeSort = (key: SortKey) => { if (sort === key) setAscending(!ascending); else { setSort(key); setAscending(key === "district_name"); } };
  const selectDistrict = (id: string) => {
    setSelectedId(id);
    const feature = geometry.geometry.features.find((item) => item.properties.district_id === id);
    const coordinates = (feature?.geometry as { coordinates?: unknown } | undefined)?.coordinates;
    const positions: number[][] = [];
    const visit = (value: unknown) => {
      if (!Array.isArray(value)) return;
      if (value.length >= 2 && typeof value[0] === "number" && typeof value[1] === "number") positions.push(value as number[]);
      else value.forEach(visit);
    };
    visit(coordinates);
    if (positions.length && mapRef.current) {
      let minLon = Infinity, minLat = Infinity, maxLon = -Infinity, maxLat = -Infinity;
      for (const [lon, lat] of positions) {
        minLon = Math.min(minLon, lon); minLat = Math.min(minLat, lat);
        maxLon = Math.max(maxLon, lon); maxLat = Math.max(maxLat, lat);
      }
      const west = Math.max(67.875, minLon);
      const south = Math.max(9.875, minLat);
      const east = Math.min(80.125, maxLon);
      const north = Math.min(22.125, maxLat);
      if (west < east && south < north) mapRef.current.fitBounds([[west, south], [east, north]], { padding: 45, maxZoom: 8, duration: 300 });
    }
  };
  return <div className="page-content districts-page"><PageHeading title="District Intelligence" subtitle="2019 historical reforecast district analysis across the validated domain; not an advisory or live warning." action={<PrototypeNote />} />
    <CaseSelector cases={cases} demos={demos} selectedId={caseId} onSelect={(id) => { setCaseId(id); setSelectedId(null); router.replace(`/districts?case=${encodeURIComponent(id)}`, { scroll: false }); }} />
    {record ? <div className="case-meta"><span><b>VALID PERIOD</b> {utc(record.valid_period_start_utc)} — {utc(record.valid_period_end_utc)}</span><span><b>LEAD</b> {leadName(record.lead_hours)}</span><span><b>METHOD</b> Area-overlap weighting</span></div> : null}
    {districts.isPending ? <LoadingState label="Loading district aggregation" /> : districts.isError || !list ? <ErrorState /> : <>
      <div className="districts-layout"><section className="districts-map-panel"><div className="map-panel-heading"><div><strong>Corrected district mean rainfall</strong><span>{list.length} case-valid · {geometry.geometry.features.length} source districts intersect domain</span></div></div><MapControls district onReset={() => mapRef.current?.fitBounds(mapBounds([67.875, 9.875, 80.125, 22.125]), { padding: 18, duration: 0 })} onZoom={(delta) => mapRef.current?.zoomTo((mapRef.current?.getZoom() ?? 0) + delta, { duration: 150 })} /><DistrictMap geometry={geometry.geometry} districts={list} selectedId={effectiveId} onSelect={selectDistrict} onReady={(map) => { mapRef.current = map; }} /><div className="district-map-legend"><RainLegend /></div><p className="micro-note">Polygon color is the frozen case-specific corrected mean, not interpolated grid rainfall. Geography: {geometry.source} · {geometry.license}. Domain-limited coverage only.</p></section>
      <aside className="district-detail"><span className="small-label">DISTRICT INSPECTOR</span>{selected ? <><h2>{selected.district_name}</h2><p className="micro-note">{regimeName(selected.dominant_regime)} · {selected.valid_grid_cells} valid intersecting grid cells.</p><div className="detail-pair"><span>Raw GEFS mean <b>{mm(selected.raw_mean_mm)}</b></span><span>Corrected mean <b>{mm(selected.corrected_mean_mm)}</b></span><span>Corrected maximum <b>{mm(selected.corrected_max_mm)}</b></span><span>Change from Raw <b>{mm(selected.corrected_mean_mm - selected.raw_mean_mm)}</b></span></div><div className="detail-pair"><span>Heavy probability <b>{percent(selected.heavy_probability)}</b></span><span>Very Heavy probability <b>{percent(selected.very_heavy_probability)}</b></span><span>Heavy area <b>{percent(selected.heavy_area_fraction)}</b></span><span>Very Heavy area <b>{percent(selected.very_heavy_area_fraction)}</b></span></div></> : <><h2>No case-valid district</h2><p>The selected historical case has no district product in this domain.</p></>}</aside></div>
      <SectionHeading title="District product" note="Sort by any column · probabilities and area fractions are distinct measures" /><div className="district-table-wrap"><table className="science-table district-table"><caption className="sr-only">Area-weighted district rainfall and event probabilities for the selected historical case</caption><thead><tr>{columns.map((column) => <th scope="col" key={column.key} aria-sort={sort === column.key ? ascending ? "ascending" : "descending" : "none"}><button type="button" onClick={() => changeSort(column.key)}>{column.label}{sort === column.key ? ascending ? " ↑" : " ↓" : ""}</button></th>)}</tr></thead><tbody>{ordered.map((item: District) => <tr key={item.district_id} className={item.district_id === effectiveId ? "selected-row" : ""}><th scope="row"><button type="button" onClick={() => selectDistrict(item.district_id)}>{item.district_name}</button></th><td>{mm(item.corrected_mean_mm)}</td><td>{mm(item.corrected_max_mm)}</td><td>{percent(item.heavy_probability)}</td><td>{percent(item.very_heavy_probability)}</td><td>{percent(item.heavy_area_fraction)}</td><td>{percent(item.very_heavy_area_fraction)}</td></tr>)}</tbody></table></div>
    </>}
  </div>;
}
