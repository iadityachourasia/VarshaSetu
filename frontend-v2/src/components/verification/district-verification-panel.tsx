"use client";

import dynamic from "next/dynamic";
import { useQuery } from "@tanstack/react-query";
import { useMemo, useRef, useState } from "react";
import type { Map as MapLibreMap } from "maplibre-gl";
import type { District } from "@/lib/api/science";
import { geometrySchema, getScience } from "@/lib/api/science";
import {
  DISTRICT_BREAKDOWNS, DISTRICT_CONTRAST_KEYS, DISTRICT_DEFINITIONS, DISTRICT_MODELS, EVIDENCE_MODELS, EvidenceApiError, getDistrictVerification,
  type BootstrapStat, type DistrictBreakdown, type DistrictDefinition, type DistrictEntry, type DistrictModel, type DistrictVerification,
} from "@/lib/api/evidence";
import type { EvidenceThreshold } from "@/lib/api/evidence";
import { improvementColor } from "@/lib/maps/grid";
import { regimeName } from "@/lib/format";
import { ErrorState, LoadingState } from "@/components/science/common";
import { MapControls } from "@/components/maps/map-controls";
import { mapBounds } from "@/components/maps/use-weather-map";

const DistrictMap = dynamic(() => import("@/components/districts/district-map"), { ssr: false, loading: () => <div className="map-placeholder" /> });

type Metric = "POD" | "FAR" | "CSI" | "ETS" | "ratio";
const METRICS: { key: Metric; label: string }[] = [
  { key: "POD", label: "POD" }, { key: "FAR", label: "FAR" }, { key: "CSI", label: "CSI" }, { key: "ETS", label: "ETS" }, { key: "ratio", label: "Forecast / observed events" },
];
const DEFINITION_LABEL: Record<DistrictDefinition, string> = {
  E1: "E1 any valid cell ≥ threshold (primary)", E2: "E2 ≥ 25 % of valid area (secondary)", E3: "E3 district mean (sensitivity)",
};
const BREAKDOWN_LABEL: Record<DistrictBreakdown, string> = { pooled: "Pooled", by_lead: "By lead day", by_regime: "By pseudo-regime", by_region: "By latitude band" };
const MODEL_LABEL: Record<string, string> = { M0: "M0 Raw", M1: "M1 Ridge", M2: "M2 Global ML", M3: "M3 Hard regime", M4: "M4 Soft regime" };
const PAIR_LABEL: Record<string, string> = {
  M1_minus_M0: "M1 − Raw", M2_minus_M0: "M2 − Raw", M3_minus_M0: "M3 − Raw", M4_minus_M0: "M4 − Raw", M3_minus_M2: "M3 − M2", M4_minus_M2: "M4 − M2", M3_minus_M4: "M3 − M4",
};
const fixed = (value: number | null | undefined, digits = 3) => (value == null || !Number.isFinite(value) ? "undefined" : value.toFixed(digits));

function interval(stat: BootstrapStat | undefined, digits = 4) {
  if (!stat || stat.status !== "ok" || stat.point === undefined || !stat.interval95) return stat ? `not reported (${stat.status})` : "not reported";
  const [low, high] = stat.interval95;
  return `${stat.point >= 0 ? "+" : ""}${stat.point.toFixed(digits)} [${low.toFixed(digits)}, ${high.toFixed(digits)}] · interval ${low > 0 || high < 0 ? "excludes" : "includes"} 0`;
}

function groupLabel(kind: DistrictBreakdown, name: string) {
  if (kind === "by_regime") return regimeName(name);
  if (kind === "by_lead") return name.replace("day", "Day ");
  return name === "all" ? "All district-case pairs" : name;
}

function ImprovementLegend() {
  return <div className="district-error-legend" role="img" aria-label="Diverging scale: warm colours mean the corrected district mean is farther from IMD than Raw, teal means closer, from minus 5 to plus 5 millimetres">
    <span>−5 mm · farther than Raw</span><i className="district-improvement-ramp" aria-hidden="true" /><span>closer than Raw · +5 mm</span>
  </div>;
}

export function DistrictVerificationPanel({ year }: { year: number }) {
  const [definition, setDefinition] = useState<DistrictDefinition>("E1");
  const [threshold, setThreshold] = useState<EvidenceThreshold>("heavy");
  const [metric, setMetric] = useState<Metric>("CSI");
  const [breakdown, setBreakdown] = useState<DistrictBreakdown>("pooled");
  const [model, setModel] = useState<DistrictModel>("M1");
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [supportedOnly, setSupportedOnly] = useState(false);
  const mapRef = useRef<MapLibreMap | null>(null);
  const query = useQuery({ queryKey: ["district-verification", year], queryFn: () => getDistrictVerification(year), staleTime: 5 * 60_000 });
  const geometry = useQuery({ queryKey: ["district-geometry"], queryFn: () => getScience("/geometry/districts", geometrySchema) });
  const data = query.data;

  const rows = useMemo(() => {
    if (!data) return [] as DistrictEntry[];
    const withData = data.districts.filter((entry) => entry.improvement !== "insufficient_support");
    return supportedOnly ? withData.filter((entry) => entry.categorical.E1.heavy.status === "supported") : withData;
  }, [data, supportedOnly]);
  const ordered = useMemo(() => [...rows].sort((a, b) => {
    const x = a.improvement === "insufficient_support" ? -Infinity : a.improvement[model].mean_improvement_mm ?? -Infinity;
    const y = b.improvement === "insufficient_support" ? -Infinity : b.improvement[model].mean_improvement_mm ?? -Infinity;
    return y - x || a.district_name.localeCompare(b.district_name);
  }), [rows, model]);
  const mapDistricts: District[] = useMemo(() => (data?.districts ?? []).flatMap((entry) => entry.improvement === "insufficient_support" ? [] : [{
    district_id: entry.district_id, district_name: entry.district_name, raw_mean_mm: 0, corrected_mean_mm: entry.improvement[model].mean_improvement_mm ?? 0, corrected_max_mm: 0,
    heavy_probability: 0, very_heavy_probability: 0, heavy_area_fraction: 0, very_heavy_area_fraction: 0, dominant_regime: "", valid_grid_cells: entry.included_cases,
  }]), [data, model]);
  const selected = data?.districts.find((entry) => entry.district_id === (selectedId ?? ordered[0]?.district_id)) ?? null;

  if (query.isPending) return <LoadingState compact label="Loading district-level verification evidence" />;
  if (query.isError || !data) {
    const error = query.error;
    const integrity = error instanceof EvidenceApiError && error.code === "SCIENCE_INTEGRITY_FAILURE";
    return <ErrorState message={integrity ? `Evidence integrity check failed: ${error.message}. This is a hard failure.` : error instanceof Error ? error.message : "District-level verification evidence is unavailable."} />;
  }
  const blocks = data.categorical[definition][threshold][breakdown];
  const postHoc = /POST-HOC/.test(data.evidence_label);
  const excluded = data.inclusion.districts_excluded;

  return <section className="phase5-analysis-block district-verification" aria-labelledby="district-verification-title">
    <h2 id="district-verification-title">District-level verification · protocol v1</h2>
    <p className={postHoc ? "phase5-caveat" : undefined}><strong>{data.evidence_label}</strong>. Track {data.track} · {data.year} · {data.inclusion.cases} cases · {data.inclusion.districts_included} of {data.inclusion.districts_total} districts included (≥ {data.inclusion.min_valid_cells} valid IMD land cells; {excluded.length} excluded) · {data.inclusion.district_case_pairs.toLocaleString("en-GB")} district-case pairs.
      Event definitions, support rules and groupings were approved and frozen (SHA-256 {data.protocol_sha256.slice(0, 12)}…) before any result was computed. Reproduction gate: {data.reproduction.status} ({data.reproduction.check_count} checks). Evidence SHA-256 {data.evidence_sha256.slice(0, 12)}…</p>
    <p className="regime-evidence-downloads"><strong>District verification report</strong> (generated from this hash-verified evidence):{" "}
      {(["md", "csv", "json"] as const).map((format, index) => <span key={format}>{index ? " · " : ""}<a href={`/api/science/evidence/district-verification/report?year=${year}&format=${format}`} download>{format === "md" ? "Markdown" : format.toUpperCase()}</a></span>)}</p>

    <h3>Pooled district-mean error (mm/24 h)</h3>
    <div className="district-table-wrap"><table className="phase5-table regime-evidence-table"><caption className="sr-only">Pooled district-mean RMSE, MAE and bias of Raw and the four corrected models against IMD</caption>
      <thead><tr><th scope="col">Model</th><th scope="col">RMSE</th><th scope="col">MAE</th><th scope="col">Bias (model − IMD)</th><th scope="col">District-case pairs</th></tr></thead>
      <tbody>{EVIDENCE_MODELS.map((m) => { const c = data.continuous.pooled.all[m]; return <tr key={m}><th scope="row">{MODEL_LABEL[m]}</th><td>{fixed(c.rmse_mm, 2)}</td><td>{fixed(c.mae_mm, 2)}</td><td>{fixed(c.bias_mm, 2)}</td><td>{c.pairs.toLocaleString("en-GB")}</td></tr>; })}</tbody></table></div>
    <div className="district-table-wrap"><table className="phase5-table regime-evidence-table"><caption className="sr-only">Paired change in district-mean absolute error between models</caption>
      <thead><tr><th scope="col">Contrast (first vs second)</th><th scope="col">Mean of (|err second| − |err first|), mm · 95 % interval</th></tr></thead>
      <tbody>{Object.entries(data.contrasts.continuous).map(([key, stat]) => { const [a, b] = key.split("_vs_"); return <tr key={key}><th scope="row">{MODEL_LABEL[a]} vs {MODEL_LABEL[b]}</th><td>{interval(stat, 3)}</td></tr>; })}</tbody></table></div>
    <p className="micro-note">Positive means the first model&rsquo;s district mean is closer to IMD on average. Lower mean error and better event detection are different properties: compare this table with the event tables below.</p>

    <h3>District events</h3>
    <div className="phase5-tab-row" role="group" aria-label="Event definition">{DISTRICT_DEFINITIONS.map((item) => <button key={item} type="button" aria-pressed={definition === item} onClick={() => setDefinition(item)}>{DEFINITION_LABEL[item]}</button>)}</div>
    <div className="phase5-controls">
      <div className="phase5-tab-row" role="group" aria-label="Rainfall threshold"><button type="button" aria-pressed={threshold === "heavy"} onClick={() => setThreshold("heavy")}>Heavy ≥ 64.5 mm / 24 h</button><button type="button" aria-pressed={threshold === "very_heavy"} onClick={() => setThreshold("very_heavy")}>Very Heavy ≥ 115.6 mm / 24 h</button></div>
      <div className="phase5-tab-row" role="group" aria-label="Event metric">{METRICS.map((item) => <button key={item.key} type="button" aria-pressed={metric === item.key} onClick={() => setMetric(item.key)}>{item.label}</button>)}</div>
      <div className="phase5-tab-row" role="group" aria-label="Breakdown">{DISTRICT_BREAKDOWNS.map((item) => <button key={item} type="button" aria-pressed={breakdown === item} onClick={() => setBreakdown(item)}>{BREAKDOWN_LABEL[item]}</button>)}</div>
    </div>
    <div className="district-table-wrap"><table className="phase5-table regime-evidence-table"><caption className="sr-only">{METRICS.find((item) => item.key === metric)?.label} for {definition} {threshold === "heavy" ? "heavy" : "very heavy"} district events, {BREAKDOWN_LABEL[breakdown].toLowerCase()}</caption>
      <thead><tr><th scope="col">Group</th>{EVIDENCE_MODELS.map((m) => <th scope="col" key={m}>{MODEL_LABEL[m]}</th>)}</tr></thead>
      <tbody>{Object.entries(blocks).map(([name, perModel]) => <tr key={name}><th scope="row">{groupLabel(breakdown, name)}<span className="micro-note"> {perModel.M0.observed_event_count} observed events</span></th>
        {EVIDENCE_MODELS.map((m) => { const cell = perModel[m]; const text = metric === "ratio" ? (cell.observed_event_count ? fixed(cell.forecast_event_count / cell.observed_event_count, 3) : "undefined") : fixed(cell[metric], 3); return <td key={m}>{text}{metric === "ratio" ? <span className="micro-note"> · fcst {cell.forecast_event_count}</span> : null}</td>; })}</tr>)}</tbody></table></div>
    <p className="micro-note">Undefined means no forecast or observed event in that group (never shown as 0). Values near 0 in the ratio mean the model forecasts almost no events at this threshold.</p>

    <h3>Paired differences in CSI · {DEFINITION_LABEL[definition]} · {threshold === "heavy" ? "heavy" : "very heavy"}</h3>
    <div className="district-table-wrap"><table className="phase5-table regime-evidence-table"><caption className="sr-only">Paired whole-case bootstrap differences in district-event CSI</caption>
      <thead><tr><th scope="col">Contrast</th><th scope="col">Δ CSI [95 % interval]</th></tr></thead>
      <tbody>{DISTRICT_CONTRAST_KEYS.map((key) => <tr key={key}><th scope="row">{PAIR_LABEL[key]}</th><td>{interval(data.contrasts.categorical[definition][threshold][key]?.CSI)}</td></tr>)}</tbody></table></div>

    <h3>Districts improved or worsened versus Raw</h3>
    <div className="district-table-wrap"><table className="phase5-table regime-evidence-table"><caption className="sr-only">Number of districts improved, worsened or indeterminate versus Raw, with the number expected by chance</caption>
      <thead><tr><th scope="col">Model</th><th scope="col">Districts tested</th><th scope="col">Improved</th><th scope="col">Worsened</th><th scope="col">Indeterminate</th><th scope="col">Expected by chance (total / per direction)</th></tr></thead>
      <tbody>{DISTRICT_MODELS.map((m) => { const c = data.improved_worsened[m]; return <tr key={m}><th scope="row">{MODEL_LABEL[m]}</th><td>{c.tested_districts}</td><td>{c.improved}</td><td>{c.worsened}</td><td>{c.indeterminate}</td><td>{c.expected_by_chance_total} / {c.expected_by_chance_per_direction}</td></tr>; })}</tbody></table></div>
    <p className="micro-note">&ldquo;Improved&rdquo; means a district&rsquo;s mean (|Raw error| − |model error|) is positive and its 95 % paired whole-case interval excludes 0; with this many districts tested, about 5 % in total would be classified improved or worsened by chance even with no true effect.</p>

    <h3>District map and table</h3>
    <div className="phase5-controls">
      <label>Corrected model<select value={model} onChange={(event) => setModel(event.target.value as DistrictModel)}>{DISTRICT_MODELS.map((m) => <option key={m} value={m}>{MODEL_LABEL[m]}</option>)}</select></label>
      <label className="phase5-check"><input type="checkbox" checked={supportedOnly} onChange={(event) => setSupportedOnly(event.target.checked)} /> Only districts with ≥ 30 observed heavy events (E1)</label>
    </div>
    {geometry.data ? <div className="districts-layout"><section className="districts-map-panel" aria-label="District improvement map"><div className="map-panel-heading"><div><strong>Mean improvement vs Raw · {MODEL_LABEL[model]}</strong><span>{mapDistricts.length} districts with ≥ 30 included cases · {excluded.length} excluded for coverage</span></div></div>
      <MapControls district onReset={() => mapRef.current?.fitBounds(mapBounds([67.875, 9.875, 80.125, 22.125]), { padding: 18, duration: 0 })} onZoom={(delta) => mapRef.current?.zoomTo((mapRef.current?.getZoom() ?? 0) + delta, { duration: 150 })} />
      <DistrictMap geometry={geometry.data.geometry} districts={mapDistricts} selectedId={selected?.district_id ?? null} onSelect={setSelectedId} onReady={(map) => { mapRef.current = map; }} colorFor={improvementColor} />
      <div className="district-map-legend"><ImprovementLegend /></div>
      <p className="micro-note">Polygon colour is each district&rsquo;s mean over its cases of (|Raw − IMD| − |model − IMD|) for the district mean, in mm; grey districts are excluded or lack support. Not a skill score by itself: read it with the status column.</p></section>
      <aside className="district-detail"><span className="small-label">DISTRICT VERIFICATION</span>{selected ? <><h2>{selected.district_name}</h2><p className="micro-note">{selected.region} · {selected.included_cases} included cases · median {selected.median_valid_cells} valid cells</p>
        {selected.improvement !== "insufficient_support" ? <table className="phase5-table district-model-table"><caption className="sr-only">Improvement versus Raw for the selected district</caption><thead><tr><th scope="col">Model</th><th scope="col">Mean improvement</th><th scope="col">Status</th></tr></thead>
          <tbody>{DISTRICT_MODELS.map((m) => { const v = selected.improvement === "insufficient_support" ? null : selected.improvement[m]; return <tr key={m}><th scope="row">{m}</th><td>{v ? `${fixed(v.mean_improvement_mm, 2)} mm [${fixed(v.interval95[0], 2)}, ${fixed(v.interval95[1], 2)}]` : "—"}</td><td>{v?.status ?? "—"}</td></tr>; })}</tbody></table> : <p>Insufficient support.</p>}
        {(["heavy", "very_heavy"] as const).map((key) => { const cell = selected.categorical.E1[key]; return <p key={key} className="micro-note"><b>E1 {key === "heavy" ? "heavy" : "very heavy"}:</b> {cell.observed_events} observed events · {cell.status === "supported" && cell.models ? `CSI Raw ${fixed(cell.models.M0.CSI)}, ${model} ${fixed(cell.models[model].CSI)}` : "insufficient support (fewer than 30 observed events)"}</p>; })}</> : <p>Select a district.</p>}</aside></div> : null}
    <div className="district-table-wrap"><table className="science-table district-table"><caption className="sr-only">Per-district mean improvement versus Raw, status and E1 heavy-event support</caption>
      <thead><tr><th scope="col">District</th><th scope="col">Region</th><th scope="col">Cases</th><th scope="col">Mean improvement (mm)</th><th scope="col">95 % interval</th><th scope="col">Status</th><th scope="col">E1 heavy observed events</th><th scope="col">E1 heavy CSI Raw / {model}</th></tr></thead>
      <tbody>{ordered.map((entry) => { const imp = entry.improvement === "insufficient_support" ? null : entry.improvement[model]; const cell = entry.categorical.E1.heavy; return <tr key={entry.district_id} className={entry.district_id === selected?.district_id ? "selected-row" : ""}>
        <th scope="row"><button type="button" onClick={() => setSelectedId(entry.district_id)}>{entry.district_name}</button></th><td>{entry.region}</td><td>{entry.included_cases}</td>
        <td>{fixed(imp?.mean_improvement_mm, 2)}</td><td>[{fixed(imp?.interval95[0], 2)}, {fixed(imp?.interval95[1], 2)}]</td><td>{imp?.status ?? "insufficient support"}</td><td>{cell.observed_events}</td>
        <td>{cell.status === "supported" && cell.models ? `${fixed(cell.models.M0.CSI)} / ${fixed(cell.models[model].CSI)}` : "insufficient support"}</td></tr>; })}</tbody></table></div>
    {excluded.length ? <details className="micro-note"><summary>{excluded.length} districts excluded for coverage (median valid cells below {data.inclusion.min_valid_cells})</summary><p>{excluded.map((item) => `${item.district_name} (${item.median_valid_cells})`).join(" · ")}</p></details> : null}

    <h3>Method and limitations</h3>
    <ul className="phase5-caveats">{data.caveats.map((caveat) => <li className="phase5-caveat" key={caveat}>{caveat}</li>)}<li className="phase5-caveat">Regime assignment: {data.regime_assignment}.</li></ul>
  </section>;
}

export type { DistrictVerification };
