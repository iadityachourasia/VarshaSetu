"use client";

import dynamic from "next/dynamic";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { useMemo, useRef, useState } from "react";
import { CartesianGrid, Legend, Line, LineChart, Tooltip, XAxis, YAxis } from "recharts";
import type { Map as MapLibreMap } from "maplibre-gl";
import type { District, Geometry } from "@/lib/api/science";
import { geometrySchema, getScience } from "@/lib/api/science";
import {
  getOperationalAvailability, getOperationalDistricts, getOperationalDistrictsCompare, getOperationalDistrictHistory,
  operationalDistrictModelSchema, operationalYearSchema,
  type OperationalDistrictCompareRow, type OperationalDistrictModel, type OperationalDistrictRow, type OperationalYear,
} from "@/lib/api/operational";
import { loadOperationalCaseList, caseDisplayLabel } from "@/lib/operational-case-list";
import { withStaticFallback } from "@/lib/data-source";
import { mm, percent, regimeName } from "@/lib/format";
import { errorColor, rainfallColor } from "@/lib/maps/grid";
import { IMD_COLOR, MODEL_COLOR } from "@/lib/model-colors";
import { DataSourceIndicator, ErrorState, LoadingState, PageHeading, PrototypeNote, SectionHeading } from "@/components/science/common";
import { ChartFrame } from "@/components/science/chart-frame";
import { RainLegend } from "@/components/maps/map-legend";
import { MapControls } from "@/components/maps/map-controls";
import { fitToData } from "@/components/maps/use-weather-map";
import { HashChip } from "@/components/ui/hash-chip";
import { DownloadLink } from "@/components/ui/download-link";

const DistrictMap = dynamic(() => import("./district-map"), { ssr: false, loading: () => <div className="map-placeholder" /> });

const YEARS = [2023, 2024, 2025] as const;
const MODELS = ["m1", "m2", "m3", "m4"] as const;
const MODEL_LABEL: Record<OperationalDistrictModel, string> = {
  m1: "M1 Ridge MOS (primary)", m2: "M2 global ML", m3: "M3 hard regime-routed", m4: "M4 soft regime-mixture",
};
const MODEL_SHORT: Record<OperationalDistrictModel, string> = { m1: "M1", m2: "M2", m3: "M3", m4: "M4" };
const MODEL_TOKEN = { m1: MODEL_COLOR.M1, m2: MODEL_COLOR.M2, m3: MODEL_COLOR.M3, m4: MODEL_COLOR.M4 } as const;
type MapVariable = "corrected" | "raw" | "observed" | "error";
const MAP_VARIABLE: Record<MapVariable, { label: string; field: "corrected_mean_mm" | "raw_mean_mm" | "observed_mean_mm" | "error" }> = {
  corrected: { label: "Corrected mean", field: "corrected_mean_mm" },
  raw: { label: "Raw GEFS mean", field: "raw_mean_mm" },
  observed: { label: "IMD observed mean (replay)", field: "observed_mean_mm" },
  error: { label: "Selected model error vs IMD (mm)", field: "error" },
};
type View = "single" | "compare";
type Show = "means" | "errors" | "improvement";
const SHOW_LABEL: Record<Show, string> = { means: "District means", errors: "Error vs IMD (mean − IMD)", improvement: "Improvement vs Raw (|Raw err| − |model err|)" };
type SortKey = "district_name" | "raw_mean_mm" | "corrected_mean_mm" | "observed_mean_mm" | "error_mm" | "heavy_probability" | "very_heavy_probability" | "heavy_area_fraction" | "observed_heavy_area_fraction";
const columns: { key: SortKey; label: string }[] = [
  { key: "district_name", label: "District" }, { key: "raw_mean_mm", label: "Raw Mean" },
  { key: "corrected_mean_mm", label: "Corrected Mean" }, { key: "observed_mean_mm", label: "IMD Mean" },
  { key: "error_mm", label: "Corrected − IMD" }, { key: "heavy_probability", label: "Heavy P" },
  { key: "very_heavy_probability", label: "Very Heavy P" }, { key: "heavy_area_fraction", label: "Corrected Heavy Area" },
  { key: "observed_heavy_area_fraction", label: "IMD Heavy Area" },
];
type CompareSort = "district_name" | "raw" | "observed" | OperationalDistrictModel;

const valueOf = (row: OperationalDistrictRow, key: SortKey): string | number =>
  key === "error_mm" ? row.corrected_mean_mm - row.observed_mean_mm : (row[key as keyof OperationalDistrictRow] as string | number | null) ?? Number.NEGATIVE_INFINITY;
const signed = (value: number) => `${value > 0 ? "+" : ""}${value.toFixed(1)} mm`;

function compareValue(row: OperationalDistrictCompareRow, key: CompareSort, show: Show): string | number {
  if (key === "district_name") return row.district_name;
  if (key === "observed") return row.observed_mean_mm;
  if (key === "raw") return show === "means" ? row.raw_mean_mm : show === "errors" ? row.raw_error_mm : 0;
  const cell = row.models[key];
  return show === "means" ? cell.mean_mm : show === "errors" ? cell.error_mm : cell.improvement_vs_raw_mm;
}

function positions(value: unknown, out: number[][] = []): number[][] {
  if (!Array.isArray(value)) return out;
  if (value.length >= 2 && typeof value[0] === "number" && typeof value[1] === "number") out.push(value as number[]);
  else value.forEach((item) => positions(item, out));
  return out;
}

function ErrorLegend() {
  return <div className="district-error-legend" role="img" aria-label="Diverging scale: blue under-forecast, grey near zero, red over-forecast, from minus 100 to plus 100 millimetres">
    <span>−100 mm · under-forecast</span><i aria-hidden="true" /><span>over-forecast · +100 mm</span>
  </div>;
}

function DistrictHistory({ year, districtId, model }: { year: OperationalYear; districtId: string; model: OperationalDistrictModel }) {
  const history = useQuery({
    queryKey: ["operational-district-history", year, districtId, model],
    queryFn: () => withStaticFallback(() => getOperationalDistrictHistory(year, districtId, model), null),
    staleTime: 5 * 60_000,
  });
  const body = history.data?.data;
  const data = useMemo(() => (body?.points ?? []).map((point, index) => ({
    index, label: `${point.initialization_utc.slice(0, 10)} · Day ${point.lead_hours / 24}`, observed: point.observed_mean_mm, raw: point.raw_mean_mm, model: point.model_mean_mm,
  })), [body]);
  if (history.isPending) return <LoadingState label="Loading district history" />;
  if (history.isError || !body) {
    return <ErrorState message={history.data?.mode === "INTEGRITY_FAILURE" ? `Scientific artifact integrity check failed: ${history.data.message}.` : (history.data?.message ?? "District history is unavailable.")} />;
  }
  return <section className="phase5-analysis-block district-history" aria-labelledby="district-history-title">
    <h2 id="district-history-title">{body.district_name} · district-mean history across {body.case_count} {year} cases</h2>
    <p className="phase5-caveat">{body.descriptive_only_note}</p>
    <ChartFrame caption={<>Each point is one paired case (initialization date × lead), ordered by date. Lines join cases only to show order; the series are district area-weighted means of Raw GEFS, {MODEL_SHORT[model]} ({body.model_role}) and IMD. {body.case_count} cases in which this district had at least one valid paired cell.</>}>
      <LineChart data={data} margin={{ top: 10, right: 15, bottom: 0, left: -10 }}>
        <CartesianGrid stroke="var(--line)" strokeDasharray="2 6" />
        <XAxis dataKey="index" tick={{ fill: "var(--text-subtle)", fontSize: 11 }} tickFormatter={(value) => data[value as number]?.label.slice(5, 10) ?? ""} minTickGap={30} />
        <YAxis tick={{ fill: "var(--text-subtle)", fontSize: 11 }} unit=" mm" />
        <Tooltip labelFormatter={(value) => data[value as number]?.label ?? ""} formatter={(value) => (typeof value === "number" ? `${value.toFixed(1)} mm` : value)} />
        <Legend />
        <Line type="linear" dataKey="observed" name="IMD observed" stroke={IMD_COLOR} strokeWidth={2} dot={{ r: 2 }} isAnimationActive={false} />
        <Line type="linear" dataKey="raw" name="Raw GEFS" stroke={MODEL_COLOR.M0} strokeWidth={1.5} dot={{ r: 2 }} isAnimationActive={false} />
        <Line type="linear" dataKey="model" name={MODEL_SHORT[model]} stroke={MODEL_TOKEN[model]} strokeWidth={1.5} strokeDasharray="5 3" dot={{ r: 2 }} isAnimationActive={false} />
      </LineChart>
    </ChartFrame>
  </section>;
}

export function OperationalDistrictWorkspace({ initialYear, initialCase }: { initialYear?: OperationalYear; initialCase?: string }) {
  const [year, setYear] = useState<OperationalYear>(initialYear ?? 2025);
  const [caseId, setCaseId] = useState(initialCase ?? "");
  const [model, setModel] = useState<OperationalDistrictModel>("m1");
  const [variable, setVariable] = useState<MapVariable>("corrected");
  const [view, setView] = useState<View>("single");
  const [show, setShow] = useState<Show>("means");
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [sort, setSort] = useState<SortKey>("observed_mean_mm");
  const [ascending, setAscending] = useState(false);
  const [compareSort, setCompareSort] = useState<CompareSort>("observed");
  const [compareAscending, setCompareAscending] = useState(false);
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
  const compare = useQuery({
    queryKey: ["operational-districts-compare", year, selectedCase?.case_id],
    queryFn: () => withStaticFallback(() => getOperationalDistrictsCompare(year, selectedCase!.case_id), null),
    enabled: Boolean(selectedCase) && districtsAvailable,
  });

  const body = districts.data?.data ?? null;
  const compareBody = compare.data?.data ?? null;
  const compareById = useMemo(() => new Map((compareBody?.districts ?? []).map((row) => [row.district_id, row])), [compareBody]);
  const list = body?.districts;
  const errorMapReady = compareById.size > 0;
  const activeVariable: MapVariable = variable === "error" && !errorMapReady ? "corrected" : variable;
  const ordered = useMemo(() => [...(list ?? [])].sort((a, b) => {
    const x = valueOf(a, sort), y = valueOf(b, sort);
    const order = typeof x === "string" && typeof y === "string" ? x.localeCompare(y) : Number(x) - Number(y);
    return (ascending ? order : -order) || a.district_name.localeCompare(b.district_name);
  }), [list, sort, ascending]);
  const compareOrdered = useMemo(() => [...(compareBody?.districts ?? [])].sort((a, b) => {
    const x = compareValue(a, compareSort, show), y = compareValue(b, compareSort, show);
    const order = typeof x === "string" && typeof y === "string" ? x.localeCompare(y) : Number(x) - Number(y);
    return (compareAscending ? order : -order) || a.district_name.localeCompare(b.district_name);
  }), [compareBody, compareSort, compareAscending, show]);
  // The shared choropleth reads `corrected_mean_mm`; feed it the selected variable (and its colour scale).
  const mapDistricts: District[] = useMemo(() => (list ?? []).map((row) => {
    const value = activeVariable === "error"
      ? compareById.get(row.district_id)?.models[model].error_mm ?? 0
      : row[MAP_VARIABLE[activeVariable].field as "corrected_mean_mm" | "raw_mean_mm" | "observed_mean_mm"];
    return {
      district_id: row.district_id, district_name: row.district_name, raw_mean_mm: row.raw_mean_mm, corrected_mean_mm: value,
      corrected_max_mm: row.corrected_max_mm, heavy_probability: row.heavy_probability ?? 0, very_heavy_probability: row.very_heavy_probability ?? 0,
      heavy_area_fraction: row.heavy_area_fraction, very_heavy_area_fraction: row.very_heavy_area_fraction,
      dominant_regime: body?.predicted_regime ?? "", valid_grid_cells: row.valid_grid_cells,
    };
  }), [list, activeVariable, compareById, model, body?.predicted_regime]);

  const defaultId = list?.reduce<OperationalDistrictRow | undefined>((first, item) => !first || item.observed_mean_mm > first.observed_mean_mm ? item : first, undefined)?.district_id ?? null;
  const effectiveId = selectedId ?? defaultId;
  // Linked hover: pointing at a table row outlines its polygon on the map, and pointing at a polygon marks its table row.
  const [hoveredId, setHoveredId] = useState<string | null>(null);
  const rowProps = (districtId: string) => ({ className: `${districtId === effectiveId ? "selected-row" : ""}${districtId === hoveredId ? " linked-row" : ""}`.trim(), onMouseEnter: () => setHoveredId(districtId), onMouseLeave: () => setHoveredId(null), onFocus: () => setHoveredId(districtId), onBlur: () => setHoveredId(null) });
  const selected = list?.find((item) => item.district_id === effectiveId) ?? null;
  const selectedCompare = effectiveId ? compareById.get(effectiveId) ?? null : null;
  const changeSort = (key: SortKey) => { if (sort === key) setAscending(!ascending); else { setSort(key); setAscending(key === "district_name"); } };
  const changeCompareSort = (key: CompareSort) => { if (compareSort === key) setCompareAscending(!compareAscending); else { setCompareSort(key); setCompareAscending(key === "district_name"); } };

  const selectDistrict = (id: string, geo: Geometry) => {
    setSelectedId(id);
    const feature = geo.geometry.features.find((item) => item.properties.district_id === id);
    const points = positions((feature?.geometry as { coordinates?: unknown } | undefined)?.coordinates);
    if (!points.length || !mapRef.current) return;
    const west = Math.max(67.875, Math.min(...points.map((p) => p[0]))), east = Math.min(80.125, Math.max(...points.map((p) => p[0])));
    const south = Math.max(9.875, Math.min(...points.map((p) => p[1]))), north = Math.min(22.125, Math.max(...points.map((p) => p[1])));
    if (west < east && south < north) mapRef.current.fitBounds([[west, south], [east, north]], { padding: 45, maxZoom: 8, duration: 300 });
  };

  const heading = <PageHeading title="District Intelligence" subtitle={`Historical District Decision-Support Prototype · historical operational GEFS · ${year} · area-weighted district aggregation of frozen grids; historical replay, not an advisory or live warning.`}
    action={<span style={{ display: "flex", gap: 8, alignItems: "center" }}>{districts.data && districts.data.mode !== "VERIFIED_API" ? <DataSourceIndicator mode={districts.data.mode} /> : null}<PrototypeNote /></span>} />;
  const controls = <div className="phase5-controls">
    <label>Year<select value={year} onChange={(change) => { setYear(operationalYearSchema.parse(Number(change.target.value))); setCaseId(""); setSelectedId(null); }}>{YEARS.map((item) => <option key={item} value={item}>{item}</option>)}</select></label>
    {districtsAvailable ? <>
      <label>Historical case<select value={selectedCase?.case_id ?? ""} onChange={(change) => { setCaseId(change.target.value); setSelectedId(null); }}>{cases.map((item) => <option key={item.case_id} value={item.case_id}>{caseDisplayLabel(item)}</option>)}</select></label>
      <label>Corrected model<select value={model} onChange={(change) => setModel(operationalDistrictModelSchema.parse(change.target.value))}>{operationalDistrictModelSchema.options.map((item) => <option key={item} value={item}>{MODEL_LABEL[item]}</option>)}</select></label>
      <label>Map shows<select value={activeVariable} onChange={(change) => setVariable(change.target.value as MapVariable)}>{(Object.keys(MAP_VARIABLE) as MapVariable[]).map((item) => <option key={item} value={item} disabled={item === "error" && !errorMapReady}>{MAP_VARIABLE[item].label}</option>)}</select></label>
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
  const tableMetric = (cell: OperationalDistrictCompareRow["models"]["m1"]) => show === "means" ? mm(cell.mean_mm) : show === "errors" ? signed(cell.error_mm) : signed(cell.improvement_vs_raw_mm);

  return <div className="page-content districts-page">{heading}{controls}
    <div className="phase5-context-strip"><strong>{year} · {body.year_role === "FINAL_TEST_COMPLETED" ? "Consumed final-test holdout (historical replay)" : "Validation / selection year"}</strong>
      <span>{body.model_role}</span>{regime ? <span>Forecast-only pseudo-regime: {regimeName(regime)}</span> : null}<span>Not live warning guidance</span></div>
    <div className="case-meta"><span><b>DISTRICTS</b> {list.length} case-valid of {body.source_district_count} intersecting the domain</span><span><b>METHOD</b> Area-overlap weighting</span><span><b>WEIGHTS</b> sha256 <HashChip hash={body.weights_sha256} /></span></div>
    <div className="districts-layout"><section className="districts-map-panel" aria-label="District rainfall map"><div className="map-panel-heading"><div><strong>{MAP_VARIABLE[activeVariable].label} · district mean rainfall</strong><span>{list.length} case-valid · {geo.geometry.features.length} source districts intersect domain</span></div></div>
      <MapControls district onReset={() => { if (mapRef.current) fitToData(mapRef.current); }} onZoom={(delta) => mapRef.current?.zoomTo((mapRef.current?.getZoom() ?? 0) + delta, { duration: 150 })} />
      <DistrictMap geometry={geo.geometry} districts={mapDistricts} selectedId={effectiveId} hoveredId={hoveredId} onHover={setHoveredId} onSelect={(id) => selectDistrict(id, geo)} onReady={(map) => { mapRef.current = map; }} colorFor={activeVariable === "error" ? errorColor : rainfallColor} />
      <div className="district-map-legend">{activeVariable === "error" ? <ErrorLegend /> : <RainLegend />}</div>
      <p className="micro-note">Polygon color is the frozen case-specific district mean of the selected variable{activeVariable === "error" ? ` (${MODEL_SHORT[model]} minus IMD; a district-mean error for this one case, not a skill score)` : ""}, not interpolated grid rainfall. Geography: {body.geometry_source} · {body.geometry_license}. Domain-limited coverage only.</p></section>
      <aside className="district-detail"><span className="small-label">DISTRICT INSPECTOR</span>{selected ? <><h2>{selected.district_name}</h2>
        <p className="micro-note">{selected.valid_grid_cells} valid intersecting grid cells.</p>
        <div className="detail-pair"><span>Raw GEFS mean <b>{mm(selected.raw_mean_mm)}</b></span><span>Corrected mean <b>{mm(selected.corrected_mean_mm)}</b></span><span>IMD observed mean <b>{mm(selected.observed_mean_mm)}</b></span><span>Corrected − Raw <b>{mm(selected.corrected_mean_mm - selected.raw_mean_mm)}</b></span><span>Corrected − IMD <b>{mm(selected.corrected_mean_mm - selected.observed_mean_mm)}</b></span><span>Raw − IMD <b>{mm(selected.raw_mean_mm - selected.observed_mean_mm)}</b></span></div>
        <div className="detail-pair"><span>Corrected maximum <b>{mm(selected.corrected_max_mm)}</b></span><span>IMD maximum <b>{mm(selected.observed_max_mm)}</b></span><span>Heavy probability <b>{percent(selected.heavy_probability)}</b></span><span>Very Heavy probability <b>{percent(selected.very_heavy_probability)}</b></span><span>Corrected heavy area <b>{percent(selected.heavy_area_fraction)}</b></span><span>IMD heavy area <b>{percent(selected.observed_heavy_area_fraction)}</b></span><span>Corrected very heavy area <b>{percent(selected.very_heavy_area_fraction)}</b></span><span>IMD very heavy area <b>{percent(selected.observed_very_heavy_area_fraction)}</b></span></div>
        {selectedCompare ? <table className="phase5-table district-model-table"><caption className="sr-only">All corrected models for the selected district and case</caption>
          <thead><tr><th scope="col">Model</th><th scope="col">Mean</th><th scope="col">Error vs IMD</th><th scope="col">Closer than Raw?</th></tr></thead>
          <tbody><tr><th scope="row">Raw GEFS</th><td>{mm(selectedCompare.raw_mean_mm)}</td><td>{signed(selectedCompare.raw_error_mm)}</td><td>reference</td></tr>
            {MODELS.map((key) => { const cell = selectedCompare.models[key]; return <tr key={key}><th scope="row">{MODEL_SHORT[key]}</th><td>{mm(cell.mean_mm)}</td><td>{signed(cell.error_mm)}</td><td>{cell.improvement_vs_raw_mm > 0 ? "closer" : cell.improvement_vs_raw_mm < 0 ? "farther" : "equal"} ({signed(cell.improvement_vs_raw_mm)})</td></tr>; })}</tbody></table> : null}
      </> : <><h2>No case-valid district</h2><p>The selected historical case has no district product in this domain.</p></>}</aside></div>

    {effectiveId && selected ? <DistrictHistory year={year} districtId={effectiveId} model={model} /> : null}

    <p className="micro-note">District-level verification of these models (event definitions fixed in advance, support rules, improved/worsened counts): <Link href="/verification">Verification Lab → District-level tab</Link> (Track B, 2024 and 2025).</p>
    <SectionHeading title="District product" note="Sort by any column · probabilities and area fractions are distinct measures · IMD columns are historical replay" />
    <div className="phase5-tab-row" role="group" aria-label="Table view"><button type="button" aria-pressed={view === "single"} onClick={() => setView("single")}>Selected model</button><button type="button" aria-pressed={view === "compare"} onClick={() => setView("compare")} disabled={!compareBody}>Compare all models</button></div>
    {compareBody && selectedCase ? <p className="regime-evidence-downloads" data-testid="district-export"><strong>Download this case</strong> (Raw, M1 to M4 and IMD for every district, with weights and geometry hashes):{" "}
      {(["csv", "json"] as const).map((format, index) => <span key={format}>{index ? " · " : ""}<DownloadLink href={`/api/science/operational/${year}/cases/${selectedCase.case_id}/districts/export?format=${format}`}>{format.toUpperCase()}</DownloadLink></span>)}</p> : null}
    {view === "compare" && compareBody ? <>
      <div className="phase5-tab-row" role="group" aria-label="Comparison measure">{(Object.keys(SHOW_LABEL) as Show[]).map((item) => <button key={item} type="button" aria-pressed={show === item} onClick={() => setShow(item)}>{SHOW_LABEL[item]}</button>)}</div>
      <p className="micro-note">{show === "improvement" ? compareBody.improvement_definition : "Raw and the four corrected models share the same area weights, valid cells and IMD replay; differences are not skill scores."}</p>
      <div className="district-table-wrap"><table className="science-table district-table district-compare-table"><caption className="sr-only">Area-weighted district comparison of Raw GEFS and all four corrected models with IMD replay for the selected historical case</caption>
        <thead><tr>{([["district_name", "District"], ["raw", show === "improvement" ? "Raw (reference)" : "Raw"], ...MODELS.map((key) => [key, MODEL_SHORT[key]]), ["observed", "IMD Mean"]] as [CompareSort, string][]).map(([key, label]) => <th scope="col" key={key} aria-sort={compareSort === key ? compareAscending ? "ascending" : "descending" : "none"}><button type="button" onClick={() => changeCompareSort(key)}>{label}{compareSort === key ? compareAscending ? " ↑" : " ↓" : ""}</button></th>)}</tr></thead>
        <tbody>{compareOrdered.map((row) => <tr key={row.district_id} {...rowProps(row.district_id)}><th scope="row"><button type="button" onClick={() => selectDistrict(row.district_id, geo)}>{row.district_name}</button></th>
          <td>{show === "means" ? mm(row.raw_mean_mm) : show === "errors" ? signed(row.raw_error_mm) : "—"}</td>{MODELS.map((key) => <td key={key}>{tableMetric(row.models[key])}</td>)}<td>{mm(row.observed_mean_mm)}</td></tr>)}</tbody></table></div>
    </> : <div className="district-table-wrap"><table className="science-table district-table"><caption className="sr-only">Area-weighted district rainfall, event probabilities and IMD replay for the selected historical operational-era case</caption><thead><tr>{columns.map((column) => <th scope="col" key={column.key} aria-sort={sort === column.key ? ascending ? "ascending" : "descending" : "none"}><button type="button" onClick={() => changeSort(column.key)}>{column.label}{sort === column.key ? ascending ? " ↑" : " ↓" : ""}</button></th>)}</tr></thead>
      <tbody>{ordered.map((item) => <tr key={item.district_id} {...rowProps(item.district_id)}><th scope="row"><button type="button" onClick={() => selectDistrict(item.district_id, geo)}>{item.district_name}</button></th><td>{mm(item.raw_mean_mm)}</td><td>{mm(item.corrected_mean_mm)}</td><td>{mm(item.observed_mean_mm)}</td><td>{mm(item.corrected_mean_mm - item.observed_mean_mm)}</td><td>{percent(item.heavy_probability)}</td><td>{percent(item.very_heavy_probability)}</td><td>{percent(item.heavy_area_fraction)}</td><td>{percent(item.observed_heavy_area_fraction)}</td></tr>)}</tbody></table></div>}
    <ul className="phase5-caveats">{body.caveats.map((caveat) => <li key={caveat} className="phase5-caveat">{caveat}</li>)}</ul>
  </div>;
}
